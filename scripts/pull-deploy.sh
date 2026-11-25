#!/usr/bin/env bash
# 服务器端定时部署：检测 ACR 最新镜像 digest，有更新才拉取重建，失败自动回滚
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/wuliu}"
ENV_FILE="$APP_DIR/.env"
DIGEST_FILE="$APP_DIR/.deployed_digest"
LOCK_FILE=/tmp/wuliu-pull.lock
CHECK_LOG=/tmp/wuliu-pull-check.log
SERVICE=wuliu
CONTAINER=wuliu-app

cd "$APP_DIR"

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  exit 0
fi

read_env() {
  grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '\r' || true
}

ACR_REGISTRY=$(read_env ACR_REGISTRY)
ACR_USERNAME=$(read_env ACR_USERNAME)
ACR_PASSWORD=$(read_env ACR_PASSWORD)
IMAGE_BASE=$(read_env APP_IMAGE_BASE)
LATEST_IMAGE="$IMAGE_BASE:latest"

if [ -z "$ACR_REGISTRY" ] || [ -z "$ACR_USERNAME" ] || [ -z "$ACR_PASSWORD" ] || [ -z "$IMAGE_BASE" ]; then
  echo "$(date '+%F %T') 配置缺失：请检查 $ENV_FILE" >> "$CHECK_LOG"
  exit 1
fi

echo "$ACR_PASSWORD" | docker login "$ACR_REGISTRY" --username "$ACR_USERNAME" --password-stdin >/dev/null 2>&1

REMOTE_DIGEST=$(docker manifest inspect "$LATEST_IMAGE" 2>/dev/null | grep -oE 'sha256:[0-9a-f]{64}' | head -1 || true)
[ -z "$REMOTE_DIGEST" ] && exit 0

OLD_DIGEST=$(cat "$DIGEST_FILE" 2>/dev/null || echo "")
[ "$REMOTE_DIGEST" = "$OLD_DIGEST" ] && exit 0

# 首次部署（mysql 尚未创建）与常规更新走不同分支
if ! docker ps -a --format '{{.Names}}' | grep -qx wuliu-mysql; then
  echo "$(date '+%F %T') FIRST_DEPLOY $REMOTE_DIGEST" >> "$CHECK_LOG"
  docker compose up -d >/dev/null 2>&1 || { echo "$(date '+%F %T') first deploy failed" >> "$CHECK_LOG"; exit 1; }
else
  # 用不可变的 image id 记录回滚点，避免 :latest 标签已被覆盖导致回滚失效
  PREV_ID=$(docker inspect -f '{{.Image}}' "$CONTAINER" 2>/dev/null || true)
  if [ -n "$PREV_ID" ]; then
    docker tag "$PREV_ID" "$IMAGE_BASE:rollback" >/dev/null 2>&1 || true
  fi

  docker pull "$LATEST_IMAGE" >/dev/null 2>&1 || { echo "$(date '+%F %T') pull failed" >> "$CHECK_LOG"; exit 1; }

  if grep -q '^APP_IMAGE=' "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^APP_IMAGE=.*|APP_IMAGE=$LATEST_IMAGE|" "$ENV_FILE"
  else
    echo "APP_IMAGE=$LATEST_IMAGE" >> "$ENV_FILE"
  fi

  APP_IMAGE="$LATEST_IMAGE" docker compose up -d --no-deps --force-recreate "$SERVICE" >/dev/null 2>&1 || true
fi

ok=0
for _ in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1/api/health || true)
  if [ "$code" = "200" ]; then
    ok=1
    break
  fi
  sleep 2
done

if [ "$ok" = "1" ]; then
  echo "$REMOTE_DIGEST" > "$DIGEST_FILE"
  docker image prune -f >/dev/null 2>&1 || true
  echo "$(date '+%F %T') DEPLOY_OK http=$code image=$LATEST_IMAGE" >> "$CHECK_LOG"
  exit 0
fi

echo "$(date '+%F %T') health failed, rolling back" >> "$CHECK_LOG"
if docker image inspect "$IMAGE_BASE:rollback" >/dev/null 2>&1; then
  sed -i "s|^APP_IMAGE=.*|APP_IMAGE=$IMAGE_BASE:rollback|" "$ENV_FILE"
  APP_IMAGE="$IMAGE_BASE:rollback" docker compose up -d --no-deps --force-recreate "$SERVICE" >/dev/null 2>&1 || true
fi
echo "$(date '+%F %T') DEPLOY_FAILED rolled back" >> "$CHECK_LOG"
exit 1

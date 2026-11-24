#!/usr/bin/env bash
# ECS 定时部署脚本：检测 ACR latest 镜像 digest，有更新才拉取并重建容器，失败自动回滚
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/huanuo-ai}"
ENV_FILE="$APP_DIR/.env"                 # 根目录部署配置（含 ACR 凭证，切勿入库）
DIGEST_FILE="$APP_DIR/.deployed_digest"  # 已部署镜像的 digest
LAST_FILE="$APP_DIR/.last_good_image"    # 回滚点
LOCK_FILE=/tmp/huanuo-pull.lock
CHECK_LOG=/tmp/huanuo-pull-check.log
SERVICE=huanuo
CONTAINER=huanuo-ai

cd "$APP_DIR"

# 并发锁：防止两次 cron 任务重叠执行
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  exit 0
fi

# 读取配置的工具函数（.env 中值不要用引号包裹）
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

# ACR token 会过期，每次都登录
echo "$ACR_PASSWORD" | docker login "$ACR_REGISTRY" --username "$ACR_USERNAME" --password-stdin >/dev/null 2>&1

# 只取远端 digest 元数据，不下载镜像体
REMOTE_DIGEST=$(docker manifest inspect "$LATEST_IMAGE" 2>/dev/null | grep -m1 '"digest"' | sed 's/.*"digest"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' || true)
[ -z "$REMOTE_DIGEST" ] && exit 0

OLD_DIGEST=$(cat "$DIGEST_FILE" 2>/dev/null || echo "")
[ "$REMOTE_DIGEST" = "$OLD_DIGEST" ] && exit 0   # 无更新，零开销退出

# 记录回滚点（当前正在运行的镜像）
CURRENT_IMAGE=$(docker inspect -f '{{.Config.Image}}' "$CONTAINER" 2>/dev/null || true)
[ -n "$CURRENT_IMAGE" ] && echo "$CURRENT_IMAGE" > "$LAST_FILE"

# 拉取新镜像
docker pull "$LATEST_IMAGE" >/dev/null 2>&1 || { echo "$(date '+%F %T') pull failed" >> "$CHECK_LOG"; exit 1; }

# 只重建 app 容器，数据库卷与数据文件全程不动
if grep -q '^APP_IMAGE=' "$ENV_FILE" 2>/dev/null; then
  sed -i "s|^APP_IMAGE=.*|APP_IMAGE=$LATEST_IMAGE|" "$ENV_FILE"
else
  echo "APP_IMAGE=$LATEST_IMAGE" >> "$ENV_FILE"
fi
APP_IMAGE="$LATEST_IMAGE" docker compose up -d --no-deps --force-recreate "$SERVICE" >/dev/null 2>&1

# 健康检查：/api/health 返回 200 视为成功（最多约 90 秒）
ok=0
for i in $(seq 1 45); do
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

# 失败回滚到上一个正常镜像
echo "$(date '+%F %T') health failed, rolling back" >> "$CHECK_LOG"
if [ -n "$CURRENT_IMAGE" ]; then
  sed -i "s|^APP_IMAGE=.*|APP_IMAGE=$CURRENT_IMAGE|" "$ENV_FILE"
  APP_IMAGE="$CURRENT_IMAGE" docker compose up -d --no-deps --force-recreate "$SERVICE" >/dev/null 2>&1
fi
echo "$(date '+%F %T') DEPLOY_FAILED rolled back" >> "$CHECK_LOG"
exit 1

#!/usr/bin/env bash
# 首次上线手动初始化脚本：只从 ACR 拉取镜像并启动，不在服务器构建
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/huanuo-ai}"
cd "$APP_DIR"

ENV_FILE="$APP_DIR/.env"
read_env() {
  grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '\r' || true
}
ACR_REGISTRY=$(read_env ACR_REGISTRY)
ACR_USERNAME=$(read_env ACR_USERNAME)
ACR_PASSWORD=$(read_env ACR_PASSWORD)
IMAGE_BASE=$(read_env APP_IMAGE_BASE)
LATEST_IMAGE="$IMAGE_BASE:latest"

echo "==> 检查 Docker"
docker --version
docker compose version

# SQLite 数据库文件需预先存在，否则 bind mount 会被创建成目录
mkdir -p "$APP_DIR/Backend_template"
[ -f "$APP_DIR/Backend_template/huanuo.db" ] || touch "$APP_DIR/Backend_template/huanuo.db"

echo "==> 登录 ACR 并拉取镜像"
echo "$ACR_PASSWORD" | docker login "$ACR_REGISTRY" --username "$ACR_USERNAME" --password-stdin
docker pull "$LATEST_IMAGE"

echo "==> 启动应用（只重建 app，不动数据卷）"
APP_IMAGE="$LATEST_IMAGE" docker compose up -d --no-deps huanuo

echo "==> 等待健康检查"
for i in $(seq 1 45); do
  if curl -fsS "http://127.0.0.1/api/health" >/dev/null 2>&1; then
    echo "服务已就绪: http://$(curl -fsS ifconfig.me 2>/dev/null || echo 'SERVER_IP')"
    curl -fsS "http://127.0.0.1/api/health"
    echo
    echo "==> 对齐 digest 基线，避免首次轮询误触发重复部署"
    docker manifest inspect "$LATEST_IMAGE" \
      | grep -m1 '"digest"' \
      | sed 's/.*"digest"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/' > "$APP_DIR/.deployed_digest"
    exit 0
  fi
  sleep 2
done

echo "启动超时，查看日志："
docker compose logs --tail=80
exit 1

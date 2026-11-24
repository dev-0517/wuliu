#!/usr/bin/env bash
# ECS 服务器一键初始化：拉代码 -> 校验 .env -> 首次部署 -> 配置定时轮询
# 用法：在 ECS 上运行 bash deploy/ecs-init.sh
# 前置：已创建 /opt/huanuo-ai/.env（ACR 凭证）与 Backend_template/.env（应用配置）
set -euo pipefail

REPO_URL="https://github.com/dev-0517/wuliu.git"
APP_DIR="${APP_DIR:-/opt/huanuo-ai}"
SERVER_IP="120.55.102.191"

echo "==> 检查前置条件"
command -v docker >/dev/null 2>&1 || { echo "请先安装 Docker"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "缺少 docker compose 插件"; exit 1; }

echo "==> 获取代码"
if [ -d "$APP_DIR/.git" ]; then
  (cd "$APP_DIR" && git pull --ff-only)
else
  mkdir -p "$(dirname "$APP_DIR")"
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

[ -f .env ] || { echo "缺少 $APP_DIR/.env（ACR 凭证），请先创建"; exit 1; }
[ -f Backend_template/.env ] || { echo "缺少 $APP_DIR/Backend_template/.env（应用配置），请先创建"; exit 1; }
chmod 600 .env Backend_template/.env
chmod +x scripts/pull-deploy.sh deploy/deploy.sh

echo "==> 首次部署（只拉镜像，不构建）"
bash deploy/deploy.sh

echo "==> 配置定时轮询（每 2 分钟）"
CRON_LINE="*/2 * * * * cd $APP_DIR && flock -n /tmp/huanuo-cron.lock bash scripts/pull-deploy.sh >> /tmp/huanuo-pull-check.log 2>&1"
( crontab -l 2>/dev/null || true; echo "$CRON_LINE" ) | sort -u | crontab -
echo "cron 当前条目："
crontab -l | grep pull-deploy || true

echo "==> 验证"
curl -fsS "http://127.0.0.1/api/health" && echo
echo "DONE: http://$SERVER_IP"

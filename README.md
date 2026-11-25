# 物流管理系统

Vue 3 + FastAPI + MySQL 的物流后台，含 GitHub Actions 自动构建与服务器自动部署。

## 功能

- 登录鉴权（JWT），角色区分管理员 / 操作员
- 运营总览：运单总数、今日新建、各状态分布、网点车辆司机数量
- 运单管理：新建、列表检索（单号 / 姓名 / 电话 / 货物）、状态流转、物流轨迹时间线
- 基础资料：网点、车辆、司机的增删改查

演示账号：`admin / admin123`（管理员）、`operator / operator123`（操作员）

## 本地开发

```bash
# 后端（默认 SQLite，无需装数据库）
cd Backend_template
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python serve.py          # http://127.0.0.1:8000

# 前端
cd frontend_template
npm install
npm run dev                            # http://127.0.0.1:5173，/api 代理到 8000
```

## 生产部署

`docker compose` 起两个容器：`wuliu-mysql`（MySQL 8）与 `wuliu-app`（API + 静态页面，暴露 80）。

镜像由 GitHub Actions 在云端构建并推送到阿里云 ACR，服务器上 `scripts/pull-deploy.sh` 每 2 分钟比对 digest，有更新才拉取重建，健康检查失败自动回滚到上一个镜像。

服务器目录约定 `/opt/wuliu`，配置写在根目录 `.env`（镜像仓库凭证 + MySQL 密码）与 `Backend_template/.env`（应用配置）。

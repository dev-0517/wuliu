# 华诺 AI 助手 · GitHub Actions 自动化部署实现步骤

> 参照《康膳 SmartDiet 自动化部署实现步骤》的方案，适配本项目「FastAPI + Vue 同源单镜像 + SQLite」的技术栈。
> 已知配置已填入：GitHub 仓库 `https://github.com/dev-0517/wuliu.git`（公开），ECS `120.55.102.191`，
> ACR Registry `crpi-bez2magwy58wcu7z.cn-hangzhou.personal.cr.aliyuncs.com`，命名空间 `wuliu11`，仓库名 `wuliu`。
> 仍以 `<占位符>` 表示的用户名/密码请在实际环境中填写；**不要把凭证提交到代码仓库**。案件测试目录已在 `.gitignore` 中排除。

---

## 一、方案总览

### 1. 一句话概括

开发者只需 `git push` 到 `main`：GitHub Actions 云端构建出包含前端与后端的单镜像并推送到阿里云 ACR；ECS 服务器每 2 分钟检查镜像 digest，发现更新后自动拉取、只重建 app 容器、健康检查，失败则自动回滚。

### 2. 与康膳方案的关键差异

| 维度 | 康膳（Next.js） | 本项目（华诺 AI） |
| --- | --- | --- |
| 技术栈 | Node/Next.js 单语言 | Vue(Vite) 前端 + Python/FastAPI 后端 |
| 镜像结构 | 前后端同一 Node 镜像 | 多阶段：Node 构建静态产物 → Python 镜像运行 `serve.py` 同源托管 |
| 数据库 | MySQL 独立容器 + 数据卷 | SQLite 文件 bind mount，无需独立 db 容器 |
| 健康检查 | `curl :3000`（接受 200/302/307） | `curl :80/api/health`（要求 200） |
| 服务名 / 容器名 | `app` / `kangshan-web` | `huanuo` / `huanuo-ai` |

### 3. 完整流程图

```text
① git push main
        │
        ▼
② GitHub Actions：Node 阶段 npm build → Python 阶段打包 serve.py + 前端 dist
        │
        ▼
③ docker push ACR（commit tag + latest）
        │
        ▼
④ ECS cron 每 2 分钟检测 latest 的 digest
        │
   ┌────┴────┐
 无变化     有变化
   │         │
   │   ⑤ docker pull + 只重建 huanuo 容器（--no-deps）
   │         │
   │   ⑥ 健康检查 curl 127.0.0.1/api/health
   │         │
   │   ┌─────┴─────┐
   │ 成功         失败
   │   │           │
   │ 写 digest   自动回滚旧镜像
   └───┴───────────┘
```

### 4. 为什么服务器绝不构建

ECS 只有 1~2G 内存，本项目前端 `vite build` 与后端依赖安装放在服务器会拖慢甚至拖挂服务。构建全部放到 GitHub 云端，镜像作为唯一交付物，杜绝环境不一致。

---

## 二、关键文件清单

| 文件 | 位置 | 作用 |
| --- | --- | --- |
| `Dockerfile` | 仓库根目录 | 多阶段构建：Node 编译 Vue → Python 运行时同源托管 |
| `.dockerignore` | 仓库根目录 | 排除 node_modules / .venv / .env / *.db / dist 等 |
| `docker-compose.yml` | 仓库 + ECS | **只拉镜像版**（无 `build:` 段），注入 `APP_IMAGE` |
| `.github/workflows/deploy.yml` | 仓库 | 云端构建并推送镜像到 ACR |
| `scripts/pull-deploy.sh` | 仓库 + ECS | 检测更新、拉取、只重建 app、健康检查、失败回滚 |
| `deploy/deploy.sh` | 仓库 + ECS | 首次上线手动初始化（只拉镜像，不构建） |
| `.env.example` | 仓库根目录 | ECS 部署配置模板（根目录 `.env`，切勿入库） |
| `Backend_template/.env` | 仅 ECS 本地 | 应用运行配置（DeepSeek 密钥等，切勿入库） |
| `.deployed_digest` / `.last_good_image` | 仅 ECS 本地 | 已部署指纹与回滚点，脚本自动维护 |

---

## 三、第一步：准备代码仓库

1. 本项目目录目前**不是 Git 仓库**，需先初始化并推送到 GitHub 仓库 `dev-0517/wuliu`（当前为公开仓库，注意不要提交敏感材料）：

   ```bash
   cd D:/Specialized\ and\ Higher/专业/专高五2/项目/hua-nuo-ai-main
   git init
   git add .
   git commit -m "init: 华诺 AI 自动化部署"
   git remote add origin https://github.com/dev-0517/wuliu.git
   git push -u origin main
   ```

   > push 成功后，Actions 页面应出现名为「华诺 AI 自动部署」的 run。

2. 确认 `.gitignore` 已排除 `**/.env`、`**/*.db`、`**/node_modules/`、`**/dist/` 等；根目录 `.env.example` 可入库作模板。

3. 配置 GitHub Secrets（仓库 Settings → Secrets and variables → Actions → New repository secret）：

   | Secret | 说明 |
   | --- | --- |
   | `ACR_REGISTRY` | 已确定：`crpi-bez2magwy58wcu7z.cn-hangzhou.personal.cr.aliyuncs.com` |
   | `ACR_NAMESPACE` | 已确定：`wuliu11` |
   | `ACR_REPO` | 已确定：`wuliu` |
   | `ACR_USERNAME` | 已确定：`nick6504622135` |
   | `ACR_PASSWORD` | ACR 登录密码（或访问凭证） |

   > 使用 Secrets 而非在 workflow 里明文写凭证。当前 PAT 尝试通过 API 写入 Secrets 返回 403（缺少 Secrets 写权限），
   > 需在 GitHub 网页端手动添加以上 5 个 Secret，或给 PAT 勾选 Repository → Secrets: Read and write 后重试。
   > 由于当前仓库是公开仓库，**切勿把 ACR 密码写进 workflow 文件**。

---

## 四、第二步：ECS 服务器配置

### 1. 目录结构

```text
/opt/huanuo-ai/
├── docker-compose.yml          # 从仓库同步（只拉镜像版）
├── .env                        # 根目录部署配置（含 ACR 凭证，chmod 600）
├── .deployed_digest            # 已部署镜像 digest
├── .last_good_image            # 回滚点
├── deploy/deploy.sh            # 首次初始化脚本
├── scripts/pull-deploy.sh      # 定时部署脚本
└── Backend_template/
    ├── .env                    # 应用运行配置（DEEPSEEK_API_KEY 等）
    └── huanuo.db               # SQLite 数据文件（首次需存在）
```

### 2. 根目录 `.env`（部署配置）

```ini
ACR_REGISTRY=crpi-bez2magwy58wcu7z.cn-hangzhou.personal.cr.aliyuncs.com
ACR_USERNAME=nick6504622135
ACR_PASSWORD=<ACR_PASSWORD>
APP_IMAGE_BASE=crpi-bez2magwy58wcu7z.cn-hangzhou.personal.cr.aliyuncs.com/wuliu11/wuliu
```

> 值不要用引号包裹。部署脚本会自动读写 `APP_IMAGE` 行，无需手动配置。设置 `chmod 600 .env`。

### 3. `Backend_template/.env`（应用配置）

按 `.env.example` 填写，至少包含：

```ini
DATABASE_URL=sqlite+aiosqlite:///./huanuo.db
DEEPSEEK_API_KEY=<DEEPSEEK_API_KEY>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
CORS_ORIGINS=http://120.55.102.191,http://localhost,http://127.0.0.1
```

### 4. 配置 cron

```bash
chmod +x /opt/huanuo-ai/scripts/pull-deploy.sh
crontab -e
```

加入（每 2 分钟，外层再加一把锁）：

```cron
*/2 * * * * cd /opt/huanuo-ai && flock -n /tmp/huanuo-cron.lock bash scripts/pull-deploy.sh >> /tmp/huanuo-pull-check.log 2>&1
```

确认 cron 服务运行中：`systemctl status cron`。

---

## 五、第三步：首次部署

```bash
# 1. 把仓库的 docker-compose.yml、deploy/、scripts/ 同步到 /opt/huanuo-ai
#    注意：compose 必须无 build: 段，否则服务器本地构建会拖垮服务

# 2. 按上面两节创建根目录 .env 与 Backend_template/.env，并 chmod 600

# 3. 如已有历史数据，把旧 huanuo.db 放到 Backend_template/huanuo.db

# 4. 首次初始化（拉镜像、启动、对齐 digest 基线）
bash deploy/deploy.sh

# 5. 验证
curl http://127.0.0.1/api/health
# 访问 http://120.55.102.191 应看到登录页
```

---

## 六、日常发布流程

1. 本地修改代码，`git add` → `git commit` → `git push origin main`。
2. 等待 Actions 构建完成（约 2～4 分钟），确认 run 成功、日志末尾有 `PUSHED ...`。
3. ECS 最多 2 分钟后自动拉取并重启；`tail -f /tmp/huanuo-pull-check.log` 看到 `DEPLOY_OK` 即成功。

---

## 七、故障排查

| 现象 | 可能原因 | 处理 |
| --- | --- | --- |
| Actions 构建失败 | Secrets 配置错误 / 网络 | 检查 workflow 的 ACR Secrets 与 Actions 日志 |
| 线上长时间不更新 | cron 未执行 / digest 未变化 | `systemctl status cron`；看日志是否为空或 mirror 拉取失败 |
| 服务器响应慢或卡死 | compose 仍是 build 版 | 确认 compose 无 `build:` 段，改回只拉镜像版 |
| 数据库打不开 / 空库 | `huanuo.db` 不存在或权限不足 | 确保 `Backend_template/huanuo.db` 是文件而非目录 |
| 日志出现 `DEPLOY_FAILED` | 健康检查未通过 | 脚本已自动回滚；查 `docker compose logs --tail=80` |
| 登录凭证失效 | 重建时换了数据库文件 | 检查 bind mount 路径与 `DATABASE_URL` 是否一致 |

---

## 八、安全与后续改进

1. `.env` 权限设为 `chmod 600`，并定期备份 `Backend_template/huanuo.db`。
2. 如需 push 后立即部署，可由 Actions 通过 SSH/webhook 主动通知 ECS，替代 2 分钟轮询，但需评估 ECS 暴露接口的安全风险。
3. 目前回滚点是「上一个容器镜像」；如需精确到任意历史版本，可用 workflow 推送的 commit tag 手动指定 `APP_IMAGE`。

# 华诺 AI 助手 v0.2

这是基于三份需求资料开发的本地内部试用版本。采用 Vue 3 + Axios + FastAPI + SQLAlchemy，使用 DeepSeek 工具调用查询当前用户的案件。首版默认 SQLite，安装后无需另行配置数据库服务。


## v0.2 升级内容

- **两种对话模式**：AI 助手页面可直接开始日常聊天，也可选择案件咨询。日常聊天不读取案件或提供案件查询工具；案件咨询第一轮强制查询所选案件及材料。
- **深入案情分析**：按案件类型整理事实陈述、原文摘录、争议、缺失信息、时间线、关注事项、下一步和追问。来源编号和逐字摘录由服务端校验；引用存在不等于事实或证据已经核实。
- **来源快照**：案件回答可展开本轮查阅的记录；保留生成时的原文与材料状态。
- **分析版本**：每次成功生成均保留历史版本。案情或材料修改后当前结果失效，历史结果仍可回看。旧版现存分析在替换或失效前也会归档。
- **聊天记录**：支持按日常/案件模式筛选，按标题或消息内容搜索，以及修改标题。日常聊天首轮成功后自动以问题命名。

本工作区已配置小皮 MySQL 的 `huanuo` 数据库，并创建专用 Conda 环境 `HuaNuo`。在项目根目录的 PowerShell 中启动后端：

```powershell
conda activate HuaNuo
cd Backend_template
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

后端启动会执行 v0.2 的幂等增量迁移：允许会话不关联案件，并新增 `message_sources` 和 `analysis_revisions` 表。兼容本项目旧版 SQLite 与 MySQL 数据。MySQL 表会显式采用 InnoDB，旧 MyISAM 表会转为 InnoDB 并补齐级联外键；如发现孤立记录则停止升级并提示处理，不会自动删除记录。升级前应备份数据库，本工作区升级前已备份到后端 `backups/` 目录，该目录不进入 Git。

删除单项材料不会清除已经生成的回答和分析中的快照；删除会话会清除其来源快照，删除案件会级联删除关联分析版本、会话和来源快照。

验证升级：

```powershell
conda run -n HuaNuo python -m pytest Backend_template/tests -q
cd frontend_template
npm run build
npm run test:upgrade
# 可选：使用虚构数据调用真实模型，消耗少量额度
$env:AI_LIVE='1'
npm run test:upgrade
Remove-Item Env:AI_LIVE
```

浏览器检查会创建独立测试账号，结束时清除其案件与会话并退出；测试账号本身会保留。截图只保存到 `test-artifacts/`。普通聊天、案件咨询和深入分析仍使用 JSON 响应，文件上传、OCR、流式输出和报告导出不在本次升级范围内。

## 基础功能

- 登录注册：账号密码登录、主动勾选协议、同意版本与时间留痕、7 天有效登录凭证、退出后服务端立即失效。
- 案件管理：新建、搜索、分页、查看、编辑和删除自己的案件。
- AI 助手：选择案件、强制查询该案件及文字材料后回答、多轮上下文、失败提示、复制回答。
- 历史记录：按近 7 天、近 30 天、近半年筛选，分页、继续咨询、删除。
- 个人中心：查看账号、修改昵称、案件与会话数量。
- 案情整理：AI 生成摘要、争议、缺失信息、带来源说明的时间线、建议材料；结构校验后保存。
- 材料清单：文字记录增删改查、已有/待补充标记；案情或材料变更后使当前分析失效，历史版本保留。
- 页面适配桌面与手机。App.vue 仅挂载路由，业务代码放在独立页面中。

## 本地启动

环境：Node 24 或 package.json 指定的兼容版本，Python 3.11 及以上。以下命令在 PowerShell 执行。

### 1. 启动后端

从本 README 所在目录进入后端：

```powershell
cd Backend_template
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
# 首次配置：只有不存在 .env 时才复制，避免覆盖已填好的密钥
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

编辑 `Backend_template/.env`，填写 `DEEPSEEK_API_KEY`。本次开发已将用户提供的密钥放入本地 `.env`，不要覆盖它，也不要分享该文件。

后端接口文档：http://127.0.0.1:8000/docs

### 2. 启动前端

打开另一个 PowerShell，在本 README 所在目录执行：

```powershell
cd frontend_template
npm ci
npm run dev
```

打开 http://127.0.0.1:5173 ，首次使用请自行注册账号。没有默认密码，也没有自动录入的真实案件。

### 3. 试用流程

注册并同意说明 → 新建案件 → 填写脱敏案情 → 添加文字材料 → 咨询这个案件 → 发送问题 → 咨询记录回看。

案件详情的「AI 案情梳理」可单独生成结构化结果。材料录入状态只代表用户标记，不是律师审核或证据认证。

## 目录与代码阅读顺序

```text
Backend_template/
  main.py                  应用入口、跨域与建表
  config/settings.py       环境变量
  config/db_config.py      数据库连接和会话依赖
  models/data_model.py     数据表
  schemas/                 输入和 AI 结构化输出校验
  routers/auth.py          登录、注册、个人中心
  routers/cases.py         案件、材料、AI 案情整理
  routers/chat.py          问答和历史记录
  crud/cases.py            所有权检查与数据库查询工具
  services/ai_service.py   DeepSeek 调用与工具执行循环
  utils/security.py        密码哈希与登录验证
  tests/                   集成测试
frontend_template/src/
  api/index.js             Axios 实例、凭证与错误处理
  stores/user.js           用户状态
  router/index.js          路由与登录守卫
  components/              公共框架和图标
  views/                   各功能页面
  assets/main.css          桌面与移动端样式
```

原模板中的 router_add、router_get、router_chat、crud_chat、add_pyadntic 等占位文件未接入新应用，可作为原始模板参考。旧的 HomeView、AboutView 和 counter store 同样不再被入口引用。

## AI 如何查询真实数据

1. 后端认证用户，检查会话、案件归属。
2. 给模型提供唯一工具 `get_current_case`，没有 user_id、case_id 或 SQL 参数。
3. 第一轮强制调用工具；后端以已认证用户与当前会话确定查询范围。
4. 工具返回真实案情、诉求、阶段和文字材料。用户记录作为待分析数据处理，不作为系统指令。
5. 模型根据记录回复。案件咨询最多两次供应商请求，日常聊天一次；普通回答最多 2400 tokens，深入分析最多 6000 tokens。
6. 生成成功才成对保存提问、回答和 token 消耗；失败不写入假回答。

技术依据：[DeepSeek 工具调用文档](https://api-docs.deepseek.com/guides/tool_calls/)。开发时已通过 `/models` 确认当前密钥可访问 `deepseek-flash`。模型名称可在 `.env` 修改。

“必须查库”通过代码执行保证；“模型绝不产生事实错误”无法仅靠提示词保证，仍需核对输出。当前没有经审核的法律知识库，不提供精确法条检索或专业结论保证。

## 数据库

默认数据库文件：`Backend_template/huanuo.db`。未配置连接时数据保存在本机 SQLite；本工作区已切换到 MySQL `huanuo`。删除案件会级联删除关联材料、会话、消息、分析版本和来源快照。测试使用单独的临时数据库。

需要 MySQL 时先自行创建数据库，再设置：

```dotenv
DATABASE_URL=mysql+aiomysql://用户名:URL编码后的密码@127.0.0.1:3306/huanuo?charset=utf8mb4
```

首次启动自动建表；不会自动把 SQLite 数据迁移到 MySQL。本工作区已有数据已单独迁移并保留备份。v0.2 包含指定结构的增量迁移，未来其他结构变更仍需要相应迁移方案。

## 验证

在项目目录运行后端测试：

```powershell
.\Backend_template\.venv\Scripts\python -m pytest Backend_template/tests -q
```

前端构建与浏览器检查：

```powershell
cd frontend_template
npm run build
# 需要先启动前后端，默认使用系统 Microsoft Edge，无模型调用费用
npm run test:smoke
# 可选：验证真实 DeepSeek 问答及案情整理，会消耗少量模型额度
$env:AI_LIVE='1'
npm run test:smoke
Remove-Item Env:AI_LIVE
```

浏览器测试会新建专用测试账号和虚构案件，在结束后删除该案件并退出登录；空测试账号会留在本地数据库。截图保存在 `frontend_template/test-artifacts/`，不会进入 Git。没有 Edge 时可修改测试脚本的浏览器 channel，或安装 Playwright 浏览器。

## 当前边界

- 当前用于本机内部试用：不直接部署到公网。
- 协议页面已明确标注内部试用，正式运营主体、联系方式和完整权利请求流程尚待补齐。
- 暂无短信登录、一键登录、找回密码、账号注销、企业/律师角色。
- 暂无文件上传、OCR、音视频解析、律师审核、胜诉率、证据真实性判断。
- 暂用普通 JSON 问答；流式输出是后续迭代项。
- 暂未引入 LangChain：MVP 的单工具调用采用直接 HTTP 请求，保持流程易读，后续可替换 AI 服务层。
- 密码用带随机盐的 scrypt 哈希；服务端仅保存登录凭证哈希，浏览器使用 sessionStorage。开发库没有静态加密，已有升级前手动备份，但尚无自动备份恢复机制。
- 并发与基础限流在单进程内生效；正式上线前需要共享限流、HTTPS、备份、审计、数据保存规则、专业内容评测等实际建设。

密钥只存在后端本地 `.env`，已由 `.gitignore` 排除。不要将物料原文、密钥、数据库、日志或包含真实案情的截图提交到仓库。

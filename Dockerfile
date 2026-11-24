# 多阶段构建：云端一次构建出「前端 + 后端」单镜像
# 阶段一：构建 Vue 前端（Node 22，与 package.json engines 对齐）
FROM node:22-alpine AS frontend
WORKDIR /web
COPY frontend_template/package.json frontend_template/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend_template/ ./
RUN npm run build
# 产物位于 /web/dist

# 阶段二：Python 运行时，serve.py 同源提供 API 与前端静态文件
FROM python:3.12-slim AS runner
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

COPY Backend_template/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY Backend_template/ ./
COPY --from=frontend /web/dist ./frontend_dist

EXPOSE 8000
CMD ["python", "serve.py"]

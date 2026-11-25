# ---------- 阶段一：构建前端 ----------
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend_template/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend_template/ ./
RUN npm run build

# ---------- 阶段二：Python 运行时同时托管 API 与静态产物 ----------
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    FRONTEND_DIST=/app/frontend_dist

COPY Backend_template/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY Backend_template/ ./
COPY --from=web /frontend_dist /app/frontend_dist

EXPOSE 8000
CMD ["python", "serve.py"]

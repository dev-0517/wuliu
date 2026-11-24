"""生产部署入口：单端口同时提供 API 与前端静态文件（同源，无需 CORS/反向代理）。

启动方式：
    python serve.py
"""
import os
from pathlib import Path

import uvicorn
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from main import app

ROOT = Path(__file__).resolve().parent
# 部署时将前端 dist 拷贝到 Backend_template/frontend_dist
DIST = ROOT / "frontend_dist"

if DIST.exists():
    # 挂载静态资源目录（Vite 打包产物）
    assets = DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    # 单页应用 fallback：非 /api 路径一律返回 index.html
    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        # 已知静态文件（favicon 等）直接返回
        candidate = DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        if (DIST / "index.html").exists():
            return FileResponse(str(DIST / "index.html"))
        return JSONResponse({"detail": "frontend not built"}, status_code=404)
else:
    print("[warn] frontend_dist not found; only API will be served.")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    # 必须直接传 app 对象：用字符串 "main:app" 会让 uvicorn 重新导入模块，
    # 导致上面挂载的静态目录与 SPA fallback 全部失效（页面 404）。
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1)

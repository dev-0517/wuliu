import os

import uvicorn
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import FRONTEND_DIST
from main import app


class SPAStaticFiles(StaticFiles):
    """前端为单页应用，未命中的路径回退到 index.html。"""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except Exception:
            index = os.path.join(self.directory, "index.html")
            if os.path.isfile(index):
                return FileResponse(index)
            raise


if FRONTEND_DIST.is_dir():
    app.mount("/", SPAStaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    print(f"[warn] 未找到前端产物目录：{FRONTEND_DIST}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.health import router as health_router
from app.api.routes.attempts import router as attempts_router
from app.api.routes.auth import router as auth_router
from app.api.routes.papers import router as papers_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router)
app.include_router(auth_router, prefix="/api/auth")
app.include_router(papers_router, prefix="/api/papers")
app.include_router(attempts_router, prefix="/api/attempts")

# Uploaded documents and question crops are private, served only by owner-checked routes.

# The separate repair preview serves the built UI and API on one free service.
frontend_dir = os.getenv("FRONTEND_DIST", "")
if frontend_dir and os.path.isdir(frontend_dir):
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    from pathlib import Path
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="ui-assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str):
        if path.startswith(("api/", "uploads/")):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(Path(frontend_dir) / "index.html", headers={"Cache-Control": "no-cache"})

from pathlib import Path
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.routes.imports import router as imports_router
from app.api.routes.health import router as health_router
from app.api.routes.logs import router as logs_router
from app.api.routes.practice import router as practice_router
from app.api.routes.papers import router as papers_router
from app.api.routes.questions import router as questions_router
from app.api.routes.tags import router as tags_router
from app.db.session import init_db
from app.core.settings import settings

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
FRONTEND_INDEX = FRONTEND_DIST / "index.html"
MEDIA_ROOT = Path(__file__).resolve().parents[1] / "media"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(imports_router)
    app.include_router(logs_router)
    app.include_router(practice_router)
    app.include_router(papers_router)
    app.include_router(questions_router)
    app.include_router(tags_router)

    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(MEDIA_ROOT)), name="media")

    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

        @app.get("/")
        def frontend_index() -> FileResponse:
            return FileResponse(FRONTEND_INDEX)

        @app.get("/{full_path:path}")
        def frontend_spa(full_path: str) -> Response:
            if full_path.startswith("api"):
                return Response(status_code=404)
            if full_path.startswith("assets/"):
                return Response(status_code=404)
            return FileResponse(FRONTEND_INDEX)

    return app


app = create_app()

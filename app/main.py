from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router
from app.db.init_db import init_db
from app.storage.s3 import ensure_bucket_exists
from app.vector.qdrant import ensure_collection
from app.core.config import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="Visual Search API")
    app.include_router(router)

    @app.on_event("startup")
    def _startup():
        init_db()
        s = get_settings()
        ensure_bucket_exists(s.s3_bucket)
        ensure_collection()

    return app


app = create_app()


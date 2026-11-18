from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.database import Base
from app.deps import get_db
from app.domain.errors import DomainError
from app.routers import (
    admin_auth,
    admin_settings,
    admin_volunteers,
    admin_week,
    public_volunteer,
)
from app.services.bootstrap import ensure_first_admin, ensure_opening_hours

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_engine(app_settings.database_url, pool_pre_ping=True)
        app.state.engine = engine
        app.state.session_factory = sessionmaker(
            bind=engine, expire_on_commit=False, autoflush=False
        )
        Base.metadata.create_all(engine)
        # Migration légère V1 : create_all ne modifie pas une table existante.
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE admin_users "
                    "ADD COLUMN IF NOT EXISTS gender VARCHAR(8)"
                )
            )
        with app.state.session_factory() as session:
            ensure_opening_hours(session)
            ensure_first_admin(session, app_settings)
        logger.info("API Emmaüs prête.")
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="Disponibilités des bénévoles Emmaüs",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = app_settings

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        fields = [
            ".".join(str(part) for part in error.get("loc", ()) if part not in ("body", "query"))
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "detail": "Certaines données sont invalides. Vérifiez les champs du formulaire.",
                "fields": fields,
            },
        )

    @app.get("/api/health", tags=["technique"])
    def health(session: Session = Depends(get_db)) -> dict[str, str]:
        session.execute(text("SELECT 1"))
        return {"status": "ok"}

    app.include_router(public_volunteer.router)
    app.include_router(admin_auth.router)
    app.include_router(admin_volunteers.router)
    app.include_router(admin_week.router)
    app.include_router(admin_settings.router)
    return app


app = create_app()

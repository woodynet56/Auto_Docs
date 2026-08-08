"""ASGI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.health import router as health_router
from app.api.portal import router as portal_router
from app.api.web import router as web_router
from app.api.webhooks import router as webhook_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.LOG_LEVEL)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.APP_NAME,
        version="0.12.2",
        docs_url=None if settings.APP_ENV == "production" else "/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    application.mount("/static", StaticFiles(directory="app/static"), name="static")
    application.include_router(health_router)
    application.include_router(web_router)
    application.include_router(webhook_router)
    application.include_router(portal_router)
    application.include_router(admin_router)

    return application


app = create_app()

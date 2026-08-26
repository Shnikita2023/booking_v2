from fastapi import FastAPI

from booking.core.config import get_settings
from booking.core.errors import install_error_handlers
from booking.core.logging import RequestIdMiddleware, setup_logging
from booking.routers import auth, events, pages, staff, system


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    app = FastAPI(
        title="Booking API",
        version=settings.app_version,
        docs_url="/docs" if settings.app_env != "prod" else None,
    )
    install_error_handlers(app)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(staff.router)
    app.include_router(events.router)
    app.include_router(pages.router)
    return app


app = create_app()

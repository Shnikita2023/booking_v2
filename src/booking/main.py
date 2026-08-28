from fastapi import FastAPI

from booking.core.config import get_settings
from booking.core.errors import install_error_handlers
from booking.core.logging import RequestIdMiddleware, setup_logging
from booking.routers import auth, events, pages, staff, system
from booking.routers.admin import clients, users
from booking.routers.admin import events as admin_events
from booking.routers.admin import settings as admin_settings
from booking.routers.client import orders as client_orders


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
    app.include_router(client_orders.router)
    app.include_router(admin_events.router)
    app.include_router(clients.router)
    app.include_router(users.router)
    app.include_router(admin_settings.router)
    return app


app = create_app()

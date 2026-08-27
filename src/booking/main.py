import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from booking.core.config import get_settings
from booking.core.errors import install_error_handlers
from booking.core.logging import RequestIdMiddleware, setup_logging
from booking.db.engine import get_session_factory
from booking.routers import auth, events, pages, staff, system
from booking.routers.client import orders as client_orders
from booking.services.order_service import OrderService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_expire_reservations())
    try:
        yield
    finally:
        task.cancel()


async def _expire_reservations() -> None:
    while True:
        await asyncio.sleep(60)
        try:
            factory = get_session_factory()
            async with factory() as session:
                await OrderService(session).cleanup_expired()
        except Exception:  # noqa: BLE001 - background task must not crash app
            pass


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    app = FastAPI(
        title="Booking API",
        version=settings.app_version,
        docs_url="/docs" if settings.app_env != "prod" else None,
        lifespan=lifespan,
    )
    install_error_handlers(app)
    app.add_middleware(RequestIdMiddleware)
    app.include_router(system.router)
    app.include_router(auth.router)
    app.include_router(staff.router)
    app.include_router(events.router)
    app.include_router(pages.router)
    app.include_router(client_orders.router)
    return app


app = create_app()

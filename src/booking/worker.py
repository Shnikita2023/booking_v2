import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from booking.db.engine import get_session_factory
from booking.services.order_service import OrderService

logger = logging.getLogger("booking.worker")


async def cleanup_once() -> None:
    factory = get_session_factory()
    async with factory() as session:
        released = await OrderService(session).cleanup_expired()
        if released:
            logger.info("Expired reservations released: %d", released)


def build_scheduler(interval_seconds: int | None = None) -> AsyncIOScheduler:
    interval = interval_seconds or 60
    scheduler: AsyncIOScheduler = AsyncIOScheduler()
    scheduler.add_job(
        cleanup_once,
        "interval",
        seconds=interval,
        id="cleanup_expired",
        max_instances=1,
        coalesce=True,
    )
    return scheduler


async def run_worker(interval_seconds: int | None = None) -> None:
    scheduler = build_scheduler(interval_seconds)
    scheduler.start()
    logger.info("Cleanup worker started (interval=%ss)", interval_seconds or 60)
    stop = asyncio.Event()
    try:
        await stop.wait()
    finally:
        scheduler.shutdown(wait=False)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()

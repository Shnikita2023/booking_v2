"""Report service: thin wrapper over repository aggregations (step 9)."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from booking.repositories.reports import ReportRepository
from booking.schemas.report import (
    AuditStatsReport,
    OccupancyReport,
    RevenueByDateReport,
    RevenueReport,
    SalesReport,
    TopClientReport,
)


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ReportRepository(session)

    async def revenue_by_event(
        self,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[RevenueReport]:
        rows = await self._repo.revenue_by_event(from_date=from_date, to_date=to_date)
        return [RevenueReport(**row) for row in rows]

    async def revenue_by_date(
        self,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[RevenueByDateReport]:
        rows = await self._repo.revenue_by_date(from_date=from_date, to_date=to_date)
        return [RevenueByDateReport(**row) for row in rows]

    async def sales_by_status(
        self,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[SalesReport]:
        rows = await self._repo.sales_by_status(from_date=from_date, to_date=to_date)
        return [SalesReport(**row) for row in rows]

    async def occupancy(self) -> list[OccupancyReport]:
        rows = await self._repo.occupancy()
        return [OccupancyReport(**row) for row in rows]

    async def top_clients(
        self, *, limit: int = 10, offset: int = 0
    ) -> list[TopClientReport]:
        rows = await self._repo.top_clients(limit=limit, offset=offset)
        return [TopClientReport(**row) for row in rows]

    async def audit_stats(
        self,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[AuditStatsReport]:
        rows = await self._repo.audit_stats(from_date=from_date, to_date=to_date)
        return [AuditStatsReport(**row) for row in rows]

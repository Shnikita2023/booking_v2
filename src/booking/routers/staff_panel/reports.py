"""Staff reports endpoints: revenue, sales, occupancy, clients, audit (S-6)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from booking.core.deps import ReportServiceDep, require_role
from booking.core.dto import Principal
from booking.models.users import RoleCode
from booking.schemas.report import (
    AuditStatsReport,
    OccupancyReport,
    RevenueByDateReport,
    RevenueReport,
    SalesReport,
    TopClientReport,
)

AdminManager = Annotated[Principal, Depends(require_role(RoleCode.ADMIN, RoleCode.MANAGER))]

router = APIRouter(prefix="/api/v1/staff/reports", tags=["staff-reports"])


@router.get(
    "/revenue",
    summary="Revenue by event",
    description="Aggregated revenue grouped by event. Filter by date range.",
    response_model=list[RevenueReport],
)
async def revenue_by_event(
    _principal: AdminManager,
    service: ReportServiceDep,
    from_date: Annotated[datetime | None, Query(description="Start date (ISO 8601)")] = None,
    to_date: Annotated[datetime | None, Query(description="End date (ISO 8601)")] = None,
) -> list[RevenueReport]:
    return await service.revenue_by_event(from_date=from_date, to_date=to_date)


@router.get(
    "/revenue-by-date",
    summary="Revenue by day",
    description="Daily revenue aggregation. Filter by date range.",
    response_model=list[RevenueByDateReport],
)
async def revenue_by_date(
    _principal: AdminManager,
    service: ReportServiceDep,
    from_date: Annotated[datetime | None, Query(description="Start date (ISO 8601)")] = None,
    to_date: Annotated[datetime | None, Query(description="End date (ISO 8601)")] = None,
) -> list[RevenueByDateReport]:
    return await service.revenue_by_date(from_date=from_date, to_date=to_date)


@router.get(
    "/sales",
    summary="Sales by order status",
    description="Order count and total amount grouped by status. Filter by date range.",
    response_model=list[SalesReport],
)
async def sales_by_status(
    _principal: AdminManager,
    service: ReportServiceDep,
    from_date: Annotated[datetime | None, Query(description="Start date (ISO 8601)")] = None,
    to_date: Annotated[datetime | None, Query(description="End date (ISO 8601)")] = None,
) -> list[SalesReport]:
    return await service.sales_by_status(from_date=from_date, to_date=to_date)


@router.get(
    "/occupancy",
    summary="Event occupancy",
    description="Ticket occupancy per event: sold vs quota with percentage.",
    response_model=list[OccupancyReport],
)
async def occupancy(
    _principal: AdminManager,
    service: ReportServiceDep,
) -> list[OccupancyReport]:
    return await service.occupancy()


@router.get(
    "/top-clients",
    summary="Top clients by spending",
    description="Clients ranked by total order amount (paid orders only).",
    response_model=list[TopClientReport],
)
async def top_clients(
    _principal: AdminManager,
    service: ReportServiceDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TopClientReport]:
    return await service.top_clients(limit=limit, offset=offset)


@router.get(
    "/audit-stats",
    summary="Audit log statistics",
    description="Audit action counts grouped by action and actor role. Filter by date range.",
    response_model=list[AuditStatsReport],
)
async def audit_stats(
    _principal: AdminManager,
    service: ReportServiceDep,
    from_date: Annotated[datetime | None, Query(description="Start date (ISO 8601)")] = None,
    to_date: Annotated[datetime | None, Query(description="End date (ISO 8601)")] = None,
) -> list[AuditStatsReport]:
    return await service.audit_stats(from_date=from_date, to_date=to_date)

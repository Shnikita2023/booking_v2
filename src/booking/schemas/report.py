"""Report response schemas (step 9)."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ReportQuery(BaseModel):
    """Common query parameters for date-filtered reports."""

    from_date: datetime | None = Field(default=None, description="Start date (ISO 8601)")
    to_date: datetime | None = Field(default=None, description="End date (ISO 8601)")


class PaginationQuery(BaseModel):
    """Common query parameters for paginated reports."""

    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class RevenueReport(BaseModel):
    """Revenue grouped by event."""

    event_id: uuid.UUID
    event_title: str
    event_starts_at: datetime
    total_revenue: Decimal
    payment_count: int


class RevenueByDateReport(BaseModel):
    """Revenue grouped by day."""

    date: datetime
    total_revenue: Decimal
    payment_count: int


class SalesReport(BaseModel):
    """Order count and total by status."""

    status: str
    order_count: int
    total_amount: Decimal


class OccupancyReport(BaseModel):
    """Ticket occupancy per event."""

    event_id: uuid.UUID
    event_title: str
    event_starts_at: datetime
    total_quota: int
    total_sold: int
    occupancy_pct: Decimal


class TopClientReport(BaseModel):
    """Top clients by total spending."""

    client_id: uuid.UUID
    full_name: str | None
    email: str
    total_orders: int
    total_spent: Decimal


class AuditStatsReport(BaseModel):
    """Audit log action counts grouped by action and role."""

    action: str
    actor_role: str | None
    count: int

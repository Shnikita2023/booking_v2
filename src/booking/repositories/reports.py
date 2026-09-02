"""Report repository: read-only SQL aggregations (step 9)."""

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import Numeric, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from booking.models.audit import AuditLog
from booking.models.clients import Client
from booking.models.events import Event, TicketType
from booking.models.orders import Order, OrderStatus, Payment, PaymentStatus


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def revenue_by_event(
        self,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> Sequence[dict[str, Any]]:
        stmt = (
            select(
                Event.id.label("event_id"),
                Event.title.label("event_title"),
                Event.starts_at.label("event_starts_at"),
                func.sum(Payment.amount).label("total_revenue"),
                func.count(Payment.id).label("payment_count"),
            )
            .join(Order, Order.id == Payment.order_id)
            .join(Event, Event.id == Order.event_id)
            .where(
                Payment.status == PaymentStatus.SUCCEEDED,
                Order.deleted_at.is_(None),
            )
        )
        if from_date is not None:
            stmt = stmt.where(Payment.paid_at >= from_date)
        if to_date is not None:
            stmt = stmt.where(Payment.paid_at <= to_date)
        stmt = (
            stmt.group_by(Event.id, Event.title, Event.starts_at)
            .order_by(func.sum(Payment.amount).desc())
        )
        result = await self._session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def revenue_by_date(
        self,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> Sequence[dict[str, Any]]:
        date_col = func.date_trunc("day", Payment.paid_at).label("date")
        stmt = (
            select(
                date_col,
                func.sum(Payment.amount).label("total_revenue"),
                func.count(Payment.id).label("payment_count"),
            )
            .where(
                Payment.status == PaymentStatus.SUCCEEDED,
                Payment.paid_at.is_not(None),
            )
        )
        if from_date is not None:
            stmt = stmt.where(Payment.paid_at >= from_date)
        if to_date is not None:
            stmt = stmt.where(Payment.paid_at <= to_date)
        stmt = stmt.group_by(date_col).order_by(date_col)
        result = await self._session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def sales_by_status(
        self,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> Sequence[dict[str, Any]]:
        stmt = select(
            Order.status.label("status"),
            func.count(Order.id).label("order_count"),
            func.sum(Order.total_amount).label("total_amount"),
        ).where(Order.deleted_at.is_(None))
        if from_date is not None:
            stmt = stmt.where(Order.created_at >= from_date)
        if to_date is not None:
            stmt = stmt.where(Order.created_at <= to_date)
        stmt = stmt.group_by(Order.status)
        result = await self._session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def occupancy(self) -> Sequence[dict[str, Any]]:
        stmt = (
            select(
                Event.id.label("event_id"),
                Event.title.label("event_title"),
                Event.starts_at.label("event_starts_at"),
                func.sum(TicketType.quota).label("total_quota"),
                func.sum(TicketType.sold).label("total_sold"),
                case(
                    (
                        func.sum(TicketType.quota) > 0,
                        func.round(
                            func.cast(func.sum(TicketType.sold), Numeric)
                            / func.cast(func.sum(TicketType.quota), Numeric)
                            * 100,
                            1,
                        ),
                    ),
                    else_=0,
                ).label("occupancy_pct"),
            )
            .join(TicketType, TicketType.event_id == Event.id)
            .where(Event.deleted_at.is_(None), TicketType.deleted_at.is_(None))
            .group_by(Event.id, Event.title, Event.starts_at)
            .order_by(Event.starts_at)
        )
        result = await self._session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def top_clients(
        self, *, limit: int = 10, offset: int = 0
    ) -> Sequence[dict[str, Any]]:
        stmt = (
            select(
                Client.id.label("client_id"),
                Client.full_name.label("full_name"),
                Client.email.label("email"),
                func.count(Order.id).label("total_orders"),
                func.sum(Order.total_amount).label("total_spent"),
            )
            .join(Order, Order.client_id == Client.id)
            .where(
                Order.status == OrderStatus.PAID,
                Order.deleted_at.is_(None),
                Client.deleted_at.is_(None),
            )
            .group_by(Client.id, Client.full_name, Client.email)
            .order_by(func.sum(Order.total_amount).desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def audit_stats(
        self,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> Sequence[dict[str, Any]]:
        stmt = select(
            AuditLog.action.label("action"),
            AuditLog.actor_role.label("actor_role"),
            func.count(AuditLog.id).label("count"),
        )
        if from_date is not None:
            stmt = stmt.where(AuditLog.created_at >= from_date)
        if to_date is not None:
            stmt = stmt.where(AuditLog.created_at <= to_date)
        stmt = (
            stmt.group_by(AuditLog.action, AuditLog.actor_role)
            .order_by(func.count(AuditLog.id).desc())
        )
        result = await self._session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

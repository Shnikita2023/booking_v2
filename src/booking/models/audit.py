"""Append-only audit journal of system and client actions (D-2, D-3, S-7)."""

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from booking.models.base import Base, UUIDPkMixin
from booking.models.clients import UserType
from booking.models.events import enum_values
from booking.models.users import RoleCode


class AuditAction(enum.StrEnum):
    EVENT_CREATE = "event_create"
    EVENT_UPDATE = "event_update"
    EVENT_PUBLISH = "event_publish"
    EVENT_HIDE = "event_hide"
    EVENT_CANCEL = "event_cancel"
    EVENT_COMPLETE = "event_complete"
    EVENT_CLONE = "event_clone"
    EVENT_PAUSE = "event_pause"
    EVENT_RESUME = "event_resume"
    EVENT_MOVE = "event_move"
    TICKET_TYPE_CREATE = "ticket_type_create"
    TICKET_TYPE_UPDATE = "ticket_type_update"
    TICKET_TYPE_DELETE = "ticket_type_delete"
    CLIENT_CREATE = "client_create"
    CLIENT_UPDATE = "client_update"
    CLIENT_RESET_PASSWORD = "client_reset_password"
    CLIENT_BLOCK = "client_block"
    CLIENT_UNBLOCK = "client_unblock"
    CLIENT_DELETE = "client_delete"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_RESET_PASSWORD = "user_reset_password"
    USER_BLOCK = "user_block"
    USER_UNBLOCK = "user_unblock"
    USER_DELETE = "user_delete"
    SETTINGS_SET = "settings_set"
    ORDER_RESERVE = "order_reserve"
    ORDER_CONFIRM = "order_confirm"
    ORDER_CANCEL = "order_cancel"
    ORDER_CLEANUP = "order_cleanup"
    AUTH_REGISTER = "auth_register"
    AUTH_LOGIN_OK = "auth_login_ok"
    AUTH_LOGIN_FAIL = "auth_login_fail"
    AUTH_LOGOUT = "auth_logout"
    PAYMENT_CREATED = "payment_created"
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_REFUNDED = "payment_refunded"
    CASHIER_SALE = "cashier_sale"


def _enum(enum_cls: type[enum.Enum], length: int) -> Enum:
    return Enum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=enum_values,
    )


class AuditLog(UUIDPkMixin, Base):
    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_entity", "entity_type", "entity_id"),)

    actor_type: Mapped[UserType | None] = mapped_column(String(16), default=None, index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), default=None, index=True)
    actor_role: Mapped[RoleCode | None] = mapped_column(_enum(RoleCode, 32), default=None)
    action: Mapped[AuditAction] = mapped_column(_enum(AuditAction, 32), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(), default=None)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )

"""Discount repository."""

from booking.models.discounts import Discount
from booking.repositories.base import BaseRepository


class DiscountRepository(BaseRepository[Discount]):
    model = Discount

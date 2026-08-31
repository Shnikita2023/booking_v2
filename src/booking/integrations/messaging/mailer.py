"""Email sending abstraction (D-8)."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class EmailMessage:
    to: str
    subject: str
    body: str
    template: str


class Mailer(Protocol):
    async def send(self, *, to: str, subject: str, body: str, template: str) -> EmailMessage: ...

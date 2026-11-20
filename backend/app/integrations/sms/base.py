"""The interface every SMS adapter implements."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class SmsResult:
    ok: bool
    ref: str | None = None
    error: str | None = None


class SmsSender(Protocol):
    name: str

    def send(self, phone_number: str, text: str) -> SmsResult: ...

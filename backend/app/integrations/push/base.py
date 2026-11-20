"""The interface every push adapter implements."""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class PushMessage:
    title: str
    body: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class PushResult:
    """Outcome of sending one message to one user's devices."""

    delivered_refs: list[str] = field(default_factory=list)  # one per accepted device
    invalid_tokens: list[str] = field(default_factory=list)  # app uninstalled: delete these
    error: str | None = None  # set when nothing was accepted

    @property
    def ok(self) -> bool:
        return bool(self.delivered_refs)


class PushSender(Protocol):
    name: str

    def send(self, tokens: list[str], message: PushMessage) -> PushResult: ...

"""The interface for storing report photos (decision D6)."""

from typing import Protocol


class PhotoStorage(Protocol):
    name: str

    def save(self, key: str, data: bytes) -> None: ...

    def read(self, key: str) -> bytes | None: ...

    def delete(self, key: str) -> None: ...

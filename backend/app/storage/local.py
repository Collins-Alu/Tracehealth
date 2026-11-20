"""Photos on the server's own disk (development and single-server pilots)."""

from pathlib import Path


class LocalPhotoStorage:
    name = "local"

    def __init__(self, root: Path):
        self._root = root

    def _path(self, key: str) -> Path:
        root = self._root.resolve()
        path = (root / key).resolve()
        if root not in path.parents:  # blocks "../../etc/passwd" style keys
            raise ValueError("invalid storage key")
        return path

    def save(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes | None:
        try:
            path = self._path(key)
        except ValueError:
            return None
        return path.read_bytes() if path.is_file() else None

    def delete(self, key: str) -> None:
        try:
            self._path(key).unlink(missing_ok=True)
        except ValueError:
            pass

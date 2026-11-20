"""Photos stored in PostgreSQL (see app/models/stored_photo.py)."""

from collections.abc import Callable

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import StoredPhoto


class DatabasePhotoStorage:
    name = "database"

    def __init__(self, session_factory: Callable[[], Session]):
        # Its own short sessions: a photo is saved before the report row exists
        self._session_factory = session_factory

    def save(self, key: str, data: bytes) -> None:
        with self._session_factory() as db:
            db.execute(
                insert(StoredPhoto)
                .values(key=key, data=data)
                .on_conflict_do_update(index_elements=["key"], set_={"data": data})
            )
            db.commit()

    def read(self, key: str) -> bytes | None:
        with self._session_factory() as db:
            return db.scalar(select(StoredPhoto.data).where(StoredPhoto.key == key))

    def delete(self, key: str) -> None:
        with self._session_factory() as db:
            db.execute(delete(StoredPhoto).where(StoredPhoto.key == key))
            db.commit()

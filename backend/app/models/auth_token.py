import uuid 
from datetime import datetime

from sqlalchemy import Datetime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.om import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

class RefreshenToken(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "refreshe_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
            UUID(asuuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
            )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True) , nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    

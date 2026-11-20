"""
In-app inbox and push-token registration.

GET    /notifications              my inbox (newest first) + unread count
POST   /notifications/{id}/read    mark one as read
POST   /notifications/read-all     mark all as read
POST   /devices/push-token         register this phone for push notifications
DELETE /devices/push-token         unregister (on logout)
"""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import DevicePushToken, Notification, User
from app.schemas.notification import (
    NotificationOut,
    NotificationPage,
    PushTokenDelete,
    PushTokenIn,
)
from app.services.notification_service import inbox_query

router = APIRouter(tags=["Notifications"])


@router.get("/notifications", response_model=NotificationPage, summary="My notifications")
def my_notifications(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationPage:
    base = inbox_query(user.id)
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    unread = db.scalar(
        select(func.count()).select_from(base.where(Notification.read_at.is_(None)).subquery())
    )
    items = db.scalars(
        base.order_by(Notification.created_at.desc(), Notification.id).limit(limit).offset(offset)
    ).all()
    return NotificationPage(
        items=[NotificationOut.model_validate(n) for n in items],
        total=total,
        unread=unread,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/notifications/{notification_id}/read", status_code=204, summary="Mark a notification read"
)
def mark_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    n = db.scalar(inbox_query(user.id).where(Notification.id == notification_id))
    if n is None:
        raise HTTPException(404, "Notification not found.")
    if n.read_at is None:
        n.read_at = datetime.now(UTC)
        db.commit()
    return Response(status_code=204)


@router.post("/notifications/read-all", status_code=204, summary="Mark all notifications read")
def mark_all_read(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    db.execute(
        update(Notification)
        .where(Notification.id.in_(inbox_query(user.id).with_only_columns(Notification.id)))
        .where(Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    db.commit()
    return Response(status_code=204)


@router.post("/devices/push-token", status_code=204, summary="Register this phone for push")
def register_push_token(
    body: PushTokenIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    # Upsert: the same phone used by a different account moves to that account
    stmt = insert(DevicePushToken).values(
        id=uuid.uuid4(), user_id=user.id, token=body.token, platform=body.platform
    )
    db.execute(
        stmt.on_conflict_do_update(
            index_elements=[DevicePushToken.token],
            set_={"user_id": user.id, "platform": body.platform, "last_seen_at": func.now()},
        )
    )
    db.commit()
    return Response(status_code=204)


@router.delete("/devices/push-token", status_code=204, summary="Stop push to this phone")
def unregister_push_token(
    body: PushTokenDelete, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Response:
    db.execute(
        delete(DevicePushToken).where(
            DevicePushToken.token == body.token, DevicePushToken.user_id == user.id
        )
    )
    db.commit()
    return Response(status_code=204)

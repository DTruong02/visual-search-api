from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Image, ImageStatus


def create_image(
    db: Session,
    *,
    s3_bucket: str,
    s3_key: str,
    content_type: str,
    bytes: int,
    sha256: str,
) -> Image:
    img = Image(
        s3_bucket=s3_bucket,
        s3_key=s3_key,
        content_type=content_type,
        bytes=bytes,
        sha256=sha256,
        status=ImageStatus.processing,
        error=None,
    )
    db.add(img)
    db.commit()
    db.refresh(img)
    return img


def get_image(db: Session, image_id: uuid.UUID) -> Image | None:
    return db.get(Image, image_id)


def get_images_by_ids(db: Session, ids: list[uuid.UUID]) -> list[Image]:
    if not ids:
        return []
    stmt = select(Image).where(Image.id.in_(ids))
    return list(db.execute(stmt).scalars().all())


def list_ready_images(db: Session, limit: int = 1000) -> list[Image]:
    stmt = select(Image).where(Image.status == ImageStatus.ready).limit(limit)
    return list(db.execute(stmt).scalars().all())


def set_image_status(db: Session, image_id: uuid.UUID, status: ImageStatus, error: str | None = None) -> None:
    img = db.get(Image, image_id)
    if img is None:
        return
    img.status = status
    img.error = error
    db.add(img)
    db.commit()


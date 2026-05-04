from __future__ import annotations

import io
import uuid

from celery import shared_task
from PIL import Image

from app.db import crud
from app.db.models import ImageStatus
from app.db.session import SessionLocal
from app.ml.clip import embed_image
from app.storage.s3 import get_bytes
from app.vector.qdrant import ensure_collection, upsert_image_vector


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def embed_image_task(self, image_id: str) -> None:
    image_uuid = uuid.UUID(image_id)
    db = SessionLocal()
    try:
        img = crud.get_image(db, image_uuid)
        if img is None:
            return

        ensure_collection()
        raw = get_bytes(bucket=img.s3_bucket, key=img.s3_key)
        pil = Image.open(io.BytesIO(raw)).convert("RGB")
        vec = embed_image(pil)
        upsert_image_vector(image_id=img.id, sha256=img.sha256, vector=vec)
        crud.set_image_status(db, img.id, ImageStatus.ready, error=None)
    except Exception as e:
        crud.set_image_status(db, image_uuid, ImageStatus.failed, error=str(e))
        raise
    finally:
        db.close()


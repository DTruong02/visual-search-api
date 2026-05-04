from __future__ import annotations

import io
import os
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.schemas import (
    DedupeRequest,
    DedupeResponse,
    ImageOut,
    SearchHit,
    SearchResponse,
    TextSearchRequest,
    UploadResponse,
)
from app.db import crud
from app.db.models import ImageStatus
from app.db.session import get_db
from app.ml.clip import embed_image, embed_text
from app.storage.s3 import compute_sha256_and_bytes, make_object_key, presign_get_url, put_bytes
from app.vector.qdrant import search
from app.workers.tasks import embed_image_task
from PIL import Image


router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


@router.post("/images", response_model=UploadResponse)
def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="file must be an image")

    data = file.file.read()
    sha256, size_bytes = compute_sha256_and_bytes(data)
    ext = os.path.splitext(file.filename or "")[1].lstrip(".") or None

    from app.core.config import get_settings
    from app.storage.s3 import ensure_bucket_exists

    s = get_settings()
    ensure_bucket_exists(s.s3_bucket)
    key = make_object_key(sha256, ext=ext)
    put_bytes(bucket=s.s3_bucket, key=key, content_type=file.content_type, data=data)

    img = crud.create_image(
        db,
        s3_bucket=s.s3_bucket,
        s3_key=key,
        content_type=file.content_type,
        bytes=size_bytes,
        sha256=sha256,
    )

    embed_image_task.delay(str(img.id))
    return UploadResponse(image_id=img.id, status=img.status.value)


@router.get("/images/{image_id}", response_model=ImageOut)
def get_image(image_id: UUID, db: Session = Depends(get_db)):
    img = crud.get_image(db, image_id)
    if img is None:
        raise HTTPException(status_code=404, detail="not found")

    url = presign_get_url(bucket=img.s3_bucket, key=img.s3_key) if img.status == ImageStatus.ready else None
    return ImageOut(
        id=img.id,
        status=img.status.value,
        sha256=img.sha256,
        bytes=img.bytes,
        content_type=img.content_type,
        created_at=img.created_at,
        updated_at=img.updated_at,
        url=url,
        error=img.error,
    )


@router.post("/search/text", response_model=SearchResponse)
def search_text(req: TextSearchRequest, db: Session = Depends(get_db)):
    vec = embed_text(req.query)
    hits = search(vector=vec, top_k=req.top_k)
    imgs = {img.id: img for img in crud.get_images_by_ids(db, [h[0] for h in hits])}
    out: list[SearchHit] = []
    for image_id, score in hits:
        img = imgs.get(image_id)
        if img is None or img.status != ImageStatus.ready:
            continue
        out.append(SearchHit(image_id=image_id, score=score, url=presign_get_url(bucket=img.s3_bucket, key=img.s3_key)))
    return SearchResponse(hits=out)


@router.post("/search/image", response_model=SearchResponse)
def search_image(top_k: int = 5, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="file must be an image")
    data = file.file.read()
    pil = Image.open(io.BytesIO(data)).convert("RGB")
    vec = embed_image(pil)
    hits = search(vector=vec, top_k=top_k)
    imgs = {img.id: img for img in crud.get_images_by_ids(db, [h[0] for h in hits])}
    out: list[SearchHit] = []
    for image_id, score in hits:
        img = imgs.get(image_id)
        if img is None or img.status != ImageStatus.ready:
            continue
        out.append(SearchHit(image_id=image_id, score=score, url=presign_get_url(bucket=img.s3_bucket, key=img.s3_key)))
    return SearchResponse(hits=out)


@router.post("/dedupe", response_model=DedupeResponse)
def dedupe(req: DedupeRequest, db: Session = Depends(get_db)):
    # Simple pair generation: for each image, query neighbors and emit pairs above threshold.
    ready = crud.list_ready_images(db, limit=req.limit_images)
    ready_map = {img.id: img for img in ready}

    pairs = []
    seen = set()
    for img in ready:
        # Use Qdrant similarity: query by the stored vector by doing a textless trick is non-trivial without scroll.
        # For MVP, we approximate by querying neighbors using the image itself (download + embed).
        from app.storage.s3 import get_bytes
        raw = get_bytes(bucket=img.s3_bucket, key=img.s3_key)
        pil = Image.open(io.BytesIO(raw)).convert("RGB")
        vec = embed_image(pil)
        hits = search(vector=vec, top_k=req.top_k)
        for other_id, score in hits:
            if other_id == img.id:
                continue
            if other_id not in ready_map:
                continue
            if score < req.threshold:
                continue
            a, b = sorted([img.id, other_id])
            key = (a, b)
            if key in seen:
                continue
            seen.add(key)
            pairs.append({"a": a, "b": b, "score": float(score)})

    return DedupeResponse(pairs=pairs)


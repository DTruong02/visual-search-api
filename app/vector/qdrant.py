from __future__ import annotations

import uuid

from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from app.core.config import get_settings
from app.ml.clip import embedding_dim


def get_qdrant() -> QdrantClient:
    s = get_settings()
    return QdrantClient(url=s.qdrant_url)


def ensure_collection() -> None:
    s = get_settings()
    client = get_qdrant()
    collections = client.get_collections().collections
    if any(c.name == s.qdrant_collection for c in collections):
        return

    client.create_collection(
        collection_name=s.qdrant_collection,
        vectors_config=qm.VectorParams(size=embedding_dim(), distance=qm.Distance.COSINE),
    )


def upsert_image_vector(*, image_id: uuid.UUID, sha256: str, vector: list[float]) -> None:
    s = get_settings()
    client = get_qdrant()
    client.upsert(
        collection_name=s.qdrant_collection,
        points=[
            qm.PointStruct(
                id=str(image_id),
                vector=vector,
                payload={"image_id": str(image_id), "sha256": sha256},
            )
        ],
    )


def search(*, vector: list[float], top_k: int) -> list[tuple[uuid.UUID, float]]:
    s = get_settings()
    client = get_qdrant()
    hits = client.search(collection_name=s.qdrant_collection, query_vector=vector, limit=top_k)
    out: list[tuple[uuid.UUID, float]] = []
    for h in hits:
        try:
            out.append((uuid.UUID(str(h.id)), float(h.score)))
        except Exception:
            continue
    return out


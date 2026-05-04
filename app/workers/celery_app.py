from __future__ import annotations

from celery import Celery

from app.core.config import get_settings


def _make_celery() -> Celery:
    s = get_settings()
    return Celery(
        "visual_search",
        broker=s.celery_broker_url,
        backend=s.celery_result_backend,
        include=["app.workers.tasks"],
    )


celery_app = _make_celery()


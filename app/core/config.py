from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"

    database_url: str

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "image_embeddings"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"
    s3_bucket: str = "images"
    s3_region: str = "us-east-1"
    s3_presign_expires_seconds: int = 3600

    model_name: str = "ViT-B-32"
    model_pretrained: str = "laion2b_s34b_b79k"
    embedding_device: str = "cpu"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
        if _settings.celery_broker_url is None:
            _settings.celery_broker_url = _settings.redis_url
        if _settings.celery_result_backend is None:
            _settings.celery_result_backend = _settings.redis_url
    return _settings


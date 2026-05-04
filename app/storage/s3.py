from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings


@dataclass(frozen=True)
class UploadResult:
    bucket: str
    key: str
    sha256: str
    size_bytes: int


def _client():
    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url,
        aws_access_key_id=s.s3_access_key_id,
        aws_secret_access_key=s.s3_secret_access_key,
        region_name=s.s3_region,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket_exists(bucket: str) -> None:
    c = _client()
    try:
        c.head_bucket(Bucket=bucket)
        return
    except ClientError:
        pass
    c.create_bucket(Bucket=bucket)


def compute_sha256_and_bytes(data: bytes) -> tuple[str, int]:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest(), len(data)


def put_bytes(*, bucket: str, key: str, content_type: str, data: bytes) -> None:
    c = _client()
    c.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)


def get_bytes(*, bucket: str, key: str) -> bytes:
    c = _client()
    obj = c.get_object(Bucket=bucket, Key=key)
    body = obj["Body"].read()
    return body


def presign_get_url(*, bucket: str, key: str) -> str:
    s = get_settings()
    c = _client()
    return c.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=s.s3_presign_expires_seconds,
    )


def make_object_key(sha256: str, *, ext: str | None) -> str:
    # Spread keys across prefixes to keep listings efficient.
    prefix1 = sha256[:2]
    prefix2 = sha256[2:4]
    if ext:
        ext = ext.lstrip(".")
        return f"{prefix1}/{prefix2}/{sha256}.{ext}"
    return f"{prefix1}/{prefix2}/{sha256}"


def bytes_to_fileobj(data: bytes) -> io.BytesIO:
    return io.BytesIO(data)


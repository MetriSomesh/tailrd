"""File storage abstraction: local filesystem (dev) or S3 (production).

All DOCX artifacts go through this interface. Callers never know which backend
is active.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings
from app.core.errors import StorageError
from app.core.logging import get_logger

log = get_logger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    async def upload(
        self, data: bytes, key: str, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload bytes. Returns the storage key."""
        ...

    @abstractmethod
    async def get_download_url(self, key: str) -> str:
        """Get a URL to download the file. For local, returns a file:// or API path."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a file by key."""
        ...


class LocalStorageBackend(StorageBackend):
    """Writes to the local filesystem. For development only."""

    def __init__(self) -> None:
        self._root = Path(settings.STORAGE_LOCAL_DIR)
        self._root.mkdir(parents=True, exist_ok=True)

    async def upload(
        self, data: bytes, key: str, content_type: str = "application/octet-stream"
    ) -> str:
        path = self._root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        log.info("storage_upload_local", key=key, size=len(data))
        return key

    async def get_download_url(self, key: str) -> str:
        # In dev, the download endpoint serves files directly.
        return f"/api/v1/runs/download/{key}"

    async def delete(self, key: str) -> None:
        path = self._root / key
        if path.exists():
            path.unlink()
            log.info("storage_delete_local", key=key)

    def read(self, key: str) -> bytes | None:
        """Sync read for local dev (used by the download endpoint)."""
        path = self._root / key
        if path.exists():
            return path.read_bytes()
        return None


class S3StorageBackend(StorageBackend):
    """AWS S3 with presigned URLs for download."""

    def __init__(self) -> None:
        import boto3

        self._client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        self._bucket = settings.S3_BUCKET

    async def upload(
        self, data: bytes, key: str, content_type: str = "application/octet-stream"
    ) -> str:
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
            log.info("storage_upload_s3", key=key, size=len(data))
            return key
        except Exception as exc:
            log.error("storage_upload_s3_failed", key=key, error=str(exc)[:300])
            raise StorageError("Failed to upload file to storage.") from exc

    async def get_download_url(self, key: str) -> str:
        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=settings.PRESIGNED_URL_TTL_SECONDS,
            )
        except Exception as exc:
            log.error("storage_presign_failed", key=key, error=str(exc)[:300])
            raise StorageError("Failed to generate download link.") from exc

    async def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            log.info("storage_delete_s3", key=key)
        except Exception as exc:
            log.warning("storage_delete_s3_failed", key=key, error=str(exc)[:200])


def get_storage() -> StorageBackend:
    if settings.STORAGE_BACKEND == "s3":
        return S3StorageBackend()
    return LocalStorageBackend()


def generate_storage_key(user_id: str, run_id: str, filename: str) -> str:
    """Generate a unique storage key for a DOCX artifact."""
    return f"resumes/{user_id}/{run_id}/{filename}"

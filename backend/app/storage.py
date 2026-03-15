# backend/app/storage.py

"""
Storage Abstraction - Derekh Food API
Local filesystem (dev) ou Cloudflare R2/S3 (producao)
"""

import os
import uuid
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger("superfood.storage")


class StorageBackend(ABC):
    """Interface abstrata para armazenamento de arquivos"""

    @abstractmethod
    def upload(self, file_bytes: bytes, key: str, content_type: str = "image/webp") -> str:
        """Upload arquivo e retorna URL publica"""
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Remove arquivo pelo key"""
        ...

    @abstractmethod
    def get_url(self, key: str) -> str:
        """Retorna URL publica do arquivo"""
        ...


class LocalStorageBackend(StorageBackend):
    """Armazenamento local em filesystem (desenvolvimento)"""

    def __init__(self, upload_dir: str = "backend/static/uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def upload(self, file_bytes: bytes, key: str, content_type: str = "image/webp") -> str:
        filepath = self.upload_dir / key
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_bytes(file_bytes)
        logger.info(f"Upload local: {key}")
        return f"/static/uploads/{key}"

    def delete(self, key: str) -> bool:
        filepath = self.upload_dir / key
        if filepath.exists():
            filepath.unlink()
            logger.info(f"Deletado local: {key}")
            return True
        return False

    def get_url(self, key: str) -> str:
        return f"/static/uploads/{key}"


class R2StorageBackend(StorageBackend):
    """Armazenamento em Cloudflare R2 (producao) - compativel S3"""

    def __init__(self):
        import boto3
        self.bucket_name = os.getenv("R2_BUCKET_NAME", "superfood-uploads")
        self.cdn_url = os.getenv("CDN_URL", "").rstrip("/")

        self.client = boto3.client(
            "s3",
            endpoint_url=os.getenv("R2_ENDPOINT"),
            aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
            region_name="auto",
        )
        logger.info(f"R2 Storage inicializado: bucket={self.bucket_name}")

    def upload(self, file_bytes: bytes, key: str, content_type: str = "image/webp") -> str:
        self.client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=file_bytes,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
        logger.info(f"Upload R2: {key}")
        return self.get_url(key)

    def delete(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Deletado R2: {key}")
            return True
        except Exception as e:
            logger.error(f"Erro ao deletar R2 {key}: {e}")
            return False

    def get_url(self, key: str) -> str:
        if self.cdn_url:
            return f"{self.cdn_url}/{key}"
        return f"https://{self.bucket_name}.r2.cloudflarestorage.com/{key}"


# Factory — singleton
_storage_instance: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """Retorna backend de storage baseado em STORAGE_BACKEND env var"""
    global _storage_instance
    if _storage_instance is None:
        backend = os.getenv("STORAGE_BACKEND", "local").lower()
        if backend == "r2":
            _storage_instance = R2StorageBackend()
        else:
            _storage_instance = LocalStorageBackend()
        logger.info(f"Storage backend: {backend}")
    return _storage_instance

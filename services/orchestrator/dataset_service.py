import hashlib
import logging
import os
import time
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional

from minio import Minio
from minio.error import S3Error
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(message)s")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minio123")
DATASETS_BUCKET = os.getenv("MINIO_BUCKET", "datasets")
UPLOAD_RETRIES = 3
RETRY_DELAY_SECONDS = 1


class DatasetRecord(BaseModel):
    dataset_id: int
    name: str
    path: str
    checksum: str
    format: str = "csv"


class DatasetRegistry:
    def __init__(self) -> None:
        self._records_by_checksum: Dict[str, DatasetRecord] = {}
        self._records_by_id: Dict[int, DatasetRecord] = {}
        self._next_id = 1

    def upsert(self, name: str, path: str, checksum: str) -> DatasetRecord:
        existing = self._records_by_checksum.get(checksum)
        if existing:
            return existing

        record = DatasetRecord(
            dataset_id=self._next_id,
            name=name,
            path=path,
            checksum=checksum,
        )
        self._records_by_checksum[checksum] = record
        self._records_by_id[self._next_id] = record
        self._next_id += 1
        return record

    def get(self, dataset_id: int) -> Optional[DatasetRecord]:
        return self._records_by_id.get(dataset_id)

    def reset(self) -> None:
        self._records_by_checksum.clear()
        self._records_by_id.clear()
        self._next_id = 1


class ObjectStorageClient:
    def __init__(self) -> None:
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )

    def ensure_bucket(self, bucket_name: str) -> None:
        if not self.client.bucket_exists(bucket_name):
            self.client.make_bucket(bucket_name)

    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        try:
            self.client.stat_object(bucket_name, object_name)
            return True
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                return False
            raise

    def upload_bytes(
        self,
        bucket_name: str,
        object_name: str,
        payload: bytes,
        content_type: str = "text/csv",
        retries: int = UPLOAD_RETRIES,
    ) -> str:
        self.ensure_bucket(bucket_name)

        if self.object_exists(bucket_name, object_name):
            logging.info("Dataset already exists in object storage: %s", object_name)
            return object_name

        for attempt in range(1, retries + 1):
            try:
                self.client.put_object(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    data=BytesIO(payload),
                    length=len(payload),
                    content_type=content_type,
                )
                return object_name
            except Exception:
                if attempt == retries:
                    raise
                logging.warning(
                    "Upload attempt %s/%s failed for %s, retrying...",
                    attempt,
                    retries,
                    object_name,
                )
                time.sleep(RETRY_DELAY_SECONDS * attempt)

        return object_name


def compute_checksum(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def build_object_name(filename: str, checksum: str) -> str:
    stem = Path(filename).stem or "dataset"
    return f"{stem}/{checksum}.csv"


dataset_registry = DatasetRegistry()
storage_client = ObjectStorageClient()


def register_uploaded_dataset(
    filename: str,
    payload: bytes,
    content_type: str,
    name: Optional[str] = None,
) -> DatasetRecord:
    dataset_name = name or Path(filename).stem
    checksum = compute_checksum(payload)
    object_name = build_object_name(filename, checksum)

    storage_path = storage_client.upload_bytes(
        bucket_name=DATASETS_BUCKET,
        object_name=object_name,
        payload=payload,
        content_type=content_type or "text/csv",
    )

    return dataset_registry.upsert(
        name=dataset_name,
        path=storage_path,
        checksum=checksum,
    )

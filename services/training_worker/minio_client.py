from minio import Minio
import logging
import os
import time

logging.basicConfig(level=logging.INFO)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minio123")
MODELS_BUCKET = os.getenv("MODELS_BUCKET", "models")
DATASETS_BUCKET = os.getenv("MINIO_BUCKET", "datasets")

logging.info(f"Connecting to MinIO at {MINIO_ENDPOINT}")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)

for i in range(3):
    try:
        buckets = minio_client.list_buckets()
        logging.info(f"Found buckets: {[b.name for b in buckets]}")
        break
    except Exception as e:
        logging.warning(f"MinIO connection attempt {i + 1} failed: {e}")
        time.sleep(2)


def download_dataset(dataset_name: str, file_path: str, bucket=None):
    if bucket is None:
        bucket = DATASETS_BUCKET
    for i in range(3):
        try:
            minio_client.fget_object(
                bucket_name=bucket, object_name=dataset_name, file_path=file_path
            )
            return
        except Exception as e:
            logging.warning(f"Download attempt {i + 1} failed: {e}")
            if i < 2:
                time.sleep(2)
            else:
                raise


def save_model_to_minio(local_model_path, model_name, model_version):
    object_path = f"{model_name}/{model_version}.joblib"

    file_path = os.path.join(local_model_path, "model.pkl")

    minio_client.fput_object(
        bucket_name=MODELS_BUCKET,
        object_name=object_path,
        file_path=file_path,
    )

    return object_path

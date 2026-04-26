from minio import Minio
import logging
import os
import time
import socket

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minio123")
MODELS_BUCKET = os.getenv("MODELS_BUCKET", "models")
DATASETS_BUCKET = os.getenv("MINIO_BUCKET", "datasets")

logger.info(
    f"Connecting to MinIO at {MINIO_ENDPOINT}", extra={"event": "minio_client_init"}
)

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)

for i in range(3):
    try:
        buckets = minio_client.list_buckets()
        logger.info(
            f"Found buckets: {[b.name for b in buckets]}",
            extra={"event": "minio_connection_success"},
        )
        break
    except Exception as e:
        logger.warning(
            f"MinIO connection attempt {i + 1} failed: {e}",
            extra={"event": "minio_connection_retry", "attempt": i + 1},
        )
        time.sleep(2)


def download_dataset(dataset_name: str, file_path: str, bucket=None):
    if bucket is None:
        bucket = DATASETS_BUCKET

    context = {"dataset_name": dataset_name, "bucket": bucket}
    for i in range(3):
        try:
            minio_client.fget_object(
                bucket_name=bucket, object_name=dataset_name, file_path=file_path
            )
            logger.info(
                "Dataset downloaded successfully",
                extra={"event": "dataset_download_success", **context},
            )
            return
        except Exception as e:
            logger.warning(
                f"Download attempt {i + 1} failed: {e}",
                extra={"event": "dataset_download_retry", "attempt": i + 1, **context},
            )
            if i < 2:
                time.sleep(2)
            else:
                logger.error(
                    "All download attempts failed",
                    extra={"event": "dataset_download_error", **context},
                )
                raise


def save_model_to_minio(local_model_path, model_name, model_version):
    object_path = f"{model_name}/{model_version}.joblib"
    context = {
        "model_name": model_name,
        "model_version": model_version,
        "object_path": object_path,
    }

    # Try different possible file names
    possible_files = ["model.pkl", "model.joblib", "model"]
    file_path = None
    for fname in possible_files:
        test_path = os.path.join(local_model_path, fname)
        if os.path.exists(test_path):
            file_path = test_path
            break

    if not file_path:
        # List what's in the directory
        files_in_dir = (
            os.listdir(local_model_path) if os.path.exists(local_model_path) else []
        )
        logger.error(
            "Model file not found",
            extra={
                "event": "model_file_missing",
                "found_files": files_in_dir,
                **context,
            },
        )
        raise FileNotFoundError(f"Model file not found in {local_model_path}")

    logger.info(
        "Saving model to MinIO",
        extra={"event": "minio_upload_start", "file_path": file_path, **context},
    )
    try:
        socket.setdefaulttimeout(10)

        minio_client.fput_object(
            bucket_name=MODELS_BUCKET,
            object_name=object_path,
            file_path=file_path,
        )
        logger.info(
            "Model saved to MinIO", extra={"event": "minio_upload_success", **context}
        )
    except Exception as e:
        logger.error(
            "Failed to save model",
            extra={"event": "minio_upload_error", "error": str(e), **context},
        )
        raise

    return object_path

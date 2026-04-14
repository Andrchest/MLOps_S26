from minio import Minio
import os

minio_user = os.getenv("MINIO_ROOT_USER", "minio")
minio_password = os.getenv("MINIO_ROOT_PASSWORD", "minio123")
minio_endpoint = "minio:9000"

# Initialize Minio Client
minio_client = Minio(
    minio_endpoint, access_key=minio_user, secret_key=minio_password, secure=False
)


def get_model_from_minio(model_name: str, model_version: str, bucket: str = "models"):
    """
    Synchronous helper to pull bytes from Minio.
    """
    object_name = f"{model_name}/{model_version}.joblib"
    response = minio_client.get_object(bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()

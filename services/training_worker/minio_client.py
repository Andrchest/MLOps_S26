from minio import Minio
import os

# Connection to MinIO
minio_client = Minio(
    "minio:9000", access_key="minio", secret_key="minio123", secure=False
)


def download_dataset(dataset_name: str, file_path: str, bucket="datasets"):
    minio_client.fget_object(
        bucket_name=bucket, object_name=dataset_name, file_path=file_path
    )


def save_model_to_minio(local_model_path, model_name, model_version):
    object_path = f"{model_name}/{model_version}.joblib"

    file_path = os.path.join(local_model_path, "model.pkl")

    minio_client.fput_object(
        bucket_name="models",
        object_name=object_path,
        file_path=file_path,
    )

    return object_path

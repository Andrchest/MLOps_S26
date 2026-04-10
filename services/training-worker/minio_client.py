from minio import Minio
from io import BytesIO
import joblib


minio_client = Minio(
    "minio:9000",
    access_key="minio",
    secret_key="minio123",
    secure=False
)


def download_dataset(dataset_name: str, file_path: str, bucket="datasets"):
    minio_client.fget_object(
        bucket_name=bucket,
        object_name=dataset_name,
        file_path=file_path
    )


def save_model_to_minio(model, model_name, model_version):
    buffer = BytesIO()
    joblib.dump(model, buffer)
    buffer.seek(0)

    path = f"{model_name}/{model_version}.joblib"

    minio_client.put_object(
        bucket_name="models",
        object_name=path,
        data=buffer,
        length=buffer.getbuffer().nbytes,
        content_type="application/octet-stream",
    )

    return path


def load_model_from_minio(object_name: str, bucket: str = "models"):
    import joblib

    response = minio_client.get_object(bucket, object_name)
    data = BytesIO(response.read())

    return joblib.load(data)

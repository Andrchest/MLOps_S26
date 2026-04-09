from minio import Minio
import json

minio_client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="1234",
    secure=False
)


def load_dataset(dataset_name: str, bucket: str = "datasets"):
    response = minio_client.get_object(bucket, dataset_name)
    data = response.read().decode("utf-8")
    return json.loads(data)

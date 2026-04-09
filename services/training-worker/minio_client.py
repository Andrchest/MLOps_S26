from minio import Minio
import json
import joblib
import io


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


def save_model_to_minio(model, model_name, model_version):
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    buffer.seek(0)

    object_name = f"{model_name}_{model_version}.joblib"

    minio_client.put_object(
        "models",
        object_name,
        buffer,
        length=len(buffer.getvalue())
    )

    return f"models/{object_name}"

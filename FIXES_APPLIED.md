# MLOps Platform - Fixes Applied

This document lists all changes made to get the MLOps platform working up to the training pipeline completion.

## Overview of Changes

All fixes were made in the `integration/week-2-backbone` branch, which merges:
- `main`
- `feature/training-worker`
- `feature/inference-service`
- `feature/inference-service-db`

---

## Fix 1: Database Tables Missing

**Problem:** Jobs table didn't exist, causing `UndefinedTableError`

**Solution:** Create the tables in the database:

```bash
# Run this on the postgres container:
docker exec -i mlops_s26-postgres-1 psql -U mlops -d mlops < migrations/tables_for_worker.sql
```

**SQL content** (`migrations/tables_for_worker.sql`):
```sql
CREATE TABLE IF NOT EXISTS jobs (
    job_id SERIAL PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    dataset_id INT NOT NULL,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS trained_models (
    job_id INT NOT NULL REFERENCES jobs(job_id),
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    model_path TEXT NOT NULL,
    metrics JSONB NOT NULL,
    parameters JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE (job_id, model_version),
    PRIMARY KEY (job_id, model_version)
);
```

---

## Fix 2: Case Sensitivity in Job Status

**Problem:** Worker looked for status `'Pending'` but orchestrator inserts `'pending'`

**File:** `services/training_worker/db.py`

**Before:**
```python
WHERE status = 'Pending'
SET status = 'Running'
```

**After:**
```python
WHERE status = 'pending'
SET status = 'running'
```

---

## Fix 3: MinIO Connection Retry Logic

**Problem:** MinIO connection fails at startup, no bucket visibility

**File:** `services/training_worker/minio_client.py`

**Complete replacement:**
```python
from minio import Minio
import logging
import os
import time

logging.basicConfig(level=logging.INFO)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "minio123")

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
        logging.warning(f"MinIO connection attempt {i+1} failed: {e}")
        time.sleep(2)


def download_dataset(dataset_name: str, file_path: str, bucket="datasets"):
    for i in range(3):
        try:
            minio_client.fget_object(
                bucket_name=bucket, object_name=dataset_name, file_path=file_path
            )
            return
        except Exception as e:
            logging.warning(f"Download attempt {i+1} failed: {e}")
            if i < 2:
                time.sleep(2)
            else:
                raise


def save_model_to_minio(local_model_path, model_name, model_version):
    object_path = f"{model_name}/{model_version}.joblib"

    file_path = os.path.join(local_model_path, "model.pkl")

    minio_client.fput_object(
        bucket_name="models",
        object_name=object_path,
        file_path=file_path,
    )

    return object_path
```

---

## Fix 4: Dataset File Extension

**Problem:** Pipeline expects `.csv` file but MinIO downloads without extension

**File:** `services/training_worker/worker.py`

**Add after download_dataset call:**
```python
# Rename downloaded file to .csv
csv_path = f"{data_path}.csv"
import shutil
shutil.move(data_path, csv_path)
```

Then update the subprocess call to use `csv_path` instead of `data_path`.

---

## Fix 5: Disable MLflow Security Middleware

**Problem:** MLflow rejects internal Docker network requests due to DNS rebinding protection (error 403)

**File:** `docker-compose.yml`

**Before:**
```yaml
mlflow:
    image: ghcr.io/mlflow/mlflow
    command: mlflow server --host 0.0.0.0 --port 5000
```

**After:**
```yaml
mlflow:
    image: ghcr.io/mlflow/mlflow
    command: mlflow server --host 0.0.0.0 --port 5000 --disable-security-middleware
```

---

## Fix 6: Add MLFLOW_TRACKING_URI to Training Worker

**File:** `docker-compose.yml`

**Add to training-worker service:**
```yaml
training-worker:
    build:
      context: .
      dockerfile: services/training_worker/Dockerfile
    env_file: .env
    environment:
      MLFLOW_TRACKING_URI: "http://mlflow:5000"
    depends_on:
      - postgres
      - mlflow
      - minio
```

---

## Fix 7: Add Logging to Training Worker

**File:** `services/training_worker/app.py`

**Add logging setup:**
```python
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(message)s')
```

**Update lifespan with logging:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("LIFESPAN: creating DB pool")
    db.db_pool = await asyncpg.create_pool(
        user=os.getenv("POSTGRES_USER", "mlops"),
        password=os.getenv("POSTGRES_PASSWORD", "mlops"),
        database=os.getenv("POSTGRES_DB", "mlops"),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=5432,
    )
    logging.info("LIFESPAN: DB pool created, starting worker")
    asyncio.create_task(worker_loop())
    logging.info("LIFESPAN: worker task started")
    yield
    logging.info("LIFESPAN: shutting down")
    await db.db_pool.close()
```

---

## Fix 8: Add /health Endpoint to Training Worker

**File:** `services/training_worker/app.py`

```python
@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## Fix 9: Create MinIO Buckets

**Run after container restart:**

```bash
docker exec mlops_s26-minio-1 mc mb minio/datasets
docker exec mlops_s26-minio-1 mc mb minio/models
```

---

## Fix 11: JSON Dumps for Metrics/Parameters

**Problem:** asyncpg throws error when inserting dict into JSONB column

**File:** `services/training_worker/db.py`

**Fix:**
```python
import json
# Use json.dumps() for metrics and parameters
metrics=json.dumps(metrics),
parameters=json.dumps(parameters),
```

---

## Fix 12: Logging + Error Handling in save_model_to_minio

**Problem:** Worker hangs at save_model_to_minio() with no error visibility

**File:** `services/training_worker/minio_client.py`

**Fix:** Added try/except + logging + file name detection
```python
def save_model_to_minio(local_model_path, model_name, model_version):
    import logging
    import os
    
    # Try different possible file names
    possible_files = ["model.pkl", "model.joblib", "model"]
    for fname in possible_files:
        test_path = os.path.join(local_model_path, fname)
        if os.path.exists(test_path):
            file_path = test_path
            break
    
    logging.info(f"Saving model to MinIO: {object_path}")
    try:
        minio_client.fput_object(...)
        logging.info(f"Model saved: {object_path}")
    except Exception as e:
        logging.error(f"Failed to save model: {e}")
        raise
```

---

## Summary - How to Run on Your Machine

### 1. Start containers:
```bash
cd MLOps_S26
docker compose up -d
```

### 2. Initialize database (ONE TIME only):
```bash
docker exec -i mlops_s26-postgres-1 psql -U mlops -d mlops < migrations/tables_for_worker.sql
```
**Note:** Database name is `mlops`, not `ml`!

### 5. Create MinIO buckets:
```bash
docker exec mlops_s26-minio-1 mc mb minio/datasets
docker exec mlops_s26-minio-1 mc mb minio/models
```

### 6. Upload test data:
```bash
echo "feature1,feature2,target
1.0,2.0,0
2.0,3.0,0
3.0,4.0,1
4.0,5.0,1
5.0,6.0,0
6.0,7.0,1" > /tmp/test.csv

docker cp /tmp/test.csv mlops_s26-minio-1:/tmp/test.csv
docker exec mlops_s26-minio-1 mc cp /tmp/test.csv local/datasets/test_data
```

### 7. Test training:
```bash
curl -X POST "http://localhost:8000/train?dataset_name=test_data&dataset_id=1"
```

### 8. Check job:
```bash
curl "http://localhost:8000/jobs/1"
```

---

## Known Issue Remaining

The worker successfully runs the ML pipeline but hangs when trying to save the final model from MLflow back to MinIO. Jobs complete the training pipeline but status never updates to "succeeded" because `save_model_to_minio()` call hangs.

To debug further, add logging around the `save_model_to_minio` call in `worker.py`.

---

## Verification Commands

### Check all containers running:
```bash
docker compose ps
```

### Check orchestrator health:
```bash
curl http://localhost:8000/health
```

### Check training worker health:
```bash
curl http://localhost:8000/health  # Orchestrator returns this
# Or use docker logs
docker logs mlops_s26-training-worker-1
```

### Check inference service:
```bash
curl http://localhost:8001/health
```

### Test prediction:
```bash
curl -X POST "http://localhost:8001/predict?model_name=logistic_regression&model_version=1.0" \
  -H "Content-Type: application/json" \
  -d '{"age": 30, "monthly_spend": 100, "tenure_months": 12}'
```
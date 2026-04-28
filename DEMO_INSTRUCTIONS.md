# Demo Recording Instructions — MLOps Platform

## What to show

Record your screen showing the web UIs as you walk through the ML lifecycle:
1. Data uploaded to MinIO → registered in DB
2. Model trained → logged in MLflow
3. Model deployed → visible in Streamlit dashboard
4. Predictions served → metrics in Streamlit + API
5. Drift detected → automatic retraining job created
6. Container killed → inference still works → interrupted training recovers

**Show browser UIs. Use terminal only for quick triggers (curl commands).**

---

## Before recording (fresh start)

```bash
cd /home/andreipc/MLOps/MLOps_S26
docker compose build --no-cache
docker compose up -d
sleep 30
```

> **Note**: Always use `docker compose build --no-cache` for a clean build. Cached layers can cause stale service configurations.

Open these tabs in browser:
- **Streamlit:** http://localhost:8501 (login: `admin` / `admin123`)
- **MLflow:** http://localhost:5000
- **MinIO:** http://localhost:9001 (login: `minio` / `minio123`)
- **API Docs:** http://localhost:8000/docs  and  http://localhost:8001/docs

---

## STEP 1: Data Ingestion

**System Overview:** A dataset is uploaded via the orchestrator API, stored in MinIO, and registered in PostgreSQL.

**Terminal (trigger upload):**
```bash
curl -X POST http://localhost:8000/datasets \
  -F "file=@seeds/sample_dataset.csv" \
  -F "name=customer_churn"
```

Expected response:
```json
{
  "dataset_id": 1,
  "name": "customer_churn",
  "path": "sample_dataset/<checksum>.csv",
  "size": 527,
  "format": "csv"
}
```

**Browser — MinIO (http://localhost:9001):**
1. Click "datasets" bucket
2. Show the uploaded CSV file with its checksum-based path

**Browser — Streamlit (http://localhost:8501):**
1. Click "Datasets" tab
2. Show the dataset row in the table with status "ready"

---

## STEP 2: Training

**System Overview:** A training job is created via the orchestrator, picked up by the training worker, which downloads the dataset, runs the ML pipeline, logs metrics to MLflow, and saves the model to MinIO.

**Terminal (start training):**
```bash
curl -X POST "http://localhost:8000/train?dataset_id=1&dataset_name=customer_churn"
```

Expected response:
```json
{
  "job_id": 1,
  "status": "pending"
}
```

**Wait ~30 seconds** for the worker to complete the training.

**Browser — MLflow (http://localhost:5000):**
1. Click the "first_ml_baseline" experiment
2. Show the run with parameters (`model_type`, `test_size`, etc.) and metrics (`accuracy`, `precision`, `recall`, `f1`)
3. Expand "Artifacts" to show the saved `model.joblib` file

**Browser — Streamlit (http://localhost:8501) → "Jobs" tab:**
1. Show the job with status "succeeded"

**Browser — MinIO:**
1. Click "models" bucket → "LogisticRegression"
2. Show the `.joblib` model file

---

## STEP 3: Deployment

**System Overview:** A trained model is promoted to production via the orchestrator API. This creates an active deployment record.

**Terminal (promote model):**
```bash
# Get the latest model version
LATEST_VER=$(docker compose exec -T postgres psql -U mlops -d mlops -t -c \
  "SELECT model_version FROM trained_models ORDER BY created_at DESC LIMIT 1;" 2>/dev/null | tr -d ' \n')

curl -X POST "http://localhost:8000/promote" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "model_name=LogisticRegression&model_version=$LATEST_VER"
```

Expected response:
```json
{
  "deployment_id": 1,
  "model_name": "LogisticRegression",
  "model_version": "1_1_<run_id>",
  "status": "active"
}
```

> **Note:** Each promote deactivates any previous active deployment for the same model name, ensuring only one version is in production at a time.

**Browser — Streamlit (http://localhost:8501) → "Deployments" tab:**
1. Show the deployment row with status "active"

---

## STEP 4: Inference

**System Overview:** The inference service loads the model from MinIO, runs predictions, logs results to PostgreSQL, and performs real-time drift detection in the background.

**Browser — Inference API (http://localhost:8001/docs):**
1. Expand `/predict` → click "Try it out"
2. Fill in: `model_name=LogisticRegression`, `model_version=1_1_<run_id>`
3. Enter JSON body:
```json
{
  "age": 30,
  "monthly_spend": 100,
  "tenure_months": 24,
  "income": 55000,
  "credit_score": 700
}
```
4. Click "Execute" → show response with prediction, score, `latency_ms`
5. Repeat 2-3 more times with different values

Example response:
```json
{
  "request_id": "...",
  "timestamp": "...",
  "model_version": "1_1_<run_id>",
  "prediction": {"label": 0, "score": 0.42},
  "latency_ms": 3,
  "status": "success"
}
```

**Browser — Streamlit (http://localhost:8501) → "Monitoring" tab:**
1. Show prediction counts, success/failed distribution
2. Show latency statistics (avg, min, max)

---

## STEP 5: Drift Detection & Automatic Retraining

**System Overview:** The inference service evaluates drift for every prediction by comparing input features against the model's reference profile (mean/std from training). If drift is detected, a retraining job is automatically created in the database. The training worker picks it up and retrains the model.

**Browser — Inference API (http://localhost:8001/docs):**
1. `/predict` endpoint again
2. Enter extreme values (out of distribution):
```json
{
  "age": 999,
  "monthly_spend": 99999,
  "tenure_months": 999,
  "income": 999999,
  "credit_score": 999
}
```
3. Execute 5-10 times

**Terminal (check drift detection logs):**
```bash
docker compose logs inference_service --tail=20 | grep drift
```

Expected output:
```
Drift detected for LogisticRegression:<version> score=408.7176 retraining_job_id=<id>
```

**Browser — Streamlit (http://localhost:8501) → "Jobs" tab:**
1. Show a new job with status "pending" → "running" → "succeeded" (drift-triggered retraining)

**Browser — MLflow (http://localhost:5000):**
1. Show the new run created by the retraining job
2. Compare metrics with the original model

**Terminal (promote the retrained model):**
```bash
LATEST_VER=$(docker compose exec -T postgres psql -U mlops -d mlops -t -c \
  "SELECT model_version FROM trained_models ORDER BY created_at DESC LIMIT 1;" 2>/dev/null | tr -d ' \n')

curl -X POST "http://localhost:8000/promote" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "model_name=LogisticRegression&model_version=$LATEST_VER"
```

**Browser — Streamlit (http://localhost:8501) → "Deployments" tab:**
1. Show the new deployment (previous version is now inactive)

---

## STEP 6: Fault Tolerance & Crash Recovery

**Hypothesis:** The system is resilient to failures — inference continues when the training worker is killed, and interrupted training jobs recover automatically when the worker restarts.

### Part 1: Inference survives worker crash

**Terminal (baseline prediction):**
```bash
curl -s -X POST "http://localhost:8001/predict?model_name=LogisticRegression&model_version=<version>" \
  -H "Content-Type: application/json" \
  -d '{"age": 30, "monthly_spend": 100, "tenure_months": 24, "income": 55000, "credit_score": 700}' | python3 -m json.tool
```

**Terminal (kill training worker):**
```bash
docker compose kill training-worker
```

**Terminal (inference with "crashed" worker):**
```bash
curl -s -X POST "http://localhost:8001/predict?model_name=LogisticRegression&model_version=<version>" \
  -H "Content-Type: application/json" \
  -d '{"age": 35, "monthly_spend": 150, "tenure_months": 12, "income": 60000, "credit_score": 720}' | python3 -m json.tool
```

Expected: Prediction succeeds with `latency_ms` and `status: "success"`

### Part 2: Crash Recovery — interrupted training job

**Terminal (start a new training job):**
```bash
curl -s -X POST "http://localhost:8000/train?dataset_id=1&dataset_name=customer_churn" | python3 -m json.tool
```

Note the `job_id` from the response.

**Terminal (wait for worker to pick up the job):**
```bash
# Poll until job status changes to "running"
while [ "$(docker compose exec -T postgres psql -U mlops -d mlops -t -c "SELECT status FROM jobs WHERE job_id=<JOB_ID>;" 2>/dev/null | tr -d ' \n')" != "running" ]; do
  sleep 2
done
echo "Job is RUNNING — killing worker now..."
```

**Terminal (kill worker DURING training):**
```bash
docker compose kill training-worker
```

**Terminal (job status after crash):**
```bash
docker compose exec -T postgres psql -U mlops -d mlops -c \
  "SELECT job_id, status FROM jobs WHERE job_id=<JOB_ID>;"
```

Expected: `status = "running"` (job is stuck)

**Terminal (restart worker — simulates auto-recovery):**
```bash
docker compose up -d training-worker
```

**Terminal (wait for recovery — polls every 5s for up to 60s):**
```bash
for i in $(seq 1 12); do
  STATUS=$(docker compose exec -T postgres psql -U mlops -d mlops -t -c \
    "SELECT status FROM jobs WHERE job_id=<JOB_ID>;" 2>/dev/null | tr -d ' \n')
  echo "  $((i*5))s: job status=$STATUS"
  if [ "$STATUS" = "succeeded" ]; then
    echo "  ✅ Job recovered and completed in $((i*5))s"
    break
  fi
  if [ "$STATUS" = "failed" ]; then
    echo "  ❌ Job failed"
    break
  fi
  sleep 5
done
```

**Terminal (verify recovery):**
```bash
echo "Job status:"
docker compose exec -T postgres psql -U mlops -d mlops -c \
  "SELECT job_id, status FROM jobs WHERE job_id=<JOB_ID>;"

echo "Model in DB:"
docker compose exec -T postgres psql -U mlops -d mlops -c \
  "SELECT model_name, model_version FROM trained_models WHERE job_id=<JOB_ID>;"

echo "Model in MinIO:"
docker compose exec -T postgres psql -U mlops -d mlops -t -c \
  "SELECT model_path FROM trained_models WHERE job_id=<JOB_ID>;"
```

### Part 3: Data Integrity

**Terminal (verify all data is consistent):**
```bash
echo "Datasets:"
docker compose exec -T postgres psql -U mlops -d mlops -t -c "SELECT count(*) FROM datasets;"

echo "Trained models:"
docker compose exec -T postgres psql -U mlops -d mlops -t -c "SELECT count(*) FROM trained_models;"

echo "Jobs:"
docker compose exec -T postgres psql -U mlops -d mlops -t -c "SELECT count(*) FROM jobs;"

echo "Prediction logs:"
docker compose exec -T postgres psql -U mlops -d mlops -t -c "SELECT count(*) FROM prediction_logs;"
```

### Part 4: Final Verification

**Terminal (inference still works):**
```bash
curl -s -X POST "http://localhost:8001/predict?model_name=LogisticRegression&model_version=<version>" \
  -H "Content-Type: application/json" \
  -d '{"age": 40, "monthly_spend": 200, "tenure_months": 36, "income": 70000, "credit_score": 750}' | python3 -m json.tool
```

**Result summary:**
- ✅ Inference works when worker is killed
- ✅ Interrupted job recovered after worker restart
- ✅ Data intact (DB, MinIO, MLflow)
- ✅ System fully operational

---

## Quick Reference

```bash
cd /home/andreipc/MLOps/MLOps_S26

# Start (fresh build)
docker compose build --no-cache
docker compose up -d
sleep 30

# Upload dataset
curl -X POST http://localhost:8000/datasets -F "file=@seeds/sample_dataset.csv" -F "name=customer_churn"

# Train
curl -X POST "http://localhost:8000/train?dataset_id=1&dataset_name=customer_churn"

# Deploy (auto-fetch latest version)
LATEST_VER=$(docker compose exec -T postgres psql -U mlops -d mlops -t -c \
  "SELECT model_version FROM trained_models ORDER BY created_at DESC LIMIT 1;" 2>/dev/null | tr -d ' \n')
curl -X POST "http://localhost:8000/promote" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "model_name=LogisticRegression&model_version=$LATEST_VER"

# Drift detection (send extreme values via API docs)
# Then check: docker compose logs inference_service --tail=20 | grep drift

# Fault tolerance
docker compose kill training-worker
docker compose up -d training-worker

# Find model version
docker compose exec -T postgres psql -U mlops -d mlops -c \
  "SELECT model_name, model_version FROM trained_models LIMIT 1;"

# Stop
docker compose down
```

---

## URLs

| UI | URL |
|---|---|
| Streamlit Dashboard | http://localhost:8501 |
| MLflow | http://localhost:5000 |
| MinIO | http://localhost:9001 (minio/minio123) |
| Orchestrator API | http://localhost:8000/docs |
| Inference API | http://localhost:8001/docs |

---

## Troubleshooting

**Services won't start:**
```bash
docker compose down -v && docker compose build --no-cache && docker compose up -d && sleep 30
```

**Training fails:**
```bash
docker compose logs training-worker --tail=50
```

**Can't find model version:**
```bash
docker compose exec -T postgres psql -U mlops -d mlops -c \
  "SELECT model_name, model_version FROM trained_models ORDER BY created_at DESC LIMIT 3;"
```

**Drift not triggering:**
```bash
# Check drift threshold
docker compose exec -T postgres psql -U mlops -d mlops -t -c \
  "SELECT parameters->>'reference_profile' FROM trained_models ORDER BY created_at DESC LIMIT 1;"

# Check inference logs
docker compose logs inference_service --tail=50 | grep -E "drift|Drift"
```

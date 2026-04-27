# Demo Recording Instructions — MLOps Platform

## What to show

Record your screen showing the web UIs as you walk through the ML lifecycle:
1. Data uploaded to MinIO → registered in DB
2. Model trained → logged in MLflow
3. Model deployed → visible in Streamlit dashboard
4. Predictions served → metrics in Streamlit + API
5. Drift detected → automatic retraining job created
6. Container stopped → inference still works → container restarted

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
- **Streamlit:** http://localhost:8501
- **MLflow:** http://localhost:5000
- **MinIO:** http://localhost:9001 (minio / minio123)
- **API Docs:** http://localhost:8000/docs  and  http://localhost:8001/docs

---

## STEP 1: Data Ingestion

**Terminal (trigger upload):**
```bash
curl -X POST http://localhost:8000/datasets -F "file=@seeds/sample_dataset.csv" -F "name=customer_churn"
```

**Browser — MinIO (http://localhost:9001):**
1. Click "datasets" bucket
2. Show the uploaded CSV file with checksum path

**Browser — Streamlit (http://localhost:8501):**
1. Click "Datasets" tab
2. Show the dataset row in the table

---

## STEP 2: Training

**Terminal (start training):**
```bash
curl -X POST "http://localhost:8000/train?dataset_id=1&dataset_name=customer_churn"
```

**Browser — MLflow (http://localhost:5000):**
1. Click the "customer_churn" experiment
2. Show the run with parameters and metrics (accuracy, precision, recall)
3. Expand "Artifacts" to show the saved model

**Browser — Streamlit (http://localhost:8501) → "Jobs" tab:**
1. Show job status changed to "succeeded"

**Browser — MinIO:**
1. Click "models" bucket → "LogisticRegression"
2. Show the .joblib model file

---

## STEP 3: Deployment

**Terminal (promote model):**
```bash
curl -X POST "http://localhost:8000/promote" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "model_name=LogisticRegression&model_version=1_1_xxx"
```
(Replace `1_1_xxx` with the actual version from MLflow or the Jobs tab)

**Browser — Streamlit (http://localhost:8501) → "Deployments" tab:**
1. Show the deployment row with status "active"

---

## STEP 4: Inference

**Browser — Inference API (http://localhost:8001/docs):**
1. Expand `/predict` → click "Try it out"
2. Fill in: `model_name=LogisticRegression`, `model_version=1_1_xxx`
3. Enter JSON body:
```json
{"age": 30, "monthly_spend": 100, "tenure_months": 24, "income": 55000, "credit_score": 700}
```
4. Click "Execute" → show response with prediction, score, latency_ms
5. Repeat 2-3 more times with different values

**Browser — Streamlit (http://localhost:8501) → "Monitoring" tab:**
1. Show prediction counts, success/failed distribution
2. Show latency statistics

---

## STEP 5: Drift Detection

**Browser — Inference API (http://localhost:8001/docs):**
1. `/predict` endpoint again
2. Enter extreme values:
```json
{"age": 999, "monthly_spend": 99999, "tenure_months": 999, "income": 999999, "credit_score": 999}
```
3. Execute 5-10 times

**Browser — Streamlit (http://localhost:8501) → "Jobs" tab:**
1. Show a new job with status "pending" (drift-triggered retraining)

---

## STEP 6: Fault Tolerance

**Terminal (stop worker):**
```bash
docker compose stop training-worker
```

**Browser — Inference API (http://localhost:8001/docs):**
1. Make a prediction — it still works!
2. Show the successful response

**Terminal (restart worker):**
```bash
docker compose start training-worker
```

**Terminal (verify):**
```bash
docker compose ps
```
Show that training-worker is back to "Up" status.

---

## Quick Reference

```bash
cd /home/andreipc/MLOps/MLOps_S26

# Start (fresh build)
docker compose build --no-cache
docker compose up -d

# Upload dataset
curl -X POST http://localhost:8000/datasets -F "file=@seeds/sample_dataset.csv" -F "name=customer_churn"

# Train
curl -X POST "http://localhost:8000/train?dataset_id=1&dataset_name=customer_churn"

# Deploy (replace version)
curl -X POST "http://localhost:8000/promote" -H "Content-Type: application/x-www-form-urlencoded" -d "model_name=LogisticRegression&model_version=1_1_xxx"

# Fault tolerance
docker compose stop training-worker
docker compose start training-worker

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
docker compose build orchestrator && docker compose restart orchestrator
```

**Can't find model version:**
```bash
docker compose exec postgres psql -U mlops -d mlops -c "SELECT model_name, model_version FROM trained_models LIMIT 1;"
```

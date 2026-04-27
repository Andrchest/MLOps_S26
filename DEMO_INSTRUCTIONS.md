# Demo Recording Instructions — MLOps Platform

## Demo Overview

This demo shows the full ML model lifecycle through web UIs:
- Data ingestion → MinIO (object storage web UI)
- Training → MLflow (experiment tracking UI)
- Deployment → PostgreSQL + Streamlit (operational dashboard)
- Inference → API docs (FastAPI Swagger)
- Monitoring → Grafana (dashboards)
- Drift detection → automatic retraining trigger

**The key: show the browser UIs, not terminal commands.**

---

## Preparation (before recording)

### 1. Start the platform
```bash
cd /home/andreipc/MLOps/MLOps_S26
docker compose up -d
```
Wait 30 seconds for all services to start.

### 2. Clear database for clean demo
```bash
docker compose exec postgres psql -U mlops -d mlops -c "DELETE FROM prediction_logs; DELETE FROM deployments; DELETE FROM trained_models; DELETE FROM jobs; DELETE FROM datasets; ALTER SEQUENCE jobs_job_id_seq RESTART WITH 1; ALTER SEQUENCE datasets_dataset_id_seq RESTART WITH 1; ALTER SEQUENCE deployments_deployment_id_seq RESTART WITH 1;"
```

### 3. IMPORTANT: Reset application code
The running containers need updated code. Rebuild and restart:
```bash
docker compose build orchestrator
docker compose restart orchestrator inference-service
sleep 10
```

---

## Recording Steps (show browser UIs)

### STEP 1: Show platform overview (30 seconds)

Open in browser and show each tab:

1. **MinIO** — http://localhost:9001 (login: minio, password: minio123)
   - Show the buckets: `datasets/` and `models/`
   - These are empty initially

2. **MLflow** — http://localhost:5000
   - Show the experiments page (empty at start)

3. **Grafana** — http://localhost:3000 (admin/admin)
   - Show the dashboards: "ML Platform Overview" and "ML Monitoring"

4. **Streamlit** — http://localhost:8501
   - Show the operational dashboard with tabs

Say: "This platform has 4 main web UIs: MinIO for storage, MLflow for experiments, Grafana for monitoring, Streamlit for operations."

---

### STEP 2: Data Ingestion (30 seconds)

**In browser — MinIO:** http://localhost:9001

1. Navigate to buckets
2. Click "Upload" — select the file `seeds/sample_dataset.csv`
3. Show the uploaded file in the bucket
4. Copy the path (shown in MinIO)

**Then in terminal (quick, just to trigger):**
```bash
curl -X POST http://localhost:8000/datasets -F "file=@seeds/sample_dataset.csv" -F "name=customer_churn"
```

**Back to browser:**

1. **Streamlit** — http://localhost:8501 → "Datasets" tab
   - Show the new dataset appears in the table

2. **PostgreSQL** (optional, show in terminal):
```bash
docker compose exec postgres psql -U mlops -d mlops -c "SELECT * FROM datasets;"
```
Show: dataset_id=1, name=customer_churn

Say: "Data is uploaded to MinIO AND registered in PostgreSQL. Dataset ID = 1."

---

### STEP 3: Model Training (60 seconds)

**In terminal (quick, just to trigger training):**
```bash
curl -X POST "http://localhost:8000/train?dataset_id=1&dataset_name=customer_churn"
```

**While training runs, SHOW IN BROWSER:**

1. **MLflow** — http://localhost:5000
   - Refresh page periodically
   - Show new experiment appears: "customer_churn"
   - Click on it → show parameters, metrics appearing in real-time

2. **Streamlit** — http://localhost:8501 → "Jobs" tab
   - Show job status: "running"

**Wait 30-60 seconds for training to complete, then:**

1. **MLflow** — refresh
   - Show completed run with metrics (accuracy, precision, recall)
   - Show model artifact registered

2. **Streamlit** — refresh "Jobs" tab
   - Show job status: "succeeded"

3. **MinIO** — refresh bucket
   - Show new model file in `models/LogisticRegression/`

Say: "Training worker picks up the job, runs the ML pipeline, logs everything to MLflow, saves the model to MinIO."

---

### STEP 4: Model Deployment (30 seconds)

**In browser:**

1. **Streamlit** — http://localhost:8501 → "Deployments" tab
   - Shows empty initially
   - Click "Deploy" button for the trained model
   - Or use API:

**In terminal (quick):**
```bash
curl -X POST "http://localhost:8000/promote" -H "Content-Type: application/x-www-form-urlencoded" -d "model_name=LogisticRegression&model_version=1_1_xxx"
```
(Replace 1_1_xxx with actual version from MLflow or jobs table)

**Back to browser:**

1. **Streamlit** — refresh "Deployments" tab
   - Show: deployment_id=1, model_name, status="active"

Say: "Model is promoted to production. It's now active for inference."

---

### STEP 5: Make Predictions (30 seconds)

**In browser — API docs:** http://localhost:8001/docs

1. Click on `/predict` endpoint
2. Click "Try it out"
3. Enter model_name and model_version (from deployments)
4. Enter JSON:
```json
{"age": 30, "monthly_spend": 100, "tenure_months": 24, "income": 55000, "credit_score": 700}
```
5. Click "Execute"
6. Show the response: prediction, score, latency_ms

**Repeat 2-3 times with different data.**

**Then SHOW IN BROWSER:**

1. **Streamlit** — http://localhost:8501 → "Monitoring" tab
   - Show prediction counts, success/failed distribution, latency chart

2. **Grafana** — http://localhost:3000 → "ML Monitoring" dashboard
   - Show prediction metrics, latency over time

Say: "Predictions are served with latency metrics. Every request is logged and visible in monitoring dashboards."

---

### STEP 6: Drift Detection (45 seconds)

**Send anomalous data:**

**In browser — API docs:** http://localhost:8001/docs

1. `/predict` endpoint again
2. Enter extreme values:
```json
{"age": 999, "monthly_spend": 99999, "tenure_months": 999, "income": 999999, "credit_score": 999}
```
3. Execute multiple times (5-10x)

**SHOW IN BROWSER:**

1. **Streamlit** — http://localhost:8501 → "Jobs" tab
   - New job appears: status="pending" (drift-triggered retraining)

2. **Or in terminal:**
```bash
docker compose exec postgres psql -U mlops -d mlops -c "SELECT * FROM jobs WHERE status='pending';"
```
Show: new job for retraining

Say: "When I send out-of-distribution data (age=999), the system detects data drift and automatically creates a retraining job. The model will be retrained on fresh data."

---

### STEP 7: Fault Tolerance (45 seconds)

**STOP a container:**

**In terminal:**
```bash
docker compose stop training-worker
```

**SHOW IN BROWSER — proves system still works:**

1. **API docs** — http://localhost:8001/docs
   - Make a prediction — it still works!
   - Show inference service is healthy despite worker being down

2. **Streamlit** — refresh "Jobs" tab
   - Existing completed jobs are still visible

3. **Grafana** — http://localhost:3000
   - Show dashboard is still updating

**RESTART container:**

```bash
docker compose start training-worker
```

**SHOW:**

1. **Terminal:**
```bash
docker compose ps
```
Show: training-worker is back up

Say: "Even when the training worker is down, inference continues. The system is resilient to failures."

---

### STEP 8: Summary — Show all UIs (30 seconds)

Walk through each UI one more time:

1. **MLflow** — http://localhost:5000
   - Show experiments, artifacts

2. **Grafana** — http://localhost:3000
   - Show both dashboards

3. **Streamlit** — http://localhost:8501
   - Walk through all tabs

4. **MinIO** — http://localhost:9001
   - Show datasets bucket and models bucket

Say: "Complete MLOps platform with ML lifecycle, monitoring, and fault tolerance."

---

## Quick Reference — All Commands

```bash
cd /home/andreipc/MLOps/MLOps_S26

# Start platform
docker compose up -d

# Clear database
docker compose exec postgres psql -U mlops -d mlops -c "DELETE FROM prediction_logs; DELETE FROM deployments; DELETE FROM trained_models; DELETE FROM jobs; DELETE FROM datasets; ALTER SEQUENCE jobs_job_id_seq RESTART WITH 1; ALTER SEQUENCE datasets_dataset_id_seq RESTART WITH 1; ALTER SEQUENCE deployments_deployment_id_seq RESTART WITH 1;"

# Rebuild with fixes
docker compose build orchestrator
docker compose restart orchestrator inference-service

# Trigger demo steps
curl -X POST http://localhost:8000/datasets -F "file=@seeds/sample_dataset.csv" -F "name=customer_churn"
curl -X POST "http://localhost:8000/train?dataset_id=1&dataset_name=customer_churn"
curl -X POST "http://localhost:8000/promote" -H "Content-Type: application/x-www-form-urlencoded" -d "model_name=LogisticRegression&model_version=XXX"

# Fault tolerance test
docker compose stop training-worker
docker compose start training-worker

# Stop
docker compose down
```

---

## Troubleshooting

### Problem: Services won't start
```bash
docker compose down -v
docker compose up -d --build
sleep 30
```

### Problem: Training fails with "NoSuchKey"
Rebuild orchestrator with fixes:
```bash
docker compose build orchestrator
docker compose restart orchestrator
```

### Problem: Can't find model version
```bash
docker compose exec postgres psql -U mlops -d mlops -c "SELECT model_name, model_version FROM trained_models LIMIT 1;"
```

---

## Access Points

| UI | URL | Login | Purpose |
|---|---|---|---|
| MLflow | http://localhost:5000 | (none) | Experiment tracking |
| Grafana | http://localhost:3000 | admin/admin | Monitoring dashboards |
| Streamlit | http://localhost:8501 | (none) | Operational dashboard |
| MinIO | http://localhost:9001 | minio/minio123 | Object storage |
| API Docs | http://localhost:8000/docs | (none) | Orchestrator API |
| Inference API | http://localhost:8001/docs | (none) | Inference API |

---

## Platform Architecture

```
┌────────────────────────────────────────────┐
│              Web UIs                        │
├──────────┬──────────┬──────────┬──────────┤
│  MLflow   │ Grafana  │ Streamlit│  MinIO   │
│  :5000    │  :3000  │  :8501   │  :9001   │
├──────────┴──────────┴──────────┴──────────┤
│            Services                        │
│  Orchestrator:8000 │ Inference:8001       │
│  Training Worker:8500                     │
├────────────────────────────────────────────┤
│         Infrastructure                    │
│  PostgreSQL:5432 │ MinIO Storage         │
└────────────────────────────────────────────┘
```
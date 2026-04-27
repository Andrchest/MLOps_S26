# Demo Recording Instructions — MLOps Platform

## What this demo shows

The demo demonstrates the full ML model lifecycle in a distributed platform:
data ingestion → training → deployment → inference → drift detection → automated retraining → fault tolerance.

---

## Preparation (5 minutes before recording)

### 1. Start the platform
```bash
cd /home/andreipc/MLOps/MLOps_S26
docker compose up -d
```
Wait 30 seconds for all services to come up.

### 2. Verify everything works
Open in browser:
- **MLflow:** http://localhost:5000 — MLflow UI should load
- **Grafana:** http://localhost:3000 (login/password: admin/admin) — dashboards
- **Streamlit:** http://localhost:8501 — Streamlit dashboard
- **MinIO:** http://localhost:9001 (login/password: minio/minio123) — file manager

### 3. Clear the database for a clean demo
```bash
docker compose exec postgres psql -U mlops -d mlops -c "DELETE FROM prediction_logs; DELETE FROM deployments; DELETE FROM trained_models; DELETE FROM jobs; DELETE FROM datasets; ALTER SEQUENCE jobs_job_id_seq RESTART WITH 1; ALTER SEQUENCE datasets_dataset_id_seq RESTART WITH 1; ALTER SEQUENCE deployments_deployment_id_seq RESTART WITH 1;"
```

### 4. Open terminal
Open a terminal in `/home/andreipc/MLOps/MLOps_S26` — this will be the main recording window.

---

## Recording Steps

### STEP 0: Start recording
Open your screen recording software and start recording.

---

### STEP 1: Data Ingestion (20 seconds)
**Terminal command:**
```bash
bash scripts/demo.sh data 2>&1
```

**Show on screen:**
- Script output: `Dataset uploaded: id=1`
- Data is now in MinIO and PostgreSQL

---

### STEP 2: Model Training (30-40 seconds)
**Terminal command:**
```bash
bash scripts/demo.sh train 2>&1
```

**Show on screen:**
- Job creation: `Training job created: job_id=1`
- Status: `Training completed successfully!`
- Training results (accuracy, metrics)

---

### STEP 3: Model Deployment (15 seconds)
**Terminal command:**
```bash
bash scripts/demo.sh deploy 2>&1
```

**Show on screen:**
- Response: `{"deployment_id": 1, "status": "active", ...}`
- Model is now available for inference

---

### STEP 4: Inference (20 seconds)
**Terminal command:**
```bash
bash scripts/demo.sh infer 2>&1
```

**Show on screen:**
- Prediction response: `{"prediction": {"label": 1, "score": 0.51}, "latency_ms": 3063}`
- 5 additional predictions for metrics collection

---

### STEP 5: Drift Detection & Retraining (30 seconds)
**Terminal command:**
```bash
bash scripts/demo.sh drift 2>&1
```

**Show on screen:**
- Prediction with anomalous data: `{"age": 999, "monthly_spend": 99999}`
- Response: `Drift-triggered retraining jobs found: 2|customer_churn|pending`

**Optional — show pending jobs:**
```bash
docker compose exec postgres psql -U mlops -d mlops -c "SELECT * FROM jobs WHERE status='pending';"
```

---

### STEP 6: Fault Tolerance (30 seconds)
**Terminal command:**
```bash
bash scripts/demo.sh fault 2>&1
```

**Show on screen:**
- Container stop: `training-worker container stopped`
- Health check: `Inference service is still healthy despite training-worker being down`
- Recovery: `training-worker is back up and running`
- Final table: all services in `Up` status

---

### STEP 7: Final — Service Overview (20 seconds)
**Terminal command:**
```bash
bash scripts/demo.sh all 2>&1 | tail -20
```

**OR show in browser:**
1. **MLflow** (http://localhost:5000) — experiments, metrics, artifacts
2. **Grafana** (http://localhost:3000) — monitoring dashboards
3. **Streamlit** (http://localhost:8501) — operational dashboard

---

## Quick Reference — All Commands

```bash
cd /home/andreipc/MLOps/MLOps_S26

# Start the platform
docker compose up -d

# Clear DB for a new demo
docker compose exec postgres psql -U mlops -d mlops -c "DELETE FROM prediction_logs; DELETE FROM deployments; DELETE FROM trained_models; DELETE FROM jobs; DELETE FROM datasets; ALTER SEQUENCE jobs_job_id_seq RESTART WITH 1; ALTER SEQUENCE datasets_dataset_id_seq RESTART WITH 1; ALTER SEQUENCE deployments_deployment_id_seq RESTART WITH 1;"

# Full demo (all steps)
bash scripts/demo.sh all

# Or step by step:
bash scripts/demo.sh data
bash scripts/demo.sh train
bash scripts/demo.sh deploy
bash scripts/demo.sh infer
bash scripts/demo.sh drift
bash scripts/demo.sh fault

# Stop the platform
docker compose down
```

---

## Troubleshooting

### Problem: "Dataset already exists"
**Solution:** Clear the database (see Preparation step 3).

### Problem: "Training failed"
**Solution:** Check worker logs:
```bash
docker compose logs training-worker --tail=30
```
Restart the worker:
```bash
docker compose restart training-worker
```

### Problem: "Not Found" on deploy
**Solution:** The model hasn't been trained yet. Run the train step first.

### Problem: services won't start
**Solution:** Full restart:
```bash
docker compose down -v
docker compose up -d --build
sleep 30
```

---

## Platform Architecture (for Q&A)

```
┌─────────────────────────────────────────────────────────────┐
│                    MLOps Platform                           │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│ Orchestrator│ Training    │ Inference   │ Monitoring      │
│ :8000       │ Worker      │ Service     │ Dashboards      │
│ Job Mgmt    │ :8500       │ :8001       │ Grafana:3000    │
│ Training    │ Training    │ Inference   │ Streamlit:8501  │
├─────────────┴─────────────┴─────────────┴─────────────────┤
│              Infrastructure                                 │
│  PostgreSQL:5432  │  MinIO:9000  │  MLflow:5000           │
│  Metadata         │  Storage     │  Experiments           │
└─────────────────────────────────────────────────────────────┘
```

### Key capabilities:
- **Data Drift** — automatic detection via statistical tests
- **Fault Tolerance** — circuit breakers, retry logic, graceful degradation
- **Scheduled Retraining** — background service with configurable interval
- **Monitoring** — Prometheus metrics + Grafana dashboards + prediction logs
- **CI/CD** — GitHub Actions with tests, linting, Docker build, Trivy

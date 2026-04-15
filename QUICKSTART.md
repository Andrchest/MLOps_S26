# Quick Start Guide

```bash
# 1. Start containers
docker compose up -d

# 2. Initialize database (one time only)
docker exec -i mlops_s26-postgres-1 psql -U mlops -d mlops -c "
CREATE TABLE IF NOT EXISTS jobs (job_id SERIAL PRIMARY KEY, dataset_name TEXT NOT NULL, dataset_id INT NOT NULL, status TEXT DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS trained_models (job_id INT NOT NULL REFERENCES jobs(job_id), model_name TEXT NOT NULL, model_version TEXT NOT NULL, model_path TEXT NOT NULL, metrics JSONB NOT NULL, parameters JSONB NOT NULL, created_at TIMESTAMP DEFAULT now(), UNIQUE (job_id, model_version), PRIMARY KEY (job_id, model_version));
"

# 3. Check health
curl http://localhost:8000/health   # Orchestrator
curl http://localhost:8001/health  # Inference

# 4. Create dataset
curl -X POST "http://localhost:8000/datasets?dataset_name=test_data&dataset_id=1"

# 5. Start training
curl -X POST "http://localhost:8000/train?dataset_name=test_data&dataset_id=1"

# 6. Check job status
curl http://localhost:8000/jobs/1

# 7. Try inference (after model is trained)
curl -X POST "http://localhost:8001/predict?model_name=test&model_version=1.0" -H "Content-Type: application/json" -d '{"age": 30, "monthly_spend": 100, "tenure_months": 12}'
```
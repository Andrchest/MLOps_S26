# Quick Start Guide

## 1. Get Latest Code
```bash
git checkout integration/week-2-backbone
git pull
```

## 2. Start Containers
```bash
docker compose up -d
```

## 3. Build (after code changes)
```bash
docker compose build training-worker
docker compose up -d training-worker
```

## 4. Initialize Database (one time only)
```bash
docker exec -i mlops_s26-postgres-1 psql -U mlops -d mlops -c "
CREATE TABLE IF NOT EXISTS jobs (job_id SERIAL PRIMARY KEY, dataset_name TEXT NOT NULL, dataset_id INT NOT NULL, status TEXT DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS trained_models (job_id INT NOT NULL REFERENCES jobs(job_id), model_name TEXT NOT NULL, model_version TEXT NOT NULL, model_path TEXT NOT NULL, metrics JSONB NOT NULL, parameters JSONB NOT NULL, created_at TIMESTAMP DEFAULT now(), UNIQUE (job_id, model_version), PRIMARY KEY (job_id, model_version));
"
```

## 5. Create MinIO Buckets (one time only)
```bash
docker exec mlops_s26-minio-1 mc mb minio/datasets
docker exec mlops_s26-minio-1 mc mb minio/models
```

## 6. Upload Test Dataset to MinIO
```bash
echo "feature1,feature2,target
1.0,2.0,0
2.0,3.0,0
3.0,4.0,1" > /tmp/test.csv

docker cp /tmp/test.csv mlops_s26-minio-1:/tmp/test.csv
docker exec mlops_s26-minio-1 mc cp /tmp/test.csv local/datasets/test_data
```

## 7. Check Health
```bash
curl http://localhost:8000/health   # Orchestrator
curl http://localhost:8001/health  # Inference
```

## 8. Start Training Job
```bash
curl -X POST "http://localhost:8000/train?dataset_name=test_data&dataset_id=1"
```

## 9. Check Job Status
```bash
sleep 30
curl http://localhost:8000/jobs/1
```

## 10. Try Inference (after model is trained)
```bash
curl -X POST "http://localhost:8001/predict?model_name=test&model_version=1.0" -H "Content-Type: application/json" -d '{"age": 30, "monthly_spend": 100, "tenure_months": 12}'
```

## Debug Commands
```bash
# Check worker logs
docker logs mlops_s26-training-worker-1 | tail -30

# Check jobs in database
docker exec mlops_s26-postgres-1 psql -U mlops -d mlops -c "SELECT * FROM jobs ORDER BY job_id DESC LIMIT 5;"

# Check MinIO files
docker exec mlops_s26-minio-1 mc ls minio/models/
```
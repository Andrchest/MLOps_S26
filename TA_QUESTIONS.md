# MLOps Platform — TA Questions & Gap Analysis

**Date:** Apr 20, 2026  
**Branch:** `feature/week2-integration`  
**Purpose:** Identify missed parts and prepare for TA evaluation

---

## 1. MISSING FEATURES (Should exist per requirements)

### 1.1 Data Ingestion Pipeline ❌
| Requirement | Status | Details |
|-------------|--------|---------|
| `pipelines/data_ingestion/` | ❌ Empty | Directory exists but has only `.gitkeep` |
| Data validation | ❌ Not implemented | No schema validation, no data quality checks |
| Data transformation | ❌ Not implemented | No preprocessing, feature engineering |
| Data versioning | ❌ Not implemented | No DVC, no data lineage tracking |

**Impact:** The project says "data ingestion" but there's no actual pipeline. We only have `POST /datasets` which uploads CSV to MinIO. No validation, no transformation, no versioning.

**What TA will notice:** Directory `pipelines/data_ingestion/` exists but is empty. The word "ingestion" implies more than just upload.

---

### 1.2 Model Deployment ❌
| Requirement | Status | Details |
|-------------|--------|---------|
| `POST /models/promote` | ❌ Not implemented | No promote endpoint |
| `GET /models/{name}/deployments` | ❌ Not implemented | No deployment tracking |
| `POST /deployments/{id}/rollback` | ❌ Not implemented | No rollback |
| `GET /deployments` | ❌ Not implemented | No deployment list |
| `prod_models` DB table | ❌ Not implemented | No production model tracking |

**Impact:** The project requires "deployment" but we have no deployment mechanism. Models are saved to MinIO but there's no way to promote a model to production or track which version is live.

**What TA will notice:** No deployment endpoints, no production model tracking, no rollback capability.

---

### 1.3 Retraining Trigger ❌
| Requirement | Status | Details |
|-------------|--------|---------|
| Data drift detection | ❌ Not implemented | No drift detection logic |
| Automated retraining | ❌ Not implemented | No trigger for retraining |
| Retraining pipeline | ❌ Empty | `pipelines/training/` has only `.gitkeep` |
| Performance monitoring | ⚠️ Partial | Dashboard shows logs but no drift/degradation detection |

**Impact:** The project explicitly requires "retraining" but there's no mechanism to trigger it. The dashboard shows prediction logs but doesn't analyze them for drift or performance degradation.

**What TA will notice:** No drift detection, no automated retraining, empty `pipelines/training/` directory.

---

### 1.4 Written Report ❌
| Requirement | Status | Details |
|-------------|--------|---------|
| Project report | ❌ Not implemented | No `REPORT.md` or `docs/report/` |
| Architecture Decision Records (ADRs) | ❌ Not implemented | No `docs/adr/` directory |
| Experimental validation | ❌ Not implemented | No results, no benchmarks, no ablation studies |

**Impact:** 50% of the grade is "Design and Documentation" which includes written report, ADRs, demonstration quality, and explanation of design choices. We have README, TEST_FIXES, MERGE_LOG but NO actual project report.

**What TA will notice:** No formal report, no ADRs, no experimental results. This is the biggest gap.

---

### 1.5 Monitoring Service ❌
| Requirement | Status | Details |
|-------------|--------|---------|
| `services/monitoring-service/` | ⚠️ Skeleton | Only `/health` endpoint |
| Prediction logging | ✅ Implemented | In inference service, logs to DB |
| Drift detection | ❌ Not implemented | No drift detection logic |
| Alerting | ❌ Not implemented | No alerting mechanism |

**Impact:** The monitoring-service is just a skeleton. The actual monitoring work is in the dashboard (Streamlit), which reads directly from the database.

**What TA will notice:** `services/monitoring-service/app.py` is only 8 lines (just `/health`).

---

### 1.6 Experiments ❌
| Requirement | Status | Details |
|-------------|--------|---------|
| `experiments/` | ❌ Empty | Directory exists but has only `.gitkeep` |
| Hyperparameter tuning | ❌ Not implemented | No MLflow tracking of experiments |
| Model comparison | ❌ Not implemented | No model comparison UI |

**Impact:** The `experiments/` directory is empty. MLflow tracks experiments but there's no structured experiment management.

**What TA will notice:** Empty `experiments/` directory.

---

## 2. WEAK AREAS (Exist but incomplete/fragile)

### 2.1 Logging ⚠️
| Item | Status | Details |
|------|--------|---------|
| `shared/logging_utils.py` | ✅ Created | JSONFormatter, StructuredLogger, CorrelationLogger |
| Services using logging | ❌ Not implemented | All services still use basic `logging` |
| Log aggregation | ❌ Not implemented | No ELK, no Grafana Loki |

**Risk:** TA may ask "how do you debug in production?" — answer: you can't, because logging isn't implemented.

---

### 2.2 Fault Tolerance ⚠️
| Item | Status | Details |
|------|--------|---------|
| `recover_stuck_jobs()` | ❌ Bug | Resets ALL running jobs, should only reset stale ones (>30 min) |
| Graceful shutdown | ❌ Not implemented | No SIGTERM/SIGINT handlers |
| Health checks | ❌ Not implemented | No Docker health checks in docker-compose |
| Circuit breakers | ❌ Not implemented | No fallback when services are down |

**Risk:** TA will demo and see that if worker crashes, stuck jobs are never recovered (or all running jobs are reset).

---

### 2.3 Configuration ⚠️
| Item | Status | Details |
|------|--------|---------|
| Hardcoded paths | ⚠️ Present | Worker uses `/tmp/`, `pipelines/first_ml_baseline/train.py` |
| Config files | ❌ Empty | `shared/config/` has only `.gitkeep` |
| Environment validation | ❌ Not implemented | No check that required env vars exist |

**Risk:** Code is not production-ready due to hardcoded paths.

---

### 2.4 Code Quality ⚠️
| Item | Status | Details |
|------|--------|---------|
| Inline comments | ⚠️ Partial | Some files have comments, others don't |
| Type hints | ⚠️ Partial | `logging_utils.py` has type hints, others don't |
| Docstrings | ❌ Not implemented | No docstrings on functions/classes |
| Shared code | ❌ Empty | `shared/utils/`, `shared/schemas/` are empty |

**Risk:** TA may complain about lack of code documentation.

---

## 3. QUESTIONS TA WILL ASK (And How to Answer)

### 3.1 Architecture Questions

**Q1: "Why microservices instead of a modular monolith?"**
**Answer:** Microservices allow independent scaling and deployment. Each service has its own lifecycle and can be updated without affecting others. For example, the inference service can scale horizontally during high traffic while the training worker runs independently.

**Follow-up:** "What's the downside?"
**Answer:** Increased operational complexity, network latency, and debugging difficulty. We mitigate this with Docker Compose for local development and structured logging (planned).

---

**Q2: "Why PostgreSQL for job queue instead of RabbitMQ/Celery?"**
**Answer:** We use PostgreSQL's `SELECT ... FOR UPDATE SKIP LOCKED` to implement a distributed job queue. This avoids adding another infrastructure component (RabbitMQ) and leverages the database we already need. It's simpler to operate and doesn't require managing a separate message broker.

**Follow-up:** "What are the limitations?"
**Answer:** PostgreSQL's job queue doesn't support advanced features like dead letter queues, priority queues, or message TTL out of the box. For our use case (simple training job queue), it's sufficient.

---

**Q3: "Why MLflow for experiment tracking?"**
**Answer:** MLflow is an open-source, well-maintained tool with good Python integration. It handles parameter tracking, metric logging, and model versioning out of the box. Alternatives include Weights & Biases (cloud-only), Kubeflow (complex), or custom solutions (reinventing the wheel).

**Follow-up:** "Why not use MLflow's model registry?"
**Answer:** We store models in MinIO (S3-compatible) instead of MLflow's artifact store. This gives us more control over model storage and avoids MLflow's storage limitations.

---

**Q4: "Why MinIO instead of AWS S3?"**
**Answer:** MinIO is self-hosted, which means no cloud costs and full control over data. For a student project, this is more practical than setting up AWS accounts and dealing with billing. The API is S3-compatible, so switching to AWS later would require minimal changes.

**Follow-up:** "What about data durability?"
**Answer:** MinIO doesn't replicate data by default, so it's less durable than S3. For production, we'd use S3 or run MinIO with erasure coding.

---

### 3.2 Functionality Questions

**Q5: "Does the full lifecycle work? Can you demonstrate?"**
**Answer:** Yes. The flow is:
1. `POST /datasets` — Upload CSV to MinIO + register
2. `POST /train` — Create training job
3. Worker polls for pending jobs, downloads dataset from MinIO, runs training pipeline, logs to MLflow, saves model to MinIO
4. `POST /predict` — Fetch model from MLflow/MinIO, run inference, log to PostgreSQL

**Follow-up:** "What happens if MLflow is down during inference?"
**Answer:** The inference service has retry logic (`fetch_model_with_retry`) that retries 7 times with exponential backoff. If MLflow stays down, it returns 503 Service Unavailable.

---

**Q6: "How do you handle model versioning?"**
**Answer:** Models are versioned using the format `{job_id}_{dataset_id}_{mlflow_run_id}`. This version string is stored in the `trained_models` table and used by the inference service to fetch the correct model. MLflow also tracks versions internally.

**Follow-up:** "How do you promote a model to production?"
**Answer:** Currently, we don't have a promote endpoint. This is a known gap (see Section 1.2). The model version is determined by the latest training job.

---

**Q7: "How does the system handle failures?"**
**Answer:**
- **Training failure:** Worker catches exceptions, updates job status to "failed", and continues to the next job
- **MinIO failure:** Retry logic with exponential backoff (7 retries)
- **MLflow failure:** Retry logic with exponential backoff
- **PostgreSQL failure:** Inference service continues without prediction logging (DB pool is optional)
- **Worker crash:** `recover_stuck_jobs()` should reset stale jobs, but it has a bug (resets ALL running jobs)

**Follow-up:** "What about the `recover_stuck_jobs()` bug?"
**Answer:** It's a known issue. The function currently resets ALL running jobs, but it should only reset jobs that have been running for more than 30 minutes. This is scheduled for fix.

---

**Q8: "How do you detect data drift?"**
**Answer:** We don't currently implement drift detection. The dashboard shows prediction logs, but there's no automated analysis. This is a planned feature for future sprints.

**Follow-up:** "What would you use to detect drift?"
**Answer:** We could use statistical tests (KS-test, PSI) or ML-based approaches (Evidently AI, Alibi Detect). We'd compare the distribution of production data against the training data distribution.

---

### 3.3 Testing Questions

**Q9: "What's your test coverage?"**
**Answer:** We have 53 unit/service tests passing and 11 integration tests passing. The tests cover:
- Orchestrator endpoints (train, jobs, datasets)
- Training worker (job processing, DB operations, retry logic)
- Inference service (prediction, model reload, concurrent requests)
- Full lifecycle (upload → train → inference)
- Failure scenarios (MinIO down, MLflow down, DB down)

**Follow-up:** "What's not covered?"
**Answer:** Integration tests don't run in CI (they require Docker containers). We also don't have tests for the monitoring dashboard or the monitoring service.

---

**Q10: "How do you validate the system works end-to-end?"**
**Answer:** We have integration tests that start Docker Compose, upload a dataset, trigger training, wait for completion, and verify predictions. These tests run locally with `pytest tests/integration/`.

**Follow-up:** "Why don't integration tests run in CI?"
**Answer:** CI runs in GitHub Actions which doesn't have Docker-in-Docker support. We'd need to use `act` locally or set up a self-hosted runner with Docker support.

---

### 3.4 Design Questions

**Q11: "Why does the dashboard query the database directly instead of using the orchestrator API?"**
**Answer:** The dashboard is read-only and needs to query multiple tables (jobs, models, prediction_logs). Querying the database directly is simpler and more efficient than making multiple API calls. For production, we'd add a read-only API endpoint on the orchestrator.

**Follow-up:** "Isn't this a violation of separation of concerns?"
**Answer:** Yes, it is. The dashboard should use the orchestrator API. However, for a student project, direct DB access is acceptable and simplifies the architecture.

---

**Q12: "Why use subprocess.run() for training instead of async?"**
**Answer:** Training is CPU-intensive and blocking. Using `subprocess.run()` allows us to run the training script in a separate OS process, which doesn't block the async worker loop. If training crashes, the worker stays alive and can process the next job.

**Follow-up:** "What if training uses too much memory?"
**Answer:** We've added Docker resource limits (1GB RAM for training-worker) to prevent OOM crashes. We could also use `resource` module to set limits within Python.

---

**Q13: "Why is the dataset_registry in-memory instead of database-backed?"**
**Answer:** It's a design decision by the original author. In-memory storage is simpler and sufficient for a single-node deployment. For production, we'd persist it to the database or use a distributed cache (Redis).

**Follow-up:** "What happens on restart?"
**Answer:** The in-memory registry is lost. Users would need to re-upload datasets. This is a known limitation.

---

## 4. QUESTIONS WE SHOULD ASK TA

### 4.1 Clarifications Needed

**Q1: "Does the project require a written report, or is the README sufficient?"**
**Context:** The evaluation schema mentions "written report" but we only have README, TEST_FIXES, MERGE_LOG. No formal report exists.

**Why ask:** If a report is required, we need to write one ASAP. If README is sufficient, we can focus on other gaps.

---

**Q2: "What's the expected depth of the 'experimental approach'?"**
**Context:** The brief says "students are expected to validate both the correctness of the system and the effectiveness of the proposed solution through a structured experimental approach." We have tests, but no ablation studies, no performance benchmarks, no comparison with alternatives.

**Why ask:** We need to know if we need to run experiments (e.g., compare different training pipelines, measure inference latency under load, etc.).

---

**Q3: "Is it acceptable that monitoring-service is a skeleton?"**
**Context:** The monitoring-service only has `/health`. The actual monitoring work is in the dashboard (Streamlit). The brief mentions "performance monitoring" as a requirement.

**Why ask:** If monitoring-service is required to be functional, we need to implement it. If dashboard is sufficient, we can document this decision.

---

**Q4: "What's the minimum viable demo for the presentation?"**
**Context:** We have 30% of features missing (data ingestion, deployment, retraining). We need to prioritize what to demo.

**Why ask:** We should focus on demonstrating the core flow (upload → train → predict) and be honest about what's missing.

---

**Q5: "Are ADRs required, or is the README sufficient for design decisions?"**
**Context:** The evaluation mentions "architecture decisions" but we have no ADRs. We have logs_contract.md which is a partial ADR.

**Why ask:** If ADRs are required, we need to write them. If README is sufficient, we can document decisions there.

---

### 4.2 Scope Clarifications

**Q6: "Does 'data ingestion' mean just uploading files, or does it include validation/transformation?"**
**Context:** We have `POST /datasets` which uploads CSV to MinIO. We don't have data validation, transformation, or versioning.

**Why ask:** If ingestion means more than upload, we need to implement validation/transformation.

---

**Q7: "Does 'model deployment' mean having a promote endpoint, or is saving to MinIO sufficient?"**
**Context:** We save models to MinIO but don't have a promote endpoint or production model tracking.

**Why ask:** If deployment requires promote/rollback, we need to implement it.

---

**Q8: "Does 'retraining' mean automated retraining on drift, or is manual retraining sufficient?"**
**Context:** We have manual retraining (POST /train) but no automated retraining on drift.

**Why ask:** If automated retraining is required, we need to implement drift detection.

---

**Q9: "Is 'distributed' meaning multiple containers, or does it require Kubernetes?"**
**Context:** We use Docker Compose with 8 containers. We don't use Kubernetes.

**Why ask:** If Kubernetes is required, we need to rewrite the deployment. If Docker Compose is sufficient, we're good.

---

**Q10: "Does 'robustness under failures' mean we need circuit breakers, or is retry logic sufficient?"**
**Context:** We have retry logic but no circuit breakers, no graceful shutdown, no health checks.

**Why ask:** If robustness requires circuit breakers, we need to implement them.

---

## 5. PRIORITY ACTION ITEMS

### 🔴 Critical (Before Presentation)
| Item | Effort | Owner |
|------|--------|-------|
| Write project report (README + ADRs) | 4 hours | All |
| Prepare demo script (upload → train → predict) | 2 hours | Andrei |
| Prepare answers to Q1-Q13 (TA questions) | 2 hours | All |
| Fix `recover_stuck_jobs()` bug | 1 hour | Danil |

### 🟡 High (If Time Permits)
| Item | Effort | Owner |
|------|--------|-------|
| Implement `POST /models/promote` | 2 hours | Danil |
| Add health checks to docker-compose | 1 hour | Andrei |
| Add service logging (use shared_logging_utils) | 4 hours | All |
| Write ADRs (5-10) | 3 hours | Julia |

### 🟢 Medium (Nice to Have)
| Item | Effort | Owner |
|------|--------|-------|
| Implement data validation | 2 hours | Dasha |
| Add CI integration tests | 2 hours | Andrei |
| Implement drift detection | 4 hours | Dasha |
| Add graceful shutdown | 2 hours | All |

---

## 6. DEMO SCRIPT (Suggested Flow)

1. **Start services:** `docker-compose up -d`
2. **Verify all services running:** `docker ps`
3. **Upload dataset:** `curl -X POST http://localhost:8000/datasets -F "file=@seeds/sample_dataset.csv"`
4. **Trigger training:** `curl -X POST "http://localhost:8000/train?dataset_name=sample&dataset_id=1"`
5. **Check job status:** `curl http://localhost:8000/jobs/1`
6. **Wait for completion:** Check job status until "succeeded"
7. **Make prediction:** `curl -X POST "http://localhost:8001/predict?model_name=logistic_regression&model_version=1_1_run_123" -H "Content-Type: application/json" -d '{"age": 34, "monthly_spend": 120.5, "tenure_months": 18, "income": 50000, "credit_score": 700}'`
8. **Show dashboard:** Open `http://localhost:8501`
9. **Show MLflow UI:** Open `http://localhost:5000`
10. **Show test results:** `pytest tests/ --ignore=tests/integration/`

---

## 7. WHAT TO BE HONEST ABOUT

When TA asks about missing features, be honest and explain:

1. **"We implemented the core flow (upload → train → predict) and have tests for it. The missing features (deployment, retraining, drift detection) are planned for future sprints."**

2. **"We prioritized getting the core pipeline working end-to-end over implementing every feature. This is a common approach in agile development."**

3. **"The architecture is designed to support all required features. The missing parts are implementation gaps, not design flaws."**

4. **"We have a detailed merge log (MERGE_LOG.md) and test fixes documentation (TEST_FIXES.md) that show the complexity of integrating 5 feature branches."**

---

*Generated: Apr 20, 2026*  
*Branch: feature/week2-integration*  
*Next review: Wednesday (Apr 22)*

# Merge Log — `feature/week2-integration`

**Created:** Apr 20, 2026  
**Base Branch:** `origin/dev` (commit `427b695`, Apr 16, 2026)  
**Total Changes:** 72 files, +3,653 insertions, −152 deletions

---

## Merge Summary

This branch merges all Week 1 and Week 2 feature work into a single unified codebase. Every service, test, and migration from the individual feature branches is now present on this branch.

---

## Step-by-Step Merge Record

### Step 1: Merge `origin/training-worker-week2` (Danil Kudinov)

**Command:** `git merge origin/training-worker-week2 --no-edit -X theirs`

**Files merged (14 files, +300 / −35):**
- `services/training_worker/` — Complete worker v2: `app.py`, `worker.py`, `db.py`, `minio_client.py`, `retry.py`, `schemas.py`, `Dockerfile`
- `tests/services/training_worker/` — 7 test files: `test_worker.py`, `test_db.py`, `test_concurrency.py`, `test_retry.py`, `test_timeout.py`, `test_worker_crash.py`, `__init__.py`
- Infrastructure: `DESCRIPTION.md`, `PROBLEMS_FOUND.md`, `FIXES_APPLIED.md`, `QUICKSTART.md`, `.env.example`, `Makefile`, `README.md`, `docker-compose.yml`, `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, `.secrets.baseline`, `setup.cfg`, `docs/logs_contract.md`, `migrations/tables_for_worker.sql`, `pipelines/first_ml_baseline/train.py`, `pipelines/first_ml_baseline/requirements.txt`

**Why this first:** Danil's branch is the most comprehensive — it includes monitoring-service updates, CI fixes, docker-compose, and all infrastructure. All other Week 2 branches are based on this state.

**Conflicts resolved:** None (used `-X theirs` strategy, took Week 2 versions for all overlapping files)

**Key decisions:**
- Kept `services/training_worker/` (underscore) directory — this is the correct naming
- Kept `retry.py` — provides `sync_retry` and `async_retry` decorators used by worker

---

### Step 2: Merge `origin/feature/inference-service-week2` (AraNge / Lesha)

**Command:** `git merge origin/feature/inference-service-week2 --no-edit -X theirs`

**Files merged (10 files, +460 / −95):**
- `services/inference-service/` — Complete inference v2: `app.py` (140 lines), `load_model.py`, `minio_client.py`, `predictor.py`, `schemas.py`, `Dockerfile`, `README.md`, `README_WEEK_2.md`
- `tests/services/inference-service/` — 8 test files: `test_predict_endpoint.py`, `test_reload.py`, `test_reload_endpoint.py`, `test_reload_concurrency.py`, `test_reload_endpoint_concurrent.py`, `test_concurrent_requests.py`, `test_model_fetch_retry.py`, `test_load.py`, `test_predictor.py`
- `services/orchestrator/` — Updated `app.py` (67 lines), `Dockerfile`, `requirements.txt`
- `services/monitoring-service/` — Updated `Dockerfile`
- `services/training_worker/` — Updated files from inference branch
- Infrastructure: `docker-compose.yml`, `.github/workflows/ci.yml`, `README.md`, `.actrc`

**Why this second:** Lesha's branch is also a superset that includes monitoring-service and orchestrator updates. Merging after training-worker ensures the baseline is correct.

**Conflicts resolved:** All in infrastructure files (docker-compose, CI, README) — resolved with `-X theirs` (Week 2 version wins)

**Key decisions:**
- Kept inference-service `app.py` from Week 2 (140 lines, MinIO-based, tenacity retry, process pool)
- Kept `tenacity` in requirements.txt (used by `load_model.py` for retry logic)
- Kept `cachetools` in requirements.txt (used for LRU byte cache)

---

### Step 3: Merge `origin/feat/monitoring-dashboard` (laschien / Ahmed)

**Command:** `git merge origin/feat/monitoring-dashboard --no-edit -X theirs`

**Files merged (11 files, +254 / −6):**
- `services/monitoring-dashboard/` — Complete Streamlit dashboard: `app.py` (66 lines), `db.py`, `repository.py`, `ui.py`, `Dockerfile`, `requirements.txt`, `.dockerignore`, `README.md`
- `services/inference-service/Dockerfile` — Updated
- `services/monitoring-service/Dockerfile` — Updated
- `services/orchestrator/Dockerfile` — Updated
- Infrastructure: `docker-compose.yml`, `.github/workflows/ci.yml`, `README.md`, `.actrc`

**Why this third:** Ahmed's dashboard is a new directory (`monitoring-dashboard/`) that doesn't conflict with existing services. It also touches infrastructure files.

**Conflicts resolved:** All in infrastructure files — resolved with `-X theirs`

**Key decisions:**
- Kept both `monitoring-service/` (skeleton FastAPI, port 8002) and `monitoring-dashboard/` (Streamlit, port 8501)
- Dashboard uses direct PostgreSQL access (read-only) — acceptable per project spec

---

### Step 4: Cherry-pick Orchestrator from `feature/dataset-upload-flow` (Daria Galushko)

**Command:** Manual file copy (not a merge — Liza's v1 on dev and v2 on dataset-upload-flow are divergent)

**Files copied:**
- `services/orchestrator/app.py` — Replaced v1 (67 lines) with v2 (120 lines)
- `services/orchestrator/dataset_service.py` — New file (157 lines): in-memory dataset registry + MinIO upload client
- `services/orchestrator/requirements.txt` — Added `minio` and `python-multipart`

**Why cherry-pick instead of merge:** Liza's v1 (`feature/inference-service-db`) and v2 (`feature/dataset-upload-flow`) have divergent orchestrator code. A merge would create massive conflicts. Cherry-picking the complete v2 `app.py` is cleaner.

**New endpoints added:**
- `POST /datasets` — Upload CSV dataset to MinIO + register
- `GET /datasets/{dataset_id}` — Get dataset info

**Existing endpoints preserved:**
- `GET /health`
- `POST /train`
- `GET /jobs/{job_id}`

**Key decisions:**
- Kept v2's approach: in-memory `DatasetRegistry` (not DB-backed) — matches Dasha's implementation
- Added `minio` dependency for dataset upload to object storage
- Added `python-multipart` for FastAPI file upload handling

---

### Step 5: Merge `feature/integration-tests` (Andrei)

**Command:** `git merge feature/integration-tests --no-edit -X theirs`

**Files merged (32 files, +2,376 / −1):**
- `tests/integration/` — 4 integration test files: `test_full_lifecycle.py` (371 lines), `test_failure_scenarios.py` (296 lines), `test_idempotency.py` (55 lines), `test_degraded_mode.py` (36 lines), `conftest.py` (177 lines)
- `tests/unit/` — 8 unit test files across all services
- `tests/services/inference-service/` — Additional API and predictor tests
- `pyproject.toml` — Pytest configuration
- `tests/README.md` — Test documentation

**Why this fifth:** Tests need to be compatible with all service code. Merging last ensures tests see the final state of all services.

**Conflicts resolved:** Minimal — some test files had path changes (tests moved from `tests/` to `tests/services/`). Resolved with `-X theirs`.

**Test coverage after merge:**
- 29 test files total
- 8 unit tests (across all services)
- 16 service tests (inference, training worker)
- 4 integration tests (lifecycle, failure scenarios, idempotency, degraded mode)

---

### Step 6: Add Missing Migration — `migrations/pred_logs.sql`

**Source:** `feature/inference-service-db:migrations/pred_logs.sql` (Liza v1)

**Why needed:** The inference service writes prediction logs to the `prediction_logs` table, and the dashboard reads from it. This table was defined in Liza's v1 branch but never made it to dev or any Week 2 branch.

**Table schema:**
- `prediction_logs` — UUID-based, stores prediction requests with input data, predictions, latency, timestamps
- Indexed on `request_id`, `model_version`, `created_at`

---

### Step 7: Fix `docker-compose.yml`

**Changes made:**
1. **Added `monitoring-dashboard` service** — Streamlit app on port 8501, depends on postgres + orchestrator
2. **Added `minio` to orchestrator's `depends_on`** — Dataset upload requires MinIO
3. **Port mapping:** `8501:8501` (host:container) for dashboard

**Final service list (7 services):**
| Service | Port | Purpose |
|---|---|---|
| postgres | 5432 | Database |
| minio | 9000/9001 | Object storage (API/console) |
| mlflow | 5000 | Experiment tracking |
| orchestrator | 8000 | Control plane |
| training-worker | — | Async training execution |
| inference-service | 8001 | Prediction serving |
| monitoring-service | 8002 | Health check (skeleton) |
| monitoring-dashboard | 8501 | Streamlit dashboard |

---

### Step 8: Fix `services/inference-service/requirements.txt`

**Problem:** `pandas` and `uvicorn` were listed twice (merge artifact).

**Fix:** Removed duplicates, keeping single entries for all 13 dependencies.

---

## Verification Results

### Service Files — All Present ✅

| Service | Files | Endpoints |
|---|---|---|
| `services/orchestrator/` | `app.py` (120 lines), `dataset_service.py` (157 lines), `Dockerfile`, `requirements.txt` | `GET /health`, `POST /train`, `GET /jobs/{id}`, `POST /datasets`, `GET /datasets/{id}` |
| `services/training_worker/` | `app.py`, `worker.py`, `db.py`, `minio_client.py`, `retry.py`, `schemas.py`, `Dockerfile` | `GET /health` (worker loop runs in background) |
| `services/inference-service/` | `app.py` (140 lines), `load_model.py`, `minio_client.py`, `predictor.py`, `schemas.py`, `Dockerfile` | `GET /health`, `POST /predict`, `POST /reload` |
| `services/monitoring-service/` | `app.py` (skeleton), `Dockerfile` | `GET /health` |
| `services/monitoring-dashboard/` | `app.py`, `db.py`, `repository.py`, `ui.py`, `Dockerfile` | Streamlit (port 8501) |

### Migrations — All Present ✅

| File | Tables |
|---|---|
| `migrations/tables_for_worker.sql` | `jobs`, `trained_models` |
| `migrations/pred_logs.sql` | `prediction_logs` |

### Tests — All Present ✅

| Category | Count | Files |
|---|---|---|
| Unit | 8 | orchestrator, inference, monitoring, training_worker |
| Service | 16 | inference (10), training_worker (6) |
| Integration | 4 | lifecycle, failure scenarios, idempotency, degraded mode |
| **Total** | **29** | |

---

## Problems Spotted During Merge (Not Fixed)

### P0 — Critical (Known, Owned by Team)

| Problem | Branch Where It Exists | Why Not Fixed | Owner |
|---|---|---|---|
| **Orchestrator `POST /train` is not idempotent** — duplicate requests create duplicate jobs | `services/orchestrator/app.py` | Requires adding `client_id` header + unique constraint on DB. This is a logic change that affects the API contract. Danil owns this (scheduled Apr 22). | Danil |
| **`recover_stuck_jobs()` resets ALL running jobs** — should only reset stale jobs (>30 min) | `services/training_worker/worker.py` | Bug in job recovery logic. Requires adding timeout check. Danil owns this (scheduled Apr 20). | Danil |
| **No `datasets` / `prod_models` / `deployments` DB tables** | `migrations/` | The `dataset_service.py` uses in-memory registry, not DB. Adding tables requires schema design decision (ADR). Julia owns docs/ADRs. | Julia |

### P1 — High

| Problem | Branch Where It Exists | Why Not Fixed | Owner |
|---|---|---|---|
| **No graceful shutdown** on any service | All services | Requires adding signal handlers (SIGTERM/SIGINT) and draining connections. Not a blocker for Week 2 demo. | All |
| **No docker resource limits** (RAM/CPU) | `docker-compose.yml` | Andrei owns this (scheduled Apr 21). Not a blocker for merge. | Andrei |
| **`monitoring-service/` is still a skeleton** (only `/health`) | `services/monitoring-service/app.py` | Ahmed's actual work is on `monitoring-dashboard/` (Streamlit). The `monitoring-service/` dir was a separate service that was never implemented. Not a blocker. | Ahmed |
| **No health checks in docker-compose** | `docker-compose.yml` | DevOps improvement — doesn't affect functionality. Can be added later. | Andrei |

### P2 — Medium

| Problem | Branch Where It Exists | Why Not Fixed |
|---|---|---|
| **Dashboard queries DB directly** instead of using orchestrator API | `services/monitoring-dashboard/db.py` | Architecture choice — dashboard is read-only, direct DB access is acceptable per spec. Changing would require API changes on orchestrator. |
| **Duplicate retry logic** — `minio_client.py` has its own retry + `retry.py` wraps it | `services/training_worker/minio_client.py` | Code smell, not a bug. Cleaning up requires refactoring, not merge work. |
| **Hardcoded paths** in worker (`/tmp/`, `pipelines/first_ml_baseline/train.py`) | `services/training_worker/worker.py` | Configuration concern, not a merge issue. Should be env vars, but not blocking. |
| **`dataset_registry` is in-memory only** — data lost on restart | `services/orchestrator/dataset_service.py` | Design decision by Dasha. Persisting to DB would require adding tables and migration. |
| **No CI integration tests** — only unit/service tests run in CI | `.github/workflows/ci.yml` | Integration tests need running Docker containers. Can be added as a separate CI step. |
| **No `.env` file in repo** (only `.env.example`) | Root | Intentional — secrets should not be committed. Users must create `.env` from `.env.example`. |

---

## Branch Mapping (Source → What Was Taken)

| Source Branch | Author | What Was Taken | What Was Left Out |
|---|---|---|---|
| `origin/training-worker-week2` | Danil | All service files, tests, docs, infrastructure | Nothing (full merge) |
| `origin/feature/inference-service-week2` | Lesha | All service files, tests, docs | Infrastructure conflicts resolved with "theirs" |
| `origin/feat/monitoring-dashboard` | Ahmed | Dashboard service files, Dockerfile | Infrastructure conflicts resolved with "theirs" |
| `feature/dataset-upload-flow` | Daria | `app.py`, `dataset_service.py`, `requirements.txt` only (cherry-pick) | Full merge would conflict with Liza's v1 |
| `feature/integration-tests` | Andrei | All test files, pytest config | Infrastructure conflicts resolved with "theirs" |
| `feature/inference-service-db` | Liza | `migrations/pred_logs.sql` only | Full code was superseded by Week 2 branches |

---

## Git History

```
* 2d6106a fix: add monitoring-dashboard to docker-compose and fix requirements
*   6a56c8a Merge branch 'feature/integration-tests' into feature/week2-integration
* | 0385c14 feat: add dataset upload endpoints to orchestrator (cherry-pick)
* |   763d22b Merge remote-tracking branch 'origin/feat/monitoring-dashboard'
* | |   52fb08d Merge remote-tracking branch 'origin/feature/inference-service-week2'
* | |   3057110 Merge remote-tracking branch 'origin/training-worker-week2'
* | |   427b695 Merge pull request #34 from Andrchest/fix/readme-act-setup
* | |   45061f9 Merge pull request #33 from Andrchest/integration/week-2-backbone
* | |   1feebc5 Merge pull request #10 from Andrchest/dev  (origin/main)
```

---

## Next Steps

1. **Run `docker-compose up`** — Verify all services start
2. **Run tests** — `pytest` (unit + service + integration)
3. **Test the happy path** — POST /datasets → POST /train → Worker completes → GET /predict
4. **Merge to `dev`** — Then to `main` for the demo

---

*This log was auto-generated during the merge process on Apr 20, 2026.*

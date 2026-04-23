# 1. Infrastructure Changes (docker-compose.yml)

### 🛠 Docker Logging Driver
Add logging driver to all services

```yaml
logging:
  driver: "loki"
  options:
    loki-url: "http://localhost:3100/loki/api/v1/push"
    loki-external-labels: "project=mlops,service=inference-service"
    loki-retries: "2"
    loki-max-backoff: "1000ms"
    loki-timeout: "1s"
```

### 📦 Persistent Storage (Volumes)
To ensure logs and dashboards persist across restarts, we configured volumes for Loki and Grafana:

```yaml
volumes:
  loki_data:    # Stores ingested logs
  grafana_data: # Stores dashboards and data source configs
```

Also mount shared/ folder to all services:

```yaml
volumes:
    - ./shared:/app/shared
```

### 🐍 Python Environment
Added 

`PYTHONUNBUFFERED: 1 `

to all Python services to ensure logs are flushed to the Docker driver immediately,
preventing log loss during crashes.

---

# 2. Application-Level Setup
All services use a custom JSONFormatter that captures:

* Standard fields: Timestamp, Level, Message, Logger name.
* Context fields: correlation_id (via asgi-correlation-id), service_name, and filename.
* Extra fields: Any dynamic data passed via logger.info(..., extra={"key": "value"}).
* Events can be used: Any event passed via logger.info(..., extra={"event": "value"}).

## 🔗 Correlation ID Injection

* FastAPI: Implemented via CorrelationIdMiddleware.
* Streamlit: Manual injection into contextvars during session start to track UI interactions.

---
# 3. How to Track Requests (Tracing Samples)## Sample 1: Manual Trigger with curl
To simulate a request and track it through the stack, send a custom header:

```bash
curl -X GET "http://localhost:8001/health" -H "X-Correlation-ID: debug-trace-101"
```

Open Grafana Explore and use the following LogQL queries:

* View all logs for a specific request:

{project="mlops"} |= "debug-trace-101"

* View only errors for the Training Worker:

{service="training-worker"} | json | level="ERROR"

* Extract JSON fields for analysis:

{service="inference-service"} | json | line_format "{{.message}} (ID: {{.correlation_id}})"

---

# Some of Events used

## Orchestrator Events

| Event | Level | Description |
|---|---|---|
| startup_initiated | INFO | Orchestrator started. |
| train_request_received | INFO | A training request was received. |
| job_created_in_db | INFO | The task was successfully written to the database. |
| job_creation_failed | ERROR | Error inserting the task into the database. |
| status_check_requested | INFO | Request the status of a specific task. |
| job_not_found | WARNING | Attempt to check the status of a non-existent task. |


## Inference-Service Events

| Event | Level | Description |
|---|---|---|
| prediction_started | INFO | Request processing started. |
| prediction_completed | INFO | Prediction completed successfully. |
| model_fetch_failed | WARNING | Model not found in storage (404). |
| infrastructure_error | ERROR | Error communicating with MinIO or network (503). |
| prediction_runtime_error | CRITICAL | Unexpected failure in model logic (500). |
| reload_started | INFO | The pool hot reload process has started. |
| reload_success | INFO | The process pool was successfully updated. |
| cache_cleared | INFO | The model byte cache was successfully cleared. |
| startup / shutdown | INFO | The application lifecycle. |


## Training Worker Events

| Event | Level | Description |
|---|---|---|
| db_pool_creating | INFO | Starting the process of creating a database connection pool. |
| db_pool_ready | INFO | The pool was successfully created, the database is available. |
| worker_task_start | INFO | The background training task (worker_loop) has started. |
| shutdown_initiated | INFO | The service received a signal to stop. |
| db_pool_closed | INFO | The database connection pool was successfully closed. |
| job_polled | INFO | New task successfully retrieved from the database. |
| dataset_download_start | INFO | Dataset download started from storage. |
| dataset_ready | INFO | Dataset downloaded, moved, and ready for processing. |
| training_subprocess_start | INFO | Starting external Python training script. |
| training_subprocess_failed | ERROR | The training script exited with a non-zero code. |
| pipeline_warnings | WARNING | Training was successful, but there are log entries in stderr. |
| minio_upload_start | INFO | Starting uploading the final model to MinIO. |
| job_success | INFO | The task has been fully completed, and the database data has been updated. |
| job_failed | ERROR | An unexpected error occurred while processing the task. |
| status_update_error | ERROR | An error occurred while attempting to write the failed status to the database. |
| worker_loop_error | ERROR | A critical error occurred in the main loop (database polling). | 

## Monitoring Dashboard Events

| Event | Level | Description |
|---|---|---|
| dashboard_started | INFO | Script initialized and running. |
| db_health_check_failed | ERROR | Failed to connect to the database. |
| db_health_check_passed | DEBUG | Successfully confirmed database availability. |
| fetch_jobs_success | DEBUG | Successfully retrieved the total number of jobs (metric). |
| fetch_jobs_failed | WARNING | Error while querying job data aggregation. |
| fetch_models_success | DEBUG | Successfully retrieved the total number of models (metric). |
| fetch_models_failed | WARNING | Error requesting data aggregation by models. |
| jobs_page_loaded | INFO | The list of all jobs was successfully loaded and displayed. |
| jobs_page_failed | ERROR | Error loading the detailed job table. |
| models_page_loaded | INFO | The list of trained models was successfully loaded. |
| models_page_failed | ERROR | Error loading the detailed model table. |

## Configuration
The logger's behavior is controlled via environment variables:

* LOG_LEVEL: Verbosity level (DEBUG, INFO, ERROR). Defaults to INFO.
* SERVICE_NAME: The service name to display in the service field.
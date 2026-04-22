## Orchestrator Events

| Event | Level | Description | Extra Data |
|---|---|---|---|
| startup_initiated | INFO | Orchestrator started. | - |
| train_request_received | INFO | A training request was received. | dataset_name, request_id |
| job_created_in_db | INFO | The task was successfully written to the database. | job_id, request_id |
| job_creation_failed | ERROR | Error inserting the task into the database. | error, request_id |
| status_check_requested | INFO | Request the status of a specific task. | job_id |
| job_not_found | WARNING | Attempt to check the status of a non-existent task. | job_id |


## Inference-Service Events

| Event | Level | Description | Additional data |
|---|---|---|---|
| prediction_started | INFO | Request processing started. | model_name, input_data |
| prediction_completed | INFO | Prediction completed successfully. | latency_ms, score, label |
| model_fetch_failed | WARNING | Model not found in storage (404). | error_type, model_version |
| infrastructure_error | ERROR | Error communicating with MinIO or network (503). | error_detail, exc_info |
| prediction_runtime_error | CRITICAL | Unexpected failure in model logic (500). | exc_info, input_snapshot |
| reload_started | INFO | The pool hot reload process has started. | request_id |
| reload_success | INFO | The process pool was successfully updated. | workers_count |
| cache_cleared | INFO | The model byte cache was successfully cleared. | previous_size |
| startup / shutdown | INFO | The application lifecycle. | max_workers |


## Training Worker Events

| Event | Level | Description | Extra Data Fields |
|---|---|---|---|
| db_pool_creating | INFO | Starting the process of creating a database connection pool. | - |
| db_pool_ready | INFO | The pool was successfully created, the database is available. | - |
| worker_task_start | INFO | The background training task (worker_loop) has started. | - |
| shutdown_initiated | INFO | The service received a signal to stop. | - |
| db_pool_closed | INFO | The database connection pool was successfully closed. | - |
| job_polled | INFO | New task successfully retrieved from the database. | job_id, dataset_id |
| dataset_download_start | INFO | Dataset download started from storage. | target_path, dataset_name |
| dataset_ready | INFO | Dataset downloaded, moved, and ready for processing. | csv_path |
| training_subprocess_start | INFO | Starting external Python training script. | pipeline |
| training_subprocess_failed | ERROR | The training script exited with a non-zero code. | stderr, exit_code |
| pipeline_warnings | WARNING | Training was successful, but there are log entries in stderr. | stderr |
| minio_upload_start | INFO | Starting uploading the final model to MinIO. | model_version |
| job_success | INFO | The task has been fully completed, and the database data has been updated. | metrics, model_version |
| job_failed | ERROR | An unexpected error occurred while processing the task. | exc_info, job_id |
| status_update_error | ERROR | An error occurred while attempting to write the failed status to the database. | job_id |
| worker_loop_error | ERROR | A critical error occurred in the main loop (database polling). | exc_info |

## Monitoring Dashboard Events

| Event | Level | Description | Additional data |
|---|---|---|---|
| dashboard_started | INFO | Script initialized and running. | - |
| db_health_check_failed | ERROR | Failed to connect to the database. | error |
| db_health_check_passed | DEBUG | Successfully confirmed database availability. | - |
| fetch_jobs_success | DEBUG | Successfully retrieved the total number of jobs (metric). | - |
| fetch_jobs_failed | WARNING | Error while querying job data aggregation. | - |
| fetch_models_success | DEBUG | Successfully retrieved the total number of models (metric). | - |
| fetch_models_failed | WARNING | Error requesting data aggregation by models. | - |
| jobs_page_loaded | INFO | The list of all jobs was successfully loaded and displayed. | count (number of rows) |
| jobs_page_failed | ERROR | Error loading the detailed job table. | error |
| models_page_loaded | INFO | The list of trained models was successfully loaded. | count (number of rows) |
| models_page_failed | ERROR | Error loading the detailed model table. | error |

## Configuration
The logger's behavior is controlled via environment variables:

* LOG_LEVEL: Verbosity level (DEBUG, INFO, ERROR). Defaults to INFO.
* SERVICE_NAME: The service name to display in the service field.
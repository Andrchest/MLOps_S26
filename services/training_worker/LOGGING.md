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
# Logging

## List of used events (event)

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

## Configuration
The logger's behavior is controlled via environment variables:

* LOG_LEVEL: Verbosity level (DEBUG, INFO, ERROR). Defaults to INFO.
* SERVICE_NAME: The service name to display in the service field.
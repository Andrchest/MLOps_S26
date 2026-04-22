## Orchestrator Events

| Event | Level | Description | Extra Data |
|---|---|---|---|
| startup_initiated | INFO | Orchestrator started. | - |
| train_request_received | INFO | A training request was received. | dataset_name, request_id |
| job_created_in_db | INFO | The task was successfully written to the database. | job_id, request_id |
| job_creation_failed | ERROR | Error inserting the task into the database. | error, request_id |
| status_check_requested | INFO | Request the status of a specific task. | job_id |
| job_not_found | WARNING | Attempt to check the status of a non-existent task. | job_id |
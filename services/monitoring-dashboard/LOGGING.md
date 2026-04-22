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
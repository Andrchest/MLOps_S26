## Description

## Week 1

This PR introduces a fully functional Training Worker service responsible for executing asynchronous ML training jobs as part of the distributed MLOps platform.

The worker integrates with:

- Postgres (job orchestration and state tracking)
- MinIO (dataset and model storage)
- MLflow (experiment tracking and model registry)
- Training pipeline (sklearn baseline model)

This implementation follows the system architecture defined in the project:

### Control Plane
Jobs are fetched atomically from Postgres using FOR UPDATE SKIP LOCKED
Job status is updated throughout lifecycle (Pending → Running → Persisting → Succeeded/Failed)
### Execution Plane
Worker executes training pipeline asynchronously
### Storage Plane
MinIO stores dataset and trained model artifacts
Postgres stores job state and model metadata
MLflow stores experiment tracking and model artifacts

### Implemented Features

1. #### Worker service
- Async worker loop with polling mechanism
- Periodic job fetching every POLL_INTERVAL

2. #### Job Management (Postgres)
- Atomic job acquisition
- Status updating

3. #### Dataset Handling (MinIO)
- Dataset is downloaded from MinIO bucket datasets
- Stored temporarily in /tmp/
- Passed to training pipeline as local file path

4. #### MLflow Integration
Worker extracts:

- run_id from pipeline stdout
- model parameters from MLflow run
- metrics from MLflow run
- model artifact via MLflow model registry

MLflow is used as source of truth for:

- model parameters
- metrics
- trained model artifact

5. #### Model Storage (MinIO)
- Trained model is loaded from MLflow
- Saved to MinIO bucket models
- Object path format: <model_name>/<job_id>\_<dataset_id>\_<run_id>.joblib

6. #### Metadata Persistence (Postgres)
Stored in table trained_models:

- job_id
- model_name
- model_version
- model_path (MinIO path)
- metrics (JSONB)
- parameters (JSONB)

### Implementation decisions

1. #### worker.py
- The dataset is stored in a temporary folder named tmp, which exists only inside the Docker container, before being transferred to the pipeline.
- The job_id is passed to the parser in order to later use it to find the record of the desired experiment.
- The model version is made up of job_id, dataset_id, and run_id for maximum informativeness and uniqueness.
- Before we start uploading the model to MinIO and its artifacts to the database, we determine the Pending job status in order to separate this important part of the program and avoid job freezes.

2. #### db.py
- In the get_job function, there is a line FOR UPDATE SKIP LOCKED in the request. This is done to avoid a race condition where two workers can take the same job.
- Combining UPDATE and SELECT allows this query to be atomic. 


## Week 2

- Added logging of the full work cycle of files (successes and errors)
- Added try/except in risky part of the worker_loop
- Added recovery after failures and retry-mechanisms for critical operations
- Added in db.py function recover_stuck_jobs to update the status of jobs that have the running status at the time of the start of the worker_loop
- Added in minio_client.py in function save_model_to_minio timeout and try/except for fput_object (it puts the model to minio)
- Added file retry.py where retry-mechanisms is implemented through the async_retry and sync_retry functions; This is necessary to highlight this mechanism and centralize it throughout the work cycle, as it is used for various functions
- In worker.py all the additions described above are reflected
- Added new unit test (concurrency, retry, timeouts, and worker crash)

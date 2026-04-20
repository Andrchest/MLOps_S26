# Service Documentation

## System Architecture
As part of Week 2, the architecture was simplified to improve performance and reliability:
* PostgreSQL Removal: The dependency on the Postgres database (both read and write) has been completely removed.

* MinIO-Centric: The service now directly relies on the MinIO client to load model artifacts.
* Graceful Degradation: The system is designed so that even if the storage client fails, it continues to function correctly, returning standardized errors (503 or 500) instead of crashing uncontrollably.


## Request Life Cycle
1. **Request Reception:** The API receives a prediction request.
2. **Model Fetching:** The service checks the local `LRUCache`. If the model is missing, it triggers a fetch from MinIO.
3. **Multi-process Handoff:** To maintain event loop responsiveness, synchronous I/O and CPU-bound tasks are handed off to executors.
4. **Response:** Results are returned with standardized status codes.

## 3. Reliability & Resiliency
The service is designed to be resilient against transient failures and provides clear feedback on error states.

### Retry Logic
Model fetching is wrapped in a `tenacity` retry loop with exponential backoff.
* **Strategy:** Exponential backoff starting at 2 seconds.
* **Max Attempts:** 3 attempts.
* **Benefit:** Automatically handles transient network glitches or temporary storage timeouts without failing the end-user request immediately.

### Graceful Failure Handling
The service explicitly maps storage and execution errors to appropriate HTTP responses to ensure predictable API behavior:
* **404 Not Found:** Returned when a requested model version is missing from Minio (specifically handling `NoSuchKey` errors).
* **503 Service Unavailable:** Returned if the Minio infrastructure is unreachable after all retry attempts have been exhausted.
* **500 Internal Server Error:** A catch-all for any other unexpected bugs, code errors, or exceptions during the prediction lifecycle to prevent leaking system internals.

---

## Technical Components Updates

### `load_model.py`
The bridge between storage and the API.
* **Retry Wrapper:** Implements `fetch_model_with_retry` using `tenacity` to ensure robust artifact retrieval.
* **Async Execution:** Uses `loop.run_in_executor` to wrap synchronous Minio client calls, keeping the event loop responsive during I/O.
* **Cache Management:** Implements the `LRUCache` to track and store frequently accessed model blobs.

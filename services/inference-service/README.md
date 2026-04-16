# ML Inference Service

A high-performance, stateless FastAPI service designed for serving Scikit-Learn models. This architecture utilizes **Minio** for model versioning and artifact storage, and a **Multi-Process Executor** to bypass Python's Global Interpreter Lock (GIL).

---

## System Architecture

The service is engineered to separate I/O-bound tasks from CPU-bound tasks to maximize throughput and maintain low latency.

### 1. Separation of Concerns
* **Asynchronous I/O:** FastAPI and `asyncio` manage web requests without blocking the main execution thread.
* **Parallel Execution:** CPU-intensive inference is offloaded to a `ProcessPoolExecutor`. This prevents heavy model computations from locking the event loop, ensuring the API remains responsive.

### 2. Tiered Caching Strategy
* **Main Process (Byte Cache):** Stores raw `.joblib` bytes in an `LRUCache`. This prevents redundant, high-latency network requests to Minio.
* **Worker Process (Model Cache):** Each individual worker process uses `functools.lru_cache` to store deserialized model objects in memory. This eliminates the CPU overhead of `joblib.load` for recurring requests.

### 3. Reliability & Resiliency
Here is the updated section regarding error handling to reflect the addition of the 500 status code for unexpected exceptions.

### Reliability & Resiliency
* **Retry Logic:** Model fetching is wrapped in a `tenacity` retry loop with exponential backoff (starting at 2s, up to 3 attempts). This handles transient network failures or storage timeouts automatically.
* **Graceful Failure Handling:** The service explicitly maps storage and execution errors to appropriate HTTP responses to ensure predictable API behavior:
    * **404 Not Found:** Returned when a requested model version is missing from Minio (specifically handling `NoSuchKey` errors).
    * **503 Service Unavailable:** Returned if the Minio infrastructure is unreachable after all retry attempts have been exhausted.
    * **500 Internal Server Error:** A catch-all for any other unexpected bugs, code errors, or exceptions during the prediction lifecycle to prevent leaking system internals.

---

### Request Life Cycle
1.  **Request:** User hits `/predict?model_name=X&model_version=Y` with a JSON payload.
2.  **Fetch:** `fetch_model_with_retry` checks the `LRUCache`. On a miss, it attempts to download the model from Minio, retrying up to 3 times on failure.
3.  **Handoff:** The main process sends model bytes and input data to an available worker in the `ProcessPoolExecutor`.
4.  **Inference:** The worker process deserializes the model (or hits its own internal `lru_cache`), performs the prediction, and returns the result.
5.  **Error Check:** If any stage fails, the service returns the mapped 404, 503, or 500 status code.
6.  **Response:** On success, the user receives a structured `PredictResponse` containing the prediction, model metadata, and latency metrics.

---

## File Overview

### `app.py`
The core application entry point.
* **Lifespan Management:** Manages the lifecycle of the `ProcessPoolExecutor`.
* **`/predict` Endpoint:** Coordinates the workflow: fetches models with retry logic, offloads inference, and handles error reporting.
* **`/reload` Endpoint:** Uses an `asyncio.Lock` to safely clear the byte cache and rotate the process pool, allowing for "hot-swapping" models while ensuring existing requests finish gracefully.

### `minio_client.py`
The dedicated storage utility.
* **Initialization:** Authenticates using `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, and `MINIO_ENDPOINT`.
* **Storage Logic:** A synchronous utility designed to pull objects from the `models` bucket.

### `load_model.py`
The bridge between storage and the API.
* **Retry Wrapper:** Implements `fetch_model_with_retry` using `tenacity` to ensure robust artifact retrieval.
* **Async Execution:** Uses `loop.run_in_executor` to wrap synchronous Minio client calls, keeping the event loop responsive during I/O.
* **Cache Management:** Implements the `LRUCache` to track and store frequently accessed model blobs.

### `predictor.py`
The ML execution logic (runs inside worker processes).
* **Deserialization:** Utilizes `joblib.load` with `io.BytesIO` to reconstruct Python objects from cached bytes.
* **Inference:** Converts input JSON into a Pandas DataFrame for compatibility with Scikit-Learn pipelines.

---

## Request Life Cycle

1.  **Request:** User hits `/predict?model_name=X&model_version=Y` with a JSON payload.
2.  **Fetch:** `fetch_model_with_retry` checks the `LRUCache`. on a miss, it attempts to download the model from Minio (retrying up to 3 times on failure).
3.  **Handoff:** The main process sends model bytes and input data to an available worker in the `ProcessPoolExecutor`.
4.  **Inference:** The worker process deserializes the model (or hits its own internal `lru_cache`), performs the prediction, and returns the result.
5.  **Response:** The user receives a structured `PredictResponse` containing the prediction, model metadata, and latency metrics.

---

## Configuration (Environment Variables)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `MINIO_ROOT_USER` | Access Key / Username | `minio` |
| `MINIO_ROOT_PASSWORD` | Secret Key / Password | `minio123` |
| `MINIO_ENDPOINT` | Minio Server Address | `minio:9000` |

---

## Deployment & Development

### 1. Requirements
Install dependencies including `fastapi`, `minio`, `tenacity`, `cachetools`, and `joblib`.

### 2. Testing
The service includes a comprehensive test suite covering:
* **Retry behavior:** verifying backoff and call counts without network delays.
* **Failure modes:** validating 404 and 503 HTTP status codes.
* **Concurrency:** testing parallel reloads and simultaneous prediction requests.

### 3. Execution
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
```
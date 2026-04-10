# ML Inference Service

A high-performance FastAPI service designed for serving Scikit-Learn models. This architecture utilizes **Minio** for model versioning, **PostgreSQL** for audit logging, and a **Multi-Process Executor** to bypass Python's Global Interpreter Lock (GIL).

---

## System Architecture

The service is engineered to separate I/O-bound tasks from CPU-bound tasks to maximize throughput and maintain low latency.

### 1. Separation of Concerns
* **Asynchronous I/O:** FastAPI and `asyncpg` manage web requests and database logging without blocking the main execution thread.
* **Parallel Execution:** CPU-intensive inference is offloaded to a `ProcessPoolExecutor`. This prevents heavy model computations from locking the event loop, ensuring the API remains responsive.

### 2. Tiered Caching Strategy
* **Main Process (Byte Cache):** Stores raw `.joblib` bytes in an `LRUCache`. This prevents redundant, high-latency network requests to Minio.
* **Worker Process (Model Cache):** Each individual worker process uses `functools.lru_cache` to store deserialized model objects in memory. This eliminates the CPU overhead of `joblib.load` for recurring requests.

---

## File Overview

### `app.py`
The core application entry point.
* **Lifespan Management:** Manages the lifecycle of the PostgreSQL connection pool and the `ProcessPoolExecutor`.
* **`/predict` Endpoint:** The primary workflow coordinator: triggers model byte fetching, offloads inference to the pool, and initiates background logging.
* **`/reload` Endpoint:** Clears the byte cache and rotates the process pool, allowing for "hot-swapping" models without a full service restart.

### `minio_client.py`
The dedicated storage utility.
* **Initialization:** Authenticates using `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`.
* **Storage Logic:** A synchronous utility designed to stream objects directly from the `models` bucket.

### `load_model.py`
The bridge between storage and the API.
* **Async Wrapper:** Uses `loop.run_in_executor` to wrap the synchronous Minio client, ensuring file downloads do not block the FastAPI event loop.
* **Cache Management:** Implements the `LRUCache` logic to track and store frequently accessed model blobs.

### `predictor.py`
The ML execution logic (runs inside worker processes).
* **Deserialization:** Utilizes `joblib.load` with `io.BytesIO` to reconstruct Python objects from cached bytes.
* **Inference:** Automatically converts input JSON into a Pandas DataFrame to ensure compatibility with standard Scikit-Learn pipelines.

---

## Request Life Cycle

1.  **Request:** User hits `/predict?model_name=X&model_version=Y` with a JSON payload.
2.  **Fetch:** `fetch_model_bytes` checks the `LRUCache`. On a miss, it downloads the model from Minio and populates the cache.
3.  **Handoff:** The main process pickles the model bytes and input data, sending them to an available worker in the `ProcessPoolExecutor`.
4.  **Inference:** The worker process deserializes the model (or hits its own `lru_cache`), performs the prediction, and returns the result.
5.  **Logging:** A FastAPI `BackgroundTask` (`save_log`) records the request metadata to PostgreSQL. The user receives the response immediately, before the log write is even finished.

---

## Configuration (Environment Variables)

Ensure these are configured in your `docker-compose.yml` or `.env` file.

| Variable | Description |
| :--- | :--- |
| `MINIO_ROOT_USER` | Access Key / Username |
| `MINIO_ROOT_PASSWORD` | Secret Key / Password |
| `POSTGRES_USER` | Database Username |
| `POSTGRES_PASSWORD` | Database Password |
| `POSTGRES_DB` | Database Name |

---

## Deployment

1.  **Install Requirements:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run with Uvicorn:**
    ```bash
    # We use 1 worker because the app manages its own ProcessPoolExecutor
    uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
    ```

---


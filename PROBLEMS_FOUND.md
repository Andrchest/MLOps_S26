# Problems Found in MLOps Codebase

## FIXED Issues

### 1. save_model_to_minio() - FIXED ✓
- Now has try/except + logging + file name detection

### 2. JSON metrics/parameters - FIXED ✓  
- Now uses json.dumps()


## Remaining Issues
```python
def save_model_to_minio(local_model_path, model_name, model_version):
    object_path = f"{model_name}/{model_version}.joblib"
    file_path = os.path.join(local_model_path, "model.pkl")
    minio_client.fput_object(...)  # No try/except!
    return object_path
```
**Problem:** If this hangs or fails, entire worker hangs with no error logged.

---

### 2. No error handling in `get_model_from_minio()`
**File:** `services/inference-service/minio_client.py:14`
```python
def get_model_from_minio(model_name: str, model_version: str, bucket: str = "models"):
    # No try/except!
```
**Problem:** If MinIO is down, inference service crashes.

---

### 3. No error handling in `_run_prediction()`
**File:** `services/inference-service/app.py:17`
```python
def _run_prediction(model_bytes: bytes, input_dict: dict):
    predictor = Predictor(model_bytes)
    return predictor.predict(input_dict)  # No try/except
```
**Problem:** If model.predict() fails, no graceful error handling.

---

## Missing Logging

### 4. `save_model_to_minio()` - No logging
- No log before starting upload
- No log on success
- No log on failure

### 5. `get_model_from_minio()` - No logging
- Can't debug when MinIO fails

---

## Weak Error Handling

### 6. `save_log()` uses print()
**File:** `services/inference-service/app.py:73`
```python
except Exception as e: print("FAILED: ", e)  # Not proper logging
```

---

## Missing Validation

### 7. `download_dataset()` - No validation
**File:** `services/training_worker/minio_client.py:33`
- Could overwrite existing files
- No validation of dataset_name

---

## Suggested Fixes

### Fix #1 - Add logging + error handling to save_model_to_minio():
```python
def save_model_to_minio(local_model_path, model_name, model_version):
    import logging
    object_path = f"{model_name}/{model_version}.joblib"
    file_path = os.path.join(local_model_path, "model.pkl")
    
    logging.info(f"Saving model to MinIO: {object_path}")
    try:
        minio_client.fput_object(
            bucket_name=MODELS_BUCKET,
            object_name=object_path,
            file_path=file_path,
        )
        logging.info(f"Model saved: {object_path}")
    except Exception as e:
        logging.error(f"Failed to save model: {e}")
        raise
    
    return object_path
```

### Fix #2 - Add logging + error handling to get_model_from_minio():
```python
def get_model_from_minio(model_name: str, model_version: str, bucket: str = "models"):
    import logging
    object_name = f"{model_name}/{model_version}.joblib"
    logging.info(f"Loading model from MinIO: {object_name}")
    
    try:
        response = minio_client.get_object(bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except Exception as e:
        logging.error(f"Failed to load model: {e}")
        raise
```

### Fix #3 - Add error handling to _run_prediction():
```python
def _run_prediction(model_bytes: bytes, input_dict: dict):
    import logging
    try:
        predictor = Predictor(model_bytes)
        return predictor.predict(input_dict)
    except Exception as e:
        logging.error(f"Prediction failed: {e}")
        raise
```

### Fix #6 - Replace print with logging in save_log():
```python
async def save_log(response: PredictResponse):
    import logging
    try:
        # existing code
        await conn.execute(query, ...)
    except Exception as e:
        logging.error(f"Failed to save prediction log: {e}")
```
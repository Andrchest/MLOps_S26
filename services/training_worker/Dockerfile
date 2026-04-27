FROM python:3.11-slim

WORKDIR /app

COPY services/training_worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/training_worker/ .
COPY services/drift_detection/ ./drift_detection/
COPY pipelines/ ./pipelines/

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8500"]

FROM python:3.11-slim

WORKDIR /app

COPY services/inference_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/inference_service/ ./services/inference_service/
COPY services/drift_detection/ ./services/drift_detection/
COPY shared/ ./shared/

ENV PYTHONPATH=/app

EXPOSE 8001
CMD ["uvicorn", "services.inference_service.app:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]

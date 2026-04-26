FROM python:3.11-slim

WORKDIR /app

COPY services/training_worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/training_worker/ ./services/training_worker/
COPY pipelines/ ./pipelines/

EXPOSE 8500
ENV PYTHONPATH=/app

CMD ["uvicorn", "services.training_worker.app:app", "--host", "0.0.0.0", "--port", "8500"]
FROM python:3.11-slim

WORKDIR /app

COPY services/monitoring_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/monitoring_service ./services/monitoring_service

EXPOSE 8002

ENV PYTHONPATH=/app
CMD ["uvicorn", "services.monitoring_service.app:app", "--host", "0.0.0.0", "--port", "8002"]

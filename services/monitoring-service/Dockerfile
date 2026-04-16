FROM python:3.11-slim

WORKDIR /app

COPY services/monitoring-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/monitoring-service/ .

EXPOSE 8002
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]

FROM python:3.11-slim

RUN pip install --no-cache-dir --default-timeout 300 mlflow==2.17.0 gunicorn

EXPOSE 5000

ENV PYTHONUNBUFFERED=1

CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000", "--backend-store-uri", "sqlite:////mlruns/mlflow.db", "--default-artifact-root", "/mlruns", "--workers", "1"]

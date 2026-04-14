FROM python:3.11-slim

WORKDIR /app

COPY services/training_worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/training_worker/ .
COPY pipelines/ ./pipelines/

CMD ["python", "app.py"]

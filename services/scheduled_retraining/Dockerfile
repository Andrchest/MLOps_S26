FROM python:3.11-slim

WORKDIR /app

COPY services/scheduled_retraining/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/scheduled_retraining/ .

ENV PYTHONPATH=/app

CMD ["python", "scheduled_retraining.py"]

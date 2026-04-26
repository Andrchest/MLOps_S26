FROM python:3.11-slim

WORKDIR /app

COPY services/orchestrator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/orchestrator/ ./services/orchestrator/
COPY shared/ ./shared/
COPY pipelines/ ./pipelines/

ENV PYTHONPATH=/app

CMD ["uvicorn", "services.orchestrator.app:app", "--host", "0.0.0.0", "--port", "8000"]

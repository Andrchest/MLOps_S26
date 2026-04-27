FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/monitoring-dashboard/ ./services/monitoring-dashboard/

EXPOSE 8501

ENV PYTHONPATH=/app

CMD ["streamlit", "run", "services/monitoring-dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501"]

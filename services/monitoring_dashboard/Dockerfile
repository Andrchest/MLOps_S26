
FROM python:3.11-slim

WORKDIR /app

COPY services/monitoring_dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/monitoring_dashboard/ ./services/monitoring_dashboard/

EXPOSE 8501

ENV PYTHONPATH=/app

CMD ["streamlit", "run", "services/monitoring_dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
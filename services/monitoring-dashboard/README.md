# Monitoring Dashboard

A read-only Streamlit dashboard for visibility into system state.

## Responsibilities

- Build dashboard UI in Streamlit
- Display job and model information from DB
- Keep DB access read-only
- Handle DB unavailability
- Handle partial and empty data

## Pages

- System Overview
- Jobs
- Models

## Technical decisions

- Implemented as a separate service under `services/`
- Uses direct read-only SQL queries
- Avoids service bypass and reads from the shared DB state
- Designed to degrade gracefully when the DB is unavailable or data is partial

## Local run

```bash
streamlit run app.py
```

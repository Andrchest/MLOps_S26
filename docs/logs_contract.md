# Monitoring Contract v0

## Purpose
This contract defines what data must be logged for each prediction request in Sprint 1.

The goal is to make predictions traceable and prepare the system for future monitoring, dashboarding, and model quality analysis.

## Logged Event
One `prediction_log` record must be created for every successful prediction request.

## Required Fields

| Field Name    | Type       | Required | Description |
|---------------|------------|----------|-------------|
| request_id    | string     | yes      | Unique request identifier |
| timestamp     | datetime   | yes      | Time when prediction was made |
| model_version | string     | yes      | Version of model used for prediction |
| model_name    | string     | yes      | Name of model used |
| input_data    | JSON       | yes      | Input payload sent to `/predict` |
| prediction    | JSON/value | yes      | Prediction result returned by model |
| latency_ms    | int/float  | yes      | Prediction latency in milliseconds |
| status        | string     | yes      | Request result: success / failed |

## Optional Fields

| Field Name      | Type   | Description |
|-----------------|--------|-------------|
| dataset_name    | string | Dataset associated with model |
| features_schema | JSON   | Schema/version of input features |
| error_message   | string | Error description if request failed |
| prediction_type | string | Classification / regression |

## Storage
For Sprint 1, prediction logs should be stored in the `prediction_logs` table in PostgreSQL.

## Example Log Record

```json
{
  "request_id": "req_001",
  "timestamp": "2026-04-06T14:20:31Z",
  "model_version": "churn_model_v1",
  "model_name": "customer_churn_model",
  "input_data": {
    "age": 34,
    "monthly_spend": 120.5,
    "tenure_months": 18
  },
  "prediction": {
    "label": 1,
    "score": 0.82
  },
  "latency_ms": 24,
  "status": "success"
}

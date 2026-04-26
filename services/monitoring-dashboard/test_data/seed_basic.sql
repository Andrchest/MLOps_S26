DELETE FROM prediction_logs;
DELETE FROM trained_models;
DELETE FROM jobs;

INSERT INTO jobs (job_id, dataset_name, dataset_id, status)
VALUES
(1, 'customer_churn.csv', 101, 'pending'),
(2, 'fraud_data.csv', 102, 'running'),
(3, 'retention_data.csv', 103, 'succeeded'),
(4, 'claims_data.csv', 104, 'failed');

INSERT INTO trained_models (
    job_id, model_name, model_version, model_path, metrics, parameters
)
VALUES
(
    3,
    'customer_churn_model',
    'v1.0.0',
    'customer_churn_model/v1.0.0.joblib',
    '{"accuracy": 0.91, "f1": 0.88}',
    '{"model_type": "random_forest", "n_estimators": 100}'
);

INSERT INTO prediction_logs (
    request_id, timestamp, model_version, model_name, input_data, prediction,
    latency_ms, status, dataset_name, prediction_type
)
VALUES
(
    'req_001',
    NOW() - INTERVAL '3 day',
    'v1.0.0',
    'customer_churn_model',
    '{"age": 34, "monthly_spend": 120.5, "tenure_months": 18}',
    '{"label": 1, "score": 0.82}',
    24.0,
    'success',
    'customer_churn.csv',
    'classification'
),
(
    'req_002',
    NOW() - INTERVAL '2 day',
    'v1.0.0',
    'customer_churn_model',
    '{"age": 41, "monthly_spend": 87.2, "tenure_months": 10}',
    '{"label": 0, "score": 0.21}',
    19.5,
    'success',
    'customer_churn.csv',
    'classification'
),
(
    'req_003',
    NOW() - INTERVAL '1 day',
    'v1.0.0',
    'customer_churn_model',
    '{"age": 29, "monthly_spend": 203.1, "tenure_months": 26}',
    '{"label": 1, "score": 0.91}',
    31.2,
    'failed',
    'customer_churn.csv',
    'classification'
),
(
    'req_004',
    NOW(),
    'v1.0.0',
    'customer_churn_model',
    '{"age": 37, "monthly_spend": 156.0, "tenure_months": 14}',
    '{"label": 1, "score": 0.73}',
    22.7,
    'success',
    'customer_churn.csv',
    'classification'
);

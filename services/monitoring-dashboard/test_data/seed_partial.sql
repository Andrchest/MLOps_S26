DELETE FROM prediction_logs;
DELETE FROM trained_models;
DELETE FROM jobs;

INSERT INTO jobs (job_id, dataset_name, dataset_id, status)
VALUES
(1, 'customer_churn.csv', 101, 'running'),
(2, 'fraud_data.csv', 102, 'failed');

INSERT INTO prediction_logs (
    request_id, timestamp, model_version, model_name, input_data, prediction,
    latency_ms, status, dataset_name, prediction_type, error_message
)
VALUES
(
    'req_partial_001',
    NOW() - INTERVAL '1 day',
    'unknown_model',
    'customer_churn_model',
    '{"age": 34, "monthly_spend": 120.5}',
    '{"label": 1}',
    27.0,
    'failed',
    'customer_churn.csv',
    'classification',
    'Model artifact not found'
);
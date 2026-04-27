CREATE TABLE IF NOT EXISTS jobs (
    job_id SERIAL PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    dataset_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    status TEXT DEFAULT 'pending'
);


CREATE TABLE IF NOT EXISTS trained_models (
    job_id INT NOT NULL REFERENCES jobs(job_id),
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    model_path TEXT NOT NULL,
    metrics JSONB NOT NULL,
    parameters JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT now(),
    UNIQUE (job_id, model_version),
    PRIMARY KEY (job_id, model_version)
);


CREATE TABLE IF NOT EXISTS prediction_logs (
    request_id TEXT PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_version TEXT NOT NULL,
    model_name TEXT NOT NULL,
    input_data JSONB NOT NULL,
    prediction JSONB NOT NULL,
    latency_ms DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL,
    dataset_name TEXT,
    features_schema JSONB,
    error_message TEXT,
    prediction_type TEXT
);
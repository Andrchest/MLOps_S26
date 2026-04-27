-- MLOps Platform Database Schema
-- Auto-applied on first postgres startup via docker-entrypoint-initdb.d

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Datasets table
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id INT NOT NULL PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    dataset_version TEXT DEFAULT '1',
    dataset_path TEXT,
    file_size_bytes BIGINT,
    checksum TEXT,
    format TEXT DEFAULT 'csv',
    status TEXT DEFAULT 'ready',
    created_at TIMESTAMP DEFAULT now()
);

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    job_id SERIAL PRIMARY KEY,
    dataset_id INT NOT NULL REFERENCES datasets(dataset_id),
    status TEXT DEFAULT 'pending',
    client_id TEXT,
    dataset_path TEXT,
    dataset_name TEXT,
    created_at TIMESTAMP DEFAULT now(),
    CONSTRAINT unique_client_id UNIQUE (client_id)
);

-- Trained models table
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

-- Production models registry
CREATE TABLE IF NOT EXISTS prod_models (
    model_name TEXT NOT NULL PRIMARY KEY,
    model_version TEXT
);

-- Deployments table
CREATE TABLE IF NOT EXISTS deployments (
    deployment_id SERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    deployed_at TIMESTAMP DEFAULT now(),
    deployed_by TEXT
);

-- Prediction logs table
CREATE TABLE IF NOT EXISTS prediction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    model_version TEXT NOT NULL,
    model_name TEXT NOT NULL,
    input_data JSONB NOT NULL,
    prediction JSONB NOT NULL,
    latency_ms INT CHECK (latency_ms >= 0),
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_request_id ON prediction_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_model_version ON prediction_logs(model_version);
CREATE INDEX IF NOT EXISTS idx_prediction_logs_created_at ON prediction_logs(created_at);

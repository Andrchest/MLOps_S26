CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE TABLE IF NOT EXISTS prediction_logs (
	id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,

    model_version TEXT NOT NULL,
    model_name TEXT NOT NULL,

    input_data JSONB NOT NULL,
    prediction JSONB NOT NULL,

    latency_ms INT CHECK (latency_ms>=0),
    status TEXT NOT NULL,

    created_at TIMESTAMP DEFAULT NOW()
);



CREATE INDEX idx_prediction_logs_request_id
ON prediction_logs(request_id);

CREATE INDEX idx_prediction_logs_model_version
ON prediction_logs(model_version);

CREATE INDEX idx_prediction_logs_created_at
ON prediction_logs(created_at);



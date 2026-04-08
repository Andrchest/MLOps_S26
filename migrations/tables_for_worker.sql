CREATE TABLE IF NOT EXISTS jobs (
    job_id SERIAL PRIMARY KEY,
    dataset JSONB NOT NULL,
    status TEXT DEFAULT 'pending'
);


CREATE TABLE  IF NOT EXISTS trained_models (
    model_id SERIAL PRIMARY KEY,
    job_id INT REFERENCES jobs(job_id),
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    model BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);
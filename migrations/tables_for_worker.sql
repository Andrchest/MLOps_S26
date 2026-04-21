CREATE TABLE IF NOT EXISTS datasets (
    dataset_id INT NOT NULL PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    dataset_version TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS jobs (
    job_id SERIAL PRIMARY KEY,
    dataset_id INT NOT NULL REFERENCES datasets(dataset_id),
    status TEXT DEFAULT 'pending'
);



CREATE TABLE  IF NOT EXISTS trained_models (
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


CREATE TABLE IF NOT EXISTS prod_models (
    model_name TEXT,
    model_version TEXT,
    PRIMARY KEY (model_name)
);


CREATE TABLE IF NOT EXISTS deployments (
    deployment_id SERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    status TEXT NOT NULL, --flag for rollback
    created_at TIMESTAMP DEFAULT now()

);

CREATE TABLE IF NOT EXISTS deployments (
    deployment_id SERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    deployed_at TIMESTAMP DEFAULT now(),
    deployed_by TEXT
);
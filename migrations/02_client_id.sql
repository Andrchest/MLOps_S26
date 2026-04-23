ALTER TABLE jobs ADD COLUMN IF NOT EXISTS client_id TEXT;
ALTER TABLE jobs ADD CONSTRAINT unique_client_id UNIQUE (client_id);
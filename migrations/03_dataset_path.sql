-- Add dataset_path column to jobs table for object storage path
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS dataset_path TEXT;

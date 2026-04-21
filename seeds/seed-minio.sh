#!/bin/bash
set -e

echo "Waiting for MinIO to be ready..."
while ! nc -z minio 9000 2>/dev/null; do
    sleep 1
done
echo "MinIO is ready."

echo "Creating buckets..."
mc alias set myminio http://minio:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}
mc mb --ignore-existing myminio/datasets
mc mb --ignore-existing myminio/models
echo "Buckets created."

echo "Uploading sample dataset..."
mc cp /seeds/sample_dataset.csv myminio/datasets/test_data
echo "Dataset uploaded."

echo "Seed complete."

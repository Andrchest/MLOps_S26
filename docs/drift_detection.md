# Drift Detection

This project uses a simple drift check.

## How it works

1. During training, we save a small file called `reference_profile.json`.
2. This file stores the mean and standard deviation for each numeric feature.
3. During inference, the new input is compared with those saved values.
4. If the difference is too large, we say drift was detected.
5. If drift is detected, the service creates a new training job.

## API

- `POST /predict`
  - Makes a prediction.
  - Also runs the drift check in the background.
- `GET /drift/visualization?model_name=...&model_version=...`
  - Returns the latest drift result for that model.

## Config

- `DRIFT_THRESHOLD`
  - Default: `2.0`
  - Lower value means retraining will trigger more often.

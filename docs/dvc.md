# DVC

This repository uses DVC to keep data and training steps reproducible.

## What is included

- `.dvc/config`
  - DVC remote settings for MinIO.
- `dvc.yaml`
  - Pipeline steps.
- `params.yaml`
  - Parameters used by the steps.

## Pipeline steps

1. `preprocess_dataset`
   - Reads the source CSV.
   - Removes duplicates.
   - Fills missing numeric values.
2. `train_model`
   - Trains the baseline model.
   - Saves the model, metrics, and reference profile.

## Basic commands

```bash
dvc repro
dvc status
dvc push
dvc pull
```

## CI

CI checks that the DVC pipeline is valid with:

```bash
dvc repro --dry
```

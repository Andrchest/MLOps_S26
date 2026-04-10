"""Simple baseline training script for tabular binary classification.

Usage:
    python pipelines/first_ml_baseline/train.py --data pipelines/first_ml_baseline/data/breast_cancer.csv
"""

import argparse
import json
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

RANDOM_STATE = 42
DEFAULT_TARGET_COLUMN = "target"
DEFAULT_ARTIFACTS_DIR = Path("artifacts")
DEFAULT_MLFLOW_EXPERIMENT = "first_ml_baseline"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a baseline binary classification model on tabular CSV data."
    )
    parser.add_argument(
        "--data",
        required=True,
        help="Path to the input CSV dataset.",
    )
    parser.add_argument(
        "--target",
        default=DEFAULT_TARGET_COLUMN,
        help=f"Target column name. Default: {DEFAULT_TARGET_COLUMN}",
    )
    parser.add_argument(
        "--mlflow-experiment",
        default=DEFAULT_MLFLOW_EXPERIMENT,
        help=f"MLflow experiment name. Default: {DEFAULT_MLFLOW_EXPERIMENT}",
    )
    return parser.parse_args()


def load_csv(data_path: str) -> pd.DataFrame:
    path = Path(data_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    if path.suffix.lower() != ".csv":
        raise ValueError(f"Expected a CSV file, got: {path}")

    try:
        return pd.read_csv(path)
    except Exception as exc:
        raise ValueError(f"Failed to read CSV file '{path}': {exc}") from exc


def prepare_features_and_target(
    df: pd.DataFrame, target_column: str
) -> tuple[pd.DataFrame, pd.Series]:
    if target_column not in df.columns:
        raise ValueError(
            f"Target column '{target_column}' not found in dataset. "
            f"Available columns: {list(df.columns)}"
        )

    feature_df = df.drop(columns=[target_column])
    if feature_df.empty:
        raise ValueError("Dataset must contain at least one feature column.")

    non_numeric_columns = feature_df.select_dtypes(exclude="number").columns.tolist()
    if non_numeric_columns:
        raise ValueError(
            "Only numeric feature columns are supported. "
            f"Non-numeric columns found: {non_numeric_columns}"
        )

    y = df[target_column]
    if y.isna().any():
        raise ValueError("Target column contains missing values.")
    if y.nunique(dropna=False) != 2:
        raise ValueError(
            "Binary classification requires exactly 2 unique target values."
        )

    return feature_df, y


def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> Pipeline:
    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
            ),
        ]
    )
    model.fit(X_train, y_train)
    return model


def calculate_metrics(y_true: pd.Series, y_pred: pd.Series) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred)),
        "recall": float(recall_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred)),
    }


def save_artifacts(
    model: Pipeline, metrics: dict[str, float], artifacts_dir: Path
) -> tuple[Path, Path]:
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    model_path = artifacts_dir / "model.joblib"
    metrics_path = artifacts_dir / "metrics.json"

    joblib.dump(model, model_path)

    with metrics_path.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2)

    return model_path, metrics_path


def log_to_mlflow(
    model: Pipeline,
    metrics: dict[str, float],
    data_path: str,
    target_column: str,
    experiment_name: str,
) -> str:
    mlflow.set_experiment(experiment_name)

    classifier = model.named_steps["classifier"]
    classifier_params = classifier.get_params()

    with mlflow.start_run() as run:
        mlflow.log_param("model_type", type(classifier).__name__)
        mlflow.log_param("target_column", target_column)
        mlflow.log_param("data_path", data_path)
        mlflow.log_param("random_state", RANDOM_STATE)

        for param_name, param_value in classifier_params.items():
            mlflow.log_param(f"model__{param_name}", param_value)

        mlflow.log_metrics(metrics)
        mlflow.sklearn.log_model(model, artifact_path="model")

        return run.info.run_id


def main() -> None:
    args = parse_args()
    df = load_csv(args.data)
    X, y = prepare_features_and_target(df, args.target)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    model = train_model(X_train, y_train)
    y_pred = model.predict(X_test)
    metrics = calculate_metrics(y_test, y_pred)
    model_path, metrics_path = save_artifacts(
        model=model,
        metrics=metrics,
        artifacts_dir=DEFAULT_ARTIFACTS_DIR,
    )
    run_id = log_to_mlflow(
        model=model,
        metrics=metrics,
        data_path=args.data,
        target_column=args.target,
        experiment_name=args.mlflow_experiment,
    )

    print("Training completed successfully.")
    print(f"Model saved to: {model_path}")
    print(f"Metrics saved to: {metrics_path}")
    print(f"MLflow run logged successfully: {run_id}")
    print("Metrics:")
    for metric_name, metric_value in metrics.items():
        print(f"  {metric_name}: {metric_value:.4f}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)

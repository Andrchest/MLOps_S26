import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipelines.first_ml_baseline import train as baseline_train


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the baseline model via DVC.")
    parser.add_argument("--data", required=True, help="Processed CSV dataset.")
    parser.add_argument(
        "--artifacts-dir",
        required=True,
        help="Directory where training artifacts should be written.",
    )
    parser.add_argument(
        "--target-column",
        default="target",
        help="Target column to use during training.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    artifacts_dir = Path(args.artifacts_dir)

    df = baseline_train.load_csv(args.data)
    X, y = baseline_train.prepare_features_and_target(df, args.target_column)
    X_train, X_test, y_train, y_test = baseline_train.train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=baseline_train.RANDOM_STATE,
        stratify=y,
    )

    model = baseline_train.train_model(X_train, y_train)
    y_pred = model.predict(X_test)
    metrics = baseline_train.calculate_metrics(y_test, y_pred)
    baseline_train.save_artifacts(
        model=model,
        metrics=metrics,
        reference_profile=baseline_train.build_reference_profile(X_train),
        artifacts_dir=artifacts_dir,
    )


if __name__ == "__main__":
    main()

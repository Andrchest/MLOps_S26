import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preprocess a CSV dataset for DVC.")
    parser.add_argument("--input", required=True, help="Input CSV file.")
    parser.add_argument("--output", required=True, help="Output CSV file.")
    parser.add_argument(
        "--target-column",
        default="target",
        help="Target column to preserve. Default: target",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    df = pd.read_csv(input_path)
    df = df.drop_duplicates().reset_index(drop=True)

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    if args.target_column in numeric_columns:
        numeric_columns.remove(args.target_column)

    for column in numeric_columns:
        df[column] = df[column].fillna(df[column].median())

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()

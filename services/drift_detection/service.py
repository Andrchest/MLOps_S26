from __future__ import annotations

from typing import Any

import pandas as pd

EPSILON = 1e-6


def _to_dataframe(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy()
    if isinstance(data, list):
        return pd.DataFrame(data)
    if isinstance(data, dict):
        if "features" in data:
            return pd.DataFrame()
        return pd.DataFrame([data])
    raise TypeError(f"Unsupported data type for drift detection: {type(data)!r}")


def build_reference_profile(
    reference_data: pd.DataFrame | list[dict[str, Any]] | dict[str, Any],
) -> dict[str, Any]:
    df = _to_dataframe(reference_data)
    numeric_df = df.select_dtypes(include="number")

    features: dict[str, dict[str, float]] = {}
    for column in numeric_df.columns:
        series = pd.to_numeric(numeric_df[column], errors="coerce").dropna()
        features[column] = {
            "mean": float(series.mean()) if not series.empty else 0.0,
            "std": float(series.std(ddof=0)) if len(series) > 1 else 0.0,
        }

    return {
        "feature_names": list(features.keys()),
        "sample_size": int(df.shape[0]),
        "features": features,
    }


def analyze_drift(
    reference_data: pd.DataFrame | dict[str, Any] | list[dict[str, Any]],
    current_data: pd.DataFrame | list[dict[str, Any]] | dict[str, Any],
    threshold: float = 0.2,
) -> dict[str, Any]:
    reference_profile = (
        reference_data
        if isinstance(reference_data, dict) and "features" in reference_data
        else build_reference_profile(reference_data)
    )
    current_df = _to_dataframe(current_data)
    if current_df.empty:
        return {
            "drift_score": 0.0,
            "drift_detected": False,
            "threshold": threshold,
            "feature_scores": {},
        }

    feature_scores: dict[str, float] = {}
    sample = current_df.iloc[0]

    for feature_name in reference_profile.get("feature_names", []):
        if feature_name not in sample:
            continue
        reference_feature = reference_profile["features"][feature_name]
        current_value = float(sample[feature_name])
        reference_mean = float(reference_feature.get("mean", 0.0))
        reference_std = float(reference_feature.get("std", 0.0))
        score = abs(current_value - reference_mean) / max(reference_std, 1.0, EPSILON)
        feature_scores[feature_name] = float(score)

    drift_score = (
        sum(feature_scores.values()) / len(feature_scores) if feature_scores else 0.0
    )
    return {
        "drift_score": float(drift_score),
        "drift_detected": float(drift_score) >= threshold,
        "threshold": threshold,
        "feature_scores": feature_scores,
    }


def detect_drift(
    reference_data: pd.DataFrame | dict[str, Any] | list[dict[str, Any]],
    current_data: pd.DataFrame | list[dict[str, Any]] | dict[str, Any],
    threshold: float = 0.2,
) -> float:
    return analyze_drift(reference_data, current_data, threshold)["drift_score"]


def format_drift_alert(
    model_name: str,
    model_version: str,
    drift_result: dict[str, Any],
    dataset_name: str | None = None,
) -> dict[str, Any]:
    return {
        "message": (
            f"Drift detected for {model_name}:{model_version} "
            f"with score {drift_result['drift_score']:.4f}"
        ),
        "dataset_name": dataset_name,
        "drift_score": drift_result["drift_score"],
        "threshold": drift_result["threshold"],
        "feature_scores": drift_result.get("feature_scores", {}),
    }


def build_drift_visualization(drift_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "drift_score": drift_result.get("drift_score", 0.0),
        "threshold": drift_result.get("threshold", 0.0),
        "drift_detected": drift_result.get("drift_detected", False),
        "feature_scores": drift_result.get("feature_scores", {}),
    }

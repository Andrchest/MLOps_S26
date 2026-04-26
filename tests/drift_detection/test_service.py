import pandas as pd

from services.drift_detection.service import (
    analyze_drift,
    build_drift_visualization,
    build_reference_profile,
    detect_drift,
)


def test_detect_drift_returns_low_score_for_similar_data():
    reference = pd.DataFrame(
        {
            "age": [30, 31, 29, 32, 28, 30],
            "monthly_spend": [100.0, 102.0, 98.0, 101.0, 99.0, 100.5],
        }
    )
    current = pd.DataFrame(
        {
            "age": [30, 31, 30, 29],
            "monthly_spend": [100.0, 101.0, 99.5, 100.5],
        }
    )

    drift_score = detect_drift(reference, current, threshold=2.0)

    assert drift_score < 2.0


def test_analyze_drift_flags_shifted_data_and_builds_visualization():
    reference = pd.DataFrame(
        {
            "age": [30, 31, 29, 32, 28, 30],
            "monthly_spend": [100.0, 102.0, 98.0, 101.0, 99.0, 100.5],
        }
    )
    shifted = pd.DataFrame(
        {
            "age": [55, 56, 57, 58],
            "monthly_spend": [220.0, 225.0, 230.0, 240.0],
        }
    )

    reference_profile = build_reference_profile(reference)
    drift_result = analyze_drift(reference_profile, shifted, threshold=2.0)
    visualization = build_drift_visualization(drift_result)

    assert drift_result["drift_detected"] is True
    assert drift_result["drift_score"] >= 2.0
    assert visualization["feature_scores"]
    assert set(visualization["feature_scores"]) == {"age", "monthly_spend"}

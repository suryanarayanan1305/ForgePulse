"""
tests/test_anomaly_detection.py — Unit Tests for Multi-Tier Anomaly Detectors
"""

from app.analytics.statistical import RollingStatisticsDetector
from app.analytics.ml_model import MachineAnomalyMLModel


def test_statistical_rolling_detector_baseline():
    """Normal stable readings should NOT trigger a statistical anomaly."""
    detector = RollingStatisticsDetector(window_size=30, z_threshold=3.0)
    for _ in range(25):
        is_anom, z, _, _ = detector.push_and_evaluate("CNC-001", "temp", 50.0 + (_ % 3))
        assert is_anom is False


def test_statistical_rolling_detector_sudden_spike():
    """A sudden extreme spike after stable baseline MUST trigger a Z-score anomaly."""
    detector = RollingStatisticsDetector(window_size=30, z_threshold=3.0)
    for _ in range(25):
        detector.push_and_evaluate("CNC-001", "temp", 50.0 + (_ % 2) * 0.5)

    # Sudden extreme jump
    is_anom, z_score, mean, std = detector.push_and_evaluate("CNC-001", "temp", 98.0)
    assert is_anom is True
    assert z_score > 3.0


def test_ml_isolation_forest_anomaly_detection():
    """IsolationForest should identify normal operating points as normal and extreme outliers as anomalous."""
    model = MachineAnomalyMLModel()

    # Normal operating point
    is_anom, score = model.predict(
        temperature=45.0,
        vibration=2.0,
        pressure=6.0,
        rpm=4000.0,
        power_consumption=10.0,
    )
    assert is_anom is False

    # Extreme multi-metric anomalous point
    is_anom_outlier, outlier_score = model.predict(
        temperature=140.0,
        vibration=35.0,
        pressure=25.0,
        rpm=9000.0,
        power_consumption=80.0,
    )
    assert is_anom_outlier is True

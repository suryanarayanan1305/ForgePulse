"""
analytics/statistical.py — Statistical Anomaly Detection (Z-Score & Rolling Statistics)
========================================================================================

LEVEL 2 ANOMALY DETECTION:
  Calculates rolling baseline statistics (mean, std dev) over recent telemetry windows.
  Flags readings whose Z-score exceeds the configured threshold (|Z| > 3.0).

WHY STATISTICAL ANOMALY DETECTION?
  Fixed thresholds (Level 1) only catch extreme values (e.g. Temp > 85°C).
  Statistical anomaly detection catches unusual deviations relative to the machine's
  recent operating regime, even if the value is below the absolute critical limit.

FORMULA:
  Z = (x - mean) / std_dev
"""

from collections import deque
from typing import Dict, List, Optional, Tuple
import numpy as np


class RollingStatisticsDetector:
    """
    In-memory rolling buffer detector for high-frequency telemetry streams.
    Maintains a rolling FIFO window per machine per metric.
    """

    def __init__(self, window_size: int = 50, z_threshold: float = 3.0) -> None:
        self.window_size = window_size
        self.z_threshold = z_threshold
        # Buffer map: (machine_id, metric_name) -> deque of recent values
        self._buffers: Dict[Tuple[str, str], deque] = {}

    def push_and_evaluate(
        self, machine_id: str, metric_name: str, value: Optional[float]
    ) -> Tuple[bool, float, float, float]:
        """
        Pushes a new metric value into the rolling window and tests for Z-score anomaly.

        Returns:
            Tuple of (is_anomaly: bool, z_score: float, rolling_mean: float, rolling_std: float)
        """
        if value is None:
            return False, 0.0, 0.0, 0.0

        key = (machine_id, metric_name)
        if key not in self._buffers:
            self._buffers[key] = deque(maxlen=self.window_size)

        buffer = self._buffers[key]

        # Need at least 10 samples to calculate a statistically meaningful baseline
        if len(buffer) < 10:
            buffer.append(value)
            return False, 0.0, value, 0.0

        # Calculate current window baseline before adding the new reading
        arr = np.array(buffer)
        mean = float(np.mean(arr))
        std = float(np.std(arr))

        # Standard deviation guard (prevent divide-by-zero if machine is completely constant)
        if std < 1e-4:
            std = 0.01

        z_score = (value - mean) / std
        is_anomaly = abs(z_score) > self.z_threshold

        # Update rolling buffer
        buffer.append(value)

        return is_anomaly, float(z_score), mean, std


# Module-level singleton
statistical_detector = RollingStatisticsDetector(window_size=50, z_threshold=3.0)

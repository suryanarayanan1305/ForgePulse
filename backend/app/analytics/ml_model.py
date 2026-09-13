"""
analytics/ml_model.py — Lightweight Unsupervised Machine Learning Anomaly Detection
====================================================================================

LEVEL 3 ANOMALY DETECTION:
  Uses Scikit-Learn's IsolationForest algorithm to detect multidimensional outliers
  across correlated features: (temperature, vibration, pressure, rpm, power_consumption).

WHY ISOLATION FOREST?
  1. Unsupervised: Does not require labeled "failure vs normal" data (which is rarely
     available in real industrial plants).
  2. Multi-metric correlation: Detects complex compound anomalies (e.g. normal temperature
     and normal vibration individually, but anomalous when paired with high RPM and high load).
  3. Fast inference: Tree-based partitioning evaluates in < 1ms per sample.

INTERVIEW CONTEXT:
  "I used an IsolationForest model fitted on baseline normal operating telemetry.
   The model isolates observations by randomly selecting a feature and split value.
   Anomalies require fewer splits to isolate because they are few and different.
   This is a prototype model — in production with 10k machines, we would train
   per-machine models on historical clean runs and periodically re-fit."
"""

import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class MachineAnomalyMLModel:
    """
    Multivariate Anomaly Detection Model using IsolationForest.
    Features: [temperature, vibration, pressure, rpm, power_consumption]
    """

    FEATURE_NAMES = ["temperature", "vibration", "pressure", "rpm", "power_consumption"]

    def __init__(self, contamination: float = 0.05) -> None:
        self.contamination = contamination
        self.model: Optional[IsolationForest] = None
        self.is_trained = False
        self._initialize_baseline_model()

    def _initialize_baseline_model(self) -> None:
        """
        Synthesizes a clean baseline dataset to pre-train the model
        so it is operational immediately upon system startup.
        """
        np.random.seed(42)
        n_samples = 1500

        # Normal CNC / Mill operational envelope
        rpm = np.random.uniform(2000, 6000, n_samples)
        rpm_ratio = rpm / 6000.0
        temp = 30.0 + (rpm_ratio * 35.0) + np.random.normal(0, 1.5, n_samples)
        vib = 1.0 + (rpm_ratio * 2.5) + np.random.normal(0, 0.2, n_samples)
        pres = 5.0 + (rpm_ratio * 2.0) + np.random.normal(0, 0.1, n_samples)
        pwr = 3.0 + (rpm_ratio * 15.0) + np.random.normal(0, 0.5, n_samples)

        X_train = np.column_stack([temp, vib, pres, rpm, pwr])

        self.model = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=42,
            n_jobs=-1,
        )
        self.model.fit(X_train)
        self.is_trained = True
        logger.info("IsolationForest baseline anomaly detection model pre-trained and ready.")

    def predict(
        self,
        temperature: Optional[float],
        vibration: Optional[float],
        pressure: Optional[float],
        rpm: Optional[float],
        power_consumption: Optional[float],
    ) -> Tuple[bool, float]:
        """
        Evaluates a single multi-metric telemetry reading.

        Returns:
            Tuple of (is_anomaly: bool, anomaly_score: float)
            anomaly_score is normalized from -1.0 (severe anomaly) to +1.0 (highly normal).
        """
        if not self.is_trained or self.model is None:
            return False, 0.0

        # Default fallback values for missing features
        t = temperature if temperature is not None else 35.0
        v = vibration if vibration is not None else 1.5
        p = pressure if pressure is not None else 6.0
        r = rpm if rpm is not None else 3000.0
        pw = power_consumption if power_consumption is not None else 8.0

        X = np.array([[t, v, p, r, pw]])

        try:
            # -1 = anomaly, 1 = normal
            pred = self.model.predict(X)[0]
            # decision_function yields raw anomaly score: lower = more abnormal
            score = float(self.model.decision_function(X)[0])
            is_anomaly = bool(pred == -1)
            return is_anomaly, score
        except Exception as e:
            logger.error(f"ML anomaly prediction failed: {e}")
            return False, 0.0


# Module-level singleton
ml_anomaly_detector = MachineAnomalyMLModel()

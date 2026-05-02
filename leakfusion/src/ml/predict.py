"""Stage 3 predictor — ZoneSeverityPredictor with uncertainty fallback."""
from __future__ import annotations
import numpy as np


class ZoneSeverityPredictor:
    """Stateless wrapper around the trained zone classifier + severity regressor.

    Adds:
    - `op_point_extrapolated` short-circuit -> ml_uncertain
    - `proba_max < 0.5` short-circuit -> ml_uncertain
    - severity clipping to [0, 0.15] with explicit flag
    """

    PROBA_THRESHOLD = 0.5
    SEVERITY_MIN = 0.0
    SEVERITY_MAX = 0.15

    def __init__(self, zone_clf, severity_reg, severity_sigma: float, feature_columns):
        self.zone_clf = zone_clf
        self.severity_reg = severity_reg
        self.severity_sigma = float(severity_sigma)
        self.feature_columns = list(feature_columns)

    def predict_from_features(self, X, op_point_extrapolated: bool) -> dict:
        if op_point_extrapolated:
            return {
                "ml_status": "ml_uncertain",
                "predicted_zone": "uncertain",
                "predicted_zone_proba": None,
                "predicted_severity": None,
                "predicted_severity_ci": None,
                "predicted_severity_clipped": False,
            }
        proba = self.zone_clf.predict_proba(X)[0]
        top_idx = int(np.argmax(proba))
        top_proba = float(proba[top_idx])
        if top_proba < self.PROBA_THRESHOLD:
            return {
                "ml_status": "ml_uncertain",
                "predicted_zone": "uncertain",
                "predicted_zone_proba": top_proba,
                "predicted_severity": None,
                "predicted_severity_ci": None,
                "predicted_severity_clipped": False,
            }
        sev_raw = float(self.severity_reg.predict(X)[0])
        clipped = sev_raw < self.SEVERITY_MIN or sev_raw > self.SEVERITY_MAX
        sev = float(np.clip(sev_raw, self.SEVERITY_MIN, self.SEVERITY_MAX))
        sev_lo = float(np.clip(sev - 1.96 * self.severity_sigma, self.SEVERITY_MIN, self.SEVERITY_MAX))
        sev_hi = float(np.clip(sev + 1.96 * self.severity_sigma, self.SEVERITY_MIN, self.SEVERITY_MAX))
        zone = self.zone_clf.classes_[top_idx]
        return {
            "ml_status": "ml_decision",
            "predicted_zone": str(zone),
            "predicted_zone_proba": top_proba,
            "predicted_severity": sev,
            "predicted_severity_ci": (sev_lo, sev_hi),
            "predicted_severity_clipped": clipped,
        }

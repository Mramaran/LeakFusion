"""Residual orchestrator: compute all 6 residuals for one sensor row."""
from __future__ import annotations
from typing import Any, Dict, Optional

import pandas as pd

from . import (
    r1_intake_mass, r2_boost_balance, r3_exhaust_mass,
    r4_aftertreatment_dp, r5_lambda, r6_thermal,
)
from leakfusion.src.calibration.calibration_set import CalibrationSet

# Must match leakfusion.src.calibration.fit._RPM_BIN_STEP / _LOAD_BIN_STEP.
# Duplicated here to avoid import cycle (fit imports from orchestrator's package).
_RPM_BIN_STEP = 200
_LOAD_BIN_STEP = 0.25


def _snap_rpm(rpm: float) -> int:
    return int(round(rpm / _RPM_BIN_STEP)) * _RPM_BIN_STEP


def _snap_load(load: float) -> float:
    return round(round(load / _LOAD_BIN_STEP) * _LOAD_BIN_STEP, 4)


def _z(value: Optional[float], mu: float, sigma: float) -> Optional[float]:
    if value is None:
        return None
    if sigma <= 0:
        return None
    return (value - mu) / sigma


def compute_residuals(row: pd.Series, calibration: CalibrationSet) -> Dict[str, Any]:
    """Compute all 6 residuals + z-scores + provenance for one sensor row.

    Returns dict:
      residuals:  {R1..R6: float | None}
      z_scores:   {R1..R6: float | None}
      provenance: {R1..R6: str}
      op_point:   {rpm_bin, load_bin, cell_samples}
      flags:      {op_point_extrapolated, z_score_undefined}
    """
    rpm_raw = float(row["engine_rpm"])
    load_raw = float(row.get("load_fraction", 0.0))
    rpm_snapped = _snap_rpm(rpm_raw)
    load_snapped = _snap_load(load_raw)

    cell, extrapolated = calibration.get_nearest_cell(rpm_snapped, load_snapped)
    coeffs = cell.coeffs

    r1, p1 = r1_intake_mass.compute_r1(row, coeffs)
    r2, p2 = r2_boost_balance.compute_r2(row, coeffs)
    r3, p3 = r3_exhaust_mass.compute_r3(row, coeffs)
    r4, p4 = r4_aftertreatment_dp.compute_r4(row, coeffs)
    r5, p5 = r5_lambda.compute_r5(row, coeffs["lambda_baseline_mean"])
    r6, p6 = r6_thermal.compute_r6(row, coeffs)

    residuals = {"R1": r1, "R2": r2, "R3": r3, "R4": r4, "R5": r5, "R6": r6}
    provenance = {"R1": p1, "R2": p2, "R3": p3, "R4": p4, "R5": p5, "R6": p6}

    z_scores: Dict[str, Optional[float]] = {}
    for rk, val in residuals.items():
        stats = cell.residual_stats[rk]
        z_scores[rk] = _z(val, stats.mu, stats.sigma)

    any_z_undefined = any(z is None and val is not None for z, val in zip(z_scores.values(), residuals.values()))

    return {
        "residuals": residuals,
        "z_scores": z_scores,
        "provenance": provenance,
        "op_point": {
            "rpm_bin": cell.rpm_bin,
            "load_bin": cell.load_bin,
            "cell_samples": cell.sample_count,
        },
        "flags": {
            "op_point_extrapolated": extrapolated,
            "z_score_undefined": any_z_undefined,
        },
    }

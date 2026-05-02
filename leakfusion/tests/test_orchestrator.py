"""Orchestrator: compute_residuals(row, calibration) → dict with all 6 residuals + z-scores."""
import pandas as pd
import pytest
from pathlib import Path

from leakfusion.src.residuals.orchestrator import compute_residuals
from leakfusion.src.calibration.calibration_set import (
    CalibrationSet, CellCalibration, ResidualStats,
)
from leakfusion.src.calibration.persist import CURRENT_SCHEMA_VERSION


def _sample_calibration():
    cell = CellCalibration(
        rpm_bin=1400, load_bin=0.75, sample_count=100,
        coeffs={"a0": 0.85, "a1": 0.0, "a2": 0.0, "eta_c": 0.75,
                "e0": 3509.5, "e1": 0.0, "k_ats": 968.0, "phi_coolant": 0.25,
                "lambda_baseline_mean": 1.948},
        residual_stats={
            "R1": ResidualStats(mu=0.0, sigma=2.0),
            "R2": ResidualStats(mu=0.0, sigma=5.0),
            "R3": ResidualStats(mu=0.0, sigma=0.005),
            "R4": ResidualStats(mu=0.0, sigma=1.0),
            "R5": ResidualStats(mu=0.0, sigma=0.02),
            "R6": ResidualStats(mu=0.0, sigma=10.0),
        },
    )
    return CalibrationSet(schema_version=CURRENT_SCHEMA_VERSION, cells=[cell])


def _healthy_row():
    return pd.Series({
        "engine_rpm": 1400, "load_fraction": 0.75,
        "maf": 169.5, "fuel_flow": 6.0, "torque": 500.0,
        "t_intake": 298.0, "t_boost": 310.0, "t_exhaust_manifold": 847.7,
        "intake_manifold_pressure": 200.0, "boost_pressure": 239.0,
        "exhaust_manifold_pressure": 210.0, "exhaust_backpressure": 180.0,
        "ambient_pressure": 101.3, "turbo_speed": 80000.0,
    })


def test_output_has_all_six_residuals():
    row = _healthy_row()
    cs = _sample_calibration()
    out = compute_residuals(row, cs)
    for rk in ["R1", "R2", "R3", "R4", "R5", "R6"]:
        assert rk in out["residuals"]
        assert rk in out["z_scores"]
        assert rk in out["provenance"]


def test_output_has_op_point_and_flags():
    row = _healthy_row()
    cs = _sample_calibration()
    out = compute_residuals(row, cs)
    assert "op_point" in out
    assert "flags" in out
    assert out["op_point"]["rpm_bin"] == 1400
    assert out["op_point"]["load_bin"] == 0.75


def test_extrapolation_flag_set_for_far_op_point():
    row = _healthy_row()
    row["engine_rpm"] = 3000  # outside our calibration
    row["load_fraction"] = 0.25
    cs = _sample_calibration()
    out = compute_residuals(row, cs)
    assert out["flags"]["op_point_extrapolated"] is True


def test_healthy_row_z_scores_small():
    row = _healthy_row()
    cs = _sample_calibration()
    out = compute_residuals(row, cs)
    for rk, z in out["z_scores"].items():
        if z is None:
            continue
        assert abs(z) < 3.0, f"{rk} z-score {z:.2f} too large for textbook healthy row"


def test_provenance_tags_match_design():
    row = _healthy_row()
    cs = _sample_calibration()
    out = compute_residuals(row, cs)
    assert out["provenance"]["R1"] == "real"
    assert out["provenance"]["R2"] == "syn+real"
    assert out["provenance"]["R3"] == "real"
    assert out["provenance"]["R4"] == "syn+real"
    assert out["provenance"]["R5"] == "formula"
    assert out["provenance"]["R6"] == "real"

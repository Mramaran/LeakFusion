"""Tests for csv_pipeline.py — CSV validation + Stage 1+2+3 orchestration."""
import pandas as pd
import pytest

from leakfusion.src.demo.csv_pipeline import validate_csv, CsvValidationError


def _make_valid_row(**overrides) -> dict:
    base = {
        "engine_rpm": 1500.0, "torque": 400.0,
        "maf": 80.0, "boost_pressure": 200.0,
        "intake_manifold_pressure": 195.0, "turbo_speed": 80000.0,
        "exhaust_manifold_pressure": 230.0, "exhaust_backpressure": 110.0,
        "fuel_flow": 5.0, "lambda_sensor": 1.5,
        "t_intake": 305.0, "t_boost": 320.0,
        "t_exhaust_manifold": 850.0, "t_turbine_outlet": 720.0,
        "t_aftertreatment_inlet": 600.0,
        "ambient_pressure": 101.3, "ambient_temperature": 295.0,
    }
    base.update(overrides)
    return base


def test_valid_csv_passes():
    df = pd.DataFrame([_make_valid_row() for _ in range(60)])
    errors = validate_csv(df)
    assert errors == []

def test_missing_column_reported():
    df = pd.DataFrame([_make_valid_row() for _ in range(60)])
    df = df.drop(columns=["boost_pressure"])
    errors = validate_csv(df)
    assert any("boost_pressure" in e for e in errors)

def test_too_few_rows_rejected():
    df = pd.DataFrame([_make_valid_row() for _ in range(10)])
    errors = validate_csv(df)
    assert any("at least 5 seconds" in e or "at least 50 rows" in e for e in errors)


def test_negative_pressure_rejected():
    df = pd.DataFrame([_make_valid_row(boost_pressure=-10.0) for _ in range(60)])
    errors = validate_csv(df)
    assert any("boost_pressure" in e and "negative" in e for e in errors)

def test_rpm_out_of_range_rejected():
    rows = [_make_valid_row() for _ in range(60)]
    rows[3]["engine_rpm"] = 50000.0  # implausible
    df = pd.DataFrame(rows)
    errors = validate_csv(df)
    assert any("engine_rpm" in e and "row 3" in e for e in errors)

def test_non_numeric_rejected():
    rows = [_make_valid_row() for _ in range(60)]
    rows[5]["maf"] = "NA"
    df = pd.DataFrame(rows)
    errors = validate_csv(df)
    assert any("maf" in e and ("numeric" in e or "row 5" in e) for e in errors)


from leakfusion.src.demo.csv_pipeline import _inject_timestamp


def test_inject_timestamp_when_missing():
    df = pd.DataFrame([_make_valid_row() for _ in range(60)])
    out = _inject_timestamp(df)
    assert "timestamp" in out.columns
    assert out["timestamp"].iloc[0] == 0.0
    assert abs(out["timestamp"].iloc[-1] - 5.9) < 1e-9  # 60 rows x 0.1s = 5.9s last value

def test_inject_timestamp_preserves_existing():
    df = pd.DataFrame([_make_valid_row() for _ in range(60)])
    df["timestamp"] = [i * 0.5 for i in range(60)]  # 2 Hz
    out = _inject_timestamp(df)
    assert out["timestamp"].iloc[10] == 5.0  # unchanged


import json
from pathlib import Path

from leakfusion.src.calibration.persist import load_calibration
from leakfusion.src.demo.csv_pipeline import process_sensor_csv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODELS = PROJECT_ROOT / "leakfusion" / "models"


def _load_real_artifacts():
    cal = load_calibration(str(MODELS / "calibration.json"))
    cusum = json.loads((MODELS / "cusum_config.json").read_text())
    return cal, cusum


@pytest.mark.skipif(
    not (MODELS / "calibration.json").exists()
    or not (MODELS / "cusum_config.json").exists(),
    reason="calibration / cusum config not built in this checkout",
)
def test_process_sensor_csv_returns_residuals_and_events():
    """End-to-end smoke: a labeled zone3a slice should fire a CRITICAL event."""
    leak_parquet = PROJECT_ROOT / "leakfusion" / "data" / "leak_labeled.parquet"
    if not leak_parquet.exists():
        pytest.skip("leak_labeled.parquet not built in this checkout")

    df = pd.read_parquet(leak_parquet)
    slice_ = df[(df["leak_zone"] == "zone3a")
                & (df["leak_severity"] == 0.10)
                & (df["engine_rpm"].between(1400, 1600))
                & (df["load_fraction"] == 0.75)].head(60).reset_index(drop=True)
    if len(slice_) < 50:
        pytest.skip(f"Not enough rows for zone3a slice: {len(slice_)}")

    cal, cusum = _load_real_artifacts()
    residuals_df, events = process_sensor_csv(slice_, cal, cusum, predictor=None)

    # Stage 1 produced 6 z-scored residual columns
    for i in range(1, 7):
        assert f"z_R{i}" in residuals_df.columns

    # Stage 2 detected at least one event (zone3a is a strong signal)
    assert len(events) >= 1
    assert any(e["tier"] in ("WARN", "CRITICAL") for e in events)

"""R5 — Lambda (Air-Fuel Ratio residual).

R5 = λ_calc − λ_baseline_cell_mean, where λ_calc = MAF / (fuel_flow · 14.5).
"""
import pandas as pd
import pytest
from leakfusion.src.residuals.r5_lambda import compute_r5, MissingSensorError


def _healthy_row(maf=50.0, fuel_flow=2.0):
    return pd.Series({"maf": maf, "fuel_flow": fuel_flow})


def test_healthy_row_near_baseline():
    # At MAF=50, fuel=2, lambda = 50/(2*14.5) = 1.724
    # If baseline_mean = 1.724, R5 ≈ 0
    row = _healthy_row(maf=50.0, fuel_flow=2.0)
    r5, prov = compute_r5(row, lambda_baseline_mean=1.724)
    assert abs(r5) < 0.01
    assert prov == "formula"


def test_lean_row_positive_residual():
    # More air same fuel → λ rises
    row = _healthy_row(maf=60.0, fuel_flow=2.0)
    r5, _ = compute_r5(row, lambda_baseline_mean=1.724)
    assert r5 > 0


def test_rich_row_negative_residual():
    row = _healthy_row(maf=40.0, fuel_flow=2.0)
    r5, _ = compute_r5(row, lambda_baseline_mean=1.724)
    assert r5 < 0


def test_idle_returns_none():
    row = _healthy_row(maf=50.0, fuel_flow=0.0)
    r5, prov = compute_r5(row, lambda_baseline_mean=1.724)
    assert r5 is None
    assert prov == "idle"


def test_missing_maf_raises():
    row = pd.Series({"fuel_flow": 2.0})
    with pytest.raises(MissingSensorError) as exc:
        compute_r5(row, lambda_baseline_mean=1.724)
    assert "maf" in str(exc.value)


def test_missing_fuel_flow_raises():
    row = pd.Series({"maf": 50.0})
    with pytest.raises(MissingSensorError) as exc:
        compute_r5(row, lambda_baseline_mean=1.724)
    assert "fuel_flow" in str(exc.value)

"""R1 — Intake Mass Balance residual.

MAF_expected = eta_v · V_disp · (RPM/120) · rho_intake · 1000,
rho_intake   = (P_boost · 1000) / (R_air · T_boost)
R1           = MAF_measured − MAF_expected
"""
import pandas as pd
import pytest
from leakfusion.src.residuals.r1_intake_mass import compute_r1, MissingSensorError


def _textbook_row(maf=50.0, rpm=1400, t_boost=310.0, p_boost=200.0):
    """Row at typical NavicEngine steady-state point."""
    return pd.Series({
        "engine_rpm": rpm,
        "maf": maf,
        "t_boost": t_boost,
        "intake_manifold_pressure": p_boost,
    })


def _default_coeffs():
    return {"a0": 0.85, "a1": 0.0, "a2": 0.0}


def test_healthy_row_residual_near_zero():
    # With eta_v=0.85 at RPM=1400, P=200 kPa, T=310 K:
    # rho = 200000 / (287.058 * 310) = 2.248 kg/m^3
    # V_dot = 0.85 * 0.0076 * 1400/120 = 0.0754 m^3/s
    # MAF = 0.0754 * 2.248 * 1000 = 169.5 g/s
    # If we pass MAF_measured = 169.5, R1 should be near 0
    row = _textbook_row(maf=169.5, rpm=1400, t_boost=310.0, p_boost=200.0)
    r1, prov = compute_r1(row, _default_coeffs())
    assert abs(r1) < 1.0
    assert prov == "real"


def test_low_maf_negative_residual():
    # MAF reads lower than physics predicts -> leak before compressor
    row = _textbook_row(maf=150.0, rpm=1400, t_boost=310.0, p_boost=200.0)
    r1, _ = compute_r1(row, _default_coeffs())
    assert r1 < -10


def test_rpm_dependent_eta_v():
    # eta_v = a0 + a1*(RPM/1000) + a2*(RPM/1000)^2
    # With a0=0.7, a1=0.1 at RPM=1000 → eta_v = 0.8
    row = _textbook_row(maf=100.0, rpm=1000, t_boost=310.0, p_boost=200.0)
    coeffs = {"a0": 0.7, "a1": 0.1, "a2": 0.0}
    r1, _ = compute_r1(row, coeffs)
    # eta_v = 0.7 + 0.1*1.0 = 0.8
    # rho = 200000 / (287.058 * 310) = 2.248
    # V_dot = 0.8 * 0.0076 * 1000/120 = 0.0507 m^3/s
    # MAF_exp = 0.0507 * 2.248 * 1000 = 113.9 g/s
    # R1 = 100 - 113.9 = -13.9
    assert -16 < r1 < -12


def test_missing_sensor_raises():
    row = pd.Series({"maf": 50.0, "t_boost": 310.0})  # missing rpm and pressure
    with pytest.raises(MissingSensorError):
        compute_r1(row, _default_coeffs())

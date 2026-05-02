"""R2 — Boost Pressure Balance residual.

Euler turbomachinery: w_c = U_tip^2
Isentropic pressure ratio:
  pi_exp = (1 + eta_c * U_tip^2 / (Cp_air * T_inlet)) ^ (gamma/(gamma-1))
  P_boost_exp = P_ambient * pi_exp
R2 = P_boost_measured − P_boost_exp
"""
import math
import pandas as pd
import pytest
from leakfusion.src.residuals.r2_boost_balance import compute_r2, MissingSensorError


def _textbook_row(p_boost=200.0, turbo_speed=80000.0, t_intake=298.0, p_amb=101.3):
    return pd.Series({
        "intake_manifold_pressure": p_boost,  # use this as measured "boost"
        "boost_pressure": p_boost,
        "turbo_speed": turbo_speed,
        "t_intake": t_intake,
        "ambient_pressure": p_amb,
    })


def test_reasonable_turbo_produces_reasonable_boost():
    # U_tip = π * 0.08 * 80000/60 = 335 m/s
    # U_tip^2 = 112225
    # eta_c * U_tip^2 / (Cp * T) = 0.75 * 112225 / (1005 * 298) = 0.281
    # pi = (1 + 0.281)^(1.4/0.4) = 1.281^3.5 = 2.36
    # P_boost_exp = 101.3 * 2.36 = 239 kPa
    # With measured = 239 → R2 ≈ 0
    row = _textbook_row(p_boost=239.0, turbo_speed=80000.0, t_intake=298.0, p_amb=101.3)
    coeffs = {"eta_c": 0.75}
    r2, prov = compute_r2(row, coeffs)
    assert abs(r2) < 5.0  # kPa tolerance
    assert prov == "syn+real"


def test_post_compressor_leak_gives_negative_r2():
    # Turbo spins normally but leak drops measured boost below predicted
    row = _textbook_row(p_boost=200.0, turbo_speed=80000.0, t_intake=298.0, p_amb=101.3)
    coeffs = {"eta_c": 0.75}
    r2, _ = compute_r2(row, coeffs)
    assert r2 < -20


def test_missing_sensor_raises():
    row = pd.Series({"boost_pressure": 200.0})
    with pytest.raises(MissingSensorError):
        compute_r2(row, {"eta_c": 0.75})

"""R6 — Thermal Balance residual.

Q_fuel    = fuel_flow · LHV_diesel                                   [W]
Q_brake   = torque · RPM · 2*pi / 60                                 [W; measured]
Q_cool    = Q_fuel · phi_coolant
Q_rad     = Q_fuel · 0.05
Q_exh     = Q_fuel − Q_brake − Q_cool − Q_rad
T_exh_exp = 300 + Q_exh / (m_exh · Cp_exh)
R6        = T_exh_manifold − T_exh_exp
"""
import pandas as pd
import pytest
from leakfusion.src.residuals.r6_thermal import compute_r6, MissingSensorError


def _textbook_row(maf=170.0, fuel_flow=6.0, torque=500.0, rpm=1400,
                  t_exh_man=750.0):
    return pd.Series({
        "maf": maf, "fuel_flow": fuel_flow, "torque": torque,
        "engine_rpm": rpm, "t_exhaust_manifold": t_exh_man,
    })


def test_healthy_row_residual_near_zero():
    # Q_fuel = 6 * 42700 = 256200 W
    # Q_brake = 500 * 1400 * 2π/60 = 73304 W
    # Q_cool  = 256200 * 0.25 = 64050
    # Q_rad   = 256200 * 0.05 = 12810
    # Q_exh   = 256200 - 73304 - 64050 - 12810 = 106036
    # m_exh   = (170+6)/1000 = 0.176 kg/s
    # T_exh_exp = 300 + 106036 / (0.176 * 1100) = 300 + 547.7 = 847.7 K
    # So pick t_exh_manifold = 847.7 for zero residual
    row = _textbook_row(t_exh_man=847.7)
    coeffs = {"phi_coolant": 0.25}
    r6, prov = compute_r6(row, coeffs)
    assert abs(r6) < 2.0
    assert prov == "real"


def test_exhaust_disruption_gives_negative_r6():
    # Lower actual exhaust temp than physics predicts → leak disrupted flow
    row = _textbook_row(t_exh_man=750.0)
    coeffs = {"phi_coolant": 0.25}
    r6, _ = compute_r6(row, coeffs)
    assert r6 < -50


def test_idle_handles_zero_fuel():
    row = _textbook_row(fuel_flow=0.0, torque=0.0)
    coeffs = {"phi_coolant": 0.25}
    r6, prov = compute_r6(row, coeffs)
    assert prov == "idle"
    assert r6 is None


def test_missing_sensor_raises():
    row = pd.Series({"maf": 170.0})
    with pytest.raises(MissingSensorError):
        compute_r6(row, {"phi_coolant": 0.25})

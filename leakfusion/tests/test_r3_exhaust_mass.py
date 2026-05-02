"""R3 — Exhaust Mass Balance residual.

m_exh_expected = (MAF + fuel_flow) / 1000                            [kg/s]
m_exh_measured = sqrt( (P_exh_manifold − P_ambient − e1) / e0 )       [kg/s]
R3             = m_exh_measured − m_exh_expected
"""
import math
import pandas as pd
import pytest
from leakfusion.src.residuals.r3_exhaust_mass import compute_r3, MissingSensorError


def _textbook_row(maf=170.0, fuel_flow=6.0, p_exh=210.0, p_amb=101.3):
    return pd.Series({
        "maf": maf, "fuel_flow": fuel_flow,
        "exhaust_manifold_pressure": p_exh,
        "ambient_pressure": p_amb,
    })


def _coeffs(e0=20000.0, e1=0.0):
    """Pick e0 so that (P_exh - P_amb) / e0 ≈ (MAF+fuel)^2 at textbook op point."""
    return {"e0": e0, "e1": e1}


def test_healthy_row_residual_near_zero():
    # Solve e0 so that sqrt((210 - 101.3) / e0) = (170+6)/1000 = 0.176 kg/s
    # e0 = (210 - 101.3) / 0.176^2 = 3509.5
    row = _textbook_row()
    coeffs = {"e0": 3509.5, "e1": 0.0}
    r3, prov = compute_r3(row, coeffs)
    assert abs(r3) < 0.005  # kg/s
    assert prov == "real"


def test_exhaust_leak_gives_negative_r3():
    # If pressure falls (leak) → measured exhaust mass backs out smaller
    row = _textbook_row(p_exh=180.0)
    coeffs = {"e0": 3509.5, "e1": 0.0}
    r3, _ = compute_r3(row, coeffs)
    assert r3 < -0.01


def test_invalid_sqrt_argument_returns_nan_flag():
    # If P_exh < P_amb, sqrt would be imaginary - must handle gracefully
    row = _textbook_row(p_exh=90.0)
    coeffs = {"e0": 3509.5, "e1": 0.0}
    r3, prov = compute_r3(row, coeffs)
    assert math.isnan(r3)
    assert prov == "invalid_pressure"


def test_missing_sensor_raises():
    row = pd.Series({"maf": 170.0})
    with pytest.raises(MissingSensorError):
        compute_r3(row, _coeffs())

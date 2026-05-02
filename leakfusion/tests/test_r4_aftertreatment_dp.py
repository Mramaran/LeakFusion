"""R4 — Aftertreatment ΔP residual.

ΔP_expected = k_ats · (m_exh/1000)^2       [Forchheimer quadratic, kPa]
ΔP_measured = P_exh_manifold − P_backpressure
R4          = ΔP_measured − ΔP_expected
"""
import pandas as pd
import pytest
from leakfusion.src.residuals.r4_aftertreatment_dp import compute_r4, MissingSensorError


def _textbook_row(maf=170.0, fuel_flow=6.0, p_exh=210.0, p_back=180.0):
    return pd.Series({
        "maf": maf, "fuel_flow": fuel_flow,
        "exhaust_manifold_pressure": p_exh,
        "exhaust_backpressure": p_back,
    })


def test_healthy_row_near_zero_with_right_k():
    # m_exh = (170+6)/1000 = 0.176 kg/s -> m_exh^2 = 0.031
    # ΔP_measured = 210 - 180 = 30 kPa
    # k_ats = 30 / 0.031 = 968
    row = _textbook_row()
    coeffs = {"k_ats": 968.0}
    r4, prov = compute_r4(row, coeffs)
    assert abs(r4) < 1.0
    assert prov == "syn+real"


def test_pre_dpf_leak_gives_negative_r4():
    # Leak drops m_exh reaching DPF → actual ΔP lower than predicted
    row = _textbook_row(p_exh=200.0)  # lower manifold pressure → lower ΔP
    coeffs = {"k_ats": 968.0}
    r4, _ = compute_r4(row, coeffs)
    assert r4 < -5


def test_missing_sensor_raises():
    row = pd.Series({"maf": 170.0})
    with pytest.raises(MissingSensorError):
        compute_r4(row, {"k_ats": 1000.0})

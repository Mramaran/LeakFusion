"""R1 — Intake Mass Balance residual.

Physics: conservation of mass + ideal gas law at intake-manifold conditions.
  rho_intake  = (P_boost · 1000) / (R_air · T_boost)   [kg/m^3; kPa -> Pa]
  eta_v(RPM)  = a0 + a1·(RPM/1000) + a2·(RPM/1000)^2
  MAF_exp     = eta_v · V_disp · (RPM/120) · rho_intake · 1000   [g/s]
  R1          = MAF_measured − MAF_exp

See docs/stage1/STAGE1_DESIGN.md §2 (R1) and syn-engine/src/subsystems/air_intake.py.
"""
from __future__ import annotations
from typing import Dict, Tuple

import pandas as pd

from .constants import R_AIR, DISPLACEMENT_M3


class MissingSensorError(KeyError):
    pass


_REQUIRED = ("engine_rpm", "maf", "t_boost", "intake_manifold_pressure")


def compute_r1(row: pd.Series, coeffs: Dict[str, float]) -> Tuple[float, str]:
    """Compute R1. coeffs must contain a0, a1, a2."""
    for col in _REQUIRED:
        if col not in row.index:
            raise MissingSensorError(f"R1 requires {_REQUIRED}; missing: {col}")

    rpm = float(row["engine_rpm"])
    maf_measured = float(row["maf"])
    t_boost = float(row["t_boost"])
    p_boost = float(row["intake_manifold_pressure"])

    rpm_k = rpm / 1000.0
    eta_v = coeffs["a0"] + coeffs["a1"] * rpm_k + coeffs["a2"] * rpm_k ** 2

    rho_intake = (p_boost * 1000.0) / (R_AIR * t_boost)  # kg/m^3
    v_dot = eta_v * DISPLACEMENT_M3 * (rpm / 120.0)       # m^3/s
    maf_expected = v_dot * rho_intake * 1000.0            # g/s

    r1 = maf_measured - maf_expected
    return r1, "real"

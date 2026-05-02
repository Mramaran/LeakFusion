"""R6 — Thermal Balance residual.

First law of thermodynamics: fuel energy = brake work + coolant loss + radiation + exhaust enthalpy.

Q_fuel    = fuel_flow · LHV_diesel                              [W]
Q_brake   = torque · RPM · 2π / 60                              [W, measured]
Q_cool    = Q_fuel · phi_coolant                                [calibrated]
Q_rad     = Q_fuel · 0.05                                       [fixed textbook]
Q_exh     = Q_fuel − Q_brake − Q_cool − Q_rad
T_exh_exp = 300 + Q_exh / (m_exh · Cp_exh)
R6        = T_exh_manifold − T_exh_exp

See docs/stage1/STAGE1_DESIGN.md §2 (R6) and syn-engine/src/subsystems/exhaust.py:33-41.
"""
from __future__ import annotations
import math
from typing import Dict, Optional, Tuple

import pandas as pd

from .constants import LHV_DIESEL, CP_EXHAUST, RADIATION_LOSS_FRACTION


class MissingSensorError(KeyError):
    pass


_REQUIRED = ("maf", "fuel_flow", "torque", "engine_rpm", "t_exhaust_manifold")
_T_REFERENCE = 300.0  # K, matches syn-engine exhaust.py:41


def compute_r6(row: pd.Series, coeffs: Dict[str, float]) -> Tuple[Optional[float], str]:
    """Compute R6. coeffs must contain phi_coolant."""
    for col in _REQUIRED:
        if col not in row.index:
            raise MissingSensorError(f"R6 requires {_REQUIRED}; missing: {col}")

    fuel_flow = float(row["fuel_flow"])
    if fuel_flow <= 0.0:
        return None, "idle"

    torque = float(row["torque"])
    rpm = float(row["engine_rpm"])
    maf = float(row["maf"])
    t_exh_measured = float(row["t_exhaust_manifold"])

    q_fuel = fuel_flow * LHV_DIESEL  # W (g/s · J/g)
    q_brake = torque * rpm * 2 * math.pi / 60.0  # W
    q_cool = q_fuel * coeffs["phi_coolant"]
    q_rad = q_fuel * RADIATION_LOSS_FRACTION
    q_exh = q_fuel - q_brake - q_cool - q_rad
    q_exh = max(q_exh, 100.0)  # floor to avoid negative temperatures at pathological inputs

    m_exh_kgs = (maf + fuel_flow) / 1000.0
    t_exh_expected = _T_REFERENCE + q_exh / (m_exh_kgs * CP_EXHAUST)

    r6 = t_exh_measured - t_exh_expected
    return r6, "real"

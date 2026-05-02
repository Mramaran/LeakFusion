"""R2 — Boost Pressure Balance residual.

Uses turbo_speed (syn-filled on NavicEngine rows) to stay orthogonal to R1.

U_tip      = π · D_compressor · (turbo_speed/60)                     [m/s]
pi_expected = (1 + eta_c · U_tip^2 / (Cp_air · T_inlet))^(gamma/(gamma-1))
P_boost_exp = P_ambient · pi_expected
R2         = P_boost_measured − P_boost_exp

See docs/stage1/STAGE1_DESIGN.md §2 (R2).
"""
from __future__ import annotations
import math
from typing import Dict, Tuple

import pandas as pd

from .constants import GAMMA_AIR, CP_AIR, D_COMPRESSOR


class MissingSensorError(KeyError):
    pass


_REQUIRED = ("boost_pressure", "turbo_speed", "t_intake", "ambient_pressure")


def compute_r2(row: pd.Series, coeffs: Dict[str, float]) -> Tuple[float, str]:
    """Compute R2. coeffs must contain eta_c."""
    for col in _REQUIRED:
        if col not in row.index:
            raise MissingSensorError(f"R2 requires {_REQUIRED}; missing: {col}")

    p_boost_measured = float(row["boost_pressure"])
    turbo_speed = float(row["turbo_speed"])
    t_intake = float(row["t_intake"])
    p_amb = float(row["ambient_pressure"])

    u_tip = math.pi * D_COMPRESSOR * (turbo_speed / 60.0)   # m/s
    arg = 1.0 + coeffs["eta_c"] * u_tip ** 2 / (CP_AIR * t_intake)
    pi_expected = arg ** (GAMMA_AIR / (GAMMA_AIR - 1.0))
    p_boost_expected = p_amb * pi_expected

    r2 = p_boost_measured - p_boost_expected
    return r2, "syn+real"

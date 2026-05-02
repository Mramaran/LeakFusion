"""R3 — Exhaust Mass Balance residual.

Mass conservation: m_exh_expected = (MAF + fuel_flow) / 1000   [kg/s]

NavicEngine has no exhaust mass flow sensor, so we invert syn-engine's
turbulent-flow manifold pressure model:
    P_exh_manifold = P_ambient + e0 · m_exh^2 + e1
    m_exh_measured = sqrt((P_exh_manifold − P_ambient − e1) / e0)

R3 = m_exh_measured − m_exh_expected                           [kg/s]

See docs/stage1/STAGE1_DESIGN.md §2 (R3) and syn-engine/src/subsystems/exhaust.py:51.
"""
from __future__ import annotations
import math
from typing import Dict, Tuple

import pandas as pd


class MissingSensorError(KeyError):
    pass


_REQUIRED = ("maf", "fuel_flow", "exhaust_manifold_pressure", "ambient_pressure")


def compute_r3(row: pd.Series, coeffs: Dict[str, float]) -> Tuple[float, str]:
    """Compute R3. coeffs must contain e0, e1."""
    for col in _REQUIRED:
        if col not in row.index:
            raise MissingSensorError(f"R3 requires {_REQUIRED}; missing: {col}")

    maf = float(row["maf"])
    fuel_flow = float(row["fuel_flow"])
    p_exh = float(row["exhaust_manifold_pressure"])
    p_amb = float(row["ambient_pressure"])

    m_exh_expected = (maf + fuel_flow) / 1000.0  # kg/s

    inside = (p_exh - p_amb - coeffs["e1"]) / coeffs["e0"]
    if inside < 0:
        return float("nan"), "invalid_pressure"
    m_exh_measured = math.sqrt(inside)

    r3 = m_exh_measured - m_exh_expected
    return r3, "real"

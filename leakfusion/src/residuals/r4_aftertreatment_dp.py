"""R4 — Aftertreatment ΔP residual.

ΔP_expected = k_ats · m_exh^2   [Forchheimer quadratic for porous media, kPa]
ΔP_measured = P_exh_manifold − P_backpressure
R4          = ΔP_measured − ΔP_expected

Provenance is "syn+real" because density normalization would use t_aftertreatment_inlet,
which is syn-filled on NavicEngine rows.

See docs/stage1/STAGE1_DESIGN.md §2 (R4).
"""
from __future__ import annotations
from typing import Dict, Tuple

import pandas as pd


class MissingSensorError(KeyError):
    pass


_REQUIRED = ("maf", "fuel_flow", "exhaust_manifold_pressure", "exhaust_backpressure")


def compute_r4(row: pd.Series, coeffs: Dict[str, float]) -> Tuple[float, str]:
    """Compute R4. coeffs must contain k_ats."""
    for col in _REQUIRED:
        if col not in row.index:
            raise MissingSensorError(f"R4 requires {_REQUIRED}; missing: {col}")

    m_exh_kgs = (float(row["maf"]) + float(row["fuel_flow"])) / 1000.0
    dp_measured = float(row["exhaust_manifold_pressure"]) - float(row["exhaust_backpressure"])
    dp_expected = coeffs["k_ats"] * m_exh_kgs ** 2
    r4 = dp_measured - dp_expected
    return r4, "syn+real"

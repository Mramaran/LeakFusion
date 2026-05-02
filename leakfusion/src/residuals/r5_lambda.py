"""R5 — Lambda (Air-Fuel Ratio) residual.

λ_calc       = MAF / (fuel_flow · 14.5)
R5           = λ_calc − λ_baseline_cell_mean   [NavicEngine has no lambda sensor]

Provenance: "formula" when computed, "idle" when fuel_flow ≤ 0.

See docs/stage1/STAGE1_DESIGN.md §2 (R5).
"""
from __future__ import annotations
from typing import Optional, Tuple

import pandas as pd

from .constants import AFR_STOICH


class MissingSensorError(KeyError):
    """Raised when a required sensor column is absent from the input row."""


_REQUIRED = ("maf", "fuel_flow")


def compute_r5(row: pd.Series, lambda_baseline_mean: float) -> Tuple[Optional[float], str]:
    """Return (R5, provenance_tag).

    Args:
        row: Single sensor row with maf (g/s) and fuel_flow (g/s).
        lambda_baseline_mean: Calibrated healthy-cell mean of λ_calc.

    Returns:
        (R5 residual, provenance tag). R5 is None when engine is idle (fuel_flow ≤ 0).
    """
    for col in _REQUIRED:
        if col not in row.index:
            raise MissingSensorError(f"R5 requires {_REQUIRED}; missing: {col}")

    fuel_flow = float(row["fuel_flow"])
    if fuel_flow <= 0.0:
        return None, "idle"

    lambda_calc = float(row["maf"]) / (fuel_flow * AFR_STOICH)
    r5 = lambda_calc - lambda_baseline_mean
    return r5, "formula"

"""Empirical CUSUM h tuning — per-residual sweep over a discrete grid.

Picks the smallest h such that per-sample FAR <= target_far on a healthy
validation stream. NaN samples are excluded from the FAR denominator
(Isermann §7.2.1).
"""
from __future__ import annotations
import math
from typing import Iterable

import numpy as np

from leakfusion.src.detection.cusum import CusumChannel


_DEFAULT_H_GRID: tuple[float, ...] = (3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0, 12.0, 15.0)
_DEFAULT_K = 0.5


def _measure_far(z: Iterable[float], k: float, h: float) -> tuple[float, int]:
    """Run CusumChannel over z, return (FAR, n_valid)."""
    ch = CusumChannel(name="_tune", k=k, h=h)
    fire_count = 0
    n_valid = 0
    for z_t in z:
        if z_t is None or (isinstance(z_t, float) and math.isnan(z_t)):
            continue
        n_valid += 1
        if ch.update(float(z_t)):
            fire_count += 1
    if n_valid == 0:
        return 0.0, 0
    return fire_count / n_valid, n_valid


def tune_cusum_thresholds(
    z_streams: dict[str, Iterable[float]],
    target_far: float = 0.01,
    h_grid: tuple[float, ...] = _DEFAULT_H_GRID,
    k: float = _DEFAULT_K,
) -> dict[str, dict]:
    """Tune h per residual to hit FAR <= target_far on the given z-streams.

    Returns: {residual: {"k": k, "h": h_chosen, "FAR_measured": far, "n_validation": n}}
    """
    config: dict[str, dict] = {}
    for residual, stream in z_streams.items():
        z_list = list(stream)
        chosen_h = h_grid[-1]
        chosen_far = 1.0
        n_valid_chosen = 0
        for h in h_grid:
            far, n_valid = _measure_far(z_list, k=k, h=h)
            if far <= target_far:
                chosen_h = h
                chosen_far = far
                n_valid_chosen = n_valid
                break
            chosen_h = h
            chosen_far = far
            n_valid_chosen = n_valid
        config[residual] = {
            "k": k,
            "h": chosen_h,
            "FAR_measured": chosen_far,
            "n_validation": n_valid_chosen,
        }
    return config

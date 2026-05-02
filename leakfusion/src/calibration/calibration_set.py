"""In-memory representation of fitted calibration.

One CalibrationSet contains many CellCalibration objects, each one fit for a
specific (rpm_bin, load_bin) cell. Z-score normalization is per-cell because
residual variance is operating-point-dependent.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


class CellNotFoundError(KeyError):
    """Raised when a requested (rpm_bin, load_bin) cell does not exist in the calibration."""


@dataclass
class ResidualStats:
    """Per-residual (mu, sigma) for z-score normalization."""
    mu: float
    sigma: float


@dataclass
class CellCalibration:
    """Fitted constants and residual stats for one (rpm_bin, load_bin) cell."""
    rpm_bin: int
    load_bin: float
    sample_count: int
    coeffs: Dict[str, float]
    residual_stats: Dict[str, ResidualStats]


@dataclass
class CalibrationSet:
    """Full calibration artifact — one per engine, regenerated on recalibration."""
    schema_version: int
    cells: List[CellCalibration] = field(default_factory=list)

    def get_cell(self, rpm_bin: int, load_bin: float) -> CellCalibration:
        """Exact-match lookup. Raises CellNotFoundError if not present."""
        for c in self.cells:
            if c.rpm_bin == rpm_bin and abs(c.load_bin - load_bin) < 1e-6:
                return c
        raise CellNotFoundError(f"No calibration for cell ({rpm_bin}, {load_bin})")

    def get_nearest_cell(self, rpm: float, load: float) -> Tuple[CellCalibration, bool]:
        """Return (nearest_cell, extrapolated_flag).

        extrapolated_flag is True if the requested (rpm, load) does not match any
        cell exactly (within tolerance).
        """
        if not self.cells:
            raise CellNotFoundError("Calibration has no cells")
        best = min(self.cells, key=lambda c: (c.rpm_bin - rpm) ** 2 + ((c.load_bin - load) * 2000) ** 2)
        extrapolated = not (abs(best.rpm_bin - rpm) < 1.0 and abs(best.load_bin - load) < 1e-3)
        return best, extrapolated

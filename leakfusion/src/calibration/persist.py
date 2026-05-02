"""Save/load CalibrationSet as JSON with schema-version safety."""
from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path

from .calibration_set import CalibrationSet, CellCalibration, ResidualStats

CURRENT_SCHEMA_VERSION = 1


class CalibrationVersionError(ValueError):
    """Raised when a loaded calibration has an unsupported schema_version."""


def save_calibration(cs: CalibrationSet, path: Path | str) -> None:
    """Write calibration to JSON. Overwrites any existing file at path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": cs.schema_version,
        "cells": [
            {
                "rpm_bin": c.rpm_bin,
                "load_bin": c.load_bin,
                "sample_count": c.sample_count,
                "coeffs": c.coeffs,
                "residual_stats": {k: asdict(v) for k, v in c.residual_stats.items()},
            }
            for c in cs.cells
        ],
    }
    path.write_text(json.dumps(payload, indent=2))


def load_calibration(path: Path | str) -> CalibrationSet:
    """Load calibration from JSON. Raises CalibrationVersionError on schema mismatch."""
    path = Path(path)
    data = json.loads(path.read_text())
    if data.get("schema_version") != CURRENT_SCHEMA_VERSION:
        raise CalibrationVersionError(
            f"Schema version {data.get('schema_version')} not supported "
            f"(expected {CURRENT_SCHEMA_VERSION})"
        )
    cells = [
        CellCalibration(
            rpm_bin=d["rpm_bin"], load_bin=d["load_bin"],
            sample_count=d["sample_count"], coeffs=d["coeffs"],
            residual_stats={k: ResidualStats(**v) for k, v in d["residual_stats"].items()},
        )
        for d in data["cells"]
    ]
    return CalibrationSet(schema_version=data["schema_version"], cells=cells)

"""Registry of pre-built sample CSVs for the demo UI's quick-load buttons."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


SAMPLE_BUTTONS: list[dict] = [
    {"key": "healthy_run",
     "label": "Healthy Run",
     "icon": "check",
     "filename": "healthy_run.csv"},
    {"key": "zone1_intake_leak",
     "label": "Zone 1 Leak (Intake)",
     "icon": "warning",
     "filename": "zone1_intake_leak.csv"},
    {"key": "zone3a_exhaust_leak",
     "label": "Zone 3a Leak (Exhaust)",
     "icon": "warning",
     "filename": "zone3a_exhaust_leak.csv"},
    {"key": "zone4_testcell_leak",
     "label": "Zone 4 Leak (Test-Cell)",
     "icon": "warning",
     "filename": "zone4_testcell_leak.csv"},
]


def load_sample(samples_dir: Path, key: str) -> pd.DataFrame:
    """Load a sample CSV by its registry key."""
    spec = next((b for b in SAMPLE_BUTTONS if b["key"] == key), None)
    if spec is None:
        raise KeyError(f"Unknown sample: {key}")
    path = samples_dir / spec["filename"]
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: python -m leakfusion.scripts.build_demo_samples"
        )
    return pd.read_csv(path)

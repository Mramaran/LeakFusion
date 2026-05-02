"""Leak-labeled dataset builder: wraps syn-engine batch mode, verifies labels."""
import tempfile
from pathlib import Path

import pandas as pd

from leakfusion.scripts.build_leaks import build_leak_dataset
from leakfusion.src.schema import REQUIRED_COLUMNS, LABEL_COLUMNS


# Small grid to keep test under 2 minutes
_TEST_GRID = {
    "rpms": [1200],
    "loads": [0.5, 0.9],
    "zones": ["no_leak", "zone2"],
    "severities": [0.05],
    "samples_per_point": 10,
}


def test_produces_parquet():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "leaks.parquet"
        build_leak_dataset(out_path=out, **_TEST_GRID)
        assert out.exists()


def test_has_labels():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "leaks.parquet"
        build_leak_dataset(out_path=out, **_TEST_GRID)
        df = pd.read_parquet(out)
        for col in LABEL_COLUMNS:
            assert col in df.columns, f"Missing label column {col}"


def test_has_all_required_columns():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "leaks.parquet"
        build_leak_dataset(out_path=out, **_TEST_GRID)
        df = pd.read_parquet(out)
        missing = REQUIRED_COLUMNS - set(df.columns)
        assert not missing, f"Missing columns: {missing}"


def test_no_leak_has_zero_severity():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "leaks.parquet"
        build_leak_dataset(out_path=out, **_TEST_GRID)
        df = pd.read_parquet(out)
        no_leak_rows = df[df["leak_zone"] == "no_leak"]
        assert len(no_leak_rows) > 0
        assert (no_leak_rows["leak_severity"] == 0.0).all()


def test_leak_rows_have_nonzero_severity():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "leaks.parquet"
        build_leak_dataset(out_path=out, **_TEST_GRID)
        df = pd.read_parquet(out)
        leak_rows = df[df["leak_zone"] != "no_leak"]
        assert len(leak_rows) > 0
        assert (leak_rows["leak_severity"] > 0.0).all()


def test_row_count_matches_grid():
    # 1 rpm * 2 loads * ((1 no_leak * 1) + (1 zone * 1 severity)) * 10 samples = 40 rows
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "leaks.parquet"
        build_leak_dataset(out_path=out, **_TEST_GRID)
        df = pd.read_parquet(out)
        expected = 1 * 2 * (1 + 1 * 1) * 10  # rpms * loads * (no_leak + zones*severities) * samples
        assert len(df) == expected, f"Expected {expected} rows, got {len(df)}"

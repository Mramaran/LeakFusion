"""Tests for build_demo_samples script."""
import pandas as pd
import pytest
from pathlib import Path

from leakfusion.scripts.build_demo_samples import SAMPLE_SPECS, build_one


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LEAK_PARQUET = PROJECT_ROOT / "leakfusion" / "data" / "leak_labeled.parquet"


@pytest.mark.skipif(not LEAK_PARQUET.exists(), reason="leak_labeled.parquet not built")
def test_build_one_zone3a(tmp_path):
    spec = SAMPLE_SPECS["zone3a_exhaust_leak"]
    out_path = tmp_path / "zone3a.csv"
    build_one(LEAK_PARQUET, spec, out_path)
    df = pd.read_csv(out_path)
    assert 50 <= len(df) <= 1000
    assert (df["leak_zone"] == spec["zone"]).all()
    # 17 sensor cols + timestamp + leak_zone + leak_severity + maybe load_fraction
    assert "engine_rpm" in df.columns
    assert "boost_pressure" in df.columns
    assert "timestamp" in df.columns


def test_sample_specs_has_four_entries():
    assert set(SAMPLE_SPECS.keys()) == {
        "healthy_run",
        "zone1_intake_leak",
        "zone3a_exhaust_leak",
        "zone4_testcell_leak",
    }

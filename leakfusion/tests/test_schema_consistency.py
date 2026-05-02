"""Smoke test: both Phase 1 artifacts share the same REQUIRED_COLUMNS schema."""
from pathlib import Path

import pandas as pd
import pytest

from leakfusion.src.schema import REQUIRED_COLUMNS

HEALTHY = Path("leakfusion/data/healthy_baseline.parquet")
LEAKED = Path("leakfusion/data/leak_labeled.parquet")


@pytest.mark.skipif(not HEALTHY.exists(), reason="healthy_baseline.parquet not built yet")
@pytest.mark.skipif(not LEAKED.exists(), reason="leak_labeled.parquet not built yet")
def test_both_parquets_have_required_columns():
    h = pd.read_parquet(HEALTHY)
    l = pd.read_parquet(LEAKED)
    for col in REQUIRED_COLUMNS:
        assert col in h.columns, f"Healthy missing {col}"
        assert col in l.columns, f"Leaked missing {col}"


@pytest.mark.skipif(not HEALTHY.exists() or not LEAKED.exists(), reason="artifacts not built")
def test_same_units_across_artifacts():
    """Pressure/temp ranges should overlap: both are the same physical system."""
    h = pd.read_parquet(HEALTHY)
    l = pd.read_parquet(LEAKED)

    # Boost pressure: expect overlapping ranges
    h_boost = h["boost_pressure"].describe()
    l_boost = l["boost_pressure"].describe()
    assert l_boost["min"] < h_boost["max"]
    assert h_boost["min"] < l_boost["max"]

    # T_intake: near ambient (270-330 K) for both
    assert h["t_intake"].between(250, 400).all()
    assert l["t_intake"].between(250, 400).all()


@pytest.mark.skipif(not HEALTHY.exists() or not LEAKED.exists(), reason="artifacts not built")
def test_leak_data_is_superset_of_op_points():
    """Leak dataset should cover at least the NavicEngine RPMs (1000, 1200, 1400, 1600)."""
    l = pd.read_parquet(LEAKED)
    leak_rpms = set(round(r) for r in l["engine_rpm"].unique())
    navic_rpms = {1000, 1200, 1400, 1600}
    # Each NavicEngine RPM should have at least one nearby match (+/-20)
    for target in navic_rpms:
        assert any(abs(r - target) < 20 for r in leak_rpms), f"No leak data near RPM {target}"


@pytest.mark.skipif(not HEALTHY.exists(), reason="healthy not built")
def test_healthy_rows_above_minimum():
    h = pd.read_parquet(HEALTHY)
    assert len(h) > 1000, f"Healthy baseline too small: {len(h)} rows"


@pytest.mark.skipif(not LEAKED.exists(), reason="leak dataset not built")
def test_leaked_rows_above_minimum():
    l = pd.read_parquet(LEAKED)
    assert len(l) > 10_000, f"Leak dataset too small: {len(l)} rows"

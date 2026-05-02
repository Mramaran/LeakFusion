"""End-to-end test of healthy baseline builder: produces parquet with correct schema."""
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from leakfusion.scripts.build_healthy import build_healthy_baseline
from leakfusion.src.schema import REQUIRED_COLUMNS, LABEL_COLUMNS


def test_produces_parquet():
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "healthy.parquet"
        build_healthy_baseline(out_path=out_path, speeds=[1200])
        assert out_path.exists()


def test_schema_has_all_required_columns():
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "healthy.parquet"
        build_healthy_baseline(out_path=out_path, speeds=[1200])
        df = pd.read_parquet(out_path)
        missing = REQUIRED_COLUMNS - set(df.columns)
        assert not missing, f"Missing columns: {missing}"


def test_has_load_fraction_column():
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "healthy.parquet"
        build_healthy_baseline(out_path=out_path, speeds=[1200])
        df = pd.read_parquet(out_path)
        assert "load_fraction" in df.columns
        assert (df["load_fraction"] >= 0).all()
        assert (df["load_fraction"] <= 1).all()


def test_no_nan_in_required_columns():
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "healthy.parquet"
        build_healthy_baseline(out_path=out_path, speeds=[1200])
        df = pd.read_parquet(out_path)
        for col in REQUIRED_COLUMNS:
            assert not df[col].isna().any(), f"{col} has NaN"


def test_synthetic_columns_present_and_reasonable():
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "healthy.parquet"
        build_healthy_baseline(out_path=out_path, speeds=[1200])
        df = pd.read_parquet(out_path)
        assert df["turbo_speed"].between(10_000, 200_000).all()
        assert df["t_aftertreatment_inlet"].between(350, 900).all()


def test_units_are_si():
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "healthy.parquet"
        build_healthy_baseline(out_path=out_path, speeds=[1200])
        df = pd.read_parquet(out_path)
        # Pressures: kPa absolute, expect 50-500 range
        assert df["boost_pressure"].between(50, 500).all()
        # Temps: Kelvin, T_intake should be 250-350 K (ambient-ish)
        assert df["t_intake"].between(250, 400).all()
        # Exhaust temp: 500-1000 K
        assert df["t_exhaust_manifold"].between(400, 1100).all()


# ---------- Hybrid augmentation tests (Phase 1.5) ----------

def test_source_column_has_both_real_and_syn_values():
    """Hybrid healthy must carry provenance: some rows navic_real, some syn_baseline."""
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "healthy.parquet"
        build_healthy_baseline(
            out_path=out_path,
            speeds=[1200],
            aug_rpms=[800.0, 2000.0],
            aug_loads=[0.25, 0.50],
            aug_samples_per_cell=5,
        )
        df = pd.read_parquet(out_path)
        assert "source" in df.columns, "source provenance column missing"
        sources = set(df["source"].unique())
        assert "navic_real" in sources, f"no navic_real rows; got {sources}"
        assert "syn_baseline" in sources, f"no syn_baseline rows; got {sources}"


def test_syn_baseline_covers_every_requested_grid_cell():
    """For every (rpm, load) pair in the augmentation grid, at least one syn row exists."""
    aug_rpms = [800.0, 1000.0, 2400.0]
    aug_loads = [0.25, 0.50, 1.00]
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "healthy.parquet"
        build_healthy_baseline(
            out_path=out_path,
            speeds=[1200],
            aug_rpms=aug_rpms,
            aug_loads=aug_loads,
            aug_samples_per_cell=3,
        )
        df = pd.read_parquet(out_path)
        syn = df[df["source"] == "syn_baseline"]
        # Bin syn rpms to nearest 100 because syn-engine adds noise around setpoint
        syn_rpm_binned = (syn["engine_rpm"] / 100).round() * 100
        for rpm in aug_rpms:
            for load in aug_loads:
                cell_rows = syn[
                    (syn_rpm_binned == rpm)
                    & (syn["load_fraction"].round(2) == round(load, 2))
                ]
                assert len(cell_rows) > 0, f"no syn_baseline row at rpm={rpm}, load={load}"


def test_augmentation_row_count_matches_cells_times_samples():
    """Syn rows = len(aug_rpms) * len(aug_loads) * samples_per_cell."""
    aug_rpms = [800.0, 2400.0]
    aug_loads = [0.25, 1.00]
    samples = 7
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "healthy.parquet"
        build_healthy_baseline(
            out_path=out_path,
            speeds=[1200],
            aug_rpms=aug_rpms,
            aug_loads=aug_loads,
            aug_samples_per_cell=samples,
        )
        df = pd.read_parquet(out_path)
        expected = len(aug_rpms) * len(aug_loads) * samples
        actual = (df["source"] == "syn_baseline").sum()
        assert actual == expected, f"expected {expected} syn rows, got {actual}"

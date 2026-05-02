"""Smoke test for run_stage2.py CLI."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


RESIDUALS = Path("leakfusion/data/residuals.parquet")
CUSUM_CONFIG = Path("leakfusion/models/cusum_config.json")
LEAK_DATA = Path("leakfusion/data/leak_labeled.parquet")
ML_MODELS_DIR = Path("leakfusion/models")
ML_ARTIFACTS = ["stage3_zone_rf.joblib", "stage3_severity_xgb.joblib", "stage3_features_schema.json"]


@pytest.mark.skipif(not RESIDUALS.exists() or not CUSUM_CONFIG.exists(),
                    reason="Residuals/cusum_config not built")
def test_run_stage2_cli_emits_valid_json(tmp_path):
    out = tmp_path / "alerts.json"
    result = subprocess.run(
        [
            "python", "-m", "leakfusion.scripts.run_stage2",
            "--residuals", str(RESIDUALS),
            "--cusum-config", str(CUSUM_CONFIG),
            "--out", str(out),
            "--persistence-seconds", "3.0",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"CLI failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    assert out.exists()
    payload = json.loads(out.read_text())
    assert payload["schema_version"] == "stage2-v1"
    assert "events" in payload
    # At least one CRITICAL event must fire on the leak runs
    crit = [e for e in payload["events"] if e["tier"] == "CRITICAL"]
    assert len(crit) >= 1, "Expected >=1 CRITICAL event on leak_labeled.parquet replay"


@pytest.mark.skipif(
    not RESIDUALS.exists() or not CUSUM_CONFIG.exists() or not LEAK_DATA.exists()
    or not all((ML_MODELS_DIR / a).exists() for a in ML_ARTIFACTS),
    reason="Residuals/cusum_config/leak_data/Stage 3 models not built"
)
def test_run_stage2_cli_emits_ml_augmented_payload(tmp_path):
    """When --source-data and --ml-models-dir are passed, AlertEvents carry ml_* fields."""
    out = tmp_path / "alerts_ml.json"
    result = subprocess.run(
        [
            sys.executable, "-m", "leakfusion.scripts.run_stage2",
            "--residuals", str(RESIDUALS),
            "--cusum-config", str(CUSUM_CONFIG),
            "--source-data", str(LEAK_DATA),
            "--ml-models-dir", str(ML_MODELS_DIR),
            "--out", str(out),
            "--persistence-seconds", "3.0",
        ],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"CLI failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    payload = json.loads(out.read_text())
    assert payload["schema_version"] == "stage2-v2"
    assert payload["ml_augmented"] is True
    crit = [e for e in payload["events"] if e["tier"] == "CRITICAL"]
    assert len(crit) >= 1
    # At least one CRITICAL event must have produced an ml_decision (not all skipped/uncertain).
    decided = [e for e in crit if e.get("ml_status") == "ml_decision"]
    assert len(decided) >= 1, (
        f"Expected >=1 ml_decision among {len(crit)} CRITICAL events; "
        f"got {len(decided)}"
    )
    sample = decided[0]
    assert sample["predicted_zone"] in {"zone1", "zone2", "zone3a", "zone3b", "zone4"}
    assert 0.0 <= sample["predicted_severity"] <= 0.15
    assert isinstance(sample["predicted_severity_ci"], list)
    assert len(sample["predicted_severity_ci"]) == 2

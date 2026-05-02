"""Stage 3 end-to-end: trained models + Stage 2 detector -> augmented AlertEvent on a real leak run."""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest


@pytest.fixture(scope="module")
def trained_models():
    """Load Stage 3 artifacts. Skip if not yet trained."""
    models_dir = Path("leakfusion/models")
    needed = ["stage3_zone_rf.joblib", "stage3_severity_xgb.joblib", "stage3_features_schema.json"]
    if not all((models_dir / n).exists() for n in needed):
        pytest.skip("Stage 3 models not yet trained; run train_stage3.py first.")
    zone_clf = joblib.load(models_dir / "stage3_zone_rf.joblib")
    sev_bundle = joblib.load(models_dir / "stage3_severity_xgb.joblib")
    schema = json.loads((models_dir / "stage3_features_schema.json").read_text())
    return zone_clf, sev_bundle["model"], float(sev_bundle["sigma"]), schema


def test_zone1_run_predicts_zone1_with_high_proba(trained_models):
    """Pick rows from leak_labeled where leak_zone=='zone1', verify ML predicts zone1 most of the time."""
    from leakfusion.src.ml.features import build_feature_frame
    from leakfusion.src.ml.predict import ZoneSeverityPredictor

    zone_clf, sev_reg, sev_sigma, schema = trained_models
    df = pd.read_parquet("leakfusion/data/leak_labeled.parquet")
    df = df[df["leak_zone"] == "zone1"].sample(n=200, random_state=42).reset_index(drop=True)

    X, _, _, _ = build_feature_frame(df, "leakfusion/models/calibration.json")
    predictor = ZoneSeverityPredictor(
        zone_clf=zone_clf, severity_reg=sev_reg, severity_sigma=sev_sigma,
        feature_columns=schema["feature_columns"],
    )

    decisions = []
    for i in range(len(X)):
        out = predictor.predict_from_features(X.iloc[[i]].to_numpy(), op_point_extrapolated=False)
        decisions.append(out)

    decided = [d for d in decisions if d["ml_status"] == "ml_decision"]
    correct = [d for d in decided if d["predicted_zone"] == "zone1"]
    # At least 60% of high-confidence decisions must hit zone1.
    if decided:
        assert len(correct) / len(decided) >= 0.6, (
            f"Only {len(correct)}/{len(decided)} ml_decisions hit zone1"
        )
    # And severity should be in [0, 0.15] for all decisions
    for d in decided:
        assert 0.0 <= d["predicted_severity"] <= 0.15

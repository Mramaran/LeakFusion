"""Stage 3 — sim-to-real audit on healthy_baseline + per-zone leak slice eval."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from leakfusion.src.ml.features import FEATURE_COLUMNS, build_feature_frame


def _load_models(models_dir: Path):
    zone_clf = joblib.load(models_dir / "stage3_zone_rf.joblib")
    sev_bundle = joblib.load(models_dir / "stage3_severity_xgb.joblib")
    return zone_clf, sev_bundle["model"], float(sev_bundle["sigma"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models-dir", required=True)
    p.add_argument("--healthy-data", required=True)
    p.add_argument("--leak-data", required=True)
    p.add_argument("--calibration", default="leakfusion/models/calibration.json")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    zone_clf, sev_reg, sev_sigma = _load_models(Path(args.models_dir))

    # Sim-to-real audit: predict severity on healthy_baseline real rows.
    healthy = pd.read_parquet(args.healthy_data)
    if "source" in healthy.columns:
        healthy = healthy[healthy["source"] == "navic_real"].copy()
    # Inject placeholder leak label so build_feature_frame doesn't drop them.
    healthy["leak_zone"] = "zone1"
    healthy["leak_severity"] = 0.0
    Xh, _, _, _ = build_feature_frame(healthy, args.calibration)
    sev_pred_healthy = sev_reg.predict(Xh.to_numpy())
    healthy_mean_sev = float(np.clip(sev_pred_healthy, 0.0, 0.15).mean())

    # Per-zone severity check on leak slice.
    leak = pd.read_parquet(args.leak_data)
    Xl, y_zone, y_sev, _ = build_feature_frame(leak, args.calibration)
    by_zone = {}
    for zone in sorted(set(y_zone)):
        mask = y_zone == zone
        zone_pred = zone_clf.predict(Xl.to_numpy()[mask])
        sev_pred = sev_reg.predict(Xl.to_numpy()[mask])
        by_zone[zone] = {
            "n": int(mask.sum()),
            "zone_recall": float((zone_pred == zone).mean()),
            "mean_predicted_severity": float(sev_pred.mean()),
            "mean_true_severity": float(y_sev[mask].mean()),
        }

    out = {
        "healthy_mean_predicted_severity": healthy_mean_sev,
        "healthy_n_rows": int(len(Xh)),
        "by_zone": by_zone,
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"[stage3] Audit: healthy mean severity = {healthy_mean_sev:.4f} (target < 0.005)")
    for zone, stats in by_zone.items():
        print(f"[stage3] {zone}: recall={stats['zone_recall']:.3f}, "
              f"sev_pred={stats['mean_predicted_severity']:.4f} vs true={stats['mean_true_severity']:.4f}")


if __name__ == "__main__":
    main()

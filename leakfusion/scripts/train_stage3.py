"""Stage 3 — train zone classifier + severity regressor on leak_labeled.parquet."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from leakfusion.src.ml.evaluate import (
    bootstrap_macro_f1_ci,
    bootstrap_mae_ci,
    expected_calibration_error,
    macro_f1,
    mae,
)
from leakfusion.src.ml.features import FEATURE_COLUMNS, ZONE_NAMES, build_feature_frame
from leakfusion.src.ml.severity_regressor import train_severity
from leakfusion.src.ml.splits import held_out_test_indices
from leakfusion.src.ml.zone_classifier import train_zone


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--leak-data", required=True)
    p.add_argument("--calibration", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--report-out", required=True)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[stage3] Loading {args.leak_data}")
    df = pd.read_parquet(args.leak_data)
    X, y_zone, y_sev, groups = build_feature_frame(df, args.calibration)
    print(f"[stage3] After dropping no_leak: {len(X)} rows, {len(set(groups))} unique runs")

    test_idx, train_idx = held_out_test_indices(
        X.to_numpy(), y_zone, groups, n_splits=5, seed=args.seed
    )
    Xt = X.iloc[train_idx]
    Xv = X.iloc[test_idx]
    yt_zone, yv_zone = y_zone[train_idx], y_zone[test_idx]
    yt_sev, yv_sev = y_sev[train_idx], y_sev[test_idx]
    gt = groups[train_idx]

    print(f"[stage3] Training zone classifier on {len(Xt)} rows...")
    zone_clf = train_zone(Xt.to_numpy(), yt_zone, gt, seed=args.seed)
    print(f"[stage3] Training severity regressor on {len(Xt)} rows...")
    sev_reg, sev_sigma = train_severity(Xt.to_numpy(), yt_sev, gt, seed=args.seed)

    print(f"[stage3] Evaluating on {len(Xv)} held-out rows...")
    zone_pred = zone_clf.predict(Xv.to_numpy())
    zone_proba = zone_clf.predict_proba(Xv.to_numpy())
    sev_pred = sev_reg.predict(Xv.to_numpy())

    f1 = macro_f1(yv_zone, zone_pred)
    f1_lo, f1_hi = bootstrap_macro_f1_ci(yv_zone, zone_pred, n_resamples=200, seed=args.seed)
    ece = expected_calibration_error(yv_zone, zone_proba, list(zone_clf.classes_))
    sev_mae = mae(yv_sev, sev_pred)
    sev_mae_lo, sev_mae_hi = bootstrap_mae_ci(yv_sev, sev_pred, n_resamples=200, seed=args.seed)

    print(f"[stage3] zone macro-F1 = {f1:.4f} (95% CI [{f1_lo:.4f}, {f1_hi:.4f}])")
    print(f"[stage3] zone ECE = {ece:.4f}")
    print(f"[stage3] severity MAE = {sev_mae:.4f} (95% CI [{sev_mae_lo:.4f}, {sev_mae_hi:.4f}])")
    print(f"[stage3] severity sigma = {sev_sigma:.4f}")

    joblib.dump(zone_clf, out_dir / "stage3_zone_rf.joblib")
    joblib.dump({"model": sev_reg, "sigma": sev_sigma}, out_dir / "stage3_severity_xgb.joblib")
    with open(out_dir / "stage3_features_schema.json", "w") as f:
        json.dump({"feature_columns": FEATURE_COLUMNS, "zone_names": ZONE_NAMES}, f, indent=2)

    report = {
        "zone": {
            "macro_f1": float(f1),
            "macro_f1_ci_95": [float(f1_lo), float(f1_hi)],
            "ece": float(ece),
            "n_test": int(len(Xv)),
        },
        "severity": {
            "mae": float(sev_mae),
            "mae_ci_95": [float(sev_mae_lo), float(sev_mae_hi)],
            "sigma": float(sev_sigma),
            "n_test": int(len(Xv)),
        },
        "n_train": int(len(Xt)),
        "n_train_groups": int(len(set(gt))),
        "seed": args.seed,
    }
    with open(args.report_out, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[stage3] Wrote report to {args.report_out}")


if __name__ == "__main__":
    main()

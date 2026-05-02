"""CLI: replay residuals.parquet through Stage 2 detector, emit alerts.json.

Usage:
    python -m leakfusion.scripts.run_stage2 \\
        --residuals leakfusion/data/residuals.parquet \\
        --cusum-config leakfusion/models/cusum_config.json \\
        --out leakfusion/data/alerts.json \\
        --persistence-seconds 3.0

Optional Stage 3 ML augmentation (predicts zone + severity on each emitted
event):
    python -m leakfusion.scripts.run_stage2 \\
        --residuals leakfusion/data/residuals.parquet \\
        --cusum-config leakfusion/models/cusum_config.json \\
        --source-data leakfusion/data/leak_labeled.parquet \\
        --ml-models-dir leakfusion/models \\
        --out leakfusion/data/alerts.json \\
        --persistence-seconds 3.0

When --source-data and --ml-models-dir are both provided AND the model
artifacts exist, each AlertEvent in the output is augmented with predicted
zone, severity, and CI. Otherwise events have ml_status="ml_skipped".

Each (rpm_bin, load_bin, leak_zone, leak_severity) tuple is one independent
run; detector state is reset between groups. Runs in this dataset are 100
samples (10s @ 10Hz), so the default 60s persistence would never fire CRITICAL
on these short runs — pass --persistence-seconds 3.0 (or similar) for the
demo path.
"""
from __future__ import annotations
import argparse
import json
import math
from dataclasses import asdict
from pathlib import Path

import joblib
import pandas as pd

from leakfusion.src.detection.cusum import CusumChannel
from leakfusion.src.detection.detector import LeakDetector


def _build_detector(cusum_config: dict, sample_rate_hz: float = 10.0,
                    persistence_seconds: float = 60.0,
                    predictor=None) -> LeakDetector:
    channels = {}
    for residual, cfg in cusum_config["channels"].items():
        channels[residual] = CusumChannel(name=residual, k=cfg["k"], h=cfg["h"])
    return LeakDetector(
        channels=channels,
        sample_rate_hz=sample_rate_hz,
        persistence_samples=int(persistence_seconds * sample_rate_hz),
        idle_holdoff_samples=int(5.0 * sample_rate_hz),
        cooldown_samples=int(10.0 * sample_rate_hz),
        predictor=predictor,
    )


def _maybe_load_predictor(models_dir: Path):
    """Load Stage 3 ZoneSeverityPredictor if all artifacts are present, else None."""
    needed = ["stage3_zone_rf.joblib", "stage3_severity_xgb.joblib", "stage3_features_schema.json"]
    if not all((models_dir / n).exists() for n in needed):
        return None, None
    from leakfusion.src.ml.predict import ZoneSeverityPredictor

    zone_clf = joblib.load(models_dir / "stage3_zone_rf.joblib")
    sev_bundle = joblib.load(models_dir / "stage3_severity_xgb.joblib")
    schema = json.loads((models_dir / "stage3_features_schema.json").read_text())
    predictor = ZoneSeverityPredictor(
        zone_clf=zone_clf,
        severity_reg=sev_bundle["model"],
        severity_sigma=float(sev_bundle["sigma"]),
        feature_columns=schema["feature_columns"],
    )
    return predictor, schema


def _z_dict_from_row(row: pd.Series) -> dict[str, float | None]:
    """Convert one residuals.parquet row to z_scores dict, mapping NaN to None."""
    out = {}
    for i in range(1, 7):
        v = row[f"z_R{i}"]
        if v is None or (isinstance(v, float) and math.isnan(v)):
            out[f"R{i}"] = None
        else:
            out[f"R{i}"] = float(v)
    return out


def _meta_from_row(row: pd.Series) -> dict:
    return {
        "rpm_bin": int(row["rpm_bin"]),
        "load_bin": float(row["load_bin"]),
        "leak_zone": str(row["leak_zone"]),
        "leak_severity": float(row["leak_severity"]),
        "op_point_extrapolated": bool(row.get("op_point_extrapolated", False)),
    }


def run_stage2(residuals_df: pd.DataFrame, cusum_config: dict,
               persistence_seconds: float = 60.0,
               predictor=None,
               source_df: pd.DataFrame | None = None) -> list[dict]:
    """Run Stage 2 over residuals_df grouped by (rpm_bin, load_bin, zone, severity).

    Each group is a separate run with fresh detector state.

    If `predictor` and `source_df` are both provided, each emitted AlertEvent
    is augmented with Stage 3 ML fields (predicted zone, severity, CI). source_df
    must be the original sensor parquet aligned by row_index.

    Returns list of AlertEvent dicts in chronological order.
    """
    group_cols = ["rpm_bin", "load_bin", "leak_zone", "leak_severity"]
    df = residuals_df.sort_values(group_cols).reset_index(drop=True)
    all_events: list[dict] = []

    use_ml = predictor is not None and source_df is not None
    if use_ml:
        from leakfusion.src.ml.features import build_feature_row

    for keys, grp in df.groupby(group_cols, sort=False):
        det = _build_detector(cusum_config, persistence_seconds=persistence_seconds,
                              predictor=predictor)
        for _, row in grp.iterrows():
            z = _z_dict_from_row(row)
            meta = _meta_from_row(row)
            extrap = bool(row.get("op_point_extrapolated", False))
            if use_ml:
                src_row = source_df.iloc[int(row["row_index"])]
                feats = build_feature_row(row, src_row).reshape(1, -1)
                ev = det.update(z, meta, row_features=feats, op_point_extrapolated=extrap)
            else:
                ev = det.update(z, meta)
            if ev is None:
                continue
            ev_dict = asdict(ev)
            ev_dict["tier"] = ev.tier.value
            if isinstance(ev_dict.get("predicted_severity_ci"), tuple):
                ev_dict["predicted_severity_ci"] = list(ev_dict["predicted_severity_ci"])
            ev_dict["run_keys"] = dict(zip(group_cols, [
                int(keys[0]), float(keys[1]), str(keys[2]), float(keys[3])
            ]))
            all_events.append(ev_dict)
    return all_events


def _main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--residuals", default="leakfusion/data/residuals.parquet")
    ap.add_argument("--cusum-config", default="leakfusion/models/cusum_config.json")
    ap.add_argument("--out", default="leakfusion/data/alerts.json")
    ap.add_argument("--persistence-seconds", type=float, default=60.0,
                    help="Sustained-signature time required for CRITICAL "
                         "(default 60s; use ~3s for short synthetic runs).")
    ap.add_argument("--source-data", default=None,
                    help="Optional: path to original sensor parquet (e.g. leak_labeled.parquet) "
                         "for Stage 3 ML feature lookup. Required for ML augmentation.")
    ap.add_argument("--ml-models-dir", default="leakfusion/models",
                    help="Directory holding stage3_*.joblib model artifacts. "
                         "If artifacts are missing, ML augmentation is skipped.")
    ap.add_argument("--no-ml", action="store_true",
                    help="Disable Stage 3 ML augmentation even if artifacts and source-data are present.")
    args = ap.parse_args()

    df = pd.read_parquet(args.residuals)
    cfg_path = Path(args.cusum_config)
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"{cfg_path} not found. Run: "
            f"python -m leakfusion.scripts.tune_cusum --out {cfg_path}"
        )
    cusum_config = json.loads(cfg_path.read_text())

    predictor = None
    source_df = None
    if not args.no_ml and args.source_data is not None:
        predictor, _ = _maybe_load_predictor(Path(args.ml_models_dir))
        if predictor is not None:
            source_df = pd.read_parquet(args.source_data).reset_index(drop=True)
            print(f"[stage3] ML augmentation enabled "
                  f"(source={args.source_data}, models={args.ml_models_dir})")
        else:
            print(f"[stage3] ML artifacts not found in {args.ml_models_dir}; "
                  f"running Stage 2 only.")

    events = run_stage2(df, cusum_config,
                        persistence_seconds=args.persistence_seconds,
                        predictor=predictor,
                        source_df=source_df)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "stage2-v2" if predictor is not None else "stage2-v1",
        "persistence_seconds": args.persistence_seconds,
        "ml_augmented": predictor is not None,
        "n_events": len(events),
        "events": events,
    }
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"Wrote {len(events)} events to {out_path}")

    # Per-zone CRITICAL summary
    crit = [e for e in events if e["tier"] == "CRITICAL"]
    print(f"CRITICAL events: {len(crit)}")
    by_zone: dict[str, int] = {}
    for e in crit:
        z = e["run_keys"]["leak_zone"]
        by_zone[z] = by_zone.get(z, 0) + 1
    for z, n in sorted(by_zone.items()):
        print(f"  {z}: {n} CRITICAL events")


if __name__ == "__main__":
    _main()

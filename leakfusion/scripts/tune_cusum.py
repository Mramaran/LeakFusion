"""CLI: tune per-residual CUSUM h on a held-out healthy validation slice.

Usage:
    python -m leakfusion.scripts.tune_cusum \\
        --residuals leakfusion/data/residuals.parquet \\
        --out leakfusion/models/cusum_config.json \\
        --target-far 0.01 \\
        --validation-fraction 0.2

The validation slice is the last 20% of no_leak rows (deterministic split).
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

import pandas as pd

from leakfusion.src.detection.tuning import tune_cusum_thresholds


def _main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--residuals", default="leakfusion/data/residuals.parquet")
    ap.add_argument("--out", default="leakfusion/models/cusum_config.json")
    ap.add_argument("--target-far", type=float, default=0.01)
    ap.add_argument("--validation-fraction", type=float, default=0.2)
    args = ap.parse_args()

    df = pd.read_parquet(args.residuals)
    nl = df[df["leak_zone"] == "no_leak"].reset_index(drop=True)
    n = len(nl)
    val_start = int(n * (1.0 - args.validation_fraction))
    val_slice = nl.iloc[val_start:].reset_index(drop=True)
    print(f"Using {len(val_slice)} no_leak rows for validation "
          f"(of {n} total no_leak rows).")

    z_streams = {f"R{i}": val_slice[f"z_R{i}"].values for i in range(1, 7)}

    config = tune_cusum_thresholds(z_streams, target_far=args.target_far)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "stage2-v1",
        "target_far": args.target_far,
        "validation_fraction": args.validation_fraction,
        "validation_n_total": n,
        "channels": config,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {out_path}")
    for r, cfg in config.items():
        print(f"  {r}: k={cfg['k']}, h={cfg['h']}, "
              f"FAR={cfg['FAR_measured']:.4f}, n={cfg['n_validation']}")


if __name__ == "__main__":
    _main()

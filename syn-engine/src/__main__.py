"""CLI entry point for the synthetic engine simulator.

Usage:
    python -m src --rpm 1800 --load 75 --duration 300 --output output.csv
    python -m src --rpm 1800 --load 75 --leak zone2 --severity 5 --output leaked.csv
    python -m src --batch --output dataset/generated/training_data.parquet
"""
import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="LeakFusion Synthetic Engine Simulator")
    parser.add_argument("--rpm", type=int, default=1200, help="Engine speed (RPM)")
    parser.add_argument("--load", type=int, default=75, help="Load percentage (0-100)")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--rate", type=float, default=10.0, help="Sample rate Hz")
    parser.add_argument("--leak", type=str, default="no_leak", help="Leak zone")
    parser.add_argument("--severity", type=float, default=0, help="Leak severity (percent)")
    parser.add_argument("--output", type=str, default="output.csv", help="Output file path")
    parser.add_argument("--batch", action="store_true", help="Generate full training set")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()

    from src.synthetic_engine import SyntheticEngine

    print("Initializing SyntheticEngine...")
    engine = SyntheticEngine()
    print("Calibrating against NavicEngine data...")
    engine.calibrate()
    print("Calibration complete.")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.batch:
        print("Generating full training dataset...")
        X, y_zone, y_sev, meta = engine.generate_training_set(seed=args.seed)
        # Combine into single DataFrame
        result = X.copy()
        result["zone"] = y_zone.values
        result["severity"] = y_sev.values
        result["source_rpm"] = meta["rpm"].values
        result["source_load"] = meta["load"].values

        if str(output_path).endswith(".parquet"):
            result.to_parquet(output_path, index=False)
        else:
            result.to_csv(output_path, index=False)
        print(f"Saved {len(result)} samples to {output_path}")
    else:
        print(f"Generating: RPM={args.rpm}, Load={args.load}%, "
              f"Leak={args.leak}, Severity={args.severity}%")
        df = engine.run(
            rpm=args.rpm,
            load_fraction=args.load / 100.0,
            duration_seconds=args.duration,
            sample_rate_hz=args.rate,
            leak_zone=args.leak,
            leak_severity=args.severity / 100.0,
            seed=args.seed,
        )
        if str(output_path).endswith(".parquet"):
            df.to_parquet(output_path, index=False)
        else:
            df.to_csv(output_path, index=False)
        print(f"Saved {len(df)} rows to {output_path}")


if __name__ == "__main__":
    main()

"""Load and preprocess NavicEngine PUMA test cell data.

Handles column mapping, unit conversion (gauge->absolute, kg/h->g/s, C->K),
and steady-state median extraction for calibration.
"""
import pandas as pd
import numpy as np
from src.constants import PUMA_DIR, PUMA_COLUMN_MAP, NAVIC_SPEEDS


def load_puma_nominal(speed: int) -> pd.DataFrame:
    """Load a PUMA NOMINAL file, map columns, convert to SI units.

    Args:
        speed: Engine speed (1000, 1200, 1400, or 1600).

    Returns:
        DataFrame with standard column names, SI units:
        - Mass flows in g/s
        - Pressures in kPa absolute
        - Temperatures in Kelvin
    """
    filepath = PUMA_DIR / f"SPEED_{speed}_NOMINAL.xlsx"
    if not filepath.exists():
        raise FileNotFoundError(f"PUMA file not found: {filepath}")

    # Row 0 = headers, row 1 = units, row 2 = descriptions, row 3+ = data
    df = pd.read_excel(filepath, header=0, skiprows=[1, 2])
    df = df.dropna(how="all")

    # Rename columns using mapping (reverse: PUMA_name -> our_name)
    reverse_map = {v: k for k, v in PUMA_COLUMN_MAP.items()}
    df = df.rename(columns={c: reverse_map[c] for c in df.columns if c in reverse_map})

    # Ensure numeric
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # --- Unit conversions ---

    # Mass flows: kg/h -> g/s
    if "maf_kgh" in df.columns:
        df["maf"] = df["maf_kgh"] / 3.6
    if "fuel_flow_kgh" in df.columns:
        df["fuel_flow"] = df["fuel_flow_kgh"] / 3.6

    # Ambient pressure: mbar -> kPa
    if "p_baro_mbar" in df.columns:
        df["ambient_pressure"] = df["p_baro_mbar"] / 10.0

    # Gauge pressures -> absolute (kPa)
    # PUMA pressures are gauge (relative to atmospheric)
    p_amb = df["ambient_pressure"] if "ambient_pressure" in df.columns else 101.325
    if "boost_pressure_gauge" in df.columns:
        df["boost_pressure"] = p_amb + df["boost_pressure_gauge"]
    if "comp_inlet_pressure_gauge" in df.columns:
        df["compressor_inlet_pressure"] = p_amb + df["comp_inlet_pressure_gauge"]
    # exhaust_manifold_pressure and exhaust_backpressure - add ambient for absolute
    if "exhaust_manifold_pressure" in df.columns:
        df["exhaust_manifold_pressure"] = p_amb + df["exhaust_manifold_pressure"]
    if "exhaust_backpressure" in df.columns:
        df["exhaust_backpressure"] = p_amb + df["exhaust_backpressure"]
    if "turbine_outlet_pressure" in df.columns:
        df["turbine_outlet_pressure"] = p_amb + df["turbine_outlet_pressure"]

    # Pressure ratio
    if "boost_pressure" in df.columns and "compressor_inlet_pressure" in df.columns:
        df["pressure_ratio"] = df["boost_pressure"] / df["compressor_inlet_pressure"].replace(0, np.nan)

    # Temperatures: degC -> Kelvin
    temp_map = {
        "t_comp_in_c": "t_intake",
        "t_comp_out_c": "t_boost",
        "t_after_cac_c": "t_after_intercooler",
        "t_int_man_c": "t_intake_manifold",
        "t_turb_out_c": "t_turbine_outlet",
        "t_cell_c": "ambient_temperature",
    }
    for src, dst in temp_map.items():
        if src in df.columns:
            df[dst] = df[src] + 273.15

    # Per-cylinder exhaust temps -> average for exhaust manifold
    cyl_cols_c = [f"t_exh_cyl_{i}_c" for i in range(1, 7)]
    existing_cyl = [c for c in cyl_cols_c if c in df.columns]
    if existing_cyl:
        df["t_exhaust_manifold"] = df[existing_cyl].mean(axis=1) + 273.15
        # Also keep individual cylinder temps in K
        for c in existing_cyl:
            i = c.split("_")[3]  # extract cylinder number
            df[f"t_exh_cyl_{i}"] = df[c] + 273.15

    return df


def extract_operating_points() -> pd.DataFrame:
    """Extract steady-state median sensor values at each NavicEngine speed.

    Returns:
        DataFrame with 4 rows (one per speed), median of each sensor column.
    """
    rows = []
    for speed in NAVIC_SPEEDS:
        df = load_puma_nominal(speed)
        medians = df.median(numeric_only=True).to_dict()
        medians["speed_setpoint"] = speed
        rows.append(medians)

    return pd.DataFrame(rows)

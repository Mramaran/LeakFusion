"""Physical constants and configuration for LeakFusion synthetic engine.

All values sourced from:
- Thermodynamics textbooks (gas properties)
- NavicEngine README (engine specs)
- docs/Physics_For_AI_Students.md (project physics reference)
"""
from pathlib import Path
import numpy as np

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent.parent.parent  # syn-engine -> Caterpillar root
DATA_DIR = PROJECT_ROOT / "dataset" / "NavicEngine"
PUMA_DIR = DATA_DIR / "processed_PUMA" / "processed_PUMA"

# --- Gas Properties (Standard Thermodynamics) ---
GAMMA_AIR = 1.4                     # Heat capacity ratio for air
GAMMA_EXHAUST = 1.35                # Heat capacity ratio for exhaust gas
R_AIR = 287.058                     # J/(kg*K) - specific gas constant for air
CP_AIR = 1005.0                     # J/(kg*K) - specific heat at constant pressure
CP_EXHAUST = 1100.0                 # J/(kg*K) - exhaust gas at ~500C
ISENTROPIC_EXP_AIR = (GAMMA_AIR - 1) / GAMMA_AIR          # 0.2857
ISENTROPIC_EXP_EXHAUST = (GAMMA_EXHAUST - 1) / GAMMA_EXHAUST  # 0.2593

# --- Fuel Properties ---
LHV_DIESEL = 42700.0               # J/g - Lower Heating Value of diesel
AFR_STOICH = 14.5                   # Stoichiometric air-fuel ratio for diesel

# --- NavicEngine Specs (from README) ---
DISPLACEMENT_LITERS = 7.6           # Inline-6, 7.6L Navistar DT
DISPLACEMENT_M3 = 0.0076            # m^3
NUM_CYLINDERS = 6
STROKES_PER_CYCLE = 4               # 4-stroke diesel

# --- Fixed Efficiency Estimates (Textbook Typical) ---
ETA_MECHANICAL = 0.88               # Mechanical efficiency
RADIATION_LOSS_FRACTION = 0.05      # ~5% of fuel energy lost to radiation

# --- Standard Ambient Conditions ---
P_AMB_STD = 101.325                 # kPa
T_AMB_STD = 298.15                  # K (25 degC)

# --- Available NavicEngine Speeds ---
NAVIC_SPEEDS = [1000, 1200, 1400, 1600]

# --- Leak Zones ---
LEAK_ZONES = ["no_leak", "zone1", "zone2", "zone3a", "zone3b", "zone4"]

# --- PUMA Column Mapping ---
# Maps our standard names -> NavicEngine PUMA column names
PUMA_COLUMN_MAP = {
    "engine_rpm": "SPEED",
    "torque": "TORQUE",
    "maf_kgh": "ENG_MF_LFE",
    "boost_pressure_gauge": "P_COMP_OUT",
    "comp_inlet_pressure_gauge": "P_COMP_IN",
    "exhaust_manifold_pressure": "P_EXH_MAN",
    "exhaust_backpressure": "P_BACKPRESSURE",
    "turbine_outlet_pressure": "P_TURB_OUT",
    "fuel_flow_kgh": "FB_VAL",
    "fuel_rail_pressure": "P_Fuel_Rail",
    "t_comp_in_c": "T_COMP_IN",
    "t_comp_out_c": "T_COMP_OUT",
    "t_after_cac_c": "T_ENG_AIR_down_CAC",
    "t_exh_cyl_1_c": "T_EXH_CYL_1",
    "t_exh_cyl_2_c": "T_EXH_CYL_2",
    "t_exh_cyl_3_c": "T_EXH_CYL_3",
    "t_exh_cyl_4_c": "T_EXH_CYL_4",
    "t_exh_cyl_5_c": "T_EXH_CYL_5",
    "t_exh_cyl_6_c": "T_EXH_CYL_6",
    "t_turb_out_c": "T_TURB_OUT",
    "t_int_man_c": "T_INT_MAN",
    "p_baro_mbar": "P_BARO",
    "t_cell_c": "T_CELL",
}

"""Canonical SI column schema for LeakFusion datasets.

Every parquet artifact emitted by Phase 1 conforms to this schema.
All pressures in kPa absolute, temperatures in K, flows in g/s.
"""

REQUIRED_COLUMNS = {
    # Operating point
    "engine_rpm",               # RPM
    "torque",                   # Nm

    # Intake path
    "maf",                      # g/s
    "boost_pressure",           # kPa absolute
    "intake_manifold_pressure", # kPa absolute (approx = boost - intercooler_dp)
    "turbo_speed",              # RPM (synthetic fill-in for NavicEngine)

    # Exhaust path
    "exhaust_manifold_pressure",# kPa absolute
    "exhaust_backpressure",     # kPa absolute
    "fuel_flow",                # g/s
    "lambda_sensor",            # ratio, calculated from MAF/fuel_flow

    # Temperatures
    "t_intake",                 # K
    "t_boost",                  # K
    "t_exhaust_manifold",       # K
    "t_turbine_outlet",         # K
    "t_aftertreatment_inlet",   # K (synthetic fill-in for NavicEngine)

    # Reference conditions
    "ambient_pressure",         # kPa absolute
    "ambient_temperature",      # K
}

OPTIONAL_COLUMNS = {
    "coolant_temperature",      # K
    "oil_temperature",          # K
    "oil_pressure",             # kPa
    "fuel_rail_pressure",       # kPa
    "timestamp",                # seconds
}

SYN_FILLED_COLUMNS = {
    "turbo_speed",
    "t_aftertreatment_inlet",
}

LABEL_COLUMNS = {
    "leak_zone",                # str, one of {"no_leak","zone1","zone2","zone3a","zone3b","zone4"}
    "leak_severity",            # float, 0.0 to 0.20
    "load_fraction",            # float, 0.0 to 1.0
}

PROVENANCE_TAG = {
    "engine_rpm": "real",
    "torque": "real",
    "maf": "real",
    "boost_pressure": "real",
    "intake_manifold_pressure": "derived",
    "turbo_speed": "synthetic",
    "exhaust_manifold_pressure": "real",
    "exhaust_backpressure": "real",
    "fuel_flow": "real",
    "lambda_sensor": "formula",
    "t_intake": "real",
    "t_boost": "real",
    "t_exhaust_manifold": "real",
    "t_turbine_outlet": "real",
    "t_aftertreatment_inlet": "synthetic",
    "ambient_pressure": "real",
    "ambient_temperature": "real",
}

"""Re-export physical constants from syn-engine plus Stage 1-specific additions.

One source of truth: anything syn-engine calibrates against must use the same
constants as Stage 1's residuals, otherwise residuals would reflect only the
constant drift, not actual sensor-vs-physics deviations.
"""
import sys
from pathlib import Path

_SYN_ENGINE = Path(__file__).parent.parent.parent.parent / "syn-engine"
if str(_SYN_ENGINE) not in sys.path:
    sys.path.insert(0, str(_SYN_ENGINE))

from src.constants import (  # noqa: E402
    GAMMA_AIR, GAMMA_EXHAUST,
    R_AIR, CP_AIR, CP_EXHAUST,
    ISENTROPIC_EXP_AIR, ISENTROPIC_EXP_EXHAUST,
    LHV_DIESEL, AFR_STOICH,
    DISPLACEMENT_M3, NUM_CYLINDERS, STROKES_PER_CYCLE,
    ETA_MECHANICAL, RADIATION_LOSS_FRACTION,
    P_AMB_STD, T_AMB_STD,
)

# Stage 1-specific additions (not in syn-engine)
D_COMPRESSOR = 0.08  # m, Navistar DT turbo compressor tip diameter (typical dual-stage)
DEFAULT_ETA_C = 0.75  # Compressor isentropic efficiency nominal (CIMAC Rec. 27)
DEFAULT_PHI_COOLANT = 0.25  # Fraction of fuel energy lost to coolant (ICCT 2014)

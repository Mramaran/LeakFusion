"""Stage 1 physics residuals.

One module per residual: R1 intake mass, R2 boost balance, R3 exhaust mass,
R4 aftertreatment ΔP, R5 lambda, R6 thermal balance.

See docs/stage1/STAGE1_DESIGN.md for the physics derivations.
"""
from .orchestrator import compute_residuals  # noqa: F401

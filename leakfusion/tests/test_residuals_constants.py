"""constants.py re-exports physical constants from syn-engine — one source of truth."""
from leakfusion.src.residuals import constants as rc


def test_gas_constants_present():
    assert rc.GAMMA_AIR == 1.4
    assert rc.R_AIR == 287.058
    assert rc.CP_AIR == 1005.0
    assert rc.CP_EXHAUST == 1100.0


def test_fuel_constants_present():
    assert rc.LHV_DIESEL == 42700.0
    assert rc.AFR_STOICH == 14.5


def test_engine_spec_present():
    assert rc.DISPLACEMENT_M3 == 0.0076


def test_isentropic_exponents():
    assert abs(rc.ISENTROPIC_EXP_AIR - 0.2857) < 1e-4
    assert abs(rc.ISENTROPIC_EXP_EXHAUST - 0.2593) < 1e-4


def test_stage1_specific_constants():
    assert rc.D_COMPRESSOR == 0.08  # m, Navistar DT turbo tip diameter
    assert rc.RADIATION_LOSS_FRACTION == 0.05

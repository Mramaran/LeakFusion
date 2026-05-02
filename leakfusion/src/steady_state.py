"""Steady-state detection for engine sensor streams.

A window is "steady" when RPM and torque vary less than configurable tolerances.
Transient windows (ramps, load changes) are filtered out before training
expected-value regressors to avoid fitting to dynamic noise.
"""
import pandas as pd


def is_steady_window(window: pd.DataFrame,
                     rpm_tol: float = 50.0,
                     torque_tol_pct: float = 5.0) -> bool:
    """Return True if a window's RPM range <= rpm_tol AND torque range <= torque_tol_pct%."""
    if "engine_rpm" not in window.columns or "torque" not in window.columns:
        raise KeyError("Window missing 'engine_rpm' or 'torque' column")

    rpm_range = window["engine_rpm"].max() - window["engine_rpm"].min()
    if rpm_range > rpm_tol:
        return False

    torque_mean = window["torque"].mean()
    if abs(torque_mean) < 1e-6:
        return True  # idle, no torque swing possible
    torque_range = window["torque"].max() - window["torque"].min()
    torque_pct = 100.0 * torque_range / abs(torque_mean)
    return bool(torque_pct <= torque_tol_pct)


def filter_steady_state(df: pd.DataFrame,
                        window: int = 10,
                        rpm_tol: float = 50.0,
                        torque_tol_pct: float = 5.0) -> pd.DataFrame:
    """Keep only rows whose surrounding window of size `window` is steady.

    Args:
        df: DataFrame sorted by time, must contain engine_rpm and torque.
        window: Number of consecutive samples examined per check.
        rpm_tol: Max RPM range allowed within window.
        torque_tol_pct: Max torque range as percent of mean allowed within window.

    Returns:
        Filtered DataFrame with same columns as input. Index reset.
    """
    if len(df) < window:
        return df.iloc[0:0].copy()

    keep_mask = [False] * len(df)
    for i in range(len(df) - window + 1):
        win = df.iloc[i:i + window]
        if is_steady_window(win, rpm_tol=rpm_tol, torque_tol_pct=torque_tol_pct):
            for j in range(i, i + window):
                keep_mask[j] = True

    return df.loc[keep_mask].reset_index(drop=True)

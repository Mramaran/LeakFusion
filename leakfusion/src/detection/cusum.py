"""Two-sided tabular CUSUM with hysteresis (Page 1954 + Bosch §3.5 + ASHRAE G36).

For each residual, two accumulators track positive and negative drift:
  c_pos[t] = max(0, c_pos[t-1] + z[t] - k)
  c_neg[t] = max(0, c_neg[t-1] - z[t] - k)

Channel fires when either accumulator exceeds h (rising edge entry).
Hysteresis: once fired, stays fired while max(c_pos, c_neg) > 0.7 * h
(30% deadband per Bosch handbook §3.5 / ASHRAE Guideline 36).

NaN handling (Isermann §7.2.1): NaN samples return False without mutating state.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math


HYSTERESIS_FRACTION = 0.7  # exit threshold = HYSTERESIS_FRACTION * h


@dataclass
class CusumState:
    c_pos: float = 0.0
    c_neg: float = 0.0
    was_fired: bool = False  # tracks hysteresis state


@dataclass
class CusumChannel:
    name: str
    k: float
    h: float
    state: CusumState = field(default_factory=CusumState)

    def update(self, z: float | None) -> bool:
        """One-sample step. Returns True iff channel is currently fired."""
        if z is None or (isinstance(z, float) and math.isnan(z)):
            return False  # NaN: no state mutation, no fire
        self.state.c_pos = max(0.0, self.state.c_pos + z - self.k)
        self.state.c_neg = max(0.0, self.state.c_neg - z - self.k)
        cusum_max = max(self.state.c_pos, self.state.c_neg)
        exit_threshold = HYSTERESIS_FRACTION * self.h
        if self.state.was_fired:
            # Stay fired until below hysteresis exit threshold
            if cusum_max < exit_threshold:
                self.state.was_fired = False
                return False
            return True
        # Not previously fired — enter on rising edge above h
        if cusum_max > self.h:
            self.state.was_fired = True
            return True
        return False

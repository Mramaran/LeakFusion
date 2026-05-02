"""Stage 2 LeakDetector — orchestrator + state machine + AlertEvent + recommendations.

Components:
- Tier: enum WARN | CRITICAL
- AlertEvent: dataclass output payload
- ZONE_RECOMMENDATIONS: zone -> human-readable inspection guidance
- recommendation_for(): join recommendations for multi-zone candidate sets
- LeakDetector: stateful per-row detector (added in Task 5)

See docs/plans/2026-05-01-stage2-design.md §4.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional

from leakfusion.src.detection.cusum import CusumChannel
from leakfusion.src.detection.signatures import match_signature


class Tier(Enum):
    WARN = "WARN"
    CRITICAL = "CRITICAL"


@dataclass
class AlertEvent:
    event_id: str
    timestamp_idx: int
    timestamp_s: float
    tier: Tier
    fired_residuals: list[str]
    candidate_zones: list[str]
    signature_status: Literal["matched", "novel"]
    confidence: Literal["high", "medium", "low"]
    time_above_threshold_s: dict[str, float]
    explanation: str
    recommendation: str
    op_point: dict
    ml_status: Literal["ml_decision", "ml_uncertain", "ml_skipped"] = "ml_skipped"
    predicted_zone: Optional[str] = None
    predicted_zone_proba: Optional[float] = None
    predicted_severity: Optional[float] = None
    predicted_severity_ci: Optional[tuple[float, float]] = None
    predicted_severity_clipped: bool = False


ZONE_RECOMMENDATIONS: dict[str, str] = {
    "zone1":  "Inspect intake manifold gasket and pre-compressor ducting",
    "zone2":  "Inspect post-compressor / intercooler joints; thermal-only signature",
    "zone3a": "Inspect exhaust manifold gasket and pre-turbine seals",
    "zone3b": "Inspect post-turbine pipe and aftertreatment inlet flange",
    "zone4":  "Inspect test-cell ducting at compressor inlet",
}


def recommendation_for(candidate_zones: set[str],
                       signature_status: Literal["matched", "novel"]) -> str:
    """Build a human-readable recommendation string for the alert payload."""
    if signature_status == "novel" or not candidate_zones:
        return ("Pattern not in known zone catalog; "
                "Stage 4 novelty detection required for classification.")
    recs = sorted({ZONE_RECOMMENDATIONS[z] for z in candidate_zones if z in ZONE_RECOMMENDATIONS})
    if len(recs) == 1:
        return recs[0]
    return " OR ".join(recs)


class _State:
    IDLE = "idle"
    WARN = "warn"
    CRITICAL_PENDING = "critical_pending"
    CRITICAL = "critical"
    COOLDOWN = "cooldown"


@dataclass
class LeakDetector:
    channels: dict[str, CusumChannel]
    sample_rate_hz: float = 10.0
    persistence_samples: int = 600       # 60s @ 10Hz
    idle_holdoff_samples: int = 50       # 5s @ 10Hz
    cooldown_samples: int = 100          # 10s @ 10Hz
    predictor: object = None             # Optional Stage 3 ZoneSeverityPredictor

    # Mutable state
    _state: str = field(default=_State.IDLE, init=False)
    _persistence_count: int = field(default=0, init=False)
    _last_candidates: frozenset[str] = field(default_factory=frozenset, init=False)
    _idle_holdoff_count: int = field(default=0, init=False)
    _cooldown_count: int = field(default=0, init=False)
    _t: int = field(default=0, init=False)
    _channel_first_fire_t: dict[str, int] = field(default_factory=dict, init=False)

    def update(self, z_scores: dict[str, float | None],
               row_meta: dict,
               *,
               row_features=None,
               op_point_extrapolated: bool = False) -> Optional[AlertEvent]:
        """Process one row. Returns an AlertEvent on tier transitions, else None.

        If `predictor` is set and `row_features` is provided, the emitted event
        is augmented with Stage 3 ML fields (predicted_zone, severity, etc.).
        """
        self._t += 1

        # 1. Update each channel
        fired_set = set()
        for name, ch in self.channels.items():
            if ch.update(z_scores.get(name)):
                fired_set.add(name)
                if name not in self._channel_first_fire_t:
                    self._channel_first_fire_t[name] = self._t
            else:
                self._channel_first_fire_t.pop(name, None)
        fired_frozen = frozenset(fired_set)

        # 2. Match signature
        candidates = match_signature(fired_frozen)
        candidates_frozen = frozenset(candidates)
        signature_status: str = "matched" if candidates else ("novel" if fired_frozen else "matched")

        # 3. Step state machine
        emit_tier: Optional[Tier] = None

        if self._state == _State.COOLDOWN:
            self._cooldown_count += 1
            if self._cooldown_count >= self.cooldown_samples:
                self._state = _State.IDLE
                self._cooldown_count = 0

        if self._state == _State.IDLE:
            if fired_frozen:
                self._state = _State.WARN
                emit_tier = Tier.WARN

        elif self._state == _State.WARN:
            if not fired_frozen:
                self._idle_holdoff_count += 1
                if self._idle_holdoff_count >= self.idle_holdoff_samples:
                    self._state = _State.IDLE
                    self._idle_holdoff_count = 0
                    self._last_candidates = frozenset()
            else:
                self._idle_holdoff_count = 0
                if candidates_frozen:
                    self._state = _State.CRITICAL_PENDING
                    self._last_candidates = candidates_frozen
                    self._persistence_count = 1

        elif self._state == _State.CRITICAL_PENDING:
            if not fired_frozen:
                self._idle_holdoff_count += 1
                if self._idle_holdoff_count >= self.idle_holdoff_samples:
                    self._state = _State.IDLE
                    self._reset_pending()
            elif candidates_frozen != self._last_candidates:
                # Signature changed — drop back to WARN, reset persistence
                self._state = _State.WARN
                self._persistence_count = 0
                self._last_candidates = frozenset()
            else:
                self._persistence_count += 1
                if self._persistence_count >= self.persistence_samples:
                    self._state = _State.CRITICAL
                    emit_tier = Tier.CRITICAL

        elif self._state == _State.CRITICAL:
            if not fired_frozen:
                self._idle_holdoff_count += 1
                if self._idle_holdoff_count >= self.idle_holdoff_samples:
                    self._state = _State.COOLDOWN
                    self._reset_pending()

        # 4. Emit event if tier transitioned upward
        if emit_tier is None:
            return None
        event = self._build_alert(emit_tier, fired_frozen, candidates_frozen,
                                  signature_status, row_meta)
        if self.predictor is not None and row_features is not None:
            ml = self.predictor.predict_from_features(
                row_features, op_point_extrapolated=op_point_extrapolated
            )
            event.ml_status = ml["ml_status"]
            event.predicted_zone = ml.get("predicted_zone")
            event.predicted_zone_proba = ml.get("predicted_zone_proba")
            event.predicted_severity = ml.get("predicted_severity")
            event.predicted_severity_ci = ml.get("predicted_severity_ci")
            event.predicted_severity_clipped = ml.get("predicted_severity_clipped", False)
        return event

    def _reset_pending(self) -> None:
        self._persistence_count = 0
        self._idle_holdoff_count = 0
        self._last_candidates = frozenset()

    def _build_alert(self, tier: Tier, fired: frozenset[str],
                     candidates: frozenset[str], signature_status: str,
                     row_meta: dict) -> AlertEvent:
        nz = len(candidates)
        if nz == 1:
            confidence = "high"
        elif 2 <= nz <= 3:
            confidence = "medium"
        else:
            confidence = "low"

        time_above = {
            r: (self._t - self._channel_first_fire_t.get(r, self._t)) / self.sample_rate_hz
            for r in fired
        }

        zones_str = "/".join(sorted(c.replace("zone", "") for c in candidates)) if candidates else "novel"
        explanation = (
            f"{', '.join(sorted(fired))} elevated; "
            f"pattern matches zone {zones_str}"
            if candidates else
            f"{', '.join(sorted(fired))} elevated; signature is novel (no known zone match)"
        )

        return AlertEvent(
            event_id=str(uuid.uuid4()),
            timestamp_idx=self._t,
            timestamp_s=self._t / self.sample_rate_hz,
            tier=tier,
            fired_residuals=sorted(fired),
            candidate_zones=sorted(candidates),
            signature_status=signature_status,
            confidence=confidence,
            time_above_threshold_s=time_above,
            explanation=explanation,
            recommendation=recommendation_for(set(candidates), signature_status),
            op_point=row_meta,
        )

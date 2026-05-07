from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Residuals(BaseModel):
    r1: float
    r2: float
    r3: float
    r4: float
    r5: float
    r6: float


class ZoneProbabilities(BaseModel):
    zone1: float = Field(ge=0.0, le=1.0)
    zone2: float = Field(ge=0.0, le=1.0)
    zone3a: float = Field(ge=0.0, le=1.0)
    zone3b: float = Field(ge=0.0, le=1.0)
    zone4: float = Field(ge=0.0, le=1.0)


HDBStatus = Literal["Known Pattern", "Unknown — flag for review"]
BackendZone = Literal["zone1", "zone2", "zone3a", "zone3b", "zone4"]
EventTier = Literal["WARN", "CRITICAL"]


class Reading(BaseModel):
    timestamp: str
    reading_index: int
    rpm: int
    load_percent: float
    is_steady_state: bool
    residuals: Residuals
    zone_probabilities: ZoneProbabilities
    detected_zone: Optional[BackendZone]
    severity: int = Field(ge=0, le=5)
    cusum_score: float
    hdbscan_status: HDBStatus
    alert_triggered: bool
    leak_probability: int = Field(ge=0, le=100)
    # event_tier mirrors Streamlit's 3-state status banner:
    #   None      -> ALL CLEAR  (no event covering this frame)
    #   "WARN"    -> EARLY WARNING (yellow — investigate, do not pulse 3D)
    #   "CRITICAL"-> LEAK CONFIRMED (red — full alert path, alert_triggered=True)
    event_tier: Optional[EventTier] = None


class SampleListItem(BaseModel):
    key: str
    label: str
    icon: str


class ProcessResponse(BaseModel):
    sample_label: str
    readings: list[Reading]
    event_count: int

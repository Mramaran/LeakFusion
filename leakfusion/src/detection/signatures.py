"""Zone signature table per syn-engine §10.4 + multi-residual matching.

Reference: docs/plans/2026-04-14-synthetic-engine-design.md §10.4
("Leak Signature Correctness").
"""
from __future__ import annotations


ZONE_SIGNATURES: dict[str, frozenset[str]] = {
    "zone1":  frozenset({"R1", "R2"}),   # boost down, MAF same
    "zone2":  frozenset({"R6"}),         # T_exh up, boost same
    "zone3a": frozenset({"R1", "R2"}),   # exh manifold P down AND boost down (boost-drop component)
    "zone3b": frozenset({"R4"}),         # only backpressure down
    "zone4":  frozenset({"R1", "R2"}),   # comp_in down
}


def match_signature(fired: frozenset[str]) -> set[str]:
    """Return the set of zones whose signature is a subset of `fired`.

    Subset matching (not exact) supports compound leaks (multiple zones fired
    simultaneously) and prefix-matches sparse residual events.
    """
    if not fired:
        return set()
    return {zone for zone, sig in ZONE_SIGNATURES.items() if sig.issubset(fired)}

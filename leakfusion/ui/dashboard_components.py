"""Streamlit render components + pure payload builders for the demo dashboard.

Render functions take a Streamlit context and write widgets. Payload builders
are pure (dict in, dict out) and unit-tested.
"""
from __future__ import annotations

from leakfusion.src.demo.derived_fields import (
    ZONE_DISPLAY,
    confidence_pct,
    decision,
    severity_label,
)


def build_status_banner_payload(events: list[dict]) -> dict:
    """Pure: classify events into one of three banner variants."""
    if not events:
        return {
            "variant": "all_clear",
            "headline": "ALL CLEAR",
            "subline": "All 6 residuals within +/-2 sigma",
            "color": "green",
            "decision": "GO",
        }

    critical = [e for e in events if e.get("tier") == "CRITICAL"]
    if not critical:
        latest_warn = events[-1]
        zones = ", ".join(latest_warn.get("candidate_zones", []))
        return {
            "variant": "warn_only",
            "headline": "EARLY WARNING - investigate",
            "subline": f"Candidate zones: {zones}",
            "color": "yellow",
        }

    latest = critical[-1]
    zone = latest.get("predicted_zone") or "unknown"
    sev = latest.get("predicted_severity")
    return {
        "variant": "leak_confirmed",
        "headline": "LEAK CONFIRMED",
        "zone_label": ZONE_DISPLAY.get(zone, zone),
        "confidence": confidence_pct(latest.get("predicted_zone_proba")),
        "severity_label": severity_label(sev) if sev is not None else "n/a",
        "decision": decision(latest),
        "color": "red",
    }


def render_status_banner(st, events: list[dict]) -> None:
    """Render the top status banner using Streamlit primitives."""
    p = build_status_banner_payload(events)
    # Saturated backgrounds + white text — readable in both light and dark themes.
    bg = {"green": "#1e7e34", "yellow": "#b8860b", "red": "#c82333"}[p["color"]]
    border = {"green": "#155724", "yellow": "#856404", "red": "#721c24"}[p["color"]]

    if p["variant"] == "all_clear":
        body = f"<b>{p['headline']}</b> &nbsp; {p['subline']} &nbsp;|&nbsp; Decision: <b>{p['decision']}</b>"
    elif p["variant"] == "warn_only":
        body = f"<b>{p['headline']}</b> &nbsp; {p['subline']}"
    else:  # leak_confirmed
        body = (
            f"<b>{p['headline']}</b> &nbsp; <b>{p['zone_label']}</b> &nbsp;|&nbsp; "
            f"Confidence: <b>{p['confidence']}</b> &nbsp;|&nbsp; "
            f"Severity: <b>{p['severity_label']}</b> &nbsp;|&nbsp; "
            f"Decision: <b>{p['decision']}</b>"
        )
    st.markdown(
        f"<div style='padding:14px;border:2px solid {border};background:{bg};"
        f"color:#ffffff;border-radius:6px;font-size:1.05em'>{body}</div>",
        unsafe_allow_html=True,
    )


import pandas as pd

from leakfusion.src.demo.derived_fields import residual_status_badge


_RESIDUAL_NAMES = {
    "R1": "Intake Mass Flow",
    "R2": "Boost Pressure",
    "R3": "Exhaust Mass",
    "R4": "AT Pressure Drop",
    "R5": "Lambda",
    "R6": "Thermal Balance",
}


def build_residual_bars_payload(residuals_df: pd.DataFrame, event: dict) -> list[dict]:
    """Build one bar-row per residual: {name, label, z_value, badge, color}.

    z_value = the sample with the largest |z| in the residuals_df (signed).
    """
    fired = set(event.get("fired_residuals", []))
    primary = None
    primary_abs = -1.0
    for r in fired:
        col = f"z_{r}"
        if col not in residuals_df.columns:
            continue
        peak = residuals_df[col].abs().max()
        if pd.notna(peak) and peak > primary_abs:
            primary_abs = peak
            primary = r

    rows = []
    for i in range(1, 7):
        name = f"R{i}"
        col = f"z_{name}"
        series = residuals_df[col].dropna() if col in residuals_df.columns else pd.Series(dtype=float)
        if len(series) == 0:
            z_signed = 0.0
        else:
            idx = series.abs().idxmax()
            z_signed = float(series.loc[idx])
        badge, color = residual_status_badge(name, z_signed, fired, primary)
        rows.append({
            "name": name,
            "label": _RESIDUAL_NAMES[name],
            "z_value": round(z_signed, 2),
            "badge": badge,
            "color": color,
        })
    return rows


def render_residual_bars(st, residuals_df: pd.DataFrame, event: dict) -> None:
    """Render the 6-bar horizontal Plotly chart with status badges."""
    import plotly.graph_objects as go

    rows = build_residual_bars_payload(residuals_df, event)
    fig = go.Figure()
    for r in rows:
        fig.add_trace(go.Bar(
            x=[r["z_value"]],
            y=[f"{r['name']}  {r['label']}"],
            orientation="h",
            marker_color={"green": "#34a853", "orange": "#f29900", "red": "#d93025"}[r["color"]],
            text=[f"{r['z_value']:+.1f} sigma"],
            textposition="outside",
            hoverinfo="skip",
            showlegend=False,
        ))
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(range=[-6, 6], zeroline=True, zerolinecolor="#888",
                   tickvals=[-3, -2, 0, 2, 3], color="#1f2937"),
        yaxis=dict(autorange="reversed", color="#1f2937"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#1f2937"),
    )
    st.plotly_chart(fig, use_container_width=True)

    cols = st.columns(6)
    for i, r in enumerate(rows):
        bg = {"green": "#1e7e34", "orange": "#b8860b", "red": "#c82333"}[r["color"]]
        cols[i].markdown(
            f"<div style='text-align:center;padding:4px;background:{bg};"
            f"color:#ffffff;border-radius:4px;font-size:0.85em'>"
            f"<b>{r['name']}</b><br>{r['badge']}</div>",
            unsafe_allow_html=True,
        )


from leakfusion.src.demo.recommendations import get_action


def build_recommendation_payload(event: dict | None) -> dict:
    if event is None:
        return get_action("no_leak")
    if event.get("tier") == "CRITICAL" and event.get("predicted_zone"):
        return get_action(event["predicted_zone"])
    candidates = event.get("candidate_zones", [])
    if candidates:
        return get_action(candidates[0])
    return get_action("no_leak")


def render_recommendation(st, event: dict | None) -> None:
    p = build_recommendation_payload(event)
    bullets_html = "".join(f"<li>{b}</li>" for b in p["bullets"])
    st.markdown(
        f"<div style='padding:12px;background:#b8860b;border-left:6px solid #856404;"
        f"color:#ffffff;border-radius:4px'>"
        f"<b>Recommended Action:</b> {p['headline']}"
        f"<ul style='margin-top:6px;margin-bottom:0'>{bullets_html}</ul>"
        f"</div>",
        unsafe_allow_html=True,
    )


def build_timeline_payload(events: list[dict], duration_s: float) -> dict:
    markers = []
    for i, e in enumerate(events):
        markers.append({
            "index": i,
            "t": float(e.get("timestamp_s", 0.0)),
            "tier": e.get("tier", "WARN"),
            "zone": e.get("predicted_zone") or
                    (e.get("candidate_zones", [None]) or [None])[0]
                    or "unknown",
        })
    default_index = None
    crit_idx = [i for i, e in enumerate(events) if e.get("tier") == "CRITICAL"]
    if crit_idx:
        default_index = crit_idx[-1]
    elif events:
        default_index = len(events) - 1
    return {"markers": markers, "duration_s": duration_s, "default_index": default_index}


def render_timeline_strip(st, events: list[dict], duration_s: float,
                          selected_index: int | None) -> int | None:
    """Render the bottom timeline strip. Returns the (possibly updated) selected index."""
    import plotly.graph_objects as go

    p = build_timeline_payload(events, duration_s)
    if not p["markers"]:
        st.markdown("_No events detected during this run._")
        return None

    fig = go.Figure()
    for m in p["markers"]:
        color = "#d93025" if m["tier"] == "CRITICAL" else "#fbbc04"
        fig.add_trace(go.Scatter(
            x=[m["t"]], y=[0],
            mode="markers+text",
            marker=dict(size=18, color=color, symbol="circle"),
            text=[f"{m['tier']}<br>{m['zone']}<br>{m['t']:.1f}s"],
            textposition="bottom center",
            hoverinfo="text",
            hovertext=f"Event {m['index']}: {m['tier']} {m['zone']}",
            showlegend=False,
        ))
    fig.update_layout(
        height=180, margin=dict(l=10, r=10, t=10, b=50),
        xaxis=dict(range=[0, duration_s], title="seconds", color="#1f2937"),
        yaxis=dict(visible=False, range=[-1, 1]),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#1f2937"),
    )
    st.plotly_chart(fig, use_container_width=True)

    return st.number_input(
        "Jump to event #",
        min_value=0,
        max_value=len(events) - 1,
        value=selected_index if selected_index is not None else (p["default_index"] or 0),
        step=1,
    )

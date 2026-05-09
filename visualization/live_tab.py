"""Streamlit Live Status tab for train 169 (WebSocket-backed)."""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

import extraction_pipeline.live_client as live_client

TRAIN_NO = "169"
REFRESH_INTERVAL_MS = 30_000

CACHE_DIR = Path.home() / ".cache" / "train_analysis"
RUNHASH_CACHE_PATH = CACHE_DIR / "runhash_169.json"
SHARE_URL_HINT = (
    "https://ttsview.railway.co.th/v3/search/?qType=21&qParam=<runhash>&auth=..."
)


def _load_runhash_cache() -> Optional[dict]:
    try:
        return json.loads(RUNHASH_CACHE_PATH.read_text())
    except Exception:
        return None


def _save_runhash_cache(runhash: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RUNHASH_CACHE_PATH.write_text(
        json.dumps({"runhash": runhash, "date": date.today().isoformat()}, indent=2)
    )


def _is_filled(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in {"", "-", "0", "None"}
    return True


def _resolve_current_index(stations: list[dict]) -> int:
    last_arrived = -1
    for i, s in enumerate(stations):
        if _is_filled(s.get("act_arrtime")):
            last_arrived = i
    if last_arrived == -1:
        return 0
    if last_arrived < len(stations) - 1 and _is_filled(stations[last_arrived].get("act_deptime")):
        return last_arrived + 1
    return last_arrived


def _coerce_int(value) -> Optional[int]:
    try:
        if value in (None, "", "-"):
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _status_color(delay_min: Optional[int]) -> tuple[str, str]:
    if delay_min is None:
        return ("Unknown", "#64748b")
    if delay_min <= 5:
        return ("On time", "#10b981")
    if delay_min <= 30:
        return ("Slight delay", "#f59e0b")
    return ("Major delay", "#f43f5e")


def _hhmm_add(base: str, minutes: int) -> str:
    try:
        h, m = map(int, base.split(":")[:2])
    except Exception:
        return base
    total = h * 60 + m + (minutes or 0)
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def _runhash_input_form() -> Optional[str]:
    """Prompt the user for today's train-169 runhash. Cache for the day."""
    cached = _load_runhash_cache()
    today = date.today().isoformat()
    if cached and cached.get("date") == today and cached.get("runhash"):
        return cached["runhash"]

    st.info(
        "Live tracking needs today's runhash for train 169. "
        "On https://ttsview.railway.co.th/v3/ click the train 169 row to open its tracking page, "
        "then paste the share URL (or just the `qParam` value) below. "
        "Cached locally for the rest of the day."
    )

    raw = st.text_input(
        "Share URL or runhash",
        placeholder=SHARE_URL_HINT,
        help="Either the full /v3/search/?qType=21&qParam=... URL, or just the qParam string.",
    )
    if not raw:
        return None

    candidate = live_client.parse_url_for_runhash(raw) or raw.strip()
    if len(candidate) < 16:
        st.error("That doesn't look like a runhash. Expected at least 16 characters.")
        return None

    _save_runhash_cache(candidate)
    st.success(f"Runhash cached for {today}.")
    return candidate


def render_live_tab() -> None:
    st.markdown("### Live Status — Train 169")
    st.caption(
        "Streams real-time tracking from ttsview.railway.co.th over WebSocket. "
        "Refreshes every 30 seconds while this tab is open."
    )

    runhash = _runhash_input_form()
    if not runhash:
        return

    try:
        from streamlit_autorefresh import st_autorefresh

        st_autorefresh(interval=REFRESH_INTERVAL_MS, key="live_169_refresh")
    except ImportError:
        if st.button("Refresh now"):
            st.rerun()

    col_meta, col_action = st.columns([3, 1])
    with col_action:
        if st.button("Reset runhash"):
            try:
                RUNHASH_CACHE_PATH.unlink(missing_ok=True)
            except Exception:
                pass
            st.rerun()

    try:
        stations = live_client.fetch_train_stations(runhash)
    except Exception as e:
        st.error(f"Failed to fetch live data: {e}")
        return

    if not stations:
        st.warning(
            "No station data returned. The runhash may be from a different day "
            "or train. Try resetting and pasting today's URL."
        )
        return

    cur_idx = _resolve_current_index(stations)
    cur = stations[cur_idx]
    cur_delay = _coerce_int(cur.get("act_arr_late") or cur.get("act_dep_late"))
    status_label, status_color = _status_color(cur_delay)
    status_th = cur.get("status_name_th") or cur.get("status_name_en") or ""
    last_update = cur.get("latesttime") or time.strftime("%Y-%m-%d %H:%M:%S")

    with col_meta:
        st.markdown(
            f"""
            <div style="background:#ffffff;padding:1.2rem;border-radius:1rem;
                       border-left:6px solid {status_color};margin-bottom:1rem;">
                <span style="color:#64748b;font-size:0.75rem;text-transform:uppercase;
                            letter-spacing:0.1em;">Current Status</span>
                <div style="font-size:1.5rem;font-weight:700;color:#0f172a;margin-top:0.25rem;">
                    {status_label} &nbsp;·&nbsp; {cur.get('stop_name', '')}
                </div>
                <div style="color:#475569;margin-top:0.5rem;">
                    Latest delay: <strong>{cur_delay if cur_delay is not None else '—'} min</strong>
                    &nbsp;·&nbsp; {status_th}
                    &nbsp;·&nbsp; updated {last_update}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    progress = (cur_idx + 1) / len(stations)
    st.progress(progress, text=f"Station {cur_idx + 1}/{len(stations)}")

    rows = []
    for i, s in enumerate(stations):
        passed = i < cur_idx or (i == cur_idx and _is_filled(s.get("act_deptime")))
        is_current = i == cur_idx and not passed
        arr_late = _coerce_int(s.get("act_arr_late"))

        if passed:
            marker = "✓"
        elif is_current:
            marker = "▶"
        else:
            marker = "·"

        # Live ETA: prefer actual, then estimated, then schedule + propagated delay
        live_arr = (
            s.get("act_arrtime")
            or s.get("est_arrtime")
            or _hhmm_add(s.get("def_arrtime", ""), cur_delay or 0)
        )
        live_dep = (
            s.get("act_deptime")
            or s.get("est_deptime")
            or _hhmm_add(s.get("def_deptime", ""), cur_delay or 0)
        )

        rows.append(
            {
                "": marker,
                "Station": s.get("stop_name", ""),
                "Sched. Arr": s.get("def_arrtime", "—"),
                "Live Arr": live_arr,
                "Sched. Dep": s.get("def_deptime", "—"),
                "Live Dep": live_dep,
                "Delay (m)": arr_late if arr_late is not None else "—",
                "Status": s.get("status_name_th", ""),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("Raw current-station record (debug)"):
        st.json(cur)

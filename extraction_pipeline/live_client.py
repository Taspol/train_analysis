"""
WebSocket client for ttsview.railway.co.th live tracking.

The SRT search page (/v3/search/) connects to a Socket.IO server at
:5000 and emits `viewSubTrain` with a runhash to receive the per-station
status array. This bypasses the Cloudflare Turnstile gate and the JWT
auth flow that the REST endpoints require.

Public functions:
    fetch_train_stations(runhash) -> list[dict]
    parse_url_for_runhash(url) -> str | None
"""

from __future__ import annotations

import threading
from typing import Optional
from urllib.parse import urlparse, parse_qs

import socketio

SOCKET_URL = "https://ttsview.railway.co.th:5000"
DEFAULT_TIMEOUT = 15.0


def fetch_train_stations(runhash: str, timeout: float = DEFAULT_TIMEOUT) -> list[dict]:
    """Connect, emit viewSubTrain, wait for the callback payload, disconnect."""
    sio = socketio.Client(logger=False, engineio_logger=False, reconnection=False)
    payload: dict = {"data": None}
    done = threading.Event()

    def cb(arg):
        payload["data"] = arg
        done.set()

    try:
        sio.connect(SOCKET_URL, transports=["websocket"], wait_timeout=timeout)
        sio.emit("viewSubTrain", runhash, callback=cb)
        if not done.wait(timeout=timeout):
            raise TimeoutError(f"viewSubTrain callback did not return within {timeout}s")
    finally:
        try:
            sio.disconnect()
        except Exception:
            pass

    data = payload["data"]
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "stations" in data:
        return data["stations"]
    return []


def parse_url_for_runhash(url: str) -> Optional[str]:
    """Pull the runhash out of a /v3/search/?qType=21&qParam=... share link."""
    try:
        q = parse_qs(urlparse(url.strip()).query)
    except Exception:
        return None
    candidate = (q.get("qParam") or [None])[0]
    if candidate and len(candidate) >= 16:
        return candidate
    return None

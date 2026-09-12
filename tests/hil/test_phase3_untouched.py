"""If Phase 3 is still answering on :8080, it must look like the frozen demo."""

from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request

import pytest

pytestmark = pytest.mark.hil

HOST = os.environ.get("CERTARIG_PHASE3_HOST", "certarig-pi.local")
PORT = int(os.environ.get("CERTARIG_PHASE3_PORT", "8080"))


def _reachable() -> bool:
    try:
        socket.create_connection((HOST, PORT), timeout=1.5).close()
        return True
    except OSError:
        return False


def test_phase3_port_is_still_the_frozen_dashboard() -> None:
    if not _reachable():
        pytest.skip(f"Phase 3 host {HOST}:{PORT} is off or not on this LAN")
    request = urllib.request.Request(f"http://{HOST}:{PORT}/health", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        pytest.skip(f"could not read Phase 3 /health: {exc}")
    try:
        health = json.loads(body)
    except json.JSONDecodeError:
        health = {}
    assert "ready_to_arm" not in health, (
        f"{HOST}:{PORT} looks like the new platform. Phase 3 must stay on live-dashboard until 21 Sep."
    )

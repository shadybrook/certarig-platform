"""Hardware-in-the-loop. Skipped unless the wave-1 Pi answers on the LAN."""

from __future__ import annotations

import os
import socket

import pytest

from certarig.edge.client import EdgeClient

pytestmark = pytest.mark.hil

HOST = os.environ.get("CERTARIG_HIL_HOST", "certarig-pi.local")
PORT = int(os.environ.get("CERTARIG_HIL_PORT", "8080"))


def _reachable() -> bool:
    try:
        socket.create_connection((HOST, PORT), timeout=1.5).close()
        return True
    except OSError:
        return False


@pytest.fixture(scope="module")
def bench() -> EdgeClient:
    if not _reachable():
        pytest.skip(f"HIL bench {HOST}:{PORT} is not reachable (Pi is powered off or not on this LAN)")
    key = os.environ.get("CERTARIG_OPERATOR_KEY")
    if not key:
        pytest.skip("CERTARIG_OPERATOR_KEY is not set for the HIL bench")
    return EdgeClient(f"http://{HOST}:{PORT}", operator_key=key, principal_name="hil")


def test_bench_health_is_the_wave1_pi(bench: EdgeClient) -> None:
    health = bench.health()
    assert health["hardware_mode"] == "raspberry_pi"
    assert health["status"] == "ok"
    assert bench.rig()["signals"]

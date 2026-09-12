"""Platform HIL. Skipped unless a *platform* Edge node answers.

Default port is 8081 so Phase 3's live-dashboard on :8080 is never mistaken
for this product. `make check` never requires the Pi.
"""

from __future__ import annotations

import os
import socket

import pytest

from certarig.edge.client import EdgeClient

pytestmark = pytest.mark.hil

HOST = os.environ.get("CERTARIG_HIL_HOST", "certarig-pi.local")
PORT = int(os.environ.get("CERTARIG_HIL_PORT", "8081"))


def _reachable() -> bool:
    try:
        socket.create_connection((HOST, PORT), timeout=1.5).close()
        return True
    except OSError:
        return False


@pytest.fixture(scope="module")
def bench() -> EdgeClient:
    if not _reachable():
        pytest.skip(f"platform HIL {HOST}:{PORT} is not reachable (optional lab, not required)")
    key = os.environ.get("CERTARIG_OPERATOR_KEY")
    if not key:
        pytest.skip("CERTARIG_OPERATOR_KEY is not set for the platform HIL")
    client = EdgeClient(f"http://{HOST}:{PORT}", operator_key=key, principal_name="hil")
    health = client.health()
    if "ready_to_arm" not in health:
        pytest.skip(f"{HOST}:{PORT} is not a CertaRig platform node (missing ready_to_arm)")
    return client


def test_bench_health_is_this_platform(bench: EdgeClient) -> None:
    health = bench.health()
    assert health["status"] == "ok"
    assert "ready_to_arm" in health
    assert "contract_hash" in health
    assert bench.rig()["signals"]

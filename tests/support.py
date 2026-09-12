"""Shared test helpers: a controllable fake rig and an in-process Edge server."""

from __future__ import annotations

import contextlib
import tempfile
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from certarig.edge.bootstrap import NodeSettings as _NodeSettings
from certarig.edge.bootstrap import build_node
from certarig.edge.client import EdgeClient
from certarig.edge.config import load_config
from certarig.edge.hardware.base import HardwareAdapter
from certarig.edge.models import RigConfig, RigSnapshot, Sample
from certarig.edge.server import EdgeNode, make_edge_server

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
STUDIO_DIR = ROOT / "studio"
SKILLS_DIR = ROOT / "skills"
OPERATOR_KEY = "test-operator-key-0001"
AGENT_KEY = "test-agent-key-000001"


class ControllableRig(HardwareAdapter):
    """A hand-driven rig: tests set pressure, flow, estop and faults directly."""

    def __init__(self, config: RigConfig) -> None:
        self.config = config
        self.values: dict[str, float] = {}
        self.quality: dict[str, str] = {}
        for channel in config.channels:
            self.values[channel.channel_id] = (channel.safe_min + channel.safe_max) / 2
            self.quality[channel.channel_id] = "good"
        self.estop = False
        self.output = False
        self.closed = False
        self.fail_on_set = False
        self.drop_channels: set[str] = set()
        self.raise_on_snapshot = False

    def set(self, channel_id: str, value: float, quality: str = "good") -> None:
        self.values[channel_id] = value
        self.quality[channel_id] = quality

    def snapshot(self) -> RigSnapshot:
        if self.raise_on_snapshot:
            raise RuntimeError("sensor bus failure")
        now = datetime.now(UTC).isoformat()
        samples = tuple(
            Sample(
                channel_id=channel.channel_id,
                value=self.values[channel.channel_id],
                unit=channel.unit,
                raw_value=None,
                quality=self.quality[channel.channel_id],
                captured_at=now,
            )
            for channel in self.config.channels
            if channel.channel_id not in self.drop_channels
        )
        return RigSnapshot(
            rig_id=self.config.rig_id,
            config_hash=self.config.config_hash,
            emergency_stop_active=self.estop,
            output_safe=not self.output,
            samples=samples,
            captured_at=now,
        )

    def set_valve(self, open_state: bool) -> None:
        if self.fail_on_set and open_state:
            raise RuntimeError("driver failure")
        if open_state and self.estop:
            raise RuntimeError("emergency stop is active")
        self.output = bool(open_state)

    def force_safe_state(self) -> None:
        self.output = False

    def output_is_safe(self) -> bool:
        return not self.output

    def close(self) -> None:
        self.output = False
        self.closed = True


@dataclass
class RunningEdge:
    node: EdgeNode
    url: str
    rig: ControllableRig
    evidence_dir: Path

    def operator(self, name: str = "tester") -> EdgeClient:
        return EdgeClient(self.url, operator_key=OPERATOR_KEY, principal_name=name)

    def agent(self, name: str = "agent-under-test") -> EdgeClient:
        return EdgeClient(self.url, agent_key=AGENT_KEY, principal_name=name)

    def anonymous(self) -> EdgeClient:
        return EdgeClient(self.url)


@contextlib.contextmanager
def edge_server(
    config_name: str = "rig.wave1.json",
    capabilities_name: str | None = "capabilities.wave1.json",
    *,
    static: bool = True,
    agent_key: str | None = AGENT_KEY,
    start_loop: bool = False,
    skills_dir: Path | None = SKILLS_DIR,
) -> Iterator[RunningEdge]:
    with tempfile.TemporaryDirectory() as temp:
        config_path = CONFIG_DIR / config_name
        config = load_config(config_path)
        rig = ControllableRig(config)
        settings = _NodeSettings(
            config_path=config_path,
            capabilities_path=CONFIG_DIR / capabilities_name if capabilities_name else None,
            evidence_dir=Path(temp) / "evidence",
            static_root=STUDIO_DIR if static else None,
            operator_key=OPERATOR_KEY,
            agent_key=agent_key,
            allow_output=True,
        )
        node = build_node(settings, hardware=rig)
        procedures = node.extensions.get("procedures")
        if procedures is not None and skills_dir is not None and skills_dir.is_dir():
            procedures.load_library(skills_dir)
        server = make_edge_server(node, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        if start_loop:
            node.start()
        else:
            node.runtime.sample_once()
        try:
            yield RunningEdge(node, f"http://127.0.0.1:{server.server_port}", rig, Path(temp) / "evidence")
        finally:
            server.shutdown()
            server.server_close()
            node.close()

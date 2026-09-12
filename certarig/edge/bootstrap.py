"""Build a fully wired :class:`EdgeNode` from configuration files.

Used by the CLI, the tests and the simulator runner so that every entry point
constructs the node the same way.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .capabilities import CapabilityManifest
from .config import load_config
from .hardware.base import HardwareAdapter
from .hardware.mock import MockHardware
from .live import LiveBenchRuntime
from .models import RigConfig
from .server import EdgeNode

DEFAULT_STUDIO_ROOT = Path(__file__).resolve().parents[2] / "studio"
DEFAULT_SKILLS_ROOT = Path(__file__).resolve().parents[2] / "skills"


def build_hardware(config: RigConfig) -> HardwareAdapter:
    mode = config.hardware.mode
    if mode == "mock":
        return MockHardware(config)
    if mode == "simulator":
        from certarig.sim.plant import SimulatedRig

        return SimulatedRig(config)
    if mode == "raspberry_pi":
        from .hardware.raspberry_pi import RaspberryPiHardware

        return RaspberryPiHardware(config)
    raise ValueError(f"unsupported hardware mode: {mode}")


@dataclass(frozen=True)
class NodeSettings:
    config_path: Path
    capabilities_path: Path | None
    evidence_dir: Path
    static_root: Path | None
    operator_key: str
    agent_key: str | None
    allow_output: bool
    skills_root: Path | None = None
    poweroff_command: str | None = None

    @classmethod
    def from_env(
        cls,
        config_path: str | Path,
        capabilities_path: str | Path | None,
        evidence_dir: str | Path,
        static_root: str | Path | None = DEFAULT_STUDIO_ROOT,
        skills_root: str | Path | None = DEFAULT_SKILLS_ROOT,
    ) -> NodeSettings:
        operator_key = os.environ.get("CERTARIG_OPERATOR_KEY", "")
        if len(operator_key) < 12:
            raise SystemExit("CERTARIG_OPERATOR_KEY must be set to at least 12 characters")
        agent_key = os.environ.get("CERTARIG_AGENT_KEY") or None
        return cls(
            config_path=Path(config_path),
            capabilities_path=Path(capabilities_path) if capabilities_path else None,
            evidence_dir=Path(evidence_dir),
            static_root=Path(static_root) if static_root else None,
            operator_key=operator_key,
            agent_key=agent_key,
            allow_output=os.environ.get("CERTARIG_ENABLE_ACTUATION") == "1",
            skills_root=Path(skills_root) if skills_root else None,
            poweroff_command=os.environ.get("CERTARIG_POWEROFF_CMD") or None,
        )


def build_node(settings: NodeSettings, hardware: HardwareAdapter | None = None) -> EdgeNode:
    config = load_config(settings.config_path)
    manifest = (
        CapabilityManifest.load(settings.capabilities_path)
        if settings.capabilities_path
        else CapabilityManifest.read_only()
    )
    adapter = hardware or build_hardware(config)
    # Mock and simulator hardware can never energise anything real, so output is always allowed there.
    allow_output = settings.allow_output or config.hardware.mode in {"mock", "simulator"}
    runtime = LiveBenchRuntime(config, adapter, settings.evidence_dir, allow_output=allow_output)
    node = EdgeNode(
        runtime=runtime,
        manifest=manifest,
        operator_key=settings.operator_key,
        agent_key=settings.agent_key,
        static_root=settings.static_root,
    )
    from .procedures import install_procedures

    install_procedures(node, settings.skills_root)
    from .ops import install_ops, poweroff_command

    poweroff = poweroff_command(settings.poweroff_command) if settings.poweroff_command else None
    install_ops(node, poweroff)
    from certarig.sim.plant import SimulatedRig

    if isinstance(adapter, SimulatedRig):
        from certarig.sim.api import install_sim_api

        install_sim_api(node, adapter)
    from .agent_api import install_agent_api

    install_agent_api(node, settings.skills_root)
    return node

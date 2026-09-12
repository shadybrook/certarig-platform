"""Property-based tests: the kernel invariants hold for any sequence of observations and commands."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule

from certarig.edge.commissioning import ProcessGuardrail
from certarig.edge.config import load_config
from certarig.edge.live import LiveBenchRuntime
from certarig.edge.models import RigSnapshot, Sample
from certarig.sim.invariants import no_restart_without_reset, read_rows
from tests.support import CONFIG_DIR, ControllableRig, fast_config

CONFIG = load_config(CONFIG_DIR / "rig.wave1.json")

pressure_values = st.one_of(
    st.floats(min_value=-1.0, max_value=12.0, allow_nan=False),
    st.just(float("nan")),
    st.just(float("inf")),
)
flow_values = st.floats(min_value=-1.0, max_value=25.0, allow_nan=False)
qualities = st.sampled_from(["good", "good", "good", "bad", "stale"])
commands = st.sampled_from(["safe", "reset", "permit", "permit", "reset", "bogus"])


def make_snapshot(pressure: float, flow: float, estop: bool, quality: str, drop_flow: bool) -> RigSnapshot:
    now = datetime.now(UTC).isoformat()
    samples = [Sample("pressure_emulator", pressure, "bar", None, quality, now)]
    if not drop_flow:
        samples.append(Sample("flow_emulator", flow, "L/min", None, "good", now))
    return RigSnapshot(CONFIG.rig_id, CONFIG.config_hash, estop, True, tuple(samples), now)


class GuardrailMachine(RuleBasedStateMachine):
    """Drives ProcessGuardrail with random observations/commands and checks the safety contract."""

    def __init__(self) -> None:
        super().__init__()
        self.guardrail = ProcessGuardrail(CONFIG, allow_output=True)
        self.events: list[str] = []
        self.last_result = self.guardrail.result()

    @initialize()
    def start(self) -> None:
        self.guardrail = ProcessGuardrail(CONFIG, allow_output=True)
        self.events = []
        self.last_result = self.guardrail.result()

    @rule(
        pressure=pressure_values, flow=flow_values, estop=st.booleans(), quality=qualities, drop=st.booleans()
    )
    def observe(self, pressure: float, flow: float, estop: bool, quality: str, drop: bool) -> None:
        self.last_result = self.guardrail.observe(make_snapshot(pressure, flow, estop, quality, drop))
        if self.last_result.event:
            self.events.append(self.last_result.event)
        self.snapshot_unsafe = (
            estop
            or quality != "good"
            or drop
            or pressure != pressure  # nan
            or pressure in (float("inf"),)
            or not (0.0 <= pressure <= 4.2)
            or not (0.0 <= flow <= 15.0)
        )
        if self.snapshot_unsafe:
            assert self.last_result.drive_high is False, "output high on an unsafe observation"

    @rule(command=commands)
    def command(self, command: str) -> None:
        self.last_result = self.guardrail.command(command)
        if self.last_result.event:
            self.events.append(self.last_result.event)

    @invariant()
    def drive_high_needs_every_condition(self) -> None:
        g = self.guardrail
        assert g.drive_high == (
            g.allow_output
            and g.permit_requested
            and not g.trip_latched
            and not g.estop_active
            and g.process_healthy
        )
        if g.estop_active:
            assert not g.drive_high and g.trip_latched and not g.permit_requested

    @invariant()
    def no_restart_without_reset_in_events(self) -> None:
        assert no_restart_without_reset(self.events) == []


GuardrailMachine.TestCase.settings = settings(
    max_examples=150, stateful_step_count=40, deadline=None, suppress_health_check=[HealthCheck.too_slow]
)
TestGuardrailMachine = GuardrailMachine.TestCase


@given(
    st.lists(
        st.one_of(
            st.tuples(
                st.just("obs"),
                st.floats(0, 8, allow_nan=False),
                st.floats(0, 20, allow_nan=False),
                st.booleans(),
            ),
            st.tuples(
                st.just("cmd"), st.sampled_from(["safe", "reset", "permit"]), st.just(0.0), st.booleans()
            ),
        ),
        min_size=1,
        max_size=40,
    )
)
@settings(max_examples=60, deadline=None)
def test_runtime_output_mirrors_kernel_and_csv_is_complete(ops: list[tuple[str, float, float, bool]]) -> None:
    config = fast_config()
    rig = ControllableRig(config)
    with tempfile.TemporaryDirectory() as temp:
        runtime = LiveBenchRuntime(config, rig, Path(temp), allow_output=True)
        runtime.start_recording("property")
        expected_rows = 0
        for kind, a, b, flag in ops:
            if kind == "obs":
                rig.set("pressure_emulator", a)
                rig.set("flow_emulator", b)
                rig.estop = flag
                state = runtime.sample_once()
            else:
                state = runtime.command(str(a) if isinstance(a, str) else "safe")
            expected_rows += 1
            # the physical output always equals the commanded output
            assert rig.output == state["outputs"]["gpio23_command_high"]
            if kind == "obs" and (flag or float(a) > 4.2 or float(b) > 15.0):
                assert rig.output is False
            if rig.estop:
                assert rig.output is False
        stopped = runtime.stop_recording()
        assert stopped["completed_recording"]["samples"] == expected_rows
        rows = read_rows(runtime.latest_recording())  # type: ignore[arg-type]
        assert len(rows) == expected_rows
        assert no_restart_without_reset([r["event"] for r in rows if r["event"]]) == []
        runtime.close()
        assert rig.output is False and rig.closed

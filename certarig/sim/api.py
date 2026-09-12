"""Operator-only HTTP routes to drive the simulator (pots, E-stop, faults) from Studio or tests.

Only mounted when the node's hardware is a :class:`SimulatedRig`. These routes have no tool
name: the agent principal cannot touch the plant, exactly as it cannot touch a real bench.
"""

from __future__ import annotations

from typing import Any

from certarig.edge.capabilities import Principal
from certarig.edge.server import EdgeNode, HttpError, RequestContext

from .plant import SimulatedRig


def install_sim_api(node: EdgeNode, rig: SimulatedRig) -> None:
    def _operator(ctx: RequestContext) -> None:
        if ctx.principal is not Principal.OPERATOR:
            raise HttpError(403, "simulator controls are operator-only")

    def state(ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        return 200, {**rig.describe(), "faults": rig.faults(), "log_tail": rig.log[-20:]}

    def set_target(ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        _operator(ctx)
        try:
            rig.set_target(str(ctx.body["channel"]), float(ctx.body["value"]))
        except KeyError as exc:
            raise HttpError(400, f"missing or unknown field/channel: {exc}") from exc
        return 200, rig.describe()

    def ramp(ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        _operator(ctx)
        try:
            rig.ramp(str(ctx.body["channel"]), float(ctx.body["to"]), float(ctx.body.get("over_s", 1.0)))
        except KeyError as exc:
            raise HttpError(400, f"missing or unknown field/channel: {exc}") from exc
        return 200, rig.describe()

    def estop(ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        _operator(ctx)
        rig.press_estop(bool(ctx.body.get("pressed", True)))
        return 200, rig.describe()

    def fault(ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        _operator(ctx)
        kind = str(ctx.body.get("kind", ""))
        if not kind:
            raise HttpError(400, "kind is required")
        params = ctx.body.get("params", {})
        if not isinstance(params, dict):
            raise HttpError(400, "params must be an object")
        try:
            rig.inject(kind, ctx.body.get("channel"), **params)
        except (KeyError, ValueError) as exc:
            raise HttpError(400, str(exc)) from exc
        return 200, {**rig.describe(), "faults": rig.faults()}

    def clear(ctx: RequestContext) -> tuple[int, dict[str, Any]]:
        _operator(ctx)
        try:
            rig.clear(ctx.body.get("kind"), ctx.body.get("channel"))
        except KeyError as exc:
            raise HttpError(400, str(exc)) from exc
        return 200, {**rig.describe(), "faults": rig.faults()}

    node.extensions["simulator"] = rig
    add = node.add_route
    add("GET", "/v1/sim/state", state)
    add("POST", "/v1/sim/set_target", set_target)
    add("POST", "/v1/sim/ramp", ramp)
    add("POST", "/v1/sim/estop", estop)
    add("POST", "/v1/sim/fault", fault)
    add("POST", "/v1/sim/clear", clear)

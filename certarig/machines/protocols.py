"""Documented wire formats only. These builders do not connect to any machine."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

from .gateway import Refused, safe_job_path


def moonraker_request(action: str, job: str | None = None) -> tuple[str, str]:
    if action == "start":
        return "POST", "/printer/print/start?" + urlencode({"filename": safe_job_path(job or "")})
    if action in {"pause", "resume", "cancel"}:
        return "POST", "/printer/print/" + action
    if action == "emergency_stop":
        return "POST", "/printer/emergency_stop"
    raise Refused("action_not_available")


def grbl_realtime(action: str) -> bytes:
    """Feed hold is not an E-stop and does not prove spindle shutdown."""
    commands = {"status": b"?", "feed_hold": b"!", "resume": b"~"}
    if action not in commands:
        raise Refused("action_not_available")
    return commands[action]


def sdcp_request(
    action: str, *, brand_id: str, board_id: str, request_id: str, timestamp: int, filename: str | None = None
) -> dict[str, Any]:
    """SDCP 3.0 frame. Requires a commissioned identity and device-specific file format."""
    commands = {"start": 128, "pause": 129, "cancel": 130, "resume": 131}
    if action not in commands:
        raise Refused("action_not_available")
    if not all(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value) for value in (brand_id, board_id, request_id)):
        raise Refused("invalid_sdcp_identity")
    if type(timestamp) is not int or timestamp <= 0:
        raise Refused("invalid_sdcp_timestamp")
    data: dict[str, Any] = {}
    if action == "start":
        if (
            not filename
            or "/" in filename
            or "\\" in filename
            or not re.fullmatch(r"[A-Za-z0-9_.-]+\.(ctb|goo)", filename, re.IGNORECASE)
        ):
            raise Refused("invalid_resin_job_filename")
        data = {"Filename": filename, "StartLayer": 0}
    return {
        "Id": brand_id,
        "Data": {
            "Cmd": commands[action],
            "Data": data,
            "RequestID": request_id,
            "MainboardID": board_id,
            "TimeStamp": timestamp,
            "From": 0,
        },
        "Topic": "sdcp/request/" + board_id,
    }

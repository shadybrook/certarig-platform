"""Commissioning facts: what the agent must learn before proposing a rig map.

This is not a scripted quiz. The kernel only cares that required slots are filled.
An LLM (or the Fake policy) may ask in any order, in its own words. One operator
message can fill every slot. Apply stays human-only. Never arms output.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any, TypedDict

from .atomic import write_json_atomic
from .live import utc_now
from .models import CONCEPT_BY_UNIT

NAME = "interview.json"
IMAGE_DIR = "interview-images"
AUTO_ARM_NAME = "auto_arm.json"
_FIELD_MAX = 2000
_IMAGE_MAX_BYTES = 1_200_000
_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
}

class Slot(TypedDict):
    id: str
    required: bool
    need: str


# Facts the agent must figure out. Diagram is optional. Wording is for the
# model, not a question script — ask however you want, like plan mode.
SLOTS: tuple[Slot, ...] = (
    {
        "id": "modules",
        "required": True,
        "need": "Which modules are on the bench (ADC/pots, E-stop, relay, MQTT, Modbus, other).",
    },
    {
        "id": "signals",
        "required": True,
        "need": "Each analogue signal: customer name, concept (pressure/flow/temperature), unit, trip.",
    },
    {
        "id": "observe_only",
        "required": True,
        "need": "What must stay observe-only (none, MQTT, Modbus, everything).",
    },
    {
        "id": "diagram",
        "required": False,
        "need": "Optional diagram notes or a path under this node's evidence dir. No pin OCR. Never Phase 3 trees.",
    },
)

_CONCEPT_UNITS = {
    "pressure": "bar",
    "flow": "L/min",
    "temperature": "degC",
}

_SIGNAL_RE = re.compile(
    r"(?:(?P<name>[a-z][a-z0-9_]{0,40})\s+)?"
    r"(?P<concept>pressure|flow|temperature)\s+"
    r"(?:trip\s+)?"
    r"(?P<trip>[-+]?\d+(?:\.\d+)?)\s*"
    r"(?P<unit>bar|l/min|lpm|degc|°c|c)?",
    re.IGNORECASE,
)


def interview_path(evidence_dir: Any) -> Any:
    from pathlib import Path

    return Path(evidence_dir) / NAME


def empty_interview() -> dict[str, Any]:
    return {
        "status": "idle",
        "answers": {slot["id"]: "" for slot in SLOTS},
        "signals": [],
        "missing": [slot["id"] for slot in SLOTS if slot["required"]],
        "needs": [{"id": slot["id"], "required": slot["required"], "need": slot["need"]} for slot in SLOTS],
        "notes": [],
        "images": [],
        "proposed": None,
        "auto_arm": None,
        "prompt": _ask_prompt([slot["id"] for slot in SLOTS if slot["required"]]),
    }


def _clip(value: Any) -> str:
    return str(value or "").strip()[:_FIELD_MAX]


def _ask_prompt(missing: list[str]) -> str:
    if not missing:
        return "Required facts are in. Propose the map; a human must apply it. The interview never arms the relay."
    by_id = {slot["id"]: slot["need"] for slot in SLOTS}
    lines = "; ".join(by_id[item] for item in missing if item in by_id)
    return f"Still need: {lines} Ask in your own words. One reply can fill every slot."


def _slot_filled(slot_id: str, answers: dict[str, Any], signals: list[Any]) -> bool:
    if slot_id == "signals":
        return any(isinstance(row, dict) and row.get("concept") and row.get("trip") is not None for row in signals)
    return bool(str(answers.get(slot_id) or "").strip())


def _missing(answers: dict[str, Any], signals: list[Any]) -> list[str]:
    return [
        slot["id"]
        for slot in SLOTS
        if slot["required"] and not _slot_filled(slot["id"], answers, signals)
    ]


def _with_derived(document: dict[str, Any]) -> dict[str, Any]:
    answers: dict[str, Any] = document["answers"] if isinstance(document.get("answers"), dict) else {}
    signals: list[Any] = document["signals"] if isinstance(document.get("signals"), list) else []
    missing = _missing(answers, signals)
    document["missing"] = missing
    document["needs"] = [{"id": slot["id"], "required": slot["required"], "need": slot["need"]} for slot in SLOTS]
    document["status"] = "complete" if not missing and document.get("status") != "idle" else (
        "in_progress" if document.get("status") != "idle" else "idle"
    )
    if document["status"] == "complete":
        document["prompt"] = _ask_prompt([])
    elif document["status"] == "in_progress":
        document["prompt"] = _ask_prompt(missing)
    return document


def read_interview(evidence_dir: Any) -> dict[str, Any]:
    path = interview_path(evidence_dir)
    if not path.is_file():
        return {"present": False, **empty_interview()}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    document = empty_interview()
    if isinstance(loaded, dict):
        document["status"] = str(loaded.get("status") or "idle")
        raw_answers = loaded.get("answers")
        answers: dict[str, Any] = raw_answers if isinstance(raw_answers, dict) else {}
        for slot in SLOTS:
            document["answers"][slot["id"]] = _clip(answers.get(slot["id"]))
        signals = loaded.get("signals")
        document["signals"] = signals if isinstance(signals, list) else []
        notes = loaded.get("notes")
        document["notes"] = notes if isinstance(notes, list) else []
        document["proposed"] = loaded.get("proposed")
        images = loaded.get("images")
        document["images"] = images if isinstance(images, list) else []
        document["auto_arm"] = loaded.get("auto_arm")
        document["updated_at"] = str(loaded.get("updated_at") or "")
    return {"present": True, **_with_derived(document)}


def _write(evidence_dir: Any, document: dict[str, Any]) -> dict[str, Any]:
    document = _with_derived(dict(document))
    document["updated_at"] = utc_now()
    write_json_atomic(interview_path(evidence_dir), document)
    return {"present": True, **document}


def start_interview(evidence_dir: Any) -> dict[str, Any]:
    document = empty_interview()
    document["status"] = "in_progress"
    return _write(evidence_dir, document)


def _normalize_signal(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    concept = str(raw.get("concept") or "").strip().lower()
    if concept not in _CONCEPT_UNITS:
        return None
    unit = str(raw.get("unit") or _CONCEPT_UNITS[concept]).strip() or _CONCEPT_UNITS[concept]
    trip = raw.get("trip")
    try:
        trip_value = float(trip) if trip is not None and str(trip) != "" else None
    except (TypeError, ValueError):
        trip_value = None
    name = str(raw.get("customer_name") or raw.get("channel_id") or "").strip()
    return {
        "customer_name": name,
        "concept": concept,
        "unit": unit,
        "trip": trip_value,
    }


def parse_signals(text: str, existing: list[Any] | None = None) -> list[dict[str, Any]]:
    clipped = _clip(text)
    if not clipped:
        return [row for row in (existing or []) if isinstance(row, dict)]
    try:
        loaded = json.loads(clipped)
    except json.JSONDecodeError:
        loaded = None
    if isinstance(loaded, list):
        return [row for row in (_normalize_signal(item) for item in loaded) if row]
    if isinstance(loaded, dict) and isinstance(loaded.get("signals"), list):
        return [row for row in (_normalize_signal(item) for item in loaded["signals"]) if row]
    rows: list[dict[str, Any]] = []
    for match in _SIGNAL_RE.finditer(clipped):
        rows.append(
            {
                "customer_name": (match.group("name") or "").strip(),
                "concept": match.group("concept").lower(),
                "unit": (match.group("unit") or _CONCEPT_UNITS[match.group("concept").lower()]),
                "trip": float(match.group("trip")),
            }
        )
    return rows or [row for row in (existing or []) if isinstance(row, dict)]


def extract_facts(text: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Pull any slots the operator (or the model) just revealed. Partial is fine."""
    facts: dict[str, Any] = {}
    payload = body or {}
    for slot in SLOTS:
        if payload.get(slot["id"]) not in (None, ""):
            facts[slot["id"]] = payload[slot["id"]]
    if isinstance(payload.get("signals"), list):
        facts["signals"] = [row for row in (_normalize_signal(item) for item in payload["signals"]) if row]
    clipped = _clip(text)
    if not clipped:
        return facts
    lower = clipped.lower()
    modules: list[str] = []
    if any(word in lower for word in ("adc", "pot", "potentiometer")):
        modules.append("ADC/pots")
    if "e-stop" in lower or "estop" in lower or "mushroom" in lower:
        modules.append("E-stop")
    if "relay" in lower or "permit" in lower:
        modules.append("relay")
    if "mqtt" in lower and "no mqtt" not in lower and "without mqtt" not in lower:
        modules.append("MQTT")
    if "modbus" in lower and "no modbus" not in lower and "without modbus" not in lower:
        modules.append("Modbus")
    if modules and "modules" not in facts:
        facts["modules"] = ", ".join(modules)
    elif "modules" not in facts and not parse_signals(clipped) and "observe" not in lower:
        facts["modules"] = clipped
    signals = parse_signals(clipped)
    if signals and "signals" not in facts:
        facts["signals"] = signals
        facts.setdefault("signals_text", clipped)
    if "observe_only" not in facts:
        if re.search(r"\bnone\b", lower) or "nothing observe" in lower or "not observe" in lower:
            facts["observe_only"] = "none"
        elif any(word in lower for word in ("everything observe", "observe-only", "observe only", "mqtt", "modbus")):
            if "mqtt" in lower or "modbus" in lower or "everything" in lower:
                facts["observe_only"] = clipped[:400]
    if "diagram" not in facts:
        path_match = re.search(r"[\w./-]+\.(md|svg|png|jpg|txt)", clipped, re.IGNORECASE)
        if path_match:
            facts["diagram"] = path_match.group(0)
        elif "diagram" in lower or "as-built" in lower:
            facts["diagram"] = clipped
    return facts


def answer_interview(evidence_dir: Any, body: dict[str, Any]) -> dict[str, Any]:
    """Record whatever this utterance taught us. Does not advance a scripted question."""
    current = read_interview(evidence_dir)
    if current.get("status") in {None, "idle"}:
        current = start_interview(evidence_dir)
    text = str(body.get("text") or "")
    facts = extract_facts(text, body)
    answers = dict(current.get("answers") or {})
    if facts.get("modules"):
        answers["modules"] = _clip(facts["modules"])
    if facts.get("observe_only"):
        answers["observe_only"] = _clip(facts["observe_only"])
    if facts.get("diagram"):
        answers["diagram"] = _clip(facts["diagram"])
    signals = current.get("signals") if isinstance(current.get("signals"), list) else []
    if facts.get("signals"):
        signals = list(facts["signals"])
        answers["signals"] = _clip(facts.get("signals_text") or json.dumps(signals))
    notes = list(current.get("notes") or [])
    if text.strip():
        notes.append(_clip(text))
    current["answers"] = answers
    current["signals"] = signals
    current["notes"] = notes[-20:]
    current["status"] = "in_progress"
    current.pop("present", None)
    return _write(evidence_dir, current)


def _derived_concept(channel: dict[str, Any]) -> str:
    explicit = str(channel.get("concept") or "").strip().lower()
    if explicit:
        return explicit
    unit = str(channel.get("unit") or "").strip().lower()
    return CONCEPT_BY_UNIT.get(unit, "signal")


def _clamp_warnings(channel: dict[str, Any], trip: float) -> None:
    for field in ("warning_max", "warning_min"):
        raw = channel.get(field)
        if raw is None or raw == "":
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if field == "warning_max" and value > trip:
            channel[field] = trip
        if field == "warning_min" and value > trip:
            channel[field] = trip


def proposed_document(current_raw: dict[str, Any], interview: dict[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(current_raw)
    signals: list[Any] = interview["signals"] if isinstance(interview.get("signals"), list) else []
    answers: dict[str, Any] = interview["answers"] if isinstance(interview.get("answers"), dict) else {}
    if not signals:
        signals = parse_signals(str(answers.get("signals") or ""))
    channels = list(document.get("channels") or [])
    abort = dict(document.get("abort_limits") or {})
    for signal in signals:
        row = _normalize_signal(signal)
        if row is None:
            continue
        concept = str(row["concept"])
        name = str(row["customer_name"] or "")
        unit = str(row["unit"])
        trip = row["trip"]
        match = next((channel for channel in channels if name and channel.get("channel_id") == name), None)
        if match is None:
            match = next((channel for channel in channels if _derived_concept(channel) == concept), None)
        if match is None:
            channel_id = name or f"{concept}_signal"
            added: dict[str, Any] = {
                "channel_id": channel_id,
                "kind": "analog",
                "concept": concept,
                "unit": unit,
                "valid_min": 0.0,
                "valid_max": float(trip) * 1.5 if trip is not None else 100.0,
                "safe_min": 0.0,
                "safe_max": float(trip) if trip is not None else 50.0,
                "required": True,
                "calibration_id": f"UNCAL-{channel_id}",
            }
            channels.append(added)
        else:
            if name:
                match["channel_id"] = name
            match["concept"] = concept
            if unit:
                match["unit"] = unit
            if trip is not None:
                match["safe_max"] = float(trip)
                _clamp_warnings(match, float(trip))
        if trip is not None:
            abort[concept] = float(trip)
    document["channels"] = channels
    if abort:
        document["abort_limits"] = abort
        document.pop("pressure_abort_bar", None)
    observe = str(answers.get("observe_only") or "").lower()
    hardware = dict(document.get("hardware") or {})
    if any(word in observe for word in ("everything", "all", "mqtt", "modbus")) and "none" not in observe:
        hardware["observe_only"] = True
        document["hardware"] = hardware
    return document


def attach_interview_image(
    evidence_dir: Any,
    *,
    filename: str,
    content_base64: str,
    media_type: str = "",
) -> dict[str, Any]:
    """Store a bench photo under this node's evidence dir. Fills the optional diagram slot.

    A photo never applies a map and never arms output.
    """
    import base64
    import hashlib
    from pathlib import Path

    name = Path(str(filename or "bench.png")).name
    if not name or name.startswith(".") or "phase3" in name.lower():
        raise ValueError("image name is not allowed")
    lowered = (media_type or "").split(";")[0].strip().lower()
    suffix = _IMAGE_TYPES.get(lowered)
    if suffix is None:
        suffix = Path(name).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("only png, jpeg, or webp bench photos are accepted")
        if suffix == ".jpeg":
            suffix = ".jpg"
    raw = str(content_base64 or "").strip()
    if "," in raw and raw.lower().startswith("data:"):
        raw = raw.split(",", 1)[1]
    try:
        payload = base64.b64decode(raw, validate=False)
    except (ValueError, TypeError) as exc:
        raise ValueError("image is not valid base64") from exc
    if not payload or len(payload) > _IMAGE_MAX_BYTES:
        raise ValueError(f"image must be between 1 and {_IMAGE_MAX_BYTES} bytes")
    digest = hashlib.sha256(payload).hexdigest()
    relative = f"{IMAGE_DIR}/{digest[:16]}{suffix}"
    target = Path(evidence_dir) / relative
    if "phase3" in str(target.resolve()).lower():
        raise ValueError("refusing to write onto a Phase 3 tree")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    current = read_interview(evidence_dir)
    if current.get("status") in {None, "idle"}:
        current = start_interview(evidence_dir)
    images = list(current.get("images") or [])
    images.append({"path": relative, "sha256": digest, "filename": name, "bytes": len(payload)})
    answers = dict(current.get("answers") or {})
    answers["diagram"] = relative
    current["answers"] = answers
    current["images"] = images[-8:]
    current["status"] = "in_progress"
    current.pop("present", None)
    return _write(evidence_dir, current)


def acknowledge_auto_arm(
    evidence_dir: Any,
    *,
    acknowledgement: str,
    operator: str,
    allow_output: bool,
    hardware_mode: str,
) -> dict[str, Any]:
    """Log an explicit auto-arm acknowledgement. Never calls set_valve.

    Still requires a completed interview with a proposal, the env arm switch,
    and (on raspberry_pi) a fresh twin-gate stamp somewhere in the evidence dir.
    """
    from pathlib import Path

    from .atomic import write_json_atomic
    from .twin_gate import check_gate

    text = _clip(acknowledgement)
    if len(text) < 8:
        raise ValueError("acknowledgement must say, in words, that a human applied the map")
    interview = read_interview(evidence_dir)
    if interview.get("status") != "complete" or not interview.get("proposed"):
        raise RuntimeError("auto-arm needs a completed interview and a proposed map a human can apply")
    twin = None
    if hardware_mode == "raspberry_pi":
        stamps = list((Path(evidence_dir) / "twin_gate").glob("*.json")) if Path(evidence_dir).is_dir() else []
        if not stamps:
            twin = {
                "error": "digital-twin gate: no simulator pass is on this node",
                "code": "twin_gate",
            }
        else:
            first = json.loads(stamps[0].read_text(encoding="utf-8"))
            twin = check_gate(Path(evidence_dir), str(first.get("procedure_hash") or ""), hardware_mode)
    stamp = {
        "acknowledged": True,
        "acknowledgement": text,
        "operator": _clip(operator) or "operator",
        "allow_output": bool(allow_output),
        "hardware_mode": hardware_mode,
        "twin_gate_ok": twin is None,
        "twin_gate": twin,
        "may_request_permit": bool(allow_output) and twin is None,
        "set_valve": False,
        "note": "A photo never calls set_valve. Kernel still owns drive_high.",
    }
    write_json_atomic(Path(evidence_dir) / AUTO_ARM_NAME, stamp)
    current = dict(interview)
    current.pop("present", None)
    current["auto_arm"] = stamp
    saved = _write(evidence_dir, current)
    return {**saved, "auto_arm": stamp}


def attach_proposal(evidence_dir: Any, preview: dict[str, Any]) -> dict[str, Any]:
    current = read_interview(evidence_dir)
    current.pop("present", None)
    current["proposed"] = {
        "diff": preview.get("diff"),
        "current_hash": preview.get("current_hash"),
        "next_hash": preview.get("next_hash"),
        "restart_required": preview.get("restart_required"),
    }
    return _write(evidence_dir, current)

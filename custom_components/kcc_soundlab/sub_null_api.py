"""Persistent Sub Null Method sweep storage for KCC SoundLab."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .model import KCCDSPState

MAX_SWEEPS_PER_SESSION = 20
MAX_POINTS_PER_SWEEP = 31
SWEEP_STATUSES = ("active", "completed", "restored")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_for_message(
    hass: HomeAssistant,
    connection: Any,
    msg: dict[str, Any],
) -> KCCDSPState | None:
    state = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if isinstance(state, KCCDSPState):
        return state
    connection.send_error(
        msg["id"],
        "not_found",
        "KCC SoundLab config entry is not loaded",
    )
    return None


def _number(value: Any, minimum: float, maximum: float, name: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as err:
        raise ValueError(f"{name} must be numeric") from err
    if not minimum <= numeric <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return numeric


def _normalise_sweeps(session: dict[str, Any]) -> list[dict[str, Any]]:
    raw = session.get("sub_null_sweeps")
    if not isinstance(raw, list):
        raw = []

    sweeps: list[dict[str, Any]] = []
    for saved in raw[-MAX_SWEEPS_PER_SESSION:]:
        if not isinstance(saved, dict) or not saved.get("id"):
            continue
        sweep = dict(saved)
        sweep["id"] = str(sweep["id"])
        sweep["created_at"] = str(sweep.get("created_at", ""))
        sweep["channel_index"] = int(sweep.get("channel_index", 0))
        refs = sweep.get("reference_indices")
        sweep["reference_indices"] = [
            int(value) for value in refs[:2]
        ] if isinstance(refs, list) else []
        sweep["start_fine_delay_ms"] = round(
            float(sweep.get("start_fine_delay_ms", 0.0)), 2
        )
        sweep["start_phase_deg"] = round(float(sweep.get("start_phase_deg", 0.0)), 1)
        start_polarity = str(sweep.get("start_polarity", "Normal"))
        sweep["start_polarity"] = start_polarity if start_polarity in ("Normal", "Inverted") else "Normal"
        status = str(sweep.get("status", "active"))
        sweep["status"] = status if status in SWEEP_STATUSES else "active"

        points = sweep.get("points")
        normalised_points: list[dict[str, Any]] = []
        if isinstance(points, list):
            for point in points[-MAX_POINTS_PER_SWEEP:]:
                if not isinstance(point, dict):
                    continue
                try:
                    fine = _number(point.get("fine_delay_ms"), -5.0, 5.0, "fine_delay_ms")
                    level = _number(point.get("level_db"), -150.0, 150.0, "level_db")
                except ValueError:
                    continue
                normalised_points.append({
                    "fine_delay_ms": round(fine, 2),
                    "level_db": round(level, 1),
                    "measured_at": str(point.get("measured_at", "")),
                })
        normalised_points.sort(key=lambda item: item["fine_delay_ms"])
        sweep["points"] = normalised_points

        if normalised_points:
            best = min(normalised_points, key=lambda item: item["level_db"])
            sweep["auto_best_fine_delay_ms"] = best["fine_delay_ms"]
            sweep["auto_best_level_db"] = best["level_db"]
        else:
            sweep["auto_best_fine_delay_ms"] = None
            sweep["auto_best_level_db"] = None

        for key in ("best_fine_delay_ms", "best_level_db", "final_fine_delay_ms", "final_phase_deg"):
            value = sweep.get(key)
            if value is None:
                sweep[key] = None
            else:
                try:
                    sweep[key] = float(value)
                except (TypeError, ValueError):
                    sweep[key] = None
        final_polarity = sweep.get("final_polarity")
        sweep["final_polarity"] = (
            str(final_polarity)
            if final_polarity in ("Normal", "Inverted")
            else None
        )
        sweep["completed_at"] = str(sweep.get("completed_at", ""))
        sweeps.append(sweep)

    session["sub_null_sweeps"] = sweeps
    return sweeps


def _sweep_for(session: dict[str, Any], sweep_id: str) -> dict[str, Any]:
    sweeps = _normalise_sweeps(session)
    sweep = next((item for item in sweeps if item.get("id") == sweep_id), None)
    if sweep is None:
        raise ValueError("Sub null sweep was not found")
    return sweep


def _public_sweep(sweep: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(sweep.get("id", "")),
        "created_at": str(sweep.get("created_at", "")),
        "channel_index": int(sweep.get("channel_index", 0)),
        "reference_indices": list(sweep.get("reference_indices", [])),
        "start_fine_delay_ms": float(sweep.get("start_fine_delay_ms", 0.0)),
        "start_phase_deg": float(sweep.get("start_phase_deg", 0.0)),
        "start_polarity": str(sweep.get("start_polarity", "Normal")),
        "status": str(sweep.get("status", "active")),
        "points": [dict(item) for item in sweep.get("points", [])],
        "auto_best_fine_delay_ms": sweep.get("auto_best_fine_delay_ms"),
        "auto_best_level_db": sweep.get("auto_best_level_db"),
        "best_fine_delay_ms": sweep.get("best_fine_delay_ms"),
        "best_level_db": sweep.get("best_level_db"),
        "final_fine_delay_ms": sweep.get("final_fine_delay_ms"),
        "final_phase_deg": sweep.get("final_phase_deg"),
        "final_polarity": sweep.get("final_polarity"),
        "completed_at": str(sweep.get("completed_at", "")),
    }


@callback
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/get_sub_null_sweeps",
    vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
})
def websocket_get_sub_null_sweeps(
    hass: HomeAssistant,
    connection: Any,
    msg: dict[str, Any],
) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        session = state.measurement_session(msg["session_id"])
        sweeps = _normalise_sweeps(session)
    except ValueError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return
    connection.send_result(
        msg["id"],
        {"sweeps": [_public_sweep(item) for item in reversed(sweeps)]},
    )


@callback
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/create_sub_null_sweep",
    vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
    vol.Required("channel"): vol.Coerce(int),
    vol.Optional("reference_indices", default=[]): [vol.Coerce(int)],
    vol.Required("start_fine_delay_ms"): vol.Coerce(float),
    vol.Required("start_phase_deg"): vol.Coerce(float),
    vol.Required("start_polarity"): vol.In(("Normal", "Inverted")),
})
def websocket_create_sub_null_sweep(
    hass: HomeAssistant,
    connection: Any,
    msg: dict[str, Any],
) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        channel = int(msg["channel"])
        if not 0 <= channel < state.channel_count:
            raise ValueError("Channel index is out of range")
        refs = [
            int(value)
            for value in msg.get("reference_indices", [])[:2]
            if 0 <= int(value) < state.channel_count and int(value) != channel
        ]
        fine = _number(msg["start_fine_delay_ms"], -5.0, 5.0, "start_fine_delay_ms")
        phase = _number(msg["start_phase_deg"], 0.0, 360.0, "start_phase_deg")
        session = state.measurement_session(msg["session_id"])
        sweeps = _normalise_sweeps(session)
        sweep = {
            "id": uuid4().hex[:12],
            "created_at": _utc_now(),
            "channel_index": channel,
            "reference_indices": refs,
            "start_fine_delay_ms": round(fine, 2),
            "start_phase_deg": round(phase, 1),
            "start_polarity": msg["start_polarity"],
            "status": "active",
            "points": [],
            "auto_best_fine_delay_ms": None,
            "auto_best_level_db": None,
            "best_fine_delay_ms": None,
            "best_level_db": None,
            "final_fine_delay_ms": None,
            "final_phase_deg": None,
            "final_polarity": None,
            "completed_at": "",
        }
        sweeps.append(sweep)
        session["sub_null_sweeps"] = sweeps[-MAX_SWEEPS_PER_SESSION:]
        state.notify()
    except (TypeError, ValueError) as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    connection.send_result(msg["id"], {"sweep": _public_sweep(sweep)})


@callback
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/record_sub_null_point",
    vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
    vol.Required("sweep_id"): str,
    vol.Required("fine_delay_ms"): vol.Coerce(float),
    vol.Required("level_db"): vol.Coerce(float),
})
def websocket_record_sub_null_point(
    hass: HomeAssistant,
    connection: Any,
    msg: dict[str, Any],
) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        session = state.measurement_session(msg["session_id"])
        sweep = _sweep_for(session, msg["sweep_id"])
        if sweep.get("status") != "active":
            raise ValueError("Only an active sub null sweep can record points")
        fine = round(_number(msg["fine_delay_ms"], -5.0, 5.0, "fine_delay_ms"), 2)
        level = round(_number(msg["level_db"], -150.0, 150.0, "level_db"), 1)
        points = [
            item for item in sweep.get("points", [])
            if float(item.get("fine_delay_ms", 999.0)) != fine
        ]
        points.append({
            "fine_delay_ms": fine,
            "level_db": level,
            "measured_at": _utc_now(),
        })
        points = sorted(points, key=lambda item: item["fine_delay_ms"])[-MAX_POINTS_PER_SWEEP:]
        sweep["points"] = points
        best = min(points, key=lambda item: item["level_db"])
        sweep["auto_best_fine_delay_ms"] = best["fine_delay_ms"]
        sweep["auto_best_level_db"] = best["level_db"]
        state.notify()
    except (TypeError, ValueError) as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    connection.send_result(msg["id"], {"sweep": _public_sweep(sweep)})


@callback
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/finish_sub_null_sweep",
    vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
    vol.Required("sweep_id"): str,
    vol.Required("status"): vol.In(("completed", "restored")),
    vol.Optional("best_fine_delay_ms"): vol.Any(None, vol.Coerce(float)),
    vol.Optional("best_level_db"): vol.Any(None, vol.Coerce(float)),
    vol.Required("final_fine_delay_ms"): vol.Coerce(float),
    vol.Required("final_phase_deg"): vol.Coerce(float),
    vol.Required("final_polarity"): vol.In(("Normal", "Inverted")),
})
def websocket_finish_sub_null_sweep(
    hass: HomeAssistant,
    connection: Any,
    msg: dict[str, Any],
) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        session = state.measurement_session(msg["session_id"])
        sweep = _sweep_for(session, msg["sweep_id"])
        final_fine = _number(msg["final_fine_delay_ms"], -5.0, 5.0, "final_fine_delay_ms")
        final_phase = _number(msg["final_phase_deg"], 0.0, 360.0, "final_phase_deg")
        best_fine = msg.get("best_fine_delay_ms")
        best_level = msg.get("best_level_db")
        sweep["status"] = msg["status"]
        sweep["best_fine_delay_ms"] = (
            round(_number(best_fine, -5.0, 5.0, "best_fine_delay_ms"), 2)
            if best_fine is not None else None
        )
        sweep["best_level_db"] = (
            round(_number(best_level, -150.0, 150.0, "best_level_db"), 1)
            if best_level is not None else None
        )
        sweep["final_fine_delay_ms"] = round(final_fine, 2)
        sweep["final_phase_deg"] = round(final_phase, 1)
        sweep["final_polarity"] = msg["final_polarity"]
        sweep["completed_at"] = _utc_now()
        state.notify()
    except (TypeError, ValueError) as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    connection.send_result(msg["id"], {"sweep": _public_sweep(sweep)})


@callback
def async_setup_sub_null_api(hass: HomeAssistant) -> None:
    """Register persistent Sub Null Method websocket commands."""
    websocket_api.async_register_command(hass, websocket_get_sub_null_sweeps)
    websocket_api.async_register_command(hass, websocket_create_sub_null_sweep)
    websocket_api.async_register_command(hass, websocket_record_sub_null_point)
    websocket_api.async_register_command(hass, websocket_finish_sub_null_sweep)

"""Persistent per-channel frequency response storage for KCC SoundLab."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from math import isfinite
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .model import KCCDSPState

MIN_RESPONSE_POINTS = 5
MAX_RESPONSE_POINTS = 256
MIN_FREQUENCY_HZ = 20.0
MAX_FREQUENCY_HZ = 20000.0
MIN_SPL_DB = -200.0
MAX_SPL_DB = 200.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_for_message(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> KCCDSPState | None:
    state = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if isinstance(state, KCCDSPState):
        return state
    connection.send_error(
        msg["id"], "not_found", "KCC SoundLab config entry is not loaded"
    )
    return None


def _validate_channel(state: KCCDSPState, channel_index: int) -> dict[str, Any]:
    if not 0 <= channel_index < state.channel_count:
        raise ValueError("Channel index is out of range")
    return state.channel(channel_index)


def _normalise_points(points: Any) -> list[dict[str, float]]:
    if not isinstance(points, list):
        raise ValueError("Frequency response points must be a list")
    if not MIN_RESPONSE_POINTS <= len(points) <= MAX_RESPONSE_POINTS:
        raise ValueError(
            f"Frequency response must contain between {MIN_RESPONSE_POINTS} and "
            f"{MAX_RESPONSE_POINTS} points"
        )

    normalised: list[dict[str, float]] = []
    for point in points:
        if not isinstance(point, dict):
            raise ValueError("Each response point must contain frequency_hz and spl_db")
        try:
            frequency = float(point.get("frequency_hz"))
            spl_db = float(point.get("spl_db"))
        except (TypeError, ValueError) as err:
            raise ValueError("Response frequency and SPL must be numeric") from err
        if not isfinite(frequency) or not isfinite(spl_db):
            raise ValueError("Response frequency and SPL must be finite")
        if not MIN_FREQUENCY_HZ <= frequency <= MAX_FREQUENCY_HZ:
            raise ValueError("Response frequency must be between 20 and 20000 Hz")
        if not MIN_SPL_DB <= spl_db <= MAX_SPL_DB:
            raise ValueError("Response SPL must be between -200 and +200 dB")
        normalised.append(
            {
                "frequency_hz": round(frequency, 3),
                "spl_db": round(spl_db, 3),
            }
        )

    normalised.sort(key=lambda item: item["frequency_hz"])
    unique: list[dict[str, float]] = []
    for item in normalised:
        if unique and abs(item["frequency_hz"] - unique[-1]["frequency_hz"]) < 0.001:
            unique[-1] = item
        else:
            unique.append(item)
    if len(unique) < MIN_RESPONSE_POINTS:
        raise ValueError(
            f"Frequency response must contain at least {MIN_RESPONSE_POINTS} unique points"
        )
    return unique


def _responses(session: dict[str, Any]) -> dict[str, Any]:
    responses = session.get("frequency_responses")
    if not isinstance(responses, dict):
        responses = {}
        session["frequency_responses"] = responses
    return responses


def _public_response(
    state: KCCDSPState,
    channel_index: int,
    response: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(response, dict):
        return None
    channel = state.channel(channel_index)
    points = response.get("points")
    if not isinstance(points, list):
        return None
    return {
        "channel_index": channel_index,
        "channel_id": str(channel.get("id", "")),
        "output": str(channel.get("output", "")),
        "speaker": str(channel.get("speaker", "")),
        "source_name": str(response.get("source_name", "REW measurement")),
        "imported_at": str(response.get("imported_at", "")),
        "original_point_count": int(response.get("original_point_count", len(points))),
        "point_count": len(points),
        "points": deepcopy(points),
    }


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/get_frequency_response",
        vol.Required("entry_id"): str,
        vol.Required("session_id"): str,
        vol.Required("channel"): vol.Coerce(int),
    }
)
def websocket_get_frequency_response(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        channel = _validate_channel(state, msg["channel"])
        session = state.measurement_session(msg["session_id"])
    except ValueError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return
    response = _responses(session).get(str(channel.get("id", "")))
    connection.send_result(
        msg["id"],
        {"response": _public_response(state, msg["channel"], response)},
    )


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/set_frequency_response",
        vol.Required("entry_id"): str,
        vol.Required("session_id"): str,
        vol.Required("channel"): vol.Coerce(int),
        vol.Required("source_name"): str,
        vol.Required("original_point_count"): vol.Coerce(int),
        vol.Required("points"): [
            {
                vol.Required("frequency_hz"): vol.Coerce(float),
                vol.Required("spl_db"): vol.Coerce(float),
            }
        ],
    }
)
def websocket_set_frequency_response(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        channel = _validate_channel(state, msg["channel"])
        session = state.measurement_session(msg["session_id"])
        points = _normalise_points(msg["points"])
    except (TypeError, ValueError) as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return

    source_name = str(msg.get("source_name", "REW measurement")).strip()[:120]
    original_count = max(len(points), min(1000000, int(msg["original_point_count"])))
    response = {
        "source_name": source_name or "REW measurement",
        "imported_at": _utc_now(),
        "original_point_count": original_count,
        "points": points,
    }
    _responses(session)[str(channel.get("id", ""))] = response
    state.notify()
    connection.send_result(
        msg["id"],
        {"response": _public_response(state, msg["channel"], response)},
    )


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/delete_frequency_response",
        vol.Required("entry_id"): str,
        vol.Required("session_id"): str,
        vol.Required("channel"): vol.Coerce(int),
    }
)
def websocket_delete_frequency_response(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        channel = _validate_channel(state, msg["channel"])
        session = state.measurement_session(msg["session_id"])
    except ValueError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return
    _responses(session).pop(str(channel.get("id", "")), None)
    state.notify()
    connection.send_result(msg["id"], {"response": None})


@callback
def async_setup_frequency_response_api(hass: HomeAssistant) -> None:
    """Register persistent frequency response WebSocket commands."""
    websocket_api.async_register_command(hass, websocket_get_frequency_response)
    websocket_api.async_register_command(hass, websocket_set_frequency_response)
    websocket_api.async_register_command(hass, websocket_delete_frequency_response)

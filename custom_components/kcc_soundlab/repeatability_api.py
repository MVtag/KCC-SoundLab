"""Persistent repeat frequency responses for KCC SoundLab."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .frequency_response_api import (
    _normalise_points,
    _state_for_message,
    _utc_now,
    _validate_channel,
)
from .model import KCCDSPState

MAX_REPEAT_RESPONSES = 4


def _repeatability(session: dict[str, Any]) -> dict[str, Any]:
    value = session.get("frequency_response_repeats")
    if not isinstance(value, dict):
        value = {}
        session["frequency_response_repeats"] = value
    return value


def _channel_samples(session: dict[str, Any], channel_id: str) -> list[dict[str, Any]]:
    store = _repeatability(session)
    samples = store.get(channel_id)
    if not isinstance(samples, list):
        samples = []
        store[channel_id] = samples
    clean = [item for item in samples if isinstance(item, dict) and isinstance(item.get("points"), list)]
    if clean is not samples:
        store[channel_id] = clean
    return clean


def _public_sample(
    state: KCCDSPState,
    channel_index: int,
    sample: dict[str, Any],
) -> dict[str, Any]:
    channel = state.channel(channel_index)
    points = sample.get("points") if isinstance(sample.get("points"), list) else []
    return {
        "id": str(sample.get("id", "")),
        "channel_index": channel_index,
        "channel_id": str(channel.get("id", "")),
        "output": str(channel.get("output", "")),
        "speaker": str(channel.get("speaker", "")),
        "source_name": str(sample.get("source_name", "REW repeat")),
        "imported_at": str(sample.get("imported_at", "")),
        "original_point_count": int(sample.get("original_point_count", len(points))),
        "point_count": len(points),
        "points": deepcopy(points),
    }


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/get_frequency_response_repeats",
        vol.Required("entry_id"): str,
        vol.Required("session_id"): str,
        vol.Required("channel"): vol.Coerce(int),
    }
)
def websocket_get_frequency_response_repeats(
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
    samples = _channel_samples(session, str(channel.get("id", "")))
    connection.send_result(
        msg["id"],
        {
            "max_repeats": MAX_REPEAT_RESPONSES,
            "repeats": [_public_sample(state, msg["channel"], item) for item in samples],
        },
    )


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/add_frequency_response_repeat",
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
def websocket_add_frequency_response_repeat(
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

    samples = _channel_samples(session, str(channel.get("id", "")))
    if len(samples) >= MAX_REPEAT_RESPONSES:
        connection.send_error(
            msg["id"],
            "limit_reached",
            f"A maximum of {MAX_REPEAT_RESPONSES} repeat responses is supported per output",
        )
        return

    source_name = str(msg.get("source_name", "REW repeat")).strip()[:120]
    original_count = max(len(points), min(1000000, int(msg["original_point_count"])))
    sample = {
        "id": uuid4().hex[:12],
        "source_name": source_name or "REW repeat",
        "imported_at": _utc_now(),
        "original_point_count": original_count,
        "points": points,
    }
    samples.append(sample)
    state.notify()
    connection.send_result(
        msg["id"],
        {
            "max_repeats": MAX_REPEAT_RESPONSES,
            "repeat": _public_sample(state, msg["channel"], sample),
            "repeats": [_public_sample(state, msg["channel"], item) for item in samples],
        },
    )


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/delete_frequency_response_repeat",
        vol.Required("entry_id"): str,
        vol.Required("session_id"): str,
        vol.Required("channel"): vol.Coerce(int),
        vol.Required("repeat_id"): str,
    }
)
def websocket_delete_frequency_response_repeat(
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

    samples = _channel_samples(session, str(channel.get("id", "")))
    repeat_id = str(msg.get("repeat_id", ""))
    before = len(samples)
    samples[:] = [item for item in samples if str(item.get("id", "")) != repeat_id]
    if len(samples) == before:
        connection.send_error(msg["id"], "not_found", "Repeat response was not found")
        return
    state.notify()
    connection.send_result(
        msg["id"],
        {
            "max_repeats": MAX_REPEAT_RESPONSES,
            "repeats": [_public_sample(state, msg["channel"], item) for item in samples],
        },
    )


@callback
def async_setup_repeatability_api(hass: HomeAssistant) -> None:
    """Register persistent repeatability WebSocket commands."""
    websocket_api.async_register_command(hass, websocket_get_frequency_response_repeats)
    websocket_api.async_register_command(hass, websocket_add_frequency_response_repeat)
    websocket_api.async_register_command(hass, websocket_delete_frequency_response_repeat)

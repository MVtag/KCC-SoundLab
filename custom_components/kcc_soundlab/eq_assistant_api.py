"""Controlled EQ Assistant apply and rollback API for KCC SoundLab."""

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

MAX_ASSISTANT_FILTERS = 5
MIN_FREQUENCY_HZ = 20.0
MAX_FREQUENCY_HZ = 20000.0
MIN_GAIN_DB = -6.0
MAX_GAIN_DB = 3.0
MIN_Q = 0.45
MAX_Q = 6.0


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
    # snapshot() also normalises legacy/missing EQ-band data without changing tuning.
    state.snapshot()
    return state.channel(channel_index)


def _normalise_filters(filters: Any) -> list[dict[str, float]]:
    if not isinstance(filters, list) or not 1 <= len(filters) <= MAX_ASSISTANT_FILTERS:
        raise ValueError(
            f"EQ Assistant apply requires between 1 and {MAX_ASSISTANT_FILTERS} filters"
        )

    normalised: list[dict[str, float]] = []
    for item in filters:
        if not isinstance(item, dict):
            raise ValueError("Each EQ Assistant filter must be an object")
        try:
            frequency = float(item.get("frequency_hz"))
            gain = float(item.get("gain_db"))
            q_value = float(item.get("q"))
        except (TypeError, ValueError) as err:
            raise ValueError("EQ Assistant frequency, gain and Q must be numeric") from err
        if not all(isfinite(value) for value in (frequency, gain, q_value)):
            raise ValueError("EQ Assistant filter values must be finite")
        if not MIN_FREQUENCY_HZ <= frequency <= MAX_FREQUENCY_HZ:
            raise ValueError("EQ Assistant frequency must be between 20 and 20000 Hz")
        if not MIN_GAIN_DB <= gain <= MAX_GAIN_DB:
            raise ValueError("EQ Assistant gain must be between -6 and +3 dB")
        if not MIN_Q <= q_value <= MAX_Q:
            raise ValueError("EQ Assistant Q must be between 0.45 and 6")
        normalised.append(
            {
                "frequency_hz": round(frequency, 1),
                "gain_db": round(gain, 1),
                "q": round(q_value, 2),
            }
        )
    return normalised


def _applies(session: dict[str, Any]) -> dict[str, Any]:
    applies = session.get("eq_assistant_applies")
    if not isinstance(applies, dict):
        applies = {}
        session["eq_assistant_applies"] = applies
    return applies


def _apply_key(channel: dict[str, Any]) -> str:
    return str(channel.get("id", ""))


def _public_apply(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    return {
        "status": str(item.get("status", "")),
        "snapshot_id": str(item.get("snapshot_id", "")),
        "snapshot_name": str(item.get("snapshot_name", "")),
        "session_id": str(item.get("session_id", "")),
        "channel_index": int(item.get("channel_index", 0)),
        "channel_id": str(item.get("channel_id", "")),
        "output": str(item.get("output", "")),
        "smoothing": str(item.get("smoothing", "")),
        "filter_count": int(item.get("filter_count", 0)),
        "band_indices": [int(value) for value in item.get("band_indices", [])],
        "filters": deepcopy(item.get("filters", [])),
        "applied_at": str(item.get("applied_at", "")),
        "restored_at": str(item.get("restored_at", "")),
    }


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/get_eq_assistant_apply",
        vol.Required("entry_id"): str,
        vol.Required("session_id"): str,
        vol.Required("channel"): vol.Coerce(int),
    }
)
def websocket_get_eq_assistant_apply(
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
    item = _applies(session).get(_apply_key(channel))
    connection.send_result(msg["id"], {"apply": _public_apply(item)})


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/apply_eq_assistant",
        vol.Required("entry_id"): str,
        vol.Required("session_id"): str,
        vol.Required("channel"): vol.Coerce(int),
        vol.Required("smoothing"): str,
        vol.Required("filters"): [
            {
                vol.Required("frequency_hz"): vol.Coerce(float),
                vol.Required("gain_db"): vol.Coerce(float),
                vol.Required("q"): vol.Coerce(float),
            }
        ],
    }
)
def websocket_apply_eq_assistant(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        channel_index = int(msg["channel"])
        channel = _validate_channel(state, channel_index)
        session = state.measurement_session(msg["session_id"])
        filters = _normalise_filters(msg["filters"])
    except (TypeError, ValueError) as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return

    key = _apply_key(channel)
    previous = _applies(session).get(key)
    if isinstance(previous, dict) and previous.get("status") == "active":
        connection.send_error(
            msg["id"],
            "already_applied",
            "Restore the previous EQ Assistant apply before applying another set of filters",
        )
        return

    bands = channel.get("eq_bands")
    if not isinstance(bands, list):
        connection.send_error(msg["id"], "invalid_format", "Channel EQ data is unavailable")
        return

    free_indices = [
        index
        for index, band in enumerate(bands)
        if isinstance(band, dict)
        and not bool(band.get("enabled"))
        and abs(float(band.get("gain_db", 0.0))) < 0.001
    ]
    if len(free_indices) < len(filters):
        connection.send_error(
            msg["id"],
            "no_free_eq_bands",
            f"Need {len(filters)} unused EQ slots but only {len(free_indices)} are available",
        )
        return

    used_indices = free_indices[: len(filters)]
    staged = deepcopy(bands)
    for band_index, filter_data in zip(used_indices, filters, strict=True):
        staged[band_index] = {
            "enabled": True,
            "frequency_hz": filter_data["frequency_hz"],
            "gain_db": filter_data["gain_db"],
            "q": filter_data["q"],
        }

    output = str(channel.get("output", f"OUT {channel_index + 1}"))
    snapshot_name = f"EQ Assistant pre-apply · {output}"
    snapshot_id = state.save_snapshot(snapshot_name)

    # All validation and staging is complete before this single EQ-state assignment.
    channel["eq_bands"] = staged
    item = {
        "status": "active",
        "snapshot_id": snapshot_id,
        "snapshot_name": snapshot_name,
        "session_id": str(msg["session_id"]),
        "channel_index": channel_index,
        "channel_id": key,
        "output": output,
        "smoothing": str(msg.get("smoothing", ""))[:24],
        "filter_count": len(filters),
        "band_indices": used_indices,
        "filters": filters,
        "applied_at": _utc_now(),
        "restored_at": "",
    }
    _applies(session)[key] = item
    state.notify()
    connection.send_result(
        msg["id"],
        {"workspace": state.snapshot(), "apply": _public_apply(item)},
    )


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/restore_eq_assistant_apply",
        vol.Required("entry_id"): str,
        vol.Required("session_id"): str,
        vol.Required("channel"): vol.Coerce(int),
    }
)
def websocket_restore_eq_assistant_apply(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        channel_index = int(msg["channel"])
        channel = _validate_channel(state, channel_index)
        session = state.measurement_session(msg["session_id"])
    except (TypeError, ValueError) as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return

    item = _applies(session).get(_apply_key(channel))
    if not isinstance(item, dict) or item.get("status") != "active":
        connection.send_error(
            msg["id"], "not_found", "No active EQ Assistant apply exists for this channel"
        )
        return

    snapshot_id = str(item.get("snapshot_id", ""))
    try:
        state.restore_snapshot(snapshot_id)
    except ValueError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return

    item["status"] = "restored"
    item["restored_at"] = _utc_now()
    state.notify()
    connection.send_result(
        msg["id"],
        {"workspace": state.snapshot(), "apply": _public_apply(item)},
    )


@callback
def async_setup_eq_assistant_api(hass: HomeAssistant) -> None:
    """Register controlled EQ Assistant WebSocket commands."""
    websocket_api.async_register_command(hass, websocket_get_eq_assistant_apply)
    websocket_api.async_register_command(hass, websocket_apply_eq_assistant)
    websocket_api.async_register_command(hass, websocket_restore_eq_assistant_apply)

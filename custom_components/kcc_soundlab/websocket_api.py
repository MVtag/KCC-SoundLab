"""WebSocket API for the KCC SoundLab frontend workspace."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .model import KCCDSPState


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


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/get_state",
        vol.Required("entry_id"): str,
    }
)
def websocket_get_state(
    hass: HomeAssistant,
    connection: Any,
    msg: dict[str, Any],
) -> None:
    """Return the full internal tuning workspace."""
    state = _state_for_message(hass, connection, msg)
    if state is not None:
        connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/set_channel",
        vol.Required("entry_id"): str,
        vol.Required("channel"): vol.Coerce(int),
        vol.Required("field"): str,
        vol.Required("value"): vol.Any(bool, str, int, float),
    }
)
def websocket_set_channel(
    hass: HomeAssistant,
    connection: Any,
    msg: dict[str, Any],
) -> None:
    """Update one internal channel setting and return the new snapshot."""
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.set_channel_value(msg["channel"], msg["field"], msg["value"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/set_preset",
        vol.Required("entry_id"): str,
        vol.Required("preset"): str,
    }
)
def websocket_set_preset(
    hass: HomeAssistant,
    connection: Any,
    msg: dict[str, Any],
) -> None:
    """Update the active SoundLab preset and return the new snapshot."""
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.set_preset(msg["preset"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/save_snapshot",
        vol.Required("entry_id"): str,
        vol.Required("name"): str,
    }
)
def websocket_save_snapshot(
    hass: HomeAssistant,
    connection: Any,
    msg: dict[str, Any],
) -> None:
    """Save the current workspace as a tuning snapshot."""
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    state.save_snapshot(msg["name"])
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/restore_snapshot",
        vol.Required("entry_id"): str,
        vol.Required("snapshot_id"): str,
    }
)
def websocket_restore_snapshot(
    hass: HomeAssistant,
    connection: Any,
    msg: dict[str, Any],
) -> None:
    """Restore one tuning snapshot."""
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.restore_snapshot(msg["snapshot_id"])
    except ValueError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/delete_snapshot",
        vol.Required("entry_id"): str,
        vol.Required("snapshot_id"): str,
    }
)
def websocket_delete_snapshot(
    hass: HomeAssistant,
    connection: Any,
    msg: dict[str, Any],
) -> None:
    """Delete one tuning snapshot."""
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.delete_snapshot(msg["snapshot_id"])
    except ValueError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
def async_setup_websocket_api(hass: HomeAssistant) -> None:
    """Register SoundLab frontend commands."""
    websocket_api.async_register_command(hass, websocket_get_state)
    websocket_api.async_register_command(hass, websocket_set_channel)
    websocket_api.async_register_command(hass, websocket_set_preset)
    websocket_api.async_register_command(hass, websocket_save_snapshot)
    websocket_api.async_register_command(hass, websocket_restore_snapshot)
    websocket_api.async_register_command(hass, websocket_delete_snapshot)

"""WebSocket API for the KCC SoundLab frontend workspace."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .model import KCCDSPState, MEASUREMENT_POSITIONS, TARGET_CURVE_OPTIONS


def _state_for_message(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> KCCDSPState | None:
    state = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if isinstance(state, KCCDSPState):
        return state
    connection.send_error(msg["id"], "not_found", "KCC SoundLab config entry is not loaded")
    return None


def _send_value_error(connection: Any, msg: dict[str, Any], err: ValueError) -> None:
    connection.send_error(msg["id"], "invalid_format", str(err))


@callback
@websocket_api.websocket_command({vol.Required("type"): "kcc_soundlab/get_state", vol.Required("entry_id"): str})
def websocket_get_state(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is not None:
        connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/set_channel",
    vol.Required("entry_id"): str,
    vol.Required("channel"): vol.Coerce(int),
    vol.Required("field"): str,
    vol.Required("value"): vol.Any(bool, str, int, float),
})
def websocket_set_channel(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.set_channel_value(msg["channel"], msg["field"], msg["value"])
    except ValueError as err:
        _send_value_error(connection, msg, err)
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/set_eq_band",
    vol.Required("entry_id"): str,
    vol.Required("channel"): vol.Coerce(int),
    vol.Required("band"): vol.Coerce(int),
    vol.Required("field"): str,
    vol.Required("value"): vol.Any(bool, int, float),
})
def websocket_set_eq_band(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.set_eq_band(msg["channel"], msg["band"], msg["field"], msg["value"])
    except (TypeError, ValueError) as err:
        _send_value_error(connection, msg, ValueError(str(err)))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/reset_eq",
    vol.Required("entry_id"): str,
    vol.Required("channel"): vol.Coerce(int),
})
def websocket_reset_eq(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.reset_eq(msg["channel"])
    except ValueError as err:
        _send_value_error(connection, msg, err)
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/copy_eq",
    vol.Required("entry_id"): str,
    vol.Required("source"): vol.Coerce(int),
    vol.Required("target"): vol.Coerce(int),
})
def websocket_copy_eq(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.copy_eq(msg["source"], msg["target"])
    except ValueError as err:
        _send_value_error(connection, msg, err)
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/set_target_curve_preset",
    vol.Required("entry_id"): str,
    vol.Required("preset"): vol.In(TARGET_CURVE_OPTIONS),
})
def websocket_set_target_curve_preset(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.set_target_curve_preset(msg["preset"])
    except ValueError as err:
        _send_value_error(connection, msg, err)
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/set_target_curve_point",
    vol.Required("entry_id"): str,
    vol.Required("point"): vol.Coerce(int),
    vol.Required("gain_db"): vol.Coerce(float),
})
def websocket_set_target_curve_point(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.set_target_curve_point(msg["point"], msg["gain_db"])
    except (TypeError, ValueError) as err:
        _send_value_error(connection, msg, ValueError(str(err)))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command({vol.Required("type"): "kcc_soundlab/set_preset", vol.Required("entry_id"): str, vol.Required("preset"): str})
def websocket_set_preset(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.set_preset(msg["preset"])
    except ValueError as err:
        _send_value_error(connection, msg, err)
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command({vol.Required("type"): "kcc_soundlab/save_snapshot", vol.Required("entry_id"): str, vol.Required("name"): str})
def websocket_save_snapshot(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    state.save_snapshot(msg["name"])
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command({vol.Required("type"): "kcc_soundlab/restore_snapshot", vol.Required("entry_id"): str, vol.Required("snapshot_id"): str})
def websocket_restore_snapshot(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
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
@websocket_api.websocket_command({vol.Required("type"): "kcc_soundlab/delete_snapshot", vol.Required("entry_id"): str, vol.Required("snapshot_id"): str})
def websocket_delete_snapshot(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
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
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/create_measurement_session",
    vol.Required("entry_id"): str,
    vol.Required("name"): str,
    vol.Required("position"): vol.In(MEASUREMENT_POSITIONS),
    vol.Optional("notes", default=""): str,
})
def websocket_create_measurement_session(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.create_measurement_session(msg["name"], msg["position"], msg.get("notes", ""))
    except ValueError as err:
        _send_value_error(connection, msg, err)
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/select_measurement_session",
    vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
})
def websocket_select_measurement_session(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.select_measurement_session(msg["session_id"])
    except ValueError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/set_measurement_result",
    vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
    vol.Required("channel"): vol.Coerce(int),
    vol.Required("field"): str,
    vol.Required("value"): vol.Any(None, bool, str, int, float),
})
def websocket_set_measurement_result(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.set_measurement_result(msg["session_id"], msg["channel"], msg["field"], msg["value"])
    except (TypeError, ValueError) as err:
        _send_value_error(connection, msg, ValueError(str(err)))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command({
    vol.Required("type"): "kcc_soundlab/delete_measurement_session",
    vol.Required("entry_id"): str,
    vol.Required("session_id"): str,
})
def websocket_delete_measurement_session(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.delete_measurement_session(msg["session_id"])
    except ValueError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
def async_setup_websocket_api(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, websocket_get_state)
    websocket_api.async_register_command(hass, websocket_set_channel)
    websocket_api.async_register_command(hass, websocket_set_eq_band)
    websocket_api.async_register_command(hass, websocket_reset_eq)
    websocket_api.async_register_command(hass, websocket_copy_eq)
    websocket_api.async_register_command(hass, websocket_set_target_curve_preset)
    websocket_api.async_register_command(hass, websocket_set_target_curve_point)
    websocket_api.async_register_command(hass, websocket_set_preset)
    websocket_api.async_register_command(hass, websocket_save_snapshot)
    websocket_api.async_register_command(hass, websocket_restore_snapshot)
    websocket_api.async_register_command(hass, websocket_delete_snapshot)
    websocket_api.async_register_command(hass, websocket_create_measurement_session)
    websocket_api.async_register_command(hass, websocket_select_measurement_session)
    websocket_api.async_register_command(hass, websocket_set_measurement_result)
    websocket_api.async_register_command(hass, websocket_delete_measurement_session)

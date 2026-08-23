"""Read-only multi-position measurement evidence for KCC SoundLab."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .frequency_response_api import _public_response, _state_for_message, _validate_channel


def _repeat_count(session: dict[str, Any], channel_id: str) -> int:
    store = session.get("frequency_response_repeats")
    if not isinstance(store, dict):
        return 0
    samples = store.get(channel_id)
    if not isinstance(samples, list):
        return 0
    return sum(
        isinstance(item, dict) and isinstance(item.get("points"), list)
        for item in samples
    )


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/get_multi_position_responses",
        vol.Required("entry_id"): str,
        vol.Required("channel"): vol.Coerce(int),
    }
)
def websocket_get_multi_position_responses(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    """Return primary REW responses for one output across Measurement positions."""
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        channel = _validate_channel(state, msg["channel"])
    except ValueError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return

    channel_id = str(channel.get("id", ""))
    measurements: list[dict[str, Any]] = []
    position_counts: dict[str, int] = {}

    for session in state.measurement_sessions:
        responses = session.get("frequency_responses")
        if not isinstance(responses, dict):
            continue
        response = _public_response(state, msg["channel"], responses.get(channel_id))
        if response is None:
            continue
        position = str(session.get("position", "Driver seat") or "Driver seat")
        position_counts[position] = position_counts.get(position, 0) + 1
        measurements.append(
            {
                "session_id": str(session.get("id", "")),
                "session_name": str(session.get("name", "Measurement")),
                "created_at": str(session.get("created_at", "")),
                "position": position,
                "notes": str(session.get("notes", "")),
                "is_active": str(session.get("id", "")) == state.active_measurement_session_id,
                "repeat_count": _repeat_count(session, channel_id),
                "response": response,
            }
        )

    connection.send_result(
        msg["id"],
        {
            "channel": msg["channel"],
            "output": str(channel.get("output", "")),
            "speaker": str(channel.get("speaker", "")),
            "measurement_count": len(measurements),
            "position_count": len(position_counts),
            "positions": [
                {"position": position, "measurement_count": count}
                for position, count in sorted(position_counts.items())
            ],
            "measurements": measurements,
        },
    )


@callback
def async_setup_multi_position_api(hass: HomeAssistant) -> None:
    """Register read-only multi-position measurement WebSocket command."""
    websocket_api.async_register_command(hass, websocket_get_multi_position_responses)

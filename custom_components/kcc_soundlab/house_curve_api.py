"""Flexible House Curve storage and WebSocket API for KCC SoundLab."""

from __future__ import annotations

from math import isfinite
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .model import KCCDSPState, TARGET_CURVE_OPTIONS, _default_target_curve

MIN_HOUSE_CURVE_POINTS = 2
MAX_HOUSE_CURVE_POINTS = 16
MIN_FREQUENCY_HZ = 20.0
MAX_FREQUENCY_HZ = 20000.0
MIN_GAIN_DB = -12.0
MAX_GAIN_DB = 12.0


def _normalise_points(points: Any, *, strict: bool) -> list[dict[str, float]]:
    """Validate, sort and de-duplicate House Curve points."""
    if not isinstance(points, list):
        if strict:
            raise ValueError("House Curve points must be a list")
        return []
    if strict and not MIN_HOUSE_CURVE_POINTS <= len(points) <= MAX_HOUSE_CURVE_POINTS:
        raise ValueError(
            f"House Curve must contain between {MIN_HOUSE_CURVE_POINTS} and "
            f"{MAX_HOUSE_CURVE_POINTS} points"
        )

    valid: list[dict[str, float]] = []
    for point in points[:MAX_HOUSE_CURVE_POINTS]:
        if not isinstance(point, dict):
            if strict:
                raise ValueError("Each House Curve point must contain frequency_hz and gain_db")
            continue
        try:
            frequency = float(point.get("frequency_hz"))
            gain = float(point.get("gain_db"))
        except (TypeError, ValueError) as err:
            if strict:
                raise ValueError("House Curve frequency and gain must be numeric") from err
            continue
        if not isfinite(frequency) or not isfinite(gain):
            if strict:
                raise ValueError("House Curve frequency and gain must be finite")
            continue
        if not MIN_FREQUENCY_HZ <= frequency <= MAX_FREQUENCY_HZ:
            if strict:
                raise ValueError("House Curve frequency must be between 20 and 20000 Hz")
            continue
        if not MIN_GAIN_DB <= gain <= MAX_GAIN_DB:
            if strict:
                raise ValueError("House Curve gain must be between -12 and +12 dB")
            continue
        valid.append({"frequency_hz": round(frequency, 3), "gain_db": round(gain, 3)})

    valid.sort(key=lambda item: item["frequency_hz"])
    unique: list[dict[str, float]] = []
    for item in valid:
        if unique and abs(item["frequency_hz"] - unique[-1]["frequency_hz"]) < 0.001:
            if strict:
                raise ValueError("House Curve frequencies must be unique")
            unique[-1] = item
            continue
        unique.append(item)

    if strict and len(unique) < MIN_HOUSE_CURVE_POINTS:
        raise ValueError(f"House Curve must contain at least {MIN_HOUSE_CURVE_POINTS} unique points")
    return unique


class FlexibleKCCDSPState(KCCDSPState):
    """KCC state with variable-length House Curve points."""

    def _normalise_target_curve(self, saved: Any) -> None:
        if not isinstance(saved, dict):
            self.target_curve = _default_target_curve()
            return
        preset = str(saved.get("preset", "Flat"))
        if preset not in TARGET_CURVE_OPTIONS:
            preset = "Custom"
        points = _normalise_points(saved.get("points"), strict=False)
        if len(points) < MIN_HOUSE_CURVE_POINTS:
            self.target_curve = _default_target_curve(
                preset if preset in TARGET_CURVE_OPTIONS and preset != "Custom" else "Flat"
            )
            return
        self.target_curve = {"preset": preset, "points": points}

    def set_target_curve_points(self, points: Any) -> None:
        normalised = _normalise_points(points, strict=True)
        self.target_curve = {"preset": "Custom", "points": normalised}
        self.notify()


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/set_target_curve_points",
        vol.Required("entry_id"): str,
        vol.Required("points"): [
            {
                vol.Required("frequency_hz"): vol.Coerce(float),
                vol.Required("gain_db"): vol.Coerce(float),
            }
        ],
    }
)
def websocket_set_target_curve_points(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    state = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if not isinstance(state, FlexibleKCCDSPState):
        connection.send_error(
            msg["id"], "not_found", "KCC SoundLab config entry is not loaded"
        )
        return
    try:
        state.set_target_curve_points(msg["points"])
    except (TypeError, ValueError) as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
def async_setup_house_curve_api(hass: HomeAssistant) -> None:
    """Register House Curve WebSocket commands."""
    websocket_api.async_register_command(hass, websocket_set_target_curve_points)

"""Flexible House Curve storage and WebSocket API for KCC SoundLab."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from math import isfinite
from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .model import KCCDSPState, TARGET_CURVE_OPTIONS, _default_target_curve

MIN_HOUSE_CURVE_POINTS = 2
MAX_HOUSE_CURVE_POINTS = 16
MIN_FREQUENCY_HZ = 20.0
MAX_FREQUENCY_HZ = 20000.0
MIN_GAIN_DB = -12.0
MAX_GAIN_DB = 12.0
MAX_HOUSE_CURVE_PRESETS = 20
HOUSE_CURVE_LIBRARY_STORE_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    """KCC state with variable-length House Curve points and saved curve presets."""

    def __init__(self, hass: HomeAssistant, entry_id: str, channel_count: int) -> None:
        super().__init__(hass, entry_id, channel_count)
        self.house_curve_presets: list[dict[str, Any]] = []
        self._house_curve_store: Store[dict[str, Any]] = Store(
            hass,
            HOUSE_CURVE_LIBRARY_STORE_VERSION,
            f"{DOMAIN}.{entry_id}.house_curves",
        )

    async def async_load(self) -> None:
        await super().async_load()
        data = await self._house_curve_store.async_load()
        presets = data.get("presets") if isinstance(data, dict) else None
        if not isinstance(presets, list):
            return
        normalised: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for item in presets[-MAX_HOUSE_CURVE_PRESETS:]:
            saved = self._normalise_saved_preset(item)
            if saved is None or saved["id"] in seen_ids:
                continue
            seen_ids.add(saved["id"])
            normalised.append(saved)
        self.house_curve_presets = normalised

    def _normalise_saved_preset(self, item: Any) -> dict[str, Any] | None:
        if not isinstance(item, dict):
            return None
        preset_id = str(item.get("id", "")).strip()[:32]
        name = str(item.get("name", "")).strip()[:48]
        points = _normalise_points(item.get("points"), strict=False)
        if not preset_id or not name or len(points) < MIN_HOUSE_CURVE_POINTS:
            return None
        created_at = str(item.get("created_at", "")).strip() or _utc_now()
        updated_at = str(item.get("updated_at", "")).strip() or created_at
        return {
            "id": preset_id,
            "name": name,
            "created_at": created_at,
            "updated_at": updated_at,
            "points": points,
        }

    def _schedule_house_curve_library_save(self) -> None:
        self.hass.async_create_task(
            self._house_curve_store.async_save(
                {"presets": deepcopy(self.house_curve_presets)}
            )
        )

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

    def save_house_curve_preset(self, name: str) -> str:
        clean_name = str(name).strip()[:48]
        if not clean_name:
            raise ValueError("House Curve preset name cannot be empty")
        points = _normalise_points(self.target_curve.get("points"), strict=True)
        now = _utc_now()
        existing = next(
            (
                item
                for item in self.house_curve_presets
                if str(item.get("name", "")).casefold() == clean_name.casefold()
            ),
            None,
        )
        if existing is not None:
            existing["name"] = clean_name
            existing["points"] = deepcopy(points)
            existing["updated_at"] = now
            preset_id = str(existing["id"])
        else:
            preset_id = uuid4().hex[:12]
            self.house_curve_presets.append(
                {
                    "id": preset_id,
                    "name": clean_name,
                    "created_at": now,
                    "updated_at": now,
                    "points": deepcopy(points),
                }
            )
            self.house_curve_presets = self.house_curve_presets[
                -MAX_HOUSE_CURVE_PRESETS:
            ]
        self._schedule_house_curve_library_save()
        return preset_id

    def load_house_curve_preset(self, preset_id: str) -> None:
        saved = next(
            (
                item
                for item in self.house_curve_presets
                if item.get("id") == str(preset_id)
            ),
            None,
        )
        if saved is None:
            raise ValueError("House Curve preset was not found")
        self.set_target_curve_points(deepcopy(saved["points"]))

    def delete_house_curve_preset(self, preset_id: str) -> None:
        before = len(self.house_curve_presets)
        self.house_curve_presets = [
            item
            for item in self.house_curve_presets
            if item.get("id") != str(preset_id)
        ]
        if len(self.house_curve_presets) == before:
            raise ValueError("House Curve preset was not found")
        self._schedule_house_curve_library_save()

    def snapshot(self) -> dict[str, Any]:
        state = super().snapshot()
        state["house_curve_presets"] = [
            {
                "id": str(item.get("id", "")),
                "name": str(item.get("name", "House Curve")),
                "created_at": str(item.get("created_at", "")),
                "updated_at": str(item.get("updated_at", "")),
                "point_count": len(item.get("points", [])),
            }
            for item in reversed(self.house_curve_presets)
        ]
        return state


def _state_for_message(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> FlexibleKCCDSPState | None:
    state = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if isinstance(state, FlexibleKCCDSPState):
        return state
    connection.send_error(
        msg["id"], "not_found", "KCC SoundLab config entry is not loaded"
    )
    return None


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
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.set_target_curve_points(msg["points"])
    except (TypeError, ValueError) as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/save_house_curve_preset",
        vol.Required("entry_id"): str,
        vol.Required("name"): str,
    }
)
def websocket_save_house_curve_preset(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.save_house_curve_preset(msg["name"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_format", str(err))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/load_house_curve_preset",
        vol.Required("entry_id"): str,
        vol.Required("preset_id"): str,
    }
)
def websocket_load_house_curve_preset(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.load_house_curve_preset(msg["preset_id"])
    except ValueError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "kcc_soundlab/delete_house_curve_preset",
        vol.Required("entry_id"): str,
        vol.Required("preset_id"): str,
    }
)
def websocket_delete_house_curve_preset(
    hass: HomeAssistant, connection: Any, msg: dict[str, Any]
) -> None:
    state = _state_for_message(hass, connection, msg)
    if state is None:
        return
    try:
        state.delete_house_curve_preset(msg["preset_id"])
    except ValueError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return
    connection.send_result(msg["id"], state.snapshot())


@callback
def async_setup_house_curve_api(hass: HomeAssistant) -> None:
    """Register House Curve WebSocket commands."""
    websocket_api.async_register_command(hass, websocket_set_target_curve_points)
    websocket_api.async_register_command(hass, websocket_save_house_curve_preset)
    websocket_api.async_register_command(hass, websocket_load_house_curve_preset)
    websocket_api.async_register_command(hass, websocket_delete_house_curve_preset)

"""Compact status sensors for KCC SoundLab."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DSP_MODEL, CONF_VEHICLE, DOMAIN
from .entity import KCCDSPBaseEntity
from .model import KCCDSPState


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    state: KCCDSPState = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KCCStatusSensor(state, entry), KCCReferenceSensor(state, entry)])


class KCCStatusSensor(KCCDSPBaseEntity, SensorEntity):
    _attr_icon = "mdi:tune-vertical"

    def __init__(self, state: KCCDSPState, entry: ConfigEntry) -> None:
        super().__init__(state, entry.title, entry.data[CONF_DSP_MODEL], entry.data[CONF_VEHICLE])
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_suggested_object_id = "kcc_soundlab_status"
        self._attr_name = "Status"

    @property
    def native_value(self) -> str:
        return "Ready"

    @property
    def extra_state_attributes(self) -> dict[str, int | str]:
        channels = self._soundlab_state.channels
        active = None
        if self._soundlab_state.active_measurement_session_id:
            try:
                active = self._soundlab_state.measurement_session(self._soundlab_state.active_measurement_session_id)
            except ValueError:
                active = None
        measured_in_active = 0
        if active is not None:
            measured_in_active = sum(bool(item.get("completed")) for item in active.get("results", []))
        return {
            **super().extra_state_attributes,
            "preset": self._soundlab_state.preset,
            "active_outputs": self._soundlab_state.channel_count,
            "measured_outputs": sum(float(item.get("distance_cm", 0.0)) > 0 for item in channels),
            "polarity_verified": sum(bool(item.get("polarity_verified")) for item in channels),
            "alignment_verified": sum(bool(item.get("alignment_verified")) for item in channels),
            "tuning_snapshots": len(self._soundlab_state.snapshots),
            "measurement_sessions": len(self._soundlab_state.measurement_sessions),
            "active_measurement_progress": f"{measured_in_active}/{self._soundlab_state.channel_count}" if active else "none",
            "goldhorn_link": "manual",
        }


class KCCReferenceSensor(KCCDSPBaseEntity, SensorEntity):
    _attr_icon = "mdi:target"

    def __init__(self, state: KCCDSPState, entry: ConfigEntry) -> None:
        super().__init__(state, entry.title, entry.data[CONF_DSP_MODEL], entry.data[CONF_VEHICLE])
        self._attr_unique_id = f"{entry.entry_id}_reference_channel"
        self._attr_suggested_object_id = "kcc_soundlab_reference_channel"
        self._attr_name = "Time alignment reference"

    @property
    def native_value(self) -> str:
        channel = self._soundlab_state.channel(self._soundlab_state.reference_index)
        return str(channel["output"])

    @property
    def extra_state_attributes(self) -> dict[str, float | str]:
        channel = self._soundlab_state.channel(self._soundlab_state.reference_index)
        return {
            **super().extra_state_attributes,
            "channel_name": str(channel["name"]),
            "speaker": str(channel.get("speaker", channel["name"])),
            "location": str(channel.get("location", "Other")),
            "distance_cm": round(self._soundlab_state.reference_distance_cm, 1),
        }

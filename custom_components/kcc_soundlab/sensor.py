"""Compact status sensors for KCC SoundLab."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DSP_MODEL, CONF_VEHICLE, DOMAIN
from .entity import KCCDSPBaseEntity
from .model import KCCDSPState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up only the useful Home Assistant status entities."""
    state: KCCDSPState = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            KCCStatusSensor(state, entry),
            KCCReferenceSensor(state, entry),
        ]
    )


class KCCStatusSensor(KCCDSPBaseEntity, SensorEntity):
    """Expose a compact SoundLab workspace status."""

    _attr_icon = "mdi:tune-vertical"

    def __init__(self, state: KCCDSPState, entry: ConfigEntry) -> None:
        super().__init__(
            state,
            entry.title,
            entry.data[CONF_DSP_MODEL],
            entry.data[CONF_VEHICLE],
        )
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_suggested_object_id = "kcc_soundlab_status"
        self._attr_name = "Status"

    @property
    def native_value(self) -> str:
        return "Ready"

    @property
    def extra_state_attributes(self) -> dict[str, int | str]:
        return {
            **super().extra_state_attributes,
            "preset": self._soundlab_state.preset,
            "active_outputs": self._soundlab_state.channel_count,
            "goldhorn_link": "manual",
        }


class KCCReferenceSensor(KCCDSPBaseEntity, SensorEntity):
    """Show which output currently acts as time-alignment reference."""

    _attr_icon = "mdi:target"

    def __init__(self, state: KCCDSPState, entry: ConfigEntry) -> None:
        super().__init__(
            state,
            entry.title,
            entry.data[CONF_DSP_MODEL],
            entry.data[CONF_VEHICLE],
        )
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
            "distance_cm": round(self._soundlab_state.reference_distance_cm, 1),
        }

"""Calculated sensor entities for KCC SoundLab."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength, UnitOfTime
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
    state: KCCDSPState = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [KCCReferenceSensor(state, entry)]
    for index in range(state.channel_count):
        entities.extend(
            [
                KCCDelaySensor(state, entry, index),
                KCCPathDeltaSensor(state, entry, index),
            ]
        )
    async_add_entities(entities)


class _ChannelSensor(KCCDSPBaseEntity, SensorEntity):
    def __init__(self, state: KCCDSPState, entry: ConfigEntry, index: int) -> None:
        super().__init__(
            state,
            entry.title,
            entry.data[CONF_DSP_MODEL],
            entry.data[CONF_VEHICLE],
        )
        self.index = index


class KCCDelaySensor(_ChannelSensor):
    """Calculated delay relative to the furthest speaker."""

    _attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
    _attr_icon = "mdi:timer-sand"

    def __init__(self, state: KCCDSPState, entry: ConfigEntry, index: int) -> None:
        super().__init__(state, entry, index)
        channel = state.channel(index)
        self._attr_unique_id = f"{entry.entry_id}_{channel['id']}_calculated_delay"
        self._attr_suggested_object_id = f"kcc_soundlab_{channel['id']}_calculated_delay"
        self._attr_name = f"{channel['output']} Calculated delay"

    @property
    def native_value(self) -> float:
        return round(self.state.delay_for(self.index), 3)


class KCCPathDeltaSensor(_ChannelSensor):
    """Calculated path difference relative to the furthest speaker."""

    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS
    _attr_icon = "mdi:ruler"

    def __init__(self, state: KCCDSPState, entry: ConfigEntry, index: int) -> None:
        super().__init__(state, entry, index)
        channel = state.channel(index)
        self._attr_unique_id = f"{entry.entry_id}_{channel['id']}_path_delta"
        self._attr_suggested_object_id = f"kcc_soundlab_{channel['id']}_path_delta"
        self._attr_name = f"{channel['output']} Path difference"

    @property
    def native_value(self) -> float:
        return round(self.state.path_delta_for(self.index), 1)


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
        channel = self.state.channel(self.state.reference_index)
        return str(channel["output"])

    @property
    def extra_state_attributes(self) -> dict[str, float | str]:
        channel = self.state.channel(self.state.reference_index)
        return {
            "channel_name": str(channel["name"]),
            "distance_cm": round(self.state.reference_distance_cm, 1),
        }

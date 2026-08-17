"""Number entities for KCC SoundLab."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DSP_MODEL, CONF_VEHICLE, DOMAIN
from .entity import KCCDSPBaseEntity
from .model import KCCDSPState


@dataclass(frozen=True, kw_only=True)
class KCCNumberDescription(NumberEntityDescription):
    """Describe one numeric DSP setting."""

    field: str


DESCRIPTIONS = (
    KCCNumberDescription(
        key="distance",
        translation_key="distance",
        field="distance_cm",
        native_min_value=0,
        native_max_value=680,
        native_step=0.1,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        mode=NumberMode.BOX,
    ),
    KCCNumberDescription(
        key="gain",
        translation_key="gain",
        field="gain_db",
        native_min_value=-20,
        native_max_value=5,
        native_step=0.1,
        native_unit_of_measurement="dB",
        mode=NumberMode.BOX,
    ),
    KCCNumberDescription(
        key="phase",
        translation_key="phase",
        field="phase_deg",
        native_min_value=0,
        native_max_value=360,
        native_step=1,
        native_unit_of_measurement="°",
        mode=NumberMode.BOX,
    ),
    KCCNumberDescription(
        key="hpf_frequency",
        translation_key="hpf_frequency",
        field="hpf_hz",
        native_min_value=20,
        native_max_value=20000,
        native_step=1,
        native_unit_of_measurement="Hz",
        mode=NumberMode.BOX,
    ),
    KCCNumberDescription(
        key="lpf_frequency",
        translation_key="lpf_frequency",
        field="lpf_hz",
        native_min_value=20,
        native_max_value=20000,
        native_step=1,
        native_unit_of_measurement="Hz",
        mode=NumberMode.BOX,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    state: KCCDSPState = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for index in range(state.channel_count):
        for description in DESCRIPTIONS:
            entities.append(KCCChannelNumber(state, entry, index, description))
    async_add_entities(entities)


class KCCChannelNumber(KCCDSPBaseEntity, NumberEntity):
    """Editable numeric setting for one DSP output."""

    entity_description: KCCNumberDescription

    def __init__(
        self,
        state: KCCDSPState,
        entry: ConfigEntry,
        index: int,
        description: KCCNumberDescription,
    ) -> None:
        super().__init__(
            state,
            entry.title,
            entry.data[CONF_DSP_MODEL],
            entry.data[CONF_VEHICLE],
        )
        self.index = index
        self.entity_description = description
        channel = state.channel(index)
        self._attr_unique_id = f"{entry.entry_id}_{channel['id']}_{description.key}"
        self._attr_name = f"{channel['output']} {description.name or description.key.replace('_', ' ').title()}"

    @property
    def native_value(self) -> float:
        return float(self.state.channel(self.index)[self.entity_description.field])

    async def async_set_native_value(self, value: float) -> None:
        self.state.channel(self.index)[self.entity_description.field] = float(value)
        self.state.notify()

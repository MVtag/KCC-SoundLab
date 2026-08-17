"""Select entities for KCC SoundLab."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DSP_MODEL, CONF_VEHICLE, DOMAIN
from .entity import KCCDSPBaseEntity
from .model import KCCDSPState


@dataclass(frozen=True, kw_only=True)
class KCCSelectDescription(SelectEntityDescription):
    field: str


SLOPES = [f"{value} dB/oct" for value in (6, 12, 18, 24, 30, 36, 42, 48)]
FILTERS = ["Butterworth", "Linkwitz-Riley", "Bessel"]

DESCRIPTIONS = (
    KCCSelectDescription(
        key="polarity",
        translation_key="polarity",
        field="polarity",
        options=["Normal", "Inverted"],
    ),
    KCCSelectDescription(
        key="hpf_type",
        translation_key="hpf_type",
        field="hpf_type",
        options=FILTERS,
    ),
    KCCSelectDescription(
        key="hpf_slope",
        translation_key="hpf_slope",
        field="hpf_slope",
        options=SLOPES,
    ),
    KCCSelectDescription(
        key="lpf_type",
        translation_key="lpf_type",
        field="lpf_type",
        options=FILTERS,
    ),
    KCCSelectDescription(
        key="lpf_slope",
        translation_key="lpf_slope",
        field="lpf_slope",
        options=SLOPES,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    state: KCCDSPState = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        KCCChannelSelect(state, entry, index, description)
        for index in range(state.channel_count)
        for description in DESCRIPTIONS
    )


class KCCChannelSelect(KCCDSPBaseEntity, SelectEntity):
    """Editable select setting for one DSP output."""

    entity_description: KCCSelectDescription

    def __init__(
        self,
        state: KCCDSPState,
        entry: ConfigEntry,
        index: int,
        description: KCCSelectDescription,
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
        self._attr_name = f"{channel['output']} {description.key.replace('_', ' ').title()}"

    @property
    def current_option(self) -> str:
        return str(self.state.channel(self.index)[self.entity_description.field])

    async def async_select_option(self, option: str) -> None:
        self.state.channel(self.index)[self.entity_description.field] = option
        self.state.notify()

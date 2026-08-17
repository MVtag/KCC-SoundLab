"""Base entity helpers for KCC SoundLab."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .model import KCCDSPState


class KCCDSPBaseEntity(Entity):
    """Base entity connected to one DSP config entry."""

    _attr_has_entity_name = True

    def __init__(
        self,
        state: KCCDSPState,
        entry_title: str,
        dsp_model: str,
        vehicle: str,
    ) -> None:
        self.state = state
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, state.entry_id)},
            name=entry_title,
            manufacturer="KCC / Goldhorn",
            model=dsp_model,
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.state.add_listener(self.async_write_ha_state))

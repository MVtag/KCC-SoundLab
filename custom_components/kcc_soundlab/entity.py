"""Base entity helpers for KCC SoundLab."""

from __future__ import annotations

from typing import Any

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

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose stable metadata so the SoundLab frontend never relies on entity IDs."""
        attributes: dict[str, Any] = {
            "kcc_soundlab_entry_id": self.state.entry_id,
        }

        index = getattr(self, "index", None)
        if isinstance(index, int) and 0 <= index < self.state.channel_count:
            channel = self.state.channel(index)
            attributes["kcc_soundlab_channel_id"] = str(channel["id"])
            attributes["kcc_soundlab_output"] = str(channel["output"])

        description = getattr(self, "entity_description", None)
        key = getattr(description, "key", None) or getattr(self, "_kcc_key", None)
        if key:
            attributes["kcc_soundlab_key"] = str(key)

        return attributes

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.state.add_listener(self.async_write_ha_state))

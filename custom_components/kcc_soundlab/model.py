"""In-memory and persistent data model for KCC SoundLab."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import CM_PER_MS, DOMAIN, MAX_CHANNELS

STORE_VERSION = 1


def _default_channel(index: int) -> dict[str, Any]:
    letter = chr(ord("A") + index)
    return {
        "id": f"out_{letter.lower()}",
        "output": f"OUT {letter}",
        "name": f"OUT {letter}",
        "distance_cm": 0.0,
        "gain_db": 0.0,
        "phase_deg": 0.0,
        "polarity": "Normal",
        "hpf_type": "Linkwitz-Riley",
        "hpf_hz": 20.0,
        "hpf_slope": "24 dB/oct",
        "lpf_type": "Linkwitz-Riley",
        "lpf_hz": 20000.0,
        "lpf_slope": "24 dB/oct",
    }


class KCCDSPState:
    """Hold DSP tuning data and notify Home Assistant entities on changes."""

    def __init__(self, hass: HomeAssistant, entry_id: str, channel_count: int) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.channel_count = max(1, min(int(channel_count), MAX_CHANNELS))
        self.channels = [_default_channel(i) for i in range(self.channel_count)]
        self.preset = "Driver SQ"
        self._listeners: set[Callable[[], None]] = set()
        self._store: Store[dict[str, Any]] = Store(
            hass, STORE_VERSION, f"{DOMAIN}.{entry_id}"
        )

    async def async_load(self) -> None:
        """Load persisted tuning state."""
        data = await self._store.async_load()
        if not data:
            return

        saved_channels = data.get("channels")
        if isinstance(saved_channels, list):
            by_id = {
                item.get("id"): item
                for item in saved_channels
                if isinstance(item, dict) and item.get("id")
            }
            for channel in self.channels:
                saved = by_id.get(channel["id"])
                if saved:
                    channel.update(saved)

        preset = data.get("preset")
        if isinstance(preset, str):
            self.preset = preset

    async def async_save(self) -> None:
        """Persist tuning state."""
        await self._store.async_save(
            {"channels": deepcopy(self.channels), "preset": self.preset}
        )

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Register a state listener."""
        self._listeners.add(listener)

        def remove() -> None:
            self._listeners.discard(listener)

        return remove

    def notify(self) -> None:
        """Notify all entities that a tuning value changed."""
        for listener in tuple(self._listeners):
            listener()
        self.hass.async_create_task(self.async_save())

    def channel(self, index: int) -> dict[str, Any]:
        return self.channels[index]

    @property
    def reference_index(self) -> int:
        """Return the furthest channel index; first channel wins ties."""
        return max(
            range(len(self.channels)),
            key=lambda idx: float(self.channels[idx].get("distance_cm", 0.0)),
        )

    @property
    def reference_distance_cm(self) -> float:
        return float(self.channels[self.reference_index].get("distance_cm", 0.0))

    def delay_for(self, index: int) -> float:
        """Calculate delay needed to align a channel to the furthest speaker."""
        own = float(self.channels[index].get("distance_cm", 0.0))
        delta = max(0.0, self.reference_distance_cm - own)
        return delta / CM_PER_MS

    def path_delta_for(self, index: int) -> float:
        own = float(self.channels[index].get("distance_cm", 0.0))
        return max(0.0, self.reference_distance_cm - own)

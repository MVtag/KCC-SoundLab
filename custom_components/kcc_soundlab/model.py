"""In-memory and persistent data model for KCC SoundLab."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import CM_PER_MS, DOMAIN, MAX_CHANNELS

STORE_VERSION = 1

FILTERS = ("Butterworth", "Linkwitz-Riley", "Bessel")
SLOPES = tuple(f"{value} dB/oct" for value in (6, 12, 18, 24, 30, 36, 42, 48))
PRESETS = ("Driver SQ", "Front Both", "Bass Mode", "Tuning")

_NUMERIC_FIELDS: dict[str, tuple[float, float]] = {
    "distance_cm": (0.0, 680.0),
    "gain_db": (-20.0, 5.0),
    "phase_deg": (0.0, 360.0),
    "hpf_hz": (20.0, 20000.0),
    "lpf_hz": (20.0, 20000.0),
}
_SELECT_FIELDS: dict[str, tuple[str, ...]] = {
    "polarity": ("Normal", "Inverted"),
    "hpf_type": FILTERS,
    "hpf_slope": SLOPES,
    "lpf_type": FILTERS,
    "lpf_slope": SLOPES,
}


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
    """Hold DSP tuning data and notify Home Assistant listeners on changes."""

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
        if isinstance(preset, str) and preset in PRESETS:
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
        """Notify status entities and schedule persistence."""
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
        """Return path difference to the furthest speaker in centimeters."""
        own = float(self.channels[index].get("distance_cm", 0.0))
        return max(0.0, self.reference_distance_cm - own)

    def set_channel_value(self, index: int, field: str, value: Any) -> None:
        """Validate and update one internal channel value."""
        if not 0 <= index < self.channel_count:
            raise ValueError("Channel index is out of range")

        channel = self.channel(index)
        if field in _NUMERIC_FIELDS:
            try:
                numeric_value = float(value)
            except (TypeError, ValueError) as err:
                raise ValueError(f"{field} must be numeric") from err
            minimum, maximum = _NUMERIC_FIELDS[field]
            if not minimum <= numeric_value <= maximum:
                raise ValueError(f"{field} must be between {minimum} and {maximum}")
            channel[field] = numeric_value
        elif field in _SELECT_FIELDS:
            option = str(value)
            if option not in _SELECT_FIELDS[field]:
                raise ValueError(f"Invalid option for {field}")
            channel[field] = option
        else:
            raise ValueError(f"Unsupported SoundLab field: {field}")

        self.notify()

    def set_preset(self, preset: str) -> None:
        """Validate and set the active SoundLab preset."""
        if preset not in PRESETS:
            raise ValueError("Invalid SoundLab preset")
        self.preset = preset
        self.notify()

    def snapshot(self) -> dict[str, Any]:
        """Return a frontend-safe snapshot with calculated alignment data."""
        channels: list[dict[str, Any]] = []
        for index, channel in enumerate(self.channels):
            item = deepcopy(channel)
            item["delay_ms"] = round(self.delay_for(index), 3)
            item["path_delta_cm"] = round(self.path_delta_for(index), 1)
            channels.append(item)

        reference = self.channel(self.reference_index)
        return {
            "entry_id": self.entry_id,
            "preset": self.preset,
            "channel_count": self.channel_count,
            "channels": channels,
            "reference": {
                "index": self.reference_index,
                "output": str(reference["output"]),
                "channel_id": str(reference["id"]),
                "distance_cm": round(self.reference_distance_cm, 1),
            },
        }

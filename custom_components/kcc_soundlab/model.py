"""In-memory and persistent data model for KCC SoundLab."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import CM_PER_MS, DOMAIN, MAX_CHANNELS

STORE_VERSION = 1
MAX_SNAPSHOTS = 20
MAX_MEASUREMENT_SESSIONS = 20

FILTERS = ("Butterworth", "Linkwitz-Riley", "Bessel")
SLOPES = tuple(f"{value} dB/oct" for value in (6, 12, 18, 24, 30, 36, 42, 48))
PRESETS = ("Driver SQ", "Front Both", "Bass Mode", "Tuning")
ROLES = (
    "Full-range", "Tweeter", "Midrange", "Midbass", "Woofer",
    "Subwoofer", "Center", "Rear fill", "DSP output",
)
LOCATIONS = (
    "Front left dash", "Front right dash", "Front left door", "Front right door",
    "Center dash", "Rear left", "Rear right", "Boot / trunk", "Under seat", "Other",
)
MEASUREMENT_POSITIONS = ("Driver seat", "Passenger seat", "Center", "Custom")
MEASUREMENT_POLARITY = ("Unknown", "Positive", "Negative")

_NUMERIC_FIELDS: dict[str, tuple[float, float]] = {
    "distance_cm": (0.0, 680.0),
    "gain_db": (-20.0, 5.0),
    "phase_deg": (0.0, 360.0),
    "hpf_hz": (20.0, 20000.0),
    "lpf_hz": (20.0, 20000.0),
    "fine_delay_ms": (-5.0, 5.0),
}
_SELECT_FIELDS: dict[str, tuple[str, ...]] = {
    "polarity": ("Normal", "Inverted"),
    "hpf_type": FILTERS,
    "hpf_slope": SLOPES,
    "lpf_type": FILTERS,
    "lpf_slope": SLOPES,
    "role": ROLES,
    "location": LOCATIONS,
}
_TEXT_FIELDS: dict[str, int] = {"name": 48, "speaker": 80}
_BOOL_FIELDS = {"polarity_verified", "alignment_verified"}

_PROFILE = (
    ("BLAM FRS2N50 L", "Full-range", "Front left dash"),
    ("BLAM FRS2N50 R", "Full-range", "Front right dash"),
    ("BLAM 165 LSQ L", "Midbass", "Front left door"),
    ("BLAM 165 LSQ R", "Midbass", "Front right door"),
    ("BLAM SuperSub12", "Subwoofer", "Boot / trunk"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_channel(index: int) -> dict[str, Any]:
    letter = chr(ord("A") + index)
    speaker, role, location = (
        _PROFILE[index] if index < len(_PROFILE)
        else (f"OUT {letter}", "DSP output", "Other")
    )
    return {
        "id": f"out_{letter.lower()}", "output": f"OUT {letter}", "name": f"OUT {letter}",
        "speaker": speaker, "role": role, "location": location,
        "distance_cm": 0.0, "gain_db": 0.0, "phase_deg": 0.0,
        "polarity": "Normal", "polarity_verified": False,
        "hpf_type": "Linkwitz-Riley", "hpf_hz": 20.0, "hpf_slope": "24 dB/oct",
        "lpf_type": "Linkwitz-Riley", "lpf_hz": 20000.0, "lpf_slope": "24 dB/oct",
        "fine_delay_ms": 0.0, "alignment_verified": False,
    }


def _default_measurement_result(channel: dict[str, Any]) -> dict[str, Any]:
    return {
        "channel_id": str(channel["id"]),
        "completed": False,
        "impulse_ms": None,
        "level_db": None,
        "polarity": "Unknown",
        "notes": "",
        "measured_at": "",
    }


class KCCDSPState:
    """Hold DSP tuning and measurement data and notify listeners on changes."""

    def __init__(self, hass: HomeAssistant, entry_id: str, channel_count: int) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.channel_count = max(1, min(int(channel_count), MAX_CHANNELS))
        self.channels = [_default_channel(i) for i in range(self.channel_count)]
        self.preset = "Driver SQ"
        self.snapshots: list[dict[str, Any]] = []
        self.measurement_sessions: list[dict[str, Any]] = []
        self.active_measurement_session_id: str | None = None
        self._listeners: set[Callable[[], None]] = set()
        self._store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry_id}")

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if not data:
            return
        saved_channels = data.get("channels")
        if isinstance(saved_channels, list):
            by_id = {item.get("id"): item for item in saved_channels if isinstance(item, dict) and item.get("id")}
            for channel in self.channels:
                saved = by_id.get(channel["id"])
                if saved:
                    channel.update(saved)
        preset = data.get("preset")
        if isinstance(preset, str) and preset in PRESETS:
            self.preset = preset
        snapshots = data.get("snapshots")
        if isinstance(snapshots, list):
            self.snapshots = [item for item in snapshots[-MAX_SNAPSHOTS:] if isinstance(item, dict)]
        sessions = data.get("measurement_sessions")
        if isinstance(sessions, list):
            self.measurement_sessions = [item for item in sessions[-MAX_MEASUREMENT_SESSIONS:] if isinstance(item, dict)]
            for session in self.measurement_sessions:
                self._normalise_measurement_session(session)
        active_id = data.get("active_measurement_session_id")
        if isinstance(active_id, str) and any(item.get("id") == active_id for item in self.measurement_sessions):
            self.active_measurement_session_id = active_id
        elif self.measurement_sessions:
            self.active_measurement_session_id = str(self.measurement_sessions[-1].get("id"))

    async def async_save(self) -> None:
        await self._store.async_save({
            "channels": deepcopy(self.channels),
            "preset": self.preset,
            "snapshots": deepcopy(self.snapshots),
            "measurement_sessions": deepcopy(self.measurement_sessions),
            "active_measurement_session_id": self.active_measurement_session_id,
        })

    def add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(listener)
        def remove() -> None:
            self._listeners.discard(listener)
        return remove

    def notify(self) -> None:
        for listener in tuple(self._listeners):
            listener()
        self.hass.async_create_task(self.async_save())

    def channel(self, index: int) -> dict[str, Any]:
        return self.channels[index]

    @property
    def reference_index(self) -> int:
        return max(range(len(self.channels)), key=lambda idx: float(self.channels[idx].get("distance_cm", 0.0)))

    @property
    def reference_distance_cm(self) -> float:
        return float(self.channels[self.reference_index].get("distance_cm", 0.0))

    def delay_for(self, index: int) -> float:
        own = float(self.channels[index].get("distance_cm", 0.0))
        return max(0.0, self.reference_distance_cm - own) / CM_PER_MS

    def recommended_delay_for(self, index: int) -> float:
        correction = float(self.channels[index].get("fine_delay_ms", 0.0))
        return max(0.0, min(20.0, self.delay_for(index) + correction))

    def path_delta_for(self, index: int) -> float:
        own = float(self.channels[index].get("distance_cm", 0.0))
        return max(0.0, self.reference_distance_cm - own)

    def set_channel_value(self, index: int, field: str, value: Any) -> None:
        if not 0 <= index < self.channel_count:
            raise ValueError("Channel index is out of range")
        channel = self.channel(index)
        if field in _BOOL_FIELDS:
            if not isinstance(value, bool):
                raise ValueError(f"{field} must be true or false")
            channel[field] = value
        elif field in _NUMERIC_FIELDS:
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
        elif field in _TEXT_FIELDS:
            text = str(value).strip()
            if not text:
                raise ValueError(f"{field} cannot be empty")
            if len(text) > _TEXT_FIELDS[field]:
                raise ValueError(f"{field} is too long")
            channel[field] = text
        else:
            raise ValueError(f"Unsupported SoundLab field: {field}")
        self.notify()

    def set_preset(self, preset: str) -> None:
        if preset not in PRESETS:
            raise ValueError("Invalid SoundLab preset")
        self.preset = preset
        self.notify()

    def save_snapshot(self, name: str) -> str:
        clean_name = str(name).strip()[:64] or f"Tuning {len(self.snapshots) + 1}"
        snapshot_id = uuid4().hex[:12]
        self.snapshots.append({
            "id": snapshot_id, "name": clean_name, "created_at": _utc_now(),
            "preset": self.preset, "channels": deepcopy(self.channels),
        })
        self.snapshots = self.snapshots[-MAX_SNAPSHOTS:]
        self.notify()
        return snapshot_id

    def restore_snapshot(self, snapshot_id: str) -> None:
        saved = next((item for item in self.snapshots if item.get("id") == snapshot_id), None)
        if saved is None:
            raise ValueError("Tuning snapshot was not found")
        saved_channels = saved.get("channels")
        if isinstance(saved_channels, list):
            by_id = {item.get("id"): item for item in saved_channels if isinstance(item, dict) and item.get("id")}
            for index, channel in enumerate(self.channels):
                restored = by_id.get(channel["id"])
                if restored:
                    fresh = _default_channel(index)
                    fresh.update(restored)
                    fresh["id"] = channel["id"]
                    fresh["output"] = channel["output"]
                    self.channels[index] = fresh
        preset = saved.get("preset")
        if isinstance(preset, str) and preset in PRESETS:
            self.preset = preset
        self.notify()

    def delete_snapshot(self, snapshot_id: str) -> None:
        before = len(self.snapshots)
        self.snapshots = [item for item in self.snapshots if item.get("id") != snapshot_id]
        if len(self.snapshots) == before:
            raise ValueError("Tuning snapshot was not found")
        self.notify()

    def _normalise_measurement_session(self, session: dict[str, Any]) -> None:
        results = session.get("results")
        by_id = {}
        if isinstance(results, list):
            by_id = {item.get("channel_id"): item for item in results if isinstance(item, dict) and item.get("channel_id")}
        normalised = []
        for channel in self.channels:
            result = _default_measurement_result(channel)
            saved = by_id.get(channel["id"])
            if saved:
                result.update(saved)
            result["channel_id"] = channel["id"]
            normalised.append(result)
        session["results"] = normalised
        session.setdefault("position", "Driver seat")
        session.setdefault("notes", "")

    def create_measurement_session(self, name: str, position: str, notes: str = "") -> str:
        clean_name = str(name).strip()[:64] or f"Measurement {len(self.measurement_sessions) + 1}"
        if position not in MEASUREMENT_POSITIONS:
            raise ValueError("Invalid measurement position")
        session_id = uuid4().hex[:12]
        session = {
            "id": session_id,
            "name": clean_name,
            "created_at": _utc_now(),
            "position": position,
            "notes": str(notes).strip()[:500],
            "results": [_default_measurement_result(channel) for channel in self.channels],
        }
        self.measurement_sessions.append(session)
        self.measurement_sessions = self.measurement_sessions[-MAX_MEASUREMENT_SESSIONS:]
        self.active_measurement_session_id = session_id
        self.notify()
        return session_id

    def measurement_session(self, session_id: str) -> dict[str, Any]:
        session = next((item for item in self.measurement_sessions if item.get("id") == session_id), None)
        if session is None:
            raise ValueError("Measurement session was not found")
        return session

    def select_measurement_session(self, session_id: str) -> None:
        self.measurement_session(session_id)
        self.active_measurement_session_id = session_id
        self.notify()

    def set_measurement_result(self, session_id: str, channel_index: int, field: str, value: Any) -> None:
        if not 0 <= channel_index < self.channel_count:
            raise ValueError("Channel index is out of range")
        session = self.measurement_session(session_id)
        self._normalise_measurement_session(session)
        result = session["results"][channel_index]
        if field == "completed":
            if not isinstance(value, bool):
                raise ValueError("completed must be true or false")
            result[field] = value
            result["measured_at"] = _utc_now() if value else ""
        elif field == "impulse_ms":
            if value in (None, ""):
                result[field] = None
            else:
                numeric = float(value)
                if not 0.0 <= numeric <= 100.0:
                    raise ValueError("impulse_ms must be between 0 and 100")
                result[field] = numeric
        elif field == "level_db":
            if value in (None, ""):
                result[field] = None
            else:
                numeric = float(value)
                if not -150.0 <= numeric <= 30.0:
                    raise ValueError("level_db must be between -150 and 30")
                result[field] = numeric
        elif field == "polarity":
            option = str(value)
            if option not in MEASUREMENT_POLARITY:
                raise ValueError("Invalid measurement polarity")
            result[field] = option
        elif field == "notes":
            result[field] = str(value).strip()[:300]
        else:
            raise ValueError(f"Unsupported measurement field: {field}")
        self.notify()

    def delete_measurement_session(self, session_id: str) -> None:
        before = len(self.measurement_sessions)
        self.measurement_sessions = [item for item in self.measurement_sessions if item.get("id") != session_id]
        if len(self.measurement_sessions) == before:
            raise ValueError("Measurement session was not found")
        if self.active_measurement_session_id == session_id:
            self.active_measurement_session_id = str(self.measurement_sessions[-1].get("id")) if self.measurement_sessions else None
        self.notify()

    def _measurement_session_snapshot(self, session: dict[str, Any]) -> dict[str, Any]:
        self._normalise_measurement_session(session)
        arrivals = [float(item["impulse_ms"]) for item in session["results"] if item.get("impulse_ms") is not None]
        latest = max(arrivals) if arrivals else None
        results = []
        for index, result in enumerate(session["results"]):
            item = deepcopy(result)
            impulse = item.get("impulse_ms")
            item["relative_delay_ms"] = round(latest - float(impulse), 3) if latest is not None and impulse is not None else None
            item["channel_index"] = index
            results.append(item)
        return {
            "id": str(session.get("id", "")),
            "name": str(session.get("name", "Measurement")),
            "created_at": str(session.get("created_at", "")),
            "position": str(session.get("position", "Driver seat")),
            "notes": str(session.get("notes", "")),
            "completed": sum(bool(item.get("completed")) for item in results),
            "channel_count": self.channel_count,
            "latest_impulse_ms": round(latest, 3) if latest is not None else None,
            "results": results,
        }

    def snapshot(self) -> dict[str, Any]:
        channels: list[dict[str, Any]] = []
        for index, channel in enumerate(self.channels):
            item = deepcopy(channel)
            item["delay_ms"] = round(self.delay_for(index), 3)
            item["recommended_delay_ms"] = round(self.recommended_delay_for(index), 3)
            item["path_delta_cm"] = round(self.path_delta_for(index), 1)
            channels.append(item)
        reference = self.channel(self.reference_index)
        sub_channels = [item for item in self.channels if item.get("role") == "Subwoofer"]
        sessions = [self._measurement_session_snapshot(item) for item in reversed(self.measurement_sessions)]
        return {
            "entry_id": self.entry_id,
            "preset": self.preset,
            "channel_count": self.channel_count,
            "channels": channels,
            "reference": {
                "index": self.reference_index, "output": str(reference["output"]),
                "channel_id": str(reference["id"]), "distance_cm": round(self.reference_distance_cm, 1),
            },
            "progress": {
                "measured": sum(float(item.get("distance_cm", 0)) > 0 for item in self.channels),
                "polarity_verified": sum(bool(item.get("polarity_verified")) for item in self.channels),
                "alignment_verified": sum(bool(item.get("alignment_verified")) for item in self.channels),
                "subwoofers": len(sub_channels),
                "subwoofers_verified": sum(bool(item.get("alignment_verified")) for item in sub_channels),
            },
            "snapshots": [{
                "id": str(item.get("id", "")), "name": str(item.get("name", "Tuning")),
                "created_at": str(item.get("created_at", "")), "preset": str(item.get("preset", "")),
            } for item in reversed(self.snapshots)],
            "measurement_sessions": sessions,
            "active_measurement_session_id": self.active_measurement_session_id,
        }

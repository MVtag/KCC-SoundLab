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
MAX_EQ_BANDS = 31

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
EQ_FREQUENCIES = (
    20.0, 25.0, 31.5, 40.0, 50.0, 63.0, 80.0, 100.0, 125.0, 160.0,
    200.0, 250.0, 315.0, 400.0, 500.0, 630.0, 800.0, 1000.0, 1250.0,
    1600.0, 2000.0, 2500.0, 3150.0, 4000.0, 5000.0, 6300.0, 8000.0,
    10000.0, 12500.0, 16000.0, 20000.0,
)
TARGET_CURVE_PRESETS: dict[str, tuple[float, ...]] = {
    "Flat": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    "KCC SQ Draft": (4.0, 4.0, 2.0, 0.0, -1.0, -2.0),
    "Warm": (6.0, 5.0, 2.5, 0.0, -1.5, -2.5),
}
TARGET_CURVE_FREQUENCIES = (20.0, 60.0, 200.0, 1000.0, 5000.0, 20000.0)
TARGET_CURVE_OPTIONS = (*TARGET_CURVE_PRESETS.keys(), "Custom")

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


def _default_eq_bands() -> list[dict[str, Any]]:
    return [
        {
            "enabled": False,
            "frequency_hz": frequency,
            "gain_db": 0.0,
            "q": 1.0,
        }
        for frequency in EQ_FREQUENCIES
    ]


def _default_target_curve(preset: str = "Flat") -> dict[str, Any]:
    gains = TARGET_CURVE_PRESETS.get(preset, TARGET_CURVE_PRESETS["Flat"])
    return {
        "preset": preset if preset in TARGET_CURVE_PRESETS else "Flat",
        "points": [
            {"frequency_hz": frequency, "gain_db": gain}
            for frequency, gain in zip(TARGET_CURVE_FREQUENCIES, gains, strict=True)
        ],
    }


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
        "eq_bands": _default_eq_bands(),
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
    """Hold DSP tuning, EQ and measurement data and notify listeners on changes."""

    def __init__(self, hass: HomeAssistant, entry_id: str, channel_count: int) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.channel_count = max(1, min(int(channel_count), MAX_CHANNELS))
        self.channels = [_default_channel(i) for i in range(self.channel_count)]
        self.preset = "Driver SQ"
        self.target_curve: dict[str, Any] = _default_target_curve()
        self.snapshots: list[dict[str, Any]] = []
        self.measurement_sessions: list[dict[str, Any]] = []
        self.active_measurement_session_id: str | None = None
        self._listeners: set[Callable[[], None]] = set()
        self._store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, f"{DOMAIN}.{entry_id}")

    def _normalise_eq_bands(self, channel: dict[str, Any]) -> None:
        saved_bands = channel.get("eq_bands")
        normalised = _default_eq_bands()
        if isinstance(saved_bands, list):
            for index, saved in enumerate(saved_bands[:MAX_EQ_BANDS]):
                if not isinstance(saved, dict):
                    continue
                band = normalised[index]
                enabled = saved.get("enabled")
                if isinstance(enabled, bool):
                    band["enabled"] = enabled
                try:
                    frequency = float(saved.get("frequency_hz", band["frequency_hz"]))
                    if 20.0 <= frequency <= 20000.0:
                        band["frequency_hz"] = frequency
                except (TypeError, ValueError):
                    pass
                try:
                    gain = float(saved.get("gain_db", 0.0))
                    if -12.0 <= gain <= 12.0:
                        band["gain_db"] = gain
                except (TypeError, ValueError):
                    pass
                try:
                    q_value = float(saved.get("q", 1.0))
                    if 0.1 <= q_value <= 20.0:
                        band["q"] = q_value
                except (TypeError, ValueError):
                    pass
        channel["eq_bands"] = normalised

    def _normalise_target_curve(self, saved: Any) -> None:
        if not isinstance(saved, dict):
            self.target_curve = _default_target_curve()
            return
        preset = str(saved.get("preset", "Flat"))
        if preset not in TARGET_CURVE_OPTIONS:
            preset = "Custom"
        default = _default_target_curve("Flat")
        points = saved.get("points")
        if isinstance(points, list):
            for index, point in enumerate(points[:len(TARGET_CURVE_FREQUENCIES)]):
                if not isinstance(point, dict):
                    continue
                try:
                    gain = float(point.get("gain_db", 0.0))
                    if -12.0 <= gain <= 12.0:
                        default["points"][index]["gain_db"] = gain
                except (TypeError, ValueError):
                    pass
        default["preset"] = preset
        self.target_curve = default

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
                self._normalise_eq_bands(channel)
        preset = data.get("preset")
        if isinstance(preset, str) and preset in PRESETS:
            self.preset = preset
        self._normalise_target_curve(data.get("target_curve"))
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
            "target_curve": deepcopy(self.target_curve),
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

    def set_eq_band(self, channel_index: int, band_index: int, field: str, value: Any) -> None:
        if not 0 <= channel_index < self.channel_count:
            raise ValueError("Channel index is out of range")
        if not 0 <= band_index < MAX_EQ_BANDS:
            raise ValueError("EQ band index is out of range")
        channel = self.channel(channel_index)
        self._normalise_eq_bands(channel)
        band = channel["eq_bands"][band_index]
        if field == "enabled":
            if not isinstance(value, bool):
                raise ValueError("enabled must be true or false")
            band[field] = value
        elif field == "frequency_hz":
            numeric = float(value)
            if not 20.0 <= numeric <= 20000.0:
                raise ValueError("frequency_hz must be between 20 and 20000")
            band[field] = numeric
        elif field == "gain_db":
            numeric = float(value)
            if not -12.0 <= numeric <= 12.0:
                raise ValueError("gain_db must be between -12 and 12")
            band[field] = numeric
        elif field == "q":
            numeric = float(value)
            if not 0.1 <= numeric <= 20.0:
                raise ValueError("q must be between 0.1 and 20")
            band[field] = numeric
        else:
            raise ValueError(f"Unsupported EQ field: {field}")
        self.notify()

    def reset_eq(self, channel_index: int) -> None:
        if not 0 <= channel_index < self.channel_count:
            raise ValueError("Channel index is out of range")
        self.channel(channel_index)["eq_bands"] = _default_eq_bands()
        self.notify()

    def copy_eq(self, source_index: int, target_index: int) -> None:
        if not 0 <= source_index < self.channel_count or not 0 <= target_index < self.channel_count:
            raise ValueError("Channel index is out of range")
        if source_index == target_index:
            raise ValueError("Source and target EQ channels must be different")
        source = self.channel(source_index)
        self._normalise_eq_bands(source)
        self.channel(target_index)["eq_bands"] = deepcopy(source["eq_bands"])
        self.notify()

    def set_target_curve_preset(self, preset: str) -> None:
        if preset not in TARGET_CURVE_OPTIONS:
            raise ValueError("Invalid target curve preset")
        if preset == "Custom":
            self.target_curve["preset"] = "Custom"
        else:
            self.target_curve = _default_target_curve(preset)
        self.notify()

    def set_target_curve_point(self, point_index: int, gain_db: Any) -> None:
        if not 0 <= point_index < len(TARGET_CURVE_FREQUENCIES):
            raise ValueError("Target curve point index is out of range")
        numeric = float(gain_db)
        if not -12.0 <= numeric <= 12.0:
            raise ValueError("Target gain must be between -12 and 12")
        self._normalise_target_curve(self.target_curve)
        self.target_curve["points"][point_index]["gain_db"] = numeric
        self.target_curve["preset"] = "Custom"
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
            "target_curve": deepcopy(self.target_curve),
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
                    self._normalise_eq_bands(fresh)
                    self.channels[index] = fresh
        preset = saved.get("preset")
        if isinstance(preset, str) and preset in PRESETS:
            self.preset = preset
        if "target_curve" in saved:
            self._normalise_target_curve(saved.get("target_curve"))
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
            self._normalise_eq_bands(channel)
            item = deepcopy(channel)
            item["delay_ms"] = round(self.delay_for(index), 3)
            item["recommended_delay_ms"] = round(self.recommended_delay_for(index), 3)
            item["path_delta_cm"] = round(self.path_delta_for(index), 1)
            item["eq_active_bands"] = sum(
                bool(band.get("enabled")) and abs(float(band.get("gain_db", 0.0))) > 0.001
                for band in item["eq_bands"]
            )
            channels.append(item)
        reference = self.channel(self.reference_index)
        sub_channels = [item for item in self.channels if item.get("role") == "Subwoofer"]
        sessions = [self._measurement_session_snapshot(item) for item in reversed(self.measurement_sessions)]
        self._normalise_target_curve(self.target_curve)
        return {
            "entry_id": self.entry_id,
            "preset": self.preset,
            "channel_count": self.channel_count,
            "channels": channels,
            "target_curve": deepcopy(self.target_curve),
            "eq": {
                "bands_per_channel": MAX_EQ_BANDS,
                "target_curve_options": list(TARGET_CURVE_OPTIONS),
            },
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

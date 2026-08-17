"""KCC SoundLab integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CHANNEL_COUNT,
    CONF_DSP_MODEL,
    CONF_VEHICLE,
    DOMAIN,
    PLATFORMS,
)
from .model import KCCDSPState

PANEL_URL = "kcc-soundlab"
PANEL_ELEMENT = "kcc-soundlab-panel"
STATIC_URL = "/kcc_soundlab_static"
FRONTEND_REGISTERED = "frontend_registered"


async def _async_register_frontend(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register the KCC SoundLab sidebar panel and bundled frontend."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(FRONTEND_REGISTERED):
        return

    frontend_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(frontend_dir), False)]
    )

    if not frontend.async_panel_exists(hass, PANEL_URL):
        await async_register_panel(
            hass,
            frontend_url_path=PANEL_URL,
            webcomponent_name=PANEL_ELEMENT,
            sidebar_title="KCC SoundLab",
            sidebar_icon="mdi:tune-vertical",
            module_url=f"{STATIC_URL}/kcc-soundlab-panel.js",
            config={
                "entry_id": entry.entry_id,
                "dsp_model": entry.data[CONF_DSP_MODEL],
                "vehicle": entry.data[CONF_VEHICLE],
                "channel_count": int(entry.data[CONF_CHANNEL_COUNT]),
                "direct_control": False,
            },
            handle_safe_area=True,
        )

    domain_data[FRONTEND_REGISTERED] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up KCC SoundLab from a config entry."""
    state = KCCDSPState(hass, entry.entry_id, int(entry.data[CONF_CHANNEL_COUNT]))
    await state.async_load()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = state
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_register_frontend(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        domain_data = hass.data[DOMAIN]
        domain_data.pop(entry.entry_id, None)
        remaining_entries = [
            key
            for key, value in domain_data.items()
            if key != FRONTEND_REGISTERED and isinstance(value, KCCDSPState)
        ]
        if not remaining_entries and frontend.async_panel_exists(hass, PANEL_URL):
            frontend.async_remove_panel(hass, PANEL_URL)
            domain_data.pop(FRONTEND_REGISTERED, None)
    return unloaded

"""KCC SoundLab integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_CHANNEL_COUNT,
    CONF_DSP_MODEL,
    CONF_VEHICLE,
    DOMAIN,
    PLATFORMS,
    VERSION,
)
from .house_curve_api import FlexibleKCCDSPState, async_setup_house_curve_api
from .model import KCCDSPState
from .sub_null_api import async_setup_sub_null_api
from .websocket_api import async_setup_websocket_api

PANEL_URL = "kcc-soundlab"
PANEL_ELEMENT = "kcc-soundlab-panel"
STATIC_URL = "/kcc_soundlab_static"
STATIC_VERSION_URL = f"{STATIC_URL}_{VERSION.replace('.', '_')}"
STATIC_REGISTERED = "static_registered"
WEBSOCKET_REGISTERED = "websocket_registered"


async def _async_cleanup_legacy_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Remove v0.1 per-channel entities from the entity registry."""
    registry = er.async_get(hass)
    keep_unique_ids = {
        f"{entry.entry_id}_status",
        f"{entry.entry_id}_reference_channel",
    }
    for registry_entry in list(
        er.async_entries_for_config_entry(registry, entry.entry_id)
    ):
        if registry_entry.platform != DOMAIN:
            continue
        if registry_entry.unique_id in keep_unique_ids:
            continue
        registry.async_remove(registry_entry.entity_id)


async def _async_register_frontend(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register the KCC SoundLab sidebar panel and bundled frontend."""
    domain_data = hass.data.setdefault(DOMAIN, {})

    if not domain_data.get(STATIC_REGISTERED):
        frontend_dir = Path(__file__).parent / "frontend"
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(STATIC_URL, str(frontend_dir), False),
                StaticPathConfig(STATIC_VERSION_URL, str(frontend_dir), False),
            ]
        )
        domain_data[STATIC_REGISTERED] = True

    if frontend.async_panel_exists(hass, PANEL_URL):
        return

    await async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title="KCC SoundLab",
        sidebar_icon="mdi:tune-vertical",
        module_url=f"{STATIC_VERSION_URL}/kcc-soundlab-panel.js?v={VERSION}",
        config={
            "entry_id": entry.entry_id,
            "dsp_model": entry.data[CONF_DSP_MODEL],
            "vehicle": entry.data[CONF_VEHICLE],
            "channel_count": int(entry.data[CONF_CHANNEL_COUNT]),
            "direct_control": False,
            "version": VERSION,
        },
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up KCC SoundLab from a config entry."""
    state = FlexibleKCCDSPState(
        hass, entry.entry_id, int(entry.data[CONF_CHANNEL_COUNT])
    )
    await state.async_load()

    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data[entry.entry_id] = state

    if not domain_data.get(WEBSOCKET_REGISTERED):
        async_setup_websocket_api(hass)
        async_setup_sub_null_api(hass)
        async_setup_house_curve_api(hass)
        domain_data[WEBSOCKET_REGISTERED] = True

    await _async_cleanup_legacy_entities(hass, entry)
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
            value for value in domain_data.values() if isinstance(value, KCCDSPState)
        ]
        if not remaining_entries and frontend.async_panel_exists(hass, PANEL_URL):
            frontend.async_remove_panel(hass, PANEL_URL)
    return unloaded

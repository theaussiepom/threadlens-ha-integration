"""ThreadLens Home Assistant integration setup."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from .const import CONF_PANEL_ENABLED, DEFAULT_PANEL_ENABLED, DOMAIN
from .coordinator import build_coordinator
from .panel import async_register_panel, async_unregister_panel, async_update_panel_core_url
from .repairs import async_update_connection_repairs
from .report_view import async_register_http_views
from .websocket import async_register_websocket_commands

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ThreadLens from a config entry."""
    coordinator = await build_coordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def _handle_coordinator_update() -> None:
        connected = bool(coordinator.data and coordinator.data.connected)
        async_update_connection_repairs(hass, entry, connected=connected)

    entry.async_on_unload(coordinator.async_add_listener(_handle_coordinator_update))
    _handle_coordinator_update()

    async_register_websocket_commands(hass)
    async_register_http_views(hass)

    if entry.data.get(CONF_PANEL_ENABLED, DEFAULT_PANEL_ENABLED):
        await async_register_panel(hass, entry.entry_id, coordinator.api.base_url)
    else:
        async_update_panel_core_url(hass, coordinator.api.base_url)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.data.get(CONF_PANEL_ENABLED, DEFAULT_PANEL_ENABLED):
        await async_unregister_panel(hass, entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

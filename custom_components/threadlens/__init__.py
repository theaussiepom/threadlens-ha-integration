"""ThreadLens Home Assistant integration setup."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .coordinator import ThreadLensCoordinator, build_coordinator
from .frontend import async_register_frontend, async_unregister_frontend
from .repairs import async_update_connection_repairs
from .report_view import async_register_http_views
from .websocket import async_register_websocket_commands

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON]


def _has_other_entries(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return any(
        isinstance(value, ThreadLensCoordinator)
        for key, value in hass.data.get(DOMAIN, {}).items()
        if key != entry.entry_id
    )


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
    await async_register_frontend(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not _has_other_entries(hass, entry):
            async_unregister_frontend(hass)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

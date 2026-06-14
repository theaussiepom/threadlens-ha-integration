"""Diagnostics support for ThreadLens."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .api import redact_url_for_diagnostics
from .const import CONF_URL, DOMAIN
from .coordinator import ThreadLensCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: ThreadLensCoordinator | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    data = coordinator.data if coordinator else None
    return {
        "config": {
            CONF_URL: redact_url_for_diagnostics(entry.data.get(CONF_URL, "")),
        },
        "connected": data.connected if data else False,
        "version": data.version if data else None,
        "health_overall": (data.health.get("overall") if data and data.health else None),
        "status_summary": {
            "mode": data.status.get("mode") if data and data.status else None,
            "reports": data.status.get("reports") if data and data.status else None,
            "collectors": data.status.get("collectors") if data and data.status else None,
        },
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: dr.DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    return await async_get_config_entry_diagnostics(hass, entry)

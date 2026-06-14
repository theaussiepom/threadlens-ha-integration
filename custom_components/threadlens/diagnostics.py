"""Diagnostics support for ThreadLens."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .api import redact_url_for_diagnostics
from .const import CONF_EMBED_DASHBOARD, CONF_URL, DOMAIN
from .coordinator import ThreadLensCoordinator
from .panel_data import summarize_matter_read_probes
from .panel_embed import embed_dashboard_enabled


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: ThreadLensCoordinator | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    data = coordinator.data if coordinator else None
    matter_nodes = [
        node for node in ((data.matter_nodes if data else None) or []) if isinstance(node, dict)
    ]
    read_probe_summary = summarize_matter_read_probes(matter_nodes)
    matter_collector = None
    if data and isinstance(data.status, dict):
        collectors = data.status.get("collectors")
        if isinstance(collectors, dict):
            matter_collector = collectors.get("matter")
    return {
        "config": {
            CONF_URL: redact_url_for_diagnostics(entry.data.get(CONF_URL, "")),
            CONF_EMBED_DASHBOARD: embed_dashboard_enabled(entry.options),
        },
        "connected": data.connected if data else False,
        "version": data.version if data else None,
        "last_update": data.last_update if data else None,
        "health_overall": (data.health.get("overall") if data and data.health else None),
        "status_summary": {
            "mode": data.status.get("mode") if data and data.status else None,
            "reports": data.status.get("reports") if data and data.status else None,
            "collectors": data.status.get("collectors") if data and data.status else None,
        },
        "matter_read_probe_diagnostics_available": read_probe_summary[
            "read_probe_diagnostics_available"
        ],
        "matter_read_probe_issues": read_probe_summary["matter_read_probe_issues"],
        "matter_read_probe_available_but_failed": read_probe_summary[
            "matter_read_probe_available_but_failed"
        ],
        "read_probe_nodes_with_diagnostics": read_probe_summary[
            "read_probe_nodes_with_diagnostics"
        ],
        "ping_diagnostics_available": read_probe_summary["ping_diagnostics_available"],
        "ping_probe_failures": read_probe_summary["ping_probe_failures"],
        "matter_collector": matter_collector,
        "read_probe_issue_nodes": read_probe_summary["read_probe_issue_nodes"],
    }


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: dr.DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    return await async_get_config_entry_diagnostics(hass, entry)

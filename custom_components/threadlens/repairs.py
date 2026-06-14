"""Repair issues for ThreadLens integration health."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import CONF_URL, DOMAIN

ISSUE_API_DISCONNECTED = "api_disconnected"


@callback
def async_update_connection_repairs(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    connected: bool,
) -> None:
    """Create or clear the Core API connectivity repair issue."""
    issue_id = f"{ISSUE_API_DISCONNECTED}_{entry.entry_id}"
    if connected:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return

    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_API_DISCONNECTED,
        translation_placeholders={
            "url": entry.data.get(CONF_URL, ""),
        },
    )

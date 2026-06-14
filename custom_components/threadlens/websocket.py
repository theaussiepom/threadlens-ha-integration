"""Websocket API for the ThreadLens dashboard panel.

The panel never talks to ThreadLens Core directly; it asks Home Assistant for
the already-aggregated dashboard payload over the authenticated websocket
connection. This avoids CORS, mixed-content, and local-network auth issues.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DATA_WEBSOCKET_REGISTERED, DOMAIN, WS_TYPE_DASHBOARD
from .coordinator import ThreadLensCoordinator
from .dashboard import build_disconnected_payload

_LOGGER = logging.getLogger(__name__)


@callback
def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register ThreadLens websocket commands once per Home Assistant run."""
    if hass.data.get(DOMAIN, {}).get(DATA_WEBSOCKET_REGISTERED):
        return
    websocket_api.async_register_command(hass, websocket_dashboard)
    hass.data.setdefault(DOMAIN, {})[DATA_WEBSOCKET_REGISTERED] = True


def _first_coordinator(hass: HomeAssistant) -> ThreadLensCoordinator | None:
    domain_data = hass.data.get(DOMAIN, {})
    for value in domain_data.values():
        if isinstance(value, ThreadLensCoordinator):
            return value
    return None


@websocket_api.websocket_command({vol.Required("type"): WS_TYPE_DASHBOARD})
@websocket_api.async_response
async def websocket_dashboard(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the aggregated ThreadLens dashboard payload."""
    coordinator = _first_coordinator(hass)
    if coordinator is None:
        connection.send_error(
            msg["id"],
            "not_configured",
            "ThreadLens is not configured",
        )
        return
    try:
        payload = coordinator.dashboard_payload()
    except Exception:
        _LOGGER.exception("ThreadLens dashboard payload failed")
        payload = build_disconnected_payload(
            error="ThreadLens dashboard failed to build. Check Home Assistant logs.",
        )
    connection.send_result(msg["id"], payload)

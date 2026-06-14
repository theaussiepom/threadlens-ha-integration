"""Native companion panel for ThreadLens."""

from __future__ import annotations

import logging
import os

import voluptuous as vol
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .const import (
    DATA_FRONTEND_REGISTERED,
    DOMAIN,
    PANEL_FILENAME,
    PANEL_ICON,
    PANEL_STATE_KEY,
    PANEL_STATIC_URL,
    PANEL_TITLE,
    PANEL_URL_PATH,
    PANEL_WEBCOMPONENT,
    WS_TYPE_PANEL_SUMMARY,
)
from .coordinator import ThreadLensCoordinator
from .panel_data import build_panel_summary

_LOGGER = logging.getLogger(__name__)

PANEL_DIR = os.path.join(os.path.dirname(__file__), "panel")


@callback
def _find_coordinator(hass: HomeAssistant) -> tuple[ThreadLensCoordinator | None, str]:
    """Return the first available coordinator and its configured Core URL."""
    for value in (hass.data.get(DOMAIN) or {}).values():
        if isinstance(value, ThreadLensCoordinator):
            return value, value.api.base_url
    return None, ""


@callback
@websocket_api.websocket_command({vol.Required("type"): WS_TYPE_PANEL_SUMMARY})
def _ws_panel_summary(hass: HomeAssistant, connection, msg: dict) -> None:
    """Return a redacted panel summary to the frontend over the HA websocket."""
    coordinator, core_url = _find_coordinator(hass)
    if coordinator is None:
        connection.send_result(
            msg["id"], build_panel_summary(None, core_url=core_url, connected=False)
        )
        return

    connected = bool(coordinator.last_update_success and coordinator.data is not None)
    last_exception = None
    if not connected and coordinator.last_exception is not None:
        last_exception = str(coordinator.last_exception)
    summary = build_panel_summary(
        coordinator.data if connected else None,
        core_url=core_url,
        connected=connected,
        last_exception=last_exception,
    )
    connection.send_result(msg["id"], summary)


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register the websocket command and static panel asset once per HA run."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_FRONTEND_REGISTERED):
        return

    websocket_api.async_register_command(hass, _ws_panel_summary)
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                PANEL_STATIC_URL,
                os.path.join(PANEL_DIR, PANEL_FILENAME),
                cache_headers=False,
            )
        ]
    )
    domain_data[DATA_FRONTEND_REGISTERED] = True


async def async_register_panel(hass: HomeAssistant, entry_id: str, core_url: str) -> None:
    """Register the native companion panel in the Home Assistant sidebar."""
    await async_setup_frontend(hass)
    state = hass.data.setdefault(DOMAIN, {}).setdefault(PANEL_STATE_KEY, {})

    panels = hass.data.get(frontend.DATA_PANELS, {})
    existing = panels.get(PANEL_URL_PATH)
    if existing is not None:
        config = existing.get("config") or {}
        custom_meta = config.get("_panel_custom") or {}
        if custom_meta.get("embed_iframe") or not config.get("core_url"):
            frontend.async_remove_panel(hass, PANEL_URL_PATH)
            state["panel_registered"] = False
        else:
            async_update_panel_core_url(hass, core_url)
            state["panel_registered"] = True
            return

    if state.get("panel_registered"):
        async_update_panel_core_url(hass, core_url)
        return

    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_WEBCOMPONENT,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        module_url=PANEL_STATIC_URL,
        embed_iframe=False,
        require_admin=False,
        config={"core_url": core_url},
    )
    state["panel_registered"] = True
    _LOGGER.debug("Registered ThreadLens companion panel (core_url=%s)", core_url)


@callback
def async_update_panel_core_url(hass: HomeAssistant, core_url: str) -> None:
    """Update the companion panel launcher URL after Configure / options changes."""
    panels = hass.data.get(frontend.DATA_PANELS, {})
    panel = panels.get(PANEL_URL_PATH)
    if panel is not None:
        panel["config"] = {**(panel.get("config") or {}), "core_url": core_url}


async def async_unregister_panel(hass: HomeAssistant, entry_id: str) -> None:
    """Remove the sidebar panel when the config entry unloads."""
    state = hass.data.get(DOMAIN, {}).get(PANEL_STATE_KEY, {})
    if not state.get("panel_registered"):
        return
    if PANEL_URL_PATH in hass.data.get(frontend.DATA_PANELS, {}):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
    state["panel_registered"] = False

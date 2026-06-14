"""Frontend custom panel registration for ThreadLens."""

from __future__ import annotations

import logging
import os

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import (
    DATA_FRONTEND_REGISTERED,
    DOMAIN,
    PANEL_FILENAME,
    PANEL_ICON,
    PANEL_STATIC_URL,
    PANEL_TITLE,
    PANEL_URL_PATH,
    PANEL_WEBCOMPONENT,
)

_LOGGER = logging.getLogger(__name__)

PANEL_DIR = os.path.join(os.path.dirname(__file__), "panel")


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the bundled panel JS and register the sidebar panel once."""
    if hass.data.get(DOMAIN, {}).get(DATA_FRONTEND_REGISTERED):
        return

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                PANEL_STATIC_URL,
                os.path.join(PANEL_DIR, PANEL_FILENAME),
                cache_headers=False,
            )
        ]
    )

    await panel_custom.async_register_panel(
        hass,
        webcomponent_name=PANEL_WEBCOMPONENT,
        frontend_url_path=PANEL_URL_PATH,
        module_url=PANEL_STATIC_URL,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        require_admin=False,
        config={},
    )

    hass.data.setdefault(DOMAIN, {})[DATA_FRONTEND_REGISTERED] = True
    _LOGGER.debug("Registered ThreadLens dashboard panel at /%s", PANEL_URL_PATH)


def async_unregister_frontend(hass: HomeAssistant) -> None:
    """Remove the ThreadLens sidebar panel."""
    if not hass.data.get(DOMAIN, {}).get(DATA_FRONTEND_REGISTERED):
        return
    frontend.async_remove_panel(hass, PANEL_URL_PATH)
    hass.data[DOMAIN][DATA_FRONTEND_REGISTERED] = False

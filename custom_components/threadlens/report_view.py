"""Authenticated Home Assistant HTTP view that proxies the ThreadLens report YAML.

The panel opens this HA URL in a new tab instead of hitting ThreadLens Core
directly. Home Assistant authentication applies, the fetch happens server-side
using the configured ThreadLens URL, and the YAML is returned as text so the
browser displays it rather than downloading a binary blob.
"""

from __future__ import annotations

import logging

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .api import ThreadLensApiError, ThreadLensCannotConnect
from .const import DATA_HTTP_REGISTERED, DOMAIN, REPORT_PROXY_URL
from .coordinator import ThreadLensCoordinator

_LOGGER = logging.getLogger(__name__)


def async_register_http_views(hass: HomeAssistant) -> None:
    """Register the report YAML proxy view once per Home Assistant run."""
    if hass.data.get(DOMAIN, {}).get(DATA_HTTP_REGISTERED):
        return
    hass.http.register_view(ThreadLensReportView(hass))
    hass.data.setdefault(DOMAIN, {})[DATA_HTTP_REGISTERED] = True


def _first_coordinator(hass: HomeAssistant) -> ThreadLensCoordinator | None:
    for value in hass.data.get(DOMAIN, {}).values():
        if isinstance(value, ThreadLensCoordinator):
            return value
    return None


class ThreadLensReportView(HomeAssistantView):
    """Serve the ThreadLens report YAML through an authenticated HA endpoint."""

    url = REPORT_PROXY_URL
    name = "api:threadlens:report"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        coordinator = _first_coordinator(self.hass)
        if coordinator is None:
            return web.Response(status=503, text="ThreadLens is not configured")
        try:
            yaml_text = await coordinator.api.get_report_yaml_text()
        except ThreadLensCannotConnect:
            return web.Response(status=502, text="Cannot reach the ThreadLens API")
        except ThreadLensApiError as exc:
            _LOGGER.debug("ThreadLens report proxy error: %s", exc)
            return web.Response(status=502, text="ThreadLens report unavailable")
        return web.Response(
            text=yaml_text,
            content_type="text/plain",
            charset="utf-8",
        )

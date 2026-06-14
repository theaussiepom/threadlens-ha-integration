"""Panel iframe embedding safety for the ThreadLens sidebar."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from homeassistant.core import HomeAssistant

from .const import CONF_EMBED_DASHBOARD

_MIXED_CONTENT_MESSAGE = (
    "The full ThreadLens dashboard opens separately because browsers block "
    "HTTP dashboards inside HTTPS Home Assistant pages."
)


def homeassistant_browser_url(hass: HomeAssistant) -> str:
    """Return the URL Home Assistant users typically open in the browser."""
    if hass.config.external_url:
        return hass.config.external_url
    if hass.config.internal_url:
        return hass.config.internal_url
    return ""


def evaluate_iframe_embed_safety(
    homeassistant_url: str,
    core_url: str,
) -> tuple[bool, str | None]:
    """Return whether iframe embedding is likely safe and an optional blocked reason."""
    if not core_url:
        return False, "ThreadLens Core URL is not configured."

    ha_scheme = urlparse(homeassistant_url).scheme.lower() if homeassistant_url else ""
    core_scheme = urlparse(core_url).scheme.lower()

    if core_scheme not in {"http", "https"}:
        return False, "ThreadLens Core URL must use HTTP or HTTPS for embedding."

    if ha_scheme == "https" and core_scheme == "http":
        return False, _MIXED_CONTENT_MESSAGE

    if not ha_scheme:
        # Unknown HA scheme: prefer native panel rather than a likely broken iframe.
        return False, (
            "Embedded dashboard is unavailable because Home Assistant URL scheme "
            "could not be determined. Open the full dashboard in a new tab."
        )

    return True, None


def build_panel_access(
    hass: HomeAssistant,
    *,
    core_url: str,
    embed_dashboard: bool,
) -> dict[str, Any]:
    """Build panel access metadata for the sidebar companion view."""
    ha_url = homeassistant_browser_url(hass)
    embed_allowed, blocked_reason = evaluate_iframe_embed_safety(ha_url, core_url)
    show_iframe = bool(embed_dashboard and embed_allowed and core_url)

    return {
        "core_url": core_url or None,
        "embed_dashboard": embed_dashboard,
        "iframe_embed_allowed": embed_allowed,
        "iframe_blocked_reason": blocked_reason,
        "show_embedded_dashboard": show_iframe,
        "home_assistant_url": ha_url or None,
    }


def embed_dashboard_enabled(options: dict[str, Any]) -> bool:
    """Return whether the user opted into optional iframe embedding."""
    return bool(options.get(CONF_EMBED_DASHBOARD, False))

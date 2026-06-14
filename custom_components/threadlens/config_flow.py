"""Config flow for ThreadLens."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    ThreadLensApiError,
    ThreadLensCannotConnect,
    ThreadLensInvalidResponse,
    normalize_url,
    validate_threadlens_api,
)
from .const import CONF_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_URL): str})


class CannotConnect(HomeAssistantError):
    """Errors that indicate connection failure."""


class InvalidResponse(HomeAssistantError):
    """Errors that indicate an invalid response."""


async def validate_input(hass: HomeAssistant, url: str) -> dict[str, str]:
    """Validate the user input and return version info."""
    session = async_get_clientsession(hass)
    normalized = normalize_url(url)
    try:
        version = await validate_threadlens_api(session, normalized)
    except ThreadLensCannotConnect as exc:
        raise CannotConnect from exc
    except ThreadLensInvalidResponse as exc:
        raise InvalidResponse from exc
    except ThreadLensApiError as exc:
        raise HomeAssistantError from exc
    return {"title": f"ThreadLens {version.get('version', '')}".strip(), "version": version}


class ThreadLensConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ThreadLens."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = normalize_url(user_input[CONF_URL])
            await self.async_set_unique_id(url)
            self._abort_if_unique_id_configured()
            try:
                info = await validate_input(self.hass, url)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            except HomeAssistantError:
                _LOGGER.exception("Unexpected error validating ThreadLens API")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=info["title"],
                    data={CONF_URL: url},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

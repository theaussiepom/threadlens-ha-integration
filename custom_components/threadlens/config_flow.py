"""Config flow for ThreadLens."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    ThreadLensApiError,
    ThreadLensCannotConnect,
    ThreadLensInvalidResponse,
    validate_threadlens_api,
)
from .const import (
    CONF_PANEL_ENABLED,
    CONF_URL,
    CONF_VERIFY_SSL,
    DEFAULT_PANEL_ENABLED,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
        vol.Optional(CONF_PANEL_ENABLED, default=DEFAULT_PANEL_ENABLED): bool,
    }
)


class CannotConnect(HomeAssistantError):
    """Errors that indicate connection failure."""


class InvalidResponse(HomeAssistantError):
    """Errors that indicate an invalid response."""


def _normalize_core_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("invalid_url")
    return f"{parsed.scheme}://{parsed.netloc}"


async def validate_input(hass: HomeAssistant, url: str, *, verify_ssl: bool) -> dict[str, str]:
    """Validate the user input and return version info."""
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    try:
        version = await validate_threadlens_api(session, url)
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

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ThreadLensOptionsFlowHandler:
        """Return the options flow handler."""
        return ThreadLensOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                core_url = _normalize_core_url(user_input[CONF_URL])
            except ValueError:
                return self.async_show_form(
                    step_id="user",
                    data_schema=STEP_USER_SCHEMA,
                    errors={"base": "invalid_url"},
                )

            await self.async_set_unique_id(core_url)
            self._abort_if_unique_id_configured()

            verify_ssl = user_input[CONF_VERIFY_SSL]
            try:
                await validate_input(self.hass, core_url, verify_ssl=verify_ssl)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            except HomeAssistantError:
                _LOGGER.exception("Unexpected error validating ThreadLens API")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="ThreadLens",
                    data={
                        CONF_URL: core_url,
                        CONF_VERIFY_SSL: verify_ssl,
                        CONF_PANEL_ENABLED: user_input[CONF_PANEL_ENABLED],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )


class ThreadLensOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle ThreadLens integration options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                core_url = _normalize_core_url(user_input[CONF_URL])
            except ValueError:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._schema(),
                    errors={"base": "invalid_url"},
                )

            verify_ssl = user_input[CONF_VERIFY_SSL]
            try:
                await validate_input(self.hass, core_url, verify_ssl=verify_ssl)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidResponse:
                errors["base"] = "invalid_response"
            except HomeAssistantError:
                _LOGGER.exception("Unexpected error validating ThreadLens API")
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    unique_id=core_url,
                    data={
                        **self._config_entry.data,
                        CONF_URL: core_url,
                        CONF_VERIFY_SSL: verify_ssl,
                        CONF_PANEL_ENABLED: user_input[CONF_PANEL_ENABLED],
                    },
                )
                await self.hass.config_entries.async_reload(self._config_entry.entry_id)
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=self._schema(),
            errors=errors,
        )

    def _schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    CONF_URL,
                    default=self._config_entry.data.get(CONF_URL, ""),
                ): str,
                vol.Optional(
                    CONF_VERIFY_SSL,
                    default=self._config_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                ): bool,
                vol.Optional(
                    CONF_PANEL_ENABLED,
                    default=self._config_entry.data.get(CONF_PANEL_ENABLED, DEFAULT_PANEL_ENABLED),
                ): bool,
            }
        )

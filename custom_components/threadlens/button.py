"""Button platform for ThreadLens."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ThreadLensApiError
from .const import DOMAIN
from .coordinator import ThreadLensCoordinator
from .entity import ThreadLensEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ThreadLensCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ThreadLensRefreshButton(coordinator, entry.entry_id, "refresh"),
            ThreadLensGenerateReportButton(coordinator, entry.entry_id, "generate_report"),
        ]
    )


class ThreadLensRefreshButton(ThreadLensEntity, ButtonEntity):
    _attr_translation_key = "refresh"

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()


class ThreadLensGenerateReportButton(ThreadLensEntity, ButtonEntity):
    _attr_translation_key = "generate_report"

    async def async_press(self) -> None:
        try:
            await self.coordinator.api.get_report_yaml()
        except ThreadLensApiError:
            return
        await self.coordinator.async_request_refresh()

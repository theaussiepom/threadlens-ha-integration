"""Sensor platform for ThreadLens."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
            ThreadLensApiHealthSensor(coordinator, entry.entry_id, "api_health"),
            ThreadLensEnvironmentHealthSensor(coordinator, entry.entry_id, "environment_health"),
            ThreadLensLastReportGeneratedSensor(
                coordinator, entry.entry_id, "last_report_generated_at"
            ),
            ThreadLensEventCountSensor(coordinator, entry.entry_id, "event_count_24h"),
            ThreadLensWarningCountSensor(coordinator, entry.entry_id, "warning_count_24h"),
        ]
    )


class ThreadLensApiHealthSensor(ThreadLensEntity, SensorEntity):
    _attr_translation_key = "api_health"

    @property
    def native_value(self) -> str | None:
        summary = self._health_summary()
        if summary:
            return str(summary["overall_health"])
        return self._health_value("overall", "state")


class ThreadLensEnvironmentHealthSensor(ThreadLensEntity, SensorEntity):
    _attr_translation_key = "environment_health"

    @property
    def native_value(self) -> str | None:
        summary = self._health_summary()
        if summary:
            return str(summary["environment_health"])
        return self._health_value("environment", "state")


class ThreadLensLastReportGeneratedSensor(ThreadLensEntity, SensorEntity):
    _attr_translation_key = "last_report_generated_at"

    @property
    def native_value(self) -> str | None:
        value = self._status_value("reports", "last_generated_at")
        return str(value) if value is not None else None


class ThreadLensEventCountSensor(ThreadLensEntity, SensorEntity):
    _attr_translation_key = "event_count_24h"

    @property
    def native_value(self) -> int | None:
        if not self.coordinator.data or not self.coordinator.data.health:
            return None
        summary_obj = self.coordinator.data.health.get("summary")
        if not isinstance(summary_obj, dict):
            return None
        events = summary_obj.get("events_24h")
        return int(events) if events is not None else None


class ThreadLensWarningCountSensor(ThreadLensEntity, SensorEntity):
    _attr_translation_key = "warning_count_24h"

    @property
    def native_value(self) -> int | None:
        if not self.coordinator.data or not self.coordinator.data.health:
            return None
        summary_obj = self.coordinator.data.health.get("summary")
        if not isinstance(summary_obj, dict):
            return None
        warnings = summary_obj.get("warnings_24h")
        return int(warnings) if warnings is not None else None

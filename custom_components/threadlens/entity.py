"""Shared entity helpers for ThreadLens."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import build_report_urls
from .const import (
    ATTR_COLLECTORS,
    ATTR_HEALTH_REASONS,
    ATTR_REPORT_URL_JSON,
    ATTR_REPORT_URL_YAML,
    ATTR_SITE,
    ATTR_THREADLENS_VERSION,
    DOMAIN,
)
from .coordinator import ThreadLensCoordinator


def threadlens_device_info(entry_id: str, coordinator: ThreadLensCoordinator) -> DeviceInfo:
    """Return device info for the ThreadLens API connection."""
    version = None
    if coordinator.data and coordinator.data.version:
        version = coordinator.data.version.get("version")
    return DeviceInfo(
        identifiers={(DOMAIN, entry_id)},
        name="ThreadLens API",
        manufacturer="ThreadLens",
        model="ThreadLens Core API",
        sw_version=version,
        configuration_url=coordinator.api.base_url,
    )


class ThreadLensEntity(CoordinatorEntity[ThreadLensCoordinator]):
    """Base ThreadLens coordinator entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ThreadLensCoordinator,
        entry_id: str,
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_unique_id = f"{entry_id}_{unique_suffix}"
        self._attr_device_info = threadlens_device_info(entry_id, coordinator)

    @property
    def available(self) -> bool:
        return bool(self.coordinator.data and self.coordinator.data.connected)

    def _health_value(self, *path: str) -> str | None:
        if not self.coordinator.data or not self.coordinator.data.health:
            return None
        current: object = self.coordinator.data.health
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return str(current) if current is not None else None

    def _status_value(self, *path: str) -> object | None:
        if not self.coordinator.data or not self.coordinator.data.status:
            return None
        current: object = self.coordinator.data.status
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        attrs: dict[str, object] = {}
        if self.coordinator.data and self.coordinator.data.version:
            attrs[ATTR_THREADLENS_VERSION] = self.coordinator.data.version.get("version")
        report_urls = build_report_urls(self.coordinator.api.base_url)
        attrs[ATTR_REPORT_URL_YAML] = report_urls["yaml"]
        attrs[ATTR_REPORT_URL_JSON] = report_urls["json"]
        if self.coordinator.data and self.coordinator.data.health:
            overall = self.coordinator.data.health.get("overall", {})
            if isinstance(overall, dict):
                attrs[ATTR_HEALTH_REASONS] = overall.get("reasons", [])
            attrs[ATTR_SITE] = self.coordinator.data.health.get("site")
        collectors = self._status_value("collectors")
        if isinstance(collectors, dict):
            attrs[ATTR_COLLECTORS] = collectors
        return attrs

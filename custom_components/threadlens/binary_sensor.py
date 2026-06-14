"""Binary sensor platform for ThreadLens."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
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
            ThreadLensApiConnectedBinarySensor(coordinator, entry.entry_id, "api_connected"),
            ThreadLensMqttConnectedBinarySensor(coordinator, entry.entry_id, "mqtt_connected"),
            ThreadLensMdnsObserverBinarySensor(
                coordinator, entry.entry_id, "mdns_observer_running"
            ),
        ]
    )


class ThreadLensApiConnectedBinarySensor(ThreadLensEntity, BinarySensorEntity):
    _attr_translation_key = "api_connected"

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return False
        return self.coordinator.data.connected


class ThreadLensMqttConnectedBinarySensor(ThreadLensEntity, BinarySensorEntity):
    _attr_translation_key = "mqtt_connected"

    @property
    def is_on(self) -> bool | None:
        mqtt = self._status_value("collectors", "mqtt")
        if not isinstance(mqtt, dict):
            return None
        return bool(mqtt.get("connected"))


class ThreadLensMdnsObserverBinarySensor(ThreadLensEntity, BinarySensorEntity):
    _attr_translation_key = "mdns_observer_running"

    @property
    def is_on(self) -> bool | None:
        mdns = self._status_value("collectors", "mdns")
        if not isinstance(mdns, dict):
            return None
        return bool(mdns.get("observer_running"))

"""Schedule Home Assistant Matter name pushes to ThreadLens Core."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN
from .coordinator import ThreadLensCoordinator
from .ha_matter_names import parse_matter_node_id, parse_node_id_from_matter_unique_id
from .ha_matter_push import async_push_matter_names_to_core

_LOGGER = logging.getLogger(__name__)
MATTER_DOMAIN = "matter"
_DEBOUNCE_SECONDS = 2.0


def _registry_change_affects_matter(
    event: Event,
    *,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> bool:
    if event.event_type == dr.EVENT_DEVICE_REGISTRY_UPDATED:
        data = event.data
        if data.get("action") != "update":
            return False
        device = device_registry.async_get(data.get("device_id"))
        if device is None:
            return False
        return parse_matter_node_id(getattr(device, "identifiers", None) or ()) is not None

    if event.event_type == er.EVENT_ENTITY_REGISTRY_UPDATED:
        data = event.data
        if data.get("action") != "update":
            return False
        entity = entity_registry.async_get(data.get("entity_id"))
        if entity is None:
            return False
        if getattr(entity, "platform", None) == MATTER_DOMAIN:
            return True
        return parse_node_id_from_matter_unique_id(getattr(entity, "unique_id", None)) is not None

    return False


@callback
def _schedule_matter_name_push(hass: HomeAssistant, entry_id: str) -> None:
    domain_data = hass.data.get(DOMAIN) or {}
    pending = domain_data.setdefault("matter_name_push_handles", {})
    if handle := pending.pop(entry_id, None):
        handle()

    @callback
    def _push(_now) -> None:
        pending.pop(entry_id, None)
        hass.async_create_task(_push_matter_names(hass, entry_id))

    pending[entry_id] = async_call_later(hass, _DEBOUNCE_SECONDS, _push)


async def _push_matter_names(hass: HomeAssistant, entry_id: str) -> None:
    coordinator: ThreadLensCoordinator | None = (hass.data.get(DOMAIN) or {}).get(entry_id)
    if coordinator is None or coordinator.data is None or not coordinator.data.connected:
        return
    data = coordinator.data
    await async_push_matter_names_to_core(
        hass,
        coordinator.api,
        matter_servers=data.matter_servers,
        matter_nodes=data.matter_nodes,
    )


async def async_setup_matter_name_sync(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Push HA Matter names on startup and when registry entries change."""
    entry_id = entry.entry_id
    await _push_matter_names(hass, entry_id)

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    @callback
    def _on_registry_update(event: Event) -> None:
        if _registry_change_affects_matter(
            event,
            device_registry=device_registry,
            entity_registry=entity_registry,
        ):
            _schedule_matter_name_push(hass, entry_id)

    entry.async_on_unload(
        device_registry.async_listen(_on_registry_update, dr.EVENT_DEVICE_REGISTRY_UPDATED)
    )
    entry.async_on_unload(
        entity_registry.async_listen(_on_registry_update, er.EVENT_ENTITY_REGISTRY_UPDATED)
    )

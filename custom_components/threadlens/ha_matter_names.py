"""Map ThreadLens Matter node IDs to Home Assistant device/entity names.

ThreadLens reports Matter node IDs and serials from its collectors. Home
Assistant's Matter integration registers devices with identifiers like
``("matter", "deviceid_{fabric}-{node_id_hex}-...")``. This module cross-
references those registries so the dashboard can show familiar blind/cover
names from HA rather than only ThreadLens serials.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

MATTER_DOMAIN = "matter"
_DEVICE_ID_PREFIX = "deviceid_"
_SERIAL_PREFIX = "serial_"

# Domains most likely to represent blinds/shades in Ben's environment.
_PREFERRED_ENTITY_DOMAINS = ("cover", "switch", "light", "binary_sensor")


def parse_matter_node_id(
    identifiers: set[tuple[str, str]] | list[tuple[str, str]] | None,
) -> int | None:
    """Extract a Matter node ID from HA device identifiers."""
    if not identifiers:
        return None
    for domain, ident in identifiers:
        if domain != MATTER_DOMAIN or not ident.startswith(_DEVICE_ID_PREFIX):
            continue
        # deviceid_{fabric_hex}-{node_id_hex}-{postfix}
        body = ident[len(_DEVICE_ID_PREFIX) :]
        parts = body.split("-", 2)
        if len(parts) < 2:
            continue
        try:
            return int(parts[1], 16)
        except ValueError:
            continue
    return None


def parse_matter_serial(
    identifiers: set[tuple[str, str]] | list[tuple[str, str]] | None,
) -> str | None:
    """Extract a Matter serial identifier from HA device identifiers."""
    if not identifiers:
        return None
    for domain, ident in identifiers:
        if domain == MATTER_DOMAIN and ident.startswith(_SERIAL_PREFIX):
            return ident[len(_SERIAL_PREFIX) :]
    return None


def _device_display_name(device: dr.DeviceEntry) -> str | None:
    return device.name_by_user or device.name or None


def _entity_display_name(entity: er.RegistryEntry) -> str | None:
    return entity.name or entity.original_name or None


def build_matter_ha_lookup_from_registry(
    devices: list[dr.DeviceEntry],
    entities: list[er.RegistryEntry],
) -> dict[str, dict[str, Any]]:
    """Build lookup tables keyed by ``node_id`` and ``serial`` from registry snapshots."""
    by_node_id: dict[int, dict[str, Any]] = {}
    by_serial: dict[str, dict[str, Any]] = {}

    for device in devices:
        identifiers = getattr(device, "identifiers", None) or ()
        node_id = parse_matter_node_id(identifiers)
        serial = parse_matter_serial(identifiers)
        device_name = _device_display_name(device)
        if node_id is None and not serial:
            continue

        bucket = {
            "ha_device_name": device_name,
            "ha_entity_names": [],
            "ha_entity_ids": [],
            "ha_cover_entity_ids": [],
        }

        if node_id is not None:
            existing = by_node_id.get(node_id)
            if existing and not bucket["ha_device_name"]:
                bucket = existing
            elif existing and bucket["ha_device_name"]:
                # Prefer a user-renamed device when multiple HA devices map to one node.
                if device.name_by_user and not existing.get("ha_device_name_user_set"):
                    existing["ha_device_name"] = device_name
                    existing["ha_device_name_user_set"] = True
                bucket = existing
            else:
                by_node_id[node_id] = bucket
                if device.name_by_user:
                    bucket["ha_device_name_user_set"] = True

        if serial:
            by_serial[serial] = bucket

        for entity in entities:
            if entity.device_id != device.id or entity.disabled_by:
                continue
            display = _entity_display_name(entity)
            if display and display not in bucket["ha_entity_names"]:
                bucket["ha_entity_names"].append(display)
            if entity.entity_id not in bucket["ha_entity_ids"]:
                bucket["ha_entity_ids"].append(entity.entity_id)
            if entity.domain == "cover" and entity.entity_id not in bucket["ha_cover_entity_ids"]:
                bucket["ha_cover_entity_ids"].append(entity.entity_id)

    # Sort entity names with covers first for blinds.
    for bucket in {**by_node_id, **by_serial}.values():
        names = bucket.get("ha_entity_names") or []
        ids = bucket.get("ha_entity_ids") or []
        paired = list(zip(ids, names, strict=False))
        paired.sort(
            key=lambda item: (
                0 if item[0].startswith("cover.") else 1,
                item[1] or item[0],
            )
        )
        bucket["ha_entity_names"] = [name for _, name in paired if name]
        bucket["ha_entity_ids"] = [eid for eid, _ in paired]

    return {"by_node_id": by_node_id, "by_serial": by_serial}


def resolve_ha_names_for_node(
    node: dict[str, Any], lookup: dict[str, dict[str, Any]] | None
) -> dict[str, Any]:
    """Return HA name fields for a ThreadLens matter node, or empty defaults."""
    if not lookup:
        return {}
    node_id = node.get("node_id")
    serial = node.get("serial")
    by_node_id = lookup.get("by_node_id") or {}
    by_serial = lookup.get("by_serial") or {}

    match: dict[str, Any] | None = None
    if node_id is not None and node_id in by_node_id:
        match = by_node_id[node_id]
    elif isinstance(serial, str) and serial in by_serial:
        match = by_serial[serial]

    if not match:
        return {}

    return {
        "ha_device_name": match.get("ha_device_name"),
        "ha_entity_names": list(match.get("ha_entity_names") or []),
        "ha_entity_ids": list(match.get("ha_entity_ids") or []),
        "ha_cover_entity_ids": list(match.get("ha_cover_entity_ids") or []),
    }


@callback
def build_matter_node_ha_lookup(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    """Load Matter device/entity names from the HA registries."""
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    return build_matter_ha_lookup_from_registry(
        list(device_registry.devices.values()),
        list(entity_registry.entities.values()),
    )

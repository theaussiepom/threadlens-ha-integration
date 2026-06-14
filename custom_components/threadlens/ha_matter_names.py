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


def coerce_matter_node_id(value: Any) -> int | None:
    """Normalise ThreadLens/HA Matter node IDs to a comparable integer."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if raw.lower().startswith("0x"):
            try:
                return int(raw, 16)
            except ValueError:
                return None
        lowered = raw.lower()
        if len(raw) == 16 and all(char in "0123456789abcdef" for char in lowered):
            try:
                return int(lowered, 16)
            except ValueError:
                return None
        if raw.isdigit():
            return int(raw)
        if all(char in "0123456789abcdef" for char in lowered):
            try:
                return int(lowered, 16)
            except ValueError:
                return None
    return None


def parse_node_id_from_matter_unique_id(unique_id: Any) -> int | None:
    """Extract a Matter node ID from a Matter entity ``unique_id``."""
    if not isinstance(unique_id, str) or not unique_id:
        return None
    # {fabric_hex}-{node_id_hex}-{postfix}-...
    parts = unique_id.split("-", 2)
    if len(parts) < 2 or not parts[1]:
        return None
    return coerce_matter_node_id(parts[1])


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
        node_id = coerce_matter_node_id(parts[1])
        if node_id is not None:
            return node_id
    return None


def _normalise_serial(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    serial = value.strip()
    return serial or None


def parse_matter_serial(
    identifiers: set[tuple[str, str]] | list[tuple[str, str]] | None,
) -> str | None:
    """Extract a Matter serial identifier from HA device identifiers."""
    if not identifiers:
        return None
    for domain, ident in identifiers:
        if domain == MATTER_DOMAIN and ident.startswith(_SERIAL_PREFIX):
            return _normalise_serial(ident[len(_SERIAL_PREFIX) :])
    return None


def _device_display_name(device: dr.DeviceEntry) -> str | None:
    return device.name_by_user or device.name or None


def _entity_display_name(entity: er.RegistryEntry) -> str | None:
    return entity.name or entity.original_name or None


def _entity_platform(entity: er.RegistryEntry) -> str | None:
    platform = getattr(entity, "platform", None)
    if isinstance(platform, str) and platform:
        return platform
    domain = getattr(entity, "domain", None)
    return domain if isinstance(domain, str) and domain else None


def _empty_bucket() -> dict[str, Any]:
    return {
        "ha_device_name": None,
        "ha_entity_names": [],
        "ha_entity_ids": [],
        "ha_cover_entity_ids": [],
    }


def _bucket_for_node(by_node_id: dict[int, dict[str, Any]], node_id: int) -> dict[str, Any]:
    bucket = by_node_id.get(node_id)
    if bucket is None:
        bucket = _empty_bucket()
        by_node_id[node_id] = bucket
    return bucket


def _append_entity_to_bucket(bucket: dict[str, Any], entity: er.RegistryEntry) -> None:
    display = _entity_display_name(entity)
    if display and display not in bucket["ha_entity_names"]:
        bucket["ha_entity_names"].append(display)
    if entity.entity_id not in bucket["ha_entity_ids"]:
        bucket["ha_entity_ids"].append(entity.entity_id)
    if entity.domain == "cover" and entity.entity_id not in bucket["ha_cover_entity_ids"]:
        bucket["ha_cover_entity_ids"].append(entity.entity_id)


def _sort_bucket_entities(bucket: dict[str, Any]) -> None:
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


def build_matter_ha_lookup_from_registry(
    devices: list[dr.DeviceEntry],
    entities: list[er.RegistryEntry],
) -> dict[str, dict[str, Any]]:
    """Build lookup tables keyed by ``node_id`` and ``serial`` from registry snapshots."""
    by_node_id: dict[int, dict[str, Any]] = {}
    by_serial: dict[str, dict[str, Any]] = {}
    devices_by_id = {device.id: device for device in devices}

    for device in devices:
        identifiers = getattr(device, "identifiers", None) or ()
        node_id = parse_matter_node_id(identifiers)
        serial = parse_matter_serial(identifiers)
        device_name = _device_display_name(device)
        if node_id is None and not serial:
            continue

        bucket = _empty_bucket()
        bucket["ha_device_name"] = device_name

        if node_id is not None:
            existing = by_node_id.get(node_id)
            if existing:
                bucket = existing
                if device_name and (
                    not bucket.get("ha_device_name")
                    or (device.name_by_user and not existing.get("ha_device_name_user_set"))
                ):
                    bucket["ha_device_name"] = device_name
                    if device.name_by_user:
                        bucket["ha_device_name_user_set"] = True
            else:
                by_node_id[node_id] = bucket
                if device.name_by_user:
                    bucket["ha_device_name_user_set"] = True

        if serial:
            existing_serial = by_serial.get(serial)
            if existing_serial:
                bucket = existing_serial
            else:
                by_serial[serial] = bucket

        for entity in entities:
            if entity.device_id != device.id or entity.disabled_by:
                continue
            _append_entity_to_bucket(bucket, entity)

    # Fallback: map Matter entities directly via unique_id when device links are missing.
    for entity in entities:
        if entity.disabled_by or _entity_platform(entity) != MATTER_DOMAIN:
            continue
        node_id = parse_node_id_from_matter_unique_id(getattr(entity, "unique_id", None))
        if node_id is None:
            continue
        bucket = _bucket_for_node(by_node_id, node_id)
        device = devices_by_id.get(entity.device_id) if entity.device_id else None
        if device and not bucket.get("ha_device_name"):
            bucket["ha_device_name"] = _device_display_name(device)
            if device.name_by_user:
                bucket["ha_device_name_user_set"] = True
        _append_entity_to_bucket(bucket, entity)

    for bucket in {**by_node_id, **by_serial}.values():
        _sort_bucket_entities(bucket)

    return {"by_node_id": by_node_id, "by_serial": by_serial}


def resolve_ha_names_for_node(
    node: dict[str, Any], lookup: dict[str, dict[str, Any]] | None
) -> dict[str, Any]:
    """Return HA name fields for a ThreadLens matter node, or empty defaults."""
    if not lookup:
        return {}
    node_id = coerce_matter_node_id(node.get("node_id"))
    serial = _normalise_serial(node.get("serial"))
    by_node_id = lookup.get("by_node_id") or {}
    by_serial = lookup.get("by_serial") or {}

    match: dict[str, Any] | None = None
    if node_id is not None and node_id in by_node_id:
        match = by_node_id[node_id]
    elif serial and serial in by_serial:
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

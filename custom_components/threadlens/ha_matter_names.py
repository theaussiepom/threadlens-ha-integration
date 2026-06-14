"""Map ThreadLens Matter node IDs to Home Assistant device/entity names.

ThreadLens reports Matter node IDs and serials from its collectors. Home
Assistant's Matter integration registers devices with identifiers like
``("matter", "deviceid_{fabric}-{node_id_hex}-...")``. This module cross-
references those registries so the dashboard can show familiar blind/cover
names from HA rather than only ThreadLens serials.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

MATTER_DOMAIN = "matter"
_DEVICE_ID_PREFIX = "deviceid_"
_SERIAL_PREFIX = "serial_"

_LOGGER = logging.getLogger(__name__)


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


def _serial_lookup_key(value: Any) -> str | None:
    serial = _normalise_serial(value)
    if not serial:
        return None
    return serial.upper()


def _threadlens_serial_candidates(node: dict[str, Any]) -> list[str]:
    """Return serial-like identifiers from a ThreadLens node payload."""
    seen: set[str] = set()
    candidates: list[str] = []
    for key in ("serial", "friendly_name", "name"):
        serial = _normalise_serial(node.get(key))
        if not serial:
            continue
        lookup_key = _serial_lookup_key(serial)
        if lookup_key and lookup_key not in seen:
            seen.add(lookup_key)
            candidates.append(serial)
    return candidates


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


def _device_serial(device: dr.DeviceEntry) -> str | None:
    """Return a Matter serial from device identifiers or registry metadata."""
    serial = parse_matter_serial(getattr(device, "identifiers", None) or ())
    if serial:
        return serial
    return _normalise_serial(getattr(device, "serial_number", None))


def _device_display_name(device: dr.DeviceEntry) -> str | None:
    return device.name_by_user or device.name or None


def _entity_display_name(entity: er.RegistryEntry) -> str | None:
    return entity.name or entity.original_name or entity.entity_id or None


def _is_matter_registry_entity(entity: er.RegistryEntry) -> bool:
    platform = getattr(entity, "platform", None)
    if platform == MATTER_DOMAIN:
        return True
    return parse_node_id_from_matter_unique_id(getattr(entity, "unique_id", None)) is not None


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


def _register_serial_lookup(
    by_serial: dict[str, dict[str, Any]],
    serial: str | None,
    bucket: dict[str, Any],
) -> dict[str, Any]:
    """Index a bucket by normalised serial and return the canonical bucket."""
    lookup_key = _serial_lookup_key(serial)
    if not lookup_key:
        return bucket
    existing = by_serial.get(lookup_key)
    if existing is None:
        by_serial[lookup_key] = bucket
        return bucket
    return existing


def _merge_bucket(target: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    if not source:
        return target
    if source.get("ha_device_name") and not target.get("ha_device_name"):
        target["ha_device_name"] = source["ha_device_name"]
    if source.get("ha_device_name_user_set"):
        target["ha_device_name_user_set"] = True
    for entity in source.get("ha_entity_ids") or []:
        if entity not in target["ha_entity_ids"]:
            target["ha_entity_ids"].append(entity)
    for name in source.get("ha_entity_names") or []:
        if name not in target["ha_entity_names"]:
            target["ha_entity_names"].append(name)
    for cover_id in source.get("ha_cover_entity_ids") or []:
        if cover_id not in target["ha_cover_entity_ids"]:
            target["ha_cover_entity_ids"].append(cover_id)
    return target


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


def _attach_device_entities(
    bucket: dict[str, Any],
    device: dr.DeviceEntry | None,
    entities: list[er.RegistryEntry],
) -> None:
    if device is None:
        return
    device_name = _device_display_name(device)
    if device_name and (
        not bucket.get("ha_device_name")
        or (device.name_by_user and not bucket.get("ha_device_name_user_set"))
    ):
        bucket["ha_device_name"] = device_name
        if device.name_by_user:
            bucket["ha_device_name_user_set"] = True
    for entity in entities:
        if entity.device_id != device.id or entity.disabled_by:
            continue
        _append_entity_to_bucket(bucket, entity)


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
        serial = _device_serial(device)
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
            bucket = _register_serial_lookup(by_serial, serial, bucket)

        _attach_device_entities(bucket, device, entities)

    # Fallback: map Matter entities directly via unique_id when device links are missing.
    for entity in entities:
        if entity.disabled_by or not _is_matter_registry_entity(entity):
            continue
        node_id = parse_node_id_from_matter_unique_id(getattr(entity, "unique_id", None))
        if node_id is None:
            continue
        bucket = _bucket_for_node(by_node_id, node_id)
        device = devices_by_id.get(entity.device_id) if entity.device_id else None
        if device:
            serial = _device_serial(device)
            if serial:
                bucket = _register_serial_lookup(by_serial, serial, bucket)
        _attach_device_entities(bucket, device, [entity])
        _append_entity_to_bucket(bucket, entity)

    for bucket in {**by_node_id, **by_serial}.values():
        _sort_bucket_entities(bucket)

    return {"by_node_id": by_node_id, "by_serial": by_serial}


def _enrich_lookup_from_matter_client(
    hass: HomeAssistant,
    lookup: dict[str, dict[str, Any]],
    *,
    device_registry: dr.DeviceRegistry | None = None,
    entity_registry: er.EntityRegistry | None = None,
) -> None:
    """Augment registry lookup using the live Home Assistant Matter client."""
    try:
        from homeassistant.components.matter.const import DOMAIN, ID_TYPE_DEVICE_ID
        from homeassistant.components.matter.helpers import get_device_id, get_matter
    except ImportError:
        return

    try:
        matter = get_matter(hass)
    except (IndexError, AttributeError, KeyError, RuntimeError):
        return

    client = getattr(matter, "matter_client", None)
    server_info = getattr(client, "server_info", None) if client else None
    if client is None or server_info is None:
        return

    device_registry = device_registry or dr.async_get(hass)
    entity_registry = entity_registry or er.async_get(hass)
    by_node_id = lookup.setdefault("by_node_id", {})
    by_serial = lookup.setdefault("by_serial", {})
    entities = list(entity_registry.entities.values())

    try:
        nodes = client.get_nodes()
    except Exception:
        _LOGGER.debug("ThreadLens Matter client node list unavailable", exc_info=True)
        return

    for node in nodes:
        node_id = getattr(node, "node_id", None)
        if not isinstance(node_id, int):
            continue

        endpoints = getattr(node, "endpoints", None) or {}
        endpoint = endpoints.get(0) or (next(iter(endpoints.values()), None) if endpoints else None)
        if endpoint is None:
            continue

        try:
            device_id_str = get_device_id(server_info, endpoint)
        except Exception:
            _LOGGER.debug("ThreadLens could not resolve Matter device id for node %s", node_id)
            continue

        bucket = _bucket_for_node(by_node_id, node_id)
        device = device_registry.async_get_device(
            identifiers={(DOMAIN, f"{ID_TYPE_DEVICE_ID}_{device_id_str}")}
        )
        if device is None:
            continue

        serial = _device_serial(device)
        if serial:
            existing = _register_serial_lookup(by_serial, serial, bucket)
            if existing is not bucket:
                _merge_bucket(existing, bucket)
                bucket = existing
                by_node_id[node_id] = bucket

        _attach_device_entities(bucket, device, entities)


def resolve_ha_names_for_node(
    node: dict[str, Any], lookup: dict[str, dict[str, Any]] | None
) -> dict[str, Any]:
    """Return HA name fields for a ThreadLens matter node, or empty defaults."""
    if not lookup:
        return {}
    node_id = coerce_matter_node_id(node.get("node_id"))
    by_node_id = lookup.get("by_node_id") or {}
    by_serial = lookup.get("by_serial") or {}

    match: dict[str, Any] | None = None
    if node_id is not None and node_id in by_node_id:
        match = by_node_id[node_id]

    if match is None:
        for serial in _threadlens_serial_candidates(node):
            lookup_key = _serial_lookup_key(serial)
            if lookup_key and lookup_key in by_serial:
                match = by_serial[lookup_key]
                break

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
    lookup = build_matter_ha_lookup_from_registry(
        list(device_registry.devices.values()),
        list(entity_registry.entities.values()),
    )
    _enrich_lookup_from_matter_client(
        hass,
        lookup,
        device_registry=device_registry,
        entity_registry=entity_registry,
    )
    return lookup

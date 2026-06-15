"""Push Home Assistant Matter device names to ThreadLens Core."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .api import ThreadLensApi, ThreadLensApiError
from .ha_matter_names import (
    build_matter_node_ha_lookup,
    coerce_matter_node_id,
    resolve_ha_names_for_node,
)

_LOGGER = logging.getLogger(__name__)


def build_matter_names_payload(
    hass: HomeAssistant,
    *,
    matter_servers: list[dict[str, Any]],
    matter_nodes: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a Core API payload mapping Matter node IDs to HA device names."""
    lookup = build_matter_node_ha_lookup(hass)

    server_ids = [
        str(server["id"])
        for server in matter_servers
        if isinstance(server, dict) and server.get("id") is not None
    ]
    default_server_id = server_ids[0] if len(server_ids) == 1 else None

    devices: list[dict[str, Any]] = []
    for node in matter_nodes:
        if not isinstance(node, dict):
            continue
        node_id = coerce_matter_node_id(node.get("node_id"))
        if node_id is None:
            continue
        ha_fields = resolve_ha_names_for_node(node, lookup)
        ha_device_name = ha_fields.get("ha_device_name")
        if not ha_device_name:
            continue
        server_id = node.get("server_id") or default_server_id
        if not server_id:
            continue
        cover_ids = ha_fields.get("ha_cover_entity_ids") or []
        entity_ids = ha_fields.get("ha_entity_ids") or []
        ha_entity_id = cover_ids[0] if cover_ids else (entity_ids[0] if entity_ids else None)
        devices.append(
            {
                "server_id": str(server_id),
                "node_id": node_id,
                "ha_device_name": str(ha_device_name).strip(),
                "ha_entity_id": ha_entity_id,
            }
        )

    return {"source": "homeassistant", "devices": devices}


async def async_push_matter_names_to_core(
    hass: HomeAssistant,
    api: ThreadLensApi,
    *,
    matter_servers: list[dict[str, Any]],
    matter_nodes: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Best-effort push of HA Matter names to ThreadLens Core."""
    payload = build_matter_names_payload(
        hass,
        matter_servers=matter_servers,
        matter_nodes=matter_nodes,
    )
    if not payload["devices"]:
        return None
    try:
        result = await api.post_matter_names(payload)
    except ThreadLensApiError as exc:
        _LOGGER.debug("ThreadLens Matter name push failed: %s", exc)
        return None
    _LOGGER.debug(
        "ThreadLens Matter name push matched %s device(s)",
        result.get("matched_devices"),
    )
    return result

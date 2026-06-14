"""Pure dashboard aggregation for the ThreadLens panel.

This module is intentionally free of Home Assistant imports so it can be unit
tested in isolation. It composes a single dashboard payload from the raw
ThreadLens Core REST responses already collected by the coordinator.

It does not poll, mutate, or infer device parentage. It only reshapes
observations into a frontend-friendly structure.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

# Friendly, non-causal labels for known health reason codes. Unknown codes are
# humanised generically so new core reasons still render acceptably.
REASON_LABELS: dict[str, str] = {
    "otbr_rest_endpoint_mismatch": "OTBR REST endpoints disagree",
    "foreign_trel_services_observed": "Other Thread/TREL services visible",
    "mdns_service_flapping_degraded": "mDNS service add/remove instability",
    "mdns_service_flapping_warning": "mDNS service add/remove churn",
    "otbr_thread_stack_disabled": "OTBR Thread stack disabled",
    "otbr_unreachable": "OTBR REST API unreachable",
    "matter_server_disconnected": "Matter server disconnected",
    "matter_node_unavailable": "Matter node unavailable",
    "primary_thread_network_unknown": "Primary Thread network unknown",
    "configured_otbrs_disagree_on_ext_pan_id": "Configured OTBRs disagree on network",
}

_SEVERITY = {
    "healthy": 0,
    "unknown": 1,
    "warning": 2,
    "degraded": 3,
    "critical": 4,
}


def humanize_reason(code: str) -> str:
    """Return a friendly label for a reason code."""
    if code in REASON_LABELS:
        return REASON_LABELS[code]
    return code.replace("_", " ").strip().capitalize()


def friendly_reasons(codes: Any) -> list[dict[str, str]]:
    """Map a list of reason codes to ``{code, label}`` dictionaries."""
    if not isinstance(codes, list):
        return []
    result: list[dict[str, str]] = []
    seen: set[str] = set()
    for code in codes:
        if not isinstance(code, str) or code in seen:
            continue
        seen.add(code)
        result.append({"code": code, "label": humanize_reason(code)})
    return result


def _state(section: Any) -> str:
    if isinstance(section, dict):
        value = section.get("state")
        if isinstance(value, str):
            return value
    return "unknown"


def _reasons(section: Any) -> list[str]:
    if isinstance(section, dict):
        value = section.get("reasons")
        if isinstance(value, list):
            return [str(item) for item in value]
    return []


def _rollup(states: list[str]) -> str:
    """Return the worst state from a list, or ``unknown`` when empty."""
    worst = "unknown"
    worst_value = -1
    for state in states:
        value = _SEVERITY.get(state, 1)
        if value > worst_value:
            worst_value = value
            worst = state
    return worst


def _combined_reasons(*sections: Any) -> list[dict[str, str]]:
    codes: list[str] = []
    for section in sections:
        codes.extend(_reasons(section))
    return friendly_reasons(codes)


def _otbr_entry(raw: dict[str, Any]) -> dict[str, Any]:
    health = raw.get("health") if isinstance(raw.get("health"), dict) else {}
    return {
        "id": raw.get("id"),
        "name": raw.get("name"),
        "reachable": bool(raw.get("reachable")),
        "health": _state(health),
        "reasons": friendly_reasons(_reasons(health)),
        "thread_state": raw.get("thread_state"),
        "role": raw.get("role"),
        "network_name": raw.get("network_name"),
        "extended_pan_id": raw.get("ext_pan_id"),
        "rloc16": raw.get("rloc16"),
        "channel": raw.get("channel"),
        "thread_state_source": raw.get("thread_state_source"),
        "rest_endpoint_mismatch": bool(raw.get("rest_endpoint_mismatch")),
        "json_api_thread_state": raw.get("json_api_thread_state"),
        "legacy_node_thread_state": raw.get("legacy_node_thread_state"),
        "capabilities": (
            raw.get("capabilities") if isinstance(raw.get("capabilities"), dict) else {}
        ),
    }


def _network_entry(raw: dict[str, Any], health_by_pan: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ext_pan_id = raw.get("ext_pan_id")
    health_section = health_by_pan.get(ext_pan_id, {}) if ext_pan_id else {}
    return {
        "extended_pan_id": ext_pan_id,
        "name": raw.get("name"),
        "channel": raw.get("channel"),
        "pan_id": raw.get("pan_id"),
        "border_router_count": raw.get("border_router_count"),
        "classification": raw.get("classification"),
        "health": _state(health_section) if health_section else "unknown",
    }


def _matter_section(
    matter_servers: list[dict[str, Any]],
    matter_nodes: list[dict[str, Any]],
    health: dict[str, Any] | None,
) -> dict[str, Any]:
    servers_total = len(matter_servers)
    servers_connected = sum(1 for server in matter_servers if server.get("connected"))
    unavailable_nodes = [
        {
            "node_id": node.get("node_id"),
            "server_id": node.get("server_id"),
            "friendly_name": node.get("friendly_name"),
        }
        for node in matter_nodes
        if node.get("available") is False
    ]
    health_states: list[str] = []
    if isinstance(health, dict):
        for entry in health.get("matter_servers", []) or []:
            health_states.append(_state(entry))
        for entry in health.get("matter_nodes", []) or []:
            health_states.append(_state(entry))
    return {
        "servers": servers_total,
        "servers_connected": servers_connected,
        "node_count": len(matter_nodes),
        "unavailable_count": len(unavailable_nodes),
        "unavailable_nodes": unavailable_nodes,
        "health": _rollup(health_states) if health_states else "unknown",
    }


def _top_service_types(mdns_services: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for service in mdns_services:
        service_type = service.get("service_type")
        if isinstance(service_type, str) and service_type:
            counter[service_type] += 1
    return [
        {"service_type": service_type, "count": count}
        for service_type, count in counter.most_common(limit)
    ]


def build_dashboard_payload(
    *,
    connected: bool,
    last_update: str | None = None,
    version: dict[str, Any] | None = None,
    status: dict[str, Any] | None = None,
    health: dict[str, Any] | None = None,
    otbrs: list[dict[str, Any]] | None = None,
    networks: list[dict[str, Any]] | None = None,
    matter_servers: list[dict[str, Any]] | None = None,
    matter_nodes: list[dict[str, Any]] | None = None,
    mdns_services: list[dict[str, Any]] | None = None,
    trel_services: list[dict[str, Any]] | None = None,
    report_urls: dict[str, str] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Compose the unified dashboard payload from raw ThreadLens responses."""
    otbrs = otbrs or []
    networks = networks or []
    matter_servers = matter_servers or []
    matter_nodes = matter_nodes or []
    mdns_services = mdns_services or []
    trel_services = trel_services or []
    report_urls = report_urls or {}

    version_str = version.get("version") if isinstance(version, dict) else None

    overall = health.get("overall") if isinstance(health, dict) else None
    environment = health.get("environment") if isinstance(health, dict) else None
    mdns_health = health.get("mdns") if isinstance(health, dict) else None
    trel_health = health.get("trel") if isinstance(health, dict) else None

    collectors = status.get("collectors") if isinstance(status, dict) else None
    collectors = collectors if isinstance(collectors, dict) else {}
    mqtt_status = collectors.get("mqtt") if isinstance(collectors.get("mqtt"), dict) else None
    mdns_collector = collectors.get("mdns") if isinstance(collectors.get("mdns"), dict) else {}

    reports_status = status.get("reports") if isinstance(status, dict) else None
    last_generated_at = (
        reports_status.get("last_generated_at") if isinstance(reports_status, dict) else None
    )

    health_networks = health.get("thread_networks") if isinstance(health, dict) else None
    health_by_pan: dict[str, dict[str, Any]] = {}
    if isinstance(health_networks, list):
        for entry in health_networks:
            if isinstance(entry, dict) and entry.get("ext_pan_id"):
                health_by_pan[str(entry["ext_pan_id"])] = entry

    foreign_trel = sum(1 for service in trel_services if service.get("is_foreign"))

    mqtt_payload: dict[str, Any] | None = None
    if mqtt_status is not None:
        mqtt_payload = {
            "enabled": mqtt_status.get("enabled"),
            "connected": mqtt_status.get("connected"),
            "homeassistant_discovery_enabled": mqtt_status.get("homeassistant_discovery_enabled"),
            "last_publish_at": mqtt_status.get("last_publish_at"),
            "last_error": mqtt_status.get("last_error"),
        }

    return {
        "threadlens": {
            "version": version_str,
            "api_connected": bool(connected),
            "last_update": last_update,
            "overall_health": _state(overall) if connected else "unknown",
            "environment_health": _state(environment) if connected else "unknown",
            "reasons": _combined_reasons(overall, environment),
        },
        "otbrs": [_otbr_entry(item) for item in otbrs if isinstance(item, dict)],
        "networks": [
            _network_entry(item, health_by_pan) for item in networks if isinstance(item, dict)
        ],
        "matter": _matter_section(matter_servers, matter_nodes, health),
        "mdns": {
            "health": _state(mdns_health),
            "service_count": len(mdns_services),
            "observation_degraded": mdns_collector.get("observation_degraded"),
            "top_service_types": _top_service_types(mdns_services),
        },
        "trel": {
            "health": _state(trel_health),
            "service_count": len(trel_services),
            "foreign_service_count": foreign_trel,
            "reasons": friendly_reasons(_reasons(trel_health)),
        },
        "mqtt": mqtt_payload,
        "report": {
            "report_url": report_urls.get("yaml"),
            "report_url_json": report_urls.get("json"),
            "last_generated_at": last_generated_at,
        },
        "error": error,
    }


def build_disconnected_payload(
    *,
    version: dict[str, Any] | None = None,
    last_update: str | None = None,
    report_urls: dict[str, str] | None = None,
    error: str = "Cannot reach the ThreadLens API",
) -> dict[str, Any]:
    """Return a structured payload usable by the panel when the API is down."""
    return build_dashboard_payload(
        connected=False,
        last_update=last_update,
        version=version,
        report_urls=report_urls,
        error=error,
    )

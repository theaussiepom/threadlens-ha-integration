"""Build the redacted summary payload for the native companion panel."""

from __future__ import annotations

from typing import Any

from .coordinator import ThreadLensCoordinatorData
from .dashboard import compute_health_summary


def _severity_label(value: Any) -> str:
    """Map Core health values onto the panel's three calm states."""
    text = str(value or "").lower()
    if text in ("healthy", "ok"):
        return "ok"
    if text in ("warning", "watch", "degraded"):
        return "watch"
    if text in ("critical", "incident"):
        return "incident"
    return "unknown"


def _collectors(status: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(status, dict):
        return {}
    collectors = status.get("collectors")
    return collectors if isinstance(collectors, dict) else {}


def _matter_unavailable_count(nodes: list[dict[str, Any]]) -> int:
    count = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        state = str(node.get("state") or node.get("availability") or "").lower()
        if state in {"unavailable", "offline"}:
            count += 1
    return count


def build_panel_summary(
    data: ThreadLensCoordinatorData | None,
    *,
    core_url: str,
    connected: bool,
    last_exception: str | None = None,
) -> dict[str, Any]:
    """Return a redacted summary dict for the companion panel frontend."""
    summary: dict[str, Any] = {
        "connected": bool(connected and data is not None),
        "core_url": core_url,
        "core_version": None,
        "overall_health": "unknown",
        "current_finding": None,
        "matter_node_count": 0,
        "matter_nodes_unavailable": 0,
        "otbr_count": 0,
        "network_count": 0,
        "mqtt_connected": False,
        "mdns_observer_running": False,
        "last_update": None,
        "networks": [],
        "error": last_exception if not connected else None,
    }

    if data is None:
        return summary

    collectors = _collectors(data.status)
    mqtt = collectors.get("mqtt") if isinstance(collectors.get("mqtt"), dict) else {}
    mdns = collectors.get("mdns") if isinstance(collectors.get("mdns"), dict) else {}

    summary["core_version"] = (
        (data.version or {}).get("version") if isinstance(data.version, dict) else None
    )
    summary["matter_node_count"] = len(data.matter_nodes or [])
    summary["matter_nodes_unavailable"] = _matter_unavailable_count(data.matter_nodes or [])
    summary["otbr_count"] = len(data.otbrs or [])
    summary["network_count"] = len(data.networks or [])
    summary["mqtt_connected"] = bool(mqtt.get("connected"))
    summary["mdns_observer_running"] = bool(mdns.get("running") or mdns.get("observer_running"))
    summary["last_update"] = data.last_update

    health_summary = compute_health_summary(
        connected=connected,
        health=data.health,
        otbrs=data.otbrs,
    )
    if health_summary:
        summary["overall_health"] = _severity_label(health_summary.get("overall_health"))
        reasons = health_summary.get("reasons") or []
        if reasons and isinstance(reasons[0], dict):
            summary["current_finding"] = reasons[0].get("label")

    networks: list[dict[str, Any]] = []
    health = data.health if isinstance(data.health, dict) else {}
    health_networks = {
        str(item.get("extended_pan_id") or item.get("ext_pan_id") or ""): item
        for item in (health.get("thread_networks") or [])
        if isinstance(item, dict)
    }
    for net in data.networks or []:
        if not isinstance(net, dict):
            continue
        ext_pan = str(net.get("ext_pan_id") or net.get("extended_pan_id") or "")
        health_section = health_networks.get(ext_pan, {})
        networks.append(
            {
                "name": net.get("name") or ext_pan or "Thread network",
                "health": _severity_label(
                    health_section.get("state") if isinstance(health_section, dict) else "unknown"
                ),
                "border_router_count": int(net.get("border_router_count") or 0),
                "channel": net.get("channel"),
            }
        )
    summary["networks"] = networks
    return summary

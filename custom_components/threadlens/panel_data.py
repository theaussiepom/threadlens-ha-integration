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
        elif node.get("available") is False:
            count += 1
    return count


def _node_available(node: dict[str, Any]) -> bool:
    if node.get("available") is True:
        return True
    state = str(node.get("state") or node.get("availability") or "").lower()
    return state == "available"


def _read_probe_issue(node: dict[str, Any]) -> bool:
    if not node.get("read_probe_diagnostics_available"):
        return False
    if node.get("last_read_probe_limited"):
        return False
    if node.get("last_read_probe_ok") is False:
        return True
    failures = node.get("read_probe_failures_24h")
    return isinstance(failures, int) and failures >= 1


def summarize_matter_read_probes(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate read probe diagnostics from Core matter node payloads."""
    diagnostics_nodes = [
        node
        for node in nodes
        if isinstance(node, dict) and node.get("read_probe_diagnostics_available")
    ]
    issues = [node for node in diagnostics_nodes if _read_probe_issue(node)]
    available_failed = [node for node in issues if _node_available(node)]
    ping_nodes = [
        node for node in nodes if isinstance(node, dict) and node.get("ping_diagnostics_available")
    ]
    ping_failed = [
        node
        for node in ping_nodes
        if node.get("last_ping_ok") is False and not node.get("last_read_probe_limited")
    ]
    issue_summaries: list[dict[str, Any]] = []
    for node in issues[:5]:
        name = node.get("friendly_name") or f"Node {node.get('node_id', '?')}"
        last_ok = node.get("last_read_probe_ok")
        if _node_available(node) and last_ok is False:
            detail = "Last read check failed."
        elif last_ok is False:
            detail = "Last read check failed."
        else:
            failures = node.get("read_probe_failures_24h")
            failures_text = failures if failures is not None else "unknown"
            detail = f"Last read check failed ({failures_text} in 24h)."
        issue_summaries.append(
            {
                "name": name,
                "node_id": node.get("node_id"),
                "available": _node_available(node),
                "last_read_probe_ok": last_ok,
                "read_probe_failures_24h": node.get("read_probe_failures_24h"),
                "detail": detail,
            }
        )
    return {
        "read_probe_diagnostics_available": len(diagnostics_nodes) > 0,
        "matter_read_probe_issues": len(issues),
        "matter_read_probe_available_but_failed": len(available_failed),
        "read_probe_nodes_with_diagnostics": len(diagnostics_nodes),
        "ping_diagnostics_available": len(ping_nodes) > 0,
        "ping_probe_failures": len(ping_failed),
        "read_probe_issue_nodes": issue_summaries,
    }


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
        "read_probe_diagnostics_available": False,
        "matter_read_probe_issues": 0,
        "matter_read_probe_available_but_failed": 0,
        "read_probe_issue_nodes": [],
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
    matter_nodes = [node for node in (data.matter_nodes or []) if isinstance(node, dict)]
    summary["matter_node_count"] = len(matter_nodes)
    summary["matter_nodes_unavailable"] = _matter_unavailable_count(matter_nodes)
    read_probe_summary = summarize_matter_read_probes(matter_nodes)
    summary.update(read_probe_summary)
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

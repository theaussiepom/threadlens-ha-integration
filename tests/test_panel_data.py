"""Tests for the redacted panel summary payload."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from support import load_submodule

panel_data = load_submodule("panel_data")
build_panel_summary = panel_data.build_panel_summary


@dataclass
class _FakeData:
    connected: bool = True
    version: dict[str, Any] | None = field(default_factory=lambda: {"version": "0.2.0"})
    health: dict[str, Any] | None = field(
        default_factory=lambda: {
            "overall": {"state": "healthy", "reasons": []},
            "environment": {"state": "healthy", "reasons": []},
            "thread_networks": [{"extended_pan_id": "abc", "state": "healthy"}],
        }
    )
    status: dict[str, Any] | None = field(
        default_factory=lambda: {
            "collectors": {
                "mqtt": {"connected": True},
                "mdns": {"running": True},
            }
        }
    )
    last_update: str | None = "2026-06-14T12:00:00+00:00"
    otbrs: list[dict[str, Any]] = field(default_factory=lambda: [{"id": "otbr1"}])
    networks: list[dict[str, Any]] = field(
        default_factory=lambda: [{"name": "Home", "ext_pan_id": "abc", "border_router_count": 1}]
    )
    matter_nodes: list[dict[str, Any]] = field(
        default_factory=lambda: [{"state": "available"}, {"state": "unavailable"}]
    )


def test_panel_summary_disconnected() -> None:
    summary = build_panel_summary(None, core_url="http://core:8128", connected=False)
    assert summary["connected"] is False
    assert summary["core_url"] == "http://core:8128"
    assert summary["matter_node_count"] == 0


def test_panel_summary_connected_counts() -> None:
    summary = build_panel_summary(
        _FakeData(),
        core_url="https://threadlens.example.com",
        connected=True,
    )
    assert summary["connected"] is True
    assert summary["core_version"] == "0.2.0"
    assert summary["overall_health"] == "ok"
    assert summary["matter_node_count"] == 2
    assert summary["matter_nodes_unavailable"] == 1
    assert summary["otbr_count"] == 1
    assert summary["network_count"] == 1
    assert summary["mqtt_connected"] is True
    assert summary["mdns_observer_running"] is True
    assert len(summary["networks"]) == 1
    assert summary["networks"][0]["name"] == "Home"

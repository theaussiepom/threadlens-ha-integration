"""Diagnostics module tests."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from support import install_homeassistant_stubs, load_submodule, make_config_entry, make_hass

install_homeassistant_stubs()
diagnostics = load_submodule("diagnostics")
coordinator_mod = load_submodule("coordinator")


class _Data:
    connected = True
    version = {"tool": "ThreadLens", "version": "0.2.0"}
    last_update = "2026-06-14T12:00:00+00:00"
    health = {"overall": {"state": "healthy", "reasons": []}}
    status = {"mode": "both", "reports": {}, "collectors": {"mqtt": {"connected": True}}}
    matter_nodes = [
        {
            "node_id": 3,
            "friendly_name": "Blind",
            "available": True,
            "read_probe_diagnostics_available": True,
            "last_read_probe_ok": False,
            "read_probe_failures_24h": 1,
            "ping_diagnostics_available": True,
            "last_ping_ok": False,
        }
    ]


def test_diagnostics_redacts_url_and_includes_embed_setting() -> None:
    hass = make_hass()
    entry = make_config_entry(
        data={"url": "http://192.168.1.10:8128/?token=secret"},
        options={"embed_dashboard": False},
    )
    coordinator = MagicMock()
    coordinator.data = _Data()
    hass.data = {"threadlens": {entry.entry_id: coordinator}}

    result = asyncio.run(diagnostics.async_get_config_entry_diagnostics(hass, entry))
    assert result["config"]["embed_dashboard"] is False
    assert result["config"]["url"] == "http://192.168.1.10:8128/"
    assert "secret" not in result["config"]["url"]
    assert "token" not in result["config"]["url"]
    assert result["connected"] is True
    assert result["version"]["version"] == "0.2.0"
    assert result["last_update"] == "2026-06-14T12:00:00+00:00"
    assert result["matter_read_probe_diagnostics_available"] is True
    assert result["matter_read_probe_issues"] == 1
    assert result["ping_diagnostics_available"] is True
    assert result["ping_probe_failures"] == 1
    assert result["read_probe_issue_nodes"][0]["detail"]
    assert "command" not in result["read_probe_issue_nodes"][0]["detail"].lower()

"""Tests for the ThreadLens dashboard websocket command."""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType
from unittest.mock import MagicMock

from support import install_homeassistant_stubs, load_submodule


def _install_websocket_stub() -> None:
    if "homeassistant.components.websocket_api" in sys.modules:
        return

    voluptuous = ModuleType("voluptuous")

    class _Required:
        def __init__(self, key):
            self.key = key

        def __call__(self, schema):
            return schema

    voluptuous.Required = _Required
    sys.modules["voluptuous"] = voluptuous

    components = ModuleType("homeassistant.components")
    websocket_api = ModuleType("homeassistant.components.websocket_api")

    def websocket_command(schema):
        def decorator(func):
            return func

        return decorator

    def async_response(func):
        return func

    def async_register_command(hass, handler):
        hass.data.setdefault("websocket_commands", []).append(handler)

    websocket_api.websocket_command = websocket_command
    websocket_api.async_response = async_response
    websocket_api.async_register_command = async_register_command
    components.websocket_api = websocket_api
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.websocket_api"] = websocket_api


def _load_websocket():
    install_homeassistant_stubs()
    _install_websocket_stub()
    load_submodule("const")
    load_submodule("api")
    load_submodule("coordinator")
    load_submodule("dashboard")
    return load_submodule("websocket")


class _FakeConnection:
    def __init__(self):
        self.error = None
        self.result = None

    def send_error(self, msg_id, code, message):
        self.error = (msg_id, code, message)

    def send_result(self, msg_id, result):
        self.result = (msg_id, result)


class _FakeHass:
    def __init__(self, coordinator=None):
        self.data = {"threadlens": {}}
        if coordinator is not None:
            self.data["threadlens"]["entry1"] = coordinator


def test_websocket_returns_disconnected_payload_when_coordinator_missing():
    websocket = _load_websocket()
    hass = _FakeHass()
    connection = _FakeConnection()
    asyncio.run(websocket.websocket_dashboard(hass, connection, {"id": 7}))
    assert connection.error == (7, "not_configured", "ThreadLens is not configured")


def test_websocket_returns_payload_from_coordinator(monkeypatch):
    websocket = _load_websocket()
    coordinator = MagicMock()
    coordinator.dashboard_payload.return_value = {
        "threadlens": {"api_connected": True, "version": "0.1.2"},
        "error": None,
    }
    monkeypatch.setattr(websocket, "_first_coordinator", lambda _hass: coordinator)
    hass = _FakeHass()
    connection = _FakeConnection()
    asyncio.run(websocket.websocket_dashboard(hass, connection, {"id": 3}))
    assert connection.result[0] == 3
    assert connection.result[1]["threadlens"]["api_connected"] is True


def test_websocket_survives_coordinator_payload_exception(monkeypatch):
    websocket = _load_websocket()
    coordinator = MagicMock()
    coordinator.dashboard_payload.side_effect = RuntimeError("boom")
    monkeypatch.setattr(websocket, "_first_coordinator", lambda _hass: coordinator)
    hass = _FakeHass()
    connection = _FakeConnection()
    asyncio.run(websocket.websocket_dashboard(hass, connection, {"id": 9}))
    assert connection.result[0] == 9
    assert connection.result[1]["threadlens"]["api_connected"] is False
    assert "failed to build" in connection.result[1]["error"]

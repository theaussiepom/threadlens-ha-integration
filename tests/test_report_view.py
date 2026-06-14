"""Tests for the authenticated report YAML proxy HTTP view."""

from __future__ import annotations

import asyncio
import sys
from types import ModuleType
from unittest.mock import AsyncMock

from support import install_homeassistant_stubs, load_submodule


def _install_http_stub() -> None:
    if "homeassistant.components.http" in sys.modules:
        return
    components = ModuleType("homeassistant.components")
    http = ModuleType("homeassistant.components.http")

    class HomeAssistantView:
        url = None
        name = None
        requires_auth = True

    http.HomeAssistantView = HomeAssistantView
    components.http = http
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.http"] = http


def _load_report_view():
    install_homeassistant_stubs()
    _install_http_stub()
    load_submodule("const")
    load_submodule("api")
    load_submodule("coordinator")
    return load_submodule("report_view")


class _FakeHttp:
    def __init__(self):
        self.views = []

    def register_view(self, view):
        self.views.append(view)


class _FakeHass:
    def __init__(self):
        self.http = _FakeHttp()
        self.data = {}


def test_report_view_is_registered():
    report_view = _load_report_view()
    const = sys.modules["threadlens.const"]
    hass = _FakeHass()
    report_view.async_register_http_views(hass)
    assert len(hass.http.views) == 1
    view = hass.http.views[0]
    assert view.url == const.REPORT_PROXY_URL
    assert view.requires_auth is True
    # Idempotent: a second call must not double-register.
    report_view.async_register_http_views(hass)
    assert len(hass.http.views) == 1


def test_report_view_returns_yaml_text(monkeypatch):
    report_view = _load_report_view()
    hass = _FakeHass()
    view = report_view.ThreadLensReportView(hass)

    class _FakeApi:
        get_report_yaml_text = AsyncMock(return_value="version: 0.1.2\nstatus: ok\n")

    class _FakeCoordinator:
        api = _FakeApi()

    monkeypatch.setattr(report_view, "_first_coordinator", lambda _hass: _FakeCoordinator())

    response = asyncio.run(view.get(None))
    assert response.status == 200
    assert "version: 0.1.2" in response.text
    assert response.content_type == "text/plain"


def test_report_view_handles_missing_coordinator(monkeypatch):
    report_view = _load_report_view()
    hass = _FakeHass()
    view = report_view.ThreadLensReportView(hass)
    monkeypatch.setattr(report_view, "_first_coordinator", lambda _hass: None)
    response = asyncio.run(view.get(None))
    assert response.status == 503

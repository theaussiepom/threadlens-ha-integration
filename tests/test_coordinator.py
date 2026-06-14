"""Coordinator behaviour tests with lightweight Home Assistant stubs."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from support import load_api_module, load_coordinator_module, make_config_entry, make_hass

api = load_api_module()
coordinator_mod = load_coordinator_module()
ThreadLensCannotConnect = api.ThreadLensCannotConnect
ThreadLensCoordinator = coordinator_mod.ThreadLensCoordinator
UpdateFailed = coordinator_mod.UpdateFailed


@pytest.mark.asyncio
async def test_coordinator_marks_unavailable_on_connection_failure() -> None:
    api_mock = MagicMock()
    api_mock.get_version = AsyncMock(side_effect=ThreadLensCannotConnect("down"))
    coordinator = ThreadLensCoordinator(make_hass(), api_mock, make_config_entry())
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_coordinator_returns_connected_data() -> None:
    api_mock = MagicMock()
    api_mock.get_version = AsyncMock(return_value={"tool": "ThreadLens", "version": "0.1.0"})
    api_mock.get_health = AsyncMock(return_value={"overall": {"state": "healthy", "reasons": []}})
    api_mock.get_status = AsyncMock(return_value={"collectors": {"mqtt": {"connected": True}}})
    for getter in (
        "get_otbrs",
        "get_networks",
        "get_matter_servers",
        "get_matter_nodes",
        "get_mdns_services",
        "get_trel_services",
        "get_events",
    ):
        setattr(api_mock, getter, AsyncMock(return_value=[]))
    coordinator = ThreadLensCoordinator(make_hass(), api_mock, make_config_entry())
    data = await coordinator._async_update_data()
    assert data.connected is True
    assert data.version["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_coordinator_collects_dashboard_detail_endpoints() -> None:
    api_mock = MagicMock()
    api_mock.get_version = AsyncMock(return_value={"tool": "ThreadLens", "version": "0.1.2"})
    api_mock.get_health = AsyncMock(return_value={"overall": {"state": "healthy", "reasons": []}})
    api_mock.get_status = AsyncMock(return_value={"collectors": {}})
    api_mock.get_otbrs = AsyncMock(return_value=[{"id": "o1", "name": "OTBR"}])
    api_mock.get_networks = AsyncMock(return_value=[{"ext_pan_id": "AB"}])
    api_mock.get_matter_servers = AsyncMock(return_value=[])
    api_mock.get_matter_nodes = AsyncMock(return_value=[])
    api_mock.get_mdns_services = AsyncMock(return_value=[{"service_type": "_x._tcp"}])
    api_mock.get_trel_services = AsyncMock(return_value=[])
    api_mock.get_events = AsyncMock(return_value=[])
    coordinator = ThreadLensCoordinator(make_hass(), api_mock, make_config_entry())
    data = await coordinator._async_update_data()
    assert data.otbrs == [{"id": "o1", "name": "OTBR"}]
    assert data.mdns_services[0]["service_type"] == "_x._tcp"


@pytest.mark.asyncio
async def test_coordinator_detail_endpoint_failure_is_non_fatal() -> None:
    api_mock = MagicMock()
    api_mock.base_url = "http://tl:8128"
    api_mock.get_version = AsyncMock(return_value={"tool": "ThreadLens", "version": "0.1.2"})
    api_mock.get_health = AsyncMock(return_value={"overall": {"state": "healthy", "reasons": []}})
    api_mock.get_status = AsyncMock(return_value={"collectors": {}})
    api_mock.get_otbrs = AsyncMock(side_effect=api.ThreadLensInvalidResponse("boom"))
    api_mock.get_networks = AsyncMock(return_value=[])
    api_mock.get_matter_servers = AsyncMock(return_value=[])
    api_mock.get_matter_nodes = AsyncMock(return_value=[])
    api_mock.get_mdns_services = AsyncMock(return_value=[])
    api_mock.get_trel_services = AsyncMock(return_value=[])
    api_mock.get_events = AsyncMock(return_value=[])
    coordinator = ThreadLensCoordinator(make_hass(), api_mock, make_config_entry())
    data = await coordinator._async_update_data()
    assert data.connected is True
    assert data.otbrs == []


def test_coordinator_dashboard_payload_disconnected() -> None:
    api_mock = MagicMock()
    api_mock.base_url = "http://tl:8128"
    coordinator = ThreadLensCoordinator(
        make_hass(external_url="https://ha.example.com"),
        api_mock,
        make_config_entry(),
    )
    coordinator.data = None
    payload = coordinator.dashboard_payload()
    assert payload["threadlens"]["api_connected"] is False
    assert payload["report"]["report_url"].endswith("/api/v1/report.yaml")
    assert payload["panel"]["core_url"] == "http://tl:8128"
    assert payload["panel"]["embed_dashboard"] is False
    assert payload["panel"]["show_embedded_dashboard"] is False


def test_coordinator_dashboard_payload_includes_panel_access_when_embed_enabled() -> None:
    api_mock = MagicMock()
    api_mock.base_url = "http://tl:8128"
    coordinator = ThreadLensCoordinator(
        make_hass(external_url="http://ha.example.com"),
        api_mock,
        make_config_entry(options={"embed_dashboard": True}),
    )
    coordinator.data = coordinator_mod.ThreadLensCoordinatorData(
        connected=True,
        version={"tool": "ThreadLens", "version": "0.2.0"},
        health={"overall": {"state": "healthy", "reasons": []}},
        status={"collectors": {}},
        last_update="2026-06-14T12:00:00+00:00",
    )
    payload = coordinator.dashboard_payload()
    assert payload["panel"]["embed_dashboard"] is True
    assert payload["panel"]["show_embedded_dashboard"] is True


def test_coordinator_dashboard_payload_survives_ha_lookup_failure(monkeypatch) -> None:
    api_mock = MagicMock()
    api_mock.base_url = "http://tl:8128"
    coordinator = ThreadLensCoordinator(make_hass(), api_mock, make_config_entry())
    coordinator.data = coordinator_mod.ThreadLensCoordinatorData(
        connected=True,
        version={"tool": "ThreadLens", "version": "0.1.2"},
        health={"overall": {"state": "healthy", "reasons": []}},
        status={"collectors": {}},
        last_update="2026-06-14T12:00:00+00:00",
        matter_nodes=[{"node_id": 1, "available": True}],
    )

    def _boom(_hass):
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(coordinator_mod, "build_matter_node_ha_lookup", _boom)
    payload = coordinator.dashboard_payload()
    assert payload["threadlens"]["api_connected"] is True
    assert payload["matter"]["nodes"][0]["node_id"] == 1


def test_coordinator_dashboard_payload_survives_dashboard_build_failure(monkeypatch) -> None:
    api_mock = MagicMock()
    api_mock.base_url = "http://tl:8128"
    coordinator = ThreadLensCoordinator(make_hass(), api_mock, make_config_entry())
    coordinator.data = coordinator_mod.ThreadLensCoordinatorData(
        connected=True,
        version={"tool": "ThreadLens", "version": "0.1.2"},
        health={"overall": {"state": "healthy", "reasons": []}},
        status={"collectors": {}},
    )

    def _boom(**_kwargs):
        raise ValueError("bad payload")

    monkeypatch.setattr(coordinator_mod, "build_dashboard_payload", _boom)
    payload = coordinator.dashboard_payload()
    assert payload["threadlens"]["api_connected"] is False
    assert "failed to build" in payload["error"]


def test_diagnostics_redacts_url_query_strings() -> None:
    assert "secret" not in api.redact_url_for_diagnostics("http://x:8128/?q=secret")

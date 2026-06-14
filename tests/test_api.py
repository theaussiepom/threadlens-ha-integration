"""ThreadLens API client tests."""

from __future__ import annotations

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from support import load_api_module

api = load_api_module()
ThreadLensApi = api.ThreadLensApi
ThreadLensCannotConnect = api.ThreadLensCannotConnect
ThreadLensInvalidResponse = api.ThreadLensInvalidResponse
build_report_urls = api.build_report_urls
normalize_url = api.normalize_url
redact_url_for_diagnostics = api.redact_url_for_diagnostics
validate_threadlens_api = api.validate_threadlens_api

VERSION_PAYLOAD = {"tool": "ThreadLens", "version": "0.1.0"}
HEALTH_PAYLOAD = {
    "service": "threadlens-server",
    "version": "0.1.0",
    "mode": "server",
    "site": "Home",
    "overall": {"state": "healthy", "reasons": []},
    "environment": {"state": "healthy", "reasons": []},
    "summary": {"events_24h": 3, "warnings_24h": 1},
}
STATUS_PAYLOAD = {
    "status": "running",
    "collectors": {
        "mqtt": {"connected": True},
        "mdns": {"observer_running": True},
    },
    "reports": {"last_generated_at": "2026-06-14T12:00:00+00:00"},
}


def _make_app(*, broken_version: bool = False) -> web.Application:
    app = web.Application()

    async def version(_request: web.Request) -> web.Response:
        payload = {"tool": "Other", "version": "0.0.0"} if broken_version else VERSION_PAYLOAD
        return web.json_response(payload)

    async def health(_request: web.Request) -> web.Response:
        return web.json_response(HEALTH_PAYLOAD)

    async def status(_request: web.Request) -> web.Response:
        return web.json_response(STATUS_PAYLOAD)

    async def list_endpoint(_request: web.Request) -> web.Response:
        return web.json_response([])

    async def report_yaml(_request: web.Request) -> web.Response:
        return web.Response(text="generated_at: now\n", content_type="application/yaml")

    app.router.add_get("/api/v1/version", version)
    app.router.add_get("/api/v1/health", health)
    app.router.add_get("/api/v1/status", status)
    app.router.add_get("/api/v1/report.yaml", report_yaml)
    app.router.add_get("/api/v1/report.json", lambda _r: web.json_response({"generated_at": "now"}))
    for path in (
        "/api/v1/otbrs",
        "/api/v1/networks",
        "/api/v1/matter-servers",
        "/api/v1/matter-nodes",
        "/api/v1/mdns/services",
        "/api/v1/trel/services",
    ):
        app.router.add_get(path, list_endpoint)
    return app


@pytest.fixture
async def api_client() -> tuple[TestClient, str]:
    app = _make_app()
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    base_url = f"http://{server.host}:{server.port}"
    yield client, base_url
    await client.close()


def test_normalize_url_strips_trailing_slash() -> None:
    assert normalize_url("http://threadlens.local:8128/") == "http://threadlens.local:8128"


def test_build_report_urls() -> None:
    urls = build_report_urls("http://threadlens.local:8128/")
    assert urls["yaml"].endswith("/api/v1/report.yaml")
    assert urls["json"].endswith("/api/v1/report.json")


def test_redact_url_for_diagnostics() -> None:
    assert (
        redact_url_for_diagnostics("http://example:8128/path?token=secret#frag")
        == "http://example:8128/path"
    )


@pytest.mark.asyncio
async def test_api_get_version_health_status(api_client: tuple[TestClient, str]) -> None:
    import aiohttp

    _client, base_url = api_client
    async with aiohttp.ClientSession() as session:
        client = ThreadLensApi(session, base_url)
        version = await client.get_version()
        health = await client.get_health()
        status = await client.get_status()
    assert version["version"] == "0.1.0"
    assert health["overall"]["state"] == "healthy"
    assert status["collectors"]["mqtt"]["connected"] is True


@pytest.mark.asyncio
async def test_validate_threadlens_api_success(api_client: tuple[TestClient, str]) -> None:
    import aiohttp

    _client, base_url = api_client
    async with aiohttp.ClientSession() as session:
        version = await validate_threadlens_api(session, base_url)
    assert version["tool"] == "ThreadLens"


@pytest.mark.asyncio
async def test_api_invalid_tool_name_raises() -> None:
    import aiohttp

    app = _make_app(broken_version=True)
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    base_url = f"http://{server.host}:{server.port}"
    try:
        async with aiohttp.ClientSession() as session:
            api_client_obj = ThreadLensApi(session, base_url)
            with pytest.raises(ThreadLensInvalidResponse):
                await api_client_obj.get_version()
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_api_connection_failure_raises() -> None:
    import aiohttp

    async with aiohttp.ClientSession() as session:
        api_client_obj = ThreadLensApi(session, "http://127.0.0.1:1")
        with pytest.raises(ThreadLensCannotConnect):
            await api_client_obj.get_health()


@pytest.mark.asyncio
async def test_api_invalid_json_raises() -> None:
    import aiohttp

    app = web.Application()

    async def bad_json(_request: web.Request) -> web.Response:
        return web.Response(text="not-json", content_type="application/json")

    app.router.add_get("/api/v1/bad", bad_json)
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    base_url = f"http://{server.host}:{server.port}"
    try:
        async with aiohttp.ClientSession() as session:
            api_client_obj = ThreadLensApi(session, base_url)
            with pytest.raises(ThreadLensInvalidResponse):
                await api_client_obj._request("GET", "/api/v1/bad")
    finally:
        await client.close()

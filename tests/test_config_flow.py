"""Config flow validation tests."""

from __future__ import annotations

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from support import load_api_module

api = load_api_module()
ThreadLensCannotConnect = api.ThreadLensCannotConnect
ThreadLensInvalidResponse = api.ThreadLensInvalidResponse
normalize_url = api.normalize_url
validate_threadlens_api = api.validate_threadlens_api

HEALTH_PAYLOAD = {
    "overall": {"state": "healthy", "reasons": []},
    "environment": {"state": "healthy", "reasons": []},
    "summary": {},
}


@pytest.fixture
async def valid_server() -> str:
    app = web.Application()

    async def version(_request: web.Request) -> web.Response:
        return web.json_response({"tool": "ThreadLens", "version": "0.1.0"})

    async def health(_request: web.Request) -> web.Response:
        return web.json_response(HEALTH_PAYLOAD)

    app.router.add_get("/api/v1/version", version)
    app.router.add_get("/api/v1/health", health)
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    base_url = f"http://{server.host}:{server.port}"
    yield base_url
    await client.close()


@pytest.mark.asyncio
async def test_config_flow_accepts_valid_api(valid_server: str) -> None:
    import aiohttp

    async with aiohttp.ClientSession() as session:
        version = await validate_threadlens_api(session, valid_server)
    assert version["version"] == "0.1.0"
    assert normalize_url(f"{valid_server}/") == valid_server


@pytest.mark.asyncio
async def test_config_flow_rejects_connection_failure() -> None:
    import aiohttp

    async with aiohttp.ClientSession() as session:
        with pytest.raises(ThreadLensCannotConnect):
            await validate_threadlens_api(session, "http://127.0.0.1:1")


@pytest.mark.asyncio
async def test_config_flow_rejects_invalid_tool() -> None:
    import aiohttp

    app = web.Application()

    async def version(_request: web.Request) -> web.Response:
        return web.json_response({"tool": "OtherTool", "version": "1.0.0"})

    async def health(_request: web.Request) -> web.Response:
        return web.json_response(HEALTH_PAYLOAD)

    app.router.add_get("/api/v1/version", version)
    app.router.add_get("/api/v1/health", health)
    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    base_url = f"http://{server.host}:{server.port}"
    try:
        async with aiohttp.ClientSession() as session:
            with pytest.raises(ThreadLensInvalidResponse):
                await validate_threadlens_api(session, base_url)
    finally:
        await client.close()

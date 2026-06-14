"""Async client for the ThreadLens Core REST API."""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import aiohttp

from .const import TOOL_NAME

_LOGGER = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10


class ThreadLensApiError(Exception):
    """Base ThreadLens API error."""


class ThreadLensCannotConnect(ThreadLensApiError):
    """Failed to connect to ThreadLens API."""


class ThreadLensInvalidResponse(ThreadLensApiError):
    """ThreadLens API returned an invalid response."""


def normalize_url(url: str) -> str:
    """Strip trailing slashes from the ThreadLens base URL."""
    cleaned = url.strip()
    while cleaned.endswith("/"):
        cleaned = cleaned[:-1]
    return cleaned


def _coerce_list(payload: Any, key: str, label: str) -> list[dict[str, Any]]:
    """Return a list from either a bare list or a ``{count, <key>: [...]}`` object.

    ThreadLens Core wraps collection endpoints as ``{"count": n, "<key>": [...]}``
    but older builds returned bare lists. Accept both for forward/backward
    compatibility.
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    raise ThreadLensInvalidResponse(f"{label} payload must be a list or contain '{key}'")


def build_report_urls(base_url: str) -> dict[str, str]:
    """Return report endpoint URLs for entity attributes."""
    base = normalize_url(base_url)
    return {
        "yaml": f"{base}/api/v1/report.yaml",
        "json": f"{base}/api/v1/report.json",
    }


class ThreadLensApi:
    """Read-only ThreadLens Core API client."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str) -> None:
        self._session = session
        self.base_url = normalize_url(base_url)

    def _url(self, path: str) -> str:
        return urljoin(f"{self.base_url}/", path.lstrip("/"))

    async def _request(
        self,
        method: str,
        path: str,
        *,
        expect_json: bool = True,
    ) -> Any:
        url = self._url(path)
        timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
        try:
            async with self._session.request(method, url, timeout=timeout) as response:
                if response.status >= 400:
                    raise ThreadLensInvalidResponse(f"HTTP {response.status} from {path}")
                if not expect_json:
                    await response.read()
                    return None
                text = await response.text()
                try:
                    return json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ThreadLensInvalidResponse(f"Invalid JSON from {path}") from exc
        except aiohttp.ClientError as exc:
            raise ThreadLensCannotConnect(str(exc)) from exc

    async def get_version(self) -> dict[str, Any]:
        payload = await self._request("GET", "/api/v1/version")
        if not isinstance(payload, dict):
            raise ThreadLensInvalidResponse("Version payload must be an object")
        if payload.get("tool") != TOOL_NAME:
            raise ThreadLensInvalidResponse("Unexpected ThreadLens tool name")
        return payload

    async def get_health(self) -> dict[str, Any]:
        payload = await self._request("GET", "/api/v1/health")
        if not isinstance(payload, dict):
            raise ThreadLensInvalidResponse("Health payload must be an object")
        return payload

    async def get_status(self) -> dict[str, Any]:
        payload = await self._request("GET", "/api/v1/status")
        if not isinstance(payload, dict):
            raise ThreadLensInvalidResponse("Status payload must be an object")
        return payload

    async def get_report_yaml(self) -> None:
        await self._request("GET", "/api/v1/report.yaml", expect_json=False)

    async def get_report_yaml_text(self) -> str:
        """Return the ThreadLens report YAML as text for the HA proxy view."""
        url = self._url("/api/v1/report.yaml")
        timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
        try:
            async with self._session.get(url, timeout=timeout) as response:
                if response.status >= 400:
                    raise ThreadLensInvalidResponse(
                        f"HTTP {response.status} from /api/v1/report.yaml"
                    )
                return await response.text()
        except aiohttp.ClientError as exc:
            raise ThreadLensCannotConnect(str(exc)) from exc

    async def get_events(self, *, window: str = "24h", limit: int = 100) -> list[dict[str, Any]]:
        payload = await self._request("GET", f"/api/v1/events?window={window}&limit={limit}")
        return _coerce_list(payload, "events", "Events")

    async def get_report_json(self) -> dict[str, Any]:
        payload = await self._request("GET", "/api/v1/report.json")
        if not isinstance(payload, dict):
            raise ThreadLensInvalidResponse("Report payload must be an object")
        return payload

    async def get_otbrs(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/api/v1/otbrs")
        return _coerce_list(payload, "otbrs", "OTBR")

    async def get_networks(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/api/v1/networks")
        return _coerce_list(payload, "networks", "Networks")

    async def get_matter_servers(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/api/v1/matter-servers")
        return _coerce_list(payload, "matter_servers", "Matter servers")

    async def get_matter_nodes(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/api/v1/matter-nodes")
        return _coerce_list(payload, "matter_nodes", "Matter nodes")

    async def get_mdns_services(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/api/v1/mdns/services")
        return _coerce_list(payload, "services", "mDNS")

    async def get_trel_services(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/api/v1/trel/services")
        return _coerce_list(payload, "services", "TREL")


async def validate_threadlens_api(session: aiohttp.ClientSession, base_url: str) -> dict[str, Any]:
    """Validate a ThreadLens Core API endpoint during config flow."""
    api = ThreadLensApi(session, base_url)
    version = await api.get_version()
    await api.get_health()
    return version


def redact_url_for_diagnostics(url: str) -> str:
    """Remove query strings and fragments from URLs in diagnostics output."""
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

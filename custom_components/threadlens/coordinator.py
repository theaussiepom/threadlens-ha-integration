"""Data update coordinator for ThreadLens."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    ThreadLensApi,
    ThreadLensApiError,
    ThreadLensCannotConnect,
    build_report_urls,
)
from .const import (
    CONF_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_LIMIT,
    EVENT_WINDOW,
    REPORT_PROXY_URL,
)
from .dashboard import build_dashboard_payload, build_disconnected_payload
from .ha_matter_names import (
    build_matter_node_ha_lookup,
    coerce_matter_node_id,
    resolve_ha_names_for_node,
)
from .panel_embed import build_panel_access, embed_dashboard_enabled

_LOGGER = logging.getLogger(__name__)


@dataclass
class ThreadLensCoordinatorData:
    """Coordinator payload consumed by entities and the dashboard."""

    connected: bool
    version: dict[str, Any] | None
    health: dict[str, Any] | None
    status: dict[str, Any] | None
    last_update: str | None = None
    otbrs: list[dict[str, Any]] = field(default_factory=list)
    networks: list[dict[str, Any]] = field(default_factory=list)
    matter_servers: list[dict[str, Any]] = field(default_factory=list)
    matter_nodes: list[dict[str, Any]] = field(default_factory=list)
    mdns_services: list[dict[str, Any]] = field(default_factory=list)
    trel_services: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)


class ThreadLensCoordinator(DataUpdateCoordinator[ThreadLensCoordinatorData]):
    """Poll ThreadLens Core health, status, and dashboard detail."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: ThreadLensApi,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api = api
        self.entry = entry

    async def _async_update_data(self) -> ThreadLensCoordinatorData:
        try:
            version = await self.api.get_version()
            health = await self.api.get_health()
            status = await self.api.get_status()
        except ThreadLensCannotConnect as exc:
            raise UpdateFailed("Cannot connect to ThreadLens API") from exc
        except ThreadLensApiError as exc:
            raise UpdateFailed(str(exc)) from exc

        # Detail endpoints are best-effort: a transient failure on one of them
        # should not blank out core health entities.
        otbrs = await self._safe_list(self.api.get_otbrs, "otbrs")
        networks = await self._safe_list(self.api.get_networks, "networks")
        matter_servers = await self._safe_list(self.api.get_matter_servers, "matter-servers")
        matter_nodes = await self._safe_list(self.api.get_matter_nodes, "matter-nodes")
        mdns_services = await self._safe_list(self.api.get_mdns_services, "mdns")
        trel_services = await self._safe_list(self.api.get_trel_services, "trel")
        events = await self._safe_events()

        return ThreadLensCoordinatorData(
            connected=True,
            version=version,
            health=health,
            status=status,
            last_update=datetime.now(UTC).isoformat(),
            otbrs=otbrs,
            networks=networks,
            matter_servers=matter_servers,
            matter_nodes=matter_nodes,
            mdns_services=mdns_services,
            trel_services=trel_services,
            events=events,
        )

    async def _safe_events(self) -> list[dict[str, Any]]:
        try:
            return await self.api.get_events(window=EVENT_WINDOW, limit=EVENT_LIMIT)
        except ThreadLensApiError as exc:
            _LOGGER.debug("ThreadLens events endpoint unavailable: %s", exc)
            return []

    async def _safe_list(self, getter, label: str) -> list[dict[str, Any]]:
        try:
            return await getter()
        except ThreadLensApiError as exc:
            _LOGGER.debug("ThreadLens detail endpoint %s unavailable: %s", label, exc)
            return []

    def dashboard_payload(self) -> dict[str, Any]:
        """Build the aggregated dashboard payload for the frontend panel."""
        report_urls = build_report_urls(self.api.base_url)
        report_urls["proxy"] = REPORT_PROXY_URL
        panel_access = build_panel_access(
            self.hass,
            core_url=self.api.base_url,
            embed_dashboard=embed_dashboard_enabled(self.entry.options),
        )
        data = self.data
        try:
            if data is None or not data.connected:
                payload = build_disconnected_payload(
                    version=data.version if data else None,
                    last_update=data.last_update if data else None,
                    report_urls=report_urls,
                )
                payload["panel"] = panel_access
                return payload
            ha_matter_names: dict[int, dict[str, Any]] = {}
            try:
                ha_lookup = build_matter_node_ha_lookup(self.hass)
                for node in data.matter_nodes:
                    if not isinstance(node, dict):
                        continue
                    node_id = coerce_matter_node_id(node.get("node_id"))
                    if node_id is None:
                        continue
                    resolved = resolve_ha_names_for_node(node, ha_lookup)
                    if resolved:
                        ha_matter_names[node_id] = resolved
            except Exception:
                _LOGGER.exception("ThreadLens HA Matter name lookup failed; continuing without it")
            return build_dashboard_payload(
                connected=True,
                last_update=data.last_update,
                version=data.version,
                status=data.status,
                health=data.health,
                otbrs=data.otbrs,
                networks=data.networks,
                matter_servers=data.matter_servers,
                matter_nodes=data.matter_nodes,
                mdns_services=data.mdns_services,
                trel_services=data.trel_services,
                events=data.events,
                event_window=EVENT_WINDOW,
                ha_matter_names=ha_matter_names,
                report_urls=report_urls,
                panel_access=panel_access,
            )
        except Exception:
            _LOGGER.exception("ThreadLens dashboard payload failed")
            payload = build_disconnected_payload(
                version=data.version if data else None,
                last_update=data.last_update if data else None,
                report_urls=report_urls,
                error="ThreadLens dashboard failed to build. Check Home Assistant logs.",
            )
            payload["panel"] = panel_access
            return payload


async def build_coordinator(hass: HomeAssistant, entry: ConfigEntry) -> ThreadLensCoordinator:
    """Create a coordinator for a config entry."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .const import CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL

    verify_ssl = entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    api = ThreadLensApi(session, entry.data[CONF_URL])
    coordinator = ThreadLensCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()
    return coordinator

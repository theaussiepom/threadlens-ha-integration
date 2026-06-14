# Release checklist — ThreadLens HACS Integration

Version target: `0.1.3` (inline HA brand icons; pre-1.0)

## Pre-release

- [ ] ThreadLens Core is running and reachable
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check custom_components tests` passes
- [ ] `ruff format --check custom_components tests` passes
- [ ] `node --check custom_components/threadlens/panel/threadlens-panel.js` passes
- [ ] `manifest.json` version is `0.1.3`
- [ ] `hacs.json` is valid
- [ ] README explains dashboard panel and HACS install path
- [ ] Secret audit clean (no private IPs, credentials, or hostnames)

## HACS install test

1. Add custom repository: `https://github.com/theaussiepom/threadlens-ha-integration` (category: Integration)
2. Install ThreadLens integration from HACS
3. Restart Home Assistant
4. Add integration with ThreadLens API URL, e.g. `http://homeassistant.local:8128`
5. Confirm **ThreadLens** sidebar panel appears
6. Confirm dashboard loads live data via websocket (not MQTT entities)
7. Confirm helper entities appear
8. Press **Refresh** and **Generate report** buttons
9. Stop ThreadLens Core and confirm dashboard shows disconnected state without log spam

## Related repositories

- Core: https://github.com/theaussiepom/threadlens
- HAOS add-on: https://github.com/theaussiepom/threadlens-ha-addon

## Scope reminders

- Dashboard uses ThreadLens REST API through Home Assistant backend
- MQTT Discovery is optional for the dashboard
- This integration does not collect Thread/Matter data itself
- No API authentication in v1 — trusted LAN only
- No SSH, Docker socket, log scraping, commissioning, or mutating operations

## Future work

- Full Home Assistant test harness
- Dashboard Pass 3 visual polish
- In-HA proxied report download

# Release checklist — ThreadLens HACS Integration

Version target: `0.1.14` (HACS-ready hardening; pre-1.0)

## Pre-release

- [ ] ThreadLens Core `0.2.0+` is running and reachable
- [ ] `pytest tests/ -q` passes
- [ ] `ruff check custom_components tests` passes
- [ ] `ruff format --check custom_components tests` passes
- [ ] `node --check custom_components/threadlens/panel/threadlens-panel.js` passes
- [ ] HACS Action workflow passes
- [ ] Hassfest workflow passes
- [ ] `manifest.json` version is `0.1.14`
- [ ] `hacs.json` is valid
- [ ] README explains native companion panel, optional iframe, Core, and HAOS paths
- [ ] Secret audit clean (no private IPs, credentials, or hostnames in repo)
- [ ] Screenshots captured (see README placeholders) — optional for first public release

## HACS install test

1. Add custom repository: `https://github.com/theaussiepom/threadlens-ha-integration` (category: Integration)
2. Install ThreadLens integration from HACS
3. Restart Home Assistant
4. Add integration with ThreadLens API URL, e.g. `http://homeassistant.local:8128`
5. Confirm **ThreadLens** sidebar panel appears with native companion content
6. Confirm **Open full ThreadLens dashboard** opens Core in a new tab
7. Confirm optional iframe remains off by default
8. Confirm helper entities appear
9. Press **Refresh** and **Generate report** buttons
10. Stop ThreadLens Core and confirm repair issue + disconnected panel state

## Release notes draft (do not publish until approved)

```markdown
## ThreadLens HACS Integration 0.1.14

- Native companion/status sidebar panel remains the default experience
- Optional embedded Core dashboard iframe (`embed_dashboard`, default off) with mixed-content safety
- HACS Action and Hassfest validation in CI
- Repair issue when Core API is unreachable
- Works with ThreadLens Core 0.2.0+; no reverse proxy required for default HACS value
- HAOS add-on Ingress is the embedded full-dashboard path for HAOS users (live validation may still be pending)
```

## Related repositories

- Core: https://github.com/theaussiepom/threadlens
- HAOS add-on: https://github.com/theaussiepom/threadlens-ha-addon

## Scope reminders

- HACS provides companion panel, entities, diagnostics, and access — not the canonical full dashboard
- Core owns the canonical dashboard at `/`
- Optional iframe is convenience only; not required
- MQTT Discovery is optional for automations
- No API authentication in v1 — trusted LAN only
- No SSH, Docker socket, log scraping, commissioning, or mutating operations

## Remaining release tasks

- Capture screenshots listed in README (`docs/screenshots/`)
- Confirm HAOS add-on Ingress live validation before recommending HAOS embedded path broadly

# Contributing

Thank you for contributing to the ThreadLens Home Assistant integration.

## Before you start

- ThreadLens Core must already be running for manual testing. See [threadlens](https://github.com/theaussiepom/threadlens).
- This repo is **pre-1.0**. APIs and dashboard layout may change.
- Do not commit secrets, private LAN addresses, or live credentials.

## Development setup

```bash
git clone https://github.com/theaussiepom/threadlens-ha-integration.git
cd threadlens-ha-integration
python3 -m venv .venv
source .venv/bin/activate
pip install aiohttp pytest pytest-asyncio ruff
```

## Running checks

```bash
ruff check custom_components tests
ruff format --check custom_components tests
pytest tests/ -q
node --check custom_components/threadlens/panel/threadlens-panel.js
```

## Pull requests

1. Branch from `main` (do not push directly to `main`).
2. Keep changes focused — dashboard redesigns and core collector changes belong in separate passes.
3. Add or update tests for behaviour changes.
4. Ensure CI passes before requesting review.
5. Update README if install, configuration, or dashboard behaviour changes.

## Scope boundaries

**In scope for this repo**

- Home Assistant config flow, entities, diagnostics
- Dashboard panel and backend websocket payload
- HACS packaging and CI

**Out of scope**

- ThreadLens Core collectors, health engine, or MQTT publishing
- Device commissioning or Thread/Matter/OTBR mutation
- Lovelace card ecosystems (Mushroom, card-mod, etc.)

## Code style

- Python 3.12+, `ruff` for lint and format
- Match existing module layout under `custom_components/threadlens/`
- Panel JS is dependency-free; avoid external CDN imports

## Questions

Open a [GitHub issue](https://github.com/theaussiepom/threadlens-ha-integration/issues) for bugs or feature requests.

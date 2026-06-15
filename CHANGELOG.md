# Changelog

All notable changes to the ThreadLens Home Assistant integration are documented here.

## [0.1.21] - 2026-06-15

### Changed

- Companion panel and dashboard copy aligned with Core 0.2.13+: `Last read check failed` instead of `Read probe issue`
- Panel stat labels use `Failed read checks` for clearer parity with the Core Devices view

### Notes

- Recommended ThreadLens Core: **0.2.14+** (iframe CSP) with router dashboard **0.2.11+**

## [0.1.20] - 2026-06-15

### Added

- [docs/ha-matter-device-names.md](docs/ha-matter-device-names.md) — how this integration supplies HA device names to Core

### Fixed

- Matter name push to Core now uses serial fallback matching (same as companion panel), not node id alone

### Documentation

- README and RELEASE checklist: HACS integration supplies HA Matter device names to Core

## [0.1.19] - 2026-06-15

### Added
- Push Home Assistant Matter device names to ThreadLens Core on startup and registry updates
- Read-probe classification and `classification_reason` parity with Core dashboard
- Per-node read probe block in the HACS dashboard payload

### Changed
- Coordinator enriches matter nodes with per-node health reasons from Core `/health`
- Companion panel auto-embed now re-evaluates when `core_url` is set (`_maybeAutoEmbed`, ZigbeeLens parity)
- Incident summary uses read-probe-specific detail when instability is probe-only

### Requirements
- ThreadLens Core **0.2.3+** for HA Matter name sync API

## [0.1.18] - 2026-06-15

### Fixed
- Embedded Core dashboard panel now uses Home Assistant's native `ha-menu-button` above the iframe so the main HA sidebar can be reopened when hidden

### Changed
- Embedded layout uses flex column sizing instead of `100vh` height hacks
- Panel registration re-registers stale panels missing `core_url` or using `embed_iframe=True`
- Panel unregisters before config entry data is removed on unload

## [0.1.17] - 2026-06-15

### Added
- Native companion panel Matter read probe summary (issue count, per-node read reachability notes)
- Diagnostics fields for read probe and ping probe summaries from Core
- Global `matter_read_probe_issues` sensor and `matter_read_probe_issues_present` binary sensor

### Changed
- Health reason labels aligned with Core safe read probe wording

## [0.1.16] - 2026-06-15

### Added
- ZigbeeLens-style lightweight companion panel with redacted `threadlens/panel_summary` websocket
- Config flow options for Core URL, verify SSL, and sidebar panel toggle
- Auto-embed full Core dashboard when HA and Core use the same protocol (HTTP+HTTP or HTTPS+HTTPS)

### Changed
- Panel registration now passes `core_url` in config and sets `embed_iframe=False` (fixes sidebar disappearing with HTTPS FQDN)
- Replaced heavy native dashboard clone with calm summary/launcher surface matching ZigbeeLens
- Options flow simplified: removed `embed_dashboard` toggle in favour of protocol-based auto-embed

## [0.1.15] - 2026-06-15

### Added
- README screenshots (config flow, device page, companion panel, Core dashboard, node detail)

## [0.1.14] - 2026-06-14

### Added
- HACS Action validation workflow
- Hassfest validation workflow
- Repair issue when ThreadLens Core API is unreachable
- Diagnostics fields for `embed_dashboard`, `last_update`

### Changed
- README and release docs polished for public/HACS readiness
- Clarified native companion panel vs optional iframe vs Core/HAOS paths

## [0.1.13] - 2026-06-14

### Added
- Optional `embed_dashboard` integration option (default `false`)
- Mixed-content safety for optional Core dashboard iframe
- Prominent **Open full ThreadLens dashboard** button in sidebar panel

## [0.1.12] - 2026-06-14

### Changed
- Simplified dashboard health UI
- Restored Matter nodes without Home Assistant entity matches

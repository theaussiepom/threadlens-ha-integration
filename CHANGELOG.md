# Changelog

All notable changes to the ThreadLens Home Assistant integration are documented here.

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

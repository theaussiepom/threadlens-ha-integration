# Changelog

All notable changes to the ThreadLens Home Assistant integration are documented here.

## [0.1.14] - Unreleased

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

"""Manifest and HACS metadata validation."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = REPO_ROOT / "custom_components" / "threadlens"


def test_manifest_parses_and_has_expected_fields() -> None:
    manifest = json.loads((INTEGRATION_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["domain"] == "threadlens"
    assert manifest["name"] == "ThreadLens"
    assert manifest["config_flow"] is True
    assert manifest["version"] == "0.1.11"
    assert manifest["integration_type"] == "hub"
    assert manifest["iot_class"] == "local_polling"
    assert "aiohttp" in manifest["requirements"][0]


def test_hacs_branding_assets_exist() -> None:
    # Repo root icons are for GitHub/HACS listing; HA serves inline brand assets
    # from custom_components/threadlens/brand/ (HA 2026.3+ brands proxy).
    assert (REPO_ROOT / "icon.png").is_file()
    assert (REPO_ROOT / "logo.png").is_file()
    assert (INTEGRATION_DIR / "brand" / "icon.png").is_file()
    assert (INTEGRATION_DIR / "brand" / "logo.png").is_file()
    assert (INTEGRATION_DIR / "brand" / "icon@2x.png").is_file()
    assert (INTEGRATION_DIR / "brand" / "logo@2x.png").is_file()
    assert (REPO_ROOT / "docs" / "threadlens-icon.svg").is_file()
    assert (REPO_ROOT / "docs" / "threadlens-logo.svg").is_file()


def test_sidebar_icon_is_access_point_network() -> None:
    const = (INTEGRATION_DIR / "const.py").read_text(encoding="utf-8")
    assert 'PANEL_ICON = "mdi:access-point-network"' in const


def test_hacs_json_parses() -> None:
    hacs = json.loads((REPO_ROOT / "hacs.json").read_text(encoding="utf-8"))
    assert hacs["name"] == "ThreadLens"
    assert hacs["render_readme"] is True
    assert "homeassistant" in hacs
    assert hacs["homeassistant"] == "2026.3.0"


def test_translations_include_config_flow_errors() -> None:
    translations = json.loads(
        (INTEGRATION_DIR / "translations" / "en.json").read_text(encoding="utf-8")
    )
    assert "cannot_connect" in translations["config"]["error"]
    assert "invalid_response" in translations["config"]["error"]
    assert translations["entity"]["sensor"]["api_health"]["name"]

"""Static packaging tests for the bundled ThreadLens dashboard panel."""

from __future__ import annotations

import json
from pathlib import Path

from support import load_submodule

REPO_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = REPO_ROOT / "custom_components" / "threadlens"
PANEL_DIR = INTEGRATION_DIR / "panel"


def test_panel_js_is_packaged():
    panel_js = PANEL_DIR / "threadlens-panel.js"
    assert panel_js.is_file(), "Bundled panel JS must ship with the integration"
    contents = panel_js.read_text(encoding="utf-8")
    assert 'customElements.define("threadlens-panel"' in contents
    assert "threadlens/dashboard" in contents, "Panel must use the backend websocket command"


def test_panel_has_no_external_network_calls():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "http://" not in contents.replace("rgba(0,0,0", "")
    assert "https://" not in contents
    assert "import " not in contents and "require(" not in contents


def test_const_static_url_matches_filename():
    const = load_submodule("const")
    assert const.PANEL_FILENAME == "threadlens-panel.js"
    assert const.PANEL_STATIC_URL.endswith(const.PANEL_FILENAME)
    assert const.PANEL_WEBCOMPONENT == "threadlens-panel"
    assert const.WS_TYPE_DASHBOARD == "threadlens/dashboard"


def test_panel_semantics_hide_reconciled_mismatch_banner():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "JSON:API reports disabled, legacy /node reports active" not in contents
    assert "mismatch_reconciled" in contents
    assert "Effective state" in contents
    assert "Endpoint details" in contents
    assert "color-mix(in srgb" in contents


def test_manifest_declares_panel_dependencies():
    manifest = json.loads((INTEGRATION_DIR / "manifest.json").read_text(encoding="utf-8"))
    for dependency in ("http", "websocket_api", "frontend", "panel_custom"):
        assert dependency in manifest["dependencies"], f"Missing dependency: {dependency}"


def test_panel_opens_report_via_signed_proxy_in_new_tab():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "auth/sign_path" in contents, "Report YAML must open via an authenticated signed path"
    assert "report_proxy_url" in contents
    assert "window.open(" in contents
    assert '"_blank"' in contents


def test_panel_has_node_health_and_incident_view():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "Network incident summary" in contents
    assert "Matter node health" in contents
    assert "data-node-id" in contents
    assert "What this suggests" in contents
    assert "mdi:access-point-network" in contents
    assert "View" in contents
    assert "hard-refresh" in contents


def test_panel_shows_actionable_errors_instead_of_endless_loading():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "ThreadLens panel unavailable" in contents
    assert "ThreadLens API unavailable" in contents
    assert "Invalid ThreadLens dashboard response" in contents


def test_panel_collates_home_assistant_names():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "Home Assistant names" in contents
    assert "_haNamesSection" in contents
    assert "ha_entity_ids" in contents

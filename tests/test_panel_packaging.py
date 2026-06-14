"""Static packaging tests for the bundled ThreadLens dashboard panel."""

from __future__ import annotations

import json
from pathlib import Path

from support import load_submodule

REPO_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = REPO_ROOT / "custom_components" / "threadlens"
PANEL_DIR = INTEGRATION_DIR / "panel"


def test_panel_js_has_no_syntax_errors():
    import subprocess

    panel_js = PANEL_DIR / "threadlens-panel.js"
    subprocess.run(["node", "--check", str(panel_js)], check=True)


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


def test_panel_has_node_health_without_ha_entities():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "Network incident summary" in contents
    assert "Matter node health" in contents
    assert "data-node-id" in contents
    assert "What this suggests" in contents
    assert "Overall health" in contents
    assert "mdi:access-point-network" in contents
    assert "View" in contents
    assert "offline_episodes_24h" in contents
    assert "_availabilityLine" in contents


def test_panel_does_not_surface_ha_entity_lists():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "Home Assistant names" not in contents
    assert "_haNamesSection" not in contents
    assert "_formatHaEntities" not in contents
    assert "ha_entity_ids" not in contents
    assert "HA device:" not in contents
    assert "Home Assistant entities" not in contents


def test_panel_health_section_uses_labels_only():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "ThreadLens Core reports" not in contents
    assert "informational_reasons" not in contents
    assert "tl-chip-info" not in contents
    assert "All reason codes" not in contents


def test_panel_has_optional_embedded_dashboard_support():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "Open full ThreadLens dashboard" in contents
    assert "_companionAccessSection" in contents
    assert "show_embedded_dashboard" in contents
    assert "tl-dashboard-iframe" in contents
    assert 'rel="noopener noreferrer"' in contents
    assert "HTTP dashboards inside HTTPS Home Assistant pages" not in contents


def test_panel_keeps_native_companion_content_without_iframe():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "Network incident summary" in contents
    assert "Full dashboard access" in contents
    assert "Optional embedded dashboard is off" in contents


def test_panel_shows_actionable_errors_instead_of_endless_loading():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "ThreadLens panel unavailable" in contents
    assert "ThreadLens API unavailable" in contents
    assert "Invalid ThreadLens dashboard response" in contents

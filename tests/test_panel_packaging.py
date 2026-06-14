"""Static packaging tests for the bundled ThreadLens companion panel."""

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
    assert "threadlens/panel_summary" in contents, "Panel must use the summary websocket command"


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
    assert const.WS_TYPE_PANEL_SUMMARY == "threadlens/panel_summary"


def test_manifest_declares_panel_dependencies():
    manifest = json.loads((INTEGRATION_DIR / "manifest.json").read_text(encoding="utf-8"))
    for dependency in ("http", "websocket_api", "frontend", "panel_custom"):
        assert dependency in manifest["dependencies"], f"Missing dependency: {dependency}"


def test_panel_registers_with_core_url_config_and_embed_iframe_false():
    panel_py = (INTEGRATION_DIR / "panel.py").read_text(encoding="utf-8")
    assert 'config={"core_url": core_url}' in panel_py
    assert "embed_iframe=False" in panel_py
    assert "PANEL_STATE_KEY" in panel_py
    assert 'custom_meta.get("embed_iframe")' in panel_py


def test_panel_uses_zigbeelens_style_companion_views():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "Home Assistant companion panel" in contents
    assert "Current finding" in contents
    assert "Integration health" in contents
    assert "Open full ThreadLens dashboard" in contents
    assert "Try Embedded View" in contents
    assert "embed-frame" in contents
    assert "embed-layout" in contents
    assert "<ha-menu-button" in contents
    assert 'rel="noopener noreferrer"' in contents


def test_panel_auto_embeds_when_same_protocol():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "canEmbedDashboard" in contents
    assert 'this._view = "embedded"' in contents


def test_panel_does_not_use_full_dashboard_websocket():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "threadlens/dashboard" not in contents


def test_panel_does_not_surface_full_native_dashboard_sections():
    contents = (PANEL_DIR / "threadlens-panel.js").read_text(encoding="utf-8")
    assert "Network incident summary" not in contents
    assert "Matter node health" not in contents
    assert "Endpoint details" not in contents

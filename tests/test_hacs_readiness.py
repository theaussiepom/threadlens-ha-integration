"""Documentation and metadata readiness tests for HACS public release."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = REPO_ROOT / "custom_components" / "threadlens"


def test_readme_explains_install_paths() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "docker" in readme and "core" in readme
    assert "hacs" in readme
    assert "haos add-on" in readme or "haos" in readme
    assert "native companion" in readme
    assert "open full threadlens dashboard" in readme
    assert "auto-embed" in readme or "optional iframe" in readme or "try embedded view" in readme
    assert "reverse proxy" in readme
    assert "not required" in readme or "optional" in readme


def test_readme_does_not_claim_iframe_first_or_haos_validated() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "iframe-first" not in readme
    assert "iframe is required" not in readme
    assert "reverse proxy is required" not in readme
    assert "haos ingress validation has passed" not in readme
    assert "live haos ingress validation may still be pending" in readme


def test_hacs_and_hassfest_workflows_exist() -> None:
    assert (REPO_ROOT / ".github/workflows/hacs.yml").is_file()
    assert (REPO_ROOT / ".github/workflows/hassfest.yml").is_file()
    hacs = (REPO_ROOT / ".github/workflows/hacs.yml").read_text(encoding="utf-8")
    hassfest = (REPO_ROOT / ".github/workflows/hassfest.yml").read_text(encoding="utf-8")
    assert "hacs/action" in hacs
    assert "home-assistant/actions/hassfest" in hassfest


def test_translations_include_options_and_repairs() -> None:
    translations = json.loads(
        (INTEGRATION_DIR / "translations" / "en.json").read_text(encoding="utf-8")
    )
    assert "panel_enabled" in translations["options"]["step"]["init"]["data"]
    assert "verify_ssl" in translations["options"]["step"]["init"]["data"]
    assert "api_disconnected" in translations["issues"]


def test_embed_dashboard_defaults_false_in_code() -> None:
    panel_embed = (INTEGRATION_DIR / "panel_embed.py").read_text(encoding="utf-8")
    assert "options.get(CONF_EMBED_DASHBOARD, False)" in panel_embed

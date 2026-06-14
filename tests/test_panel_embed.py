"""Tests for optional dashboard iframe embedding safety."""

from __future__ import annotations

from support import load_submodule, make_hass

panel_embed = load_submodule("panel_embed")
evaluate_iframe_embed_safety = panel_embed.evaluate_iframe_embed_safety
build_panel_access = panel_embed.build_panel_access
embed_dashboard_enabled = panel_embed.embed_dashboard_enabled


def test_embed_dashboard_defaults_to_false() -> None:
    assert embed_dashboard_enabled({}) is False
    assert embed_dashboard_enabled({"embed_dashboard": False}) is False


def test_embed_dashboard_option_can_be_enabled() -> None:
    assert embed_dashboard_enabled({"embed_dashboard": True}) is True


def test_https_ha_with_http_core_blocks_iframe() -> None:
    allowed, reason = evaluate_iframe_embed_safety(
        "https://homeassistant.local:8123",
        "http://192.168.100.4:8128",
    )
    assert allowed is False
    assert reason is not None
    assert "HTTP dashboards inside HTTPS Home Assistant pages" in reason


def test_https_core_can_embed_when_enabled() -> None:
    allowed, reason = evaluate_iframe_embed_safety(
        "https://homeassistant.local:8123",
        "https://threadlens.example.com",
    )
    assert allowed is True
    assert reason is None


def test_http_ha_with_http_core_can_embed_when_enabled() -> None:
    allowed, reason = evaluate_iframe_embed_safety(
        "http://homeassistant.local:8123",
        "http://192.168.100.4:8128",
    )
    assert allowed is True
    assert reason is None


def test_uncertain_ha_scheme_prefers_native_panel() -> None:
    allowed, reason = evaluate_iframe_embed_safety("", "http://192.168.100.4:8128")
    assert allowed is False
    assert reason is not None


def test_build_panel_access_hides_iframe_when_disabled() -> None:
    hass = make_hass(external_url="http://homeassistant.local:8123")
    panel = build_panel_access(
        hass,
        core_url="http://192.168.100.4:8128",
        embed_dashboard=False,
    )
    assert panel["core_url"] == "http://192.168.100.4:8128"
    assert panel["embed_dashboard"] is False
    assert panel["show_embedded_dashboard"] is False


def test_build_panel_access_shows_iframe_when_enabled_and_safe() -> None:
    hass = make_hass(external_url="http://homeassistant.local:8123")
    panel = build_panel_access(
        hass,
        core_url="http://192.168.100.4:8128",
        embed_dashboard=True,
    )
    assert panel["show_embedded_dashboard"] is True
    assert panel["iframe_embed_allowed"] is True


def test_build_panel_access_blocks_iframe_when_unsafe_even_if_enabled() -> None:
    hass = make_hass(external_url="https://homeassistant.local:8123")
    panel = build_panel_access(
        hass,
        core_url="http://192.168.100.4:8128",
        embed_dashboard=True,
    )
    assert panel["embed_dashboard"] is True
    assert panel["show_embedded_dashboard"] is False
    assert panel["iframe_embed_allowed"] is False
    assert panel["iframe_blocked_reason"] is not None

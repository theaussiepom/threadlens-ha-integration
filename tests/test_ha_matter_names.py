"""Tests for Home Assistant Matter name resolution."""

from __future__ import annotations

from types import SimpleNamespace

from support import install_homeassistant_stubs, load_dashboard_module, load_submodule

install_homeassistant_stubs()
ha_matter_names = load_submodule("ha_matter_names")
dashboard = load_dashboard_module()
build_dashboard_payload = dashboard.build_dashboard_payload

VERSION = {"tool": "ThreadLens", "version": "0.1.2"}
STATUS = {"collectors": {"mdns": {"observation_degraded": False}}, "reports": {}}
HEALTH = {
    "overall": {"state": "healthy", "reasons": []},
    "environment": {"state": "healthy", "reasons": []},
    "mdns": {"state": "healthy", "reasons": []},
    "trel": {"state": "healthy", "reasons": []},
}


def _device(**kwargs):
    defaults = {
        "id": "dev1",
        "identifiers": {("matter", "deviceid_ABCD1234-0000000000000011-MatterNodeDevice")},
        "name": "Study Blind 1",
        "name_by_user": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _entity(**kwargs):
    defaults = {
        "device_id": "dev1",
        "entity_id": "cover.study_blind_1",
        "domain": "cover",
        "name": "Study Blind 1",
        "original_name": "Study Blind 1",
        "disabled_by": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_parse_matter_node_id_from_device_identifier():
    node_id = ha_matter_names.parse_matter_node_id(
        {("matter", "deviceid_ABCD1234-0000000000000011-MatterNodeDevice")}
    )
    assert node_id == 17


def test_parse_matter_node_id_handles_missing_identifiers():
    assert ha_matter_names.parse_matter_node_id(None) is None
    assert ha_matter_names.parse_matter_node_id([]) is None


def test_build_lookup_maps_device_and_cover_entity():
    lookup = ha_matter_names.build_matter_ha_lookup_from_registry(
        [_device()],
        [_entity()],
    )
    match = lookup["by_node_id"][17]
    assert match["ha_device_name"] == "Study Blind 1"
    assert match["ha_entity_names"] == ["Study Blind 1"]
    assert match["ha_cover_entity_ids"] == ["cover.study_blind_1"]


def test_resolve_by_serial_when_node_id_missing():
    lookup = ha_matter_names.build_matter_ha_lookup_from_registry(
        [_device(identifiers={("matter", "serial_SCM-MT-2507-0099")})],
        [_entity()],
    )
    resolved = ha_matter_names.resolve_ha_names_for_node(
        {"node_id": 99, "serial": "SCM-MT-2507-0099"},
        lookup,
    )
    assert resolved["ha_device_name"] == "Study Blind 1"


def test_dashboard_uses_ha_device_name_for_display():
    payload = build_dashboard_payload(
        connected=True,
        version=VERSION,
        status=STATUS,
        health=HEALTH,
        matter_servers=[{"id": "study_matter", "connected": True}],
        matter_nodes=[
            {
                "node_id": 17,
                "server_id": "study_matter",
                "friendly_name": "SCM-MT-2507-0099",
                "serial": "SCM-MT-2507-0099",
                "available": True,
            }
        ],
        ha_matter_names={
            17: {
                "ha_device_name": "Study Blind 1",
                "ha_entity_names": ["Study Blind 1"],
                "ha_entity_ids": ["cover.study_blind_1"],
                "ha_cover_entity_ids": ["cover.study_blind_1"],
            }
        },
    )
    node = payload["matter"]["nodes"][0]
    assert node["name"] == "Study Blind 1"
    assert node["matter_name"] == "SCM-MT-2507-0099"
    assert node["ha_device_name"] == "Study Blind 1"

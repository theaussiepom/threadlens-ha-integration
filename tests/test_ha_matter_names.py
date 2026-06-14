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


def test_parse_matter_node_id_ignores_three_element_identifiers():
    node_id = ha_matter_names.parse_matter_node_id(
        [
            ["homekit", "01KAMS87J7F0DVC3Q7E961B2R5", "homekit.bridge"],
            ["matter", "deviceid_11C2DEB7A4D8CDBA-0000000000000011-MatterNodeDevice"],
        ]
    )
    assert node_id == 17


def test_build_lookup_survives_homekit_bridge_identifiers():
    lookup = ha_matter_names.build_matter_ha_lookup_from_registry(
        [
            _device(
                name="HomeKit Bridge",
                identifiers=[
                    ["homekit", "01KAMS87J7F0DVC3Q7E961B2R5", "homekit.bridge"],
                ],
            ),
            _device(
                identifiers={
                    ("matter", "deviceid_11C2DEB7A4D8CDBA-0000000000000011-MatterNodeDevice"),
                    ("matter", "serial_SCM-MT-2507-0099"),
                },
                name="Study Blind",
            ),
        ],
        [_entity(entity_id="cover.blind_study", name="Study Blind")],
    )
    match = lookup["by_node_id"][17]
    assert match["ha_device_name"] == "Study Blind"
    assert "cover.blind_study" in match["ha_entity_ids"]


def test_parse_matter_node_id_from_device_identifier():
    node_id = ha_matter_names.parse_matter_node_id(
        {("matter", "deviceid_ABCD1234-0000000000000011-MatterNodeDevice")}
    )
    assert node_id == 17


def test_parse_matter_node_id_handles_missing_identifiers():
    assert ha_matter_names.parse_matter_node_id(None) is None
    assert ha_matter_names.parse_matter_node_id([]) is None


def test_coerce_matter_node_id_normalises_string_and_hex_values():
    assert ha_matter_names.coerce_matter_node_id(17) == 17
    assert ha_matter_names.coerce_matter_node_id("17") == 17
    assert ha_matter_names.coerce_matter_node_id("0x11") == 17
    assert ha_matter_names.coerce_matter_node_id("0000000000000011") == 17


def test_parse_node_id_from_matter_unique_id():
    unique_id = "ABCD1234-0000000000000011-MatterNodeDevice-1-cover-4-768"
    assert ha_matter_names.parse_node_id_from_matter_unique_id(unique_id) == 17


def test_build_lookup_maps_matter_entity_unique_id_without_device_link():
    lookup = ha_matter_names.build_matter_ha_lookup_from_registry(
        [],
        [
            _entity(
                device_id=None,
                platform="matter",
                unique_id="ABCD1234-0000000000000011-MatterNodeDevice-1-cover-4-768",
            )
        ],
    )
    match = lookup["by_node_id"][17]
    assert match["ha_entity_names"] == ["Study Blind 1"]
    assert match["ha_entity_ids"] == ["cover.study_blind_1"]


def test_build_lookup_maps_cover_entity_by_unique_id_when_platform_missing():
    lookup = ha_matter_names.build_matter_ha_lookup_from_registry(
        [],
        [
            _entity(
                device_id=None,
                platform=None,
                domain="cover",
                name=None,
                original_name=None,
                unique_id="ABCD1234-000000000000001D-MatterNodeDevice-1-cover-4-768",
            )
        ],
    )
    match = lookup["by_node_id"][29]
    assert match["ha_entity_names"] == ["cover.study_blind_1"]
    assert match["ha_entity_ids"] == ["cover.study_blind_1"]


def test_build_lookup_uses_device_serial_number_field():
    lookup = ha_matter_names.build_matter_ha_lookup_from_registry(
        [
            _device(
                identifiers=set(),
                serial_number="scm-mt-2408-0753",
                name="Living Room Blind",
            )
        ],
        [_entity()],
    )
    resolved = ha_matter_names.resolve_ha_names_for_node(
        {"node_id": 29, "serial": "SCM-MT-2408-0753"},
        lookup,
    )
    assert resolved["ha_device_name"] == "Living Room Blind"


def test_resolve_matches_serial_from_friendly_name():
    lookup = ha_matter_names.build_matter_ha_lookup_from_registry(
        [_device(identifiers={("matter", "serial_SCM-MT-2408-0753")}, name="Living Room Blind")],
        [_entity()],
    )
    resolved = ha_matter_names.resolve_ha_names_for_node(
        {"node_id": 99, "friendly_name": "SCM-MT-2408-0753"},
        lookup,
    )
    assert resolved["ha_device_name"] == "Living Room Blind"


def test_resolve_matches_string_node_id_from_threadlens():
    lookup = ha_matter_names.build_matter_ha_lookup_from_registry(
        [_device()],
        [_entity()],
    )
    resolved = ha_matter_names.resolve_ha_names_for_node({"node_id": "17"}, lookup)
    assert resolved["ha_device_name"] == "Study Blind 1"


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


def test_dashboard_reports_ha_name_match_counts():
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
                "available": True,
            },
            {
                "node_id": 18,
                "server_id": "study_matter",
                "friendly_name": "SCM-MT-2507-0100",
                "available": True,
            },
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
    assert payload["matter"]["ha_names_matched"] == 1
    assert payload["matter"]["ha_names_unmatched"] == 1

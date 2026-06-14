"""Repair issue tests."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock

from support import install_homeassistant_stubs, load_submodule, make_config_entry


def _install_issue_registry_stub() -> None:
    if "homeassistant.helpers.issue_registry" in sys.modules:
        return

    issue_registry = ModuleType("homeassistant.helpers.issue_registry")

    class IssueSeverity:
        WARNING = "warning"

    created: list[tuple] = []
    deleted: list[tuple] = []

    def async_create_issue(hass, domain, issue_id, **kwargs):
        created.append((domain, issue_id, kwargs))

    def async_delete_issue(hass, domain, issue_id):
        deleted.append((domain, issue_id))

    issue_registry.IssueSeverity = IssueSeverity
    issue_registry.async_create_issue = async_create_issue
    issue_registry.async_delete_issue = async_delete_issue
    issue_registry._created = created
    issue_registry._deleted = deleted

    helpers = sys.modules["homeassistant.helpers"]
    helpers.issue_registry = issue_registry
    sys.modules["homeassistant.helpers.issue_registry"] = issue_registry


def _load_repairs():
    install_homeassistant_stubs()
    _install_issue_registry_stub()
    load_submodule("const")
    return load_submodule("repairs")


def test_repairs_create_issue_when_disconnected() -> None:
    repairs = _load_repairs()
    ir = sys.modules["homeassistant.helpers.issue_registry"]
    ir._created.clear()
    ir._deleted.clear()
    hass = MagicMock()
    entry = make_config_entry(data={"url": "http://tl:8128"})
    entry.entry_id = "test-entry-id"

    repairs.async_update_connection_repairs(hass, entry, connected=False)

    assert len(ir._created) == 1
    domain, issue_id, kwargs = ir._created[0]
    assert domain == "threadlens"
    assert issue_id == "api_disconnected_test-entry-id"
    assert kwargs["translation_key"] == "api_disconnected"
    assert kwargs["translation_placeholders"]["url"] == "http://tl:8128"


def test_repairs_delete_issue_when_connected() -> None:
    repairs = _load_repairs()
    ir = sys.modules["homeassistant.helpers.issue_registry"]
    ir._created.clear()
    ir._deleted.clear()
    hass = MagicMock()
    entry = make_config_entry()

    repairs.async_update_connection_repairs(hass, entry, connected=True)

    assert ir._created == []
    assert len(ir._deleted) == 1

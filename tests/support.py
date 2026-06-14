"""Test helpers for loading integration modules without Home Assistant installed."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

INTEGRATION_DIR = Path(__file__).resolve().parents[1] / "custom_components" / "threadlens"


def install_homeassistant_stubs() -> None:
    """Install minimal Home Assistant module stubs for coordinator tests."""
    if "homeassistant.helpers.update_coordinator" in sys.modules:
        return

    class UpdateFailed(Exception):
        pass

    class DataUpdateCoordinator:
        def __init__(self, hass, logger, name, update_interval=None):
            self.hass = hass
            self.data = None

        def __class_getitem__(cls, _item):
            return cls

    ha = ModuleType("homeassistant")
    core = ModuleType("homeassistant.core")
    core.HomeAssistant = object
    helpers = ModuleType("homeassistant.helpers")
    update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")
    update_coordinator.UpdateFailed = UpdateFailed
    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    helpers.update_coordinator = update_coordinator
    ha.core = core
    ha.helpers = helpers
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator


def _ensure_threadlens_package() -> ModuleType:
    if "threadlens" not in sys.modules:
        package = ModuleType("threadlens")
        package.__path__ = [str(INTEGRATION_DIR)]
        sys.modules["threadlens"] = package
    return sys.modules["threadlens"]


def load_submodule(name: str):
    """Load `threadlens.<name>` from the integration directory."""
    _ensure_threadlens_package()
    full_name = f"threadlens.{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    path = INTEGRATION_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(full_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


def load_api_module():
    load_submodule("const")
    return load_submodule("api")


def load_dashboard_module():
    """Load the HA-free dashboard aggregation module."""
    return load_submodule("dashboard")


def load_coordinator_module():
    install_homeassistant_stubs()
    load_api_module()
    return load_submodule("coordinator")

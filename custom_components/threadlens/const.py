"""Constants for the ThreadLens Home Assistant integration."""

DOMAIN = "threadlens"
CONF_URL = "url"

DEFAULT_SCAN_INTERVAL = 60

# Frontend panel / dashboard.
PANEL_URL_PATH = "threadlens"
PANEL_TITLE = "ThreadLens"
PANEL_ICON = "mdi:radar"
PANEL_WEBCOMPONENT = "threadlens-panel"
PANEL_FILENAME = "threadlens-panel.js"
PANEL_STATIC_URL = "/threadlens_static/threadlens-panel.js"

WS_TYPE_DASHBOARD = "threadlens/dashboard"

DATA_FRONTEND_REGISTERED = "frontend_registered"
DATA_WEBSOCKET_REGISTERED = "websocket_registered"

ATTR_HEALTH_REASONS = "health_reasons"
ATTR_THREADLENS_VERSION = "threadlens_version"
ATTR_REPORT_URL_YAML = "report_url_yaml"
ATTR_REPORT_URL_JSON = "report_url_json"
ATTR_COLLECTORS = "collectors"
ATTR_SITE = "site"

TOOL_NAME = "ThreadLens"

"""Constants for the ThreadLens Home Assistant integration."""

DOMAIN = "threadlens"
CONF_URL = "url"

DEFAULT_SCAN_INTERVAL = 60

# Frontend panel / dashboard.
PANEL_URL_PATH = "threadlens"
PANEL_TITLE = "ThreadLens"
PANEL_ICON = "mdi:access-point-network"
PANEL_WEBCOMPONENT = "threadlens-panel"
PANEL_FILENAME = "threadlens-panel.js"
PANEL_STATIC_URL = "/threadlens_static/threadlens-panel.js"

WS_TYPE_DASHBOARD = "threadlens/dashboard"

# Authenticated HTTP proxy for the ThreadLens report YAML.
REPORT_PROXY_URL = "/api/threadlens/report.yaml"

EVENT_WINDOW = "24h"
EVENT_LIMIT = 100

DATA_FRONTEND_REGISTERED = "frontend_registered"
DATA_WEBSOCKET_REGISTERED = "websocket_registered"
DATA_HTTP_REGISTERED = "http_registered"

ATTR_HEALTH_REASONS = "health_reasons"
ATTR_THREADLENS_VERSION = "threadlens_version"
ATTR_REPORT_URL_YAML = "report_url_yaml"
ATTR_REPORT_URL_JSON = "report_url_json"
ATTR_COLLECTORS = "collectors"
ATTR_SITE = "site"

TOOL_NAME = "ThreadLens"

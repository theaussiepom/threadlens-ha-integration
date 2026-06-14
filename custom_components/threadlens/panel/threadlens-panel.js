/**
 * ThreadLens dashboard panel.
 *
 * A dependency-free custom element. It fetches a pre-aggregated payload from
 * the Home Assistant backend over the authenticated websocket connection
 * (`threadlens/dashboard`) and never talks to ThreadLens Core directly, so
 * there are no CORS or local-network auth issues.
 */

const REFRESH_INTERVAL_MS = 30000;

const HEALTH_ORDER = ["critical", "degraded", "warning", "unknown", "healthy"];

function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function healthClass(state) {
  switch (state) {
    case "healthy":
      return "tl-ok";
    case "warning":
      return "tl-warn";
    case "degraded":
      return "tl-degraded";
    case "critical":
      return "tl-critical";
    default:
      return "tl-unknown";
  }
}

function badge(state) {
  const text = state || "unknown";
  return `<span class="tl-badge ${healthClass(text)}">${esc(text)}</span>`;
}

function boolText(value, onText, offText) {
  if (value === null || value === undefined) return "—";
  return value ? onText : offText;
}

class ThreadLensPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._data = null;
    this._error = null;
    this._loading = false;
    this._lastFetch = null;
    this._initialized = false;
    this._timer = null;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._initialized) {
      this._initialized = true;
      this._render();
      this._fetch();
    }
  }

  get hass() {
    return this._hass;
  }

  connectedCallback() {
    if (this._timer) clearInterval(this._timer);
    this._timer = setInterval(() => this._fetch(), REFRESH_INTERVAL_MS);
  }

  disconnectedCallback() {
    if (this._timer) clearInterval(this._timer);
    this._timer = null;
  }

  async _fetch() {
    if (!this._hass) return;
    this._loading = true;
    this._update();
    try {
      const result = await this._hass.callWS({ type: "threadlens/dashboard" });
      this._data = result;
      this._error = result && result.error ? result.error : null;
    } catch (err) {
      this._error = (err && (err.message || err.code)) || "Failed to load ThreadLens data";
    }
    this._loading = false;
    this._lastFetch = new Date();
    this._update();
  }

  _render() {
    this.shadowRoot.innerHTML = `<style>${this._styles()}</style><div class="tl-root"></div>`;
    this._update();
  }

  _update() {
    if (!this.shadowRoot) return;
    const root = this.shadowRoot.querySelector(".tl-root");
    if (!root) return;
    root.innerHTML = this._content();
    const refresh = root.querySelector("#tl-refresh");
    if (refresh) refresh.addEventListener("click", () => this._fetch());
    const copy = root.querySelector("#tl-copy-report");
    if (copy) {
      copy.addEventListener("click", () => {
        const url = copy.getAttribute("data-url");
        if (url && navigator.clipboard) navigator.clipboard.writeText(url);
      });
    }
  }

  _content() {
    const d = this._data;
    const tl = (d && d.threadlens) || {};
    const connected = tl.api_connected;
    const lastFetch = this._lastFetch
      ? this._lastFetch.toLocaleTimeString()
      : "—";

    const header = `
      <div class="tl-header">
        <div class="tl-title">
          <ha-icon icon="mdi:radar"></ha-icon>
          <h1>ThreadLens</h1>
        </div>
        <div class="tl-header-meta">
          <span class="tl-badge ${connected ? "tl-ok" : "tl-critical"}">
            ${connected ? "API connected" : "API disconnected"}
          </span>
          <span class="tl-muted">v${esc(tl.version || "?")}</span>
          <span class="tl-muted">Updated ${esc(lastFetch)}</span>
          <button id="tl-refresh" class="tl-btn" ${this._loading ? "disabled" : ""}>
            ${this._loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>`;

    if (!d) {
      return header + `<div class="tl-card"><p class="tl-muted">Loading ThreadLens data…</p></div>`;
    }

    if (this._error && !connected) {
      return (
        header +
        `<div class="tl-card tl-error">
          <h2>ThreadLens API unavailable</h2>
          <p>${esc(this._error)}</p>
          <p class="tl-muted">Confirm ThreadLens Core is running and reachable from Home Assistant, then refresh.</p>
        </div>`
      );
    }

    return (
      header +
      this._overallCard(tl) +
      this._summaryCards(d) +
      this._otbrSection(d.otbrs || []) +
      this._matterSection(d.matter || {}) +
      this._mdnsTrelSection(d.mdns || {}, d.trel || {}) +
      this._reportSection(d.report || {}) +
      this._diagnosticsSection(d)
    );
  }

  _overallCard(tl) {
    const reasons = tl.reasons || [];
    const allReasons = tl.reasons_all || reasons;
    const chips = reasons.length
      ? reasons.map((r) => `<span class="tl-chip tl-chip-warn">${esc(r.label)}</span>`).join("")
      : `<span class="tl-muted">No active warnings</span>`;
    const rawCodes = allReasons.map((r) => r.code).join(", ");
    const details = allReasons.length
      ? `<details class="tl-details"><summary>All reason codes</summary><code>${esc(rawCodes)}</code></details>`
      : "";
    return `
      <div class="tl-card">
        <div class="tl-overall">
          <div>
            <div class="tl-label">Overall health</div>
            ${badge(tl.overall_health)}
          </div>
          <div>
            <div class="tl-label">Environment</div>
            ${badge(tl.environment_health)}
          </div>
        </div>
        <div class="tl-chips">${chips}</div>
        ${details}
      </div>`;
  }

  _summaryCards(d) {
    const matter = d.matter || {};
    const mdns = d.mdns || {};
    const trel = d.trel || {};
    const mqtt = d.mqtt;
    const cards = [
      { label: "OTBRs", value: (d.otbrs || []).length, sub: "" },
      { label: "Thread networks", value: (d.networks || []).length, sub: "" },
      {
        label: "Matter nodes",
        value: matter.node_count || 0,
        sub: matter.unavailable_count
          ? `${matter.unavailable_count} unavailable`
          : "",
      },
      { label: "mDNS services", value: mdns.service_count || 0, sub: "" },
      {
        label: "TREL services",
        value: trel.service_count || 0,
        sub: trel.foreign_service_count
          ? `${trel.foreign_service_count} foreign`
          : "",
      },
      {
        label: "MQTT publishing",
        value: mqtt ? boolText(mqtt.connected, "On", "Off") : "—",
        sub: mqtt && mqtt.homeassistant_discovery_enabled ? "Discovery on" : "",
      },
    ];
    const inner = cards
      .map(
        (c) => `
        <div class="tl-summary">
          <div class="tl-summary-value">${esc(c.value)}</div>
          <div class="tl-summary-label">${esc(c.label)}</div>
          ${c.sub ? `<div class="tl-muted tl-summary-sub">${esc(c.sub)}</div>` : ""}
        </div>`
      )
      .join("");
    return `<div class="tl-summary-grid">${inner}</div>`;
  }

  _otbrSection(otbrs) {
    if (!otbrs.length) {
      return `<div class="tl-card"><h2>OTBRs</h2><p class="tl-muted">No OTBRs reported.</p></div>`;
    }
    const items = otbrs
      .map((o) => {
        const displayHealth = o.display_health || o.health;
        const effectiveState = o.effective_state || o.role || o.thread_state || "—";
        const sourceLabel = o.state_source_label || o.thread_state_source || "—";
        const mismatchDetails =
          o.rest_endpoint_mismatch && o.mismatch_detail
            ? `<details class="tl-details tl-advanced">
                <summary>Endpoint details</summary>
                <p class="tl-info-text">${esc(o.mismatch_detail)}</p>
                <div class="tl-kv tl-kv-compact">
                  <span>JSON:API state</span><span>${esc(o.json_api_thread_state || "—")}</span>
                  <span>/node state</span><span>${esc(o.legacy_node_thread_state || "—")}</span>
                </div>
              </details>`
            : "";
        const prominentWarn =
          o.rest_endpoint_mismatch && !o.mismatch_reconciled
            ? `<div class="tl-inline-warn">OTBR REST endpoints disagree and ThreadLens could not reconcile an active state.</div>`
            : "";
        return `
        <div class="tl-subcard">
          <div class="tl-subcard-head">
            <strong>${esc(o.name || o.id)}</strong>
            ${badge(displayHealth)}
          </div>
          <div class="tl-kv">
            <span>Reachable</span><span>${boolText(o.reachable, "Yes", "No")}</span>
            <span>Effective state</span><span>${esc(effectiveState)}</span>
            <span>Source</span><span>${esc(sourceLabel)}</span>
            <span>Network</span><span>${esc(o.network_name || "—")}</span>
            <span>RLOC16</span><span>${esc(o.rloc16 || "—")}</span>
          </div>
          ${prominentWarn}
          ${mismatchDetails}
        </div>`;
      })
      .join("");
    return `<div class="tl-card"><h2>OTBRs</h2>${items}</div>`;
  }

  _matterSection(matter) {
    const unavailable = matter.unavailable_nodes || [];
    const list = unavailable.length
      ? `<ul class="tl-list">${unavailable
          .map(
            (n) =>
              `<li>${esc(n.friendly_name || "Node " + n.node_id)} <span class="tl-muted">(${esc(n.server_id)})</span></li>`
          )
          .join("")}</ul>`
      : `<p class="tl-muted">All known nodes available.</p>`;
    return `
      <div class="tl-card">
        <h2>Matter ${badge(matter.health)}</h2>
        <div class="tl-kv">
          <span>Servers connected</span><span>${esc(matter.servers_connected || 0)} / ${esc(matter.servers || 0)}</span>
          <span>Nodes</span><span>${esc(matter.node_count || 0)}</span>
          <span>Unavailable</span><span>${esc(matter.unavailable_count || 0)}</span>
        </div>
        ${list}
      </div>`;
  }

  _mdnsTrelSection(mdns, trel) {
    const types = (mdns.top_service_types || [])
      .map((t) => `<span class="tl-chip">${esc(t.service_type)} (${esc(t.count)})</span>`)
      .join("");
    return `
      <div class="tl-card">
        <h2>mDNS / TREL</h2>
        <div class="tl-kv">
          <span>mDNS health</span><span>${badge(mdns.health)}</span>
          <span>mDNS services</span><span>${esc(mdns.service_count || 0)}</span>
          <span>Observation degraded</span><span>${boolText(mdns.observation_degraded, "Yes", "No")}</span>
          <span>TREL health</span><span>${badge(trel.health)}</span>
          <span>TREL services</span><span>${esc(trel.service_count || 0)}</span>
          <span>Foreign TREL</span><span>${esc(trel.foreign_service_count || 0)}</span>
        </div>
        ${types ? `<div class="tl-chips">${types}</div>` : ""}
        <p class="tl-muted tl-note">TREL visibility is observation only and does not imply device parentage.</p>
      </div>`;
  }

  _reportSection(report) {
    const url = report.report_url;
    if (!url) {
      return `<div class="tl-card"><h2>Report</h2><p class="tl-muted">Report URL unavailable.</p></div>`;
    }
    const generated = report.last_generated_at || "never";
    return `
      <div class="tl-card">
        <h2>Report</h2>
        <p class="tl-muted">Last generated: ${esc(generated)}</p>
        <div class="tl-btn-row">
          <a class="tl-btn" href="${esc(url)}" target="_blank" rel="noopener">Open report.yaml</a>
          <button id="tl-copy-report" class="tl-btn" data-url="${esc(url)}">Copy report URL</button>
        </div>
        <p class="tl-muted tl-note">Reports redact secrets but include operational metadata.</p>
      </div>`;
  }

  _diagnosticsSection(d) {
    const blocks = [
      ["Overall", d.threadlens],
      ["Matter", d.matter],
      ["mDNS", d.mdns],
      ["TREL", d.trel],
      ["OTBRs", d.otbrs],
      ["Networks", d.networks],
      ["MQTT", d.mqtt],
    ]
      .map(
        ([label, value]) =>
          `<details class="tl-details"><summary>${esc(label)}</summary><pre>${esc(
            JSON.stringify(value, null, 2)
          )}</pre></details>`
      )
      .join("");
    return `<div class="tl-card"><h2>Diagnostics</h2>${blocks}</div>`;
  }

  _styles() {
    return `
      :host { display: block; }
      .tl-root {
        padding: 16px;
        max-width: 1100px;
        margin: 0 auto;
        color: var(--primary-text-color);
        font-family: var(--paper-font-body1_-_font-family, Roboto, sans-serif);
      }
      .tl-header {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 16px;
      }
      .tl-title { display: flex; align-items: center; gap: 8px; }
      .tl-title h1 { font-size: 1.5rem; margin: 0; }
      .tl-header-meta { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
      .tl-card {
        background: var(--card-background-color, #fff);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.1));
        padding: 16px;
        margin-bottom: 16px;
      }
      .tl-card h2 { font-size: 1.1rem; margin: 0 0 12px; display: flex; align-items: center; gap: 8px; }
      .tl-error { border-left: 4px solid var(--error-color, #db4437); }
      .tl-muted { color: var(--secondary-text-color); font-size: 0.9rem; }
      .tl-note { margin-top: 8px; font-style: italic; }
      .tl-label { font-size: 0.85rem; color: var(--secondary-text-color); margin-bottom: 4px; }
      .tl-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: capitalize;
        color: var(--primary-text-color, #212121);
        border: 1px solid var(--divider-color, #bdbdbd);
        background: var(--card-background-color, #fff);
      }
      .tl-ok {
        background: color-mix(in srgb, var(--success-color, #43a047) 14%, transparent);
        border-color: var(--success-color, #43a047);
        color: var(--primary-text-color, #1b5e20);
      }
      .tl-warn {
        background: color-mix(in srgb, var(--warning-color, #fb8c00) 16%, transparent);
        border-color: var(--warning-color, #fb8c00);
        color: var(--primary-text-color, #4e342e);
      }
      .tl-degraded {
        background: color-mix(in srgb, #ef6c00 16%, transparent);
        border-color: #ef6c00;
        color: var(--primary-text-color, #4e342e);
      }
      .tl-critical {
        background: color-mix(in srgb, var(--error-color, #db4437) 14%, transparent);
        border-color: var(--error-color, #db4437);
        color: var(--primary-text-color, #b71c1c);
      }
      .tl-unknown {
        background: var(--secondary-background-color, #eeeeee);
        border-color: var(--divider-color, #bdbdbd);
        color: var(--secondary-text-color, #616161);
      }
      .tl-overall { display: flex; gap: 32px; margin-bottom: 12px; }
      .tl-chips { display: flex; flex-wrap: wrap; gap: 8px; }
      .tl-chip {
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color, #212121);
        border: 1px solid var(--divider-color, #bdbdbd);
        border-radius: 12px;
        padding: 4px 10px;
        font-size: 0.8rem;
        font-weight: 500;
      }
      .tl-chip-warn {
        background: color-mix(in srgb, var(--warning-color, #fb8c00) 12%, transparent);
        border-color: var(--warning-color, #fb8c00);
        color: var(--primary-text-color, #4e342e);
      }
      .tl-summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .tl-summary {
        background: var(--card-background-color, #fff);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0,0,0,0.1));
        padding: 16px;
        text-align: center;
      }
      .tl-summary-value { font-size: 1.8rem; font-weight: 600; }
      .tl-summary-label { color: var(--secondary-text-color); font-size: 0.85rem; }
      .tl-summary-sub { margin-top: 4px; }
      .tl-subcard {
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
      }
      .tl-subcard-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
      .tl-kv {
        display: grid;
        grid-template-columns: max-content 1fr;
        gap: 4px 16px;
        font-size: 0.9rem;
      }
      .tl-kv span:nth-child(odd) { color: var(--secondary-text-color); }
      .tl-inline-warn {
        margin-top: 10px;
        padding: 8px 10px;
        border-radius: 6px;
        background: color-mix(in srgb, var(--warning-color, #fb8c00) 12%, transparent);
        border: 1px solid var(--warning-color, #fb8c00);
        color: var(--primary-text-color, #4e342e);
        font-size: 0.85rem;
      }
      .tl-info-text {
        margin: 8px 0 0;
        color: var(--primary-text-color, #212121);
        font-size: 0.85rem;
        line-height: 1.45;
      }
      .tl-kv-compact { margin-top: 8px; }
      .tl-list { margin: 8px 0 0; padding-left: 18px; }
      .tl-btn {
        appearance: none;
        border: 1px solid transparent;
        background: var(--primary-color, #03a9f4);
        color: var(--text-primary-color, #fff);
        padding: 8px 14px;
        border-radius: 8px;
        font-size: 0.9rem;
        cursor: pointer;
        text-decoration: none;
        display: inline-block;
      }
      .tl-btn[disabled] { opacity: 0.6; cursor: default; }
      .tl-btn-row { display: flex; gap: 8px; flex-wrap: wrap; }
      .tl-details { margin-top: 8px; }
      .tl-details summary { cursor: pointer; color: var(--secondary-text-color); }
      .tl-details pre {
        overflow: auto;
        background: var(--secondary-background-color, #f5f5f5);
        padding: 10px;
        border-radius: 6px;
        font-size: 0.8rem;
      }
      @media (max-width: 600px) {
        .tl-overall { gap: 16px; }
      }
    `;
  }
}

if (!customElements.get("threadlens-panel")) {
  customElements.define("threadlens-panel", ThreadLensPanel);
}

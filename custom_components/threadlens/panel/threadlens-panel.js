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

const NODE_CLASS_META = {
  unavailable: { label: "Unavailable", cls: "tl-critical" },
  recently_unstable: { label: "Recently unstable", cls: "tl-warn" },
  healthy: { label: "Healthy", cls: "tl-ok" },
  unknown: { label: "Unknown", cls: "tl-unknown" },
};

function nodeBadge(classification) {
  const meta = NODE_CLASS_META[classification] || NODE_CLASS_META.unknown;
  return `<span class="tl-badge ${meta.cls}">${esc(meta.label)}</span>`;
}

const INCIDENT_META = {
  ok: { label: "OK", cls: "tl-ok" },
  watch: { label: "Watch", cls: "tl-warn" },
  incident: { label: "Incident", cls: "tl-critical" },
  unknown: { label: "Unknown", cls: "tl-unknown" },
};

function boolText(value, onText, offText) {
  if (value === null || value === undefined) return "—";
  return value ? onText : offText;
}

function fmtTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
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
    this._selectedNodeId = null;
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

    const openReport = root.querySelector("#tl-open-report");
    if (openReport) {
      openReport.addEventListener("click", () =>
        this._openReport(openReport.getAttribute("data-proxy"))
      );
    }

    root.querySelectorAll("[data-node-id]").forEach((el) => {
      el.addEventListener("click", () => {
        this._selectedNodeId = el.getAttribute("data-node-id");
        this._update();
      });
    });

    const back = root.querySelector("#tl-node-back");
    if (back) {
      back.addEventListener("click", () => {
        this._selectedNodeId = null;
        this._update();
      });
    }
  }

  async _openReport(proxyUrl) {
    if (!proxyUrl) return;
    // Sign the path so the new tab carries Home Assistant auth without a token.
    try {
      const signed = await this._hass.callWS({
        type: "auth/sign_path",
        path: proxyUrl,
        expires: 60,
      });
      const target = (signed && signed.path) || proxyUrl;
      window.open(target, "_blank", "noopener");
    } catch (err) {
      window.open(proxyUrl, "_blank", "noopener");
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
          <ha-icon icon="mdi:access-point-network"></ha-icon>
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

    const matter = d.matter || {};
    if (this._selectedNodeId) {
      const node = (matter.nodes || []).find(
        (n) => String(n.node_id) === String(this._selectedNodeId)
      );
      if (node) {
        return header + this._nodeDetailView(node, d);
      }
      this._selectedNodeId = null;
    }

    return (
      header +
      this._incidentCard(d) +
      this._overallCard(tl) +
      this._summaryCards(d) +
      this._matterNodeHealth(matter) +
      this._otbrSection(d.otbrs || []) +
      this._matterSection(matter) +
      this._mdnsTrelSection(d.mdns || {}, d.trel || {}) +
      this._reportSection(d.report || {}) +
      this._diagnosticsSection(d)
    );
  }

  _incidentCard(d) {
    const incident = d.incident || {};
    const meta = INCIDENT_META[incident.state] || INCIDENT_META.unknown;
    const affected = incident.affected_node_names || [];
    const affectedLine = affected.length
      ? `<p class="tl-info-text">Affected nodes: ${esc(affected.join(", "))}</p>`
      : "";
    return `
      <div class="tl-card tl-incident tl-incident-${esc(incident.state || "unknown")}">
        <div class="tl-incident-head">
          <h2>Network incident summary</h2>
          <span class="tl-badge ${meta.cls}">${esc(meta.label)}</span>
        </div>
        <p class="tl-incident-headline">${esc(incident.headline || "")}</p>
        <p class="tl-info-text">${esc(incident.detail || "")}</p>
        ${affectedLine}
      </div>`;
  }

  _matterNodeHealth(matter) {
    const nodes = matter.nodes || [];
    if (!nodes.length) {
      return `<div class="tl-card"><h2>Matter nodes</h2><p class="tl-muted">No Matter nodes reported.</p></div>`;
    }
    const groupsOrder = [
      ["unavailable", "Needs attention"],
      ["recently_unstable", "Recently unstable"],
      ["unknown", "Unknown"],
      ["healthy", "Healthy"],
    ];
    const grouped = {};
    nodes.forEach((n) => {
      (grouped[n.classification] = grouped[n.classification] || []).push(n);
    });
    const sections = groupsOrder
      .filter(([key]) => (grouped[key] || []).length)
      .map(([key, title]) => {
        const rows = grouped[key]
          .map((n) => this._nodeRow(n))
          .join("");
        return `<div class="tl-node-group"><div class="tl-node-group-title">${esc(title)} (${grouped[key].length})</div>${rows}</div>`;
      })
      .join("");
    return `
      <div class="tl-card">
        <h2>Matter node health</h2>
        <div class="tl-node-counts">
          <span>${esc(matter.unavailable_count || 0)} unavailable</span>
          <span>${esc(matter.unstable_count || 0)} unstable</span>
          <span>${esc(matter.healthy_count || 0)} healthy</span>
          <span>${esc(matter.unknown_count || 0)} unknown</span>
        </div>
        ${sections}
        <p class="tl-muted tl-note">Click a node to inspect recent events and assessment.</p>
      </div>`;
  }

  _nodeRow(n) {
    const sub = [n.vendor, n.product].filter(Boolean).join(" · ");
    const recent =
      n.recent_unavailable_count || n.recent_recovered_count
        ? `<span class="tl-muted">${esc(n.recent_unavailable_count || 0)} down / ${esc(n.recent_recovered_count || 0)} up (24h)</span>`
        : "";
    return `
      <div class="tl-node-row" data-node-id="${esc(n.node_id)}" role="button" tabindex="0">
        <div class="tl-node-row-main">
          <strong>${esc(n.name)}</strong>
          <span class="tl-muted">#${esc(n.node_id)}${sub ? " · " + esc(sub) : ""}</span>
        </div>
        <div class="tl-node-row-meta">
          ${recent}
          ${nodeBadge(n.classification)}
        </div>
      </div>`;
  }

  _nodeDetailView(node, d) {
    const events = (d.events && d.events.items) || [];
    const subjectId = node.subject_id;
    const nodeEvents = events.filter((e) => e.subject_id === subjectId);
    const detail = this._nodeAssessment(node, d);
    const eventRows = nodeEvents.length
      ? nodeEvents
          .map(
            (e) => `
            <div class="tl-event-row">
              <span class="tl-muted">${esc(fmtTime(e.timestamp))}</span>
              <span>${esc(e.event_type)}</span>
              <span class="tl-muted">${esc(e.severity || "")}</span>
            </div>`
          )
          .join("")
      : `<p class="tl-muted">No recent events for this node in the current window.</p>`;
    const sub = [node.vendor, node.product].filter(Boolean).join(" · ");
    return `
      <div class="tl-card">
        <div class="tl-subcard-head">
          <button id="tl-node-back" class="tl-btn tl-btn-secondary">← Back</button>
          ${nodeBadge(node.classification)}
        </div>
        <h2>${esc(node.name)} <span class="tl-muted">#${esc(node.node_id)}</span></h2>
        ${sub ? `<p class="tl-muted">${esc(sub)}</p>` : ""}
        <div class="tl-kv">
          <span>Availability</span><span>${boolText(node.available, "Available", "Unavailable")}</span>
          <span>Server</span><span>${esc(node.server_id || "—")}</span>
          <span>Last seen</span><span>${esc(fmtTime(node.last_seen))}</span>
          <span>Last unavailable</span><span>${esc(node.last_unavailable ? fmtTime(node.last_unavailable) : "—")}</span>
          <span>Recent down / up (24h)</span><span>${esc(node.recent_unavailable_count || 0)} / ${esc(node.recent_recovered_count || 0)}</span>
        </div>
      </div>
      <div class="tl-card">
        <h2>What this suggests</h2>
        <p class="tl-info-text">${esc(detail.assessment)}</p>
      </div>
      <div class="tl-card">
        <h2>Recent events</h2>
        ${eventRows}
      </div>`;
  }

  _nodeAssessment(node, d) {
    // Mirror the backend node-detail assessment using the payload already present.
    const events = (d.events && d.events.items) || [];
    const matter = d.matter || {};
    const nodes = matter.nodes || [];
    const thisUnstable =
      (node.recent_unavailable_count || 0) || (node.recent_recovered_count || 0);
    const otherUnstable = nodes.filter(
      (n) =>
        n.subject_id !== node.subject_id &&
        ((n.recent_unavailable_count || 0) || (n.recent_recovered_count || 0))
    );
    const infraEvents = events.filter((e) =>
      ["matter_server.disconnected", "otbr.unreachable", "thread_network.lost"].includes(
        e.event_type
      )
    );
    const nodeEvents = events.filter((e) => e.subject_id === node.subject_id);
    if (!nodeEvents.length && !thisUnstable) {
      return {
        assessment:
          "There is not enough recent event history to classify this as device-local or network-wide.",
      };
    }
    if (otherUnstable.length) {
      return {
        assessment:
          "Multiple Matter nodes changed state around the same time. This may indicate a wider Matter/Thread network issue.",
      };
    }
    if (infraEvents.length) {
      return {
        assessment:
          "Infrastructure events were observed near this node change. Review OTBR, Matter server, mDNS, and TREL sections.",
      };
    }
    if (thisUnstable) {
      return {
        assessment:
          "This looks isolated to this node. ThreadLens does not see a wider Matter/Thread infrastructure issue at the same time.",
      };
    }
    return {
      assessment:
        "There is not enough recent event history to classify this as device-local or network-wide.",
    };
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
    return `
      <div class="tl-card">
        <h2>Matter servers ${badge(matter.health)}</h2>
        <div class="tl-kv">
          <span>Servers connected</span><span>${esc(matter.servers_connected || 0)} / ${esc(matter.servers || 0)}</span>
          <span>Total nodes</span><span>${esc(matter.node_count || 0)}</span>
          <span>Recent down / up (24h)</span><span>${esc(matter.recent_unavailable_count || 0)} / ${esc(matter.recent_recovered_count || 0)}</span>
        </div>
      </div>`;
  }

  _mdnsTrelSection(mdns, trel) {
    const types = (mdns.top_service_types || [])
      .map((t) => `<span class="tl-chip">${esc(t.service_type)} (${esc(t.count)})</span>`)
      .join("");
    const foreignNote =
      trel.foreign_service_count && trel.informational
        ? `<div class="tl-info-banner">
            <strong>Other Thread/TREL services visible: ${esc(trel.foreign_service_count)}</strong>
            <p class="tl-info-text">This is common when HomePods, Apple TVs, Nest devices, or other Thread fabrics are on the LAN. ThreadLens does not treat this as a fault by itself.</p>
          </div>`
        : "";
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
        ${foreignNote}
        ${types ? `<div class="tl-chips">${types}</div>` : ""}
        <p class="tl-muted tl-note">TREL visibility is observation only and does not imply device parentage.</p>
      </div>`;
  }

  _reportSection(report) {
    const proxy = report.report_proxy_url;
    const url = report.report_url;
    if (!proxy && !url) {
      return `<div class="tl-card"><h2>Report</h2><p class="tl-muted">Report URL unavailable.</p></div>`;
    }
    const generated = report.last_generated_at || "never";
    const openBtn = proxy
      ? `<button id="tl-open-report" class="tl-btn" data-proxy="${esc(proxy)}">Open report YAML</button>`
      : "";
    const copyBtn = url
      ? `<button id="tl-copy-report" class="tl-btn tl-btn-secondary" data-url="${esc(url)}">Copy report URL</button>`
      : "";
    return `
      <div class="tl-card">
        <h2>Report</h2>
        <p class="tl-muted">Last generated: ${esc(generated)}</p>
        <div class="tl-btn-row">
          ${openBtn}
          ${copyBtn}
        </div>
        <p class="tl-muted tl-note">Opens the YAML report in a new tab via an authenticated Home Assistant proxy. Reports redact secrets but include operational metadata.</p>
      </div>`;
  }

  _diagnosticsSection(d) {
    const blocks = [
      ["Overall", d.threadlens],
      ["Incident", d.incident],
      ["Matter", d.matter],
      ["mDNS", d.mdns],
      ["TREL", d.trel],
      ["OTBRs", d.otbrs],
      ["Networks", d.networks],
      ["Events", d.events],
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
      .tl-incident-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
      .tl-incident-head h2 { margin: 0; }
      .tl-incident-headline { font-size: 1rem; font-weight: 600; margin: 10px 0 0; }
      .tl-incident { border-left: 4px solid var(--divider-color, #bdbdbd); }
      .tl-incident-ok { border-left-color: var(--success-color, #43a047); }
      .tl-incident-watch { border-left-color: var(--warning-color, #fb8c00); }
      .tl-incident-incident { border-left-color: var(--error-color, #db4437); }
      .tl-node-counts {
        display: flex;
        flex-wrap: wrap;
        gap: 8px 16px;
        margin-bottom: 12px;
        font-size: 0.85rem;
        color: var(--secondary-text-color);
      }
      .tl-node-group { margin-bottom: 12px; }
      .tl-node-group-title {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--secondary-text-color);
        margin-bottom: 6px;
      }
      .tl-node-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 10px 12px;
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 8px;
        margin-bottom: 6px;
        cursor: pointer;
      }
      .tl-node-row:hover { background: var(--secondary-background-color, #f5f5f5); }
      .tl-node-row-main { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
      .tl-node-row-meta { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
      .tl-event-row {
        display: grid;
        grid-template-columns: max-content 1fr max-content;
        gap: 12px;
        padding: 6px 0;
        border-bottom: 1px solid var(--divider-color, #eeeeee);
        font-size: 0.85rem;
      }
      .tl-info-banner {
        margin-top: 10px;
        padding: 10px 12px;
        border-radius: 8px;
        background: var(--secondary-background-color, #f5f5f5);
        border: 1px solid var(--divider-color, #e0e0e0);
      }
      .tl-btn-secondary {
        background: var(--secondary-background-color, #e0e0e0);
        color: var(--primary-text-color, #212121);
        border: 1px solid var(--divider-color, #bdbdbd);
      }
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

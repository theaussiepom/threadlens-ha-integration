# Live Home Assistant Validation Checklist

Manual validation for the ThreadLens HACS integration (version `0.1.0`).

This checklist is for **Ben to run in Home Assistant**. It is intentionally out of scope for
automated CI. Do not tag `v0.1.0` until this validation passes.

ThreadLens Core endpoint (Study Pi):

```text
http://192.168.100.4:8128
```

HACS custom repository (use `main` after PR #1 is merged):

```text
https://github.com/theaussiepom/threadlens-ha-integration
```

---

## 1. Install via HACS

1. Open **HACS** in Home Assistant.
2. Go to **Settings** (three dots menu) → **Custom repositories**.
3. Add repository:
   ```text
   https://github.com/theaussiepom/threadlens-ha-integration
   ```
4. Category: **Integration**
5. Save, then find **ThreadLens** in HACS and click **Download**.
6. **Restart Home Assistant** if HACS prompts you to.

### Expected

- HACS download completes without errors.
- `custom_components/threadlens/` appears under `/config/custom_components/`.
- `custom_components/threadlens/panel/threadlens-panel.js` exists on the HA host.

---

## 2. Add the integration

1. Go to **Settings → Devices & services**.
2. Click **Add integration**.
3. Search for **ThreadLens**.
4. Enter ThreadLens URL:
   ```text
   http://192.168.100.4:8128
   ```
5. Complete the config flow.

### Expected

- Config flow validates `/api/v1/version` and `/api/v1/health` successfully.
- Integration entry appears (title like `ThreadLens 0.1.2`).
- No config-flow error dialogs.

---

## 3. Confirm helper entities

Check that secondary helper entities load (useful for automations, not required for the dashboard):

### Sensors

- `sensor.threadlens_api_health`
- `sensor.threadlens_environment_health`
- `sensor.threadlens_last_report_generated_at`
- `sensor.threadlens_event_count_24h`
- `sensor.threadlens_warning_count_24h`

### Binary sensors

- `binary_sensor.threadlens_api_connected`
- `binary_sensor.threadlens_mqtt_connected`
- `binary_sensor.threadlens_mdns_observer_running`

### Buttons

- `button.threadlens_refresh`
- `button.threadlens_generate_report`

### Expected

- Entities appear under the ThreadLens device.
- `binary_sensor.threadlens_api_connected` is **on**.
- Sensor values update within ~60 seconds (or after pressing **Refresh**).

---

## 4. Open the ThreadLens sidebar panel

1. Look for **ThreadLens** in the Home Assistant left sidebar (icon: `mdi:radar`).
2. Click to open the panel.

### Expected

- Sidebar entry **ThreadLens** is visible.
- Panel opens without a blank screen.
- No 404 for `/threadlens_static/threadlens-panel.js` in browser network tab.

---

## 5. Confirm dashboard live data

The panel fetches data from Home Assistant via websocket command `threadlens/dashboard`. It does
**not** depend on MQTT Discovery entities.

### Expected values (as of ThreadLens Core 0.1.2 on Study Pi)

| Item | Expected |
|------|----------|
| ThreadLens Core version | `0.1.2` |
| API connected | Yes |
| Overall health | `warning` |
| Environment health | `warning` |
| Prominent reason: `foreign_trel_services_observed` | Visible (friendly label: "Other Thread/TREL services visible") |
| `otbr_rest_endpoint_mismatch` | **Not** in prominent chips when reconciled; available under Diagnostics / "All reason codes" |
| OTBR Study | Effective state `leader`, source `/node`, health badge `healthy`, no scary mismatch banner |
| OTBR Lounge | Effective state `router`, source `/node`, health badge `healthy`, no scary mismatch banner |
| OTBR endpoint details | Expand **Endpoint details** on each OTBR for informational mismatch text |
| Matter nodes | 12 |
| Matter unavailable | 0 |
| mDNS services | ~30 |
| TREL services | ~8 (foreign ~6) |
| MQTT publishing | Connected (if surfaced in summary card) |

### Dashboard sections to verify

- [ ] Header shows version, connected state, last refresh
- [ ] Overall health card with reason chips
- [ ] Summary cards (OTBRs, networks, Matter, mDNS, TREL, MQTT)
- [ ] OTBR section with Study/Lounge details
- [ ] Matter section
- [ ] mDNS / TREL section
- [ ] Report section (open/copy report URL)
- [ ] Diagnostics expandable JSON sections

Press **Refresh** and confirm data updates.

---

## 6. Check Home Assistant logs

If shell or file access is available on the HA host:

```bash
grep -Ei "threadlens|custom_components.threadlens|websocket|panel" /config/home-assistant.log | tail -150
```

### Expected

- No repeated errors from `custom_components.threadlens`.
- No websocket registration failures.
- No panel static-path registration errors.

---

## 7. Browser checks

If the panel looks wrong:

1. **Hard refresh** the browser (Ctrl+Shift+R / Cmd+Shift+R) after install.
2. Open browser **Developer Tools → Console** and note any JS errors.
3. Open **Network** tab and check for:
   - 404 on `threadlens-panel.js`
   - Failed websocket messages for `threadlens/dashboard`
4. Confirm the panel does **not** make direct HTTP calls to `192.168.100.4:8128` — data should
   come through Home Assistant only.

---

## 8. What to report back

Please report the following so we can decide whether to tag `v0.1.0`:

| # | Question | Answer |
|---|----------|--------|
| 1 | HACS install success/failure? | |
| 2 | Config flow success/failure? | |
| 3 | Sidebar panel visible? (yes/no) | |
| 4 | Panel loads? (yes/no) | |
| 5 | Dashboard shows live data? (yes/no) | |
| 6 | Any HA log errors? (paste redacted excerpt) | |
| 7 | Any browser console errors? | |
| 8 | Screenshot (if possible) | |
| 9 | Helper entities load? (yes/no) | |

---

## 9. After validation passes

Once all checks pass:

1. Confirm readiness to tag `v0.1.0` on `main`.
2. Proceed with **HACS Pass 3B** follow-up (tag, release notes, any fixes from validation).

If validation fails, note the failure category:

- Repository / HACS structure
- `hacs.json` / `manifest.json`
- Config flow validation
- Panel static file / 404
- Websocket `threadlens/dashboard` registration
- HA version compatibility
- Other (describe)

Do not merge dashboard visual polish into a validation fix unless the panel is unusable.

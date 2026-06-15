# Home Assistant Matter device names in ThreadLens

The ThreadLens HACS integration is responsible for supplying **Home Assistant device names** to ThreadLens Core. Core does not read your HA device or entity registry directly.

Without this integration (or before it has pushed names), the Core dashboard shows Matter Server labels — often serials such as `SCM-MT-2507-0099` rather than names like `Study Blind`.

## What the integration does

1. Reads Matter-related devices and entities from the Home Assistant device and entity registries.
2. Maps them to ThreadLens Matter nodes by **node id** and, when needed, by **serial** (Matter product serial / friendly name).
3. Pushes matched names to Core via:

   `POST /api/v1/integrations/homeassistant/matter-names`

4. Re-pushes when Matter device registry entries change (new blinds, renames, recommissioning).

The HACS companion panel and the Core dashboard both prefer `ha_device_name` for the primary node label when Core has received it.

## When names are pushed

| Trigger | Behaviour |
|---------|-----------|
| Integration setup / startup | Best-effort push after Core data is available |
| Matter device registry update | Push when HA Matter devices or entities change |
| Manual coordinator refresh | Panel refresh re-fetches Core; name push follows registry hooks |

Requires ThreadLens Core **0.2.3+** and this integration **0.1.19+**.

## Matching rules

For each Matter node reported by Core, the integration resolves HA names using the same logic as the companion panel:

1. **Node id** — parse Matter node id from HA device identifiers (`matter`, `deviceid_{fabric}-{node_id}-…`) or from Matter entity `unique_id`.
2. **Serial fallback** — if node id does not match, match ThreadLens `serial`, `friendly_name`, or `name` against HA Matter serial identifiers (`serial_…`) or device serial metadata.

Only nodes with a resolved `ha_device_name` are included in the push payload. Unmatched nodes are left unchanged in Core (they keep Matter Server names).

### Example payload sent to Core

```json
{
  "source": "homeassistant",
  "devices": [
    {
      "server_id": "study_matter",
      "node_id": 17,
      "ha_device_name": "Study Blind",
      "ha_entity_id": "cover.study_blind"
    }
  ]
}
```

`ha_entity_id` is the preferred cover entity when one exists; otherwise the first linked Matter entity.

## What this integration does not do

- Does not rename devices in Home Assistant
- Does not rename devices in Matter Server
- Does not mutate blinds or Matter state
- Does not replace MQTT Discovery (MQTT and name push are separate)

## Troubleshooting a missing name

**Symptom:** One node shows a Matter serial in Core while other blinds show HA names.

1. **Confirm the device exists in HA** — Settings → Devices & services → Matter → find the blind.
2. **Confirm Core knows the node** — open Core `/api/v1/dashboard` or the companion panel and note the `node_id`.
3. **Check the Matter serial** — ThreadLens `friendly_name` / serial should match the HA device serial when node-id matching fails.
4. **Reload the integration** — Settings → Devices & services → ThreadLens → Reload.
5. **Restart Home Assistant** — triggers a fresh registry read and push.
6. **Update the integration** — ensure HACS build includes serial fallback in `ha_matter_push.py` (0.1.20+).

If HA has the device but ThreadLens still shows only the serial, the Matter node id in HA’s registry may not match Core’s `node_id`. Serial fallback should cover that case; if both fail, open an issue with the node id, Matter serial, and HA device identifiers.

## Core-side documentation

ThreadLens Core documents the enrichment API and storage fields in [home-assistant-integration.md](https://github.com/theaussiepom/threadlens/blob/main/docs/home-assistant-integration.md).

## Implementation references

| Component | Role |
|-----------|------|
| `ha_matter_names.py` | Build HA registry lookup (node id + serial) |
| `ha_matter_push.py` | Build Core API payload and POST |
| `matter_name_sync.py` | Registry listeners and push scheduling |
| `coordinator.py` | Local HA name enrichment for companion panel |

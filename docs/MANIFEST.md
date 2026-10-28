# project.json reference (MTDI 5.0)

Validated by `mtdi/project.py`; `python -m mtdi check <project>` reports the exact field
that is wrong.

## project (required)

| Field | Meaning |
|---|---|
| `id` | required; lowercase id, also the folder name |
| `name`, `author`, `domain`, `tagline` | shown in the interface |
| `description` | one paragraph; `[[term]]` highlights a technical term |

## hardware

List of `{"name", "role"}`. Shown in the intro card and the spec strip.

## sources (at least one)

| `adapter` | Fields |
|---|---|
| `serial` | `port` (`"auto"`, `/dev/ttyACM0`, `COM3`, `socket://host:port`), `baud` (115200), `vid` (optional USB vendor id for auto) |
| `tcp` | `listen` (`"0.0.0.0:8765"`) **or** `connect` (`"host:port"`) |
| `http` | `data_source` (`"HARDWARE"` or `"SOFTWARE"`); posts go to `/mtdi/ingest` |
| `python` | `callable` (`"package.module:function"`, a generator yielding lines or dicts), `options`, `data_source` |
| `replay` | `file` (JSONL from `--record`), `loop` (true), `speed` (1.0), `from_source` (filter) |
| `process` | `command` (list), `env` (object), `restart_after` (2 s), `data_source` (`SOFTWARE`): any program whose stdout lines are protocol lines |
| `system` | `interval` (1 s), `disk` (`/`): the host's CPU_PCT, MEM_PCT, SWAP_PCT, LOAD1, DISK_PCT, PROCS, NET_RX_KBS, NET_TX_KBS, TEMP_C |
| `simulator` | `rate` (lines/s), `seed`; always labelled SIMULATED |

Every source needs a unique `id`. `note` is free text.

## channels (at least one)

| Field | Default | Meaning |
|---|---|---|
| `id` | required | unique channel id; NVTRA rules refer to it |
| `label` | id | display name |
| `keys` | required | protocol keys forming this channel, in axis order |
| `kind` | `vector` if >1 key | `scalar` or `vector` |
| `axes` | lowercase keys | axis names for a vector |
| `source` | first source | a source id, or a list of interchangeable source ids |
| `domain` | `generic` | any lowercase word: `ultrasonic`, `radio`, `thermal`, `motion`, `inertial`, `power`, `compute`, `network`, `security`, `software`, `energy`, … (`physical` is accepted as an alias) |
| `unit` | `""` | physical unit after scaling |
| `scale`, `offset` | 1, 0 | physical = raw × scale + offset; a number or one per key |
| `raw_range` | none | `[low, high]` raw limits; a raw value at either end is flagged as clipped. Leave it out for an on/off or state channel: sitting at 0 or 1 is its normal value, and a channel clipped on every sample never settles, which holds NVTRA at "Baseline settling" for the whole project |
| `transform` | `none` | `ac_rms`: report the RMS about the mean over `window` samples (activity, vibration) |
| `window` | 25 | samples for `ac_rms` |
| `noise_floor` | 0.01 | smallest meaningful change, in `unit` (> 0) |
| `noise_budget` | 10 × floor | noise a healthy channel should sit under at rest (resolution credit) |
| `expected_rate` | none | samples per second the source should deliver |
| `stale_after` | from rate, else 4 s | seconds without a sample before the channel is stale |
| `alert_change` | 20 × floor | smallest change from the learned baseline that a person would call an event, in `unit`. A settled channel that moves this far adds one `alert` event to the snapshot's `events` and shows `"alert": true`; it re-arms once the change is back under half of it |
| `alert_direction` | `both` | `up` or `down` to alert only on a rise or only on a drop (scalar channels; a vector's change is a length) |
| `optional` | false | if true and offline, it is left out of the score instead of scoring 0 |
| `calibration` | none | scalar only: `{gain, offset, temp_coeff, temp_ref, temperature_key}` or a path to a file saved by `mtdi.fusion.Calibration.save`; applied after `scale`/`offset`, raw stays in `raw`. `temperature_key` is a protocol key in the same packet; without it in a packet, no temperature term is added |
| `simulate` | quiet | `{"mean": n or [..], "noise": n, "wave": {"amp", "hz"}, "events": true}` in `unit` |

**Making a calibration file.** Log the sensor next to a reference into a CSV with the header `raw,reference` (add `temperature` for a temperature fit), then run `python -m mtdi calibrate readings.csv --temperature-key TEMP`. It prints the fit and writes `readings.cal.json` for a channel's `calibration`. In MATLAB, `mtdi.calibrate` does the same.

**Calibration drift.** A sensor cannot reveal its own drift, so MTDI checks it against a reference: `POST /mtdi/action {"action": "check", "args": {"channel": "co", "reference": 10.2}}` records one spot check (`Engine.check_calibration`). After 3 checks, an RMS error above 3 × the fit's `residual_sd` sets `calibration.checks.drift` in the snapshot and adds an NVTRA warning. Without a `residual_sd`, drift stays `null` (unknown).

## fused

Several scalar channels that measure the same quantity in the same unit, combined into one
estimate with an honest uncertainty (inverse-variance weighting, `mtdi.fusion.fuse`).

```json
"fused": [{"id": "co", "label": "CO (fused)", "inputs": ["co_a", "co_b"], "sd": {"co_a": 0.8}}]
```

| field | default | meaning |
|---|---|---|
| `id` | required | unique across channels and fused entries |
| `inputs` | required | two or more scalar channel ids, all in the same `unit` |
| `sd` | `{}` | per-input standard deviation. Missing inputs use the calibration residual, then the measured noise, then `noise_floor` |
| `method` | `inverse-variance` | the only method for now |

The snapshot's `fused.<id>` holds `value`, `sd`, `unit`, and per input the `sd` used and its
`basis`. Only connected inputs count; with none connected, `value` is `null`.

## environment

| Field | Default | Meaning |
|---|---|---|
| `window` | 10 | seconds of quiet samples a baseline learns from |
| `auto_relock_after` | null | seconds a proven-stale, unlocked baseline waits before re-learning itself |

## weights

Override any of `availability` (0.20), `baseline` (0.15), `signal_to_noise` (0.20),
`clipping` (0.15), `timing` (0.10), `transient` (0.10), `axial_consensus` (0.05),
`correlation` (0.05). Weights are renormalised to sum to 1.

## nvtra.rules

Ordered list; the first match wins after the universal offline/settling checks.

```json
{"id": "…", "when": {"<channel id>": ">=6", "<channel id>": "<3", "active_at_least": 2},
 "condition": "short label", "text": "what it suggests, and what else could explain it"}
```

Comparisons (`>=`, `>`, `<=`, `<`, `==`) are on the channel's signal-to-noise ratio. A
named channel must be live for the rule to match.

The signal-to-noise ratio has no sign: a reading far above its baseline and one far below it
look the same. Add `"direction": {"<channel id>": "down"}` (below the learned baseline) or
`"up"` (above it) when the rule means one of them, for example "closer" for a distance.
Scalar channels only; a vector's deviation is a length and has no sign.

## aether

`purpose`, `story` (list), `authorship` (list), `quote`. Non-functional.

## interface

The studio's words for this project: the brand, the nav and page names, each page's title and
subtitle, the boot screen, the startup intro and the Home hero and cards. Optional. Every key is
listed with today's default in `studio/content/default.json`. Set only the ones you want; each
value must be non-empty text, and an unknown key is an error (`mtdi check` reports it).

```json
"interface": {"brand.title": "Greenhouse", "nav.page1": "Climate", "page1.title": "Air and soil",
              "home.subtitle": "Three beds, eight sensors, one baseline."}
```

`mtdi run` applies them before the studio is built. For a studio without a project, point
`MTDI_CONTENT` at a JSON file of the same shape. A project's words win over `MTDI_CONTENT`.

The three display channels name themselves after the project's channels. For each slot the project
fills (see `studio` below), `ch1.name` / `ch1.unit` (and `ch2.*`, `ch3.*`) come from that channel's
`label` and `unit`. Page 1's tabs, chart axes and statuses show them, and the data fed into the
studio carries that unit. Set them in `interface` only to override.

Channel 3 is a sweep: a series of (x, y) points. From a project it is the channel's recent history,
so its x is the sample number (`ch3.axis_unit` is set to `sample`) and its level is in the channel's
unit. Data fed to `/api/ingest` keeps the x it was given, labelled with `ch3.axis_unit` (default `x`).
Only the studio's own radio sweep is read in MHz with radio services shaded behind it. The PDF
report uses the same channel names and units; `report.title` and `report.subtitle` name the report. The channel charts (channels 1–3 and the views that compare them) title their axes, legends and colour bars with the same channel names and units. The studio's own instrument views (the receiver's IQ charts, the Wi-Fi and Bluetooth scans) keep the physical units those devices measure in: MHz, dBFS, µs, dBm.

## studio

Which project channels fill the studio interface's three display channels. Optional; without
it the first three channels are used in order.

```json
"studio": {"ch1": "accel", "ch2": "temperature", "ch3": "latency"}
```

| Slot | Shows | Fed with |
|---|---|---|
| `ch1` | Page 1, first view: vector charts, 3D views, gauge | a vector channel, or a scalar (as `[v, 0, 0]`) |
| `ch2` | Page 1, second view: level, trend, baseline | one number per sample (a vector's length) |
| `ch3` | Page 2: sweep chart, peaks, waterfall | the channel's recent history as a series |

Any program can also feed the studio directly: `POST /api/ingest` with
`{"ch1": [x, y, z], "ch2": n, "ch3": {"x": [...], "y": [...]}}` and
`Authorization: Bearer $STUDIO_INGEST_TOKEN`.


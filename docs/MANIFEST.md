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
| `raw_range` | none | `[low, high]` raw limits; a raw value at either end is flagged as clipped |
| `transform` | `none` | `ac_rms`: report the RMS about the mean over `window` samples (activity, vibration) |
| `window` | 25 | samples for `ac_rms` |
| `noise_floor` | 0.01 | smallest meaningful change, in `unit` (> 0) |
| `noise_budget` | 10 × floor | noise a healthy channel should sit under at rest (resolution credit) |
| `expected_rate` | none | samples per second the source should deliver |
| `stale_after` | from rate, else 4 s | seconds without a sample before the channel is stale |
| `alert_change` | 20 × floor | smallest change a person would call an event |
| `optional` | false | if true and offline, it is left out of the score instead of scoring 0 |
| `calibration` | none | scalar only: `{gain, offset, temp_coeff, temp_ref, temperature_key}` or a path to a file saved by `mtdi.fusion.Calibration.save`; applied after `scale`/`offset`, raw stays in `raw`. `temperature_key` is a protocol key in the same packet; without it in a packet, no temperature term is added |
| `simulate` | quiet | `{"mean": n or [..], "noise": n, "wave": {"amp", "hz"}, "events": true}` in `unit` |

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

## aether

`purpose`, `story` (list), `authorship` (list), `quote`. Non-functional.

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


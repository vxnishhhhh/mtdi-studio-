# Integrating a project into MTDI 5.0

This is the whole procedure, written so a person or an AI agent can follow it without
anything else. Integrating a project means writing **one manifest** and, if needed,
**one small piece of firmware or software** that prints protocol lines. You never edit
the pillars to add a project. If a project needs something the pillars cannot express,
that is an MTDI improvement (see the end).

## 1. Create the project

```bash
python -m mtdi new astrotech --name "AstroTech"        # inside MTDI Studio
python -m mtdi adopt ../astrotech                       # or: build another repository on MTDI
python -m mtdi create                                   # or: the wizard (+ GitHub, Vercel, Notion, MATLAB)
```

## 2. Inventory the measurements

For every quantity the project measures (a sensor reading, a software metric, a network
measurement, a security counter), write down:

| Question | Becomes |
|---|---|
| Which board or program produces it, and how does it reach the computer? | a **source** (`serial`, `tcp`, `http`, `python`, `process`, `system`, `replay`) |
| What does one sample look like? | the **keys** the firmware prints |
| Is it one number or several axes of one quantity? | `kind`: `scalar` or `vector` |
| How do raw numbers become physical units? | `scale`, `offset` (per key if needed) |
| What raw values mean "saturated"? | `raw_range` (clipping detection) |
| What is the smallest real change the sensor resolves? | `noise_floor` (start from the datasheet, then correct it from the measured LOD) |
| How often should a sample arrive? | `expected_rate` |
| What field is it? | `domain`, any lowercase word (`magnetic`, `ultrasonic`, `thermal`, `compute`, `network`, `security`, `software`, …) |

Do not invent numbers. If a value is unknown, leave the default and say so in the
project README; the Validation Chamber will measure the truth.

## 3. Make the firmware speak the protocol

One line per sample (`firmware/PROTOCOL.md`):

```
KEY=value,KEY=value,_SEQ=42
```

* Existing firmware that already prints `KEY=value` lines needs **no change**: map its keys.
* New firmware: start from `firmware/mtdi_template_arduino` or `firmware/mtdi_template_micropython`.
* Software: write a probe that prints protocol lines and run it with the `process` adapter
  (`projects/network-watch/probe.py`), post to `/mtdi/ingest` (`examples/send_http.py`), or write
  a generator for the `python` adapter.
* The computer itself: the `system` adapter needs no code (`projects/host-health`).
* Test any line: `python -m mtdi parse "DIST_CM=41.7,_SEQ=3"`.

Never print a placeholder value when the sensor fails. Print nothing: the Validation
Chamber turns the silence into a visible fault, while a fake value would be trusted.

## 4. Write project.json

Field reference: `docs/MANIFEST.md`. Worked examples:
`projects/inductra-vaion` (vector channels, AC RMS, several sources, domain rules) and
`projects/ultrasonic-room` (scalar, non-electromagnetic).

Add a `simulate` block to each channel with realistic means and noise, so the project can
be checked before the hardware is connected.

## 5. Add domain knowledge to NVTRA

The universal rules (offline, settling, ambient, one channel dominant, mixed) apply to
every project. Add the project's own knowledge as rules on channel signal-to-noise:

```json
{"id": "magnetic_dominance", "when": {"magnetic": ">=6", "electric": "<3"},
 "condition": "Magnetic activity dominant", "text": "…what it physically suggests, and what else could explain it…"}
```

The first matching rule wins, in order. Text must say what is suggested *and* what else
could cause it. NVTRA never claims more than the evidence.

## 6. Write Aether

`aether.purpose`, `story`, `authorship`, `quote`: why the project exists and who made it.
It is shown, never scored.

## 7. Verify

```bash
python -m mtdi check projects/astrotech                   # manifest is valid, channel map is right
python -m mtdi run projects/astrotech --simulate          # every page renders, pillars respond
python -m mtdi run projects/astrotech --record s.jsonl    # real hardware; keep the evidence
python -m unittest discover tests                         # nothing else broke
```

On real hardware, open the **Validation Chamber**: every channel `connected`, rate near
`expected_rate`, no clipping at rest. Then set `noise_floor` from the measured LOD/3.
Then in **Environmental Intelligence**: let it learn, lock it, save the environment.

## 8. Record it

* Add a row to the Projects table in `README.md`.
* Add an entry to `CHANGELOG.md`.
* Write `projects/<id>/README.md`: what was mapped, what is assumed, what is not carried over.

## Improving MTDI itself

If a project needs something no manifest field expresses (a new transform, a new adapter,
a new factor), change the pillar **generically** so every project benefits. Keep all
projects passing, add a test, and note it in `CHANGELOG.md` as an MTDI change. MTDI's
version moves (5.0 → 5.1) when a pillar's behaviour changes, not when a project is added.

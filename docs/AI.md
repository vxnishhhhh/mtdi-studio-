# MTDI for AI assistants

You were given this repository and asked to use MTDI for a project. This page is the
procedure. Follow it in order; do not summarise MTDI from memory and stop there.

## What MTDI is, in one paragraph

MTDI (Microprocessing Technological Diagnostic Intelligence) turns anything that
produces numbers into **channels**, and runs five pillars over them:
**00 Validation Chamber** (is each channel present, fresh, on time, in range),
**01 Environmental Intelligence** (learn the normal environment, lock it, compare against it),
**02 NVTRA** (explain what is happening, in plain language, from evidence only),
**03 I³** (the interface), and **04 Aether** (purpose and authorship, never scored).
A core fuses 00 and 01 into one score of eight named factors that can be taken apart.
It is pure Python, small enough for a Raspberry Pi, and driven entirely by one
`project.json` per project.

## Step 0: read, don't guess

Read these files before writing anything, in this order:

1. `README.md`
2. `INTEGRATING.md`, the integration procedure
3. `docs/MANIFEST.md`, every manifest field (machine-readable: `docs/schema/project.schema.json`)
4. `firmware/PROTOCOL.md`, the line format firmware and probes print
5. One worked example close to the user's field:

| Field | Example |
|---|---|
| Sensors, embedded, physics | `projects/inductra-vaion`, `projects/ultrasonic-room` |
| Computers, single-board computers, DevOps | `projects/host-health` |
| Networking | `projects/network-watch` |
| Cybersecurity | `projects/auth-watch` |

`python -m mtdi describe` prints every adapter, domain, block kind and rule operator as JSON.

## Step 1: choose the mode

* **The project lives in this repository:** `python -m mtdi new <id>` creates `projects/<id>`.
* **The project has its own repository:** `python -m mtdi adopt <path-to-that-repo>` copies MTDI
  into it (`mtdi/`), creates `mtdi-project/project.json`, and adds MTDI rules to its `AGENTS.md`.
  Prefer this when the user says "use MTDI in my project".

## Step 2: map the project to channels

Make a table with the user before writing the manifest. One row per quantity:

| What is measured | Where it comes from | Adapter | Keys | Unit | Domain |
|---|---|---|---|---|---|

How each field becomes channels:

| Field | Typical channels | Typical adapter |
|---|---|---|
| Hardware / sensors | field strength, distance, temperature, acceleration, current | `serial` (firmware prints protocol lines), `tcp` |
| Firmware | loop time, free memory, reset count, error counters | `serial` (add them to the same lines) |
| Software | latency, error rate, queue depth, request rate, build time | `process` (a probe script), `python`, `http` |
| Computer / SBC | CPU, memory, load, temperature, disk, network | `system` (built in) |
| Networking | RTT, packet loss, throughput, DNS time | `process` probe |
| Cybersecurity | failed logins, new connections, firewall drops, privilege escalations | `process` probe reading logs |
| Data / science | any instrument or dataset with a timestamped number | `replay`, `python` |

Write the table down. Ask the user for anything you cannot read from their code or datasheets.

## Step 3: write the sources

* Firmware: start from `firmware/mtdi_template_arduino` or `firmware/mtdi_template_micropython`.
  If firmware already prints `KEY=value` lines, keep it and map its keys.
* Software: write a probe that prints `KEY=value` lines to stdout and declare it with the
  `process` adapter, as in `projects/network-watch/probe.py`.
* On failure, print nothing. Never print a stand-in value.

## Step 4: write project.json

Start from `projects/_template/project.json`. Set `noise_floor` from the datasheet or a
measurement; if unknown, keep the default and write "unknown, to be set from the measured LOD"
in the project README. Add `simulate` blocks so the project runs before the hardware exists.
Add NVTRA rules for the field's own knowledge. Each rule's `text` must say what the pattern
suggests **and** what else could cause it.

## Step 5: verify, then report honestly

```bash
python -m mtdi check <project>
python -m mtdi run <project> --simulate      # every page renders, every pillar responds
python -m mtdi packet <project> --simulate --seconds 15
python -m unittest discover tests            # when working inside MTDI Studio
```

Report what was verified and what was not (for example "firmware not run on hardware").

## Non-negotiable rules

1. Projects are manifests. Never put project-specific code in `mtdi/`.
2. Never invent readings, calibrations, noise floors or results.
3. Simulated data is labelled SIMULATED end to end. Never remove the label.
4. Never edit another repository the user did not ask you to change.
5. MTDI's score is a heuristic evidence-quality score, not a probability. Say so.
6. Manifests can start programs (`process` adapter). Only run manifests you wrote or the user trusts.

## Prompt the user can paste into any AI

> Use MTDI 5.0 from https://github.com/vxnishhhhh/mtdi-studio for my project. Read `docs/AI.md`
> in that repository first and follow it step by step: read the listed files, run
> `python -m mtdi adopt` on my repository, map my project to channels with me, write the
> manifest and any probes or firmware, then verify with the commands in step 5 and tell me
> exactly what was and was not verified. My project: <describe it>.

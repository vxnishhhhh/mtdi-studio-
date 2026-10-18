# Integrate anything in one manifest

*MTDI Studio · October 2026*

MTDI's promise is that a new project needs one file, not a new monitoring system. Here
is what that looks like for three very different things.

## A sensor on a microcontroller

An HC-SR04 ultrasonic ranger on any Arduino-compatible board prints one line per
measurement:

```
DIST_CM=182.4,ECHO_US=10611,_SEQ=42
```

The manifest says where those lines arrive and what they mean:

```json
{"id": "ranger", "adapter": "serial", "port": "auto", "baud": 115200}
{"id": "distance", "keys": ["DIST_CM"], "unit": "cm", "domain": "ultrasonic",
 "raw_range": [2, 400], "noise_floor": 0.3, "expected_rate": 20}
```

`raw_range` gives clipping detection, `expected_rate` gives timing evidence, and
`noise_floor` gives the starting point for Environmental Intelligence.

## A program

Anything that prints numbers is a source. Network Watch's probe is a short plain-Python
script that measures TCP connect latency and prints:

```
RTT_MS=12.84,FAIL_PCT=0
```

The `process` adapter runs it and reads its output. Written in Rust, Go, Bash or C, it
would integrate the same way.

## The computer itself

The `system` adapter needs no code at all. On Linux, including Raspberry Pi OS, it reads
`/proc` and `/sys` with the standard library and emits CPU, memory, load, temperature,
disk and network keys. Host Health maps them to channels and adds three NVTRA rules,
such as outbound traffic without compute load.

## The procedure

1. `python -m mtdi new <id>`, or `python -m mtdi adopt <repo>` for a separate repository.
2. Make a table: what is measured, where it comes from, its keys, unit and domain.
3. Make the source print `KEY=value` lines. Print nothing on failure, never a stand-in.
4. Write `project.json`, including `simulate` blocks so it runs before the hardware does.
5. Add NVTRA rules that say what a pattern suggests and what else could cause it.
6. `python -m mtdi check`, `run --simulate`, then the real thing with `--record`.

The full guide is [INTEGRATING.md](../../INTEGRATING.md).

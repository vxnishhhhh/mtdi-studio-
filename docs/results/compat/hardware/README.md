# Hardware records

The only place a result becomes "tested on hardware" in `docs/COMPATIBILITY.md`. One JSON file per
run on a real device, written by whoever ran it:

```json
{"target": "raspberry-pi-5", "check": "install.sh, mtdi doctor and the test suite", "result": "passed",
 "date": "2026-11-01", "by": "owner", "notes": "Pi 5 8 GB, Raspberry Pi OS Bookworm 64-bit"}
```

`target` is a capability record id: `arduino-uno`, `esp32`, `raspberry-pi-5`, `raspberry-pi-4`,
`desktop`, `mac-m5` or `cloud-function`. `target`, `check`, `result`, `date` and `by` are
required; `python tools/compat/lab.py report` refuses a record without them. No record here means
nothing has been run on real hardware.

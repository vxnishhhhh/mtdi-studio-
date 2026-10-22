# MTDI budget · cloud container (x86_64, NOT a Pi) · 2026-10-22, after #19, #22 and #23

Measured with `tools/pi/measure.py` on vm: 4 CPUs, 16093 MB RAM, Python 3.13.16. Command: `python tools/pi/measure.py --no-llm` (default: 3,000 packets per channel count, so the history windows are full; measured before the cache warm-up fix, so its "no new data" column includes one uncached snapshot in 50).

## Cold start per profile

| profile | import (s) | peak memory (MB) |
|---|---|---|
| edge | 0.02 | 20.3 |
| scientific | 0.05 | 20.7 |
| vision | 0.02 | 20.3 |
| autonomous | 0.05 | 20.6 |
| hybrid | 0.05 | 20.9 |
| research | 0.05 | 20.9 |

## Engine

| channels | packets/s | snapshot, new packet each time (ms) | snapshot, no new data (ms) |
|---|---|---|---|
| 8 | 21122 | 3.13 | 3.01 |
| 32 | 4784 | 18.64 | 13.23 |
| 128 | 1165 | 115.62 | 68.35 |

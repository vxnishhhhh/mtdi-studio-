# MTDI budget · cloud container (x86_64, NOT a Pi) · 2026-10-21

Measured with `tools/pi/measure.py` on vm: 4 CPUs, 16093 MB RAM, Python 3.13.16.

## Cold start per profile

| profile | import (s) | peak memory (MB) |
|---|---|---|
| edge | 0.04 | 20.3 |
| scientific | 0.07 | 20.6 |
| vision | 0.02 | 20.4 |
| autonomous | 0.06 | 20.8 |
| hybrid | 0.07 | 20.8 |
| research | 0.05 | 20.7 |

## Engine

| channels | packets/s | snapshot (ms) |
|---|---|---|
| 8 | 22510 | 8.5 |
| 32 | 7364 | 57.57 |
| 128 | 1729 | 690.89 |

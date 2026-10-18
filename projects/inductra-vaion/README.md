# Inductra Vaion · MTDI project 1

The first project integrated into MTDI. **Inductra Vaion itself lives in its own repository
(`vxnishhhhh/inductra-vaion`) and is not modified by MTDI Studio.** This folder is how MTDI
sees it: a manifest plus copies of the firmware and the bridge it already uses.

| File | What it is |
|---|---|
| `project.json` | Inductra's sources, channels, NVTRA rules and Aether text, in MTDI 5.0 form |
| `firmware/inductra_uno_bridge.ino` | Combined E-field + QMC5883P Uno firmware, **byte-identical copy** |
| `firmware/inductra_uno_adc.ino` | Three-channel E-field-only Uno firmware, **byte-identical copy** |
| `bridge/uno_network_bridge.py` | Mac → Pi TCP line bridge, **byte-identical copy** |

Copied from `inductra-vaion` at commit `48963fd` ("Recover sensor bridge from mDNS failures").
SHA-256: bridge firmware `11da46b2…`, ADC firmware `79597763…`, network bridge `0a58ef8c…`.

## Running it

```bash
python -m mtdi run projects/inductra-vaion --simulate        # no hardware
python -m mtdi run projects/inductra-vaion --host 0.0.0.0    # Uno on USB here, or the Mac bridge on :8765
```

The firmware's existing `CH1=…,CH2=…,CH3=…` and `MAGX=…,MAGY=…,MAGZ=…` lines are already
MTDI protocol lines, so nothing on the Uno changes. The Mac bridge connects to port 8765 exactly
as it does for Inductra.

## How the mapping was chosen, and what is not settled

* **Magnetic:** raw QMC5883P codes × (1/150) µT. The firmware writes 0x0C to register 0x0B
  (2 G range), which Inductra's `acquisition.py` scales at 150 LSB/µT.
* **Electric:** CH3/CH2/CH1 → x/y/z, Inductra's documented probe order. Counts × 5000/1023 mV
  (Uno AVcc nominal 5.0 V, the same uncalibrated assumption Inductra states), then AC RMS over
  25 samples (0.5 s at the firmware's 50 lines/s). This is **not** Inductra's own electric
  pipeline: Inductra converts to a provisional V/m estimate and runs D4 on block FFTs. MTDI
  scores activity relative to the environment and makes no V/m claim.
* **Noise floors:** magnetic 0.1 µT is Inductra's value. Electric 2 mV RMS is a starting guess
  for the Uno's 4.9 mV step; read the real LOD in the Validation Chamber and set it from that.
* **RF:** the tinySA is read by Inductra's own USB driver, not a line protocol, so it is an
  `http` source here and optional. It needs a small sender to feed it; until then it shows as
  waiting and does not lower the score.
* **Not carried over:** D4 (FFT harmonics, THD, RF analysis), the MATLAB twin, hand vision and
  voice. They are Inductra-specific and remain in Inductra.

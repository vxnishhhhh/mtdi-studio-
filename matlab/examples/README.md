# MATLAB examples

Each one runs as it is in MATLAB or in GNU Octave (free) from the repository root, ends with
`OK <name>`, and is run by `tests/test_sdks.py` on every change.

| Example | Shows |
|---|---|
| `calibrate_sensor.m` | Fit offset and gain against a reference, then add temperature; save the fit as a calibration file a project manifest can use |
| `fuse_two_sensors.m` | Two noisy sensors of one quantity become one reading that beats the better sensor (predicted vs observed spread) |
| `drift_check.m` | Spot checks against a reference: fresh calibration, drifted sensor, and "cannot judge" without a residual |

    octave matlab/examples/fuse_two_sensors.m

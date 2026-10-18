"""MTDI Studio: a host computer composite instrument.

Package layout (data flows top to bottom):

    app.py          Dash application, pages, callbacks and the original hardware readers
    acquisition.py  Verified sensor read paths (SRC1, SRC2, current clamp, src3)
    analysis.py     Calibration store, Baseline Lock, Transient Watch, Axial Consensus,
                    Signature Readout, MTDI confidence and the Page 3 fusion snapshot
    audition.py     Field Audition: ch2 probe, coil and RTL SDR audio paths
    devices.py      Camera process, hand tracking, host telemetry
    runtime.py      Lifecycle, streaming endpoints, exports, local HTTPS listener
    ui.py           Instrument panels, palette, browser runtime (startup gate, physics)
    selftest.py     Software checks that never claim physical validation

``run.py`` at the repository root wires these together and starts the server.
"""

APP_VERSION = "v286"

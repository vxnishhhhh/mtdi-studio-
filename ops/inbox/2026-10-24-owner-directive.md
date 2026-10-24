# Owner directive · 2026-10-24

The owner's words: "You make all of the decisions. Don't ask me about technical studio view stuff."
On the Pi: "Just build so we can put this on the pi ... like how MATLAB installs. You just install it,
all of the software is there."

Standing rules for every session, from now on:

* Sessions make every technical and design decision themselves, studio included. Record the decision
  and the reason in the report. Do not wait on the owner for one.
* Owner input is only for money (still free tiers only), credentials or keys, physical hardware, and
  reviewing GitHub workflow files (ADR 0002).
* The goal is MTDI as a single install: `install.sh`, with `mtdi doctor` to check the machine. Pi
  measurements are welcome but nothing waits on them.

S1-11 studio data path: decided. The studio reads `/mtdi/packet` directly. `StudioBridge` stays at its
three fixed display slots.

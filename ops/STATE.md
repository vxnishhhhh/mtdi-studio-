# MTDI 5 state

Updated by every session. Newest first.

* **Stage:** 1 · Universal foundation
* **Main:** green (CI on Python 3.11, 3.12, 3.13; 240 tests, MATLAB parity in GNU Octave)
* **Open PRs:** #52 S1-05 Compatibility Lab (adds a workflow: owner review, ADR 0002)
* **Next item:** phone polish: a smaller NVTRA island on the phone with no keyboard hint, and a timed-swipe step in the tour's phone pass. Then S1-06 slice 3 (section heads and cards, channel 3 sweep units, PDF headings), then S1-08 (needs a workflow file: owner review per ADR 0002).
* **Waiting on the owner:** network access for science hosts; branch protection on main;
  Codex setup; Notion connector; Vercel connector team access (see the
  plan doc's checklist). None blocks Stage 1.

## Log

* 2026-10-25 day · Owner asked for the desktop layout on phones, fixed in landscape, and dropped the Pi and Third Eye asks (ops/inbox/2026-10-25-owner-phone.md). Merged #55, the phone stage: `/phone` holds the 1180 px studio and turns it when the phone is upright, in lite mode; it is live. Merged #56: a flick carries on, so Page 1's opening takes 2 swipes; speed comes from touch timestamps; one finger drives it. Also merged #53 (Windows and shutdown) and #54 (S1-17 `alert_change` alerts). CodeRabbit raised 3 findings on #55 and #56, all fixed. Nothing has been checked on a real phone yet. Report: ops/reports/2026-10-25-night.md ("Later on 2026-10-25").

* 2026-10-25 early · Merged #48 (S1-07 Third Eye; NVTRA rules take `direction`, since the unsigned SNR made "moving away" match the "closer" rules) and #49 (studio names the fed sender and says SIMULATED; channel 2 crash on fed data fixed; bridge retries a failed push). CodeRabbit: 10 findings, 9 fixed with tests, 1 declined with reasons. Found S1-17: `alert_change` is read by nothing. Report: ops/reports/2026-10-25-night.md. Then #51 (pinned install, `MTDI_REF`).

* 2026-10-25 night · S1-07 Third Eye project in review: manifest, firmware (compiles for Uno locally), tests. Found: a 0/1 state channel with raw_range never settles and holds NVTRA at Baseline settling (documented); studio Page 1 status mislabels fed data (next PR).

* 2026-10-24 late · Merged #46 (S1-06 slice 2: channel names and units from the project; bridge now passes units, fixing channel 2 data labelled mV RMS). Next: S1-06 slice 3 (section heads and cards, channel 3 sweep units, PDF headings).

* 2026-10-24 night · Merged #41 (`mtdi update`, launcher -P fix) and #42 (studio page-ready signal, tour phone pass 3/3). S1-06 slice 1 (studio words from studio/content/default.json, MTDI_CONTENT, manifest `interface`) in review. Backlog statuses corrected (S1-02/03/04 done; S1-11 and S1-16b still in progress, with what is missing stated).

* 2026-10-24 midday · Owner directive: sessions decide everything technical. Merged #38 (install.sh, mtdi doctor, mtdi studio, local AI on by default). #39 (studio project panel, S1-11 decided: read the packet).

* 2026-10-23 midday · Main green, no open PRs, nothing merged since #36. Night passes idle: blocked on the owner's S1-11 data-path decision and the Pi measurement.

* 2026-10-22 midday · Main green, no open PRs. Paused for the owner's studio data-path decision (S1-11) and the Pi measurement. Merged since the night summary: #32 (`mtdi watch` fused/calibrated), #33 (phone nav fix), #34 (morning report).

* 2026-10-22 night · Merged #11-#30: NVTRA bot uses agents + brand mark; calibration, fused channels and drift checks in manifest/engine; Aether tags + hours counter + game spec + late-night CLI note; Pi budget doc + measure.py; snapshot 11x faster at 128 channels (1245 -> 116 ms); flaky test fixed; MATLAB fuse/calibrate/drift + examples (Octave parity); `mtdi calibrate`. Report: ops/reports/2026-10-21-night.md.

* 2026-10-21 evening · Merged S1-02 registry, S1-03 capabilities, S1-04 profiles, S1-10 research catalogue + credits, S1-11 fusion + calibration. #8 and #9 under review. Report: ops/reports/2026-10-21-evening.md.

* 2026-10-21 · S1-01: MTDI page now shows six pillars (Computational Core 02 with a live module check, Research 05 with an honest empty catalogue) plus Aether as the layer; constellation gains both branches. 56 tests, tour clean.

* 2026-10-18 · Owner added ADR 0006: Compatibility Laboratory, capability records and runtime
  selection, Intelligence Profiles (Edge, Scientific, Vision, Autonomous, Hybrid, Research). Backlog
  S1-03 to S1-05; reference projects and the universality gate renumbered S1-07 to S1-09.

* 2026-10-18 · Plan approved (all four decisions as recommended; Africa/Johannesburg time).
  Pillars per ADR 0001. Ops backbone, ADRs 0001-0005, tour tool. Scheduled sessions created.

## Owner to-do, deferred (raise at the next owner session)
* Codex: Settings → Code Review → mtdi-studio- → Trigger = every PR (no automatic review posted on PR #1).
* Vercel connector: grant team `vaishnavsh-3150s-projects` (the connector currently sees no teams).
* Keys: free Groq key in Vercel env; `NASA_API_KEY` (free) as a GitHub Actions secret.

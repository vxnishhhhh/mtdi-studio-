# MTDI 5 state

Updated by every session. Newest first.

* **Stage:** 1 · Universal foundation
* **Main:** green (CI on Python 3.11, 3.12, 3.13; 293 tests, MATLAB parity in GNU Octave)
* **Open PRs:** none
* **Next item:** the owner's priorities of 28 Oct, in order: P-01 back end visible (slice 1 merged; 13 features still missing from the studio, listed in studio/features.json), P-02 UI glitch sweep, P-03 research database, P-04 describe-it-and-build (see ops/BACKLOG.md and ops/inbox/2026-10-28-owner-priorities.md); then S1-06 slice 13, S1-08, S1-09.
* **Waiting on the owner:** whether P-04 (describe-it-and-build) goes before Stage 2; branch protection on main;
  Codex setup; Notion connector; Vercel connector team access (see the
  plan doc's checklist). None blocks Stage 1.

## Log

* 2026-10-28 late · Merged #79 (owner priorities) and #80 (P-01 slice 1): studio/features.json lists all 25 CLI commands and 42 routes as in the studio, hidden on purpose, or missing, and a test fails if one is added without an entry. Settings has a SYSTEM CHECK card (machine checks, host, targets, integrations, modules). CodeRabbit found 7 issues over 6 reviews, all fixed: a saved Settings key now counts as set up and as the AI NVTRA uses; offline mode never probes the local AI; Notion counts only with both its key and report page; a saved AI key without an id no longer crashes the key lookup; two tests no longer depend on the machine they run on.
* 2026-10-28 evening · Owner decisions: #52 Compatibility Lab approved and merged (one CodeRabbit finding fixed: checkouts no longer persist the git credential); #78 camera consent merged (NVTRA asks once and remembers; 5 CodeRabbit findings over 4 reviews, all fixed); science hosts already reachable. New owner priorities P-01 to P-04 put ahead of the rest of Stage 1.
* 2026-10-28 midday · Merged #76 (S1-06 slice 12; CodeRabbit found 4 more data-integrity issues after the night report, all fixed with tests: a calibration saved before any sample applied to feeds, skipped profiles were reported as applied, and a change of input unit or source kept the old baseline). Main green. #52 unchanged since 25 Oct, waiting on the owner. Report: ops/reports/2026-10-28-midday.md.
* 2026-10-28 early · S1-06 slice 12 (PR on auto/S1-06-slice12): the analysis engine names its channels in the project's words. Found: the studio's own magnetometer was fed to the engine with the unit "unit", so every channel 1 alert, evidence line and Page 3 card said "unit" where it meant µT; a feed naming no unit was labelled "unit" too.
* 2026-10-28 night · S1-06 slice 11 (#75, merged): Page 3, the I³ panels the runtime adds to Page 3, Settings and the MTDI pillars, the header tools, the NVTRA orb and the startup intro say what they are; the test now checks the served pages. Found: in demo mode the watermark over every page read "TEXT"; it now says the data is simulated.
* 2026-10-27 late · S1-06 slice 10 (#74, merged): the MTDI page's landing, orbit, Validation Chamber and Environmental Intelligence say what they are; each pillar's line comes from mtdi.pillars. Found: the MTDI page's live cards crashed whenever channel 3 was a fed sweep; Page 2's bad-levels warning was still a placeholder.
* 2026-10-27 evening · S1-06 slice 9 (PR on auto/S1-06-slice9): Settings, the AI key manager, the model picker and the system grid say what they are. Found: the Notion line read a placeholder setting name, so it never showed Notion as set up; TEST ACTIVE asked the model the word "Text"; the export button said "EXPORT PDF + NOTION" but the served route never contacts Notion.
* 2026-10-27 midday · Merged #70 (tour scrolls through the intro; 420 s page limit) and #71 (S1-06 slice 8, the D4 engine cards; CodeRabbit 13 findings and 1 nit over four reviews, all fixed: D4 read fed channel 3 sweeps as radio sweeps, and channel 1 units now follow the data's source). Main green. #52 unchanged since 25 Oct, waiting on the owner. Report: ops/reports/2026-10-27-midday.md.
* 2026-10-27 early · Merged #70 (tour scrolls through the intro; 420 s page limit; CodeRabbit 1 finding, fixed). S1-06 slice 8 (PR on auto/S1-06-slice8): every D4 engine card says what it shows, in the project's channel words: titles, notes, buttons, input hints, readout rows and empty states. Found: D4 read a fed channel 3 sweep as a radio sweep (MHz, dBm, radio band notes); it now carries the sweep's own units. The exposure card's source note said "100 unit" for the ICNIRP 1998 level of 100 uT.
* 2026-10-27 night · Tour (PR on auto/tour-intro): the MTDI page's slow headless load explained. The tour clicked the nav through the active startup intro (a visitor cannot: the header is pointer-events:none), so the intro's shader ran behind every page; it now scrolls the intro away first. In software GL the always-on shell (two full-screen background shaders and the full-screen scrub canvas) still holds animation near 1.5 fps, so the default page limit is 420 s. No loop leaks between pages.
* 2026-10-27 night · Merged #67 (S1-06 slice 6, Page 1; CodeRabbit 5 findings and 1 nit over 4 reviews, all fixed, one with a different condition than suggested). Merged #68 (S1-06 slice 7): Page 2's four views and tab bar say what they show; the Bluetooth strongest-signal card read "unit" for dBm; CodeRabbit 7 findings and 1 nit, all fixed. The tour needed TOUR_PAGE_TIMEOUT_MS=420000: the MTDI page takes up to 233 s to be ready in a headless browser in this container, on main too (open item).
* 2026-10-26 late · S1-06 slice 6 (PR on auto/S1-06-slice6): Page 1's three tabs say what they show in the project's channel words (section heads, cards, buttons, zoom and listen cards, chart titles, notes); channel 2's reference-scaled cards read `ch2.unit`, not a literal "unit = N/C"; the words test renders the tabs empty, fed and in reference mode, and its placeholder check now also catches padded and TITLE/Subtext/Button words.
* 2026-10-26 night · Merged #64, S1-06 slice 5: every chart and table in studio/charts.py says what it shows (MHz, dBFS, µs, dBm for the studio's own instruments; `ch3.unit` for the radio's level); CodeRabbit 4 findings, all fixed. Merged #65: D4Service computed the packet in two callbacks at once (`deque mutated during iteration`, a 500 found by the tour); computes now run one at a time and a config reload waits for one in flight; CodeRabbit 2 findings + 1 nit, all fixed. Report: ops/reports/2026-10-26-night.md.

* 2026-10-26 midday · Merged #62, S1-06 slice 4: the channel 1–3 charts and cross-channel views name their axes, legends, colour bars and empty states in the project's channel names and units (were "Text"/"Title"/"Label" and a literal "unit"); channel 2 charts keep a fed unit (CodeRabbit, 1 finding, fixed). A test renders 22 charts under a second content file. Report: ops/reports/2026-10-26-midday.md.

* 2026-10-25 evening · Merged #60, S1-06 slice 3: a fed channel 3 sweep keeps its own x unit (`ch3.axis_unit`, "sample" from the bridge) with no radio bands, in charts, readouts and the PDF report; the report takes `report.title`/`report.subtitle`, channel names and units. Fixed on the way: the report crashed on an empty archive (stale "CH1PROBE" lookup), and the archive headings had lost "RAW DIAGNOSTICS". CodeRabbit: 6 findings over 4 reviews, all fixed. Report: ops/reports/2026-10-25-night.md ("Evening on 2026-10-25").

* 2026-10-25 midday · Merged #58: an upright swipe in the intro or a scrollable panel no longer triggers Chrome's swipe-back (live since #55, fixed and checked on production 11:22 UTC); the tour gained a 60 Hz swipe pass in full Chrome; NVTRA's island says "Tap ◍" on touch and sits bottom-right on the phone stage. CodeRabbit on #58: 4 findings, 2 fixed, 2 declined with reasons. Report: ops/reports/2026-10-25-midday.md.

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

# Third Eye recordings

**No recording yet.** Nothing in this folder came from the device, and nothing here is
simulated data dressed up as a session. A real session gets recorded when the board is
running:

```bash
mtdi run projects/third-eye --record projects/third-eye/recordings/$(date +%F)-<where>.jsonl
```

Name each file for the date and the place it was recorded. Then add a replay source to the
manifest so the studio can be driven offline:

```json
{"id": "eye", "adapter": "replay", "file": "recordings/<file>.jsonl", "loop": true}
```

Until then, `mtdi run projects/third-eye --simulate` runs on the channels' `simulate` settings.
Every value it produces is labelled SIMULATED.

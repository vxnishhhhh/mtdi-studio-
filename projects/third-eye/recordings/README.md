# Third Eye recordings

**No recording yet.** Nothing in this folder came from the device, and nothing here is
simulated data dressed up as a session. A real session gets recorded when the board is
running:

```bash
mtdi run projects/third-eye --record projects/third-eye/recordings/$(date +%F)-hallway.jsonl
```

Name each file for the date and the place it was recorded: change `hallway` to wherever you
were. To drive the studio offline from it, replace the live `eye` source in the manifest
with a replay source of the same id (source ids must be unique, so keep only one of them):

```json
{"id": "eye", "adapter": "replay", "file": "recordings/2026-10-25-hallway.jsonl", "loop": true}
```

Until then, `mtdi run projects/third-eye --simulate` runs on the channels' `simulate` settings.
Every value it produces is labelled SIMULATED.

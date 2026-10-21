# Aether in code

Aether is MTDI's human layer: why a project exists, who built it, and what it cost them. It is
**never in the signal path**. No score, reading or decision depends on it.

In code, Aether lives in four comment tags. Each is written as the tag, a colon, then the text,
in any line comment (`#`, `//`, `%`).

| Tag | For | Example |
|---|---|---|
| `GUIDE` | the next person or AI who extends this | `GUIDE: a new provider needs an entry in PROVIDERS and ORDER` |
| `CONTEXT` | why it is like this: the decision, not the code | `CONTEXT: plain HTTP is allowed to LAN addresses so a Pi can serve the Mac` |
| `AETHER` | a joke, a note, a bit of the story | `AETHER: the clock decides the vibe. Never the readings.` |
| `HOURS-WASTED` | what a piece of code cost, in hours | `HOURS-WASTED: 1 - git tidied up after itself mid-delete` |

`python -m mtdi aether` (or `--json`) counts them and adds up the hours. A `HOURS-WASTED` comment
that doesn't start with a number is listed as unreadable rather than guessed.

## Rules
- **Honest hours.** Round, but don't invent. If you don't know, don't tag it.
- **Funny, not brain rot.** The test: would it still make sense to an engineer reading it in a year?
- **A `GUIDE` beats a clever comment.** If something surprised you, write the guide so it doesn't surprise the next person.
- **Never in user-facing safety text.** Warnings, errors and NVTRA's numbers stay plain.

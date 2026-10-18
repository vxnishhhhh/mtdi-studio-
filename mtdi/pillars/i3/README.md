# Pillar 03 · I³ — Induction · Interference · Intelligence

The interface every MTDI pillar is seen through, extracted from Inductra Vaion's front end.
MTDI Studio generates its pages from a project manifest (`mtdi/studio/views.py`). I³ can
also run on its own from a hand-written content pack:

```python
from mtdi.pillars.i3 import create_app, load
create_app(load("mtdi/pillars/i3/examples/placeholder.json")).run(port=8050)
```

| Piece | Origin in Inductra |
|---|---|
| Startup intro (WebGL shader, split title, overview card) | `theme.startup_intro`, `browser.bootStartupIntro` |
| Glass header, nav, status pills | `webapp` layout, `theme` header CSS |
| Page shader | `browser.bootPageShader` |
| Scroll-locked openings: `field` (magnetosphere), `flow` (signal path, data-driven) | `ui.fieldPainter`, `ui.mtdiFlowPainter` |
| Module orbit round the globe, pillar orbit opening to full screen | `browser.armHomeOrbit`, `bootHomeGlobe`, `armMtdiOrbit` |
| NVTRA dock with wire-sphere orb | `#iv-orb` island, `browser.bootMascot` |

Page types: `home`, `framework`, `document`, `module`, `settings`.
Block kinds: `section`, `text`, `cards`, `metrics`, `slot`, `spark`, `live`, `actions`, `list`, `quote`.
`[[term]]` in any text renders a highlighted technical term.

Hooks passed to `create_app`:

* `state_provider()` → `{bind_key: value | {"value", "state"} | [numbers]}`, polled by the browser;
  elements with `"bind"` follow their key, `spark` blocks draw lists.
* `ask_handler(question, path)` → the NVTRA dock's answer.
* `action_handler(action, args)` → message for `actions` blocks (raise ValueError to refuse).

`static.py` renders the same components to plain HTML (the website is built this way), and
`assets/i3.js` has no Dash dependency: it runs on `data-i3-*` attributes and
`window.I3_CONFIG`, so the same assets can back a static or React build later.
Not carried over from Inductra: hand vision, the Spline robot, voice.

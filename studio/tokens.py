"""Design tokens shared by CSS, Plotly figures and components."""
from ._shared import inherit
inherit(globals(), 'common', 'sensors', 'intelligence', 'system')

# ════════════════════════════════════════════════════════
#  DESIGN TOKENS
# ════════════════════════════════════════════════════════
BG="#07090f"; CARD="#0d1320"; CARD2="#111a2b"; BORDER="#1a2840"
BLUE="#2979ff"; CYAN="#00e5ff"; GREEN="#00e676"; AMBER="#ffab40"
YELLOW="#ffd166"; PURPLE="#b388ff"
# SUBTEXT was #5c6e8a, which measures 3.5:1 against the card surface — below WCAG AA
# for body text, and it carries almost every label in the UI. #7d8ea8 measures 5.5:1
# on the same surface while staying clearly subordinate to WHITE. Changing it here
# also fixes every Plotly axis/tick label, because the figure builders read this
# constant directly.
RED="#ff5252"; WHITE="#e8eeff"; SUBTEXT="#7d8ea8"; GLOW="rgba(41,121,255,0.15)"
FONT="'DM Mono','Courier New',monospace"
FONTUI="'Inter','DM Sans','Helvetica Neue',sans-serif"

# ── RENDERING NOTE: opaque surfaces instead of backdrop-filter ──
# Every frosted panel using backdrop-filter has to re-blur whatever is behind it on
# EVERY frame the background moves. With ~25 such panels on one page that is the single
# largest cost in this UI on a host computer, and it is also what made value updates look
# like they "shimmer". These two tokens are tuned to read the same as the old
# rgba(255,255,255,0.03)+blur stack over the dark shader, at zero per-frame cost.
SURFACE  = "rgba(16,23,38,0.74)"    # repeated small cards / tables / panels
SURFACE2 = "rgba(21,30,49,0.80)"    # large feature cards (module cards, hero panels)

def _c2_level_color(level):
    return {"LOW":GREEN,"MID":AMBER,"HIGH":RED,"OVER":RED}.get(level, SUBTEXT)

def _gain_label(g):
    fs = FULL_SCALE_VOLTS.get(g, 0)
    return f"g{g} ±{fs:g}V"

# ── theme-aware colour classes ──
# Inline style colours can't be re-themed by CSS, so dynamic values get a c-* class
# backed by CSS variables that swap automatically in light mode.
_COLOR_CLASS = {CYAN:"c-cyan", BLUE:"c-blue", GREEN:"c-green", AMBER:"c-amber",
                RED:"c-red", YELLOW:"c-yellow", PURPLE:"c-purple",
                WHITE:"c-white", SUBTEXT:"c-sub"}
def _cls(c):
    return _COLOR_CLASS.get(c, "c-white")

# ════════════════════════════════════════════════════════
#  RENDERING NOTES  (v2.0.5)
#  1. No page-entry animation anywhere. Dash swaps #page-content atomically; adding a
#     fade/slide on top of that is what produced the "old page moves, then switches"
#     jitter. .page-enter is retained as a no-op class so older markup still parses.
#  2. scroll-behavior is auto (never smooth). Navigation resets scroll instantly, and
#     the synchronous scroll dcc.Link performs *before* the swap is suppressed in JS.
#  3. scrollbar-gutter:stable removes the horizontal jump when a short page follows a
#     tall one.
#  4. #page-content reserves a full viewport height and is layout-contained, so a
#     late-rendering graph cannot shove the rest of the document around.
#  5. Live-refreshed regions have explicit min-heights and no entry animations.
# ════════════════════════════════════════════════════════


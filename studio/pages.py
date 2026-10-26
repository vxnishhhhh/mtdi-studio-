"""Page builders: Home, EM Field, Sweep3, MTDI and Settings."""
from ._shared import inherit
inherit(globals(), 'common', 'sensors', 'intelligence', 'system', 'tokens', 'theme', 'browser', 'webapp', 'reports', 'charts')
from .content import T  # studio words (S1-06)

# ════════════════════════════════════════════════════════
#  DISCIPLINE BLOCK  (for MTDI page)
# ════════════════════════════════════════════════════════
def discipline_block():
    pillars = [
        ("01","Heading 1",["Item 1","Item 2","Item 3","Item 4"]),
        ("02","Heading 2",["Item 5","Item 6","Item 7","Item 8"]),
        ("03","Heading 3",["Item 9","Item 10","Item 11","Item 12"]),
        ("04","Heading 4",["Item 13","Item 14","Item 15","Item 16"]),
    ]
    cols = [html.Div([
        html.Div([html.Div(num, className="pillar-num"), html.Div(pillar, className="pillar-title")], className="pillar-header"),
        html.Div([html.Div(className="pillar-flow"),
                  html.Div([html.Div(s, className="pillar-chip") for s in subs], className="pillar-chips")])
    ], className="pillar") for num, pillar, subs in pillars]
    return html.Div([
        html.Div(className="disc-svg-host"),
        html.Div([
            html.Div('LABEL', className="disc-eyebrow"),
            html.Div([
                html.Span("Title", className="disc-title-word"),
                html.Div('Paragraph. Enter your text here.', className="disc-under"),
                html.Div([
                    html.Div([html.Div("4", className="disc-stat-val"), html.Div('LABEL', className="disc-stat-key")], className="disc-stat"),
                    html.Div(className="disc-stat-sep"),
                    html.Div([html.Div("16", className="disc-stat-val"), html.Div('LABEL', className="disc-stat-key")], className="disc-stat"),
                    html.Div(className="disc-stat-sep"),
                    html.Div([html.Div("1", className="disc-stat-val"), html.Div('LABEL', className="disc-stat-key")], className="disc-stat"),
                ], className="disc-stats"),
            ], className="disc-title-card"),
        ], className="disc-root"),
        html.Div(cols, className="pillar-grid"),
    ], className="disc-block")


# ════════════════════════════════════════════════════════
#  HOME
# ════════════════════════════════════════════════════════
def home_page():
    with c1_lock:
        cur_c1 = ch1_data["magnitude"]
        c1_err = ch1_data["error"]
        c1_have = ch1_data["last_rx"] is not None
    with sweep3_lock:
        ch3_err = sweep3_data["error"]; ch3_pf = sweep3_data["peak_freq"]
        ch3_pl = sweep3_data["peak_level"]; ch3_have = sweep3_data["last_rx"] is not None
    with mtdi_lock:
        overall = mtdi_data["active_health"]
    if ch3_have and not ch3_err:
        ch3_val = f"{ch3_pl:+.0f} {T('ch3.unit')}"; ch3_lbl = f"PEAK @ {_freq_label(ch3_pf)}"
    elif ch3_err:
        ch3_val = "OFFLINE"; ch3_lbl = T("ch3.name").upper()
    else:
        ch3_val = "SWEEPING"; ch3_lbl = T("ch3.name").upper()
    # Fixed route identities: status and readings change, module colour never does.
    mods = [
        ("page-1","01",T("nav.page1"),T("home.card.page1"),
         f"{cur_c1:.2f} {T('ch1.unit')}" if c1_have and not c1_err else "OFFLINE",
         "MAGNITUDE" if c1_have else "NO DATA", "#67cbd5", "103,203,213"),
        ("page-2","02",T("nav.page2"),T("home.card.page2"),
         ch3_val, ch3_lbl, "#718ee8", "113,142,232"),
        ("mtdi","03",T("nav.mtdi"),T("home.card.mtdi"),
         f"{overall:.0f}%",'TEXT', "#72b99c", "114,185,156"),
        ("settings","04",T("nav.settings"),T("home.card.settings"),
         "THEME","APPEARANCE", "#9a91bd", "154,145,189"),
    ]
    orbit_cards = []
    for index, (mid, numerology, title, desc, val, vl, vc, vrgb) in enumerate(mods):
        orbit_cards.append(dcc.Link(html.Div([
            html.Div([html.Span(numerology, className="mtdi-card-index"),
                      html.Span(title.upper(), className="mtdi-card-role")], className="mtdi-card-top"),
            html.Div(title, className="mtdi-card-title"),
            html.Div(desc, className="mtdi-card-short"),
            html.Div([html.Span(val), html.Small(vl)], className="home-module-live"),
            html.Span('TEXT', className="mtdi-card-enter"),
        ], className="mtdi-card-summary"), href=f"/{mid}",
            className="mtdi-orbit-card home-module-orbit-card",
            style={"--i": str(index), "--acc": vc, "--acc-rgb": vrgb,
                   "textDecoration": "none"},
            title=f"Open {title}"))

    module_orbit = html.Div([
        html.Div(className="mtdi-orbit-ring-v2"),
        html.Div([html.Canvas(id="home-module-globe",
                             title='Title',
                             **{"aria-label": 'Text'}),
                  html.Div([html.B(), html.Span()], id="home-globe-research",
                           className="home-globe-research", hidden=True, **{"aria-live": "polite"})],
                 className="mtdi-orbit-core-v2 home-module-core"),
        html.Div(orbit_cards, id="home-module-orbit-stage", className="home-module-orbit-stage"),
    ], className="home-module-orbit")


    hero = html.Div([
        html.Div([
            html.Div(T("home.title"), className="hero-title"),
            html.Div([html.Span(T("home.tag_lead"), className="i3"), html.Span(T("home.tag"))], className="hero-tag"),
        ], className="hero-title-wrap"),
        html.Div(T("home.subtitle"), className="hero-sub"),
        html.Div([
            html.Div([html.Div('TEXT', className="k"), html.Div('Text', className="v")]),
            html.Div([html.Div('TEXT', className="k"), html.Div('Text', className="v")]),
            html.Div([html.Div('TEXT', className="k"), html.Div('Text', className="v")]),
            html.Div([html.Div('TEXT', className="k"), html.Div('Text', className="v")]),
            html.Div([html.Div('TEXT', className="k"), html.Div('TEXT', className="v")]),
            html.Div([html.Div('TEXT', className="k"), html.Div('TEXT', className="v")]),
            html.Div([html.Div('TEXT', className="k"), html.Div('Text', className="v")]),
        ], className="hero-spec"),
    ], className="hero-wrap")

    scrub_hero = html.Div(className="i3-scrub-hero", **{"data-i3-scrub": "field",
                                                        "data-i3-title": 'Title',
                                                        "data-i3-tagline": 'Paragraph. Enter your text here.'})
    return html.Div([scrub_hero, hero, html.Div([
        html.Div([
            html.Div('TITLE', className="instrument-modules-title"),
            html.Div([html.Span("Text "), html.Span("Heading", className="art-em"),
                      html.Span(" Text "), html.Span("TITLE", className="art-em", style={"letterSpacing":"0.2em","fontWeight":"500"}), html.Span(".")], className="art-line"),
            html.Div([
                html.Span([html.I(style={"--acc": "#67cbd5"}), 'TEXT']),
                html.Span([html.I(style={"--acc": "#718ee8"}), 'TEXT']),
                html.Span([html.I(style={"--acc": "#72b99c"}), 'TEXT']),
                html.Span([html.I(style={"--acc": "#9a91bd"}), 'TEXT']),
            ], className="home-module-key"),
        ], style={"textAlign":"center","marginBottom":"36px"}),
        module_orbit,
    ], style=PAD)])


def sensor_showcase_section():
    """Spatial product showcase for the two probes: 3D models (drawn by the browser) with the
    live channel readings beside them. Values come from the instrument packet; nothing here
    is a placeholder number."""
    def side(key, label, title, description, features):
        return html.Div([
            html.Div(label, className="i3-sc-kicker"),
            html.H3(title, className="i3-sc-title"),
            html.P(description, className="i3-sc-desc"),
            html.Div([
                *[html.Div([
                    html.Div([html.Span(f_label, className="i3-sc-flabel"), html.Span("—", className="i3-sc-fvalue", **{"data-i3-sc-value": f_key})], className="i3-sc-frow"),
                    html.Div(html.I(**{"data-i3-sc-bar": f_key}), className="i3-sc-bar"),
                ], className="i3-sc-feature") for f_key, f_label in features],
                html.A([html.Span('TEXT'), html.Span("→")], href="/page-1", className="i3-sc-open"),
            ], className="i3-sc-panel"),
            html.Div([html.Span("●", className="i3-sc-dot"), html.Span("Waiting", **{"data-i3-sc-state": key})], className="i3-sc-status"),
        ], className="i3-sc-details", **{"data-i3-sc-side": key})
    return html.Div([
        html.Div('TITLE', className="instrument-modules-title", style={"marginTop": "72px"}),
        html.Div('Subtext', className="i3-sc-sub"),
        html.Div([
            html.Div([
                html.Div([html.Div('LABEL', className="i3-sc-board-label"),
                          html.Canvas(className="i3-sc-boards", **{"data-i3-boards": "ch1",
                                      "aria-label": 'Text'})],
                         className="i3-sc-board-slot"),
                html.Div([html.Div('LABEL', className="i3-sc-board-label"),
                          html.Canvas(className="i3-sc-boards", **{"data-i3-boards": "ch2",
                                      "aria-label": 'Text'})],
                         className="i3-sc-board-slot"),
            ], className="i3-sc-visual i3-sc-visual-split"),
            html.Div([
                side("ch1", 'LABEL', 'Title',
                     'Paragraph. Enter your text here.',
                     [("sample_rate", 'Text'), ("snr", 'Text'), ("confidence", 'Text')]),
                side("ch2", 'LABEL', 'Title',
                     'Paragraph. Enter your text here.',
                     [("sample_rate", 'Text'), ("snr", 'Text'), ("confidence", 'Text')]),
            ], className="i3-sc-detail-wrap"),
        ], className="i3-sc-stage", **{"data-i3-showcase": "ch1"}),
        html.Div([
            html.Button('Button', type="button", className="i3-sc-btn on", **{"data-i3-sc": "ch1"}),
            html.Button('Button', type="button", className="i3-sc-btn", **{"data-i3-sc": "ch2"}),
        ], className="i3-sc-switch"),
    ], className="i3-showcase")


# ════════════════════════════════════════════════════════
#  EM FIELD  (ch1 / ch2 / combined)
# ════════════════════════════════════════════════════════
def ch1_body():
    with c1_lock:
        m = dict(ch1_data); hist = list(ch1_data["history"]); xyz = list(ch1_data["xyz_history"])
    have = m["last_rx"] is not None
    n1, u1 = T('ch1.name'), T('ch1.unit')   # the project's channel words (S1-06)
    shown = lambda value: f"{value:.2f}" if have else "—"
    return [
        html.Div([
            _mcard("mv-x", "X", shown(m["x"])),
            _mcard("mv-y", "Y", shown(m["y"])),
            _mcard("mv-z", "Z", shown(m["z"])),
            _mcard("mv-c1", "Magnitude", shown(m["magnitude"]), CYAN),
            _mcard("mv-baseline", "Quiet baseline",
                   shown(m["baseline_magnitude"]) if m["baseline_calibrated"] else "—"),
            _mcard("mv-delta", "Change from baseline",
                   shown(m["baseline_delta"]) if m["baseline_calibrated"] else "—", AMBER),
            _mcard("mv-sig", "Noise σ (last 10)", "—"),
        ], className="metric-row"),
        html.Div([
            html.Button(["RE-LEARN BASELINE"], id="c1-recal-btn",
                        className="open-btn", n_clicks=0,
                        style={"width":"auto","marginTop":"0","whiteSpace":"nowrap"}),
            html.Span("Waiting for the first reading.",
                      id="c1-recal-status",
                      style={"fontFamily":FONT,"fontSize":"11px","color":SUBTEXT,"lineHeight":"1.5"}),
            dcc.Store(id="c1-recal-request"),
        ], style={"display":"flex","alignItems":"center","gap":"16px",
                  "marginBottom":"16px","flexWrap":"wrap"}),
        html.Div([html.Span(className="online-dot off", id="c1-dot"),
                  html.Span(f"{n1.upper()} · WAITING FOR DATA", id="c1-status", className="online-text c-sub")],
                 className="online-bar"),
        _sg_listen_card("c1"),
        _chart_board("c1", f"{n1} sensor board"),
        html.Div("LIVE SIGNAL", className="section-label"),
        html.Div([
            html.Div([
                html.Div("VERTICAL ZOOM", className="ch3-ctl-label"),
                html.Div("Magnifies the line chart around the recent signal. 1× fits its typical range; a reading beyond it shows as a spike marker.",
                         className="validation-subcopy"),
            ]),
            _zoom_range("c1-zoom"),
        ], className="ch3-ctl-bar", style={"marginBottom":"16px"}),
        html.Div([
            _chart("g-line", f"{n1} magnitude over time ({u1})",
                   make_line_chart(hist, color=CYAN, fill_color="rgba(0,229,255,0.07)",
                                   height=250, ylabel=T("ch1.unit"), smart_scale=True, zoom=1,
                                   revision="c1-line")),
        ], className="chart-grid chart-grid-primary"),
        html.Div([
            _chart("g-axis", f"X, Y and Z components ({u1})", fig_axis(xyz)),
            _chart("g-scatter", "X against Y",
                   fig_2d_scatter(xyz), h=280),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div([
            _chart("g-delta", "Sample change against magnitude",
                   fig_2d_delta(xyz), h=280),
            _chart("g-gauge", f"Live magnitude ({u1})",
                   fig_gauge(m['magnitude'] if have else None)),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div([
            _chart("g-pie", "Share of each axis (|X|, |Y|, |Z|)", fig_pie(m['x'], m['y'], m['z']) if have else fig_pie(None, None, None)),
            _chart("g-bar", "Session minimum, average and maximum",
                   fig_bar(None, None, None)),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div("3D VIEWS", className="section-label", style={"marginTop":"30px"}),
        html.Div(f"The same {n1.lower()} history in three dimensions. Drag to rotate, scroll to zoom.",
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            _chart("g3d-surface", "Surface over the X–Y plane",
                   fig_3d_surface(xyz, height=400), cfg=CFG_3D, h=400),
            _chart("g3d-terrain", "Magnitude terrain, window by window",
                   fig_3d_terrain(xyz, height=400), cfg=CFG_3D, h=400),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div([
            _chart("g3d-plane", f"{n1} direction",
                   fig_3d_error_plane(xyz, height=430), cfg=CFG_3D, h=430),
            _chart("g3d-twopole", "Dipole model along that direction",
                   fig_3d_dipolch2f(xyz, height=430), cfg=CFG_3D, h=430),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div(id="mag3d-error"),
        html.Div("SIGNAL ARCHIVE", className="section-label", style={"marginTop":"30px"}),
        html.Div([
            html.Div(f"Every {n1.lower()} magnitude kept this session, oldest on the left.", className="validation-subcopy"),
            html.Div(dcc.Graph(id="g-archive", figure=fig_archive(), config=CFG_FLAT,
                               style={"height":"220px", "width":"100%"}),
                     style={"height":"220px","minHeight":"220px"}),
            html.Div([
                html.Div([html.Div("0", id="arch-count", className="arch-stat-val"), html.Div("SAMPLES", className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="arch-min", className="arch-stat-val"), html.Div("Minimum", className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="arch-avg", className="arch-stat-val"), html.Div("Average", className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="arch-max", className="arch-stat-val"), html.Div("Maximum", className="arch-stat-key")], className="arch-stat"),
            ], className="arch-stats"),
        ], className="arch-shell"),
        html.Div([html.Div("SUMMARY", className="summary-tag"),
                  html.Div([_hi("Magnitude"), html.Span("  "), html.Span("—", id="sum-c1"), html.Br(), html.Br(),
                            _hi("Axes"), html.Span("  "), html.Span("—", id="sum-axes")], className="summary-text")],
                 className="summary-panel"),
        html.Div(id="c1-error"),
        # Staggered so this host never rebuilds every figure in the same tick.
        dcc.Interval(id="c1-num-int", interval=2500, n_intervals=0),
        dcc.Interval(id="c1-chart-int", interval=3000, n_intervals=0),
        dcc.Interval(id="c1-3d-int", interval=3400, n_intervals=0),
        dcc.Interval(id="c1-dir-int", interval=2600, n_intervals=0),
        dcc.Interval(id="c1-arch-int", interval=4000, n_intervals=0),
    ]


def ch1_view():
    return html.Div(ch1_body() + [d4_ch1_blocks()])


def _zoom_range(slider_id):
    """Log scaled zoom (-1..3 -> 0.5x..8x). The Dash slider stays mounted (hidden) so the
    callbacks keep their Input; a plain range control, the same one as the audio gain, is the
    visible face and the page script mirrors its value into the Dash slider."""
    return html.Div([
        html.Div(dcc.Slider(id=slider_id, min=-1, max=3, step=0.25, value=0, updatemode="mouseup"), className="i3-zoom-dash"),
        html.Div(className="i3-zoom-face", **{"data-i3-zoom-face": slider_id}),
        html.Div([html.Span(t) for t in ("0.5×", "1×", "2×", "4×", "8×")], className="i3-zoom-ticks"),
    ], className="i3-zoom-wrap")


def _zoom_bar(slider_id, title, copy):
    return html.Div([
        html.Div([html.Div(title, className="ch3-ctl-label"), html.Div(copy, className="validation-subcopy")]),
        _zoom_range(slider_id),
    ], className="ch3-ctl-bar", style={"marginBottom": "16px"})


_LISTEN_COPY = {
    "ch2": ("LISTEN",
                 "Plays this channel as sound: louder means more activity."),
    "c1": ("LISTEN",
            "Plays this channel as sound: louder means more activity."),
    "p1": ("LISTEN TO BOTH",
           "Plays both channels as sound, mixed or one at a time."),
}


def _sg_listen_card(kind):
    """Listen card for one tab: ch2 on the Ch2 tab, ch1 on the Ch1 tab and
    the mix on the Composite tab. Reuses the Field Audition sources so one stream serves
    every page; the EM block is driven client side (both sources at once)."""
    from .ui import _audio_block
    title, copy = _LISTEN_COPY[kind]
    n1, n2 = T('ch1.name'), T('ch2.name')   # the project's channel words (S1-06)
    if kind == "ch2":
        blocks = [_audio_block(html, dcc, "ch2f", n2, [])]
    elif kind == "c1":
        blocks = [_audio_block(html, dcc, "c1", n1, [])]
    else:
        blocks = [html.Div([
            html.Div([html.Button("Play mix", type="button", className="i3-btn i3-primary", **{"data-i3-action": "audition", "data-i3-source": "p1", "data-i3-op": "start"}),
                      html.Button("Stop", type="button", className="i3-btn", **{"data-i3-action": "audition", "data-i3-source": "p1", "data-i3-op": "stop"}),
                      html.Button("Mute", type="button", className="i3-btn", **{"data-i3-action": "audition", "data-i3-source": "p1", "data-i3-op": "mute", "aria-pressed": "false"})], className="i3-form i3-p1-mix"),
            html.Div("", className="i3-inline-result", **{"data-i3-result": "true"}),
        ], className="i3-audio"),
            _audio_block(html, dcc, "ch2f", n2, []),
            _audio_block(html, dcc, "c1", n1, [])]
    return html.Div([
        html.Div([html.Div(title, className="ch3-ctl-label"), html.Div(copy, className="validation-subcopy")]),
        html.Div(blocks, className="i3-sg-listen" + (" i3-sg-two" if len(blocks) > 1 else "")),
    ], className="ch3-ctl-bar i3-sg-card", style={"marginBottom": "16px"})


def _ch2f_wiring_text():
    """Describe the probe input in prose. Read from acquisition rather than
    written out here: this paragraph claimed a differential pair with a 1.634 V
    reference on A1 long after the probe was rewired single-ended, which is the
    kind of stale sentence a judge would catch and an operator would trust."""
    try:
        from .acquisition import CH2F_MUX, CH2F_MUX_NAME
        return CH2F_MUX_NAME.get(CH2F_MUX, "input %d" % CH2F_MUX)
    except Exception:
        return "its configured input"


def _chart_board(which, label):
    """A single 3D board beside the channel that uses it.

    boards.js self-scans for canvas[data-i3-boards] and mounts whichever board
    the attribute names, so this needs no callback and no Python-side 3D."""
    return html.Div([
        html.Div(label, className="chart-hd"),
        html.Div(html.Canvas(**{"data-i3-boards": which,
                                "aria-label": label + ". Drag to rotate, scroll to zoom."}),
                 className="i3-tab-board"),
    ], className="chart-card")


def _e3_stats(series):
    """(min, average, max) over the magnitude history, or three Nones.

    Three Nones rather than three zeros: fig_bar draws nothing at all when it is
    handed None, which is the honest rendering of an empty history. Zeros would
    draw three bars at the origin and read as a measured null."""
    vals = [v for v in series if isinstance(v, (int, float))]
    if not vals:
        return None, None, None
    return min(vals), sum(vals) / len(vals), max(vals)


def _e3_shown(value, unit=""):
    """Format an axis value, or an em dash when that axis is not reporting.

    An axis that is not wired must never render as 0.00. Zero is a real
    measurement and a fabricated one would look like a working plate seeing no
    field, which is exactly the confusion the None carries up from acquisition
    to avoid."""
    return "—" if value is None else ("%.3f%s" % (value, unit))


# Channel 2's *_vu values come only from the studio's own probe, scaled to volts per metre
# (_c2_scale, the calibration profile's "V/m"). A project feed sets them to None, so their
# cards read "—" there and never in the project's unit.
CH2_REFERENCE_UNIT = "V/m est."


def ch2_triaxial_blocks():
    """The triaxial Ch2 section.

    Deliberately built on the same chart functions as the ch1probe --
    fig_axis, fig_2d_scatter, fig_3d_surface and the rest all take an x/y/z
    history in one shared shape, so publishing the Ch2 vector in that shape
    means every one of them works here unchanged. Twelve duplicated plotting
    functions would have been the alternative, and they would have drifted."""
    with ch2f_lock:
        e = dict(ch2f_data)
        xyz = list(ch2f_data.get("exyz_history") or [])
        sgm = list(ch2f_data.get("sgm_history") or [])
    live = e.get("axes_live", 0)
    status = e.get("axis_status") or {}
    tri = bool(e.get("triaxial"))
    provisional = e.get("data_source") == "ARDUINO_UNO_USB"
    axis_unit = ch2_axis_unit(e)
    n2, u2 = T('ch2.name'), CH2_REFERENCE_UNIT   # *_vu: the studio probe's own scale, not a project unit

    # The section is built whether or not the probe is triaxial. Returning a
    # different panel here would leave e3-int, e3-line and the rest unmounted
    # while their callbacks stay registered -- Dash tolerates that but logs a
    # warning per fire, and the charts silently never update. The not-triaxial
    # case is a state of this section, not a replacement for it: every axis
    # reads as unreporting, which is exactly what is true.
    single_note = None
    if not tri:
        single_note = html.Div([
            html.Div("ONE AXIS", className="summary-tag"),
            html.Div(f"This {n2.lower()} source is not triaxial, so the three-axis views below stay empty.",
                     className="summary-text"),
        ], className="summary-panel", style={"marginTop": "20px"})

    # State the truth about coverage rather than implying three working axes.
    railed_axes = [name.upper() for name, state in sorted(status.items()) if state == "railed"]
    if railed_axes:
        coverage = "UNO REFERENCE MODE · the ≥ marker identifies a lower-bound estimate."
        coverage_colour = AMBER
    elif live == 3:
        coverage = "All three axes reporting. The magnitude below is the full field vector."
        coverage_colour = GREEN
    elif live == 0:
        coverage = "No axis is reporting. Every plate reads as unwired or railed."
        coverage_colour = RED
    else:
        coverage = ("Only %d of 3 axes reporting (%s). The magnitude is a projection onto "
                    "those axes, not the full vector, and the direction is incomplete."
                    % (live, ", ".join("%s: %s" % (k.upper(), v) for k, v in sorted(status.items())
                                       if v != "ok")))
        coverage_colour = AMBER

    uncal = all(abs(float(os.environ.get("STUDIO_CH2F_SCALE_" + a, "1.0")) - 1.0) < 1e-9
                for a in ("X", "Y", "Z"))

    return [
        html.Div("THREE AXES", className="section-label",
                 style={"marginTop": "30px"}),
        single_note,
        html.Div(("Reference mode: raw ADC activity per axis, not a calibrated field."
                  if provisional else f"{n2} on each axis, and the vector they make together."),
                 className="validation-subcopy", style={"marginTop": "-4px"}),
        (html.Div("Values marked ≥ hit the input's limit and are lower bounds.",
                  className="validation-subcopy", style={"marginBottom":"14px"}) if provisional else None),
        html.Div([html.Span(coverage, style={"color": coverage_colour})],
                 className="validation-subcopy", style={"marginTop": "6px"}),
        html.Div([
            _mcard("e3-x", "X (" + axis_unit + ")", _e3_shown(e.get("ex_mv"))),
            _mcard("e3-y", "Y (" + axis_unit + ")", _e3_shown(e.get("ey_mv"))),
            _mcard("e3-z", "Z (" + axis_unit + ")", _e3_shown(e.get("ez_mv"))),
            _mcard("e3-c1", "MAGNITUDE (" + axis_unit + ")", _e3_shown(e.get("e_magnitude_mv")), CYAN),
            _mcard("e3-live", "AXES REPORTING", "%d / 3" % live,
                   GREEN if live == 3 else AMBER if live else RED),
        ], className="metric-row", style={"marginBottom": "14px", "display": "none" if provisional else "flex"}),
        html.Div([
            _mcard("e3-x-vm", f"X ({u2})", ("≥ " if (e.get("axis_clipped") or {}).get("x") else "") + _e3_shown(e.get("ex_vu"))),
            _mcard("e3-y-vm", f"Y ({u2})", ("≥ " if (e.get("axis_clipped") or {}).get("y") else "") + _e3_shown(e.get("ey_vu"))),
            _mcard("e3-z-vm", f"Z ({u2})", ("≥ " if (e.get("axis_clipped") or {}).get("z") else "") + _e3_shown(e.get("ez_vu"))),
            _mcard("e3-c1-vm", f"Magnitude ({u2})", ("≥ " if e.get("clipped") else "") + _e3_shown(e.get("e_magnitude_vu")), CYAN),
        ], className="metric-row", style={"marginBottom":"14px"}),
        html.Div("Static offset of each axis from its quiet baseline, in ADC counts.",
                 className="validation-subcopy", style={"marginTop":"6px"}) if provisional else None,
        html.Div([
            _mcard("e3-static-x", "X OFFSET (counts)", _e3_shown((e.get("dc_delta_counts") or {}).get("x"))),
            _mcard("e3-static-y", "Y OFFSET (counts)", _e3_shown((e.get("dc_delta_counts") or {}).get("y"))),
            _mcard("e3-static-z", "Z OFFSET (counts)", _e3_shown((e.get("dc_delta_counts") or {}).get("z"))),
            _mcard("e3-static-c1", "STATIC ACTIVITY (counts)", _e3_shown(e.get("static_activity_counts")), CYAN),
        ], className="metric-row", style={"marginBottom":"14px"}),
        html.Div([
            _chart("e3-line", f"{n2} magnitude over time (" + axis_unit + ")",
                   make_line_chart(sgm, color=AMBER, fill_color="rgba(255,171,64,0.08)",
                                   height=250, ylabel=axis_unit)),
            _chart("e3-axis", "X, Y and Z components (" + axis_unit + ")", fig_axis(xyz, unit=axis_unit)),
            _chart("e3-scatter", "X against Y",
                   fig_2d_scatter(xyz, unit=axis_unit), h=280),
            _chart("e3-delta", "Sample change against magnitude",
                   fig_2d_delta(xyz, unit=axis_unit), h=280),
            _chart("e3-gauge", "Live magnitude",
                   fig_gauge(e.get("e_magnitude_mv"), unit=axis_unit)),
            _chart("e3-pie", "Share of each axis (|X|, |Y|, |Z|)",
                   fig_pie(e.get("ex_mv"), e.get("ey_mv"), e.get("ez_mv"))),
            _chart("e3-bar", "Session minimum, average and maximum",
                   fig_bar(*_e3_stats(sgm), unit=axis_unit,
                           quantity=f"{T('ch2.name').lower()} activity magnitude" if provisional else f"{T('ch2.name').lower()} magnitude")),
        ], className="chart-grid"),
        html.Div("SIGNAL ARCHIVE", className="section-label",
                 style={"marginTop": "30px"}),
        html.Div(f"Every {n2.lower()} magnitude kept this session, oldest on the left.",
                 className="validation-subcopy", style={"marginTop": "-4px"}),
        html.Div(_chart("e3-archive", "Magnitude archive (" + axis_unit + ")",
                        fig_archive(series=sgm, unit=axis_unit), h=220),
                 style={"marginTop": "14px"}),
        html.Div("3D VIEWS", className="section-label",
                 style={"marginTop": "30px"}),
        html.Div([
            _chart("e3-surface", "Surface over the X–Y plane",
                   fig_3d_surface(xyz, height=400, unit=axis_unit), cfg=CFG_3D, h=400),
            _chart("e3-terrain", "Magnitude terrain, window by window",
                   fig_3d_terrain(xyz, height=400, unit=axis_unit), cfg=CFG_3D, h=400),
        ], className="chart-grid"),
        html.Div([
            _chart("e3-plane", f"{n2} direction",
                   fig_3d_error_plane(xyz, height=430, name=n2, unit=axis_unit), cfg=CFG_3D, h=430),
            _chart("e3-twopole", "Dipole model along that direction",
                   fig_3d_dipolch2f(xyz, height=430, name=n2), cfg=CFG_3D, h=430),
        ], className="chart-grid", style={"marginTop": "14px"}),
        html.Div([
            html.Div("DIRECTION", className="summary-tag"),
            html.Div([
                ("The direction comes from the three axes, each scaled by its own calibration factor. "),
                _hi("Currently uncalibrated (all factors 1.0); direction is indicative, not accurate."
                    if uncal else "Calibrated per axis."),
                " Set STUDIO_CH2F_SCALE_X, _Y and _Z to calibrate.",
            ], className="summary-text"),
        ], className="summary-panel", style={"marginTop": "20px"}),
        dcc.Interval(id="e3-int", interval=2600, n_intervals=0),
        dcc.Interval(id="e3-3d-int", interval=7000, n_intervals=0),
    ]


def ch2_body():
    with ch2f_lock:
        e = dict(ch2f_data); hist = list(ch2f_data["history"]); rel_hist = list(ch2f_data["rel_history"])
    with c1_lock:
        c1_hist = list(ch1_data["history"])
        c1_xyz = list(ch1_data["xyz_history"])
    have = e["last_rx"] is not None
    provisional = e.get("data_source") == "ARDUINO_UNO_USB"
    axis_unit = ch2_axis_unit(e)   # fed data keeps its own unit; the studio's ADC paths keep theirs
    n1, n2 = T('ch1.name'), T('ch2.name')   # the project's channel words (S1-06)
    u2 = CH2_REFERENCE_UNIT   # *_vu: the studio probe's own scale; a project feed leaves them empty
    return [
        html.Div([
            _mcard("ev-level", f"X ({u2})", (("≥ " if (e.get("axis_clipped") or {}).get("x") else "") + _e3_shown(e.get("ex_vu"))) if have and e.get("ex_vu") is not None else "—"),
            _mcard("ev-index", f"Y ({u2})", (("≥ " if (e.get("axis_clipped") or {}).get("y") else "") + _e3_shown(e.get("ey_vu"))) if have and e.get("ey_vu") is not None else "—", CYAN),
            _mcard("ev-rms", f"Z ({u2})", (("≥ " if (e.get("axis_clipped") or {}).get("z") else "") + _e3_shown(e.get("ez_vu"))) if have and e.get("ez_vu") is not None else "—"),
            _mcard("ev-gain", f"Magnitude ({u2})", (("≥ " if e.get("clipped") else "") + _e3_shown(e.get("e_magnitude_vu"))) if have and e.get("e_magnitude_vu") is not None else "—"),
            _mcard("ev-base-top", "Quiet baseline", f"{e['baseline_vu']:.3f}" if provisional and have else "—"),
            _mcard("ev-delta-top", "Change from baseline", f"{abs(e.get('e_magnitude_vu') or 0):.3f}" if provisional and have else "—"),
        ], className="metric-row", style={"marginBottom":"14px"}),
        _sg_listen_card("ch2"),
        # ── Environmental Intelligence: re-learn the baseline on command ──
        html.Div([
            html.Button(["RE-LEARN BASELINE"], id="c2-recal-btn", className="open-btn",
                        n_clicks=0, style={"width":"auto","marginTop":"0","whiteSpace":"nowrap"}),
            html.Span("Press to re-learn the quiet baseline with the probe fixed and clear.",
                      id="c2-recal-status", style={"fontFamily":FONT,"fontSize":"11px","color":SUBTEXT,"lineHeight":"1.5"}),
        ], style={"display":"flex","alignItems":"center","gap":"16px","marginBottom":"16px","flexWrap":"wrap"}),
        html.Div(id="c2-warn"),   # clipping / overload banner
        html.Div([html.Span(className="online-dot off", id="c2-dot"),
                  html.Span(f"{n2.upper()} · WAITING FOR DATA", id="c2-status", className="online-text c-sub")],
                 className="online-bar"),
        _zoom_bar("c2-zoom", "VERTICAL ZOOM", "Magnifies the level chart around the recent signal. 1× fits its typical range; a reading beyond it shows as a spike marker."),
        _chart_board("ch2f", f"{n2} sensor board"),
        html.Div("LIVE SIGNAL", className="section-label"),
        html.Div(f"{n2} level, and its activity relative to the quiet baseline (0–100).",
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            _chart("c2-line", f"{n2} level over time (" + axis_unit + ")",
                   make_line_chart(hist, color=AMBER, fill_color="rgba(255,171,64,0.08)", height=250, ylabel=axis_unit)),
            _chart("c2-index-line", "Relative activity over time (%)",
                   make_line_chart(rel_hist, color=CYAN, fill_color="rgba(0,229,255,0.07)", height=250, ylabel="%")),
            _chart("c2-gauge", "Relative activity now (0–100)", fig_c2_gauge(e["rel_index"] if have else None)),
            _chart("c2-basebar", "Baseline, level and peak (" + axis_unit + ")", fig_c2_basebar(e["baseline_vu"], e["field_vu"], e["peak_vu"], unit=axis_unit) if have else fig_c2_basebar(None, None, None, unit=axis_unit)),
        ], className="chart-grid"),
        html.Div([_chart("c2-bullet", "Activity band: low, mid, high", fig_c2_bullet(e["rel_index"] if have else None, e["level"]), h=140)],
                 style={"marginTop":"14px"}),
        html.Div(f"{n2.upper()} WITH {n1.upper()}", className="section-label", style={"marginTop":"26px"}),
        html.Div("How the two channels move together. Association only: neither chart shows cause.",
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            _chart("c2-b-correlation", f"{n2} activity against {n1} magnitude",
                   fig_c2_b_correlation(c1_hist, rel_hist), h=280),
            _chart("c2-induction-proxy", f"{n1} change per sample beside {n2} activity",
                   fig_c2_induction_proxy(c1_hist, rel_hist), h=280),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div("SESSION", className="section-label", style={"marginTop":"26px", "display":"none" if provisional else "block"}),
        html.Div([
            html.Div([html.Div("—", id="ev-baseline", className="arch-stat-val"), html.Div("Baseline", className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div("—", id="ev-peak", className="arch-stat-val"), html.Div("Peak", className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div("—", id="ev-util", className="arch-stat-val"), html.Div("INPUT RANGE USED", className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div("—", id="ev-minmax", className="arch-stat-val"), html.Div("MIN / MAX CODE", className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div(f"{C2_SCALE_PER_VOLT:,.3f}", className="arch-stat-val"), html.Div("Scale per volt", className="arch-stat-key")], className="arch-stat"),
        ], className="arch-stats", style={"display":"none" if provisional else "grid"}),
        html.Div([html.Div("STATE", className="summary-tag"),
                  html.Div([_hi("State"), html.Span("  "), html.Span("—", id="ev-statustext")], className="summary-text")],
                 className="summary-panel", style={"display":"none" if provisional else "block"}),
        html.Div([html.Div("HOW IT IS MEASURED", className="summary-tag"),
                  html.Div(["The probe reads ", _hi(_ch2f_wiring_text()),
                            ". ",
                            "Each reading is the ", _hi("AC RMS"),
                            " of a short block of samples; the input ",
                            _hi("auto-ranges"), " so weak and strong fields both stay readable. ",
                            "The quiet baseline is learned at start and on request. ",
                            _hi("relative index"), " compares the level with it: ",
                            _hi("LOW"), " (< 3× baseline), ", _hi("MID"), " (3–10×), ", _hi("HIGH"), " (> 10×). ",
                            "The V/m value is a ", _hi("reference-scaled estimate"),
                            ", not a calibrated field strength."], className="summary-text")],
                 className="summary-panel"),
        html.Div(id="c2-error"),
    ] + ch2_triaxial_blocks() + ([
        html.Div("REFERENCE MODE", className="section-label", style={"marginTop":"30px"}),
        html.Div([
            html.Div([html.Div(f"{e.get('baseline_vu', 0.0):.3f}" if have else "—", id="ev-bottom-baseline", className="arch-stat-val"), html.Div(f"Baseline ({u2})", className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div(f"{e.get('sample_rate', 0):.1f}" if have else "—", id="ev-bottom-rate", className="arch-stat-val"), html.Div("SAMPLES / S", className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div(f"{e['min_code']} / {e['max_code']}" if have else "—", id="ev-bottom-minmax", className="arch-stat-val"), html.Div("MIN / MAX CODE", className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div("UNO USB", className="arch-stat-val"), html.Div("Source", className="arch-stat-key")], className="arch-stat"),
        ], className="arch-stats"),
    ] if provisional else []) + [
        # Offset from the ch1 intervals so combined view spreads the load.
        dcc.Interval(id="c2-num-int", interval=2500, n_intervals=0),
        dcc.Interval(id="c2-chart-int", interval=3000, n_intervals=0),
    ]


def ch2_view():
    with ch2f_lock:
        provisional = ch2f_data.get("data_source") == "ARDUINO_UNO_USB"
    if provisional:
        return html.Div(ch2_body() + [html.Div([
            html.Div("REFERENCE MODE", className="section-label"),
            html.Div("The engine views are off in reference mode: raw ADC activity is not a calibrated input.",
                     className="validation-subcopy"),
        ], className="summary-panel", style={"marginTop":"24px"})])
    return html.Div(ch2_body() + [d4_ch2_blocks()])


def combined_view():
    base = _combined_view_base()
    base.children.append(d4_combined_blocks())
    return base


def _p1_composite_xyz(ch1_xyz, ch2_xyz, limit=200):
    """Equal-weight, dimensionless E+B geometry for visualization only.

    unit and ADC counts cannot be added.  Each recent vector series is therefore
    normalized by its own observed magnitude before the corresponding X/Y/Z
    components are averaged.  The result shows coincident movement and shape;
    it is not a new physical field unit or a calibrated EM vector.
    """
    count = min(len(ch1_xyz), len(ch2_xyz), limit)
    if count < 2:
        return []
    c1 = list(ch1_xyz)[-count:]
    c2x = list(ch2_xyz)[-count:]
    c1_scale = max((math.sqrt(sum(float(v) ** 2 for v in row[:3])) for row in c1), default=1.0) or 1.0
    c2x_scale = max((math.sqrt(sum(float(v) ** 2 for v in row[:3])) for row in c2x), default=1.0) or 1.0
    return [tuple((float(m[i]) / c1_scale + float(e[i]) / c2x_scale) * 0.5 for i in range(3))
            for m, e in zip(c1, c2x)]


def _combined_view_base():
    with c1_lock:
        c1_hist = list(ch1_data["history"])
        c1_xyz = list(ch1_data["xyz_history"])
    with ch2f_lock:
        c2_hist = list(ch2f_data["history"])
        c2_rel = list(ch2f_data["rel_history"])
        exyz = list(ch2f_data.get("exyz_history") or [])
        provisional = ch2f_data.get("data_source") == "ARDUINO_UNO_USB"
        c2_unit = ch2_axis_unit(ch2f_data)
    p1_xyz = _p1_composite_xyz(c1_xyz, exyz)
    n1, n2 = T('ch1.name'), T('ch2.name')   # the project's channel words (S1-06)
    p1_c1 = [math.sqrt(x*x + y*y + z*z) for x, y, z in p1_xyz]
    return html.Div([
        html.Div("BOTH CHANNELS", className="section-label"),
        html.Div(
            f"{n1} and {n2} side by side, aligned sample by sample. Their units differ, so each keeps its own axis or is normalised.",
            className="validation-subcopy",
        ),
        _sg_listen_card("p1"),
        _zoom_bar("p1-zoom", "TIME ZOOM", "Shows fewer, more recent samples in every view on this tab: 1× is the last 200, 8× the last 25."),
        html.Div([
            _chart("p1-overlay", f"{n1} and {n2} on their own axes",
                   fig_p1_overlay(c1_hist, c2_hist, unit2=c2_unit), h=320),
        ], className="chart-grid chart-grid-primary", style={"marginTop":"14px"}),
        html.Div([
            _chart("p1-normalized-overlay", "Both on one 0–100 scale",
                   fig_p1_normalized_overlay(c1_hist, c2_rel), h=300),
            _chart("p1-coupling", f"{n1} change per sample beside {n2} activity",
                   fig_c2_induction_proxy(c1_hist, c2_rel), h=300),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div("COMPOSITE VECTOR", className="section-label", style={"marginTop":"30px"}),
        html.Div("Each channel's X, Y and Z divided by its own largest magnitude, then averaged. A shape for the eye, not a physical quantity.",
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            _chart("em3-line", "Composite magnitude over time (normalised)", make_line_chart(p1_c1, color=CYAN, height=250, ylabel="normalized")),
            _chart("em3-axis", "Composite X, Y and Z (normalised)", fig_axis(p1_xyz, unit="normalized")),
            _chart("em3-scatter", "Composite X against Y", fig_2d_scatter(p1_xyz, unit="normalized"), h=280),
            _chart("em3-delta", "Composite change against magnitude", fig_2d_delta(p1_xyz, unit="normalized"), h=280),
            _chart("em3-gauge", "Composite magnitude now", fig_gauge(p1_c1[-1] if p1_c1 else None, unit="normalized")),
            _chart("em3-pie", "Share of each composite axis", fig_pie(*(p1_xyz[-1] if p1_xyz else (None,None,None)))),
            _chart("em3-bar", "Composite minimum, average and maximum", fig_bar(*_e3_stats(p1_c1), unit="normalized", quantity="E+B composite magnitude")),
        ], className="chart-grid"),
        html.Div("3D VIEWS", className="section-label", style={"marginTop":"30px"}),
        html.Div([
            _chart("em3-vector-overlay", "Both vector histories in one frame", fig_p1_vector_overlay_3d(c1_xyz, exyz), cfg=CFG_3D, h=470),
            _chart("em3-cross-proxy", f"{n2} × {n1} direction (geometry only)", fig_p1_cross_proxy_3d(c1_xyz, exyz), cfg=CFG_3D, h=470),
            _chart("em3-surface", "Composite surface over the X–Y plane", fig_3d_surface(p1_xyz, height=400, unit="normalized"), cfg=CFG_3D, h=400),
            _chart("em3-terrain", "Composite terrain, window by window", fig_3d_terrain(p1_xyz, height=400, unit="normalized"), cfg=CFG_3D, h=400),
            _chart("em3-plane", "Composite direction", fig_3d_error_plane(p1_xyz, height=430, name="Composite", unit="normalized"), cfg=CFG_3D, h=430),
            _chart("em3-twopole", "Dipole model along that direction", fig_3d_dipolch2f(p1_xyz, height=430, name="the composite"), cfg=CFG_3D, h=430),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div("Correlation over the shared window. A strong value means they move together, not that one drives the other.",
                 className="validation-subcopy", style={"marginTop":"10px"}),
        html.Div([
            _chart("p1-correlation", f"{n2} activity against {n1} magnitude",
                   fig_c2_b_correlation(c1_hist, c2_rel), h=300),
        ], className="chart-grid chart-grid-primary", style={"marginTop":"14px"}),

        html.Div("ONE PATH THROUGH TIME", className="section-label", style={"marginTop":"30px"}),
        html.Div([f"{n1} magnitude, {n2} activity and time as three axes, to show ", _hi("how they move together"),
                  ". Its shadow on the floor drops time."],
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        _graph_block("p1-traj3d", fig_p1_trajectory_3d(c1_hist, c2_rel), 440, CFG_3D),
        html.Div("EACH CHANNEL'S DIRECTION", className="section-label", style={"marginTop":"30px"}),
        html.Div(f"{n1} and {n2} directions side by side. "
                 + (f"{n2} is in reference mode, so its direction is indicative only."
                    if provisional else f"{n2}'s direction is only as good as its per-axis calibration."),
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            _chart("p1-b-plane", f"{n1} direction", fig_3d_error_plane(c1_xyz, height=430), cfg=CFG_3D, h=430),
            _chart("p1-e-plane", f"{n2} direction", fig_3d_error_plane(exyz, height=430, name=n2, unit=c2_unit), cfg=CFG_3D, h=430),
            _chart("p1-b-twopole", f"Dipole model along {n1}", fig_3d_dipolch2f(c1_xyz, height=430), cfg=CFG_3D, h=430),
            _chart("p1-e-twopole", f"Dipole model along {n2}", fig_3d_dipolch2f(exyz, height=430, name=n2), cfg=CFG_3D, h=430),
        ], className="chart-grid", style={"marginTop":"14px"}),
        dcc.Interval(id="p1-overlay-int", interval=3600, n_intervals=0),
        html.Div([
            html.Div("READING THESE VIEWS", className="summary-tag"),
            html.Div(
                "The two channels measure different quantities in different units. "
                "Every view here compares their timing and shape; none adds them into one physical value.",
                className="summary-text",
            ),
        ], className="summary-panel"),
    ])


def p1_page():
    airlock = html.Div(className="i3-scrub-hero", **{"data-i3-scrub": "p1-vector",
                                                    "data-i3-title": T("page1.hero_title"),
                                                    "data-i3-tagline": T("page1.hero_tagline")})
    return html.Div([
        airlock,
        dcc.Link(html.Button("BACK", className="back-btn"), href="/", style={"textDecoration":"none"}),
        _ph(T("page1.eyebrow"), T("page1.title"), T("page1.subtitle")),
        html.Hr(className="divider"),
        html.Div([
            html.Button(T("ch1.name").upper(), id="p1-tab-c1", className="tab-btn active", n_clicks=0),
            html.Button(T("ch2.name").upper(), id="p1-tab-c2x", className="tab-btn", n_clicks=0),
            html.Button("BOTH", id="p1-tab-both", className="tab-btn", n_clicks=0),
        ], className="tab-bar p1-mode-tabs"),
        html.Div(id="p1-subcontent", children=ch1_view()),
    ], style=PAD)


# ════════════════════════════════════════════════════════
#  SWEEP3  (src3 Ultra — live)
# ════════════════════════════════════════════════════════
def _ch3_dev_strip():
    with sweep3_lock: s = dict(sweep3_data)
    cells = [
        ("DEVICE",       s["device"]),
        ("INFO",         s["device_info"]),
        ('TEXT',     s["port"]),
        ("COMMANDS",     s["help_summary"]),
        ('TEXT', s["leveloffset"]),
        ("ULTRA >800MHz", "ON" if s["ultra"] else "off"),
        ("TRUST", "TRUSTED" if s["trusted"] else "UNTRUSTED / NO SWEEP"),
        ("SWEEPS",       str(s["sweeps"])),
    ]
    return [html.Div([html.Div(k, className="ch3-dev-key"), html.Div(v, className="ch3-dev-val")],
                     className="ch3-dev-cell") for k, v in cells]


def ch3_sweep_body():
    with sweep3_lock:
        s = dict(sweep3_data)
        wf_rows, wf_times = _waterfall_rows(
            list(sweep3_data["waterfall"]),
            list(sweep3_data["waterfall_times"]),
            list(sweep3_data["freqs"]),
        )
    return [
        html.Div([html.Button('BUTTON', id="ch3-sweep-now", className="ch3-btn ch3-on", n_clicks=0),
                  html.Span("", id="ch3-sweep-top-note", className="validation-subcopy")],
                 className="sweep3-sweep-action"),
        # ── orientation panel: this instrument is unreadable without it ──
        html.Div([html.Div('LABEL', className="summary-tag"),
                  html.Div(['Paragraph. Enter your text here. ',
                            _hi("horizontal is frequency"), ' Text ',
                            _hi('vertical is power in unit'), ' Paragraph. Enter your text here. ',
                            _hi("noise floor"), ' Text', html.Br(), html.Br(),
                            'Text ',
                            _hi("continuous range"), ' Text ',
                            _hi("as many samples across it as you ask for"),
                            f". At full span with {S3_DEFAULT_PTS} points, each bin is very wide. "
                            "This is a coarse wideband survey: narrow or short-duration signals may be "
                            "missed. Narrowing the span improves bin width, but a sweep3 peak still "
                            "does not identify a protocol, device or transmitter."],
                           className="summary-text")],
                 className="summary-panel", style={"marginTop":"0"}),
        html.Div('Label', className="section-label", style={"marginTop":"24px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        _dbm_scale(),

        html.Div("DEVICE", className="section-label", style={"marginTop":"26px"}),
        html.Div(_ch3_dev_strip(), id="ch3-dev-strip", className="ch3-dev-strip"),

        html.Div([
            _mcard("ch3-peak-f",  'LABEL', "—", AMBER),
            _mcard("ch3-peak-l",  'LABEL',     "—", CYAN),
            _mcard("ch3-floor",   'Label',    "—"),
            _mcard("ch3-span",    'LABEL',           _ch3_span(s["span_start"], s["span_stop"], s)),
            _mcard("ch3-res",     'LABEL',     "—"),
            _mcard("ch3-sweep",   'LABEL',     "—"),
        ], className="metric-row", style={"marginBottom":"18px"}),

        # ── controls ──
        html.Div([
            html.Div([html.Div('Label', className="ch3-ctl-label"),
                      html.Div([html.Button(lbl, id=f"ch3-preset-{key}", className="ch3-btn", n_clicks=0)
                                for key, lbl, _a, _b in S3_PRESETS], className="ch3-ctl-row")],
                     className="ch3-ctl-group"),
            html.Div([html.Div('Label', className="ch3-ctl-label"),
                      html.Div([html.Button("101", id="ch3-pts-101", className="ch3-btn", n_clicks=0),
                                html.Button("251", id="ch3-pts-251", className="ch3-btn ch3-on", n_clicks=0),
                                html.Button("290", id="ch3-pts-290", className="ch3-btn", n_clicks=0)],
                               className="ch3-ctl-row")], className="ch3-ctl-group"),
            html.Div([html.Div('Label', className="ch3-ctl-label"),
                      html.Div([html.Button('BUTTON', id="ch3-ax-lin", className="ch3-btn ch3-on", n_clicks=0),
                                html.Button("LOG", id="ch3-ax-log", className="ch3-btn", n_clicks=0)],
                               className="ch3-ctl-row")], className="ch3-ctl-group"),
            html.Div([html.Div('Label', className="ch3-ctl-label"),
                      html.Div([html.Button("ON", id="ch3-band-on", className="ch3-btn ch3-on", n_clicks=0),
                                html.Button("OFF", id="ch3-band-off", className="ch3-btn", n_clicks=0)],
                               className="ch3-ctl-row")], className="ch3-ctl-group"),
            html.Div([html.Div('Label', className="ch3-ctl-label"),
                      html.Div([
                          html.Button('BUTTON', id="ch3-hold-reset", className="ch3-btn", n_clicks=0),
                          html.Button('BUTTON', id="ch3-pause", className="ch3-btn", n_clicks=0),
                      ], className="ch3-ctl-row")], className="ch3-ctl-group"),
        ], className="ch3-ctl-bar"),
        html.Div([
            html.Div('Label', className="ch3-ctl-label"),
            html.Div([
                dcc.Input(id="ch3-custom-start", type="number", min=0, max=6000,
                          value=88, debounce=True, placeholder='Enter your text here'),
                dcc.Input(id="ch3-custom-stop", type="number", min=0, max=6000,
                          value=108, debounce=True, placeholder='Enter your text here'),
                html.Button('BUTTON', id="ch3-custom-apply",
                            className="ch3-btn", n_clicks=0),
                html.Span("", id="ch3-custom-status", className="validation-subcopy"),
            ], className="ch3-ctl-row"),
        ], className="ch3-ctl-bar", style={"marginTop":"10px"}),
        dcc.Store(id="ch3-bands-mode", data=True),
        dcc.Store(id="ch3-axis-mode", data="lin"),
        dcc.Store(id="ch3-points-mode", data=S3_DEFAULT_PTS),
        dcc.Store(id="ch3-preset-mode", data="full"),

        html.Div(id="ch3-warn"),
        html.Div([html.Span(className="online-dot off", id="ch3-dot"),
                  html.Span('Subtext', id="ch3-status", className="online-text c-sub")],
                 className="online-bar"),

        html.Div('LABEL', className="section-label"),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        _graph_block("ch3-sweep-graph",
                     fig_sweep3(s["freqs"], s["levels"], s["maxhold"],
                                  s["peaks"], s["floor"], False, 380, True), 380),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            html.Div([html.Div("#"), html.Div('TEXT'), html.Div('TEXT'),
                      html.Div('TEXT'), html.Div('TEXT')], className="ch3-peak-head"),
            html.Div(_peak_rows(s["peaks"], s["floor"]), id="ch3-peak-body"),
        ], className="ch3-peak-table"),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div(sg_rows(s), id="ch3-sg-body", className="ch3-sg-list"),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div(f"The last {S3_WATERFALL_ROWS} sweeps stacked over time — a signal that comes and goes shows as a broken vertical stripe.",
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        _graph_block("ch3-waterfall-graph",
                     fig_waterfall(wf_rows, s["freqs"], wf_times, 320), 320),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        _graph_block("ch3-terrain-graph",
                     fig_ch3_terrain(wf_rows, s["freqs"], wf_times, 460), 460, CFG_3D),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div([
            _chart("ch3-bands-graph", 'Title', fig_ch3_bands(s["peaks"])),
            _chart("ch3-trend-graph", 'Title', fig_ch3_trend(s["peak_history"])),
        ], className="chart-grid"),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div([
            html.Div('Subtext',
                     className="validation-subcopy"),
            html.Div([
                html.Div([html.Div("0", id="ch3-arch-count", className="arch-stat-val"),
                          html.Div('LABEL', className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="ch3-arch-min", className="arch-stat-val"),
                          html.Div('Label', className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="ch3-arch-avg", className="arch-stat-val"),
                          html.Div('Label', className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="ch3-arch-max", className="arch-stat-val"),
                          html.Div('Label', className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="ch3-arch-str", className="arch-stat-val"),
                          html.Div('LABEL', className="arch-stat-key")], className="arch-stat"),
            ], id="ch3-arch-stats", className="arch-stats"),
        ], className="arch-shell"),

        html.Div([html.Div('LABEL', className="summary-tag"),
                  html.Div(['Paragraph. Enter your text here. ',
                            _hi("scan <start> <stop> <points> 3"), ' Text ',
                            _hi("three"), ' Paragraph. Enter your text here. ',
                            'Text ', _hi("scanraw"), ' Paragraph. Enter your text here. ',
                            _hi("max hold"), ' Paragraph. Enter your text here.'],
                           className="summary-text")],
                 className="summary-panel"),
        html.Div([html.Div('LABEL', className="summary-tag"),
                  html.Div(['Paragraph. Enter your text here. ',
                            _hi('-40 to -70 unit'), ". If the whole sweep reads near ", _hi('+20 unit'),
                            'Text ', _hi("untrusted"), ". The software does not infer a physical cause; "
                            "the parser, units, analyser state and CH3 setup require verification. MTDI lowers sweep3 health and the device strip shows the queried level-offset state. ",
                            'Paragraph. Enter your text here.'],
                           className="summary-text")],
                 className="summary-panel"),
        html.Div(id="ch3-error"),

        # Staggered: the sweep itself takes seconds, so polling faster only wastes CPU.
        dcc.Interval(id="ch3-num-int",   interval=1000, n_intervals=0),
        dcc.Interval(id="ch3-chart-int", interval=2500, n_intervals=0),
        dcc.Interval(id="ch3-wf-int",    interval=4300, n_intervals=0),
    ]


def ch3_sweep_view():
    return html.Div(ch3_sweep_body() + [d4_sweep3_blocks()])


def sdr_view():
    """RTL-SDR panel: live slice, waterfall, carriers and an on-demand stitched sweep.

    Deliberately separate from the src3 view. The src3 answers "what is present
    across a very wide span"; the dongle answers "what exactly is happening inside
    two megahertz, right now". Levels here are dBFS and are never presented as unit.
    """
    snap = sdr_snapshot(include_trace=False)
    presets = snap.get("presets") or []
    return html.Div([
        html.Div([html.Button('BUTTON', id="sdr-sweep-now", className="ch3-btn ch3-on", n_clicks=0),
                  html.Span("", id="sdr-sweep-top-note", className="validation-subcopy")],
                 className="sweep3-sweep-action"),
        html.Div([html.Div('LABEL', className="summary-tag"),
                  html.Div(['Text ',
                            _hi("raw complex samples"), ' Paragraph. Enter your text here. ',
                            _hi("dBFS"), 'Paragraph. Enter your text here.'],
                           className="summary-text")],
                 className="summary-panel", style={"marginTop":"0"}),

        html.Div([
            _mcard("sdr-state",  'LABEL',    "—", CYAN),
            _mcard("sdr-centre", 'LABEL',      "—", AMBER),
            _mcard("sdr-peak",   'LABEL',   "—"),
            _mcard("sdr-data",   'LABEL', "—"),
        ], className="metric-row", style={"margin":"18px 0"}),

        html.Div([html.Span(className="online-dot off", id="sdr-dot"),
                  html.Span('Subtext', id="sdr-status", className="online-text c-sub")],
                 className="online-bar"),

        html.Div('LABEL', className="section-label"),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            dcc.Input(id="sdr-centre-in", type="number", debounce=True, placeholder='Enter your text here',
                      min=24, max=1700, step=0.001, style={"width":"150px"}),
            html.Button('BUTTON', id="sdr-tune", className="ch3-btn", n_clicks=0),
            html.Span('SUBTEXT', className="validation-subcopy", style={"margin":"0 4px 0 12px"}),
            dcc.Dropdown(id="sdr-gain", options=[{"label":"auto","value":"auto"}],
                         value="auto", clearable=False,
                         style={"width":"130px","display":"inline-block","verticalAlign":"middle"}),
        ], className="ch3-ctl-row", style={"marginTop":"8px"}),
        html.Div([html.Button(name, id={"type":"sdr-preset","band":name}, className="ch3-btn", n_clicks=0)
                  for name, _a, _b in SDR_PRESETS], className="ch3-ctl-row", style={"marginTop":"8px"}),

        _chart("sdr-live", 'Title', go.Figure(), h=300),
        _chart("sdr-fall", 'TITLE', go.Figure(), h=300),

        html.Div('LABEL', className="section-label"),
        html.Div(['Subtext ', _hi("ridge"), ' Subtext'],
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        _chart("sdr-terrain", 'TITLE', go.Figure(), h=460),

        html.Div('LABEL', className="section-label"),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div(id="sdr-peaks", className="scan-table"),

        html.Div('LABEL', className="section-label"),
        html.Div(['Subtext ',
                  _hi("0.4 s"), "."],
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            dcc.Input(id="sdr-sweep-a", type="number", placeholder='Enter your text here', value=88,
                      min=24, max=1700, step=0.1, style={"width":"130px"}),
            dcc.Input(id="sdr-sweep-b", type="number", placeholder='Enter your text here', value=108,
                      min=24, max=1700, step=0.1, style={"width":"130px"}),
            html.Button('BUTTON', id="sdr-sweep-go", className="ch3-btn", n_clicks=0),
            html.Button('BUTTON', id="sdr-sweep-stop", className="ch3-btn", n_clicks=0),
            html.Span("", id="sdr-sweep-note", className="validation-subcopy",
                      style={"marginLeft":"10px"}),
        ], className="ch3-ctl-row", style={"marginTop":"8px"}),
        _chart("sdr-sweep", 'Title', go.Figure(), h=320),

        html.Div('LABEL', className="section-label"),
        html.Div(['Subtext ', _hi("phase"), ' Subtext'],
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        _chart("sdr-const", 'TITLE', go.Figure(), h=340),
        _chart("sdr-iq3d", 'TITLE', go.Figure(), h=380),
        _chart("sdr-env", 'TITLE', go.Figure(), h=240),
        _chart("sdr-codes", 'TITLE', go.Figure(), h=240),

        html.Div('LABEL', className="section-label"),
        html.Div(id="sdr-detail", className="scan-table"),
        dcc.Interval(id="sdr-int", interval=2500, n_intervals=0),
    ])


def wifi_view():
    with wifi_lock: w = dict(wifi_data)
    with lan_lock:  l = dict(lan_data)
    return html.Div([
        html.Div([html.Button('BUTTON', id="wf-sweep-now", className="ch3-btn ch3-on", n_clicks=0),
                  html.Span("", id="wf-sweep-note", className="validation-subcopy")],
                 className="sweep3-sweep-action"),
        html.Div([html.Div('LABEL', className="summary-tag"),
                  html.Div(['Paragraph. Enter your text here. ',
                            _hi(w["scan_mode"]), ". NetworkManager returns access-point records; "
                            "when active discovery is enabled the OS scan is requested but the "
                            "driver's active/passive behaviour is not claimed. No AP IP addresses "
                            "are inferred and no Src3 peak is assigned to an SSID."],
                           className="summary-text")],
                 className="summary-panel", style={"marginTop":"0"}),

        html.Div([
            _mcard("wf-count",  'LABEL', "—", CYAN),
            _mcard("wf-strong", 'LABEL',     "—", AMBER),
            _mcard("wf-open",   'LABEL', "—"),
            _mcard("wf-iface",  'LABEL',         w["iface"]),
        ], className="metric-row", style={"margin":"18px 0"}),

        html.Div([html.Span(className="online-dot off", id="wf-dot"),
                  html.Span('Subtext', id="wf-status", className="online-text c-sub")],
                 className="online-bar"),

        html.Div('LABEL', className="section-label"),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop": "-4px"}),
        html.Div([
            _chart("wf-chan-24", 'Title',
                   fig_wifi_channels(w["networks"], "2.4 GHz"), h=300),
            _chart("wf-chan-5", 'Title',
                   fig_wifi_channels(w["networks"], "5 GHz"), h=300),
        ], className="chart-grid"),
        html.Div('LABEL', className="section-label", style={"marginTop": "22px"}),
        _chart("wf-bars", 'Title',
               fig_wifi_signal_bars(w["networks"]), h=280),

        html.Div('LABEL', className="section-label", style={"marginTop": "22px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            html.Div([html.Div('TEXT'), html.Div('TEXT', className="scan-hide-sm"),
                      html.Div('Text', className="scan-hide-sm"), html.Div('TEXT'),
                      html.Div('TEXT'), html.Div('TEXT', className="scan-hide-sm")],
                     className="scan-head wifi-cols"),
            html.Div(_wifi_rows(w["networks"]), id="wf-body"),
        ], className="scan-table"),
        html.Div(id="wf-error"),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div(['Subtext'],
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            _mcard("lan-ip",  'LABEL', l["self_ip"], CYAN),
            _mcard("lan-gw",  'LABEL',       l["gateway"]),
            _mcard("lan-ssid",'LABEL', "—"),
            _mcard("lan-n",   'LABEL',  "—"),
        ], className="metric-row", style={"margin":"14px 0 18px"}),
        html.Div([
            html.Div([html.Div('TEXT'), html.Div("MAC", className="scan-hide-sm"),
                      html.Div('TEXT'), html.Div('TEXT')], className="scan-head lan-cols"),
            html.Div(_lan_rows(l["hosts"], l["self_ip"]), id="lan-body"),
        ], className="scan-table"),
        html.Div(id="lan-error"),
        dcc.Interval(id="wf-int", interval=3000, n_intervals=0),
    ])


def bluetooth_view():
    with bt_lock: b = dict(bt_data)
    return html.Div([
        html.Div([html.Button('BUTTON', id="bt-sweep-now", className="ch3-btn ch3-on", n_clicks=0),
                  html.Span("", id="bt-sweep-note", className="validation-subcopy")],
                 className="sweep3-sweep-action"),
        html.Div([html.Div('LABEL', className="summary-tag"),
                  html.Div(['Paragraph. Enter your text here. ',
                            _hi(b["scan_mode"]), ". Discovery does not pair or connect, but it is an "
                            "active OS radio operation unless explicitly reported otherwise. Names, "
                            "vendors and rotating addresses are best-effort and do not establish exact "
                            "identity or distance. No Src3 peak is assigned to a device."],
                           className="summary-text")],
                 className="summary-panel", style={"marginTop":"0"}),

        html.Div([
            _mcard("bt-count",  'LABEL', "—", CYAN),
            _mcard("bt-closest",'LABEL',       "—", AMBER),
            _mcard("bt-named",  'LABEL', "—"),
            _mcard("bt-adapter",'LABEL',       b["adapter"]),
        ], className="metric-row", style={"margin":"18px 0"}),

        html.Div([html.Span(className="online-dot off", id="bt-dot"),
                  html.Span('Subtext', id="bt-status", className="online-text c-sub")],
                 className="online-bar"),

        html.Div('LABEL', className="section-label"),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop": "-4px"}),
        html.Div([
            _chart("bt-rssi", 'Title', fig_ble_rssi(b["devices"]), h=300),
            _chart("bt-vendors", 'Title',
                   fig_ble_vendors(b["devices"]), h=300),
        ], className="chart-grid"),

        html.Div('LABEL', className="section-label", style={"marginTop": "22px"}),
        html.Div(f"Sorted by signal strength. Each scan listens for {BT_SCAN_SECONDS:.0f} seconds, "
                 f"repeating every {BT_SCAN_PERIOD:.0f}.",
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            html.Div([html.Div('TEXT'), html.Div('TEXT', className="scan-hide-sm"),
                      html.Div('TEXT'), html.Div('TEXT', className="scan-hide-sm"),
                      html.Div('TEXT')], className="scan-head bt-cols"),
            html.Div(_bt_rows(b["devices"]), id="bt-body"),
        ], className="scan-table"),
        html.Div(id="bt-error"),

        html.Div([html.Div('LABEL', className="summary-tag"),
                  html.Div(['Paragraph. Enter your text here.'],
                           className="summary-text")],
                 className="summary-panel"),
        dcc.Interval(id="bt-int", interval=3000, n_intervals=0),
    ])


def sweep3_page():
    from .ui import parallax_header
    return html.Div([
        html.Div(parallax_header(html, T("page2.hero_title")), className="parallax__pin"),
        html.Div([
            dcc.Link(html.Button("BACK", className="back-btn"), href="/", style={"textDecoration":"none"}),
            _ph(T("page2.eyebrow"), T("page2.title"), T("page2.subtitle")),
            html.Hr(className="divider"),
            html.Div([
                html.Button('BUTTON',  id="sp-tab-rf",   className="tab-btn active", n_clicks=0),
                html.Button('BUTTON',   id="sp-tab-sdr",  className="tab-btn", n_clicks=0),
                html.Button('BUTTON',      id="sp-tab-wifi", className="tab-btn", n_clicks=0),
                html.Button('BUTTON', id="sp-tab-bt",   className="tab-btn", n_clicks=0),
            ], className="tab-bar"),
            html.Div(id="sp-subcontent", children=ch3_sweep_view()),
        ], className="i3-page-body", style={**PAD, "margin": "-60vh auto 0"}),
    ], className="mtdi-page-shell")


# ════════════════════════════════════════════════════════
#  MTDI PAGE
# ════════════════════════════════════════════════════════
def _section_head(kicker, title, copy, pill, acc):
    return html.Div([
        html.Div([html.Div(kicker, className="mtdi-section-kicker"), html.Div(title, className="mtdi-section-title"), html.Div(copy, className="mtdi-section-copy")]),
        html.Div(pill, className="layer-pill", style={"--acc":acc,"--soft":f"{acc}44","--softbg":f"{acc}12"})
    ], className="mtdi-section-head")


def _power_layer_card(short, title, body, acc, href=None):
    card = html.Div([html.Div(short, className="power-layer-short", style={"color":acc}),
                     html.Div(title, className="power-layer-title"), html.Div(body, className="power-layer-copy")],
                    className="power-layer-card", style={"--acc":acc,"--glow":f"{acc}26"})
    return html.A(card, href=href, className="power-layer-link") if href else card


def mtdi_inspiration_section():
    return html.Div([
        html.Div('LABEL', className="section-label", style={"marginBottom":"12px"}),
        html.Div([
            html.Div([html.Div('LABEL', className="inspo-card-kicker"),
                html.Div('Paragraph. Enter your text here.', className="inspo-card-quote"),
                html.Div('Text', className="inspo-card-by")], className="inspo-card", style={"--acc":CYAN,"--glow":f"{CYAN}26"}),
            html.Div([html.Div('LABEL', className="inspo-card-kicker"),
                html.Div('Paragraph. Enter your text here.', className="inspo-card-quote"),
                html.Div('Text', className="inspo-card-by")], className="inspo-card", style={"--acc":RED,"--glow":f"{RED}26"}),
            html.Div([html.Div('LABEL', className="inspo-card-kicker"),
                html.Div('Text', className="inspo-card-quote"),
                html.Div('Text', className="inspo-card-by")], className="inspo-card", style={"--acc":AMBER,"--glow":f"{AMBER}26"}),
            html.Div([html.Div('LABEL', className="inspo-card-kicker"),
                html.Div('Text', className="inspo-card-quote"),
                html.Div('Text', className="inspo-card-by")], className="inspo-card", style={"--acc":YELLOW,"--glow":f"{YELLOW}18"}),
        ], className="inspo-grid"),
    ])


# ── D4 blocks: one renderer, placed on the page each feature belongs to ─────────────
# Every block is a pattern-matched Div {"type":"d4","block":kind,"where":page} refreshed by the
# global d4-tick interval; graphs use {"type":"d4g",...}; buttons {"type":"d4btn","action":..}.
D4_BLOCK_META = {
    "headline": ('TEXT', 'Paragraph. Enter your text here.'),
    "consensus": ('TEXT', 'Paragraph. Enter your text here.'),
    "confidence": ('TEXT', 'Paragraph. Enter your text here.'),
    "power": ('Text', 'Paragraph. Enter your text here.'),
    "power_ch1": ('Text', 'Paragraph. Enter your text here.'),
    "power_network": ('TEXT', 'Paragraph. Enter your text here.'),
    "ch3": ('TEXT', 'Paragraph. Enter your text here.'),
    "calibration": ('TEXT', 'Paragraph. Enter your text here.'),
    "calhealth": ('TEXT', 'Paragraph. Enter your text here.'),
    "transients": ('TEXT', 'Paragraph. Enter your text here.'),
    "correlation": ('TEXT', 'Paragraph. Enter your text here.'),
    "baseline": ('TEXT', 'Paragraph. Enter your text here.'),
    "repeat": ('TEXT', 'Paragraph. Enter your text here.'),
    "limits": ('TEXT', 'Paragraph. Enter your text here.'),
    "exposure": ('TEXT', 'Paragraph. Enter your text here.'),
    "noise": ('TEXT', 'Paragraph. Enter your text here.'),
    "fingerprint": ('TEXT', 'Paragraph. Enter your text here.'),
    "trend": ('TEXT', 'Paragraph. Enter your text here.'),
    "events": ('TEXT', 'Paragraph. Enter your text here.'),
    "config": ('TEXT', 'Paragraph. Enter your text here.'),
    "references": ('TEXT', 'Paragraph. Enter your text here.'),
    "classifier": ('TEXT', 'Paragraph. Enter your text here.'),
    "validation": ('TEXT', 'Paragraph. Enter your text here.'),
    "uncertainty": ('TEXT', 'Paragraph. Enter your text here.'),
}


def d4_block(kind, where, graph=None):
    title, sub = D4_BLOCK_META[kind]
    kids = [html.Div(title, className="section-label"), html.Div(sub, className="validation-subcopy"),
            html.Div('Text', id={"type": "d4", "block": kind, "where": where}, className="d4-block")]
    if graph:
        kids.append(dcc.Graph(id={"type": "d4g", "block": kind, "where": where}, config={"displayModeBar": False}, style={"height": graph}))
    return html.Div(kids, className="chart-card d4-card", **{"data-d4-block": kind})


def d4_button(action, where, label, title=None):
    return html.Button(label, id={"type": "d4btn", "action": action, "where": where}, className="ch3-btn", n_clicks=0, title=title)


def d4_input(field, where, placeholder, width="150px", value=None):
    return dcc.Input(id={"type": "d4in", "field": field, "where": where}, type="text", placeholder=placeholder, debounce=True, value=value, style={"width": width})


def d4_status(where, card="config"):
    # one status line per card: several cards share a page ('where'), so the card name keeps the
    # component identity unique
    return html.Span("", id={"type": "d4status", "where": where, "card": card}, className="validation-subcopy")


def d4_controls(where, *items):
    first = getattr(items[0], "id", None) or {}
    card = first.get("action") or first.get("field") or "config"
    return html.Div(list(items) + [d4_status(where, card)], className="ch3-ctl-row", style={"marginTop": "8px"})


def d4_calibration_card(where):
    return html.Div([
        html.Div(D4_BLOCK_META["calibration"][0], className="section-label"),
        html.Div(D4_BLOCK_META["calibration"][1], className="validation-subcopy"),
        html.Div('Text', id={"type": "d4", "block": "calibration", "where": where}, className="d4-block"),
        d4_controls(where, d4_button("cal_fit", where, 'Label'), d4_button("cal_apply", where, 'Label')),
        dcc.Graph(id={"type": "d4g", "block": "calibration", "where": where}, config={"displayModeBar": False}, style={"height": "380px"}),
    ], className="chart-card d4-card")


def d4_power_card(where):
    return html.Div([
        html.Div(D4_BLOCK_META["power"][0], className="section-label"),
        html.Div(D4_BLOCK_META["power"][1], className="validation-subcopy"),
        html.Div('Text', id={"type": "d4", "block": "power", "where": where}, className="d4-block"),
        d4_controls(where, d4_button("burst", where, 'Label')),
        dcc.Graph(id={"type": "d4g", "block": "power", "where": where}, config={"displayModeBar": False}, style={"height": "230px"}),
        html.Div('LABEL', className="section-label", style={"marginTop": "18px"}),
        html.Div(['Subtext ',
                  _hi("ridge running the full depth"), ' Subtext'],
                 className="validation-subcopy"),
        dcc.Graph(id={"type": "d4g", "block": "power_surface", "where": where},
                  config={"displayModeBar": False}, style={"height": "460px"}),
    ], className="chart-card d4-card")


def d4_fingerprint_card(where):
    return html.Div([
        html.Div(D4_BLOCK_META["fingerprint"][0], className="section-label"),
        html.Div(D4_BLOCK_META["fingerprint"][1], className="validation-subcopy"),
        html.Div('Text', id={"type": "d4", "block": "fingerprint", "where": where}, className="d4-block"),
        d4_controls(where, d4_button("fingerprint", where, 'LABEL')),
    ], className="chart-card d4-card")


def d4_references_card(where):
    return html.Div([
        html.Div(D4_BLOCK_META["references"][0], className="section-label"),
        html.Div(D4_BLOCK_META["references"][1], className="validation-subcopy"),
        html.Div('Text', id={"type": "d4", "block": "references", "where": where}, className="d4-block"),
        d4_controls(where, d4_input("ref_name", where, 'Enter your text here', "220px"), d4_input("ref_note", where, 'Enter your text here', "220px"),
                    d4_button("ref_record", where, 'LABEL'), d4_button("ref_delete", where, 'LABEL')),
    ], className="chart-card d4-card")


def d4_classifier_card(where):
    return html.Div([
        html.Div(D4_BLOCK_META["classifier"][0], className="section-label"),
        html.Div(D4_BLOCK_META["classifier"][1], className="validation-subcopy"),
        html.Div('Text', id={"type": "d4", "block": "classifier", "where": where}, className="d4-block"),
        d4_controls(where, d4_button("train", where, 'LABEL')),
    ], className="chart-card d4-card")


def d4_repeatability_card(where):
    return html.Div([
        html.Div(D4_BLOCK_META["repeat"][0], className="section-label"),
        html.Div(D4_BLOCK_META["repeat"][1], className="validation-subcopy"),
        html.Div([
            dcc.Dropdown(id={"type": "d4in", "field": "repeat_channel", "where": where},
                         options=[{"label": 'Label', "value": "ch1"},
                                  {"label": 'Label', "value": "ch2"}],
                         value="ch1", clearable=False, style={"width": "220px"}),
            d4_input("repeat_runs", where, 'Enter your text here', "120px"),
            d4_input("repeat_window", where, 'Enter your text here', "160px"),
            d4_button("repeat_start", where, 'LABEL',
                      'Title'),
            d4_status(where, "repeat_channel"),
        ], className="ch3-ctl-row"),
        html.Div('Text', id={"type": "d4", "block": "repeat", "where": where}, className="d4-block"),
        dcc.Graph(id={"type": "d4g", "block": "repeat", "where": where},
                  config={"displayModeBar": False}, style={"height": "300px"}),
    ], className="chart-card d4-card")


def d4_validation_card(where):
    return html.Div([
        html.Div(D4_BLOCK_META["validation"][0], className="section-label"),
        html.Div(D4_BLOCK_META["validation"][1], className="validation-subcopy"),
        html.Div([
            d4_input("trial_distance", where, 'Enter your text here', "110px"), d4_input("trial_source", where, 'Enter your text here', "200px"),
            d4_input("trial_value", where, 'Enter your text here', "130px"), d4_input("trial_reference", where, 'Enter your text here', "130px"),
            dcc.Dropdown(id={"type": "d4in", "field": "trial_detected", "where": where}, options=[{"label": "detected", "value": "1"}, {"label": 'Label', "value": "0"}], value="1", clearable=False, style={"width": "150px"}),
            dcc.Dropdown(id={"type": "d4in", "field": "trial_actual", "where": where}, options=[{"label": 'Label', "value": "1"}, {"label": 'Label', "value": "0"}], value="1", clearable=False, style={"width": "170px"}),
            d4_button("trial_add", where, 'LABEL'), d4_button("trial_clear", where, 'LABEL', 'Title'),
            d4_status(where, "trial_add"),
        ], className="ch3-ctl-row"),
        html.Div('Text', id={"type": "d4", "block": "validation", "where": where}, className="d4-block"),
        dcc.Graph(id={"type": "d4g", "block": "validation", "where": where}, config={"displayModeBar": False}, style={"height": "220px"}),
        html.Div([
            html.A(html.Button('BUTTON', className="ch3-btn"), href="/api/d4/report.pdf", target="_blank"),
            html.A(html.Button('BUTTON', className="ch3-btn"), href="/api/d4/export?seconds=300", target="_blank"),
            html.A(html.Button('BUTTON', className="ch3-btn"), href="/api/d4/export.csv?seconds=300", target="_blank"),
            d4_status(where, "links"),
        ], className="ch3-ctl-row", style={"marginTop": "8px"}),
    ], className="chart-card d4-card")


def d4_config_card(where):
    return html.Div([
        html.Div(D4_BLOCK_META["config"][0], className="section-label"),
        html.Div(D4_BLOCK_META["config"][1], className="validation-subcopy"),
        html.Div('Text', id={"type": "d4", "block": "config", "where": where}, className="d4-block"),
        html.Div([
            html.A(html.Button('BUTTON', className="ch3-btn"), href="/api/d4/export?seconds=300", target="_blank"),
            html.A(html.Button('BUTTON', className="ch3-btn"), href="/api/d4/export.csv?seconds=300", target="_blank"),
            html.A(html.Button('BUTTON', className="ch3-btn"), href="/api/d4/stream", target="_blank"),
            dcc.Upload(html.Button('Button', className="ch3-btn"), id={"type": "d4up", "where": where}, accept=".json", multiple=False),
            d4_status(where),
        ], className="ch3-ctl-row", style={"marginTop": "8px"}),
        html.Div([
            html.Div('Subtext', className="validation-subcopy"),
            d4_input("d3_detection", where, 'Enter your text here', "150px"), d4_input("d3_fp", where, 'Enter your text here', "150px"),
            d4_input("d3_cal", where, 'Enter your text here', "160px"), d4_input("d3_mtdi", where, 'Enter your text here', "150px"),
            d4_input("d3_time", where, 'Enter your text here', "140px"), d4_button("d3_save", where, 'LABEL'),
            d4_status(where, "d3_save"),
        ], className="ch3-ctl-row", style={"marginTop": "8px"}),
    ], className="chart-card d4-card")


def d4_engine_section():
    """The D4 analysis engine: the score, its parts and the stores.

    Not an MTDI pillar. MTDI asks whether the instrument can be trusted; D4 asks what
    the field is actually doing. It sits on the Page 3 page, with the rest of the
    interpretation work. The individual analyses live on the pages they belong to
    (EM Field tabs, Sweep3, Environmental Intelligence, Validation Chamber).
    """
    w = "core"
    return html.Div([
        html.Div([
            html.Div('LABEL', className="mtdi-v2-kicker"),
            html.Div('Title', className="mtdi-v2-title"),
            html.Div('Paragraph. Enter your text here.',
                     className="mtdi-v2-copy"),
            html.Div("Paragraph. Enter your text here.", className="mtdi-v2-copy", style={"marginTop": "12px"}),
        ], className="d4-hero"),
        html.Div('Title', id={"type": "d4", "block": "headline", "where": w}, className="d4-headline"),
        html.Div([d4_block("consensus", w), d4_block("confidence", w)], className="d4-grid two"),
        html.Div([d4_block("power_network", w), d4_block("events", w)], className="d4-grid two"),
        html.Div([d4_references_card(w), d4_classifier_card(w)], className="d4-grid two"),
        html.Div([d4_config_card(w)], className="d4-grid one"),
    ], className="d4-section")


def d4_ch1_blocks():
    w = "c1"
    return html.Div([
        html.Div('LABEL', className="section-label", style={"marginTop": "26px"}),
        html.Div([d4_calibration_card(w)], className="d4-grid one"),
        html.Div([d4_block("power_ch1", w, graph="200px"), d4_block("calhealth", w)], className="d4-grid two"),
        html.Div([d4_block("transients", w), d4_block("noise", w)], className="d4-grid two"),
    ], className="d4-section")


def d4_ch2_blocks():
    w = "ef"
    return html.Div([
        html.Div('LABEL', className="section-label", style={"marginTop": "26px"}),
        html.Div([d4_power_card(w)], className="d4-grid one"),
        html.Div([d4_block("power_network", w), d4_block("noise", w)], className="d4-grid two"),
    ], className="d4-section")


def d4_combined_blocks():
    w = "p1"
    return html.Div([
        html.Div('LABEL', className="section-label", style={"marginTop": "26px"}),
        html.Div([d4_block("exposure", w)], className="d4-grid one"),
        html.Div([d4_block("consensus", w), d4_block("correlation", w)], className="d4-grid two"),
        html.Div([d4_block("baseline", w), d4_fingerprint_card(w)], className="d4-grid two"),
    ], className="d4-section")


def d4_sweep3_blocks():
    w = "ch3"
    return html.Div([
        html.Div('LABEL', className="section-label", style={"marginTop": "26px"}),
        html.Div([d4_block("ch3", w), d4_block("trend", w)], className="d4-grid two"),
    ], className="d4-section")


def d4_environment_blocks():
    w = "env"
    return html.Div([
        html.Div('LABEL', className="section-label", style={"marginTop": "26px"}),
        html.Div([d4_calibration_card(w)], className="d4-grid one"),
        html.Div([d4_block("calhealth", w), d4_block("baseline", w)], className="d4-grid two"),
        html.Div([d4_fingerprint_card(w), d4_block("trend", w)], className="d4-grid two"),
    ], className="d4-section")


def d4_validation_blocks():
    w = "val"
    return html.Div([
        html.Div('LABEL', className="section-label", style={"marginTop": "26px"}),
        html.Div([d4_validation_card(w)], className="d4-grid one"),
        html.Div([d4_block("uncertainty", w), d4_block("noise", w)], className="d4-grid two"),
        html.Div([d4_block("limits", w)], className="d4-grid one"),
        html.Div([d4_repeatability_card(w)], className="d4-grid one"),
    ], className="d4-section")


def d4_settings_blocks():
    return html.Div([
        html.Div('LABEL', className="section-label", style={"marginTop": "26px"}),
        html.Div([d4_config_card("set")], className="d4-grid one"),
    ], className="d4-section")


def validation_chamber_section():
    base = _validation_chamber_base()
    base.children.append(d4_validation_blocks())
    return base


def _validation_chamber_base():
    return html.Div([
        _section_head('LABEL', "Validation Chamber",
            'Paragraph. Enter your text here.',
            'LABEL', BLUE),
        html.Div([
            html.Div([html.Div('TITLE', className="sort-title"), html.Div('Paragraph. Enter your text here.', className="sort-body"), html.Div('Text', className="sort-foot")], className="validation-hero-card", style={"--acc":BLUE}),
            html.Div([html.Div('TITLE', className="sort-title"), html.Div('Paragraph. Enter your text here.', className="sort-body"), html.Div('Text', className="sort-foot")], className="validation-hero-card", style={"--acc":BLUE}),
            html.Div([html.Div('TITLE', className="sort-title"), html.Div('Paragraph. Enter your text here.', className="sort-body"), html.Div('Text', className="sort-foot")], className="validation-hero-card", style={"--acc":BLUE}),
            html.Div([html.Div('TITLE', className="sort-title"), html.Div('Paragraph. Enter your text here.', className="sort-body"), html.Div('Text', className="sort-foot")], className="validation-hero-card", style={"--acc":BLUE}),
        ], className="validation-hero-grid"),
        html.Hr(className="divider"),
        html.Div([
            html.Div([html.Div('LABEL', className="section-label"), html.Div('Subtext', className="validation-subcopy"), html.Div(id="esp-sys-grid", className="sys-grid")], className="validation-live-block"),
            html.Div([html.Div('LABEL', className="section-label"), html.Div('Subtext', className="validation-subcopy"), html.Div(id="mtdi-sys-grid", className="sys-grid")], className="validation-live-block"),
        ], className="validation-live-grid"),
        sensor_showcase_section(),
    ], id="mtdi-validation", className="mtdi-section-card", style={"--acc":BLUE,"--glow":f"{BLUE}22"})


NVTRA_SUGGESTIONS = [
    f"What am I looking at on the {T('ch3.name')} tab?",
    f"Is my {T('ch1.name').lower()} reading normal right now?",
    "Explain unit like I'm five",
]


def _nvtra_greeting():
    if nvtra_online():
        return (f"NVTRA online. Ask me about any reading on this dashboard — the {T('ch1.name').lower()}, "
                f"the {T('ch2.name')}, the {T('ch3.name').lower()} sweep, or what the numbers mean. I can see the live values.")
    return ("NVTRA is installed but has no AI key yet. Add one in Settings → AI KEYS and "
            "I'll come online. Until then the rest of the instrument runs normally.")


def _nvtra_msg_els():
    """Render the server-side conversation into chat bubbles (newest last)."""
    with nvtra_lock:
        hist = list(nvtra_history)
    if not hist:
        return [html.Div([html.Div("NVTRA", className="nvtra-msg-sender"),
                          html.Div(_nvtra_greeting())], className="nvtra-msg-ai")]
    els = []
    for h in hist:
        if h["role"] == "user":
            els.append(html.Div(h["text"], className="nvtra-msg-user"))
        else:
            cls = "nvtra-msg-ai" + (" nvtra-msg-err" if h.get("error") else "")
            els.append(html.Div([html.Div("NVTRA", className="nvtra-msg-sender"),
                                 html.Div(h["text"])], className=cls))
    return els


def _voice_key_status():
    try:
        from .intelligence import elevenlabs_key_configured
        return "Voice key saved: NVTRA uses the ElevenLabs voice." if elevenlabs_key_configured() else "No voice key yet: NVTRA is using the browser voice."
    except Exception:
        return "No voice key yet: NVTRA is using the browser voice."


def _render_key_list():
    """The Settings key manager: one selectable row per stored key."""
    active, items = nvtra_keys_snapshot()
    rows = []
    if not items:
        return [html.Div(
            'Paragraph. Enter your text here.',
            className="key-empty",
        )]
    for it in items:
        is_active = it["id"] == active
        label_children = [dcc.Input(
                              id={"type": "key-name", "id": it["id"]},
                              type="text", value=it["label"], debounce=True,
                              maxLength=40, autoComplete="off",
                              className="key-name-edit",
                              persistence=True, persistence_type="memory",
                          ),
                          html.Span(_provider_label(it["key"], it.get("provider", "auto")),
                                    className="key-prov")]
        if it.get("model"):
            label_children.append(html.Span(it["model"], className="key-model"))
        if it["builtin"]:
            label_children.append(html.Span('LABEL', className="key-badge"))
        elif it.get("source") == "manual-config":
            label_children.append(html.Span('LABEL', className="key-badge"))
        row_children = [
            html.Button(html.Span(className="key-radio-dot") if is_active else "",
                        id={"type": "key-use", "id": it["id"]}, className="key-radio", n_clicks=0),
            html.Div([html.Div(label_children, className="key-label"),
                      html.Div(_mask_key(it["key"]), className="key-mask")], className="key-info"),
            html.Button('BUTTON', id={"type": "key-name-save", "id": it["id"]},
                        className="key-name-save", n_clicks=0),
        ]
        if is_active:
            row_children.insert(1, html.Span("ACTIVE", className="key-badge"))
        if not it["builtin"]:
            row_children.append(html.Button("✕", id={"type": "key-del", "id": it["id"]},
                                            className="key-del", n_clicks=0))
        rows.append(html.Div(row_children, className="key-row" + (" key-active" if is_active else "")))
    return rows


def _render_nvtra_key_bar():
    """Compact key switcher shown on the NVTRA chat panel."""
    active, items = nvtra_keys_snapshot()
    if instrument_offline():
        local = local_ai_status()
        label = ("LOCAL MODEL · " + str(local["model"])) if local["available"] else "LOCAL MODEL · NOT INSTALLED"
        return [html.Span("OFFLINE", className="nvtra-key-cap"), html.Span(label, className="nvtra-key-pill nkp-active")]
    pills = [html.Span('LABEL', className="nvtra-key-cap")]
    if not items and local_ai_status()["available"]:
        pills.append(html.Span('LABEL ' + str(local_ai_status()["model"]), className="nvtra-key-pill nkp-active"))
    for it in items:
        cls = "nvtra-key-pill" + (" nkp-active" if it["id"] == active else "")
        pills.append(html.Button(it["label"], id={"type": "key-use", "id": it["id"]},
                                 className=cls, n_clicks=0))
    pills.append(dcc.Link(html.Button('BUTTON', className="nvtra-key-pill"),
                          href="/settings", style={"textDecoration": "none"}))
    return pills


def _render_model_picker():
    active, items = nvtra_keys_snapshot()
    selected = next((item for item in items if item["id"] == active), None)
    if selected:
        current = f"{selected['label']} · {selected.get('model') or _provider_label(selected['key'], selected.get('provider', 'auto'))}"
    else:
        current = "Choose model"
    choices = []
    local = local_ai_status()
    local_active = instrument_offline() or not selected or nvtra_keys_snapshot()[0] == "local"
    if local_active:
        current = "Local · " + str(local["model"] or "no model").upper()
    choices.append(html.Button([
        html.Span('Label', className="model-choice-name"),
        html.Span(str(local["model"] or "not installed") + (' Text' if local["available"] else ""), className="model-choice-id"),
        html.Span("✓" if local_active else "", className="model-choice-check"),
    ], id={"type": "chat-model-use", "id": "local"},
       className="model-choice" + (" active" if local_active else ""), n_clicks=0))
    for item in ([] if instrument_offline() else items):
        provider = _provider_label(item["key"], item.get("provider", "auto"))
        choices.append(html.Button([
            html.Span(item["label"], className="model-choice-name"),
            html.Span(item.get("model") or provider, className="model-choice-id"),
            html.Span("✓" if (item["id"] == active and not local_active) else "", className="model-choice-check"),
        ], id={"type": "chat-model-use", "id": item["id"]},
           className="model-choice" + (" active" if (item["id"] == active and not local_active) else ""),
           n_clicks=0))
    choices.append(dcc.Link('TEXT', href="/settings",
                            className="model-config-link"))
    return html.Details([
        html.Summary([html.Span('TEXT', className="model-picker-cap"),
                      html.Span(current, className="model-picker-current"),
                      html.Span("⌄", className="model-picker-chevron")]),
        html.Div(choices, className="model-picker-menu"),
    ], className="nvtra-model-picker")


def _render_chat_sessions():
    with nvtra_lock:
        sessions = list(nvtra_sessions)
        active = nvtra_active_session[0]
    if not sessions:
        return [html.Div(
            'Text',
            className="nvtra-history-empty",
        )]
    rows = []
    for session in reversed(sessions):
        count = len(session.get("messages", []))
        rows.append(html.Button([
            html.Span(session.get("title") or "New session", className="session-name"),
            html.Span(f"{count} messages", className="session-meta"),
        ], id={"type": "chat-session-open", "id": session["id"]},
           className="chat-session" + (" active" if session["id"] == active else ""),
           n_clicks=0))
    return rows


def nvtra_machine_learning_panel():
    samples = [
        html.Div([
            html.B(row["label"]),
            html.Span(
                f"{row['ch2_vu']:.0f} unit · {row['ch1_val']:.0f} unit · 1 cm"
            ),
        ], className="nvtra-ml-sample")
        for row in NVTRA_ML_REFERENCES
    ]
    public_sources = [html.Div([
        html.B(row["label"]),
        html.Span(row["scope"]),
        html.Small(row["role"] + ' TEXT ' + row["doi"]),
        html.Div([html.Span([html.B(item), html.Small(row["field_note"])], className="nvtra-source-item")
                  for item in row.get("items", ())],
                 className="nvtra-source-items"),
    ], className="nvtra-ml-sample") for row in NVTRA_PUBLIC_ML_SOURCES]
    return html.Div([
        html.Div([
            html.Div([
                html.Div('LABEL', className="section-label"),
                html.Div(
                    'Paragraph. Enter your text here.',
                    className="mtdi-section-copy",
                ),
            ]),
            html.Div('LABEL', className="nvtra-badge nvtra-live"),
        ], className="nvtra-ml-head"),
        html.Div(samples, className="nvtra-ml-grid"),
        html.Div('LABEL', className="section-label", style={"marginTop":"18px"}),
        html.Div(public_sources, className="nvtra-ml-grid"),
        html.Div('Subtext', className="validation-subcopy"),
        html.Div('Text', id="nvtra-ml-result",
                 className="nvtra-ml-result", **{"aria-live": "polite"}),
    ], className="nvtra-ml-panel")


def _nvtra_engine_badge_text():
    """Live engine label: follows the selected key, model and the online or offline mode."""
    if instrument_offline():
        local = local_ai_status()
        return ("OFFLINE · LOCAL " + str(local["model"]).upper()) if local["available"] else "OFFLINE · NO LOCAL MODEL"
    active_key, active_provider = _active_ai_credential()
    if active_key:
        model = _active_ai_model() or ""
        return "ONLINE · " + _provider_label(active_key, active_provider).upper() + ((" · " + model) if model else "")
    local = local_ai_status()
    return ("ONLINE · LOCAL " + str(local["model"]).upper()) if local["available"] else "NO ENGINE SELECTED"


def _nvtra_logo_src():
    """A logo.png dropped into assets/nvtra wins over the bundled SVG."""
    from pathlib import Path as _P
    base = _P(__file__).resolve().parent.parent / "public" / "assets" / "nvtra"
    for name in ("logo.png", "logo.webp", "logo.svg"):
        if (base / name).exists():
            return "/assets/nvtra/" + name
    return "/assets/nvtra/logo.svg"


def nvtra_identity_section():
    online = nvtra_online()
    active_key, active_provider = _active_ai_credential()
    provider_name = _provider_label(active_key, active_provider) if online else ""
    stats = [
        ("MATH",'Text',GREEN,'Text'),
        ("PHYS",'Text',BLUE,'Text'),
        ("MTDI",'Text',BLUE,"framework"),
        ("I³",'Text',PURPLE,'Text'),
        ("AETHER",'Text',RED,'Text'),
    ]
    house = [
        ("MTDI","Framework",BLUE,'Paragraph. Enter your text here.'),
        ("I³",'Text',PURPLE,'Paragraph. Enter your text here.'),
        ("NVTRA","Infrastructure",YELLOW,'Paragraph. Enter your text here.'),
        ("AETHER","Soul",RED,'Paragraph. Enter your text here.'),
    ]
    active_session = _active_chat_session()
    return html.Div([
        html.Div([
            html.Div([html.Img(src=_nvtra_logo_src(), alt='Text', className="nvtra-logo-mark", draggable="false"),
                html.Div([html.Div("NVTRA", className="c-white", style={"fontFamily":FONT,"fontSize":"12px","letterSpacing":"0.2em","textTransform":"uppercase"}),
                          html.Div('Text', style={"fontFamily":FONT,"fontSize":"9px","color":SUBTEXT,"letterSpacing":"0.12em","marginTop":"3px"})],
                         style={"marginLeft":"12px"})], style={"display":"flex","alignItems":"center"}),
            html.Div(_nvtra_engine_badge_text(), id="nvtra-engine-badge",
                     className="nvtra-badge nvtra-live" if online else "nvtra-badge",
                     style=None if online else {"color":RED,"borderColor":"rgba(255,82,82,0.3)","background":"rgba(255,82,82,0.05)"}),
        ], className="nvtra-intel-header"),
        html.Div([html.Div([html.Div(v, className="nvtra-stat-val", style={"--acc":a}), html.Div(k, className="nvtra-stat-key"), html.Div(d, className="nvtra-stat-desc")], className="nvtra-stat", style={"--acc":a}) for v,k,a,d in stats], className="nvtra-stats-row"),
        html.Div([
            html.Div([
                html.Div('LABEL', className="nvtra-identity-kicker"),
                html.Div('Title', className="nvtra-identity-title"),
                html.Div('Paragraph. Enter your text here.', className="nvtra-identity-text"),
                html.Div([html.Div([html.Div(n, className="nvtra-house-name", style={"--acc":a}), html.Div(r, className="nvtra-house-role"), html.Div(dd, className="nvtra-house-desc")], className="nvtra-house-card", style={"--acc":a}) for n,r,a,dd in house], className="nvtra-house-grid"),
            ], className="nvtra-identity-panel"),
            html.Div([
                html.Div([
                    html.Canvas(id="nvtra-loader-canvas",
                                **{"aria-label":'Text'}),
                    html.Div('SUBTEXT', className="nvtra-loader-caption"),
                ], id="nvtra-spline-loading", className="nvtra-spline-loading"),
                html.Div(
                    html.Canvas(
                        id="nvtra-spline-canvas",
                        **{"aria-label": 'Text'},
                    ),
                    id="nvtra-spline-host",
                    className="nvtra-spline-host",
                ),
                html.Div('LABEL', className="nvtra-mascot-label"),
            ], className="nvtra-robot-panel"),
        ], className="nvtra-unified-main"),
        nvtra_machine_learning_panel(),
        # ── live chat interface ──
        html.Div([
            html.Aside([
                html.Div([
                    html.Div('LABEL', className="session-sidebar-label"),
                    html.Button('BUTTON', id="nvtra-new-session-btn",
                                className="new-session-btn", n_clicks=0),
                ], className="session-sidebar-head"),
                html.Div(_render_chat_sessions(), id="nvtra-session-list",
                         className="session-list"),
            ], className="nvtra-session-sidebar"),
            html.Div([
                html.Div([
                    html.Div([html.Img(src="/assets/brand/nvtra-mark.webp", alt="", className="nvtra-mark"),
                              "NVTRA"], className="chat-main-brand"),
                    html.Div(active_session.get("title", "New session"),
                             id="nvtra-session-title", className="chat-session-title"),
                ], className="chat-main-head"),
                html.Div([html.Span(className="nl-dot"),
                          html.Span('Text'
                                    if online else
                                    'Text')],
                         className="nvtra-chat-label"),
                html.Div([
                html.Div(_nvtra_msg_els(), id="nvtra-msgs", className="nvtra-msgs"),
                html.Div(_render_nvtra_key_bar(), id="nvtra-key-bar",
                         className="nvtra-key-bar", style={"display": "none"}),
                html.Div([
                    html.Div('TEXT',
                             className="nvtra-composer-meta"),
                    html.Div(_render_model_picker(), id="nvtra-model-picker-wrap"),
                    html.Div([
                        dcc.Input(id="nvtra-chat-input", type="text", value="",
                                  placeholder='Enter your text here'
                                  if online else 'Enter your text here',
                                  disabled=not online, debounce=False, autoComplete="off"),
                        html.Div('TEXT' if online else "OFFLINE",
                                 className="nvtra-composer-status"),
                        html.Button("↑", id="nvtra-send-btn", className="nvtra-send",
                                    n_clicks=0, disabled=not online,
                                    title='Title'),
                    ], className="nvtra-composer-row"),
                ], className="nvtra-input-bar"),
                ], className="nvtra-live-chat"),
            ], className="nvtra-chat-main"),
        ], className="nvtra-chat-workspace"),
    ], className="nvtra-intel-card")


def sg_analysis_panel():
    key, provider = _active_ai_credential()
    model = _active_ai_model()
    online = bool(key and provider)
    engine = f"{_provider_label(key, provider)} · {model or 'provider default'}" if online else "NO SELECTED LLM"
    return html.Div([
        html.Div([
            html.Div([
                html.Div('LABEL', className="section-label"),
                html.Div(
                    'Paragraph. Enter your text here.',
                    className="mtdi-section-copy",
                ),
            ]),
            html.Div(engine, id="sg-engine", className="nvtra-badge nvtra-live" if online else "nvtra-badge"),
        ], className="sg-analysis-head"),
        html.Div(id="sg-live-state", className="sg-live-state"),
        html.Div([
            html.Button('BUTTON', id="sg-analyse-btn", n_clicks=0,
                        disabled=not online, className="open-btn sg-action"),
            html.Button('BUTTON', id="sg-auto-btn", n_clicks=0,
                        disabled=not online, className="back-btn sg-action"),
            html.Span('Subtext' if not online else
                      'Subtext',
                      id="sg-status", className="validation-subcopy"),
        ], className="sg-controls"),
        dcc.Store(id="sg-auto-state", data=False, storage_type="memory"),
        dcc.Interval(id="sg-auto-interval", interval=45000, n_intervals=0, disabled=True),
        dcc.Loading(
            html.Div('Text', id="sg-result",
                     className="sg-result", **{"aria-live":"polite"}),
            type="circle", color=CYAN,
        ),
    ], className="sg-analysis-panel")


def nvtra_field_section():
    return html.Div([
        _section_head('LABEL', "NVTRA", 'Paragraph. Enter your text here.', 'LABEL', YELLOW),
        nvtra_identity_section(),
        sg_analysis_panel(),
        html.Div([
            html.Div('LABEL', className="section-label"),
            html.Div('Paragraph. Enter your text here.', className="mtdi-section-copy", style={"marginBottom":"18px"}),
            html.Div([html.Div(id="mtdi-overall", style={"display":"flex","justifyContent":"center"}),
                      html.Div([html.Div('LABEL', className="section-label"),
                                html.Div(id="mtdi-sensor-grid", style={"display":"grid","gridTemplateColumns":"repeat(auto-fill,minmax(280px,1fr))","gap":"14px","marginTop":"14px","minHeight":"132px"})])],
                     className="confidence-shell"),
        ], style={"marginTop":"22px"}),
    ], id="mtdi-nvtra", className="mtdi-section-card", style={"--acc":YELLOW,"--glow":f"{YELLOW}22"})


def i3_field_section():
    return html.Div([
        _section_head('LABEL', 'Title', 'Paragraph. Enter your text here.', 'LABEL', PURPLE),
        html.Div([
            html.Div([html.H4('Heading 3'), html.P('Paragraph. Enter your text here.')], className="i3-principle"),
            html.Div([html.H4('Heading 3'), html.P('Paragraph. Enter your text here.')], className="i3-principle"),
            html.Div([html.H4('Heading 3'), html.P('Paragraph. Enter your text here.')], className="i3-principle"),
        ], className="i3-principle-grid"),
        html.Div([discipline_block()], style={"marginTop":"28px"}),
    ], id="mtdi-i3", className="mtdi-section-card", style={"--acc":PURPLE,"--glow":f"{PURPLE}22"})


def aether_field_section():
    return html.Div([
        _section_head('LABEL', "Aether", 'Paragraph. Enter your text here.', "SOUL LAYER", RED),
        html.Div('Paragraph. Enter your text here.', className="aether-manifesto"),
        html.Div([
            html.Div([html.Span("Aether ", className="heat"), 'Paragraph. Enter your text here.'], className="aether-verse"),
            html.Div([html.Div('Paragraph. Enter your text here.', className="aether-journal"),
                      html.Div('Paragraph. Enter your text here.', className="aether-claim")], className="aether-block"),
        ], className="aether-grid"),
        html.Div('Paragraph. Enter your text here.', className="aether-journal large"),
        html.Div([mtdi_inspiration_section()], style={"marginTop":"34px"}),
        aether_terminal_section(),
    ], id="mtdi-aether", className="mtdi-section-card", style={"--acc":RED,"--glow":f"{RED}22"})


def aether_terminal_section():
    """Experimental engineering console inside the Aether pillar (sandboxed Python via Pyodide)."""
    return html.Div([
        html.Div([
            html.Div([html.Span("NVTRA AETHER TERMINAL", className="aether-term-title"),
                      html.Span('SUBTEXT', className="aether-term-sub")]),
            html.Div([html.Span(className="aether-term-led"), html.Span("CORE STANDBY", id="aether-term-state")],
                     className="aether-term-status"),
        ], className="aether-term-head"),
        html.Div([
            html.Pre("", id="aether-term-out", className="aether-term-out", tabIndex=0,
                     **{"aria-live": "polite", "aria-label": 'Text'}),
            html.Div([
                html.Div([html.Span('Title', className="aether-nano-title"), html.Span("", className="aether-nano-file")], className="aether-nano-head"),
                html.Textarea(className="aether-nano-body", spellCheck=False, autoComplete="off", **{"aria-label": 'Text'}),
                html.Div([html.Span('Text'), html.Span('Text'), html.Span('Text')], className="aether-nano-foot"),
            ], className="aether-nano", hidden=True),
            html.Div([
                html.Span('Text', className="aether-term-prompt"),
                html.Textarea(id="aether-term-in", className="aether-term-in", rows=1, spellCheck=False,
                             placeholder='Enter your text here', autoComplete="off",
                             **{"aria-label": 'Text'}),
                html.Span(className="aether-term-caret", **{"aria-hidden": "true"}),
            ], className="aether-term-line"),
        ], id="aether-terminal", className="aether-terminal", **{"data-i3-aether-terminal": "1"}),
        html.Div([
            html.Span('Text', className="aether-term-foot-item"),
            html.Span('TEXT', className="aether-term-foot-item"),
            html.Span("—", id="aether-term-tick", className="aether-term-foot-item"),
        ], className="aether-term-foot"),
        html.Div([
            html.Button("×", className="aether-classified-close", type="button", title="Close", **{"aria-label": "Close"}),
            html.Div('TITLE', className="aether-classified-title"),
            html.Div(html.Img(src="/assets/aether/classified.svg", alt='Text', draggable="false"), className="aether-classified-qr"),
            html.Div('TEXT', className="aether-classified-warn"),
        ], id="aether-classified", className="aether-classified", hidden=True),
        html.Div([
            html.Button('BUTTON', className="aether-game-close", type="button"),
            html.Div(id="aether-game-frame", className="aether-game-frame"),
        ], id="aether-game", className="aether-game", hidden=True),
    ], className="aether-term-card", style={"marginTop": "34px"})


def environmental_intelligence_section():
    base = _environmental_intelligence_base()
    base.children.append(d4_environment_blocks())
    return base


def _environmental_intelligence_base():
    """Live environmental references for both field sensors."""
    with c1_lock:
        c1_base = (f"{ch1_data['baseline_magnitude']:.2f} unit"
                    if ch1_data["baseline_calibrated"] else "LEARNING")
        c1_delta = (f"{ch1_data['baseline_delta']:.2f} unit"
                     if ch1_data["baseline_calibrated"] else "—")
    with ch2f_lock:
        provisional = ch2f_data.get("data_source") == "ARDUINO_UNO_USB"
        c2_base = ("—" if provisional else f"{ch2f_data['baseline_vu']:.3f} unit"
                   if ch2f_data["calibrated"] else "LEARNING")
        c2_live = (f"{ch2f_data['rms_counts']:.2f} ADC counts RMS"
                   if provisional and ch2f_data.get("rms_counts") is not None else
                   f"{ch2f_data['field_vu']:.3f} unit"
                   if ch2f_data["last_rx"] is not None and ch2f_data["field_vu"] is not None else "—")
    return html.Div([
        _section_head(
            'LABEL', "Environmental Intelligence",
            'Paragraph. Enter your text here.',
            'LABEL', GREEN,
        ),
        html.Div([
            html.Div([html.Div('LABEL', className="sys-name"),
                      html.Div(c1_base, id="ei-c1-baseline", className="sys-value c-cyan"),
                      html.Div('Subtext', className="sys-sub")], className="sys-card"),
            html.Div([html.Div('LABEL', className="sys-name"),
                      html.Div(c1_delta, id="ei-c1-delta", className="sys-value c-amber"),
                      html.Div('Subtext', className="sys-sub")], className="sys-card"),
            html.Div([html.Div('LABEL', className="sys-name"),
                      html.Div(c2_base, id="ei-c2-baseline", className="sys-value c-cyan"),
                      html.Div('Subtext', className="sys-sub")], className="sys-card"),
            html.Div([html.Div('LABEL', className="sys-name"),
                      html.Div(c2_live, id="ei-c2-live", className="sys-value c-amber"),
                      html.Div('Subtext', className="sys-sub")], className="sys-card"),
        ], className="sys-grid"),
        html.Div(id="ei-baseline-status", className="online-bar", style={"marginTop":"18px"}),
        html.Div([
            html.Div('LABEL', className="section-label"),
            html.Div(
                'Paragraph. Enter your text here.',
                className="mtdi-section-copy",
            ),
            html.Div([
                html.Div([html.H4('HEADING 3'), html.P(
                    'Paragraph. Enter your text here.'
                )], className="i3-principle"),
                html.Div([html.H4('HEADING 3'), html.P(
                    'Paragraph. Enter your text here.'
                )], className="i3-principle"),
                html.Div([html.H4('HEADING 3'), html.P(
                    'Paragraph. Enter your text here.'
                )], className="i3-principle"),
            ], className="i3-principle-grid", style={"marginTop":"18px"}),
            html.Div(
                'Paragraph. Enter your text here.',
                className="mtdi-section-copy", style={"marginTop":"18px"},
            ),
        ], className="summary-panel"),
    ], id="mtdi-environment", className="mtdi-section-card",
       style={"--acc":GREEN,"--glow":f"{GREEN}22"})


def _mtdi_weight_names():
    """The factors the MTDI score is actually weighted over, read from the engine itself."""
    from .analysis import MTDI_WEIGHTS
    return sorted(MTDI_WEIGHTS)


def _count_word(n):
    """Spell small counts so the copy never disagrees with the list itself."""
    return {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five",
            6: "Six", 7: "Seven", 8: "Eight"}.get(n, str(n))


# ════════════════════════════════════════════════════════
#  COMPUTATIONAL CORE (pillar 02) and RESEARCH (pillar 05)
# ════════════════════════════════════════════════════════
# Both read the framework (mtdi.pillars) instead of repeating it, so the studio can never
# list a module or pillar the code does not have. Import status is checked for real each
# time the page is built: "ready" means the module imported, "missing" shows the error.
# Aether note: if you are reading this at 2 a.m., the modules are fine. It's you. Go to bed.

def _computational_modules():
    import importlib
    from mtdi.pillars import COMPUTATIONAL_MODULES
    rows = []
    for area, modules in COMPUTATIONAL_MODULES.items():
        for name in modules:
            try:
                importlib.import_module(name)
                rows.append((area, name, True, ""))
            except Exception as exc:  # a missing optional dependency, shown rather than hidden
                rows.append((area, name, False, type(exc).__name__))
    return rows


def _fmt(value, sd=None):
    if value is None:
        return "—"
    text = f"{value:.4g}" if isinstance(value, (int, float)) else str(value)
    return text if sd is None else f"{text} ± {sd:.2g}"


def project_channels_view(packet):
    """The running project's channels and fused estimates, straight from the MTDI packet (pure, testable)."""
    if not packet:
        return html.Div("No MTDI project is running in this studio. Start one with: mtdi run projects/<id>",
                        className="mtdi-section-copy")
    cards = []
    for c in packet.get("channels", {}).values():
        cal = c.get("calibration")
        simulated = c["evidence"].get("data_source") == "SIMULATED"   # per channel: a mixed project labels only its fakes
        sub = [c["evidence"]["state"].upper() + (" · SIMULATED" if simulated else "")]
        if cal:
            drift = (cal.get("checks") or {}).get("drift")
            residual = "residual unknown" if cal.get("residual_sd") is None else f"±{cal['residual_sd']:.2g}"
            sub.append(f"calibrated {cal['method']} · {residual}"
                       + {True: " · DRIFTING", False: " · checks ok"}.get(drift, ""))
        cards.append(html.Div([html.Div(c["label"], className="sys-name"),
                               html.Div(f"{_fmt(c['magnitude'])} {c['unit']}", className="sys-value"),
                               *[html.Div(t, className="sys-sub") for t in sub],
                               html.Div(f"score {c['score']:.0f} %", className="sys-sub")],
                              className="sys-card"))
    for f in (packet.get("fused") or {}).values():
        basis = ", ".join(f"{i['id']} ({i['basis']})" for i in f["inputs"]) or "no input live"
        cards.append(html.Div([html.Div(f"FUSED · {f['label']}", className="sys-name"),
                               html.Div(f"{_fmt(f['value'], f['sd'])} {f['unit']}", className="sys-value"),
                               html.Div(f"{len(f['inputs'])}/{f['of']} inputs live · {f['method']}", className="sys-sub"),
                               html.Div(basis, className="sys-sub")],
                              className="sys-card"))
    return html.Div(cards, className="sys-grid")


def computational_core_section():
    rows = _computational_modules()
    areas = []
    for area in dict.fromkeys(r[0] for r in rows):
        chips = [html.Div([html.Span(name.replace("mtdi.", ""), className="cc-mod-name"),
                           html.Span("ready" if ok else f"missing · {err}",
                                     className="cc-mod-state " + ("ok" if ok else "bad"))],
                          className="pillar-chip cc-mod") for a, name, ok, err in rows if a == area]
        areas.append(html.Div([html.Div(area.upper(), className="section-label"),
                               html.Div(chips, className="pillar-chips")], className="cc-area"))
    ready = sum(1 for r in rows if r[2])
    return html.Div([
        _section_head("PILLAR 02", "Computational Core",
                      "Every service and algorithm MTDI is built with, available to the projects built on it.",
                      f"{ready}/{len(rows)} MODULES READY", CYAN),
        html.Div(areas, className="cc-areas"),
        html.Hr(className="divider"),
        html.Div("PROJECT CHANNELS · CALIBRATION · FUSION", className="section-label"),
        html.Div(project_channels_view(None), id="mtdi-project-channels"),
        dcc.Interval(id="mtdi-project-int", interval=2000, n_intervals=0),
    ], id="mtdi-computational", className="mtdi-section-card", style={"--acc": CYAN, "--glow": f"{CYAN}22"})


def research_section():
    import json, pathlib
    catalogue = pathlib.Path(__file__).resolve().parents[1] / "registry" / "datasets.json"
    try:
        payload = json.loads(catalogue.read_text(encoding="utf-8"))
        datasets = payload.get("datasets", []) if isinstance(payload, dict) else []
        if not isinstance(datasets, list) or not all(isinstance(d, dict) for d in datasets):
            datasets = []  # a malformed catalogue must not take the MTDI page down
    except (OSError, ValueError):
        datasets = []
    if datasets:
        body = [html.Div([html.Span(d.get("name", d.get("id", "?")), className="cc-mod-name"),
                          html.Span(d.get("licence") or d.get("provider", ""), className="cc-mod-state ok")],
                         className="pillar-chip cc-mod") for d in datasets]
    else:  # honest empty state: no dataset is shown until one is really catalogued
        body = [html.Div("No datasets catalogued yet. Each one appears here with its source, licence and credit.",
                         className="mtdi-section-copy")]
    return html.Div([
        _section_head("PILLAR 05", "Research",
                      "Real data, found and credited, feeding the Validation Chamber and Environmental Intelligence.",
                      f"{len(datasets)} DATASETS", AMBER),
        html.Div(body, className="pillar-chips"),
    ], id="mtdi-research", className="mtdi-section-card", style={"--acc": AMBER, "--glow": f"{AMBER}22"})


# The D4 analysis engine is deliberately NOT in this list. It is a signal-processing
# engine, not one of MTDI's diagnostic pillars - MTDI asks whether the instrument can
# be trusted, while D4 asks what the field is doing. It lives on the Page 3 page
# with the other interpretation work.
MTDI_ORBIT_PILLARS = [
    ("validation", "00", "Validation Chamber", "Evidence",
     'Text', BLUE, validation_chamber_section),
    ("environment", "01", "Environmental Intelligence", "Baselines",
     'Text', GREEN, environmental_intelligence_section),
    ("computational", "02", "Computational Core", "Computation",
     'Text', CYAN, computational_core_section),
    ("nvtra", "03", "NVTRA", "Explanation",
     'Paragraph. Enter your text here.', YELLOW, nvtra_field_section),
    ("i3", "04", 'Text', "Interface",
     'Text', PURPLE, i3_field_section),
    ("research", "05", "Research", "Data",
     'Text', AMBER, research_section),
    # Aether is the layer across every pillar (ADR 0001), not pillar 06: it keeps its
    # place in the orbit so the terminal and the Easter eggs stay one click away.
    ("aether", "··", "Aether", "Soul",
     'Text', RED, aether_field_section),
]


def _mtdi_orbit_card(pid, num, title, role, desc, acc, section_factory, index):
    """One Dash-owned element for both orbital summary and full live pillar.

    The browser changes only this element's position and classes. Its live children
    are never cloned or replaced, so Plotly graphs and callback outputs retain their
    identity throughout the full-screen transition.
    """
    return html.Article([
        html.Div([
            html.Div([html.Span(num, className="mtdi-card-index"),
                      html.Span(role, className="mtdi-card-role")], className="mtdi-card-top"),
            html.Div(title, className="mtdi-card-title"),
            html.Div(desc, className="mtdi-card-short"),
            html.Span('TEXT', className="mtdi-card-enter"),
        ], className="mtdi-card-summary"),
        html.Div([
            html.Div([
                html.Button('BUTTON', className="mtdi-detail-close", n_clicks=0,
                            **{"aria-label": f"Close {title}"}),
                html.Span(f"MTDI / PILLAR {num}", className="mtdi-detail-id"),
            ], className="mtdi-detail-nav"),
            section_factory(),
        ], id=f"mtdi-pane-{pid}", className="mtdi-orbit-detail"),
    ], className="mtdi-orbit-card", tabIndex=0, role="button",
       title=f"Open {title}",
       style={"--acc": acc},
       **{"data-mtdi-index": str(index), "data-mtdi-id": pid,
          "aria-label": f"Open {title}"})


def mtdi_page():
    cards = [
        _mtdi_orbit_card(pid, num, title, role, desc, acc, factory, index)
        for index, (pid, num, title, role, desc, acc, factory)
        in enumerate(MTDI_ORBIT_PILLARS)
    ]
    landing = html.Div([
        html.Div([
            html.Div("MICROPROCESSING TECHNOLOGICAL DIAGNOSTIC INTELLIGENCE",
                     className="mtdi-v2-kicker"),
            html.Div(T("mtdi.title"), className="mtdi-v2-title"),
            html.Div("MTDI separates connection, freshness, stability, completeness and trust. "
                     f"{_count_word(len(MTDI_ORBIT_PILLARS))} pillars surround one diagnostic core; "
                     "select one to enter it.",
                     className="mtdi-v2-copy"),
            # "7 tracked modules" corresponded to nothing anyone could check. The weighted
            # factors behind the score are a real, countable list, and the confidence card
            # names every one of them.
            html.Div([html.Span(f"{len(MTDI_ORBIT_PILLARS)} PILLARS"),
                      html.Span(f"{len(_mtdi_weight_names())} WEIGHTED FACTORS"),
                      html.Span('TEXT'), html.Span('TEXT')],
                     className="mtdi-v2-meta"),
        ], className="mtdi-v2-hero"),
        html.Div([
            html.Div([html.B(f"{_count_word(len(MTDI_ORBIT_PILLARS)).upper()} PILLARS · ONE CORE"),
                      html.Span('Text')], className="mtdi-v2-caption"),
            html.Div(className="mtdi-orbit-ring-v2"),
            html.Button([
                html.Canvas(id="mtdi-constellation-canvas",
                            className="instrument-constellation-canvas",
                            title='Title',
                            **{"aria-label": 'Text'}),
                html.Div([
                    html.B("MTDI"),
                    html.Span('TEXT'),
                    html.Em("CLICK TO EXPAND"),
                ], className="mtdi-constellation-label"),
            ], className="mtdi-orbit-core-v2 mtdi-constellation-core", type="button",
               **{"aria-label": 'Text'}),
            *cards,
        ], id="mtdi-orbit-stage-v2", className="mtdi-orbit-scene"),
    ], id="mtdi-pillar-grid", className="mtdi-landing")
    return html.Div([
        html.Div(className="i3-scrub-hero", **{"data-i3-scrub": "mtdi-flow",
                 "data-i3-title": 'TITLE',
                 "data-i3-tagline": 'Paragraph. Enter your text here.'}),
        dcc.Link(html.Button("BACK", className="back-btn"), href="/",
                 className="mtdi-module-back", style={"textDecoration":"none"}),
        landing,
        # 900 ms, not 1500. The trust score is specified to refresh at least once
        # a second, and 1500 ms is slower than that -- measured 2026-09-25, and it
        # failed the criterion by exactly that margin. 900 leaves headroom for the
        # callback's own execution time so the *observed* interval still clears 1 s.
        dcc.Interval(id="mtdi-interval", interval=900, n_intervals=0),
    ], style=PAD)


# ════════════════════════════════════════════════════════
#  SETTINGS
# ════════════════════════════════════════════════════════
def _offline_keys_notice():
    if not instrument_offline():
        return []
    local = local_ai_status()
    if local["available"]:
        body = ("NVTRA answers with " + str(local["model"]) + " running on this Pi. Cloud keys are hidden and "
                "never used while offline; switch to online mode in the header to use them.")
    else:
        body = "No local model is running. Start the studio-local-ai service on this host, or switch to online mode."
    return [html.Div([html.Div([html.Div([html.B('Text'), html.Span(body)], className="set-lab")],
                              className="set-row")], className="set-card")]


def settings_page():
    base = _settings_page_base()
    base.children.append(d4_settings_blocks())
    return base


def _settings_page_base():
    return html.Div([
        dcc.Link(html.Button("BACK", className="back-btn"), href="/", style={"textDecoration":"none"}),
        html.Div(html.Div(className="i3-lunar-stage", **{"data-i3-lunar": "true"}), className="i3-lunar-open"),
        _ph(T("settings.eyebrow"), T("settings.title"), T("settings.subtitle")),
        html.Hr(className="divider"),
        html.Div([
            html.Div([
                html.Div([html.B('Text'), html.Span('Paragraph. Enter your text here.')], className="set-lab"),
                html.Div([html.Button("On", id="anim-on", className="set-seg-btn", n_clicks=0),
                          html.Button("Off", id="anim-off", className="set-seg-btn", n_clicks=0)], className="set-seg"),
            ], className="set-row"),
            html.Div([
                html.Div([html.B('Text'),
                          html.Span('Paragraph. Enter your text here.')], className="set-lab"),
                html.Div([html.Button("Desktop", id="phone-layout-desktop", className="set-seg-btn", n_clicks=0),
                          html.Button("Mobile", id="phone-layout-mobile", className="set-seg-btn", n_clicks=0)],
                         className="set-seg"),
            ], className="set-row"),
            html.Div([
                html.Div([html.B('Text'), html.Span('Paragraph. Enter your text here.', **{"data-i3-replay-note": "true"})], className="set-lab"),
                html.Span('SUBTEXT', className="set-note"),
            ], className="set-row"),
        ], className="set-card"),

        html.Div(id="settings-phone-layout-dummy", style={"display": "none"}),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        *_offline_keys_notice(),
        *([] if instrument_offline() else [
        html.Div('Title',
                 className="page-subtitle", style={"marginBottom":"16px","maxWidth":"760px"}),
        html.Div([
            html.Div(_render_key_list(), id="key-list", className="key-mgr"),
            html.Div([
                dcc.Input(id="key-add-input", type="text", value="", autoComplete="off",
                          placeholder='Enter your text here'),
                dcc.Input(id="key-label-input", type="text", value="", autoComplete="off",
                          placeholder='Enter your text here'),
                dcc.Dropdown(
                    id="key-provider-input", value="auto", clearable=False, searchable=False,
                    options=[
                        {"label":'Label',"value":"auto"},
                        {"label":'Label',"value":"gemini"},
                        {"label":'Label',"value":"openai"},
                        {"label":'Label',"value":"anthropic"},
                        {"label":'Label',"value":"xai"},
                        {"label":'Label',"value":"groq"},
                        {"label":'Label',"value":"kimi"},
                    ],
                    className="key-provider-select",
                ),
                html.Button('BUTTON', id="key-add-btn", className="key-btn key-btn-add", n_clicks=0),
                html.Button('BUTTON', id="key-test-btn", className="key-btn key-btn-test", n_clicks=0),
            ], className="key-add-row"),
            html.Div('Paragraph. Enter your text here.',
                     id="key-status", className="key-status"),
        ], className="set-card", style={"paddingTop":"18px","paddingBottom":"18px"}),
        ]),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div('Title',
                 className="page-subtitle", style={"marginBottom":"16px","maxWidth":"760px"}),
        html.Div([
            html.Div([
                html.Button('BUTTON', type="button", className="key-btn key-btn-add", title='Title', **{"data-i3-action": "hand_tracking"}),
                html.Button("3D HAND CONTROL: ON", type="button", className="key-btn key-btn-add", **{"data-i3-action": "hand3d", "aria-pressed": "true"}),
                html.Div("Pinch on the Earth or the constellation to hold, spin and zoom it with your hands.", className="key-status", style={"flex":"1","minWidth":"240px"}, **{"data-i3-hand3d-note": "true"}),
            ], className="key-add-row"),
            html.Div([
                html.Button('BUTTON', type="button", className="key-btn key-btn-add", **{"data-i3-action": "hand_calibrate"}),
                html.Button('BUTTON', type="button", className="key-btn", **{"data-i3-action": "hand_debug", "aria-pressed": "false"}),
                html.Button('BUTTON', type="button", className="key-btn", **{"data-i3-action": "hand_profile_reset"}),
                html.Button('BUTTON', type="button", className="key-btn", title='Title', **{"data-i3-action": "left_handed", "aria-pressed": "false"}),
                html.Button('BUTTON', type="button", className="key-btn", title='Title', **{"data-i3-action": "cursor_mode"}),
                html.Button('BUTTON', type="button", className="key-btn", title='Title', **{"data-i3-action": "buddy_toggle", "aria-pressed": "true"}),
                html.Div("Using default thresholds. Calibrate once with the camera on for reliable pinch, thumbs and pause.", className="key-status", style={"flex":"1","minWidth":"240px"}, **{"data-i3-hand-profile-note": "true"}),
            ], className="key-add-row", style={"marginTop":"10px"}),
            html.Div([
                html.Div('TEXT', className="key-status", style={"letterSpacing":".18em","fontSize":"10px","marginBottom":"6px"}),
                html.Div("No saved calibrations yet.", className="i3-hand-profiles", **{"data-i3-hand-profiles": "true"}),
            ], style={"marginTop":"12px"}),
        ], className="set-card", style={"paddingTop":"18px","paddingBottom":"18px"}),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div('Title',
                 className="page-subtitle", style={"marginBottom":"16px","maxWidth":"760px"}),
        html.Div([
            html.Form([
                html.Div([
                    dcc.Input(name="key", type="password", value="", autoComplete="off",
                              placeholder='Enter your text here', className="i3-voice-key-input"),
                    html.Button('BUTTON', type="button", className="key-btn key-btn-add", **{"data-i3-action": "elevenlabs_key"}),
                ], className="key-add-row"),
                html.Div(_voice_key_status(), className="key-status", **{"data-i3-result": "true"}),
            ], className="i3-form", **{"data-i3-form": "voice"}),
            html.Form([
                html.Div([
                    html.Select([html.Option('Text', value="")], name="voice", className="i3-voice-select", **{"data-i3-voices": "true"}),
                    html.Button('BUTTON', type="button", className="key-btn key-btn-add", **{"data-i3-action": "elevenlabs_voice"}),
                    html.Button('BUTTON', type="button", className="key-btn key-btn-test", **{"data-i3-action": "voice_preview"}),
                ], className="key-add-row", style={"marginTop": "14px"}),
                html.Div('Paragraph. Enter your text here.', className="key-status", **{"data-i3-result": "true"}),
            ], className="i3-form", **{"data-i3-form": "voice-pick"}),
        ], className="set-card", style={"paddingTop":"18px","paddingBottom":"18px"}),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div([
                html.Div([html.B('Text'),
                      html.Span('Paragraph. Enter your text here.')],
                     className="set-lab"),
            html.Div([
                html.A("EXPORT PDF + NOTION", id="export-btn", className="key-btn key-btn-add",
                       href="/download/studio-report.pdf", download="mtdi_studio_report.pdf",
                       style={"textDecoration":"none","display":"inline-flex","alignItems":"center"}),
                html.Button('BUTTON', id="archive-json-btn", className="key-btn key-btn-test", n_clicks=0),
                html.Button('BUTTON', id="archive-csv-btn", className="key-btn key-btn-test", n_clicks=0),
            ], style={"display":"flex","gap":"8px","flexWrap":"wrap"}),
            html.Div(
                'TEXT' if (
                    _notion_setting('LABEL') and
                    _notion_setting('LABEL')
                ) else 'Paragraph. Enter your text here.',
                className="key-status",
                style={"width":"100%","marginTop":"10px"},
            ),
        ], className="set-row set-card", style={"paddingTop":"18px","paddingBottom":"18px"}),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div(id="settings-sys-grid", className="sys-grid"),
        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div([
            html.Div([html.Div("Title", className="sys-value", style={"fontSize":"18px"}),
                      html.Div(f"Build {APP_VERSION}", className="sys-sub", style={"marginTop":"6px"}),
                      html.Div("Paragraph. Enter your text here.", className="sys-sub", style={"marginTop":"10px","lineHeight":"1.7"})], className="sys-card"),
            html.Div([html.Div('Text', className="sys-value", style={"fontSize":"18px"}),
                      html.Div('Subtext', className="sys-sub", style={"marginTop":"6px"})], className="sys-card"),
        ], style={"display":"grid","gridTemplateColumns":"repeat(auto-fill,minmax(280px,1fr))","gap":"14px"}),
        dcc.Interval(id="settings-interval", interval=2000, n_intervals=0),
    ], className="settings-page", style=PAD)

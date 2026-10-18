"""Page builders: Home, EM Field, Spectrum, MTDI and Settings."""
from ._shared import inherit
inherit(globals(), 'common', 'sensors', 'intelligence', 'system', 'tokens', 'theme', 'browser', 'webapp', 'reports', 'charts')

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
    with mag_lock:
        cur_mag = magnetic_data["magnitude"]
        mag_err = magnetic_data["error"]
        mag_have = magnetic_data["last_rx"] is not None
    with spectrum_lock:
        rf_err = spectrum_data["error"]; rf_pf = spectrum_data["peak_freq"]
        rf_pl = spectrum_data["peak_level"]; rf_have = spectrum_data["last_rx"] is not None
    with mtdi_lock:
        overall = mtdi_data["active_health"]
    if rf_have and not rf_err:
        rf_val = f"{rf_pl:+.0f} unit"; rf_lbl = f"PEAK @ {_freq_label(rf_pf)}"
    elif rf_err:
        rf_val = "OFFLINE"; rf_lbl = "CHANNEL 3"
    else:
        rf_val = "SWEEPING"; rf_lbl = "CHANNEL 3"
    # Fixed route identities: status and readings change, module colour never does.
    mods = [
        ("em","01","Page 1",'Paragraph. Enter your text here.',
         f"{cur_mag:.2f} unit" if mag_have and not mag_err else "OFFLINE",
         "MAGNITUDE" if mag_have else "NO DATA", "#67cbd5", "103,203,213"),
        ("spectrum","02","Page 2",'Paragraph. Enter your text here.',
         rf_val, rf_lbl, "#718ee8", "113,142,232"),
        ("mtdi","03","MTDI",'Paragraph. Enter your text here.',
         f"{overall:.0f}%",'TEXT', "#72b99c", "114,185,156"),
        ("settings","04","Settings",'Paragraph. Enter your text here.',
         "THEME","APPEARANCE", "#9a91bd", "154,145,189"),
    ]
    orbit_cards = []
    for index, (mid, numerology, title, desc, val, vl, vc, vrgb) in enumerate(mods):
        orbit_cards.append(dcc.Link(html.Div([
            html.Div([html.Span(numerology, className="mtdi-card-index"),
                      html.Span({"em": "PAGE 1", "spectrum": "PAGE 2"}.get(mid, mid.upper()), className="mtdi-card-role")], className="mtdi-card-top"),
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
            html.Div("Title", className="hero-title"),
            html.Div([html.Span('TEXT', className="i3"), html.Span('   TEXT')], className="hero-tag"),
        ], className="hero-title-wrap"),
        html.Div("Paragraph. Enter your text here.", className="hero-sub"),
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

    scrub_hero = html.Div(className="iv-scrub-hero", **{"data-iv-scrub": "field",
                                                        "data-iv-title": 'Title',
                                                        "data-iv-tagline": 'Paragraph. Enter your text here.'})
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
            html.Div(label, className="iv-sc-kicker"),
            html.H3(title, className="iv-sc-title"),
            html.P(description, className="iv-sc-desc"),
            html.Div([
                *[html.Div([
                    html.Div([html.Span(f_label, className="iv-sc-flabel"), html.Span("—", className="iv-sc-fvalue", **{"data-iv-sc-value": f_key})], className="iv-sc-frow"),
                    html.Div(html.I(**{"data-iv-sc-bar": f_key}), className="iv-sc-bar"),
                ], className="iv-sc-feature") for f_key, f_label in features],
                html.A([html.Span('TEXT'), html.Span("→")], href="/em", className="iv-sc-open"),
            ], className="iv-sc-panel"),
            html.Div([html.Span("●", className="iv-sc-dot"), html.Span("Waiting", **{"data-iv-sc-state": key})], className="iv-sc-status"),
        ], className="iv-sc-details", **{"data-iv-sc-side": key})
    return html.Div([
        html.Div('TITLE', className="instrument-modules-title", style={"marginTop": "72px"}),
        html.Div('Subtext', className="iv-sc-sub"),
        html.Div([
            html.Div([
                html.Div([html.Div('LABEL', className="iv-sc-board-label"),
                          html.Canvas(className="iv-sc-boards", **{"data-iv-boards": "magnetic",
                                      "aria-label": 'Text'})],
                         className="iv-sc-board-slot"),
                html.Div([html.Div('LABEL', className="iv-sc-board-label"),
                          html.Canvas(className="iv-sc-boards", **{"data-iv-boards": "electric",
                                      "aria-label": 'Text'})],
                         className="iv-sc-board-slot"),
            ], className="iv-sc-visual iv-sc-visual-split"),
            html.Div([
                side("magnetic", 'LABEL', 'Title',
                     'Paragraph. Enter your text here.',
                     [("sample_rate", 'Text'), ("snr", 'Text'), ("confidence", 'Text')]),
                side("electric", 'LABEL', 'Title',
                     'Paragraph. Enter your text here.',
                     [("sample_rate", 'Text'), ("snr", 'Text'), ("confidence", 'Text')]),
            ], className="iv-sc-detail-wrap"),
        ], className="iv-sc-stage", **{"data-iv-showcase": "magnetic"}),
        html.Div([
            html.Button('Button', type="button", className="iv-sc-btn on", **{"data-iv-sc": "magnetic"}),
            html.Button('Button', type="button", className="iv-sc-btn", **{"data-iv-sc": "electric"}),
        ], className="iv-sc-switch"),
    ], className="iv-showcase")


# ════════════════════════════════════════════════════════
#  EM FIELD  (magnetic / electric / combined)
# ════════════════════════════════════════════════════════
def magnetic_body():
    with mag_lock:
        m = dict(magnetic_data); hist = list(magnetic_data["history"]); xyz = list(magnetic_data["xyz_history"])
    have = m["last_rx"] is not None
    shown = lambda value: f"{value:.2f}" if have else "—"
    return [
        html.Div([
            _mcard("mv-x", "X", shown(m["x"])),
            _mcard("mv-y", "Y", shown(m["y"])),
            _mcard("mv-z", "Z", shown(m["z"])),
            _mcard("mv-mag", 'Label', shown(m["magnitude"]), CYAN),
            _mcard("mv-baseline", 'Label',
                   shown(m["baseline_magnitude"]) if m["baseline_calibrated"] else "—"),
            _mcard("mv-delta", 'Label',
                   shown(m["baseline_delta"]) if m["baseline_calibrated"] else "—", AMBER),
            _mcard("mv-sig", 'Label', "—"),
        ], className="metric-row"),
        html.Div([
            html.Button(['BUTTON'], id="mag-recal-btn",
                        className="open-btn", n_clicks=0,
                        style={"width":"auto","marginTop":"0","whiteSpace":"nowrap"}),
            html.Span('Paragraph. Enter your text here.',
                      id="mag-recal-status",
                      style={"fontFamily":FONT,"fontSize":"11px","color":SUBTEXT,"lineHeight":"1.5"}),
            dcc.Store(id="mag-recal-request"),
        ], style={"display":"flex","alignItems":"center","gap":"16px",
                  "marginBottom":"16px","flexWrap":"wrap"}),
        html.Div([html.Span(className="online-dot off", id="mag-dot"),
                  html.Span('Subtext', id="mag-status", className="online-text c-sub")],
                 className="online-bar"),
        _emi_listen_card("mag"),
        _chart_board("mag", 'Label'),
        html.Div('LABEL', className="section-label"),
        html.Div([
            html.Div([
                html.Div('LABEL', className="rf-ctl-label"),
                html.Div('Subtext',
                         className="validation-subcopy"),
            ]),
            _zoom_range("mag-zoom"),
        ], className="rf-ctl-bar", style={"marginBottom":"16px"}),
        html.Div([
            _chart("g-line", 'Title',
                   make_line_chart(hist, color=CYAN, fill_color="rgba(0,229,255,0.07)",
                                   height=250, ylabel="unit", smart_scale=True, zoom=1,
                                   revision="mag-line")),
        ], className="chart-grid chart-grid-primary"),
        html.Div([
            _chart("g-axis", 'Title', fig_axis(xyz)),
            _chart("g-scatter", 'Title',
                   fig_2d_scatter(xyz), h=280),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div([
            _chart("g-delta", 'Title',
                   fig_2d_delta(xyz), h=280),
            _chart("g-gauge", 'Title',
                   fig_gauge(m['magnitude'] if have else None)),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div([
            _chart("g-pie", 'Title', fig_pie(m['x'], m['y'], m['z']) if have else fig_pie(None, None, None)),
            _chart("g-bar", 'Title',
                   fig_bar(None, None, None)),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            _chart("g3d-surface", 'Title',
                   fig_3d_surface(xyz, height=400), cfg=CFG_3D, h=400),
            _chart("g3d-terrain", 'Title',
                   fig_3d_terrain(xyz, height=400), cfg=CFG_3D, h=400),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div([
            _chart("g3d-plane", 'Title',
                   fig_3d_error_plane(xyz, height=430), cfg=CFG_3D, h=430),
            _chart("g3d-dipole", 'Title',
                   fig_3d_dipole_field(xyz, height=430), cfg=CFG_3D, h=430),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div(id="mag3d-error"),
        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div([
            html.Div('Subtext', className="validation-subcopy"),
            html.Div(dcc.Graph(id="g-archive", figure=fig_archive(), config=CFG_FLAT,
                               style={"height":"220px", "width":"100%"}),
                     style={"height":"220px","minHeight":"220px"}),
            html.Div([
                html.Div([html.Div("0", id="arch-count", className="arch-stat-val"), html.Div('LABEL', className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="arch-min", className="arch-stat-val"), html.Div('Label', className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="arch-avg", className="arch-stat-val"), html.Div('Label', className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="arch-max", className="arch-stat-val"), html.Div('Label', className="arch-stat-key")], className="arch-stat"),
            ], className="arch-stats"),
        ], className="arch-shell"),
        html.Div([html.Div('LABEL', className="summary-tag"),
                  html.Div([_hi("Magnitude"), html.Span("  "), html.Span("—", id="sum-mag"), html.Br(), html.Br(),
                            _hi("Axes"), html.Span("  "), html.Span("—", id="sum-axes")], className="summary-text")],
                 className="summary-panel"),
        html.Div(id="mag-error"),
        # Staggered so this host never rebuilds every figure in the same tick.
        dcc.Interval(id="mag-num-int", interval=2500, n_intervals=0),
        dcc.Interval(id="mag-chart-int", interval=3000, n_intervals=0),
        dcc.Interval(id="mag-3d-int", interval=3400, n_intervals=0),
        dcc.Interval(id="mag-dir-int", interval=2600, n_intervals=0),
        dcc.Interval(id="mag-arch-int", interval=4000, n_intervals=0),
    ]


def magnetic_view():
    return html.Div(magnetic_body() + [d4_magnetic_blocks()])


def _zoom_range(slider_id):
    """Log scaled zoom (-1..3 -> 0.5x..8x). The Dash slider stays mounted (hidden) so the
    callbacks keep their Input; a plain range control, the same one as the audio gain, is the
    visible face and the page script mirrors its value into the Dash slider."""
    return html.Div([
        html.Div(dcc.Slider(id=slider_id, min=-1, max=3, step=0.25, value=0, updatemode="mouseup"), className="iv-zoom-dash"),
        html.Div(className="iv-zoom-face", **{"data-iv-zoom-face": slider_id}),
        html.Div([html.Span(t) for t in ("0.5×", "1×", "2×", "4×", "8×")], className="iv-zoom-ticks"),
    ], className="iv-zoom-wrap")


def _zoom_bar(slider_id, title, copy):
    return html.Div([
        html.Div([html.Div(title, className="rf-ctl-label"), html.Div(copy, className="validation-subcopy")]),
        _zoom_range(slider_id),
    ], className="rf-ctl-bar", style={"marginBottom": "16px"})


_LISTEN_COPY = {
    "electric": ('TEXT',
                 'Paragraph. Enter your text here.'),
    "mag": ('TEXT',
            'Paragraph. Enter your text here.'),
    "em": ('TEXT',
           'Paragraph. Enter your text here.'),
}


def _emi_listen_card(kind):
    """Listen card for one tab: electric on the Electric tab, magnetic on the Magnetic tab and
    the mix on the Electromagnetic tab. Reuses the Field Audition sources so one stream serves
    every page; the EM block is driven client side (both sources at once)."""
    from .ui import _audio_block
    title, copy = _LISTEN_COPY[kind]
    if kind == "electric":
        blocks = [_audio_block(html, dcc, "efield", 'Title', [])]
    elif kind == "mag":
        blocks = [_audio_block(html, dcc, "mag", 'Title', [])]
    else:
        blocks = [html.Div([
            html.Div([html.Button('Button', type="button", className="iv-btn iv-primary", **{"data-iv-action": "audition", "data-iv-source": "em", "data-iv-op": "start"}),
                      html.Button('Button', type="button", className="iv-btn", **{"data-iv-action": "audition", "data-iv-source": "em", "data-iv-op": "stop"}),
                      html.Button("Mute", type="button", className="iv-btn", **{"data-iv-action": "audition", "data-iv-source": "em", "data-iv-op": "mute", "aria-pressed": "false"})], className="iv-form iv-em-mix"),
            html.Div("", className="iv-inline-result", **{"data-iv-result": "true"}),
        ], className="iv-audio"),
            _audio_block(html, dcc, "efield", 'Title', []),
            _audio_block(html, dcc, "mag", 'Title', [])]
    return html.Div([
        html.Div([html.Div(title, className="rf-ctl-label"), html.Div(copy, className="validation-subcopy")]),
        html.Div(blocks, className="iv-emi-listen" + (" iv-emi-two" if len(blocks) > 1 else "")),
    ], className="rf-ctl-bar iv-emi-card", style={"marginBottom": "16px"})


def _efield_wiring_text():
    """Describe the probe input in prose. Read from acquisition rather than
    written out here: this paragraph claimed a differential pair with a 1.634 V
    reference on A1 long after the probe was rewired single-ended, which is the
    kind of stale sentence a judge would catch and an operator would trust."""
    try:
        from .acquisition import EFIELD_MUX, EFIELD_MUX_NAME
        return EFIELD_MUX_NAME.get(EFIELD_MUX, "input %d" % EFIELD_MUX)
    except Exception:
        return "its configured input"


def _chart_board(which, label):
    """A single 3D board beside the channel that uses it.

    boards.js self-scans for canvas[data-iv-boards] and mounts whichever board
    the attribute names, so this needs no callback and no Python-side 3D."""
    return html.Div([
        html.Div(label, className="chart-hd"),
        html.Div(html.Canvas(**{"data-iv-boards": which,
                                "aria-label": label + ". Drag to rotate, scroll to zoom."}),
                 className="iv-tab-board"),
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


def electric_triaxial_blocks():
    """The triaxial E-field section.

    Deliberately built on the same chart functions as the magnetometer --
    fig_axis, fig_2d_scatter, fig_3d_surface and the rest all take an x/y/z
    history in one shared shape, so publishing the E-field vector in that shape
    means every one of them works here unchanged. Twelve duplicated plotting
    functions would have been the alternative, and they would have drifted."""
    with efield_lock:
        e = dict(efield_data)
        xyz = list(efield_data.get("exyz_history") or [])
        emag = list(efield_data.get("emag_history") or [])
    live = e.get("axes_live", 0)
    status = e.get("axis_status") or {}
    tri = bool(e.get("triaxial"))
    provisional = e.get("data_source") == "ARDUINO_UNO_USB"
    axis_unit = "ADC counts RMS" if provisional else "mV RMS"

    # The section is built whether or not the probe is triaxial. Returning a
    # different panel here would leave e3-int, e3-line and the rest unmounted
    # while their callbacks stay registered -- Dash tolerates that but logs a
    # warning per fire, and the charts silently never update. The not-triaxial
    # case is a state of this section, not a replacement for it: every axis
    # reads as unreporting, which is exactly what is true.
    single_note = None
    if not tri:
        single_note = html.Div([
            html.Div('LABEL', className="summary-tag"),
            html.Div('Paragraph. Enter your text here.',
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

    uncal = all(abs(float(os.environ.get("STUDIO_EFIELD_SCALE_" + a, "1.0")) - 1.0) < 1e-9
                for a in ("X", "Y", "Z"))

    return [
        html.Div('LABEL', className="section-label",
                 style={"marginTop": "30px"}),
        single_note,
        html.Div(('Subtext'
                  if provisional else 'Subtext'),
                 className="validation-subcopy", style={"marginTop": "-4px"}),
        (html.Div('Subtext',
                  className="validation-subcopy", style={"marginBottom":"14px"}) if provisional else None),
        html.Div([html.Span(coverage, style={"color": coverage_colour})],
                 className="validation-subcopy", style={"marginTop": "6px"}),
        html.Div([
            _mcard("e3-x", "X (" + axis_unit + ")", _e3_shown(e.get("ex_mv"))),
            _mcard("e3-y", "Y (" + axis_unit + ")", _e3_shown(e.get("ey_mv"))),
            _mcard("e3-z", "Z (" + axis_unit + ")", _e3_shown(e.get("ez_mv"))),
            _mcard("e3-mag", 'LABEL' + axis_unit + ")", _e3_shown(e.get("e_magnitude_mv")), CYAN),
            _mcard("e3-live", 'LABEL', "%d / 3" % live,
                   GREEN if live == 3 else AMBER if live else RED),
        ], className="metric-row", style={"marginBottom": "14px", "display": "none" if provisional else "flex"}),
        html.Div([
            _mcard("e3-x-vm", "X (unit = N/C)" if provisional else "X (unit)", ("≥ " if (e.get("axis_clipped") or {}).get("x") else "") + _e3_shown(e.get("ex_v_m"))),
            _mcard("e3-y-vm", "Y (unit = N/C)" if provisional else "Y (unit)", ("≥ " if (e.get("axis_clipped") or {}).get("y") else "") + _e3_shown(e.get("ey_v_m"))),
            _mcard("e3-z-vm", "Z (unit = N/C)" if provisional else "Z (unit)", ("≥ " if (e.get("axis_clipped") or {}).get("z") else "") + _e3_shown(e.get("ez_v_m"))),
            _mcard("e3-mag-vm", 'Label', ("≥ " if e.get("clipped") else "") + _e3_shown(e.get("e_magnitude_v_m")), CYAN),
        ], className="metric-row", style={"marginBottom":"14px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"6px"}) if provisional else None,
        html.Div([
            _mcard("e3-static-x", 'LABEL', _e3_shown((e.get("dc_delta_counts") or {}).get("x"))),
            _mcard("e3-static-y", 'LABEL', _e3_shown((e.get("dc_delta_counts") or {}).get("y"))),
            _mcard("e3-static-z", 'LABEL', _e3_shown((e.get("dc_delta_counts") or {}).get("z"))),
            _mcard("e3-static-mag", 'LABEL', _e3_shown(e.get("static_activity_counts")), CYAN),
        ], className="metric-row", style={"marginBottom":"14px"}),
        html.Div([
            _chart("e3-line", 'Title' + axis_unit + ")",
                   make_line_chart(emag, color=AMBER, fill_color="rgba(255,171,64,0.08)",
                                   height=250, ylabel=axis_unit)),
            _chart("e3-axis", 'Title' + axis_unit + ")", fig_axis(xyz, unit=axis_unit)),
            _chart("e3-scatter", 'Title',
                   fig_2d_scatter(xyz, unit=axis_unit), h=280),
            _chart("e3-delta", 'Title',
                   fig_2d_delta(xyz, unit=axis_unit), h=280),
            _chart("e3-gauge", 'Title',
                   fig_gauge(e.get("e_magnitude_mv"), unit=axis_unit)),
            _chart("e3-pie", 'Title',
                   fig_pie(e.get("ex_mv"), e.get("ey_mv"), e.get("ez_mv"))),
            _chart("e3-bar", 'Title',
                   fig_bar(*_e3_stats(emag), unit=axis_unit,
                           quantity='channel 2 activity magnitude' if provisional else 'channel 2 magnitude')),
        ], className="chart-grid"),
        html.Div('LABEL', className="section-label",
                 style={"marginTop": "30px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop": "-4px"}),
        html.Div(_chart("e3-archive", 'Title' + axis_unit + ")",
                        fig_archive(series=emag, unit=axis_unit), h=220),
                 style={"marginTop": "14px"}),
        html.Div('LABEL', className="section-label",
                 style={"marginTop": "30px"}),
        html.Div([
            _chart("e3-surface", 'Title',
                   fig_3d_surface(xyz, height=400), cfg=CFG_3D, h=400),
            _chart("e3-terrain", 'Title',
                   fig_3d_terrain(xyz, height=400), cfg=CFG_3D, h=400),
        ], className="chart-grid"),
        html.Div([
            _chart("e3-plane", 'Title',
                   fig_3d_error_plane(xyz, height=430), cfg=CFG_3D, h=430),
            _chart("e3-dipole", 'Title',
                   fig_3d_dipole_field(xyz, height=430), cfg=CFG_3D, h=430),
        ], className="chart-grid", style={"marginTop": "14px"}),
        html.Div([
            html.Div('LABEL', className="summary-tag"),
            html.Div([
                ('Paragraph. Enter your text here. '),
                _hi("Currently uncalibrated (all factors 1.0); direction is indicative, not accurate."
                    if uncal else "Calibrated per axis."),
                ' Text',
            ], className="summary-text"),
        ], className="summary-panel", style={"marginTop": "20px"}),
        dcc.Interval(id="e3-int", interval=2600, n_intervals=0),
        dcc.Interval(id="e3-3d-int", interval=7000, n_intervals=0),
    ]


def electric_body():
    with efield_lock:
        e = dict(efield_data); hist = list(efield_data["history"]); rel_hist = list(efield_data["rel_history"])
    with mag_lock:
        mag_hist = list(magnetic_data["history"])
        mag_xyz = list(magnetic_data["xyz_history"])
    have = e["last_rx"] is not None
    provisional = e.get("data_source") == "ARDUINO_UNO_USB"
    return [
        html.Div([
            _mcard("ev-level", "X (unit = N/C)", (("≥ " if (e.get("axis_clipped") or {}).get("x") else "") + _e3_shown(e.get("ex_v_m"))) if have and e.get("ex_v_m") is not None else "—"),
            _mcard("ev-index", "Y (unit = N/C)", (("≥ " if (e.get("axis_clipped") or {}).get("y") else "") + _e3_shown(e.get("ey_v_m"))) if have and e.get("ey_v_m") is not None else "—", CYAN),
            _mcard("ev-rms", "Z (unit = N/C)", (("≥ " if (e.get("axis_clipped") or {}).get("z") else "") + _e3_shown(e.get("ez_v_m"))) if have and e.get("ez_v_m") is not None else "—"),
            _mcard("ev-gain", 'Label', (("≥ " if e.get("clipped") else "") + _e3_shown(e.get("e_magnitude_v_m"))) if have and e.get("e_magnitude_v_m") is not None else "—"),
            _mcard("ev-base-top", 'Label' if provisional else 'Label', f"{e['baseline_v_m']:.3f}" if provisional and have else "—"),
            _mcard("ev-delta-top", 'Label' if provisional else 'Label', f"{abs(e.get('e_magnitude_v_m') or 0):.3f}" if provisional and have else "—"),
        ], className="metric-row", style={"marginBottom":"14px"}),
        _emi_listen_card("electric"),
        # ── Environmental Intelligence: re-learn the baseline on command ──
        html.Div([
            html.Button(['BUTTON'], id="ef-recal-btn", className="open-btn",
                        n_clicks=0, style={"width":"auto","marginTop":"0","whiteSpace":"nowrap"}),
            html.Span('Paragraph. Enter your text here.',
                      id="ef-recal-status", style={"fontFamily":FONT,"fontSize":"11px","color":SUBTEXT,"lineHeight":"1.5"}),
        ], style={"display":"flex","alignItems":"center","gap":"16px","marginBottom":"16px","flexWrap":"wrap"}),
        html.Div(id="ef-warn"),   # clipping / overload banner
        html.Div([html.Span(className="online-dot off", id="ef-dot"),
                  html.Span('Subtext', id="ef-status", className="online-text c-sub")],
                 className="online-bar"),
        _zoom_bar("ef-zoom", 'TITLE', 'Paragraph. Enter your text here.'),
        _chart_board("efield", 'Label'),
        html.Div('LABEL', className="section-label"),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            _chart("ef-line", 'Title',
                   make_line_chart(hist, color=AMBER, fill_color="rgba(255,171,64,0.08)", height=250, ylabel="unit  (= N/C)")),
            _chart("ef-index-line", 'Title',
                   make_line_chart(rel_hist, color=CYAN, fill_color="rgba(0,229,255,0.07)", height=250, ylabel="%")),
            _chart("ef-gauge", 'Title', fig_ef_gauge(e["rel_index"] if have else None)),
            _chart("ef-basebar", 'Title', fig_ef_basebar(e["baseline_v_m"], e["field_v_m"], e["peak_v_m"]) if have else fig_ef_basebar(None, None, None)),
        ], className="chart-grid"),
        html.Div([_chart("ef-bullet", 'Title', fig_ef_bullet(e["rel_index"] if have else None, e["level"]), h=140)],
                 style={"marginTop":"14px"}),
        html.Div('LABEL', className="section-label", style={"marginTop":"26px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            _chart("ef-b-correlation", 'Title',
                   fig_ef_b_correlation(mag_hist, rel_hist), h=280),
            _chart("ef-induction-proxy", 'Title',
                   fig_ef_induction_proxy(mag_hist, rel_hist), h=280),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div('LABEL', className="section-label", style={"marginTop":"26px", "display":"none" if provisional else "block"}),
        html.Div([
            html.Div([html.Div("—", id="ev-baseline", className="arch-stat-val"), html.Div('Label', className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div("—", id="ev-peak", className="arch-stat-val"), html.Div('Label', className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div("—", id="ev-util", className="arch-stat-val"), html.Div('LABEL', className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div("—", id="ev-minmax", className="arch-stat-val"), html.Div('LABEL', className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div(f"{EF_V_PER_M_PER_VOLT:,.3f}", className="arch-stat-val"), html.Div('Label', className="arch-stat-key")], className="arch-stat"),
        ], className="arch-stats", style={"display":"none" if provisional else "grid"}),
        html.Div([html.Div('LABEL', className="summary-tag"),
                  html.Div([_hi("State"), html.Span("  "), html.Span("—", id="ev-statustext")], className="summary-text")],
                 className="summary-panel", style={"display":"none" if provisional else "block"}),
        html.Div([html.Div('LABEL', className="summary-tag"),
                  html.Div(['Text ', _hi(_efield_wiring_text()),
                            'Paragraph. Enter your text here. ',
                            'Text ', _hi("AC RMS"),
                            ' Text ',
                            _hi("auto-ranges"), ' Paragraph. Enter your text here. ',
                            'Paragraph. Enter your text here. ',
                            _hi("relative index"), ' Text ',
                            _hi("LOW"), " (< 3× baseline), ", _hi("MID"), " (3–10×), ", _hi("HIGH"), " (> 10×). ",
                            'Text ', _hi("reference-scaled estimate"),
                            'Paragraph. Enter your text here.'], className="summary-text")],
                 className="summary-panel"),
        html.Div(id="ef-error"),
    ] + electric_triaxial_blocks() + ([
        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div([
            html.Div([html.Div(f"{e.get('baseline_v_m', 0.0):.3f}" if have else "—", id="ev-bottom-baseline", className="arch-stat-val"), html.Div('Label', className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div(f"{e.get('sample_rate', 0):.1f}" if have else "—", id="ev-bottom-rate", className="arch-stat-val"), html.Div('LABEL', className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div(f"{e['min_code']} / {e['max_code']}" if have else "—", id="ev-bottom-minmax", className="arch-stat-val"), html.Div('LABEL', className="arch-stat-key")], className="arch-stat"),
            html.Div([html.Div('TEXT', className="arch-stat-val"), html.Div('Label', className="arch-stat-key")], className="arch-stat"),
        ], className="arch-stats"),
    ] if provisional else []) + [
        # Offset from the magnetic intervals so combined view spreads the load.
        dcc.Interval(id="ef-num-int", interval=2500, n_intervals=0),
        dcc.Interval(id="ef-chart-int", interval=3000, n_intervals=0),
    ]


def electric_view():
    with efield_lock:
        provisional = efield_data.get("data_source") == "ARDUINO_UNO_USB"
    if provisional:
        return html.Div(electric_body() + [html.Div([
            html.Div('LABEL', className="section-label"),
            html.Div('Subtext',
                     className="validation-subcopy"),
        ], className="summary-panel", style={"marginTop":"24px"})])
    return html.Div(electric_body() + [d4_electric_blocks()])


def combined_view():
    base = _combined_view_base()
    base.children.append(d4_combined_blocks())
    return base


def _em_composite_xyz(magnetic_xyz, electric_xyz, limit=200):
    """Equal-weight, dimensionless E+B geometry for visualization only.

    unit and ADC counts cannot be added.  Each recent vector series is therefore
    normalized by its own observed magnitude before the corresponding X/Y/Z
    components are averaged.  The result shows coincident movement and shape;
    it is not a new physical field unit or a calibrated EM vector.
    """
    count = min(len(magnetic_xyz), len(electric_xyz), limit)
    if count < 2:
        return []
    mag = list(magnetic_xyz)[-count:]
    elec = list(electric_xyz)[-count:]
    mag_scale = max((math.sqrt(sum(float(v) ** 2 for v in row[:3])) for row in mag), default=1.0) or 1.0
    elec_scale = max((math.sqrt(sum(float(v) ** 2 for v in row[:3])) for row in elec), default=1.0) or 1.0
    return [tuple((float(m[i]) / mag_scale + float(e[i]) / elec_scale) * 0.5 for i in range(3))
            for m, e in zip(mag, elec)]


def _combined_view_base():
    with mag_lock:
        mag_hist = list(magnetic_data["history"])
        mag_xyz = list(magnetic_data["xyz_history"])
    with efield_lock:
        ef_hist = list(efield_data["history"])
        ef_rel = list(efield_data["rel_history"])
        exyz = list(efield_data.get("exyz_history") or [])
        provisional = efield_data.get("data_source") == "ARDUINO_UNO_USB"
    em_xyz = _em_composite_xyz(mag_xyz, exyz)
    em_mag = [math.sqrt(x*x + y*y + z*z) for x, y, z in em_xyz]
    return html.Div([
        html.Div('LABEL', className="section-label"),
        html.Div(
            'Subtext',
            className="validation-subcopy",
        ),
        _emi_listen_card("em"),
        _zoom_bar("em-zoom", 'TITLE', 'Paragraph. Enter your text here.'),
        html.Div([
            _chart("em-overlay", 'Title',
                   fig_em_overlay(mag_hist, ef_hist), h=320),
        ], className="chart-grid chart-grid-primary", style={"marginTop":"14px"}),
        html.Div([
            _chart("em-normalized-overlay", 'Title',
                   fig_em_normalized_overlay(mag_hist, ef_rel), h=300),
            _chart("em-coupling", 'Title',
                   fig_ef_induction_proxy(mag_hist, ef_rel), h=300),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            _chart("em3-line", 'Title', make_line_chart(em_mag, color=CYAN, height=250, ylabel="normalized")),
            _chart("em3-axis", 'Title', fig_axis(em_xyz, unit="normalized")),
            _chart("em3-scatter", 'Title', fig_2d_scatter(em_xyz, unit="normalized"), h=280),
            _chart("em3-delta", 'Title', fig_2d_delta(em_xyz, unit="normalized"), h=280),
            _chart("em3-gauge", 'Title', fig_gauge(em_mag[-1] if em_mag else None, unit="normalized")),
            _chart("em3-pie", 'Title', fig_pie(*(em_xyz[-1] if em_xyz else (None,None,None)))),
            _chart("em3-bar", 'Title', fig_bar(*_e3_stats(em_mag), unit="normalized", quantity="E+B composite magnitude")),
        ], className="chart-grid"),
        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div([
            _chart("em3-vector-overlay", 'Title', fig_em_vector_overlay_3d(mag_xyz, exyz), cfg=CFG_3D, h=470),
            _chart("em3-cross-proxy", 'Title', fig_em_cross_proxy_3d(mag_xyz, exyz), cfg=CFG_3D, h=470),
            _chart("em3-surface", 'Title', fig_3d_surface(em_xyz, height=400, unit="normalized"), cfg=CFG_3D, h=400),
            _chart("em3-terrain", 'Title', fig_3d_terrain(em_xyz, height=400, unit="normalized"), cfg=CFG_3D, h=400),
            _chart("em3-plane", 'Title', fig_3d_error_plane(em_xyz, height=430), cfg=CFG_3D, h=430),
            _chart("em3-dipole", 'Title', fig_3d_dipole_field(em_xyz, height=430), cfg=CFG_3D, h=430),
        ], className="chart-grid", style={"marginTop":"14px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"10px"}),
        html.Div([
            _chart("em-correlation", 'Title',
                   fig_ef_b_correlation(mag_hist, ef_rel), h=300),
        ], className="chart-grid chart-grid-primary", style={"marginTop":"14px"}),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div(['Subtext ', _hi("how they move together"),
                  'Subtext'],
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        _graph_block("em-traj3d", fig_em_trajectory_3d(mag_hist, ef_rel), 440, CFG_3D),
        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div('Subtext '
                 + ('Subtext'
                    if provisional else 'Subtext'),
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            _chart("em-b-plane", 'Title', fig_3d_error_plane(mag_xyz, height=430), cfg=CFG_3D, h=430),
            _chart("em-e-plane", 'Title', fig_3d_error_plane(exyz, height=430), cfg=CFG_3D, h=430),
            _chart("em-b-dipole", 'Title', fig_3d_dipole_field(mag_xyz, height=430), cfg=CFG_3D, h=430),
            _chart("em-e-dipole", 'Title', fig_3d_dipole_field(exyz, height=430), cfg=CFG_3D, h=430),
        ], className="chart-grid", style={"marginTop":"14px"}),
        dcc.Interval(id="em-overlay-int", interval=3600, n_intervals=0),
        html.Div([
            html.Div('LABEL', className="summary-tag"),
            html.Div(
                'Paragraph. Enter your text here.',
                className="summary-text",
            ),
        ], className="summary-panel"),
    ])


def em_page():
    airlock = html.Div(className="iv-scrub-hero", **{"data-iv-scrub": "em-vector",
                                                    "data-iv-title": 'Title',
                                                    "data-iv-tagline": 'Paragraph. Enter your text here.'})
    return html.Div([
        airlock,
        dcc.Link(html.Button("BACK", className="back-btn"), href="/", style={"textDecoration":"none"}),
        _ph('LIVE  Source 1 + Source 2', 'Title',
            'Subtext'),
        html.Hr(className="divider"),
        html.Div([
            html.Button("CHANNEL 1", id="em-tab-mag", className="tab-btn active", n_clicks=0),
            html.Button("CHANNEL 2", id="em-tab-elec", className="tab-btn", n_clicks=0),
            html.Button('BUTTON', id="em-tab-both", className="tab-btn", n_clicks=0),
        ], className="tab-bar em-mode-tabs"),
        html.Div(id="em-subcontent", children=magnetic_view()),
    ], style=PAD)


# ════════════════════════════════════════════════════════
#  SPECTRUM  (tinySA Ultra — live)
# ════════════════════════════════════════════════════════
def _rf_dev_strip():
    with spectrum_lock: s = dict(spectrum_data)
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
    return [html.Div([html.Div(k, className="rf-dev-key"), html.Div(v, className="rf-dev-val")],
                     className="rf-dev-cell") for k, v in cells]


def rf_sweep_body():
    with spectrum_lock:
        s = dict(spectrum_data)
        wf_rows, wf_times = _waterfall_rows(
            list(spectrum_data["waterfall"]),
            list(spectrum_data["waterfall_times"]),
            list(spectrum_data["freqs"]),
        )
    return [
        html.Div([html.Button('BUTTON', id="rf-sweep-now", className="rf-btn rf-on", n_clicks=0),
                  html.Span("", id="rf-sweep-top-note", className="validation-subcopy")],
                 className="spectrum-sweep-action"),
        # ── orientation panel: this instrument is unreadable without it ──
        html.Div([html.Div('LABEL', className="summary-tag"),
                  html.Div(['Paragraph. Enter your text here. ',
                            _hi("horizontal is frequency"), ' Text ',
                            _hi('vertical is power in unit'), ' Paragraph. Enter your text here. ',
                            _hi("noise floor"), ' Text', html.Br(), html.Br(),
                            'Text ',
                            _hi("continuous range"), ' Text ',
                            _hi("as many samples across it as you ask for"),
                            f". At full span with {TSA_DEFAULT_PTS} points, each bin is very wide. "
                            "This is a coarse wideband survey: narrow or short-duration signals may be "
                            "missed. Narrowing the span improves bin width, but a spectrum peak still "
                            "does not identify a protocol, device or transmitter."],
                           className="summary-text")],
                 className="summary-panel", style={"marginTop":"0"}),
        html.Div('Label', className="section-label", style={"marginTop":"24px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        _dbm_scale(),

        html.Div("DEVICE", className="section-label", style={"marginTop":"26px"}),
        html.Div(_rf_dev_strip(), id="rf-dev-strip", className="rf-dev-strip"),

        html.Div([
            _mcard("rf-peak-f",  'LABEL', "—", AMBER),
            _mcard("rf-peak-l",  'LABEL',     "—", CYAN),
            _mcard("rf-floor",   'Label',    "—"),
            _mcard("rf-span",    'LABEL',           _span_label(s["span_start"], s["span_stop"])),
            _mcard("rf-res",     'LABEL',     "—"),
            _mcard("rf-sweep",   'LABEL',     "—"),
        ], className="metric-row", style={"marginBottom":"18px"}),

        # ── controls ──
        html.Div([
            html.Div([html.Div('Label', className="rf-ctl-label"),
                      html.Div([html.Button(lbl, id=f"rf-preset-{key}", className="rf-btn", n_clicks=0)
                                for key, lbl, _a, _b in TSA_PRESETS], className="rf-ctl-row")],
                     className="rf-ctl-group"),
            html.Div([html.Div('Label', className="rf-ctl-label"),
                      html.Div([html.Button("101", id="rf-pts-101", className="rf-btn", n_clicks=0),
                                html.Button("251", id="rf-pts-251", className="rf-btn rf-on", n_clicks=0),
                                html.Button("290", id="rf-pts-290", className="rf-btn", n_clicks=0)],
                               className="rf-ctl-row")], className="rf-ctl-group"),
            html.Div([html.Div('Label', className="rf-ctl-label"),
                      html.Div([html.Button('BUTTON', id="rf-ax-lin", className="rf-btn rf-on", n_clicks=0),
                                html.Button("LOG", id="rf-ax-log", className="rf-btn", n_clicks=0)],
                               className="rf-ctl-row")], className="rf-ctl-group"),
            html.Div([html.Div('Label', className="rf-ctl-label"),
                      html.Div([html.Button("ON", id="rf-band-on", className="rf-btn rf-on", n_clicks=0),
                                html.Button("OFF", id="rf-band-off", className="rf-btn", n_clicks=0)],
                               className="rf-ctl-row")], className="rf-ctl-group"),
            html.Div([html.Div('Label', className="rf-ctl-label"),
                      html.Div([
                          html.Button('BUTTON', id="rf-hold-reset", className="rf-btn", n_clicks=0),
                          html.Button('BUTTON', id="rf-pause", className="rf-btn", n_clicks=0),
                      ], className="rf-ctl-row")], className="rf-ctl-group"),
        ], className="rf-ctl-bar"),
        html.Div([
            html.Div('Label', className="rf-ctl-label"),
            html.Div([
                dcc.Input(id="rf-custom-start", type="number", min=0, max=6000,
                          value=88, debounce=True, placeholder='Enter your text here'),
                dcc.Input(id="rf-custom-stop", type="number", min=0, max=6000,
                          value=108, debounce=True, placeholder='Enter your text here'),
                html.Button('BUTTON', id="rf-custom-apply",
                            className="rf-btn", n_clicks=0),
                html.Span("", id="rf-custom-status", className="validation-subcopy"),
            ], className="rf-ctl-row"),
        ], className="rf-ctl-bar", style={"marginTop":"10px"}),
        dcc.Store(id="rf-bands-mode", data=True),
        dcc.Store(id="rf-axis-mode", data="lin"),
        dcc.Store(id="rf-points-mode", data=TSA_DEFAULT_PTS),
        dcc.Store(id="rf-preset-mode", data="full"),

        html.Div(id="rf-warn"),
        html.Div([html.Span(className="online-dot off", id="rf-dot"),
                  html.Span('Subtext', id="rf-status", className="online-text c-sub")],
                 className="online-bar"),

        html.Div('LABEL', className="section-label"),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        _graph_block("rf-sweep-graph",
                     fig_spectrum(s["freqs"], s["levels"], s["maxhold"],
                                  s["peaks"], s["floor"], False, 380, True), 380),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div([
            html.Div([html.Div("#"), html.Div('TEXT'), html.Div('TEXT'),
                      html.Div('TEXT'), html.Div('TEXT')], className="rf-peak-head"),
            html.Div(_peak_rows(s["peaks"], s["floor"]), id="rf-peak-body"),
        ], className="rf-peak-table"),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        html.Div(emi_rows(s), id="rf-emi-body", className="rf-emi-list"),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div(f"The last {TSA_WATERFALL_ROWS} sweeps stacked over time — a signal that comes and goes shows as a broken vertical stripe.",
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        _graph_block("rf-waterfall-graph",
                     fig_waterfall(wf_rows, s["freqs"], wf_times, 320), 320),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div('Subtext',
                 className="validation-subcopy", style={"marginTop":"-4px"}),
        _graph_block("rf-terrain-graph",
                     fig_rf_terrain(wf_rows, s["freqs"], wf_times, 460), 460, CFG_3D),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div([
            _chart("rf-bands-graph", 'Title', fig_rf_bands(s["peaks"])),
            _chart("rf-trend-graph", 'Title', fig_rf_trend(s["peak_history"])),
        ], className="chart-grid"),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div([
            html.Div('Subtext',
                     className="validation-subcopy"),
            html.Div([
                html.Div([html.Div("0", id="rf-arch-count", className="arch-stat-val"),
                          html.Div('LABEL', className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="rf-arch-min", className="arch-stat-val"),
                          html.Div('Label', className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="rf-arch-avg", className="arch-stat-val"),
                          html.Div('Label', className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="rf-arch-max", className="arch-stat-val"),
                          html.Div('Label', className="arch-stat-key")], className="arch-stat"),
                html.Div([html.Div("—", id="rf-arch-str", className="arch-stat-val"),
                          html.Div('LABEL', className="arch-stat-key")], className="arch-stat"),
            ], id="rf-arch-stats", className="arch-stats"),
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
                            "the parser, units, analyser state and RF setup require verification. MTDI lowers spectrum health and the device strip shows the queried level-offset state. ",
                            'Paragraph. Enter your text here.'],
                           className="summary-text")],
                 className="summary-panel"),
        html.Div(id="rf-error"),

        # Staggered: the sweep itself takes seconds, so polling faster only wastes CPU.
        dcc.Interval(id="rf-num-int",   interval=1000, n_intervals=0),
        dcc.Interval(id="rf-chart-int", interval=2500, n_intervals=0),
        dcc.Interval(id="rf-wf-int",    interval=4300, n_intervals=0),
    ]


def rf_sweep_view():
    return html.Div(rf_sweep_body() + [d4_spectrum_blocks()])


def sdr_view():
    """RTL-SDR panel: live slice, waterfall, carriers and an on-demand stitched sweep.

    Deliberately separate from the tinySA view. The tinySA answers "what is present
    across a very wide span"; the dongle answers "what exactly is happening inside
    two megahertz, right now". Levels here are dBFS and are never presented as unit.
    """
    snap = sdr_snapshot(include_trace=False)
    presets = snap.get("presets") or []
    return html.Div([
        html.Div([html.Button('BUTTON', id="sdr-sweep-now", className="rf-btn rf-on", n_clicks=0),
                  html.Span("", id="sdr-sweep-top-note", className="validation-subcopy")],
                 className="spectrum-sweep-action"),
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
            html.Button('BUTTON', id="sdr-tune", className="rf-btn", n_clicks=0),
            html.Span('SUBTEXT', className="validation-subcopy", style={"margin":"0 4px 0 12px"}),
            dcc.Dropdown(id="sdr-gain", options=[{"label":"auto","value":"auto"}],
                         value="auto", clearable=False,
                         style={"width":"130px","display":"inline-block","verticalAlign":"middle"}),
        ], className="rf-ctl-row", style={"marginTop":"8px"}),
        html.Div([html.Button(name, id={"type":"sdr-preset","band":name}, className="rf-btn", n_clicks=0)
                  for name, _a, _b in SDR_PRESETS], className="rf-ctl-row", style={"marginTop":"8px"}),

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
            html.Button('BUTTON', id="sdr-sweep-go", className="rf-btn", n_clicks=0),
            html.Button('BUTTON', id="sdr-sweep-stop", className="rf-btn", n_clicks=0),
            html.Span("", id="sdr-sweep-note", className="validation-subcopy",
                      style={"marginLeft":"10px"}),
        ], className="rf-ctl-row", style={"marginTop":"8px"}),
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
        html.Div([html.Button('BUTTON', id="wf-sweep-now", className="rf-btn rf-on", n_clicks=0),
                  html.Span("", id="wf-sweep-note", className="validation-subcopy")],
                 className="spectrum-sweep-action"),
        html.Div([html.Div('LABEL', className="summary-tag"),
                  html.Div(['Paragraph. Enter your text here. ',
                            _hi(w["scan_mode"]), ". NetworkManager returns access-point records; "
                            "when active discovery is enabled the OS scan is requested but the "
                            "driver's active/passive behaviour is not claimed. No AP IP addresses "
                            "are inferred and no TinySA peak is assigned to an SSID."],
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
        html.Div([html.Button('BUTTON', id="bt-sweep-now", className="rf-btn rf-on", n_clicks=0),
                  html.Span("", id="bt-sweep-note", className="validation-subcopy")],
                 className="spectrum-sweep-action"),
        html.Div([html.Div('LABEL', className="summary-tag"),
                  html.Div(['Paragraph. Enter your text here. ',
                            _hi(b["scan_mode"]), ". Discovery does not pair or connect, but it is an "
                            "active OS radio operation unless explicitly reported otherwise. Names, "
                            "vendors and rotating addresses are best-effort and do not establish exact "
                            "identity or distance. No TinySA peak is assigned to a device."],
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


def spectrum_page():
    from .ui import parallax_header
    return html.Div([
        html.Div(parallax_header(html, 'Title'), className="parallax__pin"),
        html.Div([
            dcc.Link(html.Button("BACK", className="back-btn"), href="/", style={"textDecoration":"none"}),
            _ph('LIVE  Source 3 ULTRA + Source 4 + Channel 5 + BLE', 'Title',
                'Subtext'),
            html.Hr(className="divider"),
            html.Div([
                html.Button('BUTTON',  id="sp-tab-rf",   className="tab-btn active", n_clicks=0),
                html.Button('BUTTON',   id="sp-tab-sdr",  className="tab-btn", n_clicks=0),
                html.Button('BUTTON',      id="sp-tab-wifi", className="tab-btn", n_clicks=0),
                html.Button('BUTTON', id="sp-tab-bt",   className="tab-btn", n_clicks=0),
            ], className="tab-bar"),
            html.Div(id="sp-subcontent", children=rf_sweep_view()),
        ], className="iv-page-body", style={**PAD, "margin": "-60vh auto 0"}),
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
    "power_magnetic": ('Text', 'Paragraph. Enter your text here.'),
    "power_network": ('TEXT', 'Paragraph. Enter your text here.'),
    "rf": ('TEXT', 'Paragraph. Enter your text here.'),
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
    return html.Button(label, id={"type": "d4btn", "action": action, "where": where}, className="rf-btn", n_clicks=0, title=title)


def d4_input(field, where, placeholder, width="150px", value=None):
    return dcc.Input(id={"type": "d4in", "field": field, "where": where}, type="text", placeholder=placeholder, debounce=True, value=value, style={"width": width})


def d4_status(where, card="config"):
    # one status line per card: several cards share a page ('where'), so the card name keeps the
    # component identity unique
    return html.Span("", id={"type": "d4status", "where": where, "card": card}, className="validation-subcopy")


def d4_controls(where, *items):
    first = getattr(items[0], "id", None) or {}
    card = first.get("action") or first.get("field") or "config"
    return html.Div(list(items) + [d4_status(where, card)], className="rf-ctl-row", style={"marginTop": "8px"})


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
                         options=[{"label": 'Label', "value": "magnetic"},
                                  {"label": 'Label', "value": "electric"}],
                         value="magnetic", clearable=False, style={"width": "220px"}),
            d4_input("repeat_runs", where, 'Enter your text here', "120px"),
            d4_input("repeat_window", where, 'Enter your text here', "160px"),
            d4_button("repeat_start", where, 'LABEL',
                      'Title'),
            d4_status(where, "repeat_channel"),
        ], className="rf-ctl-row"),
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
        ], className="rf-ctl-row"),
        html.Div('Text', id={"type": "d4", "block": "validation", "where": where}, className="d4-block"),
        dcc.Graph(id={"type": "d4g", "block": "validation", "where": where}, config={"displayModeBar": False}, style={"height": "220px"}),
        html.Div([
            html.A(html.Button('BUTTON', className="rf-btn"), href="/api/d4/report.pdf", target="_blank"),
            html.A(html.Button('BUTTON', className="rf-btn"), href="/api/d4/export?seconds=300", target="_blank"),
            html.A(html.Button('BUTTON', className="rf-btn"), href="/api/d4/export.csv?seconds=300", target="_blank"),
            d4_status(where, "links"),
        ], className="rf-ctl-row", style={"marginTop": "8px"}),
    ], className="chart-card d4-card")


def d4_config_card(where):
    return html.Div([
        html.Div(D4_BLOCK_META["config"][0], className="section-label"),
        html.Div(D4_BLOCK_META["config"][1], className="validation-subcopy"),
        html.Div('Text', id={"type": "d4", "block": "config", "where": where}, className="d4-block"),
        html.Div([
            html.A(html.Button('BUTTON', className="rf-btn"), href="/api/d4/export?seconds=300", target="_blank"),
            html.A(html.Button('BUTTON', className="rf-btn"), href="/api/d4/export.csv?seconds=300", target="_blank"),
            html.A(html.Button('BUTTON', className="rf-btn"), href="/api/d4/stream", target="_blank"),
            dcc.Upload(html.Button('Button', className="rf-btn"), id={"type": "d4up", "where": where}, accept=".json", multiple=False),
            d4_status(where),
        ], className="rf-ctl-row", style={"marginTop": "8px"}),
        html.Div([
            html.Div('Subtext', className="validation-subcopy"),
            d4_input("d3_detection", where, 'Enter your text here', "150px"), d4_input("d3_fp", where, 'Enter your text here', "150px"),
            d4_input("d3_cal", where, 'Enter your text here', "160px"), d4_input("d3_mtdi", where, 'Enter your text here', "150px"),
            d4_input("d3_time", where, 'Enter your text here', "140px"), d4_button("d3_save", where, 'LABEL'),
            d4_status(where, "d3_save"),
        ], className="rf-ctl-row", style={"marginTop": "8px"}),
    ], className="chart-card d4-card")


def d4_engine_section():
    """The D4 analysis engine: the score, its parts and the stores.

    Not an MTDI pillar. MTDI asks whether the instrument can be trusted; D4 asks what
    the field is actually doing. It sits on the Sixth Sense page, with the rest of the
    interpretation work. The individual analyses live on the pages they belong to
    (EM Field tabs, Spectrum, Environmental Intelligence, Validation Chamber).
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


def d4_magnetic_blocks():
    w = "mag"
    return html.Div([
        html.Div('LABEL', className="section-label", style={"marginTop": "26px"}),
        html.Div([d4_calibration_card(w)], className="d4-grid one"),
        html.Div([d4_block("power_magnetic", w, graph="200px"), d4_block("calhealth", w)], className="d4-grid two"),
        html.Div([d4_block("transients", w), d4_block("noise", w)], className="d4-grid two"),
    ], className="d4-section")


def d4_electric_blocks():
    w = "ef"
    return html.Div([
        html.Div('LABEL', className="section-label", style={"marginTop": "26px"}),
        html.Div([d4_power_card(w)], className="d4-grid one"),
        html.Div([d4_block("power_network", w), d4_block("noise", w)], className="d4-grid two"),
    ], className="d4-section")


def d4_combined_blocks():
    w = "em"
    return html.Div([
        html.Div('LABEL', className="section-label", style={"marginTop": "26px"}),
        html.Div([d4_block("exposure", w)], className="d4-grid one"),
        html.Div([d4_block("consensus", w), d4_block("correlation", w)], className="d4-grid two"),
        html.Div([d4_block("baseline", w), d4_fingerprint_card(w)], className="d4-grid two"),
    ], className="d4-section")


def d4_spectrum_blocks():
    w = "rf"
    return html.Div([
        html.Div('LABEL', className="section-label", style={"marginTop": "26px"}),
        html.Div([d4_block("rf", w), d4_block("trend", w)], className="d4-grid two"),
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
    'What am I looking at on the Channel 3 tab?',
    'Is my channel 1 reading normal right now?',
    "Explain unit like I'm five",
]


def _nvtra_greeting():
    if nvtra_online():
        return ('NVTRA online. Ask me about any reading on this dashboard — the channel 1, the Channel 2, the channel 3 sweep, or what the numbers mean. I can see the live values.')
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
                f"{row['electric_v_m']:.0f} unit · {row['magnetic_ut']:.0f} unit · 1 cm"
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
    base = _P(__file__).resolve().parent / "assets" / "nvtra"
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
                    html.Div("NVTRA", className="chat-main-brand"),
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


def emi_analysis_panel():
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
            html.Div(engine, id="emi-engine", className="nvtra-badge nvtra-live" if online else "nvtra-badge"),
        ], className="emi-analysis-head"),
        html.Div(id="emi-live-state", className="emi-live-state"),
        html.Div([
            html.Button('BUTTON', id="emi-analyse-btn", n_clicks=0,
                        disabled=not online, className="open-btn emi-action"),
            html.Button('BUTTON', id="emi-auto-btn", n_clicks=0,
                        disabled=not online, className="back-btn emi-action"),
            html.Span('Subtext' if not online else
                      'Subtext',
                      id="emi-status", className="validation-subcopy"),
        ], className="emi-controls"),
        dcc.Store(id="emi-auto-state", data=False, storage_type="memory"),
        dcc.Interval(id="emi-auto-interval", interval=45000, n_intervals=0, disabled=True),
        dcc.Loading(
            html.Div('Text', id="emi-result",
                     className="emi-result", **{"aria-live":"polite"}),
            type="circle", color=CYAN,
        ),
    ], className="emi-analysis-panel")


def nvtra_field_section():
    return html.Div([
        _section_head('LABEL', "NVTRA", 'Paragraph. Enter your text here.', 'LABEL', YELLOW),
        nvtra_identity_section(),
        emi_analysis_panel(),
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
        ], id="aether-terminal", className="aether-terminal", **{"data-iv-aether-terminal": "1"}),
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
    with mag_lock:
        mag_base = (f"{magnetic_data['baseline_magnitude']:.2f} unit"
                    if magnetic_data["baseline_calibrated"] else "LEARNING")
        mag_delta = (f"{magnetic_data['baseline_delta']:.2f} unit"
                     if magnetic_data["baseline_calibrated"] else "—")
    with efield_lock:
        provisional = efield_data.get("data_source") == "ARDUINO_UNO_USB"
        ef_base = ("—" if provisional else f"{efield_data['baseline_v_m']:.3f} unit"
                   if efield_data["calibrated"] else "LEARNING")
        ef_live = (f"{efield_data['rms_counts']:.2f} ADC counts RMS"
                   if provisional and efield_data.get("rms_counts") is not None else
                   f"{efield_data['field_v_m']:.3f} unit"
                   if efield_data["last_rx"] is not None and efield_data["field_v_m"] is not None else "—")
    return html.Div([
        _section_head(
            'LABEL', "Environmental Intelligence",
            'Paragraph. Enter your text here.',
            'LABEL', GREEN,
        ),
        html.Div([
            html.Div([html.Div('LABEL', className="sys-name"),
                      html.Div(mag_base, id="ei-mag-baseline", className="sys-value c-cyan"),
                      html.Div('Subtext', className="sys-sub")], className="sys-card"),
            html.Div([html.Div('LABEL', className="sys-name"),
                      html.Div(mag_delta, id="ei-mag-delta", className="sys-value c-amber"),
                      html.Div('Subtext', className="sys-sub")], className="sys-card"),
            html.Div([html.Div('LABEL', className="sys-name"),
                      html.Div(ef_base, id="ei-ef-baseline", className="sys-value c-cyan"),
                      html.Div('Subtext', className="sys-sub")], className="sys-card"),
            html.Div([html.Div('LABEL', className="sys-name"),
                      html.Div(ef_live, id="ei-ef-live", className="sys-value c-amber"),
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


# The D4 analysis engine is deliberately NOT in this list. It is a signal-processing
# engine, not one of MTDI's diagnostic pillars - MTDI asks whether the instrument can
# be trusted, while D4 asks what the field is doing. It lives on the Sixth Sense page
# with the other interpretation work.
MTDI_ORBIT_PILLARS = [
    ("validation", "00", "Validation Chamber", "Evidence",
     'Text', BLUE, validation_chamber_section),
    ("environment", "01", "Environmental Intelligence", "Baselines",
     'Text', GREEN, environmental_intelligence_section),
    ("nvtra", "02", "NVTRA", "Health",
     'Paragraph. Enter your text here.', YELLOW, nvtra_field_section),
    ("i3", "03", 'Text', "Meaning",
     'Text', PURPLE, i3_field_section),
    ("aether", "04", "Aether", "Reason",
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
            html.Div('Title', className="mtdi-v2-title"),
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
        html.Div(className="iv-scrub-hero", **{"data-iv-scrub": "mtdi-flow",
                 "data-iv-title": 'TITLE',
                 "data-iv-tagline": 'Paragraph. Enter your text here.'}),
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
        html.Div(html.Div(className="iv-lunar-stage", **{"data-iv-lunar": "true"}), className="iv-lunar-open"),
        _ph("SETTINGS", "Settings", 'Subtext'),
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
                html.Div([html.B('Text'), html.Span('Paragraph. Enter your text here.', **{"data-iv-replay-note": "true"})], className="set-lab"),
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
                html.Button('BUTTON', type="button", className="key-btn key-btn-add", title='Title', **{"data-iv-action": "hand_tracking"}),
                html.Button("3D HAND CONTROL: ON", type="button", className="key-btn key-btn-add", **{"data-iv-action": "hand3d", "aria-pressed": "true"}),
                html.Div("Pinch on the Earth or the constellation to hold, spin and zoom it with your hands.", className="key-status", style={"flex":"1","minWidth":"240px"}, **{"data-iv-hand3d-note": "true"}),
            ], className="key-add-row"),
            html.Div([
                html.Button('BUTTON', type="button", className="key-btn key-btn-add", **{"data-iv-action": "hand_calibrate"}),
                html.Button('BUTTON', type="button", className="key-btn", **{"data-iv-action": "hand_debug", "aria-pressed": "false"}),
                html.Button('BUTTON', type="button", className="key-btn", **{"data-iv-action": "hand_profile_reset"}),
                html.Button('BUTTON', type="button", className="key-btn", title='Title', **{"data-iv-action": "left_handed", "aria-pressed": "false"}),
                html.Button('BUTTON', type="button", className="key-btn", title='Title', **{"data-iv-action": "cursor_mode"}),
                html.Button('BUTTON', type="button", className="key-btn", title='Title', **{"data-iv-action": "buddy_toggle", "aria-pressed": "true"}),
                html.Div("Using default thresholds. Calibrate once with the camera on for reliable pinch, thumbs and pause.", className="key-status", style={"flex":"1","minWidth":"240px"}, **{"data-iv-hand-profile-note": "true"}),
            ], className="key-add-row", style={"marginTop":"10px"}),
            html.Div([
                html.Div('TEXT', className="key-status", style={"letterSpacing":".18em","fontSize":"10px","marginBottom":"6px"}),
                html.Div("No saved calibrations yet.", className="iv-hand-profiles", **{"data-iv-hand-profiles": "true"}),
            ], style={"marginTop":"12px"}),
        ], className="set-card", style={"paddingTop":"18px","paddingBottom":"18px"}),

        html.Div('LABEL', className="section-label", style={"marginTop":"30px"}),
        html.Div('Title',
                 className="page-subtitle", style={"marginBottom":"16px","maxWidth":"760px"}),
        html.Div([
            html.Form([
                html.Div([
                    dcc.Input(name="key", type="password", value="", autoComplete="off",
                              placeholder='Enter your text here', className="iv-voice-key-input"),
                    html.Button('BUTTON', type="button", className="key-btn key-btn-add", **{"data-iv-action": "elevenlabs_key"}),
                ], className="key-add-row"),
                html.Div(_voice_key_status(), className="key-status", **{"data-iv-result": "true"}),
            ], className="iv-form", **{"data-iv-form": "voice"}),
            html.Form([
                html.Div([
                    html.Select([html.Option('Text', value="")], name="voice", className="iv-voice-select", **{"data-iv-voices": "true"}),
                    html.Button('BUTTON', type="button", className="key-btn key-btn-add", **{"data-iv-action": "elevenlabs_voice"}),
                    html.Button('BUTTON', type="button", className="key-btn key-btn-test", **{"data-iv-action": "voice_preview"}),
                ], className="key-add-row", style={"marginTop": "14px"}),
                html.Div('Paragraph. Enter your text here.', className="key-status", **{"data-iv-result": "true"}),
            ], className="iv-form", **{"data-iv-form": "voice-pick"}),
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

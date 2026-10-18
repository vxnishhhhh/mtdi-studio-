"""Routing, navigation, live callbacks, self test, argument parsing and main."""
from ._shared import inherit
inherit(globals(), 'common', 'sensors', 'intelligence', 'system', 'tokens', 'theme', 'browser', 'webapp', 'reports', 'charts', 'pages')

# ════════════════════════════════════════════════════════
#  ROUTING / NAV
#
#  display_page returns the new page and a fresh scroll token in the SAME callback
#  response, so Dash mounts the content and the clientside scroll reset fires together.
#  There is no entry animation and no wrapper element — the swap is atomic.
# ════════════════════════════════════════════════════════
def _zoom_factor(value):
    """Zoom sliders are log scaled (-1..3 -> 0.5x..8x)."""
    try:
        return float(2 ** float(value))
    except (TypeError, ValueError):
        return 1.0


@app.callback(
    Output("nav-home","className"), Output("nav-em","className"), Output("nav-spectrum","className"),
    Output("nav-mtdi","className"), Output("nav-settings","className"),
    Input("url","pathname")
)
def update_nav(p):
    b = "nav-glass-btn"; a = "nav-glass-btn nav-active"
    return (a if p == "/" else b, a if p == "/em" else b, a if p == "/spectrum" else b,
            a if p == "/mtdi" else b, a if p == "/settings" else b)


PAGES = {
    "/": home_page,
    "/em": em_page,
    "/spectrum": spectrum_page,
    "/mtdi": mtdi_page,
    "/settings": settings_page,
}


@app.callback(Output("page-content","children"), Output("scroll-top-dummy","children"),
              Input("url","pathname"))
def display_page(pathname):
    # A changing token so the scroll-reset clientside fires exactly when this new
    # content lands. time.time() guarantees it differs on every swap, including
    # navigating to the page you are already on.
    sig = str(time.time())
    builder = PAGES.get(pathname, home_page)
    try:
        return builder(), sig
    except Exception as e:
        LOG.exception("Page build failed for %s", pathname)
        return html.Div(f"Page error: {e}", className="error-box", style=PAD), sig


# ── EM sub-tab switching ──
@app.callback(
    Output("em-subcontent","children"),
    Output("em-tab-mag","className"), Output("em-tab-elec","className"), Output("em-tab-both","className"),
    Input("em-tab-mag","n_clicks"), Input("em-tab-elec","n_clicks"), Input("em-tab-both","n_clicks"),
)
def em_switch(a, b, c):
    which = "mag"
    ctx = dash.callback_context
    if ctx.triggered:
        tid = ctx.triggered[0]["prop_id"].split(".")[0]
        which = {"em-tab-mag":"mag","em-tab-elec":"elec","em-tab-both":"both"}.get(tid, "mag")
    base = "tab-btn"; act = "tab-btn active"
    if which == "mag":  return magnetic_view(),  act, base, base
    if which == "elec": return electric_view(),  base, act, base
    return combined_view(), base, base, act


# ── header pills ──
@app.callback(Output("header-pills","children"), Input("header-interval","n_intervals"),
              Input("mobile-refresh-btn","n_clicks"))
def update_header(n, _refresh):
    with mag_lock:
        mv = magnetic_data["magnitude"]
        # Only a chip fault (or an outright error) makes the magnetometer pill unhealthy.
        # Running uncalibrated is normal and must not show as a warning.
        mfault = magnetic_data["error"] or magnetic_data["chip_warning"]
        mlast = magnetic_data["last_rx"]
    with efield_lock:
        ev = efield_data["field_v_m"]; eerr = efield_data["error"]
        elvl = efield_data["level"]; eclip = efield_data["clipped"]
        elast = efield_data["last_rx"]
    with mtdi_lock: ov = mtdi_data["active_health"]
    with spectrum_lock:
        rerr = spectrum_data["error"]; rpl = spectrum_data["peak_level"]
        rsane = spectrum_data["level_sane"]; rhave = spectrum_data["last_rx"] is not None
    cc = "pill-ok" if ov > 80 else "pill-warn" if ov > 50 else "pill-high"
    ec = "pill-off" if eerr else ("pill-high" if (eclip or elvl in ("HIGH","OVER")) else "pill-warn" if elvl == "MID" else "pill-ok")
    rc = "pill-off" if (rerr or not rhave) else ("pill-warn" if not rsane else "pill-ok")
    rv = f"{rpl:+.0f} unit" if (rhave and not rerr) else "—"
    mc = "pill-off" if (mfault or not mlast) else "pill-ok"
    # Labels are deliberately terse: the centre nav is absolutely positioned, so four
    # full-width pills collide with it on a 1280px laptop.
    return [
        html.Div([html.Span(className=f"pill-dot {mc}"), html.Span("CH 1"),   html.Span(f"{mv:.2f} unit" if mlast else "OFFLINE", className="pill-val")], className="status-pill pill-mag"),
        html.Div([html.Span(className=f"pill-dot {ec}"), html.Span("CH 2"), html.Span(f"{ev:.3f} unit" if elast else "OFFLINE", className="pill-val")], className="status-pill pill-ef"),
        html.Div([html.Span(className=f"pill-dot {rc}"), html.Span("CH 3"),    html.Span(rv,             className="pill-val")], className="status-pill pill-rf"),
        html.Div([html.Span(className=f"pill-dot {cc}"), html.Span("MTDI"),  html.Span(f"{ov:.0f}%",   className="pill-val")], className="status-pill pill-mtdi"),
    ]


# ── alerts (every channel, from the one alert engine in analysis.py) ──
# This used to compare the magnetometer magnitude against a fixed 80 unit / 3 unit pair,
# which is neither smart nor general: it ignored the other three channels entirely,
# and in a ~30 unit ambient it fired on rotating the instrument while missing genuine
# changes. It now reports whatever AnalysisEngine has already judged significant.
@app.callback(Output("nvtra-alert-trigger","children"), Output("nvtra-prev-state","data"),
              Input("nvtra-interval","n_intervals"), Input("mobile-refresh-btn","n_clicks"),
              State("nvtra-prev-state","data"),
              prevent_initial_call=True)
def nvtra_alerts(n, _refresh, prev):
    from .analysis import ALERT_SUMMON
    rt = _d4_runtime()
    engine = getattr(rt, "engine", None) if rt is not None else None
    seen = (prev or {}).get("seen", 0)
    if engine is None:
        return "", {"seen": seen}
    rows = [e for e in list(engine.events)
            if e.get("severity") in ALERT_SUMMON and float(e.get("timestamp") or 0) > seen]
    if not rows:
        return dash.no_update, dash.no_update
    latest = rows[-1]
    return (f"{latest['message'].upper()}|{int(time.time()*1000)}",
            {"seen": float(latest["timestamp"])})


# ── magnetic: numbers (update text in place, no layout shift) ──
@app.callback(
    Output("mv-baseline","children"),
    Output("mv-sig","children"), Output("mv-sig","className"),
    Output("mag-status","children"), Output("mag-status","className"), Output("mag-dot","className"),
    Output("mag-recal-status","children"),
    Output("sum-mag","children"), Output("sum-axes","children"), Output("mag-error","children"),
    Input("mag-num-int","n_intervals"), Input("mobile-refresh-btn","n_clicks")
)
def update_numbers(n, _refresh):
    with mag_lock:
        m = dict(magnetic_data); h10 = list(magnetic_data["history"])[-10:]
    if len(h10) >= 2:
        mean = sum(h10)/len(h10); std = (sum((v-mean)**2 for v in h10)/len(h10))**0.5
        sig = f"{std:.2f} unit"; sc = GREEN if std < 0.5 else AMBER if std < 2.0 else RED
    else:
        sig = "—"; sc = SUBTEXT
    online = m["error"] is None and m["last_rx"] is not None
    # A missing calibration profile is the normal default: the sensor is fully online
    # and the readings are real, they are simply uncorrected. It is reported as a
    # neutral note, never as a fault — only a chip-ID mismatch turns the strip amber.
    if online:
        age = time.time() - m["last_rx"]
        calibration_label = "CALIBRATED" if m["calibrated"] else "UNCALIBRATED (RAW VECTOR)"
        status = f"SOURCE ONLINE · Source 1 @ 0x2C · {calibration_label} · {age:.1f}s ago"
        if m["chip_warning"]:
            status = f"SOURCE ONLINE · {m['chip_warning']} · {age:.1f}s ago"
            stcol = AMBER; dot = "online-dot warn"
        else:
            stcol = GREEN; dot = "online-dot on"
    else:
        status = f"SOURCE OFFLINE · {(m['error'] or 'waiting')[:56]}"
        stcol = RED; dot = "online-dot off"
    # Only real faults get the red banner. "uncalibrated" is stated in the status strip
    # above and does not need an error box under the page.
    problem = m["error"] or m["chip_warning"]
    err = (
        html.Div(f"STATUS: {problem}", className="error-box", style={"marginTop":"16px"})
        if problem else None
    )
    value = (lambda number: f"{number:.2f}" if m["last_rx"] is not None else "—")
    baseline_value = f"{m['baseline_magnitude']:.2f}" if m["baseline_calibrated"] else "—"
    delta_value = f"{m['baseline_delta']:.2f}" if m["baseline_calibrated"] else "—"
    baseline_status = (
        f"Quiet vector learned: {m['baseline_magnitude']:.2f} unit; live change is {m['baseline_delta']:.2f} unit."
        if m["baseline_calibrated"] else
        'Learning the quiet channel 1 baseline… keep the instrument still and clear of devices (~5 s).'
    )
    summary_mag = f"{m['magnitude']:.2f} unit" if m["last_rx"] is not None else "—"
    summary_axes = (
        (
            f"CORRECTED X {m['x']:.2f}  Y {m['y']:.2f}  Z {m['z']:.2f} · "
            f"RAW X {m['raw_x']:.2f}  Y {m['raw_y']:.2f}  Z {m['raw_z']:.2f}"
        )
        if m["last_rx"] is not None else "—"
    )
    return (baseline_value, sig,
            f"metric-value {_cls(sc)}",
            status, f"online-text {_cls(stcol)}", dot,
            baseline_status,
            summary_mag, summary_axes, err)


# ── magnetic: Environmental Intelligence baseline button ──
@app.callback(Output("mag-recal-request", "data"),
              Input("mag-recal-btn", "n_clicks"), prevent_initial_call=True)
def magnetometer_recalibrate(n):
    with mag_lock:
        if magnetic_data["last_rx"] is None or magnetic_data["error"]:
            return {"queued":False, "reason":"offline", "t":time.time()}
    with mag_cmd_lock:
        mag_cmd["recalibrate"] = True
    return {"queued":True, "t":time.time()}


# ── magnetic: 2D charts (figure-only, uirevision keeps the view stable) ──
@app.callback(
    Output("g-line","figure"), Output("g-axis","figure"), Output("g-pie","figure"),
    Output("g-gauge","figure"), Output("g-bar","figure"),
    Output("g-scatter","figure"), Output("g-delta","figure"),
    Input("mag-chart-int","n_intervals"), Input("mag-zoom","value"),
    Input("mobile-refresh-btn","n_clicks")
)
def update_charts(n, zoom, _refresh):
    zoom = _zoom_factor(zoom)
    with mag_lock:
        m = dict(magnetic_data); hist = list(magnetic_data["history"]); xyz = list(magnetic_data["xyz_history"])
    if hist:
        mn = min(hist); mx = max(hist); avg = sum(hist)/len(hist)
    else:
        mn = avg = mx = None
    have = bool(hist)
    return (make_line_chart(hist, color=CYAN, fill_color="rgba(0,229,255,0.07)",
                            height=250, ylabel="unit", smart_scale=True, zoom=zoom,
                            revision="mag-line"),
            fig_axis(xyz), fig_pie(m['x'], m['y'], m['z']) if have else fig_pie(None, None, None),
            fig_gauge(m['magnitude'] if have else None), fig_bar(mn, avg, mx),
            fig_2d_scatter(xyz), fig_2d_delta(xyz))


# ── electric: triaxial numbers and 2D charts ──
@app.callback(
    Output("e3-x","children"), Output("e3-y","children"), Output("e3-z","children"),
    Output("e3-mag","children"), Output("e3-live","children"), Output("e3-live","className"),
    Output("e3-x-vm","children"), Output("e3-y-vm","children"),
    Output("e3-z-vm","children"), Output("e3-mag-vm","children"),
    Output("e3-static-x","children"), Output("e3-static-y","children"),
    Output("e3-static-z","children"), Output("e3-static-mag","children"),
    Output("e3-line","figure"), Output("e3-axis","figure"),
    Output("e3-scatter","figure"), Output("e3-delta","figure"),
    Output("e3-gauge","figure"), Output("e3-pie","figure"),
    Output("e3-bar","figure"), Output("e3-archive","figure"),
    Input("e3-int","n_intervals"), Input("mobile-refresh-btn","n_clicks")
)
def update_efield_triaxial(n, _refresh):
    with efield_lock:
        e = dict(efield_data)
        xyz = list(efield_data.get("exyz_history") or [])
        emag = list(efield_data.get("emag_history") or [])
    live = e.get("axes_live", 0)
    axis_unit = "ADC counts RMS" if e.get("data_source") == "ARDUINO_UNO_USB" else "mV RMS"
    # An axis that is not reporting shows an em dash. Rendering 0.00 would be a
    # fabricated measurement -- indistinguishable on screen from a working plate
    # in a null field -- which is the whole reason acquisition passes None up.
    shown = lambda v: "—" if v is None else "%.3f" % v
    clipped_axes = e.get("axis_clipped") or {}
    estimated = lambda axis, value: (("≥ " if clipped_axes.get(axis) else "") + shown(value))
    colour = GREEN if live == 3 else AMBER if live else RED
    return (shown(e.get("ex_mv")), shown(e.get("ey_mv")), shown(e.get("ez_mv")),
            shown(e.get("e_magnitude_mv")), "%d / 3" % live,
            "metric-value " + _cls(colour),
            estimated("x", e.get("ex_v_m")), estimated("y", e.get("ey_v_m")),
            estimated("z", e.get("ez_v_m")), ("≥ " if e.get("clipped") else "") + shown(e.get("e_magnitude_v_m")),
            shown((e.get("dc_delta_counts") or {}).get("x")), shown((e.get("dc_delta_counts") or {}).get("y")),
            shown((e.get("dc_delta_counts") or {}).get("z")), shown(e.get("static_activity_counts")),
            make_line_chart(emag, color=AMBER, fill_color="rgba(255,171,64,0.08)",
                            height=250, ylabel=axis_unit),
            fig_axis(xyz, unit=axis_unit),
            fig_2d_scatter(xyz, unit=axis_unit),
            fig_2d_delta(xyz, unit=axis_unit),
            fig_gauge(e.get("e_magnitude_mv"), unit=axis_unit),
            fig_pie(e.get("ex_mv"), e.get("ey_mv"), e.get("ez_mv")),
            fig_bar(*_e3_stats(emag), unit=axis_unit, quantity='channel 2 activity magnitude'),
            fig_archive(series=emag, unit=axis_unit))


# ── electric: triaxial 3D views, slower because they are expensive ──
@app.callback(
    Output("e3-surface","figure"), Output("e3-terrain","figure"),
    Output("e3-plane","figure"), Output("e3-dipole","figure"),
    Input("e3-3d-int","n_intervals"), Input("mobile-refresh-btn","n_clicks")
)
def update_efield_triaxial_3d(n, _refresh):
    with efield_lock:
        xyz = list(efield_data.get("exyz_history") or [])
        axis_unit = "ADC counts RMS" if efield_data.get("data_source") == "ARDUINO_UNO_USB" else "mV RMS"
    state = _direction_plot_state(xyz)
    return (fig_3d_surface(xyz, height=400, unit=axis_unit),
            fig_3d_terrain(xyz, height=400, unit=axis_unit),
            fig_3d_error_plane(xyz, height=430, direction_state=state),
            fig_3d_dipole_field(xyz, height=430, direction_state=state))


# ── magnetic: heavier 3D surfaces update slowly ──
@app.callback(
    Output("g3d-surface","figure"), Output("g3d-terrain","figure"),
    Input("mag-3d-int","n_intervals"), Input("mobile-refresh-btn","n_clicks")
)
def update_3d_surfaces(n, _refresh):
    with mag_lock:
        xyz = list(magnetic_data["xyz_history"])
    return (fig_3d_surface(xyz, height=400),
            fig_3d_terrain(xyz, height=400))


# ── magnetic: lightweight direction and dipole views update more frequently ──
@app.callback(
    Output("g3d-plane","figure"), Output("g3d-dipole","figure"),
    Output("mag3d-error","children"),
    Input("mag-dir-int","n_intervals"), Input("mobile-refresh-btn","n_clicks")
)
def update_3d_direction(n, _refresh):
    with mag_lock:
        xyz = list(magnetic_data["xyz_history"]); err = magnetic_data["error"]
    state = _direction_plot_state(xyz)
    e = html.Div(f"STATUS: {err}", className="error-box", style={"marginTop":"12px"}) if err else None
    return (fig_3d_error_plane(xyz, height=460, direction_state=state),
            fig_3d_dipole_field(xyz, height=460, direction_state=state),
            e)


# ── magnetic: signal archive ──
@app.callback(
    Output("g-archive","figure"), Output("arch-count","children"), Output("arch-min","children"),
    Output("arch-avg","children"), Output("arch-max","children"),
    Input("mag-arch-int","n_intervals"), Input("mobile-refresh-btn","n_clicks")
)
def update_arch(n, _refresh):
    with archive_lock:
        cnt = session_stats["count"]; mn = session_stats["min"]; mx = session_stats["max"]; sm = session_stats["sum"]
    avg = sm/cnt if cnt else 0.0
    mn = 0.0 if mn == float("inf") else mn
    return (fig_archive(), str(cnt),
            (f"{mn:.2f}" if cnt else "—"), (f"{avg:.2f}" if cnt else "—"), (f"{mx:.2f}" if cnt else "—"))


# ── electric: numbers (scalar RMS + auto-range state) ──
@app.callback(
    Output("ev-level","children"), Output("ev-level","className"),
    Output("ev-index","children"), Output("ev-rms","children"),
    Output("ev-gain","children"),
    Output("ef-status","children"), Output("ef-status","className"), Output("ef-dot","className"),
    Output("ef-warn","children"),
    Output("ev-baseline","children"),
    Output("ev-util","children"), Output("ev-minmax","children"), Output("ev-statustext","children"),
    Output("ev-base-top","children"), Output("ev-delta-top","children"),
    Output("ef-error","children"),
    Input("ef-num-int","n_intervals"), Input("mobile-refresh-btn","n_clicks")
)
def update_efield_numbers(n, _refresh):
    with efield_lock: e = dict(efield_data)
    have = e["last_rx"] is not None
    provisional = e.get("data_source") == "ARDUINO_UNO_USB"
    lc = _ef_level_color(e["level"])
    if e["error"] and not (e["last_rx"] is None and e["error"] == "Waiting for E-field sensor"):
        st = f"CHANNEL 2 OFFLINE · {e['error'][:64]}"; sc = RED; dot = "online-dot off"
    elif e["error"]:
        st = 'CHANNEL 2 WAITING · connect the Uno USB ADC'; sc = AMBER; dot = "online-dot warn"
    elif provisional:
        age = time.time() - e["last_rx"] if e["last_rx"] else 0.0
        st = f"CHANNEL 2 ONLINE · SOURCE 6 UNO USB · {e['sample_rate']:.1f} SPS · {age:.1f}s ago"
        sc = GREEN; dot = "online-dot on"
        warn = None
        clipped_axes = e.get("axis_clipped") or {}
        shown = lambda key, axis: (("≥ " if clipped_axes.get(axis) else "") + f"{e.get(key):.3f}") if have and e.get(key) is not None else "—"
        return (shown("ex_v_m", "x"), f"metric-value {_cls(lc)}",
                shown("ey_v_m", "y"), shown("ez_v_m", "z"),
                (("≥ " if e.get("clipped") else "") + f"{e.get('e_magnitude_v_m'):.3f}") if have and e.get("e_magnitude_v_m") is not None else "—",
                st, f"online-text {_cls(sc)}", dot, warn, "—", "—",
                f"{e['min_code']} / {e['max_code']}" if have else "—", e["status"],
                f"{e.get('baseline_v_m', 0.0):.3f}" if have else "—",
                f"{abs(e.get('e_magnitude_v_m') or 0.0):.3f}" if have else "—", None)
    elif not e["calibrated"]:
        st = 'CALIBRATING BASELINE · keep the source clear of devices…'; sc = AMBER; dot = "online-dot warn"
    elif e["clipped"]:
        st = ("UNO INPUT CLIPPED — RAW ACTIVITY IS A LOWER BOUND" if provisional
              else "SIGNAL TOO STRONG — MOVE PROBE AWAY"); sc = RED; dot = "online-dot off"
    else:
        age = time.time() - e["last_rx"]
        # Name the input actually in use. This used to be hardcoded to
        # "diff A0-A1", which stopped being true the moment the probe was
        # rewired single-ended, and a status line that states the wrong input
        # is worse than one that states none.
        #
        # acquisition is NOT one of the modules in _shared.ORDER, so its names
        # are not injected here and must be imported. Referencing them bare
        # raised NameError on every render once the probe came online -- caught
        # only because the page stopped loading, since the self-test does not
        # reach this branch. The import is local so a failure degrades the one
        # status string rather than the page.
        try:
            from studio.acquisition import EFIELD_MUX, EFIELD_MUX_NAME
            wiring = EFIELD_MUX_NAME.get(EFIELD_MUX, f"input {EFIELD_MUX}")
        except Exception:
            wiring = "probe input"
        st = f"CHANNEL 2 ONLINE · Source 2 {wiring} @ 0x48 · {age:.1f}s ago"; sc = GREEN; dot = "online-dot on"
    warning_text = (
        "SIGNAL ABOVE ADC RANGE — live value is streaming, but is only a lower bound while clipped"
        if e["clipped"] and e["calibrated"] else e["warning"]
    )
    warn = (
        html.Div(f"⚠  {warning_text}", className="error-box", style={"marginBottom":"16px"})
        if warning_text else None
    )
    err = html.Div(f"STATUS: {e['error']}", className="error-box", style={"marginTop":"16px"}) if e["error"] else None
    base = f"{e['baseline_v_m']:.3f}" if e["calibrated"] else "—"
    field_text = (("≥ " if e["clipped"] else "") + f"{e['field_v_m']:.3f}") if have else "—"
    peak_text = (("≥ " if e["clipped"] else "") + f"{e['peak_v_m']:.3f}") if have else "—"
    return (shown("ex_v_m", "x"), f"metric-value {_cls(lc)}",
            shown("ey_v_m", "y"), shown("ez_v_m", "z"),
            (("≥ " if e.get("clipped") else "") + f"{e.get('e_magnitude_v_m'):.3f}") if have and e.get("e_magnitude_v_m") is not None else "—",
            st, f"online-text {_cls(sc)}", dot,
            warn,
            base,
            f"{e['utilisation']:.0f}%" if have and e["utilisation"] is not None else "—",
            f"{e['min_code']} / {e['max_code']}" if have else "—",
            e["status"],
            f"{e.get('baseline_v_m', 0.0):.3f}" if have else "—",
            f"{abs(e.get('field_v_m') or 0.0):.3f}" if have else "—", err)


# ── electric: live charts (RMS line, index line, gauge, bars, bullet) ──
@app.callback(
    Output("ef-line","figure"), Output("ef-index-line","figure"),
    Output("ef-gauge","figure"), Output("ef-basebar","figure"), Output("ef-bullet","figure"),
    Output("ef-b-correlation","figure"), Output("ef-induction-proxy","figure"),
    Input("ef-chart-int","n_intervals"), Input("ef-zoom","value"), Input("mobile-refresh-btn","n_clicks")
)
def update_efield_charts(n, zoom, _refresh):
    zoom = _zoom_factor(zoom)
    with efield_lock:
        e = dict(efield_data); hist = list(efield_data["history"]); rel_hist = list(efield_data["rel_history"])
    with mag_lock:
        mag_hist = list(magnetic_data["history"])
    have = e["last_rx"] is not None
    provisional = e.get("data_source") == "ARDUINO_UNO_USB"
    return (make_line_chart(hist, color=AMBER, fill_color="rgba(255,171,64,0.08)", height=250,
                            ylabel="ADC counts RMS" if provisional else "mV RMS",
                            smart_scale=True, zoom=zoom or 1, revision="ef-line"),
            make_line_chart(rel_hist, color=CYAN, fill_color="rgba(0,229,255,0.07)", height=250, ylabel="%"),
            fig_ef_gauge(e["rel_index"] if have else None),
            (fig_ef_basebar(None, None, None) if provisional else
             fig_ef_basebar(e["baseline_v_m"], e["field_v_m"], e["peak_v_m"])) if have else fig_ef_basebar(None, None, None),
            fig_ef_bullet(e["rel_index"] if have else None, e["level"]),
            fig_ef_b_correlation(mag_hist, rel_hist),
            fig_ef_induction_proxy(mag_hist, rel_hist))


@app.callback(
    Output("em-overlay", "figure"), Output("em-normalized-overlay", "figure"),
    Output("em-coupling", "figure"), Output("em-correlation", "figure"),
    Output("em-traj3d", "figure"), Output("em-b-plane", "figure"), Output("em-e-plane", "figure"),
    Output("em-b-dipole", "figure"), Output("em-e-dipole", "figure"),
    Output("em3-line", "figure"), Output("em3-axis", "figure"), Output("em3-scatter", "figure"),
    Output("em3-delta", "figure"), Output("em3-gauge", "figure"), Output("em3-pie", "figure"),
    Output("em3-bar", "figure"), Output("em3-surface", "figure"), Output("em3-terrain", "figure"),
    Output("em3-plane", "figure"), Output("em3-dipole", "figure"),
    Output("em3-vector-overlay", "figure"), Output("em3-cross-proxy", "figure"),
    Input("em-overlay-int", "n_intervals"), Input("em-zoom", "value"), Input("mobile-refresh-btn","n_clicks"),
)
def update_em_overlays(n, zoom, _refresh):
    zoom = _zoom_factor(zoom)
    window = max(12, int(200 / max(0.5, zoom)))
    with mag_lock:
        mag_hist = list(magnetic_data["history"])[-window:]
        mag_xyz = list(magnetic_data["xyz_history"])[-window:]
    with efield_lock:
        ef_hist = list(efield_data["history"])[-window:]
        ef_rel = list(efield_data["rel_history"])[-window:]
        ef_xyz = list(efield_data.get("exyz_history") or [])[-window:]
    em_xyz = _em_composite_xyz(mag_xyz, ef_xyz, window)
    em_mag = [math.sqrt(x*x + y*y + z*z) for x, y, z in em_xyz]
    figures = (
        fig_em_overlay(mag_hist, ef_hist),
        fig_em_normalized_overlay(mag_hist, ef_rel),
        fig_ef_induction_proxy(mag_hist, ef_rel, height=300),
        fig_ef_b_correlation(mag_hist, ef_rel, height=300),
        fig_em_trajectory_3d(mag_hist, ef_rel),
        fig_3d_error_plane(mag_xyz, height=430), fig_3d_error_plane(ef_xyz, height=430),
        fig_3d_dipole_field(mag_xyz, height=430), fig_3d_dipole_field(ef_xyz, height=430),
        make_line_chart(em_mag, color=CYAN, height=250, ylabel="normalized"), fig_axis(em_xyz, unit="normalized"),
        fig_2d_scatter(em_xyz, unit="normalized"), fig_2d_delta(em_xyz, unit="normalized"), fig_gauge(em_mag[-1] if em_mag else None, unit="normalized"),
        fig_pie(*(em_xyz[-1] if em_xyz else (None, None, None))),
        fig_bar(*_e3_stats(em_mag), unit="normalized", quantity="E+B composite magnitude"),
        fig_3d_surface(em_xyz, height=400, unit="normalized"), fig_3d_terrain(em_xyz, height=400, unit="normalized"),
        fig_3d_error_plane(em_xyz, height=430), fig_3d_dipole_field(em_xyz, height=430),
        fig_em_vector_overlay_3d(mag_xyz, ef_xyz), fig_em_cross_proxy_3d(mag_xyz, ef_xyz),
    )
    # A stable uirevision normally preserves a user's 3D camera. For this explicit
    # window control it also preserved the old axis range, making the zoom appear
    # inert. Key the revision to the selected window so every graph visibly updates.
    for index, figure in enumerate(figures):
        figure.update_layout(uirevision=f"em-window-{zoom:.3f}-{index}")
    return figures


# ── electric: Environmental Intelligence baseline button ──
@app.callback(Output("ef-recal-status","children"),
              Input("ef-recal-btn","n_clicks"), prevent_initial_call=True)
def efield_recalibrate(n):
    with efield_lock:
        if efield_data["last_rx"] is None or efield_data["error"]:
            return "E-field sensor is offline; baseline request was not queued."
    with efield_cmd_lock:
        efield_cmd["recalibrate"] = True
    return "Re-learning the environmental baseline… keep the probe fixed and clear for ~10 s."


# ── spectrum: numbers, device strip, link status ──
@app.callback(
    Output("rf-peak-f","children"), Output("rf-peak-l","children"), Output("rf-floor","children"),
    Output("rf-floor","className"), Output("rf-span","children"), Output("rf-res","children"),
    Output("rf-sweep","children"),
    Output("rf-status","children"), Output("rf-status","className"), Output("rf-dot","className"),
    Output("rf-warn","children"), Output("rf-dev-strip","children"),
    Output("rf-peak-body","children"), Output("rf-emi-body","children"),
    Output("rf-arch-count","children"), Output("rf-arch-min","children"),
    Output("rf-arch-avg","children"), Output("rf-arch-max","children"), Output("rf-arch-str","children"),
    Output("rf-error","children"),
    Input("rf-num-int","n_intervals"), Input("mobile-refresh-btn","n_clicks")
)
def update_spectrum_numbers(n, _refresh):
    with spectrum_lock:
        s = dict(spectrum_data); peaks = list(spectrum_data["peaks"])
    with rf_archive_lock:
        cnt = rf_stats["count"]; mn = rf_stats["min"]; mx = rf_stats["max"]
        sm = rf_stats["sum"]; strongest = dict(rf_stats["strongest"])

    if s["error"]:
        st = f"CHANNEL 3 OFFLINE · {s['error'][:64]}"; sc = RED; dot = "online-dot off"
    elif "paused" in s["status"].lower():
        st = 'CHANNEL 3 PAUSED · last valid sweep retained'; sc = AMBER; dot = "online-dot warn"
    elif s["last_rx"] is None:
        st = 'SOURCE 3 CONNECTED · waiting for the first sweep…'; sc = AMBER; dot = "online-dot warn"
    else:
        age = time.time() - s["last_rx"]
        st = f"CHANNEL 3 ONLINE · {s['device']} · sweep {s['sweep_s']:.1f}s · {age:.1f}s ago"
        sc = GREEN; dot = "online-dot on"

    # Suspicious values are shown but never diagnosed or treated as trusted.
    warn = None
    if s["last_rx"] is not None and not s["level_sane"]:
        warn = html.Div([
            'TEXT  ', s["level_note"],
            html.Br(),
            'Paragraph. Enter your text here.',
        ], className="error-box", style={"marginBottom":"16px"})

    err = (html.Div(f"STATUS: {s['error']}", className="error-box", style={"marginTop":"16px"})
           if s["error"] else None)

    have = s["last_rx"] is not None and s["levels"]
    pf = _freq_label(s["peak_freq"]) if have else "—"
    pl = f"{s['peak_level']:+.1f} unit" if have else "—"
    fl = f"{s['floor']:+.1f} unit" if have else "—"
    flc = WHITE if s["level_sane"] else RED
    span = _span_label(s["span_start"], s["span_stop"])
    if have and len(s["freqs"]) > 1:
        step = (s["freqs"][-1] - s["freqs"][0]) / (len(s["freqs"]) - 1)
        res = f"{_freq_label(step)}/pt"
    else:
        res = "—"
    sweep = f"{s['sweep_s']:.1f} s" if have else "—"

    avg = sm / cnt if cnt else 0.0
    mn_s = f"{mn:+.1f}" if cnt else "—"
    mx_s = f"{mx:+.1f}" if cnt else "—"
    avg_s = f"{avg:+.1f}" if cnt else "—"
    str_s = (f"{strongest['level']:+.1f} unit @ {_freq_label(strongest['freq'])}" if cnt else "—")

    return (pf, pl, fl, f"metric-value {_cls(flc)}", span, res, sweep,
            st, f"online-text {_cls(sc)}", dot, warn, _rf_dev_strip(),
            _peak_rows(peaks, s["floor"]), emi_rows(s),
            str(cnt), mn_s, avg_s, mx_s, str_s, err)


# ── spectrum: sweep + breakdown charts ──
@app.callback(
    Output("rf-sweep-graph","figure"), Output("rf-bands-graph","figure"), Output("rf-trend-graph","figure"),
    Input("rf-chart-int","n_intervals"), Input("rf-axis-mode","data"), Input("rf-bands-mode","data"),
    Input("mobile-refresh-btn","n_clicks")
)
def update_spectrum_charts(n, axis_mode, show_bands, _refresh):
    with spectrum_lock:
        s = dict(spectrum_data)
    return (fig_spectrum(s["freqs"], s["levels"], s["maxhold"], s["peaks"], s["floor"],
                         logx=(axis_mode == "log"), height=380, bands=bool(show_bands)),
            fig_rf_bands(s["peaks"]),
            fig_rf_trend(s["peak_history"]))


# ── spectrum: waterfall (heaviest figure — slowest interval) ──
@app.callback(Output("rf-waterfall-graph","figure"), Output("rf-terrain-graph","figure"),
              Input("rf-wf-int","n_intervals"), Input("mobile-refresh-btn","n_clicks"))
def update_waterfall(n, _refresh):
    with spectrum_lock:
        rows = list(spectrum_data["waterfall"])
        times = list(spectrum_data["waterfall_times"])
        freqs = list(spectrum_data["freqs"])
    rows, times = _waterfall_rows(rows, times, freqs)
    return fig_waterfall(rows, freqs, times, 320), fig_rf_terrain(rows, freqs, times, 460)


# ── spectrum: range presets ──
@app.callback(
    Output("rf-preset-mode","data"),
    *[Output(f"rf-preset-{key}","className") for key, _l, _a, _b in TSA_PRESETS],
    *[Input(f"rf-preset-{key}","n_clicks") for key, _l, _a, _b in TSA_PRESETS],
)
def rf_pick_preset(*clicks):
    chosen = "full"
    ctx = dash.callback_context
    if ctx.triggered:
        tid = ctx.triggered[0]["prop_id"].split(".")[0]
        if tid.startswith("rf-preset-"):
            key = tid[len("rf-preset-"):]
            match = next((p for p in TSA_PRESETS if p[0] == key), None)
            if match:
                chosen = key
                with tinysa_cmd_lock:
                    tinysa_cmd["range"] = (match[2], match[3])
                    tinysa_cmd["preset"] = key
    return (chosen, *["rf-btn rf-on" if k == chosen else "rf-btn" for k, _l, _a, _b in TSA_PRESETS])


# ── spectrum: sweep resolution ──
@app.callback(
    Output("rf-points-mode","data"),
    Output("rf-pts-101","className"), Output("rf-pts-251","className"), Output("rf-pts-290","className"),
    Input("rf-pts-101","n_clicks"), Input("rf-pts-251","n_clicks"), Input("rf-pts-290","n_clicks"),
)
def rf_pick_points(a, b, c):
    pts = TSA_DEFAULT_PTS
    ctx = dash.callback_context
    if ctx.triggered:
        tid = ctx.triggered[0]["prop_id"].split(".")[0]
        pts = {"rf-pts-101":101, "rf-pts-251":251, "rf-pts-290":290}.get(tid, TSA_DEFAULT_PTS)
        with tinysa_cmd_lock:
            tinysa_cmd["points"] = pts
    return (pts, *["rf-btn rf-on" if pts == v else "rf-btn" for v in (101, 251, 290)])


# ── spectrum: frequency axis scale (client-side view choice, no device traffic) ──
@app.callback(
    Output("rf-axis-mode","data"), Output("rf-ax-lin","className"), Output("rf-ax-log","className"),
    Input("rf-ax-lin","n_clicks"), Input("rf-ax-log","n_clicks"),
)
def rf_pick_axis(a, b):
    mode = "lin"
    ctx = dash.callback_context
    if ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] == "rf-ax-log":
        mode = "log"
    return (mode, "rf-btn" if mode == "log" else "rf-btn rf-on",
                  "rf-btn rf-on" if mode == "log" else "rf-btn")


# ── spectrum: clear the max-hold trace ──
@app.callback(Output("rf-hold-reset","className"),
              Input("rf-hold-reset","n_clicks"), prevent_initial_call=True)
def rf_reset_hold(n):
    with tinysa_cmd_lock:
        tinysa_cmd["reset_hold"] = True
    return "rf-btn"


@app.callback(
    Output("rf-pause","children"), Output("rf-pause","className"),
    Input("rf-pause","n_clicks"), prevent_initial_call=True
)
def rf_toggle_pause(_n):
    with tinysa_cmd_lock:
        tinysa_cmd["paused"] = not tinysa_cmd["paused"]
        paused = tinysa_cmd["paused"]
    return ("RESUME" if paused else "PAUSE", "rf-btn rf-on" if paused else "rf-btn")


@app.callback(
    Output("rf-custom-status","children"),
    Input("rf-custom-apply","n_clicks"),
    State("rf-custom-start","value"), State("rf-custom-stop","value"),
    prevent_initial_call=True,
)
def rf_custom_range(_n, start_mhz, stop_mhz):
    try:
        start = float(start_mhz)
        stop = float(stop_mhz)
        if not math.isfinite(start) or not math.isfinite(stop):
            raise ValueError("values must be finite")
        if start < 0.1 or stop > 6000.0 or stop <= start:
            raise ValueError("require 0.1 <= start < stop <= 6000 MHz")
        start_hz = int(round(start * 1_000_000))
        stop_hz = int(round(stop * 1_000_000))
        with tinysa_cmd_lock:
            tinysa_cmd["range"] = (start_hz, stop_hz)
            tinysa_cmd["preset"] = "custom"
        return f"Queued exact range {_freq_label(start_hz)} – {_freq_label(stop_hz)}"
    except (TypeError, ValueError) as exc:
        return f"REJECTED · {exc}"


@app.callback(
    Output("rf-sweep-top-note", "children"),
    Input("rf-sweep-now", "n_clicks"),
    prevent_initial_call=True,
)
def rf_sweep_now(_n):
    with tinysa_cmd_lock:
        tinysa_cmd["paused"] = False
        tinysa_cmd["reset_hold"] = True
    return "On-demand sweep requested now"


# ── spectrum: band shading toggle ──
@app.callback(
    Output("rf-bands-mode","data"), Output("rf-band-on","className"), Output("rf-band-off","className"),
    Input("rf-band-on","n_clicks"), Input("rf-band-off","n_clicks"),
)
def rf_pick_bands(a, b):
    on = True
    ctx = dash.callback_context
    if ctx.triggered and ctx.triggered[0]["prop_id"].split(".")[0] == "rf-band-off":
        on = False
    return (on, "rf-btn rf-on" if on else "rf-btn", "rf-btn" if on else "rf-btn rf-on")


# ── spectrum page: RF / WiFi / Bluetooth tab switching ──
@app.callback(
    Output("sp-subcontent","children"),
    Output("sp-tab-rf","className"), Output("sp-tab-sdr","className"),
    Output("sp-tab-wifi","className"), Output("sp-tab-bt","className"),
    Input("sp-tab-rf","n_clicks"), Input("sp-tab-sdr","n_clicks"),
    Input("sp-tab-wifi","n_clicks"), Input("sp-tab-bt","n_clicks"),
)
def sp_switch(a, sdr, b, c):
    which = "rf"
    ctx = dash.callback_context
    if ctx.triggered:
        tid = ctx.triggered[0]["prop_id"].split(".")[0]
        which = {"sp-tab-rf":"rf", "sp-tab-sdr":"sdr",
                 "sp-tab-wifi":"wifi", "sp-tab-bt":"bt"}.get(tid, "rf")
    base = "tab-btn"; act = "tab-btn active"
    if which == "sdr":  return sdr_view(),       base, act,  base, base
    if which == "wifi": return wifi_view(),      base, base, act,  base
    if which == "bt":   return bluetooth_view(), base, base, base, act
    return rf_sweep_view(), act, base, base, base


# ── WiFi survey + LAN neighbours ──
@app.callback(
    Output("wf-count","children"), Output("wf-strong","children"), Output("wf-open","children"),
    Output("wf-iface","children"), Output("wf-status","children"), Output("wf-status","className"),
    Output("wf-dot","className"), Output("wf-body","children"), Output("wf-error","children"),
    Output("lan-ip","children"), Output("lan-gw","children"), Output("lan-ssid","children"),
    Output("lan-n","children"), Output("lan-body","children"), Output("lan-error","children"),
    Output("wf-chan-24","figure"), Output("wf-chan-5","figure"), Output("wf-bars","figure"),
    Input("wf-int","n_intervals"), Input("mobile-refresh-btn","n_clicks")
)
def update_wifi(n, _refresh):
    with wifi_lock: w = dict(wifi_data); nets = list(wifi_data["networks"])
    with lan_lock:  l = dict(lan_data);  hosts = list(lan_data["hosts"])
    if w.get("scanning") and nets:
        elapsed = time.time() - (w.get("scan_started") or time.time())
        st = f"CHANNEL 5 SCANNING · {elapsed:.0f}s · showing the previous sweep ({len(nets)} networks) until this one completes"
        sc = AMBER; dot = "online-dot warn"
    elif w["error"]:
        # A failed rescan keeps the previous list on screen rather than blanking it, so
        # say plainly that it is no longer current — a stale list that looks live is
        # exactly the kind of quiet dishonesty this dashboard avoids.
        stale = " · list below is the last successful scan" if nets else ""
        st = f"CHANNEL 5 SCAN UNAVAILABLE · {w['error'][:64]}{stale}"; sc = RED; dot = "online-dot off"
    elif w["last_rx"] is None:
        st = f"CHANNEL 5 DISCOVERY WAITING · {w['scan_mode']}"; sc = AMBER; dot = "online-dot warn"
    else:
        age = time.time() - w["last_rx"]
        st = (f"WIFI DISCOVERY · {len(nets)} networks · {w['backend']} on {w['iface']} "
              f"· {w['scan_mode']} · {age:.0f}s ago")
        sc = GREEN; dot = "online-dot on"
    strongest = nets[0]["ssid"] if nets else "—"
    n_open = sum(1 for x in nets if not x["sec"] or x["sec"] == "OPEN")
    werr = (html.Div(f"STATUS: {w['error']}", className="error-box", style={"marginTop":"14px"})
            if w["error"] else None)
    lerr = (html.Div(f"STATUS: {l['error']}", className="error-box", style={"marginTop":"14px"})
            if l["error"] else None)
    return (str(len(nets)), strongest, str(n_open), w["iface"],
            st, f"online-text {_cls(sc)}", dot, _wifi_rows(nets), werr,
            l["self_ip"], l["gateway"], l["ssid"], str(len(hosts)),
            _lan_rows(hosts, l["self_ip"]), lerr,
            fig_wifi_channels(nets, "2.4 GHz"), fig_wifi_channels(nets, "5 GHz"),
            fig_wifi_signal_bars(nets))


# ── Bluetooth advertising scan ──
@app.callback(
    Output("bt-count","children"), Output("bt-closest","children"), Output("bt-named","children"),
    Output("bt-adapter","children"), Output("bt-status","children"), Output("bt-status","className"),
    Output("bt-dot","className"), Output("bt-body","children"), Output("bt-error","children"),
    Output("bt-rssi","figure"), Output("bt-vendors","figure"),
    Input("bt-int","n_intervals"), Input("mobile-refresh-btn","n_clicks")
)
def update_bt(n, _refresh):
    with bt_lock: b = dict(bt_data); devs = list(bt_data["devices"])
    if b.get("scanning") and devs:
        elapsed = time.time() - (b.get("scan_started") or time.time())
        st = f"CHANNEL 6 SCANNING · {elapsed:.0f}s · showing the previous sweep ({len(devs)} devices) until this one completes"
        sc = AMBER; dot = "online-dot warn"
    elif b["error"]:
        stale = " · list below is the last successful scan" if devs else ""
        st = f"CHANNEL 6 UNAVAILABLE · {b['error'][:72]}{stale}"; sc = RED; dot = "online-dot off"
    elif b["last_rx"] is None:
        st = f"CHANNEL 6 DISCOVERY · {b['scan_mode']} · first result pending"
        sc = AMBER; dot = "online-dot warn"
    else:
        age = time.time() - b["last_rx"]
        st = f"CHANNEL 6 DISCOVERY · {len(devs)} advertisers · {b['backend']} · {b['scan_mode']} · {age:.0f}s ago"
        sc = GREEN; dot = "online-dot on"
    closest = "—"
    if devs and devs[0]["rssi"] is not None:
        closest = f"{devs[0]['rssi']} unit"
    elif devs:
        closest = devs[0]["name"][:18]
    named = sum(1 for d in devs if d["name"] and not d["name"].startswith("("))
    berr = (html.Div(f"STATUS: {b['error']}", className="error-box", style={"marginTop":"14px"})
            if b["error"] else None)
    return (str(len(devs)), closest, str(named), b["adapter"],
            st, f"online-text {_cls(sc)}", dot, _bt_rows(devs), berr,
            fig_ble_rssi(devs), fig_ble_vendors(devs))


@app.callback(Output("wf-sweep-note", "children"), Input("wf-sweep-now", "n_clicks"),
              prevent_initial_call=True)
def wifi_sweep_now(_n):
    wifi_scan_now.set()
    return 'Fresh Channel 5 discovery requested'


@app.callback(Output("bt-sweep-note", "children"), Input("bt-sweep-now", "n_clicks"),
              prevent_initial_call=True)
def bluetooth_sweep_now(_n):
    bt_scan_now.set()
    return 'Fresh Channel 6 discovery requested'


# ── NVTRA chat: word-by-word, append-only (no whole-section re-render) ──
# 1. A CLIENTSIDE handler appends the user bubble + an empty NVTRA bubble to the DOM and
#    clears the input, then stashes the question in the `nvtra-ask` store.
# 2. A SERVER callback answers (any provider) and returns the full text in `nvtra-reply`.
# 3. A CLIENTSIDE typewriter types that text word-by-word into the empty bubble.
# The #nvtra-msgs container is never rebuilt on send, so nothing flashes.
app.clientside_callback(
    """
    function(nc, ns, value){
      var dc = window.dash_clientside;
      var ctx = dc.callback_context;
      if(!ctx.triggered.length) return [dc.no_update, dc.no_update];
      // Ignore "ghost" fires when buttons are added on page mount: a real click gives
      // n_clicks >= 1, a fresh mount gives 0/null.
      if(!ctx.triggered[0].value) return [dc.no_update, dc.no_update];
      var msg = (value || '').trim();
      if(!msg) return [dc.no_update, dc.no_update];
      var title = document.getElementById('nvtra-session-title');
      if(title && title.textContent.trim() === 'New session'){
        var shortTitle = msg.replace(/\\s+/g, ' ').trim().slice(0, 54);
        title.textContent = shortTitle;
        var activeName = document.querySelector('.chat-session.active .session-name');
        if(activeName) activeName.textContent = shortTitle;
      }
      var msgs = document.getElementById('nvtra-msgs');
      if(!msgs) return [dc.no_update, ''];
      var old = document.getElementById('nvtra-live-bubble'); if(old) old.removeAttribute('id');
      var u = document.createElement('div'); u.className = 'nvtra-msg-user'; u.textContent = msg;
      msgs.appendChild(u);
      var a = document.createElement('div'); a.className = 'nvtra-msg-ai'; a.id = 'nvtra-live-bubble';
      a.innerHTML = '<div class="nvtra-msg-sender">NVTRA</div><div class="nvtra-live-text"><span class="nvtra-caret">\\u258d</span></div>';
      msgs.appendChild(a);
      msgs.scrollTop = msgs.scrollHeight;
      return [{text: msg, nonce: Date.now()}, ''];
    }
    """,
    Output("nvtra-ask", "data"), Output("nvtra-chat-input", "value"),
    Input("nvtra-send-btn", "n_clicks"), Input("nvtra-chat-input", "n_submit"),
    State("nvtra-chat-input", "value"),
    prevent_initial_call=True,
)


@app.callback(Output("nvtra-reply", "data"), Input("nvtra-ask", "data"),
              prevent_initial_call=True)
def nvtra_fetch_reply(ask):
    if not ask or not (ask.get("text") or "").strip():
        raise PreventUpdate
    msg = ask["text"].strip()
    conversation_id = str(ask.get("nonce") or int(time.time() * 1000))
    with nvtra_lock:
        session = _active_chat_session()
        is_first_message = not session.get("messages")
        if is_first_message:
            session["title"] = re.sub(r"\s+", " ", msg).strip()[:54] or "New session"
            session["title_source"] = "input"
        session_id = session["id"]
        session_title = session["title"]
        session["messages"].append({"role": "user", "text": msg})
        session["updated_utc"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )
        nvtra_history.append({"role": "user", "text": msg})
        nvtra_chat_archive.append({
            "id": conversation_id,
            "session_id": session_id,
            "title": session_title,
            "recorded_utc": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            ),
            "user": msg,
            "answer": "",
            "status": "pending",
        })
        hist = list(nvtra_history)
    _save_local_cloud_state()
    _notion_background("Chat History", f"NVTRA input · {conversation_id}", [
        ('Text', session_id),
        ("Session title", session_title),
        ('Text', conversation_id),
        ('Text', time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("User", msg),
        ("Status", "pending"),
    ])
    if not nvtra_online():
        txt = _nvtra_error_text("no-key"); is_err = True
    else:
        reply, err = _gemini_generate(hist)
        txt = reply if reply else _nvtra_error_text(err); is_err = not reply
    with nvtra_lock:
        nvtra_history.append({"role": "model", "text": txt, "error": is_err})
        session = next(
            (item for item in nvtra_sessions if item.get("id") == session_id),
            None,
        )
        if session:
            session["messages"].append({
                "role": "model", "text": txt, "error": is_err,
            })
            session["updated_utc"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            )
        archived = next(
            (item for item in reversed(nvtra_chat_archive)
             if item.get("id") == conversation_id),
            None,
        )
        if archived:
            archived["answer"] = txt
            archived["status"] = "error" if is_err else "complete"
    _save_local_cloud_state()
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _notion_background("Chat History", f"NVTRA chat · {stamp}", [
        ('Text', session_id),
        ("Session title", session_title),
        ('Text', conversation_id),
        ('Text', stamp),
        ("User", msg),
        ("NVTRA", txt),
        ("Status", "error" if is_err else "complete"),
    ])
    return {"text": txt, "error": is_err, "nonce": ask.get("nonce", 0)}


app.clientside_callback(
    """
    function(rep){
      if(!rep || !rep.nonce) return '';
      var bubble = document.getElementById('nvtra-live-bubble');
      if(!bubble) return '';
      var target = bubble.querySelector('.nvtra-live-text');
      if(!target) return '';
      bubble.classList.toggle('nvtra-msg-err', !!rep.error);
      var words = (rep.text || '').split(/(\\s+)/);
      var i = 0; target.textContent = '';
      var msgs = document.getElementById('nvtra-msgs');
      if(window.__nvtraTyper) clearInterval(window.__nvtraTyper);
      window.__nvtraTyper = setInterval(function(){
        if(!bubble.isConnected || i >= words.length){
          clearInterval(window.__nvtraTyper);
          bubble.removeAttribute('id');
          return;
        }
        target.textContent += words[i]; i++;
        if(msgs) msgs.scrollTop = msgs.scrollHeight;
      }, 40);
      return '';
    }
    """,
    Output("nvtra-type-dummy", "children"), Input("nvtra-reply", "data"),
    prevent_initial_call=True,
)


# ── EMI analysis: selected LLM + real, trusted sensor windows ──
emi_analysis_lock = threading.Lock()


@app.callback(
    Output("emi-auto-state", "data"), Output("emi-auto-btn", "children"),
    Output("emi-auto-interval", "disabled"), Output("emi-status", "children"),
    Input("emi-auto-btn", "n_clicks"), State("emi-auto-state", "data"),
    prevent_initial_call=True,
)
def toggle_emi_auto(n_clicks, enabled):
    if not n_clicks:
        raise PreventUpdate
    active = not bool(enabled)
    return (
        active,
        "STOP AUTO ANALYSIS" if active else "START AUTO · 45 S",
        not active,
        "Automatic live-window analysis is active every 45 seconds."
        if active else "Automatic analysis stopped; manual analysis remains available.",
    )


@app.callback(Output("emi-live-state", "children"), Input("mtdi-interval", "n_intervals"),
              Input("mobile-refresh-btn","n_clicks"))
def update_emi_live_state(_n, _refresh):
    with mag_lock:
        mag_count = len(magnetic_data["history"])
        mag_ok = magnetic_data["error"] is None and magnetic_data["last_rx"] is not None
    with efield_lock:
        ef_count = len(efield_data["history"])
        ef_ok = efield_data["error"] is None and efield_data["last_rx"] is not None
    with spectrum_lock:
        rf_count = len(spectrum_data["levels"])
        rf_ok = spectrum_data["error"] is None and spectrum_data["last_rx"] is not None
        rf_trusted = spectrum_data["trusted"]
    def chip(label, count, state):
        return html.Div([html.B(f"{count} SAMPLES"), f"{label} · {state}"], className="emi-live-chip")
    return [
        chip('LABEL', mag_count, "LIVE" if mag_ok else "OFFLINE"),
        chip('LABEL', ef_count, "LIVE" if ef_ok else "OFFLINE"),
        chip('LABEL', rf_count, "TRUSTED" if rf_ok and rf_trusted else
             ("UNTRUSTED" if rf_ok else "OFFLINE")),
    ]


@app.callback(Output("nvtra-ml-result", "children"),
              Input("mtdi-interval", "n_intervals"),
              Input("mobile-refresh-btn", "n_clicks"))
def update_nvtra_basic_ml(_n, _refresh):
    with mag_lock:
        magnetic_ut = float(magnetic_data["magnitude"])
        mag_ready = magnetic_data["error"] is None and magnetic_data["last_rx"] is not None
    with efield_lock:
        electric_v_m = float(efield_data["field_v_m"])
        ef_ready = efield_data["error"] is None and efield_data["last_rx"] is not None
    if not (mag_ready and ef_ready):
        return 'MODEL WAITING\nBoth live channel 1 and channel 2 sources are required.'
    result = _nvtra_basic_ml(electric_v_m, magnetic_ut)
    confidence = f"{result['confidence']}%" if result["label"] != "UNKNOWN" else "REJECTED"
    return (
        f"ESTIMATE · {result['label']}\n"
        f"LIVE INPUT · {electric_v_m:.1f} unit · {magnetic_ut:.1f} unit\n"
        f"MODEL CONFIDENCE · {confidence}\n"
        f"REASON · {result['reason']}"
    )


@app.callback(
    Output("emi-result", "children"),
    Input("emi-analyse-btn", "n_clicks"), Input("emi-auto-interval", "n_intervals"),
    prevent_initial_call=True,
)
def analyse_live_emi(manual_clicks, auto_ticks):
    ctx = dash.callback_context
    if not ctx.triggered or not ctx.triggered[0].get("value"):
        raise PreventUpdate
    if RUNTIME["demo"]:
        return html.Div(
            'Paragraph. Enter your text here.',
            className="error-box",
        )
    if not nvtra_online():
        return html.Div(_nvtra_error_text("no-key"), className="error-box")
    if not emi_analysis_lock.acquire(blocking=False):
        return 'An interference analysis is already running. The current source window remains live.'
    try:
        snapshot, error = _emi_live_snapshot()
        if error:
            return html.Div(error, className="error-box")
        prompt = (
            'Analyse this live MTDI Studio source window. Base every conclusion on the supplied arrays, computed features, freshness, and trust flags.\n\n' +
            json.dumps(snapshot, separators=(",", ":"), sort_keys=True)
        )
        reply, ai_error = _selected_ai_generate(
            EMI_ANALYST_SYSTEM, [{"role": "user", "text": prompt}],
            max_output_tokens=1800,
        )
        if not reply:
            return html.Div(_nvtra_error_text(ai_error or "empty"), className="error-box")
        missing = _emi_missing_headings(reply)
        if missing:
            repair_history = [
                {"role": "user", "text": prompt},
                {"role": "model", "text": reply},
                {"role": "user", "text": (
                    'Paragraph. Enter your text here. '
                    + ", ".join(missing)
                )},
            ]
            repaired, repair_error = _selected_ai_generate(
                EMI_ANALYST_SYSTEM, repair_history, max_output_tokens=1800,
            )
            if repaired and not _emi_missing_headings(repaired):
                reply = repaired
            else:
                still_missing = _emi_missing_headings(repaired or reply)
                return html.Div(
                    'Paragraph. Enter your text here. ' + ", ".join(still_missing) +
                    (f"\nProvider error: {_nvtra_error_text(repair_error)}"
                     if repair_error else '\nText'),
                    className="error-box",
                )
        key, provider = _active_ai_credential()
        model = _active_ai_model() or "provider default"
        header = (
            f"ANALYSED {snapshot['captured_utc']} · "
            f"{_provider_label(key, provider).upper()} · {model}\n\n"
        )
        return header + reply.strip()
    finally:
        emi_analysis_lock.release()


# ── MTDI live (health + completeness + Pi telemetry) ──
def _pi_grid():
    with sys_lock: sd = dict(sys_data)
    def _bar(p, c):
        return html.Div(html.Div(style={"width":f"{min(p,100):.0f}%","height":"4px","borderRadius":"2px","background":c},
                                 className="sys-bar-fill"), className="sys-bar-track")
    def _pc(p): return RED if p > 90 else AMBER if p > 70 else CYAN
    temp = sd["cpu_temp"]
    temp_ready = bool(sd.get("temperature_available"))
    tempc = RED if temp > 75 else AMBER if temp > 60 else GREEN
    return [
        html.Div([html.Div('LABEL', className="sys-name"), html.Div(f"{sd['cpu_usage']}%", className=f"sys-value {_cls(_pc(sd['cpu_usage']))}"), _bar(sd['cpu_usage'], _pc(sd['cpu_usage']))], className="sys-card"),
        html.Div([html.Div('LABEL', className="sys-name"), html.Div(f"{temp:.1f} °C" if temp_ready else 'TEXT', className=f"sys-value {_cls(tempc if temp_ready else SUBTEXT)}"), html.Div(sd.get("telemetry_source", "host sensor"), className="sys-sub")], className="sys-card"),
        html.Div([html.Div('LABEL', className="sys-name"), html.Div(f"{sd['ram_used_mb']} MB", className="sys-value"), html.Div(f"of {sd['ram_total_mb']} MB  ({sd['ram_pct']}%)", className="sys-sub"), _bar(sd['ram_pct'], _pc(sd['ram_pct']))], className="sys-card"),
        html.Div([html.Div('LABEL', className="sys-name"), html.Div(f"{sd['disk_used_gb']} GB", className="sys-value"), html.Div(f"of {sd['disk_total_gb']} GB  ({sd['disk_pct']}%)", className="sys-sub"), _bar(sd['disk_pct'], _pc(sd['disk_pct']))], className="sys-card"),
        html.Div([html.Div('LABEL', className="sys-name"), html.Div(sd["uptime_str"], className="sys-value")], className="sys-card"),
        html.Div([html.Div('LABEL', className="sys-name"), html.Div(f"{sd['load_1']}", className="sys-value"), html.Div(f"5m: {sd['load_5']}  15m: {sd['load_15']}", className="sys-sub")], className="sys-card"),
        html.Div([html.Div('LABEL', className="sys-name"), html.Div(sd["wifi_ip"], className="sys-value", style={"fontSize":"18px"}), html.Div(f"open :{RUNTIME['port']} here", className="sys-sub")], className="sys-card"),
        html.Div([html.Div('LABEL', className="sys-name"), html.Div(f"{sd['py_mem_mb']} MB", className="sys-value"), html.Div('Subtext', className="sys-sub")], className="sys-card"),
        html.Div([html.Div('LABEL', className="sys-name"), html.Div(f"v{sd['app_version']}", className="sys-value"), html.Div(sd.get("host_model", "host detecting"), className="sys-sub"), html.Div(f"{sd['worker_count']} workers · {sd['thread_count']} threads · live {max(0.0,time.time()-(sd.get('last_rx') or time.time())):.1f}s ago", className="sys-sub")], className="sys-card"),
        html.Div([html.Div("ARCHIVE", className="sys-name"), html.Div(f"{sd['db_size_mb']} MB", className="sys-value"), html.Div(f"queue {sd['archive_queue']} · {'writer active' if sd['last_db_write'] else 'write pending'}", className="sys-sub")], className="sys-card"),
    ]


@app.callback(
    Output("mtdi-overall","children"), Output("mtdi-sensor-grid","children"),
    Output("esp-sys-grid","children"), Output("mtdi-sys-grid","children"),
    Input("mtdi-interval","n_intervals"), Input("mobile-refresh-btn","n_clicks")
)
def update_mtdi(n, _refresh):
    with mtdi_lock:
        mc = mtdi_data["mag_health"]; ec = mtdi_data["efield_health"]
        rc = mtdi_data["rf_health"]; ov = mtdi_data["active_health"]
        completeness = mtdi_data["completeness"]
        mn_ = mtdi_data["mag_note"]; en_ = mtdi_data["efield_note"]
        rn_ = mtdi_data["rf_note"]
    with mag_lock: md = dict(magnetic_data); h10 = list(magnetic_data["history"])[-10:]
    with efield_lock: ed = dict(efield_data)
    with spectrum_lock: sd_rf = dict(spectrum_data)
    eonline = ed["error"] is None and ed["last_rx"] is not None and ed["calibrated"]
    ronline = sd_rf["error"] is None and sd_rf["last_rx"] is not None
    def _cc(v): return GREEN if v > 80 else AMBER if v > 50 else RED
    ov_el = html.Div([html.Div([
                     html.Div(f"{ov:.0f}%", className=f"conf-ring-val {_cls(_cc(ov))}"),
                     html.Div(f"ACTIVE HEALTH · {completeness:.0f}% COMPLETE", className="conf-ring-sub")],
                     className="conf-ring", style={"borderColor":_cc(ov), "boxShadow":f"0 0 40px {_cc(ov)}33"})])
    def _conf_card(name, val, note):
        return html.Div([html.Div(name, className="sensor-conf-name"),
                         html.Div(f"{val:.0f}%", className=f"source-conf-val {_cls(_cc(val))}"),
                         html.Div(note, className="sensor-conf-note"),
                         html.Div(html.Div(style={"width":f"{min(max(val,0),100):.0f}%","height":"4px",
                                                  "borderRadius":"2px","background":_cc(val)}),
                                  className="sys-bar-track")], className="sensor-conf-card")
    sensor_grid = [
        _conf_card('LABEL', mc, mn_),
        _conf_card('LABEL', ec, en_),
        _conf_card('LABEL', rc, rn_),
        _conf_card('LABEL', completeness, 'Paragraph. Enter your text here.'),
    ]
    mo_ = md["error"] is None and md["last_rx"] is not None
    ma = round(time.time() - md["last_rx"], 1) if md["last_rx"] else None
    if len(h10) >= 2:
        mean = sum(h10)/len(h10); std = (sum((v-mean)**2 for v in h10)/len(h10))**0.5
        vs = f"{std:.2f} unit"; vc_ = GREEN if std < 0.5 else AMBER if std < 2.0 else RED
    else:
        vs = "—"; vc_ = SUBTEXT
    def _card(nm, val, sub=None, vc=WHITE):
        ch = [html.Div(nm, className="sys-name"), html.Div(val, className=f"sys-value {_cls(vc)}")]
        if sub: ch.append(html.Div(sub, className="sys-sub"))
        return html.Div(ch, className="sys-card")
    sensor_side = [
        _card('SOURCE LINK', "ONLINE" if mo_ else "OFFLINE",
              f"Source 1 @ 0x2C  {ma}s ago" if ma is not None else 'Text',
              vc=(AMBER if md["chip_warning"] else GREEN) if mo_ else RED),
        _card("CALIBRATION", 'TITLE' if md["calibrated"] else 'TITLE',
              'Text' if md["calibrated"] else 'Text',
              vc=CYAN if md["calibrated"] else SUBTEXT),
        _card("MAGNITUDE", f"{md['magnitude']:.2f} unit" if mo_ else "—",
              f"Min {md['min_mag']:.2f}  Max {md['max_mag']:.2f}" if md['min_mag'] != float('inf') else "—",
              vc=CYAN if mo_ else SUBTEXT),
        _card("NOISE σ", vs, 'Text', vc=vc_),
        _card('CHANNEL 2 LINK', "ONLINE" if eonline else ('TITLE' if ed["error"] is None else "OFFLINE"),
              f"diff A0-A1 · {_gain_label(ed['gain'])} · {ed['level']}" if eonline else (ed["error"] or "warming up")[:40],
              vc=GREEN if eonline else (AMBER if ed["error"] is None else RED)),
        _card('CHANNEL 2',
              (f"{ed.get('rms_counts'):.2f} ADC counts RMS"
               if ed.get("data_source") == "ARDUINO_UNO_USB" and ed.get("rms_counts") is not None else
               f"{ed['field_v_m']:.3f} unit = N/C" if ed["last_rx"] and ed["field_v_m"] is not None else "—"),
              ('Text' if ed["clipped"] else
               'Text' if ed.get("data_source") == "ARDUINO_UNO_USB" else
               f"index {ed['rel_index']:.0f}% · base {ed['baseline_v_m']:.3f} unit"),
              vc=RED if ed["clipped"] else CYAN),
        _card("SAMPLES", str(len(md["xyz_history"])), 'Text', vc=WHITE),
        _card('CHANNEL 3 LINK', ('TITLE' if sd_rf["trusted"] else 'TITLE') if ronline else "OFFLINE",
              f"{sd_rf['device'][:28]} · {sd_rf['sweeps']} sweeps" if ronline
              else (sd_rf["error"] or "waiting")[:40],
              vc=(GREEN if sd_rf["trusted"] else AMBER) if ronline else RED),
        _card('CH 3 PEAK', f"{sd_rf['peak_level']:+.1f} unit" if ronline else "—",
              (f"{_freq_label(sd_rf['peak_freq'])} · {_band_of(sd_rf['peak_freq'])}" if ronline else 'Text'),
              vc=(CYAN if sd_rf["level_sane"] else RED) if ronline else SUBTEXT),
        _card('BROAD EST. CH 3 FLOOR', f"{sd_rf['floor']:+.1f} unit" if ronline else "—",
              (sd_rf["level_note"][:42] if ronline else "—"),
              vc=(WHITE if sd_rf["level_sane"] else RED) if ronline else SUBTEXT),
        _card('CH 3 SPAN', _span_label(sd_rf["span_start"], sd_rf["span_stop"]) if ronline else "—",
              f"{sd_rf['points']} pts · {sd_rf['sweep_s']:.1f}s/sweep" if ronline else "—", vc=CYAN),
    ]
    return ov_el, sensor_grid, sensor_side, _pi_grid()


@app.callback(
    Output("ei-mag-baseline", "children"), Output("ei-mag-delta", "children"),
    Output("ei-ef-baseline", "children"), Output("ei-ef-live", "children"),
    Output("ei-baseline-status", "children"),
    Input("mtdi-interval", "n_intervals"), Input("mobile-refresh-btn","n_clicks"),
)
def update_environmental_intelligence(n, _refresh):
    with mag_lock:
        mag_ready = magnetic_data["baseline_calibrated"]
        mag_base = magnetic_data["baseline_magnitude"]
        mag_delta = magnetic_data["baseline_delta"]
        mag_error = magnetic_data["error"]
    with efield_lock:
        ef_ready = efield_data["calibrated"]
        ef_base = efield_data["baseline_v_m"]
        ef_live = efield_data["field_v_m"]
        ef_error = efield_data["error"]
        ef_clipped = efield_data["clipped"]

    mag_text = f"{mag_base:.2f} unit" if mag_ready else "LEARNING"
    delta_text = f"{mag_delta:.2f} unit" if mag_ready else "—"
    ef_base_text = f"{ef_base:.3f} unit" if ef_ready else "LEARNING"
    ef_live_text = (("≥ " if ef_clipped else "") + f"{ef_live:.3f} unit") if not ef_error else "—"

    if mag_error or ef_error:
        status = f"BASELINE CHANNEL WARNING · CH 1: {mag_error or 'ready'} · E: {ef_error or 'ready'}"
    elif mag_ready and ef_ready:
        status = "BASELINES LOCKED · references remain fixed until recalibration"
    else:
        status = "LEARNING ENVIRONMENT · keep both probes fixed and clear"
    return mag_text, delta_text, ef_base_text, ef_live_text, status


# ── settings system grid ──
@app.callback(Output("settings-sys-grid","children"), Input("settings-interval","n_intervals"),
              Input("mobile-refresh-btn","n_clicks"))
def update_settings_sys(n, _refresh):
    return _pi_grid()


@app.callback(
    Output("archive-json-download","data"),
    Input("archive-json-btn","n_clicks"), prevent_initial_call=True,
)
def do_archive_json(n):
    if not n:
        raise PreventUpdate
    stamp = time.strftime("%Y%m%d_%H%M%S")
    payload = export_archive_json_bytes()
    filename = f"studio_archive_{stamp}.json"
    return dcc.send_bytes(lambda buffer: buffer.write(payload),
                          filename)


@app.callback(
    Output("archive-csv-download","data"),
    Input("archive-csv-btn","n_clicks"), prevent_initial_call=True,
)
def do_archive_csv(n):
    if not n:
        raise PreventUpdate
    stamp = time.strftime("%Y%m%d_%H%M%S")
    payload = export_rf_csv_bytes()
    filename = f"studio_rf_sweeps_{stamp}.csv"
    return dcc.send_bytes(lambda buffer: buffer.write(payload),
                          filename)


# ── API key manager ──────────────────────────────────────────────────────────
# Switching / deleting a key just mutates the server-side store; the two views
# (Settings list + NVTRA pill bar) are re-rendered by their page intervals so both
# stay in sync no matter where the change was made.
@app.callback(Output("key-use-sink", "data"),
              Input({"type": "key-use", "id": ALL}, "n_clicks"), prevent_initial_call=True)
def key_use(_clicks):
    ctx = dash.callback_context
    if ctx.triggered and ctx.triggered[0]["value"]:
        try:
            kid = json.loads(ctx.triggered[0]["prop_id"].rsplit(".", 1)[0])["id"]
            nvtra_set_active(kid)
        except Exception:
            LOG.warning("Invalid key-selection callback payload", exc_info=True)
    return time.time()


@app.callback(Output("chat-model-use-sink", "data"),
              Output("nvtra-model-picker-wrap", "children"),
              Input({"type": "chat-model-use", "id": ALL}, "n_clicks"),
              prevent_initial_call=True)
def chat_model_use(_clicks):
    ctx = dash.callback_context
    if ctx.triggered and ctx.triggered[0]["value"]:
        try:
            kid = json.loads(ctx.triggered[0]["prop_id"].rsplit(".", 1)[0])["id"]
            nvtra_set_active(kid)
        except Exception:
            LOG.warning("Invalid chat model-selection payload", exc_info=True)
    return time.time(), _render_model_picker()


@app.callback(
    Output("nvtra-msgs", "children"), Output("chat-session-sink", "data"),
    Output("nvtra-session-list", "children"),
    Output("nvtra-session-title", "children"),
    Input("nvtra-new-session-btn", "n_clicks"),
    Input({"type": "chat-session-open", "id": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def select_chat_session(new_clicks, session_clicks):
    ctx = dash.callback_context
    if not ctx.triggered or not ctx.triggered[0]["value"]:
        raise PreventUpdate
    triggered = ctx.triggered[0]["prop_id"].rsplit(".", 1)[0]
    with nvtra_lock:
        if triggered == "nvtra-new-session-btn":
            session = _new_chat_session()
        else:
            try:
                sid = json.loads(triggered)["id"]
            except Exception:
                raise PreventUpdate
            session = next((s for s in nvtra_sessions if s.get("id") == sid), None)
            if not session:
                raise PreventUpdate
            nvtra_active_session[0] = sid
        _sync_history_from_session(session)
        children = _nvtra_msg_els()
    _save_local_cloud_state()
    return (children, {"id": session["id"], "at": time.time()},
            _render_chat_sessions(), session.get("title", "New session"))


@app.callback(Output("key-del-sink", "data"),
              Input({"type": "key-del", "id": ALL}, "n_clicks"), prevent_initial_call=True)
def key_del(_clicks):
    ctx = dash.callback_context
    if ctx.triggered and ctx.triggered[0]["value"]:
        try:
            kid = json.loads(ctx.triggered[0]["prop_id"].rsplit(".", 1)[0])["id"]
            nvtra_delete_key(kid)
        except Exception:
            LOG.warning("Invalid key-deletion callback payload", exc_info=True)
    return time.time()


@app.callback(
    Output("key-name-sink", "data"),
    Input({"type": "key-name-save", "id": ALL}, "n_clicks"),
    State({"type": "key-name", "id": ALL}, "value"),
    State({"type": "key-name", "id": ALL}, "id"),
    prevent_initial_call=True,
)
def key_rename(_clicks, values, ids):
    ctx = dash.callback_context
    if not ctx.triggered or not ctx.triggered[0].get("value"):
        raise PreventUpdate
    try:
        triggered = json.loads(ctx.triggered[0]["prop_id"].rsplit(".", 1)[0])
        kid = triggered["id"]
        mapping = {
            ident["id"]: value for ident, value in zip(ids or [], values or [])
        }
        if not nvtra_rename_key(kid, mapping.get(kid, "")):
            raise PreventUpdate
    except PreventUpdate:
        raise
    except Exception:
        LOG.warning("Invalid key-rename callback payload", exc_info=True)
        raise PreventUpdate
    return {"renamed": kid, "at": time.time()}


@app.callback(
    Output("key-add-input", "value"), Output("key-label-input", "value"),
    Output("key-provider-input", "value"),
    Output("key-status", "children"),
    Input("key-add-btn", "n_clicks"), Input("key-test-btn", "n_clicks"),
    State("key-add-input", "value"), State("key-label-input", "value"),
    State("key-provider-input", "value"),
    prevent_initial_call=True,
)
def key_add_or_test(add_n, test_n, key_val, label_val, provider_val):
    ctx = dash.callback_context
    tid = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""
    if tid == "key-add-btn":
        key_val = (key_val or "").strip()
        requested_provider = provider_val or "auto"
        if requested_provider == "auto" and _key_provider(key_val) == "unknown":
            inferred = _provider_from_label(label_val)
            if inferred != "unknown":
                requested_provider = inferred
        provider, error = _validate_key_provider(key_val, requested_provider)
        if error:
            return key_val, label_val, provider_val or "auto", error
        kid = nvtra_add_key(label_val, key_val, provider)
        active_model = _active_ai_model()
        return "", "", "auto", (
            f"{_provider_label(key_val, provider)} key added and made active. "
            f"Model: {active_model or 'provider default'}. "
            "Hit TEST ACTIVE to verify access."
        )
    # TEST ACTIVE
    if not _gemini_key():
        return key_val, label_val, provider_val or "auto", _nvtra_error_text("no-key")
    active_key, active_provider = _active_ai_credential()
    prov = _provider_label(active_key, active_provider)
    reply, err = _gemini_generate([{"role": "user", "text": 'Text'}])
    if reply:
        return key_val, label_val, provider_val or "auto", f"Active {prov} key works — NVTRA is ready."
    return key_val, label_val, provider_val or "auto", _nvtra_error_text(err)


# Re-render the Settings key list from server state each tick (reflects add/switch/delete).
@app.callback(Output("key-list", "children"), Input("settings-interval", "n_intervals"),
              Input("mobile-refresh-btn","n_clicks"))
def refresh_key_list(_n, _refresh):
    return _render_key_list()


# Keep the NVTRA panel's key pills in sync via the MTDI interval.
@app.callback(
    Output("nvtra-key-bar", "children"),
    Output("nvtra-chat-input", "disabled"), Output("nvtra-chat-input", "placeholder"),
    Output("nvtra-send-btn", "disabled"),
    Input("mtdi-interval", "n_intervals"), Input("mobile-refresh-btn","n_clicks"),
)
def refresh_nvtra_key_bar(_n, _refresh):
    _start_notion_drain()
    online = nvtra_online()
    local = local_ai_status()
    if instrument_offline():
        placeholder = ("Ask about a reading (offline, local model " + str(local["model"]) + ")…") if online else "Offline mode: local model not installed yet…"
    else:
        placeholder = "Ask about a reading…" if online else "Add an API key to enable chat…"
    return (_render_nvtra_key_bar(), not online, placeholder, not online)


@app.callback(Output("nvtra-engine-badge", "children"), Input("mtdi-interval", "n_intervals"))
def refresh_nvtra_engine_badge(_n):
    return _nvtra_engine_badge_text()


# ── animations (clientside, persisted in localStorage) ──
app.clientside_callback(
    """
    function(non, noff){
      var c = window.dash_clientside.callback_context;
      if(!c.triggered.length) return "";
      var id = c.triggered[0].prop_id.split(".")[0];
      if(id === "anim-off"){
        document.documentElement.classList.add("no-anim");
        var sh = document.getElementById('page-shader-canvas'); if(sh) sh.remove();
        try{localStorage.setItem("iv-anim","off");}catch(e){}
      } else {
        document.documentElement.classList.remove("no-anim");
        if(window.__ivBootPageShader) window.__ivBootPageShader();
        try{localStorage.setItem("iv-anim","on");}catch(e){}
      }
      return "";
    }
    """,
    Output("settings-anim-dummy","children"),
    Input("anim-on","n_clicks"), Input("anim-off","n_clicks"),
    prevent_initial_call=True
)


# ── settings: phone layout, desktop composition or native mobile reflow ──
app.clientside_callback(
    """
    function(ndesktop, nmobile){
      var c = window.dash_clientside.callback_context;
      if(!c.triggered.length) return "";
      var id = c.triggered[0].prop_id.split(".")[0];
      var mobile = (id === "phone-layout-mobile");
      try{ localStorage.setItem("iv-phone-layout", mobile ? "mobile" : "desktop"); }catch(e){}
      /* syncPhoneMode owns the viewport meta and the stage transform. Calling it
         re-reads the setting we just stored, so the change lands without a reload;
         resizing is the event it already listens for. On a desktop browser it is a
         no-op, which is why the buttons are safe to press anywhere. */
      try{
        if(window.__ivSyncPhoneMode) window.__ivSyncPhoneMode();
        else window.dispatchEvent(new Event('resize'));
      }catch(e){}
      return "";
    }
    """,
    Output("settings-phone-layout-dummy","children"),
    Input("phone-layout-desktop","n_clicks"), Input("phone-layout-mobile","n_clicks"),
    prevent_initial_call=True
)


def _component_ids(component):
    """Yield Dash IDs from a component tree without starting the application."""
    if component is None:
        return
    component_id = getattr(component, "id", None)
    if component_id is not None:
        yield json.dumps(component_id, sort_keys=True) if isinstance(component_id, dict) else str(component_id)
    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _component_ids(child)
    elif children is not None and not isinstance(children, (str, int, float, bool)):
        yield from _component_ids(children)


def run_self_test():
    """Mock/software checks only; this never claims hardware validation."""
    failures = []

    if _nvtra_basic_ml(50.0, 2000.0)["label"] != "REFERENCE 1":
        failures.append("NVTRA basic ML rejected its first training example")
    if _nvtra_basic_ml(40.0, 702.0)["label"] != "REFERENCE 2":
        failures.append("NVTRA basic ML rejected its second training example")
    if _nvtra_basic_ml(500.0, 10000.0)["label"] != "UNKNOWN":
        failures.append("NVTRA basic ML did not reject an out-of-distribution example")

    help_variants = (
        'Text',
        'Text',
        'Text',
    )
    if not all(_help_advertises_command(text, "scan") for text in help_variants):
        failures.append("TinySA help capability lookup rejected a valid scan entry")
    if _help_advertises_command("version\ninfo\nleveloffset", "scan"):
        failures.append("TinySA help capability lookup found a nonexistent scan entry")

    two = "100000 -90.0\n200000 -88.5\n300000 -91.0\n"
    three = "scan 100000 300000 3 3\n100000 -90.0 0\n200000 -88.5 0\n300000 -91.0 0\nch>"

    class MockTinySATransport:
        """Prompt-framed serial fixture whose help intentionally omits `scan`."""
        help_text = "version\ninfo\nleveloffset"

        def __init__(self):
            self.response = b""

        def reset_input_buffer(self):
            self.response = b""

        def write(self, raw):
            command = raw.decode("ascii").strip()
            self.response = (
                f"{command}\r\n"
                "100000 -90.0 0\r\n"
                "200000 -88.5 0\r\n"
                "300000 -91.0 0\r\n"
                "ch>"
            ).encode("ascii")

        def flush(self):
            return None

        def read(self, size):
            chunk, self.response = self.response[:size], self.response[size:]
            return chunk

    try:
        mock_tsa = MockTinySATransport()
        if _help_advertises_command(mock_tsa.help_text, "scan"):
            failures.append("mock fixture unexpectedly advertises scan")
        f, levels, _raw, _warnings = _tsa_scan(
            mock_tsa, 100_000, 300_000, 3, timeout=0.25
        )
        validate_sweep(f, levels, 100_000, 300_000, 3)
    except Exception as exc:
        failures.append(f"unadvertised-but-working text scan regression: {exc}")

    for label, text in (("two-column", two), ("three-column", three)):
        try:
            f, levels = parse_text_scan(text)
            validate_sweep(f, levels, 100_000, 300_000, 3)
        except Exception as exc:
            failures.append(f"{label} parser: {exc}")
    try:
        f, levels = parse_text_scan(two)
        validate_sweep(f[:2], levels[:2], 100_000, 300_000, 3)
        failures.append("truncated sweep was accepted")
    except TinySAProtocolError:
        pass
    try:
        parse_text_scan("scan 1 2 3\nch>")
        failures.append("empty scan was accepted")
    except TinySAProtocolError:
        pass
    try:
        peaks = _tsa_peaks(
            [float(i) for i in range(9)],
            [-100, -100, -99, -70, -99, -100, -75, -100, -100],
            -100,
        )
        if not peaks or peaks[0]["bin_index"] != 3:
            failures.append("local peak detection failed")
    except Exception as exc:
        failures.append(f"peak detection: {exc}")

    # A waterfall row captured before a span change must never be plotted against the
    # new frequency axis.
    kept_rows, kept_times = _waterfall_rows(
        [[1.0, 2.0, 3.0], [1.0, 2.0]], [10.0, 11.0], [0.0, 1.0, 2.0]
    )
    if kept_rows != [[1.0, 2.0, 3.0]] or kept_times != [10.0]:
        failures.append("waterfall row filter kept a mismatched row")

    pages = {
        "root": app.layout,
        "home": home_page(),
        "em": em_page(),
        "em-magnetic": magnetic_view(),
        "em-electric": electric_view(),
        "em-combined": combined_view(),
        "spectrum-rf": spectrum_page(),
        "spectrum-wifi": wifi_view(),
        "spectrum-bluetooth": bluetooth_view(),
        "mtdi": mtdi_page(),
        "settings": settings_page(),
    }
    all_ids = set()
    for name, page in pages.items():
        ids = list(_component_ids(page))
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        if duplicates:
            failures.append(f"{name} duplicate IDs: {', '.join(duplicates[:8])}")
        all_ids.update(ids)

    for callback_name, metadata in app.callback_map.items():
        for dependency in metadata.get("inputs", []) + metadata.get("state", []):
            component_id = str(dependency.get("id", ""))
            if component_id and not component_id.startswith("{") and component_id not in all_ids:
                failures.append(
                    f"callback {callback_name} references missing input/state ID {component_id}"
                )
        raw_outputs = metadata.get("output")
        outputs = raw_outputs if isinstance(raw_outputs, list) else [raw_outputs]
        for dependency in outputs:
            component_id = getattr(dependency, "component_id", None)
            if (
                component_id is not None
                and not isinstance(component_id, dict)
                and str(component_id) not in all_ids
            ):
                failures.append(
                    f"callback {callback_name} references missing output ID {component_id}"
                )

    try:
        magnetic_empty = update_numbers(0, None)
        if magnetic_empty[:4] != ("—", "—", "—", "—"):
            failures.append('offline channel 1 UI displays numeric placeholder data')
        efield_empty = update_efield_numbers(0, None)
        if efield_empty[0] != "—" or efield_empty[2] != "—" or efield_empty[3] != "—":
            failures.append('offline Channel 2 UI displays numeric placeholder data')
    except Exception as exc:
        failures.append(f"empty hardware UI state: {exc}")

    try:
        features = _series_features([1.0, 2.0, 3.0])
        expected = {
            "samples": 3, "min": 1.0, "max": 3.0, "mean": 2.0,
            "stddev": 0.816497, "peak_to_peak": 2.0, "delta_rms": 1.0,
        }
        if features != expected:
            failures.append(f"interference feature extraction changed unexpectedly: {features}")
        snapshot = _system_snapshot()
        required = {
            "cpu_usage", "ram_used_mb", "ram_total_mb", "ram_pct",
            "disk_used_gb", "disk_total_gb", "disk_pct", "uptime_str",
            "temperature_available", "telemetry_source", "host_model",
            "raspberry_pi",
        }
        missing = sorted(required.difference(snapshot))
        if missing:
            failures.append(f"system telemetry snapshot missing keys: {', '.join(missing)}")
        reference_field = _ef_v_per_m(1265.0)
        if os.environ.get("STUDIO_EFIELD_V_PER_M_PER_VOLT") is None and abs(reference_field - 500.0) > 0.001:
            failures.append(
                f"default Channel 2 reference scale maps 1265 mV to {reference_field:.3f} unit, not 500 unit"
            )
        quiet_mv = EF_OBSERVED_QUIET_V_M / EF_V_PER_M_PER_VOLT * 1000.0
        fixture_mv = EF_OBSERVED_REFERENCE_V_M / EF_V_PER_M_PER_VOLT * 1000.0
        if abs(_ef_calibrated_v_per_m(quiet_mv, quiet_mv)) > 0.001:
            failures.append('Channel 2 environmental reference does not calibrate to 0 unit')
        calibrated_fixture = _ef_calibrated_v_per_m(fixture_mv, quiet_mv)
        normalized_fixture = 500.0 * EF_PHONE_NORMALIZATION
        if abs(calibrated_fixture - normalized_fixture) > 0.001:
            failures.append(
                f"Channel 2 fixture maps to {calibrated_fixture:.3f} unit, not {normalized_fixture:.3f} unit"
            )
        if abs(EF_PHONE_PREVIOUS_V_M * EF_PHONE_NORMALIZATION - 50.0) > 0.001:
            failures.append('Channel 2 phone normalization does not map 1200 unit to 50 unit')
        for raw_ut, expected_ut in ((MAG_RAW_REF_LOW_UT, 28.0), (120.0, 2000.0)):
            cx, cy, cz = _apply_magnetic_magnitude_curve(raw_ut, 0.0, 0.0)
            corrected_ut = math.sqrt(cx*cx + cy*cy + cz*cz)
            if abs(corrected_ut - expected_ut) > 0.001:
                failures.append(
                    f"channel 1 curve maps {raw_ut:.1f} unit to {corrected_ut:.3f} unit, not {expected_ut:.1f} unit"
                )
        provider_cases = (
            ("sk" + "-ant-" + "example-credential", "anthropic"),
            ("sk" + "-proj-" + "example-credential", "openai"),
            ("xai" + "-example-credential", "xai"),
            ("gsk" + "_example_credential", "groq"),
            ("AI" + "zaExampleCredential", "gemini"),
            ("sk" + "-generic-example-credential", "unknown"),
        )
        for fake_key, expected_provider in provider_cases:
            actual_provider = _key_provider(fake_key)
            if actual_provider != expected_provider:
                failures.append(
                    f"provider routing mapped {expected_provider} fixture to {actual_provider}"
                )
        if not all(heading in EMI_ANALYST_SYSTEM for heading in EMI_REQUIRED_HEADINGS):
            failures.append('interference analyst prompt lost a required heading')
        complete_fixture = "\n".join(EMI_REQUIRED_HEADINGS) + "\ncomplete"
        if _emi_missing_headings(complete_fixture):
            failures.append('interference heading validator rejected a complete response')
        if MANUAL_API_KEYS:
            failures.append("distributable source contains manual API-key entries")
        if not 5.0 <= AI_REQUEST_TIMEOUT <= 120.0:
            failures.append("AI provider timeout is outside its bounded range")
        source_text = Path(__file__).read_text(encoding="utf-8")
        if re.search(r'"key"\s*:\s*"[^"\n]{16,}"', source_text):
            failures.append("distributable source appears to contain an embedded API key")
    except Exception as exc:
        failures.append(f"telemetry/interference software checks: {exc}")

    # Phone contract: the instrument is a fixed landscape view of the same 1180 px
    # desktop composition, with no portrait layout. Either the browser locks the
    # orientation or the page is rotated a quarter turn; nothing reflows between the
    # two. Mobile data timers yield to the fixed manual-refresh control.
    for marker in (
        "phone-desktop", "force-landscape", "requestLandscapeLock",
        'Text', "/manifest.webmanifest",
    ):
        if marker not in app.index_string:
            failures.append(f"fixed-landscape phone bootstrap is missing {marker}")
    if "phone-portrait" in app.index_string or "phone-portrait" in GLOBAL_CSS:
        failures.append("a portrait phone layout has reappeared; the view is landscape only")
    layout_markup = str(app.layout)
    if "mobile-refresh-btn" not in layout_markup or "mobile-mode" not in layout_markup:
        failures.append("mobile manual-refresh control is missing from the permanent shell")
    if CFG_3D.get("plotGlPixelRatio") != 2:
        failures.append("3D WebGL pixel ratio is not set to the high-resolution 2x target")

    # Rendering contract: no page may ship an entry animation class, and every figure
    # must disable Plotly transitions.
    for name, page in pages.items():
        markup = str(page)
        if "page-enter" in markup:
            failures.append(f"{name} still carries the page-enter entry animation")
    for builder in (lambda: make_line_chart([1, 2, 3]), lambda: fig_gauge(30.0),
                    lambda: fig_3d_surface([(1.0, 2.0, 3.0)]), lambda: fig_archive(),
                    lambda: fig_3d_error_plane([(1.0, 2.0, 3.0)]),
                    lambda: fig_3d_dipole_field([(1.0, 2.0, 3.0)]),
                    lambda: fig_ef_b_correlation([1.0, 2.0], [10.0, 20.0]),
                    lambda: fig_rf_trend([1.0, 2.0])):
        layout = builder().layout
        if layout.transition.duration != 0:
            failures.append("a figure was built without transition duration 0")
            break
        if not layout.uirevision:
            failures.append("a figure was built without uirevision")
            break

    workers = [thread.name for thread in threading.enumerate() if thread.name.startswith("studio-")]
    if workers:
        failures.append(f"workers started during import: {workers}")

    try:
        client = server.test_client()
        for route in ("/", "/em", "/spectrum", "/mtdi", "/settings"):
            response = client.get(route)
            if response.status_code != 200:
                failures.append(f"route {route} returned HTTP {response.status_code}")
        compressed = client.get(
            "/_dash-layout", headers={"Accept-Encoding": "gzip"}
        )
        if compressed.status_code != 200:
            failures.append(f"Dash layout returned HTTP {compressed.status_code}")
        elif compressed.headers.get("Content-Encoding") != "gzip":
            failures.append('Dash layout did not use gzip for a phone/Channel 5 client')
        else:
            gzip.decompress(compressed.data)
        manifest_response = client.get("/manifest.webmanifest")
        manifest = manifest_response.get_json()
        if manifest_response.status_code != 200 or manifest.get("orientation") != "any":
            failures.append("installed-app manifest does not permit both phone orientations")
        system_response = client.get("/api/system")
        system_payload = system_response.get_json()
        if system_response.status_code != 200:
            failures.append(f"system API returned HTTP {system_response.status_code}")
        elif system_payload.get("ready") is not False:
            failures.append("system API claimed readiness before telemetry worker startup")
        elif system_payload.get("cpu", {}).get("usage_percent") is not None:
            failures.append("system API returned a fake startup CPU value")
        elif system_payload.get("cpu", {}).get("temperature_c") is not None:
            failures.append("system API returned a fake startup temperature")
    except Exception as exc:
        failures.append(f"route smoke test: {exc}")

    if failures:
        print("SELF-TEST FAILED (software/mock checks only)")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("SELF-TEST PASSED (software/mock checks only; no hardware was exercised)")
    return 0


def tinysa_hardware_check(start_hz, stop_hz, points, output_dir):
    """Conservative real-device diagnostic using text scans only."""
    report = {
        "created_at":time.time(), "candidates":[], "verified":False,
        "requested_range":{"start_hz":start_hz, "stop_hz":stop_hz, "points":points},
        "scanraw_enabled":False, "warnings":[], "error":None,
    }
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    tsa = None
    try:
        import serial
        candidates = _tsa_find_ports()
        report["candidates"] = candidates
        print("Serial candidates:")
        for candidate in candidates:
            print(f"  {candidate}")
        if not candidates:
            raise TinySAError("no TinySA serial candidates found")
        errors = []
        version = info = help_text = port = ""
        for candidate in candidates:
            trial = None
            try:
                trial = serial.Serial(candidate, TSA_BAUD, timeout=0.25, write_timeout=2)
                time.sleep(0.35)
                version = "\n".join(_tsa_reply_lines(_tsa_cmd(trial, "version", 5), "version"))
                info = "\n".join(_tsa_reply_lines(_tsa_cmd(trial, "info", 5), "info"))
                help_text = "\n".join(_tsa_reply_lines(_tsa_cmd(trial, "help", 7), "help"))
                if "tinysa" not in f"{version} {info} {help_text}".lower():
                    raise TinySAProtocolError("device did not identify as TinySA")
                tsa, port = trial, candidate
                break
            except Exception as exc:
                errors.append(f"{candidate}: {exc}")
                if trial:
                    trial.close()
        if tsa is None:
            raise TinySAError("verification failed: " + "; ".join(errors))
        report.update({"verified":True, "port":port, "version":version, "info":info})
        (destination / "help.txt").write_text(help_text, encoding="utf-8")
        print(f"Verified: {version.splitlines()[0] if version else 'TinySA'} on {port}")
        print(info)

        # A small first scan establishes parser and repeatability before the selected span.
        small_start, small_stop, small_points = 88_000_000, 108_000_000, 51
        scans = []
        for index in (1, 2):
            started = time.time()
            freqs, levels, raw, warnings = _tsa_scan(
                tsa, small_start, small_stop, small_points, timeout=30
            )
            duration = time.time() - started
            (destination / f"small_scan_{index}_raw.txt").write_text(raw, encoding="utf-8")
            csv_lines = ["frequency_hz,level_dbm"] + [
                f"{frequency:.6f},{level:.6f}"
                for frequency, level in zip(freqs, levels)
            ]
            (destination / f"small_scan_{index}.csv").write_text(
                "\n".join(csv_lines) + "\n", encoding="utf-8"
            )
            scans.append((freqs, levels, duration, warnings))
        if scans[0][0] != scans[1][0]:
            report["warnings"].append("repeat scans returned different frequency grids")
        differences = [abs(a-b) for a, b in zip(scans[0][1], scans[1][1])]
        report["small_scan"] = {
            "points":small_points,
            "duration_s":[scans[0][2], scans[1][2]],
            "mean_absolute_repeat_difference_db":(
                sum(differences)/len(differences) if differences else None
            ),
            "warnings":scans[0][3] + scans[1][3],
        }

        started = time.time()
        freqs, levels, raw, warnings = _tsa_scan(tsa, start_hz, stop_hz, points, timeout=120)
        duration = time.time() - started
        (destination / "selected_scan_raw.txt").write_text(raw, encoding="utf-8")
        (destination / "selected_scan.csv").write_text(
            "frequency_hz,level_dbm\n" + "\n".join(
                f"{frequency:.6f},{level:.6f}"
                for frequency, level in zip(freqs, levels)
            ) + "\n",
            encoding="utf-8",
        )
        report["selected_scan"] = {
            "returned_points":len(freqs), "duration_s":duration,
            "bin_width_hz":(freqs[-1]-freqs[0])/max(len(freqs)-1, 1),
            "warnings":warnings,
            "trusted":not warnings and statistics.median(levels) <= TSA_SANE_MAX_DBM,
        }
        if not report["selected_scan"]["trusted"]:
            report["warnings"].append(
                "selected scan is suspicious and has not been labelled valid"
            )
    except Exception as exc:
        report["error"] = str(exc)
        LOG.exception("TinySA hardware diagnostic failed")
    finally:
        if tsa:
            try:
                tsa.close()
            except Exception:
                LOG.exception("Diagnostic serial close failed")
        (destination / "diagnostic_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
        )
    print(f"Diagnostic report: {destination / 'diagnostic_report.json'}")
    return 0 if report["verified"] and report["error"] is None else 1


def system_hardware_check():
    """Verify the host is a host computer and that its real telemetry sources work."""
    if psutil is not None:
        psutil.cpu_percent(interval=None)
    samples = []
    errors = []
    for index in range(3):
        try:
            samples.append(_system_snapshot())
        except Exception as exc:
            errors.append(str(exc)[:180])
        if index < 2:
            time.sleep(0.55)
    latest = samples[-1] if samples else {}
    if not latest.get("raspberry_pi"):
        errors.append(f"host is not identified as a host computer ({latest.get('host_model', 'unknown')})")
    if not latest.get("temperature_available"):
        errors.append("no real host computer CPU-temperature source is available")
    temperature = latest.get("cpu_temp")
    if latest.get("temperature_available") and not (0.0 < float(temperature) < 125.0):
        errors.append(f"CPU temperature is outside the plausible range ({temperature})")
    if not latest.get("ram_total_mb"):
        errors.append("RAM telemetry is unavailable")
    if not latest.get("disk_total_gb"):
        errors.append("disk telemetry is unavailable")
    report = {
        "passed": not errors, "app_version": APP_VERSION,
        "samples_collected": len(samples), "host_model": latest.get("host_model"),
        "raspberry_pi": bool(latest.get("raspberry_pi")),
        "telemetry_source": latest.get("telemetry_source"),
        "cpu_usage_percent": latest.get("cpu_usage"),
        "cpu_temperature_c": temperature if latest.get("temperature_available") else None,
        "ram_total_mb": latest.get("ram_total_mb"),
        "disk_total_gb": latest.get("disk_total_gb"),
        "errors": errors,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="MTDI Studio instrument dashboard"
    )
    parser.add_argument(
        "--version", action="version", version=f"MTDI Studio {APP_VERSION}"
    )
    parser.add_argument("--host", default=os.environ.get("STUDIO_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("STUDIO_PORT", "8050")))
    parser.add_argument("--lan", action="store_true", help="bind 0.0.0.0 (the default; retained for compatibility)")
    parser.add_argument("--local-only", action="store_true", help="bind only to 127.0.0.1")
    parser.add_argument("--https", dest="https", action="store_true",
                        help="publish a browser-trusted HTTPS Quick Tunnel (default)")
    parser.add_argument("--no-https", dest="https", action="store_false",
                        help="disable the portable HTTPS tunnel and use local/LAN HTTP")
    parser.set_defaults(https=os.environ.get("STUDIO_HTTPS", "1").lower()
                        not in {"0", "false", "no", "off"})
    parser.add_argument("--verbose", action="store_true", help="enable detailed diagnostics in the log file")
    parser.add_argument("--log-csv", action="store_true",
                        help="append every sample from all three channels to a "
                             "per-session CSV (see --csv-dir)")
    parser.add_argument("--csv-dir",
                        default=os.environ.get("STUDIO_CSV_DIR",
                                               str(Path.home() / "studio-sessions")),
                        help="directory for per-session CSV logs")
    parser.add_argument("--location", default="",
                        help="location label recorded in the CSV metadata header")
    parser.add_argument("--source-label", default="",
                        help="label for the source under test (e.g. 'kettle', 'ambient')")
    parser.add_argument("--distance-cm", default="",
                        help='distance from source to source, in centimetres')
    parser.add_argument("--operator-notes", default="",
                        help="free-text note recorded in the CSV metadata header")
    parser.add_argument("--qr", action="store_true",
                        help="print this host's address and QR code, then exit")
    parser.add_argument("--self-test", action="store_true", help="run software/mock tests and exit")
    parser.add_argument("--system-check", action="store_true",
                        help="verify real host computer host telemetry and exit")
    parser.add_argument("--hash-password", action="store_true", help="prompt for a password and print a PBKDF2 hash")
    parser.add_argument("--tinysa-check", action="store_true", help="run the real-hardware text-scan diagnostic and exit")
    parser.add_argument("--check-start-hz", type=int, default=88_000_000)
    parser.add_argument("--check-stop-hz", type=int, default=108_000_000)
    parser.add_argument("--check-points", type=int, default=101)
    parser.add_argument("--check-output", default=f"tinysa_diagnostic_{time.strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--log-level", default=os.environ.get("STUDIO_LOG_LEVEL", "INFO"))
    parser.add_argument(
        "--log-file",
        default=os.environ.get(
            "STUDIO_LOG_FILE",
            str(Path.home() / ".mtdi-studio" / "studio.log"),
        ),
        help="rotating diagnostic log (default: ~/.mtdi-studio/studio.log)",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be 1..65535")
    if not 2 <= args.check_points <= 290:
        parser.error("--check-points must be 2..290")
    if args.check_start_hz < 0 or args.check_stop_hz <= args.check_start_hz:
        parser.error("hardware-check range must satisfy 0 <= start < stop")
    return args


def print_access_code(port=None):
    """Print the LAN address and a scannable QR code for this host.

    Used by --qr. The same block is printed at startup, but a systemd service's
    stdout goes to the journal, so on this host it is only ever visible through
    `journalctl -u mtdi-studio`. This makes it available from any terminal.
    """
    import socket
    port = RUNTIME["port"] if port is None else port
    address = _local_ip()
    url = f"http://{address}:{port}"
    print(f"MTDI Studio {APP_VERSION}", flush=True)
    print(f"LAN {url}", flush=True)
    print(f"Hostname http://{socket.gethostname().split('.')[0]}.local:{port}", flush=True)
    try:
        import qrcode
        code = qrcode.QRCode(border=1, error_correction=qrcode.constants.ERROR_CORRECT_L)
        code.add_data(url)
        code.make(fit=True)
        print("Scan to open on a phone:", flush=True)
        code.print_ascii(invert=True)
        os.sys.stdout.flush()
    except Exception as exc:
        print(f"QR unavailable ({exc}); install with: python3 -m pip install qrcode", flush=True)
        return 1
    return 0


def main(argv=None):
    args = parse_args(argv)
    # Keep successful terminal output clean: the launcher prints only the URL.
    _configure_logging(args.log_level, args.log_file or None, console=False)
    if args.hash_password:
        import getpass
        first = getpass.getpass("Password: ")
        second = getpass.getpass("Confirm password: ")
        if not first or first != second:
            print("Passwords are empty or do not match", file=os.sys.stderr)
            return 2
        print(hash_password(first))
        return 0
    if args.qr:
        # The QR code has always been printed at startup, but under systemd that
        # goes to the journal, not to whatever terminal is open - which is why it
        # looked like it had stopped being generated. This prints it on demand.
        RUNTIME["port"] = args.port
        print_access_code()
        return 0
    if args.self_test:
        return run_self_test()
    if args.system_check:
        return system_hardware_check()
    if args.tinysa_check:
        return tinysa_hardware_check(
            args.check_start_hz, args.check_stop_hz,
            args.check_points, args.check_output,
        )


    if args.log_csv:
        CSV_LOG.enabled = True
        CSV_LOG.directory = Path(args.csv_dir).expanduser()
        CSV_LOG.metadata = {
            "started_unix": time.time(),
            "location": args.location or None,
            "source_label": args.source_label or None,
            "distance_cm": args.distance_cm or None,
            "operator_notes": args.operator_notes or None,
            # Recorded so a simulated run can never be mistaken for measured data
            # once the CSV is separated from the terminal it was launched in.
            "data_source": "SIMULATED (--demo)" if RUNTIME["demo"] else "hardware",
        }
    host = "127.0.0.1" if args.https or args.local_only else ("0.0.0.0" if args.lan else args.host)
    RUNTIME["host"] = host
    RUNTIME["port"] = args.port
    RUNTIME["public_tunnel"] = bool(args.https)
    # Public HTTPS always uses the persistent high-entropy browser-establishing
    # token unless the operator configured Basic authentication instead.
    RUNTIME["access_token"] = _persistent_access_token() if args.https else None
    open_url = _dashboard_url(host, args.port)
    portable_url_path = Path.home() / ".config" / "mtdi-studio" / "public_url"

    process_lock = ApplicationLock()
    try:
        process_lock.acquire()
    except RuntimeError:
        # The dashboard is already available. Re-running the command should be a
        # useful shortcut: show its clean link and QR, then remain attached as a
        # terminal monitor instead of appearing to start and instantly close.
        if args.https:
            stored_url = _existing_public_https_url()
            if stored_url:
                open_url = stored_url
        _print_access_link(open_url)
        print("\nMTDI Studio is already running. This terminal is now attached.")
        print("Press Ctrl+C to close this monitor; the dashboard will keep running.\n")
        try:
            while True:
                owner_text = process_lock.path.read_text(encoding="utf-8").strip()
                owner_pid = int(owner_text)
                os.kill(owner_pid, 0)
                time.sleep(1.0)
        except KeyboardInterrupt:
            return 0
        except (FileNotFoundError, ProcessLookupError, PermissionError, ValueError):
            print("The running dashboard process has stopped.")
        return 0

    from werkzeug.serving import WSGIRequestHandler, make_server

    class QuietRequestHandler(WSGIRequestHandler):
        """Send request diagnostics to the log without cluttering the terminal."""

        def log(self, log_type, message, *args):
            level = logging.ERROR if log_type == "error" else logging.DEBUG
            LOG.log(level, "HTTP " + message, *args)

    tunnel_process = None
    try:
        httpd = make_server(
            host,
            args.port,
            server,
            threaded=True,
            request_handler=QuietRequestHandler,
        )
    except Exception:
        process_lock.close()
        raise
    httpd.timeout = 0.5

    def request_shutdown(signum, _frame):
        LOG.info("Received signal %s; stopping", signum)
        STOP_EVENT.set()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    LIFECYCLE.start()
    if args.https:
        try:
            tunnel_process, public_base = _start_portable_https_tunnel(args.port)
            open_url = (
                public_base + "/?access=" +
                urllib.parse.quote(RUNTIME["access_token"], safe="")
            )
            portable_url_path.parent.mkdir(parents=True, exist_ok=True)
            portable_url_path.write_text(open_url, encoding="utf-8")
            portable_url_path.chmod(0o600)
        except Exception:
            httpd.server_close()
            LIFECYCLE.stop()
            process_lock.close()
            raise
    _print_access_link(open_url)
    try:
        while not STOP_EVENT.is_set():
            httpd.handle_request()
    finally:
        if tunnel_process is not None:
            tunnel_process.terminate()
            try:
                tunnel_process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                tunnel_process.kill()
        httpd.server_close()
        LIFECYCLE.stop()
        process_lock.close()
    return 0





# ── MTDI 2.0 · D4 analysis engine (pattern matched blocks on every page) ─────────────
from .d4 import validation_stats, sensor_error, uncertainty  # noqa: E402


def _d4_runtime():
    import importlib
    return getattr(importlib.import_module("studio.common"), "INSTRUMENT_RUNTIME", None)


def _d4_kv(rows):
    return html.Table([html.Tbody([html.Tr([html.Td(k, className="d4-k"), html.Td(v, className="d4-v")]) for k, v in rows])], className="d4-table")


def _d4_bar(label, value, z=None):
    v = 0 if value is None else max(0.0, min(100.0, float(value)))
    return html.Div([html.Span(label, className="d4-bar-label"), html.Div(html.I(style={"width": f"{v:.1f}%"}), className="d4-bar"),
                     html.Span("—" if value is None else f"{v:.0f}%", className="d4-bar-val"),
                     html.Span("" if z is None else f"z {z:+.1f}σ", className="d4-bar-z")], className="d4-bar-row")


def _d4_empty(height=200, text=""):
    fig = go.Figure()
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=height, margin=dict(l=0, r=0, t=8, b=0),
                      xaxis=dict(visible=False), yaxis=dict(visible=False),
                      annotations=[dict(text=text, x=.5, y=.5, xref="paper", yref="paper", showarrow=False, font=dict(color=SUBTEXT, size=11))] if text else [])
    return fig


def _mains_rows(m, label):
    if not m:
        return [(label, 'Text')]
    if m.get("error"):
        return [(label, m["error"])]
    return [(f"{label} sample rate", f"{m.get('fs')} Hz · Nyquist {m.get('nyquist_hz')} Hz · resolution {m.get('resolution_hz')} Hz"),
            ("Fundamental", f"{m['fundamental_hz']} Hz" if m.get("fundamental_detected") else f"not detected above the noise (dominant {m.get('dominant_hz')} Hz)"),
            ('Text', f"{m['thd_pct']} %" if m.get("thd_pct") is not None else "—"),
            ("Harmonics", ", ".join(f"{h['hz']} Hz ({h['rel_db']} dB)" for h in m.get("harmonics", []) if h.get("present")) or "none above the noise"),
            ('Text', ", ".join(f"{p['hz']} Hz" for p in m.get("other_peaks", [])[:4]) or "none"),
            ("Window", f"{m.get('contiguous_s') or ''} s · {m.get('samples')} samples" + (f" · {m['note']}" if m.get("note") else ""))]


def _mains_fig(m, height=230):
    sp = (m or {}).get("spectrum") or {}
    if not sp.get("hz"):
        return _d4_empty(height, (m or {}).get("error") or "waiting for samples")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sp["hz"], y=sp["amp"], mode="lines", line=dict(color="#00e5ff", width=1.2), hovertemplate="%{x:.1f} Hz · %{y:.4f}<extra></extra>"))
    for h in m.get("harmonics", []):
        if h.get("present"):
            fig.add_vline(x=h["hz"], line=dict(color="rgba(255,171,64,.5)", width=1, dash="dot"))
    if m.get("fundamental_detected"):
        fig.add_vline(x=m["fundamental_hz"], line=dict(color="#00e676", width=1))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=height, margin=dict(l=0, r=0, t=6, b=0),
                      xaxis=dict(title='Title', tickfont=dict(size=9), showgrid=False, range=[0, min(450, (m.get("nyquist_hz") or 450))]),
                      yaxis=dict(type="log", tickfont=dict(size=9), gridcolor="rgba(255,255,255,.06)"), transition=NO_TRANSITION)
    return fig


def _d4_render(kind, d, rt, where):
    """Children for one block kind from the live packet."""
    sim = " · SIMULATED" if d.get("simulated") else ""
    sc = d.get("scores", {}); z = d.get("z", {}); cfg = rt.d4.config
    if kind == "headline":
        mt, cf, cs = d.get("mtdi"), d.get("confidence"), d.get("consensus")
        ev = d.get("events") or []
        return [html.Div([html.Div('LABEL', className="d4-big-k"), html.Div("—" if mt is None else f"{mt:.0f}", className="d4-big-v")], className="d4-big"),
                html.Div([html.Div("CONFIDENCE", className="d4-big-k"), html.Div("—" if cf is None else f"{cf:.0f}%", className="d4-big-v")], className="d4-big"),
                html.Div([html.Div('LABEL', className="d4-big-k"), html.Div("—" if cs is None else f"{cs:.0f}%", className="d4-big-v")], className="d4-big"),
                html.Div([html.Div('LABEL', className="d4-big-k"), html.Div(("#%05d OPEN" % ev[0]["id"]) if ev and ev[0].get("open") else 'Text', className="d4-big-v small")], className="d4-big"),
                html.Div(f"weights {' · '.join(f'{k} {v:.2f}' for k, v in d['weights'].items())} · engine {rt.d4.compute_seconds or 0} s per pass{sim}", className="validation-subcopy d4-weights")]
    if kind == "consensus":
        cs = d.get("consensus")
        return [_d4_bar("Channel 3", sc.get("rf"), z.get("rf")), _d4_bar("Channel 2", sc.get("electric"), z.get("electric")), _d4_bar("Channel 1", sc.get("magnetic"), z.get("magnetic")),
                _d4_bar("Transient", sc.get("transient")),
                html.Div(f"Cross-source agreement: {'—' if cs is None else f'{cs:.0f}%'} · MTDI 2.0 {d.get('mtdi')} · contributions " + ", ".join(f"{k} {v}" for k, v in (d.get("contributions") or {}).items()), className="validation-subcopy", style={"marginTop": "6px"})]
    if kind == "confidence":
        cf = d.get("confidence")
        # The card's claim is that the number can be taken apart, and the engine already
        # publishes the weights behind it - they were simply never shown, the way the
        # MTDI weights are shown under the headline. Heaviest factor first.
        cw = d.get("confidence_weights") or {}
        labels = {"snr": "signal to noise", "agreement": 'source agreement',
                  "baseline_deviation": "deviation from baseline",
                  "repeatability": "repeatability", "calibration": "calibration health"}
        parts = [f"{labels.get(k, k)} {v:.2f}"
                 for k, v in sorted(cw.items(), key=lambda kv: -kv[1])]
        weights_line = ("weights " + " · ".join(parts) + f" · sum {sum(cw.values()):.2f}") if cw else ""
        return [html.Div("—" if cf is None else f"Detection confidence: {cf:.0f}%", className="d4-line"), html.Ul([html.Li(f) for f in d.get("confidence_factors", [])], className="d4-list"),
                html.Div(weights_line, className="validation-subcopy") if weights_line else None,
                html.Div('Subtext ' + ("—" if d.get("repeatability") is None else f"{d['repeatability']*100:.0f}%"), className="validation-subcopy")]
    if kind == "power":
        # The Window row above says how long the analysed block was; state how the
        # uninterrupted E-field block is obtained.
        burst = d.get("auto_burst_s") or 0
        burst_note = (f"Contiguous capture: an uninterrupted block is requested automatically every "
                      f"{burst:.0f} s so the FFT always receives a continuous sample window."
                      if burst else "")
        return [_d4_kv(_mains_rows(d.get("mains"), 'Label')),
                html.Div(burst_note, className="validation-subcopy") if burst_note else None]
    if kind == "power_magnetic":
        mm = d.get("mains_magnetic") or {}
        return [_d4_kv(_mains_rows(mm, 'Label')), html.Div(f"ODR configured {cfg.get('mag_odr_hz')} Hz · measured {d.get('magnetic_rate_hz')} Hz", className="validation-subcopy")]
    if kind == "power_network":
        pn = d.get("power_network") or {}
        rows = [(k, (f"{v.get('fundamental_hz')} Hz · THD {v.get('thd_pct')} % · even {v.get('even_amp')} / odd {v.get('odd_amp')} · harmonics {v.get('harmonics')}" if v.get("present") else v.get("note", "—"))) for k, v in (pn.get("channels") or {}).items()]
        return [_d4_kv(rows), html.Ul([html.Li(f) for f in pn.get("findings", [])], className="d4-list"),
                html.Div([html.Div("⚠ " + a, className="d4-line") for a in pn.get("abnormal", [])] or [html.Div('Subtext', className="validation-subcopy")])]
    if kind == "rf":
        r = d.get("rf") or {}
        if r.get("error"):
            return [html.Div(r["error"], className="validation-subcopy")]
        return [_d4_kv([('Text', f"{_freq_label(r['primary_peak_hz'])} · {r['primary_peak_dbm']} unit"), ('Text', f"{r['noise_floor_dbm']} unit (MAD {r['noise_mad_db']} dB)"), ("SNR", f"{r['snr_db']} dB"),
                        ('Text', _freq_label(r["occupied_bandwidth_hz"]) if r.get("occupied_bandwidth_hz") else "—"), ("Occupancy", f"{r['occupancy_pct']} % of bins above floor + threshold"),
                        ('Text', f"{r['interference_islands']} islands · {r['interference_density_per_100mhz']} per 100 MHz"),
                        ('Text', ", ".join(f"{h['order']}× {_freq_label(h['hz'])}" for h in r.get("harmonics_of_primary", [])) or "none"),
                        ('Text', ", ".join(f"{_freq_label(p['hz'])} ({p['level_dbm']})" for p in r.get("peaks", [])[:5]) or "none"),
                        ('Text', ", ".join(_freq_label(p["hz"]) for p in r.get("unexpected", [])) or "none")]),
                html.Div(r.get("band_note", ""), className="d4-line"), html.Div(('Subtext' if r.get("trusted") else 'Subtext') + f" · {r.get('status') or ''}", className="validation-subcopy")]
    if kind == "calibration":
        lc = d.get("last_calibration")
        if not lc:
            return [html.Div('Subtext', className="validation-subcopy"),
                    html.Div(f"Active profile: {cfg.get('source')} · offsets {cfg.get('mag_offsets')} unit · quality {cfg.get('mag_calibration_quality')}", className="validation-subcopy")]
        o, s_ = lc["offsets_ut"], lc["scale"]
        return [html.Pre(f"Magnetic Calibration{'  (SIMULATED)' if lc.get('simulated') else ''}\nX offset: {o[0]:+.1f} unit\nY offset: {o[1]:+.1f} unit\nZ offset: {o[2]:+.1f} unit\n\nScale:\nX = {s_[0]:.3f}\nY = {s_[1]:.3f}\nZ = {s_[2]:.3f}\n\n"
                         f"Axis misalignment: {lc['misalignment_deg']}°\nField magnitude: {lc['field_magnitude_ut']} unit\nSphericity residual: {lc['residual_before_pct']} % → {lc['residual_after_pct']} %\nCoverage: {lc['coverage']} %\nCalibration quality: {lc['quality']} %\nSamples: {lc['samples']} over {lc.get('window_s')} s", className="d4-pre"),
                html.Pre(json.dumps({"x_offset": o[0], "y_offset": o[1], "z_offset": o[2], "soft_iron": lc["soft_iron_matrix"]}, separators=(",", ":")), className="d4-pre small")]
    if kind == "calhealth":
        ch = d.get("calibration_health") or {}
        return [_d4_kv([("Status", str(ch.get("status", "—")).upper()), ('Text', f"{ch['quality']} %" if ch.get("quality") is not None else "—"), ('Text', f"{ch.get('magnitude_spread_pct')} %"),
                        ('Text', f"{ch.get('offset_drift_ut')} unit"), ("Noise", f"{(d.get('noise_magnetic') or {}).get('rms')} unit RMS"), ("Recalibration", ch.get("recalibration", ch.get("text", "—"))), ('Text', cfg.get("source") or "defaults")])]
    if kind == "transients":
        tr = d.get("transients") or {}; ev = tr.get("events") or []
        return [_d4_kv([('Text', f"{tr.get('count', 0)} in {tr.get('window_s') or 0} s"), ("Threshold", f"{tr.get('threshold')} (baseline {tr.get('baseline')}, MAD {tr.get('noise_mad')})"), ("Repetition", f"{tr['repetition_hz']} Hz" if tr.get("repetition_hz") else "—")]),
                html.Div([html.Div(f"Peak {e['peak']} · {e['duration_ms']} ms · rise {e['rise_ms']} ms · fall {e['fall_ms']} ms · energy {e['energy']}", className="validation-subcopy") for e in ev[-4:]])]
    if kind == "correlation":
        return [_d4_kv([(k.replace("_", " / "), f"r = {v['r']}  ·  {v['text']}" if v.get("r") is not None else v["text"]) for k, v in (d.get("correlation") or {}).items()])]
    if kind == "baseline":
        bm = d.get("baseline_methods") or {}
        if not bm:
            return [html.Div('Subtext', className="validation-subcopy")]
        return [_d4_kv([(k, f"final {v['final']} · tracking RMSE {v['tracking_rmse']} · max excursion {v['max_excursion']}") for k, v in (bm.get("methods") or {}).items()]
                       + [('Text', bm.get("most_disturbance_resistant", "—")), ('Text', f"{cfg.get('baseline_method')} (α {cfg.get('baseline_alpha')})")])]
    if kind == "repeat":
        rep = d.get("repeat_run") or {}
        if not rep:
            return [_d4_kv([("Status", 'Text'),
                            ('Text', 'Paragraph. Enter your text here.')])]
        if rep.get("running"):
            return [_d4_kv([("Status", f"running — reading {rep.get('done', 0)} of {rep.get('runs')} "
                                       f"on {rep.get('label')}"),
                            ('Text', f"a fresh {rep.get('window_s')} s window of live data"),
                            ('Text', 'Paragraph. Enter your text here.')])]
        if rep.get("error"):
            return [_d4_kv([("Status", f"failed — {rep['error']}")])]
        r = rep.get("result") or {}
        if r.get("error"):
            return [_d4_kv([("Status", f"not enough readings — {r['error']}")])]
        rows = [("Channel", r.get("channel", "—")),
                ("Readings", f"{r.get('n')} x {r.get('window_s')} s windows"
                             + (f" ({r['skipped']} skipped for want of samples)" if r.get("skipped") else "")),
                ("Result", f"{r.get('text')}"),
                ("Spread", f"σ {r.get('sd')} {r.get('unit')} · range {r.get('range')} · "
                           f"min {r.get('min')} · max {r.get('max')}"),
                ('Text', (f"{r.get('rsd_pct')} % — {r.get('verdict')}"
                                         if r.get("rsd_pct") is not None else "mean too near zero to state")),
                ("Method", r.get("basis", "—")),
                ("Conditions", r.get("conditions", "—")),
                ('Text', 'Paragraph. Enter your text here.')]
        return [_d4_kv(rows)]
    if kind == "limits":
        lim = d.get("detection_limits") or {}
        rows = []
        for key, label in (("magnetic", 'Channel 1'), ("electric", 'Text')):
            v = lim.get(key) or {}
            if v.get("error") or not v.get("lod"):
                rows.append((label, v.get("error") or "not measured yet"))
                continue
            unit = v.get("unit", "")
            text = (f"smallest detectable change {v['lod']} {unit} (3σ) · "
                    f"smallest quantifiable {v['loq']} {unit} (10σ) · σ = {v['sigma']} {unit}"
                    f" from {v.get('samples')} samples")
            if v.get("nsd_per_sqrt_hz"):
                text += f" · {v['nsd_per_sqrt_hz']} {unit}/√Hz"
            rows.append((label, text))
        rows.append(("Method", 'Paragraph. Enter your text here.'))
        return [_d4_kv(rows)]
    if kind == "exposure":
        exp = d.get("exposure") or {}
        rows = []
        for ch in exp.get("channels") or []:
            if ch.get("quantitative"):
                text = (f"{ch['value']} {ch['unit']} · {ch['pct_of_public']} % of the "
                        f"{ch['public_limit']:g} {ch['unit']} public reference level · {ch['reading']}")
                if ch.get("note"):
                    text += f" · {ch['note']}"
            else:
                text = ch.get("reading") or "—"
            rows.append((ch.get("channel", "—"), text))
        if exp.get("source"):
            rows.append(("Reference", exp["source"]))
            rows.append(("Compared", exp.get("basis", "—")))
            rows.append(('Text', exp.get("caveat", "—")))
        return [_d4_kv(rows or [("Exposure", 'Text')])]
    if kind == "noise":
        ne, nm = d.get("noise_electric") or {}, d.get("noise_magnetic") or {}
        return [_d4_kv([('Text', f"RMS {ne.get('rms')} · peak {ne.get('peak')} · σ {ne.get('std')} · NSD {ne.get('nsd_per_sqrt_hz')} /√Hz @ {ne.get('fs')} Hz" if ne else "—"),
                        ('Text', f"RMS {nm.get('rms')} · peak {nm.get('peak')} · σ {nm.get('std')} · NSD {nm.get('nsd_per_sqrt_hz')} unit/√Hz @ {nm.get('fs')} Hz" if nm else "—")])]
    if kind == "fingerprint":
        fp = d.get("fingerprint") or {}; ref = d.get("fingerprint_reference"); chg = d.get("fingerprint_change") or {}
        return [_d4_kv([('Text', f"{fp.get('magnetic_ut')} unit"), ('Text', f"{fp.get('electric')}"), ('Text', f"{fp.get('rf_floor_dbm')} unit · peak {_freq_label(fp['rf_peak_hz']) if fp.get('rf_peak_hz') else '—'}"),
                        ('Reference', f"{(fp.get('mains') or {}).get('fundamental_hz')} Hz · THD {(fp.get('mains') or {}).get('thd_pct')} %"), ('Text', f"{fp.get('transient_rate_per_min')} /min")]),
                html.Div(('Text' if not ref else f"Environmental change vs reference: CH 3 floor {chg.get('rf_floor_db'):+} dB · channel 1 {chg.get('magnetic_pct')} % · channel 2 {chg.get('electric_pct')} % · transients {chg.get('transient_rate_pct')} %"), className="d4-line")]
    if kind == "trend":
        t = d.get("trend"); hist = d.get("history") or {}
        rows = [('TEXT', f"{t['minutes']} min window · slope {t['mtdi_per_min']:+} per min · {t['text']}")] if t else [('TEXT', "collecting")]
        for key in ("magnetometer", "efield", "rf"):
            h = hist.get(key)
            if h:
                rows.append((key, " · ".join(f"{w['label']}: {w.get('text')}" + (f" ({w['change_pct']:+} %)" if w.get("change_pct") is not None else "") for w in h.get("windows", [])) + f" · drift {h.get('drift_per_min')}/min · {(h.get('periodic') or {}).get('text', '')}"))
        if hist.get("error"):
            rows.append(("archive", hist["error"]))
        return [_d4_kv(rows)]
    if kind == "events":
        evs = d.get("events") or []
        return [html.Div([html.B(f"EVENT #{e['id']:05d} · {e['time']}" + (' TEXT' if e.get("open") else f" · {e.get('duration_s')} s")),
                          html.Div(f"CH 3 {e['rf']} · Channel 1 {e['magnetic']} · Channel 2 {e['electric']} · MTDI {e['mtdi']} · confidence {e['confidence']}%", className="validation-subcopy")], className="d4-event") for e in evs[:8]] \
            or [html.Div('Subtext', className="validation-subcopy")]
    if kind == "config":
        return [_d4_kv([("Source", cfg.get("source")), ('Text', str(cfg.get("mag_offsets"))), ("Scale", str(cfg.get("mag_scale"))), ('Text', f"{cfg.get('mag_calibration_quality')} %" if cfg.get("mag_calibration_quality") is not None else "—"),
                        ('Text', str(cfg.get("mtdi_weights"))), ("Thresholds", f"CH 3 {cfg.get('rf_threshold_db')} dB · anomaly {cfg.get('anomaly_sigma')}σ · event {cfg.get('event_mtdi')} · transient {cfg.get('transient_threshold')}×MAD"),
                        ("Baseline", f"{cfg.get('baseline_method')} α={cfg.get('baseline_alpha')}"), ('Text', f"{cfg.get('mag_odr_hz')} Hz"),
                        ("Filter", f"{cfg['filter'].get('type')} order {cfg['filter'].get('order')} cutoff {cfg['filter'].get('cutoff_hz')} Hz" + (" · coefficients loaded" if cfg["filter"].get("b") else " · not designed yet") + (' · APPLIED to channel 1 magnitude' if cfg["filter"].get("apply") else " · not applied")),
                        ('Text', str(cfg.get("d3_reference") or "not entered")), ("Error", d.get("config_error") or "none")])]
    if kind == "references":
        refs = d.get("references") or {}; simr = d.get("similarity") or []
        rows = [(k, f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(v.get('recorded_at') or 0))} · {v.get('note') or ''}" + (" · SIMULATED" if v.get("simulated") else "")) for k, v in refs.items()]
        return [_d4_kv(rows) if rows else html.Div('Subtext', className="validation-subcopy"),
                html.Div(('Text ' + ", ".join(f"{q['name']} · similarity {q['similarity_pct']} % ({q['features_compared']} features)" for q in simr[:3])) if simr else "", className="d4-line"),
                html.Div('Subtext ' + ", ".join(f"{k} {v}" for k, v in (d.get("features") or {}).items() if v is not None), className="validation-subcopy")]
    if kind == "classifier":
        c = d.get("classifier") or {}
        if not c.get("trained_at"):
            return [html.Div(c.get("note", "not trained"), className="d4-line"), html.Div(f"Labelled trials by source: {c.get('labelled') or {}}", className="validation-subcopy")]
        return [html.Div(f"Trained {time.strftime('%Y-%m-%d %H:%M', time.localtime(c['trained_at']))} on {c.get('n')} trials · classes {c.get('classes')}", className="validation-subcopy"),
                _d4_kv([(q["label"], f"{q['probability_pct']} %") for q in c.get("prediction", [])]), html.Div('Subtext', className="validation-subcopy")]
    if kind == "validation":
        try:
            st = _d4_trial_stats(rt)
        except Exception as exc:
            return [html.Div(f"stats failed: {exc}", className="validation-subcopy")]
        ms, ds = st.get("measurements") or {}, st.get("detection") or {}
        rows = [("Trials", f"{d.get('trials_count', 0)} recorded")]
        if ms:
            rows += [("Values", f"n {ms['n']} · mean {ms['mean']} · median {ms['median']} · σ {ms['std']} · var {ms['variance']} · CV {ms['cv_pct']} %"), ('TEXT', f"{ms['ci95']}")]
        if ds:
            rows += [("Detection", f"rate {ds['detection_rate_pct']} % · false positives {ds['false_positive_rate_pct']} % · accuracy {ds['accuracy_pct']} % · precision {ds['precision_pct']} % · recall {ds['recall_pct']} % · F1 {ds['f1_pct']} % (n {ds['n']})")]
        cmp_rows = [html.Tr([html.Th('Label'), html.Th("D3"), html.Th("D4")])] + [html.Tr([html.Td(c["metric"]), html.Td("—" if c["d3"] is None else f"{c['d3']} {c['unit']}"), html.Td("—" if c["d4"] is None else f"{c['d4']} {c['unit']}")]) for c in st.get("comparison", [])]
        return [_d4_kv(rows), html.Div('Text', className="d4-line"), html.Table(cmp_rows, className="d4-table"),
                html.Div('Text', className="d4-line"), html.Ul([html.Li(r["text"]) for r in st.get("recommendations", [])], className="d4-list")]
    if kind == "uncertainty":
        st = _d4_trial_stats(rt)
        err, u = st.get("error"), st.get("uncertainty")
        if not err:
            return [html.Div('Subtext', className="validation-subcopy")]
        return [_d4_kv([("Pairs", err["pairs"]), ('Text', f"{err['mean_abs_error']}"), ('Text', f"{err['mean_pct_error']} %"), ("Bias", f"{err['bias']}"), ("RMSE", f"{err['rmse']}"),
                        ("Result", u["text"] if u else "—"), ("Budget", str(u["budget"]) if u else "—")])]
    return [html.Div('Subtext', className="validation-subcopy")]


def _d4_trial_stats(rt):
    trials = rt.d4.trials
    values = [t["value"] for t in trials if t.get("value") is not None]
    out = validation_stats(values, [(t["detected"], t["actual"]) for t in trials])
    refs = [(t["value"], t["reference"]) for t in trials if t.get("value") is not None and t.get("reference") is not None]
    if refs:
        out["error"] = sensor_error([v for v, _ in refs], [r for _, r in refs])
        if out.get("measurements"):
            out["uncertainty"] = uncertainty(out["measurements"]["mean"], 0.0, out["measurements"]["std"], (rt.d4.snapshot().get("noise_magnetic") or {}).get("rms") or 0.0, abs(out["error"]["bias"] or 0.0))
    d3 = rt.d4.config.get("d3_reference") or {}; ds = out.get("detection") or {}
    out["comparison"] = [{"metric": "Detection rate", "d3": d3.get("detection_rate_pct"), "d4": ds.get("detection_rate_pct"), "unit": "%"},
                         {"metric": "False positives", "d3": d3.get("false_positive_rate_pct"), "d4": ds.get("false_positive_rate_pct"), "unit": "%"},
                         {"metric": "Calibration error", "d3": d3.get("calibration_error_pct"), "d4": (out.get("error") or {}).get("mean_pct_error"), "unit": "%"},
                         {"metric": "MTDI accuracy", "d3": d3.get("mtdi_accuracy_pct"), "d4": ds.get("accuracy_pct"), "unit": "%"},
                         {"metric": "Analysis time", "d3": d3.get("analysis_time_s"), "d4": rt.d4.compute_seconds, "unit": "s"}]
    from .d4 import test_recommendations
    out["recommendations"] = test_recommendations(trials)
    return out


def _d4_graph(kind, d, rt):
    if kind == "power":
        return _mains_fig(d.get("mains"), 230)
    if kind == "repeat":
        rep = d.get("repeat_run") or {}
        live = {"readings": rep.get("readings") or []} if rep.get("running") else None
        if live and len(live["readings"]) >= 2:
            vals = live["readings"]
            mean = sum(vals) / len(vals)
            sd = (sum((v - mean) ** 2 for v in vals) / (len(vals) - 1)) ** 0.5
            live.update(mean=mean, sd=sd, unit=rep.get("unit"))
            return fig_repeatability(live, 300)
        return fig_repeatability(rep.get("result"), 300)
    if kind == "power_surface":
        return fig_mains_spectrogram((d.get("mains") or {}).get("spectrogram"), 460)
    if kind == "power_magnetic":
        return _mains_fig(d.get("mains_magnetic"), 200)
    if kind == "calibration":
        lc = d.get("last_calibration")
        if not lc or not lc.get("raw"):
            return _d4_empty(380, 'Paragraph. Enter your text here.')
        raw, cor = lc["raw"], lc["corrected"]
        fig = go.Figure()
        fig.add_trace(go.Scatter3d(x=[p[0] for p in raw], y=[p[1] for p in raw], z=[p[2] for p in raw], mode="markers", name='Label', marker=dict(size=2.2, color="#ff5252", opacity=.75)))
        fig.add_trace(go.Scatter3d(x=[p[0] for p in cor], y=[p[1] for p in cor], z=[p[2] for p in cor], mode="markers", name='Label', marker=dict(size=2.2, color="#00e5ff", opacity=.85)))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=380, margin=dict(l=0, r=0, t=8, b=0), legend=dict(orientation="h", y=1.02, font=dict(size=9)), uirevision="cal",
                          scene=dict(bgcolor="rgba(0,0,0,0)", xaxis=dict(title="X unit", gridcolor="rgba(255,255,255,.08)", backgroundcolor="rgba(0,0,0,0)"), yaxis=dict(title="Y unit", gridcolor="rgba(255,255,255,.08)", backgroundcolor="rgba(0,0,0,0)"),
                                     zaxis=dict(title="Z unit", gridcolor="rgba(255,255,255,.08)", backgroundcolor="rgba(0,0,0,0)"), aspectmode="data"))
        return fig
    if kind == "validation":
        trials = rt.d4.trials
        vals = [(i, t["value"]) for i, t in enumerate(trials) if t.get("value") is not None]
        if not vals:
            return _d4_empty(220, 'Text')
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[i for i, _ in vals], y=[v for _, v in vals], mode="lines+markers", line=dict(color="#00e5ff", width=1), name="value"))
        st = validation_stats([v for _, v in vals])
        ms = st.get("measurements")
        if ms:
            fig.add_hline(y=ms["mean"], line=dict(color="#ffab40", width=1))
            fig.add_hrect(y0=ms["ci95"][0], y1=ms["ci95"][1], fillcolor="rgba(255,171,64,.15)", line_width=0)
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=220, margin=dict(l=0, r=0, t=6, b=0), showlegend=False,
                          xaxis=dict(title="trial", tickfont=dict(size=9), showgrid=False), yaxis=dict(tickfont=dict(size=9), gridcolor="rgba(255,255,255,.06)"), transition=NO_TRANSITION)
        return fig
    return _d4_empty(200)


@app.callback(Output({"type": "d4", "block": ALL, "where": ALL}, "children"), Input("d4-tick", "n_intervals"), State({"type": "d4", "block": ALL, "where": ALL}, "id"))
def d4_blocks(_n, ids):
    if not ids:
        raise dash.exceptions.PreventUpdate
    rt = _d4_runtime()
    if rt is None:
        return [html.Div('Subtext', className="validation-subcopy") for _ in ids]
    d = rt.d4.snapshot()
    out = []
    for ident in ids:
        try:
            out.append(_d4_render(ident["block"], d, rt, ident["where"]))
        except Exception as exc:
            out.append(html.Div(f"{ident['block']}: {exc}", className="validation-subcopy"))
    return out


@app.callback(Output({"type": "d4g", "block": ALL, "where": ALL}, "figure"), Input("d4-tick", "n_intervals"), State({"type": "d4g", "block": ALL, "where": ALL}, "id"))
def d4_graphs(_n, ids):
    if not ids:
        raise dash.exceptions.PreventUpdate
    rt = _d4_runtime()
    if rt is None:
        return [_d4_empty() for _ in ids]
    d = rt.d4.snapshot()
    out = []
    for ident in ids:
        try:
            out.append(_d4_graph(ident["block"], d, rt))
        except Exception as exc:
            out.append(_d4_empty(200, str(exc)[:80]))
    return out


@app.callback(Output({"type": "d4status", "where": ALL, "card": ALL}, "children"),
              Input({"type": "d4btn", "action": ALL, "where": ALL}, "n_clicks"),
              State({"type": "d4in", "field": ALL, "where": ALL}, "value"), State({"type": "d4in", "field": ALL, "where": ALL}, "id"),
              State({"type": "d4status", "where": ALL, "card": ALL}, "id"), prevent_initial_call=True)
def d4_actions(clicks, values, in_ids, status_ids):
    trig = dash.callback_context.triggered_id
    if not trig or not any(clicks):
        raise dash.exceptions.PreventUpdate
    rt = _d4_runtime()
    where, action = trig["where"], trig["action"]
    fields = {i["field"]: v for i, v in zip(in_ids, values) if i["where"] == where}
    msg = ""
    try:
        if action in ("cal_fit", "cal_apply"):
            result, patch = rt.d4.calibrate_magnetometer(120)
            if result is None:
                msg = f"REJECTED · {patch}"
            elif action == "cal_apply":
                path = rt.d4.update_config(patch)
                rt.note("d4", f"channel 1 calibration applied: offsets {result['offsets_ut']} unit, quality {result['quality']} %")
                msg = f"Fit applied: offsets {result['offsets_ut']} unit · quality {result['quality']} % · written to {path}"
            else:
                msg = f"Fit done: offsets {result['offsets_ut']} unit · quality {result['quality']} % (not applied)"
        elif action == "burst":
            rt.d4.request_burst(3440, "efield"); msg = 'Burst requested: next Channel 2 block is 3440 contiguous samples'
        elif action == "repeat_start":
            def num(k, dflt):
                v = fields.get(k)
                return dflt if v in (None, "") else float(v)
            started = rt.d4.start_repeatability(fields.get("repeat_channel") or "magnetic",
                                                num("repeat_runs", 10), num("repeat_window", 3))
            msg = (f"Running: {started['runs']} readings of {started['window_s']:g} s on "
                   f"{started['label']} — about {started['eta_s']:g} s. Keep everything still.")
        elif action == "fingerprint":
            rt.d4.set_fingerprint_reference(); rt.note("d4", "environmental fingerprint reference taken"); msg = "Reference stored; later readings are compared against it"
        elif action == "ref_record":
            name = re.sub(r"[^A-Za-z0-9 _.\-]", "", fields.get("ref_name") or "")[:40].strip()
            if not name:
                msg = "REJECTED · enter a device name"
            else:
                rt.d4.record_reference(name, fields.get("ref_note") or ""); rt.note("d4", f"reference profile recorded: {name}"); msg = f"Recorded '{name}'"
        elif action == "ref_delete":
            name = (fields.get("ref_name") or "").strip()
            rt.d4.delete_reference(name); msg = f"Deleted '{name}'" if name else "REJECTED · enter the name to delete"
        elif action == "train":
            model, counts = rt.d4.train_model()
            msg = (f"Trained on {model['n']} trials: {', '.join(f'{k} {v}' for k, v in counts.items())}") if model else f"Not trained: needs 2 sources × 5 labelled trials (have {counts})"
        elif action == "trial_add":
            def num(k):
                v = fields.get(k)
                return None if v in (None, "") else float(v)
            row = rt.d4.add_trial({"distance_cm": num("trial_distance"), "source": fields.get("trial_source") or ("ambient" if fields.get("trial_actual") == "0" else "unknown"),
                                   "value": num("trial_value"), "reference": num("trial_reference"), "detected": fields.get("trial_detected", "1") == "1", "actual": fields.get("trial_actual", "1") == "1"})
            msg = f"Trial {len(rt.d4.trials)} recorded ({row['source']}, {row['distance_cm']} cm, MTDI {row['mtdi']})"
        elif action == "trial_clear":
            rt.d4.clear_trials(); msg = "Trial store cleared"
        elif action == "d3_save":
            def num(k):
                v = fields.get(k)
                return None if v in (None, "") else float(v)
            rt.d4.update_config({"d3_reference": {"detection_rate_pct": num("d3_detection"), "false_positive_rate_pct": num("d3_fp"), "calibration_error_pct": num("d3_cal"), "mtdi_accuracy_pct": num("d3_mtdi"), "analysis_time_s": num("d3_time")}})
            msg = "D3 reference saved to iv_config.json"
        else:
            msg = f"unknown action {action}"
    except Exception as exc:
        msg = f"REJECTED · {exc}"
    card = D4_ACTION_CARD.get(action, action)
    return [msg if i["where"] == where and i.get("card") == card else dash.no_update for i in status_ids]


# which card's status line a button reports to (the card is named after its first control)
D4_ACTION_CARD = {"cal_fit": "cal_fit", "cal_apply": "cal_fit", "burst": "burst",
                  "repeat_start": "repeat_channel",
                  "fingerprint": "fingerprint", "ref_record": "ref_name", "ref_delete": "ref_name", "train": "train",
                  "trial_add": "trial_add", "trial_clear": "trial_add", "d3_save": "d3_save"}


@app.callback(Output({"type": "d4status", "where": ALL, "card": ALL}, "children", allow_duplicate=True),
              Input({"type": "d4up", "where": ALL}, "contents"), State({"type": "d4up", "where": ALL}, "filename"), State({"type": "d4status", "where": ALL, "card": ALL}, "id"), prevent_initial_call=True)
def d4_config_upload_cb(contents, filenames, status_ids):
    trig = dash.callback_context.triggered_id
    if not trig:
        raise dash.exceptions.PreventUpdate
    where = trig["where"]
    idx = [i for i, c in enumerate(contents) if c]
    if not idx:
        raise dash.exceptions.PreventUpdate
    try:
        import base64
        payload = json.loads(base64.b64decode(contents[idx[0]].split(",", 1)[1]).decode("utf8"))
        rt = _d4_runtime(); path = rt.d4.update_config(payload)
        msg = f"REJECTED · {rt.d4.config_error}" if rt.d4.config_error else f"Loaded {filenames[idx[0]]} → {path}; reader reloaded"
        if not rt.d4.config_error:
            rt.note("d4", f"iv_config.json uploaded from {filenames[idx[0]]}")
    except Exception as exc:
        msg = f"REJECTED · {exc}"
    return [msg if i["where"] == where and i.get("card") == "config" else dash.no_update for i in status_ids]


# ════════════════════════════════════════════════════════
#  RTL-SDR TAB
# ════════════════════════════════════════════════════════
def _sdr_rows(peaks):
    if not peaks:
        return [html.Div('Subtext',
                         className="validation-subcopy", style={"padding":"10px 0"})]
    rows = [html.Div([html.Div('TEXT'), html.Div('TEXT'),
                      html.Div('TEXT', className="scan-hide-sm"),
                      html.Div('TEXT', className="scan-hide-sm")],
                     className="scan-row scan-head")]
    for peak in peaks:
        rows.append(html.Div([
            html.Div(_freq_label(peak["freq"]), className=_cls(CYAN)),
            html.Div(f"+{peak['over_floor_db']:.1f} dB", className=_cls(AMBER)),
            html.Div(f"{peak['level_dbfs']:.1f} dBFS", className="scan-hide-sm scan-dim"),
            html.Div(peak.get("band") or "no common allocation", className="scan-hide-sm scan-dim"),
        ], className="scan-row"))
    return rows


def _sdr_detail(snap):
    limits = snap.get("limits") or {}
    pairs = [
        ("Device", snap.get("device") or "not detected"),
        ("Tuner", snap.get("tuner") or "unknown"),
        ("Serial", snap.get("serial") or "—"),
        ('Text', f"{limits.get('rate_hz', 0)/1e6:.3f} MS/s complex"),
        ("Resolution", f"{limits.get('bin_hz', 0):.0f} Hz per bin"),
        ('Text', f"{snap.get('span_hz', 0)/1e6:.3f} MHz after edge trim"),
        ('Text', f"{limits.get('min_hz', 0)/1e6:.0f} – {limits.get('max_hz', 0)/1e6:.0f} MHz"),
        ("Gain", (f"{snap.get('gain_db')} dB, managed by the instrument"
                  if snap.get("gain_mode") == "auto" else f"{snap.get('gain_db')} dB, fixed")),
        ('Text', f"{snap.get('rms_fullscale', 0)*100:.1f}% of full scale RMS"),
        ("Duty", ("streaming; the tab is open" if snap.get("watched")
                  else "idle; opens this tab to stream. The receiver costs the sensor threads "
                       "time, so it does not run unwatched")),
        ("Capture", ("trusted" if snap.get("trusted")
                     else (snap.get("untrusted_reason") or "no capture yet"))),
        ('Text', f"{snap.get('bursts', 0)}"),
        ('Text', f"{snap.get('megabytes', 0):.1f} MB this session"),
        ('Text', f"{snap['capture_s']:.2f} s per burst" if snap.get("capture_s") else "—"),
        ('Text', ("none" if not snap.get("clipped")
                          else f"{snap.get('clip_fraction', 0)*100:.2f}% of samples at the rail")),
        ('Text', f"{snap.get('dc_offset', 0):.4f} of full scale (removed)"),
        ('Text', (f"{snap['papr_db']:.1f} dB within the burst"
                             if snap.get("papr_db") is not None
                             else "computed while this tab is open")),
        ('Text', (f"{snap['phase_offset_hz']:+,.0f} Hz from the phase slope"
                                       if snap.get("phase_offset_hz") is not None
                                       else "computed while this tab is open")),
    ]
    return [html.Div([html.Div(k), html.Div(v, className="scan-dim")], className="scan-row")
            for k, v in pairs]


@app.callback(
    Output("sdr-state","children"), Output("sdr-centre","children"), Output("sdr-peak","children"),
    Output("sdr-data","children"), Output("sdr-status","children"), Output("sdr-status","className"),
    Output("sdr-dot","className"), Output("sdr-live","figure"), Output("sdr-fall","figure"),
    Output("sdr-peaks","children"), Output("sdr-detail","children"), Output("sdr-sweep","figure"),
    Output("sdr-sweep-note","children"), Output("sdr-gain","options"),
    Output("sdr-terrain","figure"), Output("sdr-const","figure"), Output("sdr-iq3d","figure"),
    Output("sdr-env","figure"), Output("sdr-codes","figure"),
    Input("sdr-int","n_intervals"),
)
def update_sdr(_n):
    snap = sdr_snapshot(viewing=True)
    live = snap.get("present") and snap.get("last_rx")
    state = "LIVE" if live else ("OFFLINE" if snap.get("error") else "STARTING")
    centre = _freq_label(snap["centre_hz"]) if snap.get("centre_hz") else "—"
    if snap.get("peaks"):
        top = snap["peaks"][0]
        peak = f"{_freq_label(top['freq'])} +{top['over_floor_db']:.0f} dB"
    elif live:
        peak = "nothing above the floor"
    else:
        peak = "—"
    status = snap.get("error") or snap.get("status") or "Starting"
    if live and not snap.get("trusted") and snap.get("untrusted_reason"):
        status = "Untrusted: " + snap["untrusted_reason"]
        state = "OVERLOAD" if snap.get("clipped") else "CHECK"
    elif live and snap.get("gain_note"):
        status = f"{status}; {snap['gain_note']}"
    if live and snap.get("watched") and snap.get("age_s") is not None and snap["age_s"] > 20:
        status = f"{status}; last burst {snap['age_s']:.0f} s ago"
    if snap.get("sweep_running"):
        note = f"sweeping… {snap.get('sweep_progress', 0):.0f}%"
    elif snap.get("sweep"):
        done = snap["sweep"]
        note = (f"{done['slices']} slices · {_freq_label(done['start_hz'])} to "
                f"{_freq_label(done['stop_hz'])} · {done.get('note', '')}")
    else:
        note = ""
    gains = [{"label": "auto", "value": "auto"}] + \
            [{"label": f"{g:.1f} dB", "value": str(g)} for g in (snap.get("gains_db") or [])]
    return (state, centre, peak, f"{snap.get('megabytes', 0):.1f} MB",
            status, "online-text " + (_cls(CYAN) if live else "c-sub"),
            "online-dot" if live else "online-dot off",
            fig_sdr_slice(snap.get("freqs"), snap.get("levels_dbfs"), snap.get("peaks"),
                          snap.get("floor_dbfs")),
            fig_sdr_waterfall(snap.get("waterfall"), snap.get("waterfall_freqs"),
                              snap.get("waterfall_times")),
            _sdr_rows(snap.get("peaks")), _sdr_detail(snap),
            fig_sdr_sweep(snap.get("sweep")), note, gains,
            fig_sdr_terrain(snap.get("waterfall"), snap.get("waterfall_freqs"),
                            snap.get("waterfall_times")),
            fig_sdr_constellation(snap.get("iq_grid"), snap.get("iq_axis")),
            fig_sdr_iq_3d(snap.get("iq_i"), snap.get("iq_q"), snap.get("iq_dt_s")),
            fig_sdr_envelope(snap.get("envelope"), snap.get("envelope_dt_s")),
            fig_sdr_codes(snap.get("code_hist")))


@app.callback(Output("sdr-centre-in","value"),
              Input("sdr-tune","n_clicks"),
              Input({"type":"sdr-preset","band":ALL}, "n_clicks"),
              Input("sdr-gain","value"),
              State("sdr-centre-in","value"), prevent_initial_call=True)
def sdr_tune(_go, _presets, gain, centre_mhz):
    trigger = dash.callback_context.triggered_id
    if trigger is None:
        raise dash.exceptions.PreventUpdate
    try:
        if isinstance(trigger, dict) and trigger.get("type") == "sdr-preset":
            band = trigger["band"]
            match = next((p for p in SDR_PRESETS if p[0] == band), None)
            if not match:
                raise dash.exceptions.PreventUpdate
            centre = (match[1] + match[2]) / 2
            sdr_command(centre_hz=centre)
            return round(centre / 1e6, 4)
        if trigger == "sdr-gain":
            sdr_command(gain=gain)
            raise dash.exceptions.PreventUpdate
        if centre_mhz is None:
            raise dash.exceptions.PreventUpdate
        sdr_command(centre_hz=float(centre_mhz) * 1e6)
    except (ValueError, TypeError):
        raise dash.exceptions.PreventUpdate
    return dash.no_update


@app.callback(Output("sdr-sweep-note","children", allow_duplicate=True),
              Output("sdr-sweep-top-note","children"),
              Input("sdr-sweep-go","n_clicks"), Input("sdr-sweep-now","n_clicks"),
              Input("sdr-sweep-stop","n_clicks"),
              State("sdr-sweep-a","value"), State("sdr-sweep-b","value"),
              prevent_initial_call=True)
def sdr_sweep_cb(_go, _now, _stop, start_mhz, stop_mhz):
    trigger = dash.callback_context.triggered_id
    if trigger == "sdr-sweep-stop":
        sdr_command(cancel_sweep=True)
        return "stopping…", 'Text'
    if start_mhz is None or stop_mhz is None:
        return 'Text', 'Text'
    try:
        sdr_command(sweep=(float(start_mhz) * 1e6, float(stop_mhz) * 1e6))
    except (ValueError, TypeError) as exc:
        note = str(exc)[:90]
        return note, note
    return 'Text', 'Text'

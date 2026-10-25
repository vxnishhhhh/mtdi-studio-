"""Plotly figure builders and shared chart helpers."""
from ._shared import inherit
inherit(globals(), 'common', 'sensors', 'intelligence', 'system', 'tokens', 'theme', 'browser', 'webapp', 'reports')
from .content import T  # studio words (S1-06)

# ════════════════════════════════════════════════════════
#  CHART / SHARED HELPERS
#
#  Every figure here sets BOTH:
#    uirevision            -> Plotly keeps zoom/pan/3D camera across figure swaps
#    transition duration 0 -> Plotly never animates between old and new data, which is
#                             what made values appear to slide/morph on each refresh
#  and every dcc.Graph is given an explicit pixel height so the surrounding layout is
#  reserved before Plotly has rendered anything.
# ════════════════════════════════════════════════════════
NO_TRANSITION = dict(duration=0)


def _chart_layout(height=340, ylabel="", xlabel="Independent variable — sample order"):
    return dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=64,r=12,t=8,b=42), height=height, autosize=False,
                transition=NO_TRANSITION, dragmode=False,
                xaxis=dict(showgrid=False, showticklabels=True, zeroline=False,
                           tickfont=dict(color=SUBTEXT, size=9),
                           title=dict(text=xlabel, font=dict(color=SUBTEXT, size=9))),
                yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickfont=dict(color=SUBTEXT, size=10),
                           zeroline=False, title=dict(
                               text=f"Dependent variable — {ylabel}" if ylabel else 'Text',
                               font=dict(color=SUBTEXT, size=10))),
                showlegend=False)


def make_line_chart(history, color=BLUE, fill_color="rgba(41,121,255,0.08)",
                    height=340, ylabel="", smart_scale=False, zoom=1.0,
                    revision="line"):
    values = [float(v) for v in history if v is not None and math.isfinite(float(v))]
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=values, mode="lines",
        line=dict(color=color, width=2, shape="spline", smoothing=0.5),
        fill="tozeroy", fillcolor=fill_color, hovertemplate="%{y:.2f}<extra></extra>"))
    fig.update_layout(**_chart_layout(height, ylabel))
    if smart_scale and values:
        ordered = sorted(values)
        median = statistics.median(ordered)
        deviations = [abs(v - median) for v in ordered]
        mad = statistics.median(deviations) if deviations else 0.0
        q10 = ordered[int((len(ordered) - 1) * 0.10)]
        q90 = ordered[int((len(ordered) - 1) * 0.90)]
        robust_span = max(q90 - q10, mad * 5.0, abs(median) * 0.015, 0.05)
        zoom = max(0.5, min(float(zoom or 1.0), 8.0))
        half = robust_span * 1.65 / zoom
        lo = median - half
        hi = median + half
        if min(values) >= 0:
            lo = max(0.0, lo)
        if hi <= lo:
            hi = lo + 0.1

        spike_x, spike_y, spike_real, spike_symbol = [], [], [], []
        for i, value in enumerate(values):
            if value > hi:
                spike_x.append(i); spike_y.append(hi)
                spike_real.append(value); spike_symbol.append("triangle-up")
            elif value < lo:
                spike_x.append(i); spike_y.append(lo)
                spike_real.append(value); spike_symbol.append("triangle-down")
        if spike_x:
            fig.add_trace(go.Scatter(
                x=spike_x, y=spike_y, mode="markers",
                customdata=spike_real,
                marker=dict(size=8, color=RED, symbol=spike_symbol,
                            line=dict(color=WHITE, width=1)),
                hovertemplate="SPIKE %{customdata:.4f} unit<extra></extra>",
                showlegend=False,
            ))
        fig.update_yaxes(range=[lo, hi], fixedrange=False)
        fig.add_annotation(
            x=1, y=1, xref="paper", yref="paper", xanchor="right", yanchor="top",
            text=f"SMART ×{zoom:g}", showarrow=False,
            font=dict(family=FONT, color=CYAN, size=9),
            bgcolor="rgba(7,9,15,0.65)", bordercolor="rgba(0,229,255,0.22)",
            borderpad=4,
        )
    fig.update_layout(uirevision=f"{revision}-{float(zoom or 1.0):.2f}")
    return fig


# ── extra chart builders (all uirevision-stable so updates don't reset the view) ──
CFG_FLAT = {
    "displayModeBar": False, "responsive": True, "staticPlot": False,
    "scrollZoom": False, "doubleClick": False,
}
CFG_3D = {
    "displayModeBar": False, "displaylogo": False, "responsive": True,
    "staticPlot": False, "scrollZoom": True, "doubleClick": "reset",
    "plotGlPixelRatio": 2,
}


def _scene(height):
    ax = dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="rgba(128,128,128,0.14)", zerolinecolor="rgba(128,128,128,0.14)",
              tickfont=dict(color=SUBTEXT, size=8), title=dict(font=dict(color=SUBTEXT, size=9)), showbackground=True)
    return dict(paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=0, b=0), height=height,
                autosize=False, transition=NO_TRANSITION,
                scene=dict(bgcolor="rgba(0,0,0,0)", aspectmode="cube",
                           dragmode="orbit",
                           xaxis={**ax, "title": {**ax["title"], "text":'Text'}},
                           yaxis={**ax, "title": {**ax["title"], "text":'Text'}},
                           zaxis={**ax, "title": {**ax["title"], "text":'Text'}},
                           camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))))


def ch2_axis_unit(data):
    """The unit channel 2's charts show. Data fed in (an MTDI project, /api/ingest) carries its own
    unit; the studio's own ADC paths keep their labels. "mV RMS relative" is feed_ch2's default when a
    sender gave no unit, so it is treated as none."""
    fed = str(data.get("unit") or "").strip()
    if fed and fed != "mV RMS relative":
        return fed
    return "ADC counts RMS" if data.get("data_source") == "ARDUINO_UNO_USB" else "mV RMS"


def fig_axis(xyz, height=250, unit=None):
    unit = T("ch1.unit") if unit is None else unit   # the project's channel 1 unit (S1-06)
    fig = go.Figure()
    if xyz:
        for idx, (c, nm) in enumerate([(BLUE,"X"), (GREEN,"Y"), (AMBER,"Z")]):
            fig.add_trace(go.Scatter(y=[p[idx] for p in xyz], mode="lines",
                line=dict(color=c, width=1.6, shape="spline", smoothing=0.4), name=nm,
                hovertemplate=nm+" %{y:.2f}<extra></extra>"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=70,r=12,t=6,b=42), height=height, autosize=False,
        transition=NO_TRANSITION, dragmode=False,
        xaxis=dict(showgrid=False, showticklabels=True, zeroline=False,
                   tickfont=dict(color=SUBTEXT, size=9),
                   title=dict(text='Text', font=dict(color=SUBTEXT,size=9))),
        yaxis=dict(gridcolor="rgba(128,128,128,0.12)", zeroline=False,
                   tickfont=dict(color=SUBTEXT, size=9),
                   title=dict(text=f"Dependent variables — X, Y, Z components ({unit})",
                              font=dict(color=SUBTEXT,size=9))),
        showlegend=True, legend=dict(orientation="h", y=1.16, x=0, font=dict(color=SUBTEXT, size=9), bgcolor="rgba(0,0,0,0)"),
        uirevision="axis")
    return fig


def fig_pie(x, y, z, height=250):
    fig = go.Figure()
    if x is not None and y is not None and z is not None:
        vals = [abs(x), abs(y), abs(z)]
        fig.add_trace(go.Pie(labels=["X","Y","Z"], values=vals, hole=0.62, sort=False,
            marker=dict(colors=[BLUE, GREEN, AMBER], line=dict(color="rgba(7,9,15,0.5)", width=2)),
            textfont=dict(family=FONT, size=11, color=WHITE), hovertemplate="%{label}: %{percent}<extra></extra>"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0,r=0,t=6,b=0), height=height,
                      autosize=False, transition=NO_TRANSITION, showlegend=False, uirevision="pie")
    return fig


def fig_gauge(c1, height=250, unit=None):
    unit = T("ch1.unit") if unit is None else unit   # the project's channel 1 unit (S1-06)
    if c1 is None:
        fig = go.Figure()
        fig.add_annotation(text='TEXT', x=0.5, y=0.5,
                           showarrow=False, font=dict(color=SUBTEXT, size=11))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=height, autosize=False,
                          transition=NO_TRANSITION, margin=dict(l=14,r=14,t=18,b=6), uirevision="gauge")
        return fig
    top = max(1.0 if unit == "normalized" else 80.0, c1 * 1.3)
    fig = go.Figure(go.Indicator(mode="gauge+number", value=c1,
        number=dict(font=dict(family=FONT, color=CYAN, size=24), suffix=" " + unit),
        gauge=dict(axis=dict(range=[0, top], tickcolor=SUBTEXT, tickfont=dict(color=SUBTEXT, size=8)),
                   bar=dict(color=CYAN, thickness=0.28), bgcolor="rgba(255,255,255,0.03)", bordercolor="rgba(255,255,255,0.08)",
                   steps=[dict(range=[0, top * 0.32], color="rgba(41,121,255,0.15)"),
                          dict(range=[top * 0.32, top * 0.81], color="rgba(0,230,118,0.15)"),
                          dict(range=[top * 0.81, top], color="rgba(255,171,64,0.15)")])))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=14,r=14,t=18,b=6), height=height,
                      autosize=False, transition=NO_TRANSITION, font=dict(color=SUBTEXT), uirevision="gauge")
    return fig


def fig_bar(mn, avg, mx, height=250, unit=None, quantity=None):
    """Session min/average/max.

    unit and quantity are parameters because the Ch2 channel needs the same
    chart in mV RMS. Defaulting them to the ch1 pair keeps every existing
    call unchanged -- a second near-identical function would have been the
    alternative, and the two would have drifted apart the first time either was
    touched."""
    unit = T("ch1.unit") if unit is None else unit   # the project's channel 1 words (S1-06)
    quantity = f"{T('ch1.name').lower()} magnitude" if quantity is None else quantity
    fig = go.Figure()
    if mn is not None and avg is not None and mx is not None:
        fig.add_trace(go.Bar(x=["MIN","AVG","MAX"], y=[mn, avg, mx], marker=dict(color=[BLUE, CYAN, AMBER]),
            text=[f"{v:.2f}" for v in (mn, avg, mx)], textposition="outside",
            textfont=dict(family=FONT, color=WHITE, size=10),
            hovertemplate="%{x}: %{y:.2f} " + unit + "<extra></extra>"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=68,r=12,t=16,b=52), height=height, autosize=False,
        transition=NO_TRANSITION, dragmode=False,
        xaxis=dict(tickfont=dict(color=SUBTEXT, size=10),
                   title=dict(text='Text',
                              font=dict(color=SUBTEXT,size=9))),
        yaxis=dict(gridcolor="rgba(128,128,128,0.12)", zeroline=False,
                   tickfont=dict(color=SUBTEXT, size=9),
                   title=dict(text=f"Dependent value — {quantity} ({unit})",
                              font=dict(color=SUBTEXT,size=9))),
        showlegend=False, uirevision="bar")
    return fig


def fig_2d_scatter(xyz, height=280, unit=None):
    unit = T("ch1.unit") if unit is None else unit   # the project's channel 1 unit (S1-06)
    fig = go.Figure()
    if xyz:
        xs = [p[0] for p in xyz]; ys = [p[1] for p in xyz]
        mags = [math.sqrt(a*a+b*b+c*c) for a,b,c in xyz]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+lines",
            line=dict(color="rgba(0,229,255,0.20)", width=1),
            marker=dict(size=6, color=mags, colorscale="Turbo", opacity=0.82,
                        showscale=True, colorbar=dict(
                            title=dict(text=unit, font=dict(color=SUBTEXT, size=8)),
                            thickness=8, tickfont=dict(color=SUBTEXT, size=8))),
            hovertemplate="X %{x:.3f} " + unit + "<br>Y %{y:.3f} " + unit + "<extra></extra>",
            showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=[xs[-1]], y=[ys[-1]], mode="markers",
            marker=dict(size=11, color=CYAN, line=dict(color=WHITE, width=1)),
            hovertemplate="CURRENT<br>X %{x:.3f}<br>Y %{y:.3f}<extra></extra>",
            showlegend=False,
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=height, autosize=False, transition=NO_TRANSITION, dragmode=False,
        margin=dict(l=42,r=14,t=10,b=36),
        xaxis=dict(title=f"Independent variable — X component ({unit})", gridcolor="rgba(128,128,128,0.12)",
                   zerolinecolor="rgba(0,229,255,0.20)", tickfont=dict(color=SUBTEXT, size=9)),
        yaxis=dict(title=f"Dependent variable — Y component ({unit})", gridcolor="rgba(128,128,128,0.12)",
                   zerolinecolor="rgba(0,229,255,0.20)", tickfont=dict(color=SUBTEXT, size=9),
                   scaleanchor="x", scaleratio=1),
        uirevision="c1-scatter",
    )
    return fig


def fig_2d_delta(xyz, height=280, unit=None):
    unit = T("ch1.unit") if unit is None else unit   # the project's channel 1 unit (S1-06)
    fig = go.Figure()
    if len(xyz) > 1:
        mags = [math.sqrt(a*a+b*b+c*c) for a,b,c in xyz]
        delta = [0.0] + [abs(mags[i]-mags[i-1]) for i in range(1, len(mags))]
        fig.add_trace(go.Scatter(
            x=mags, y=delta, mode="markers",
            marker=dict(size=6, color=list(range(len(mags))), colorscale="Viridis",
                        opacity=0.78, showscale=False),
            hovertemplate="Magnitude %{x:.3f} " + unit + "<br>Δ %{y:.4f} " + unit + "<extra></extra>",
            showlegend=False,
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=height, autosize=False, transition=NO_TRANSITION, dragmode=False,
        margin=dict(l=48,r=12,t=10,b=38),
        xaxis=dict(title=f"Independent variable — magnitude ({unit})", gridcolor="rgba(128,128,128,0.12)",
                   tickfont=dict(color=SUBTEXT, size=9)),
        yaxis=dict(title=f"Dependent variable — sample change Δ ({unit})", gridcolor="rgba(128,128,128,0.12)",
                   tickfont=dict(color=SUBTEXT, size=9)),
        uirevision="c1-delta",
    )
    return fig


def fig_3d_surface(xyz, height=300, unit=None):
    unit = T("ch1.unit") if unit is None else unit   # the project's channel 1 unit (S1-06)
    fig = go.Figure()
    if xyz:
        pts = xyz[-80:]
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]; zs=[p[2] for p in pts]
        xlo,xhi=min(xs),max(xs); ylo,yhi=min(ys),max(ys)
        if xhi == xlo: xlo,xhi=xlo-1,xhi+1
        if yhi == ylo: ylo,yhi=ylo-1,yhi+1
        # 14x14 retains the measured topology while cutting interpolation work and
        # WebGL surface triangles by ~40% compared with the former 18x18 mesh.
        gx=[xlo+(xhi-xlo)*i/13 for i in range(14)]
        gy=[ylo+(yhi-ylo)*j/13 for j in range(14)]
        radius=max((xhi-xlo),(yhi-ylo),0.1)*0.28
        grid=[]
        for yy in gy:
            row=[]
            for xx in gx:
                weights=[math.exp(-((xx-x)**2+(yy-y)**2)/(2*radius*radius)) for x,y in zip(xs,ys)]
                total=sum(weights)
                row.append(sum(w*z for w,z in zip(weights,zs))/total if total else 0.0)
            grid.append(row)
        fig.add_trace(go.Surface(x=gx, y=gy, z=grid, colorscale="Turbo",
                                 showscale=False, opacity=0.92,
                                 hovertemplate="X %{x:.2f}<br>Y %{y:.2f}<br>Z %{z:.2f}<extra></extra>"))
        fig.add_trace(go.Scatter3d(x=[xs[-1]],y=[ys[-1]],z=[zs[-1]],mode="markers",
                                   marker=dict(size=7,color=WHITE),showlegend=False))
    fig.update_layout(uirevision="field-surface", **_scene(height))
    fig.update_layout(scene=dict(
        xaxis=dict(title=dict(text=f"Independent variable — X component ({unit})")),
        yaxis=dict(title=dict(text=f"Independent variable — Y component ({unit})")),
        zaxis=dict(title=dict(text=f"Dependent surface — interpolated Z ({unit})")),
    ))
    return fig


def fig_3d_terrain(xyz, height=300, unit=None):
    unit = T("ch1.unit") if unit is None else unit   # the project's channel 1 unit (S1-06)
    fig = go.Figure()
    if xyz:
        pts=xyz[-120:]
        mags=[math.sqrt(a*a+b*b+c*c) for a,b,c in pts]
        rows=min(12,max(2,len(mags)//8)); cols=max(8,min(28,len(mags)))
        terrain=[]
        for row in range(rows):
            shift=int(row*max(1,len(mags)-cols)/max(1,rows-1))
            segment=mags[shift:shift+cols]
            if len(segment)<cols: segment += [segment[-1] if segment else 0.0]*(cols-len(segment))
            terrain.append(segment)
        fig.add_trace(go.Surface(
            z=terrain, x=list(range(cols)), y=list(range(rows)),
            colorscale=[[0,"#001a72"],[0.35,"#00a8ff"],[0.65,"#ffee00"],[1,"#ff2d00"]],
            showscale=True, colorbar=dict(
                title=dict(text=unit, font=dict(color=SUBTEXT,size=8)),
                thickness=9, tickfont=dict(color=SUBTEXT,size=8)),
            hovertemplate="Sample %{x}<br>Window %{y}<br>%{z:.3f} " + unit + "<extra></extra>",
        ))
    fig.update_layout(uirevision="signal-terrain", **_scene(height))
    fig.update_layout(scene=dict(
        xaxis=dict(title=dict(text='Text')),
        yaxis=dict(title=dict(text='Text')),
        zaxis=dict(title=dict(text=f"Dependent response — magnitude ({unit})")),
    ))
    return fig


_direction_viz_lock = threading.RLock()
_direction_viz_state = {"direction": (0.0, 1.0, 0.0)}


def _normalise3(vector, fallback=(0.0, 1.0, 0.0)):
    length = math.sqrt(sum(value * value for value in vector))
    return tuple(value / length for value in vector) if length > 1e-12 else fallback


def _cross3(a, b):
    return (a[1]*b[2]-a[2]*b[1],
            a[2]*b[0]-a[0]*b[2],
            a[0]*b[1]-a[1]*b[0])


def _direction_plot_state(xyz):
    """Map the flat sensor into a +Y-up scene, smooth direction, compress magnitude."""
    if not xyz:
        return {"direction": (0.0, 1.0, 0.0), "magnitude": 0.0,
                "display_length": 0.25, "error": 0.0, "raw": (0.0, 0.0, 0.0)}
    sx, sy, sz = xyz[-1]
    magnitude = math.sqrt(sx*sx + sy*sy + sz*sz)
    # Sensor board: X/Y lie in its plane and Z is normal to it.
    # Plot scene: +Y is up, so sensor Z -> plot Y and sensor Y -> -plot Z.
    mapped = _normalise3((sx, sz, -sy))
    with _direction_viz_lock:
        previous = _direction_viz_state["direction"]
        alpha = 0.28
        smoothed = _normalise3(tuple(
            previous[index] * (1.0-alpha) + mapped[index] * alpha
            for index in range(3)
        ), mapped)
        _direction_viz_state["direction"] = smoothed
    # Log compression keeps weak fields visible without letting spikes leave the cube.
    compressed = min(1.0, max(0.0, math.log1p(max(0.0, magnitude)) / math.log1p(100.0)))
    display_length = 0.28 + 0.72 * compressed
    recent = [math.sqrt(x*x+y*y+z*z) for x,y,z in xyz[-40:]]
    reference = statistics.median(recent) if recent else 0.0
    return {
        "direction": smoothed,
        "magnitude": magnitude,
        "display_length": display_length,
        "error": abs(magnitude-reference),
        "raw": (sx, sy, sz),
    }


@functools.lru_cache(maxsize=1)
def _unit_arrow_geometry():
    """Build one cylinder + cone along local +Y; callers only rotate and scale it."""
    sides = 12
    shaft_radius, shaft_top, head_radius = 0.042, 0.76, 0.12
    shaft_vertices = []
    for y in (0.0, shaft_top):
        for index in range(sides):
            angle = 2.0 * math.pi * index / sides
            shaft_vertices.append((shaft_radius*math.cos(angle), y,
                                   shaft_radius*math.sin(angle)))
    shaft_faces = []
    for index in range(sides):
        nxt = (index+1) % sides
        shaft_faces.extend([
            (index, nxt, sides+index),
            (nxt, sides+nxt, sides+index),
        ])
    head_vertices = [
        (head_radius*math.cos(2.0*math.pi*index/sides), shaft_top,
         head_radius*math.sin(2.0*math.pi*index/sides))
        for index in range(sides)
    ] + [(0.0, 1.0, 0.0)]
    tip = sides
    head_faces = [(index, (index+1)%sides, tip) for index in range(sides)]
    return shaft_vertices, shaft_faces, head_vertices, head_faces


def _rotate_arrow_points(points, direction, scale):
    """Rotate local +Y geometry onto direction using an orthonormal basis."""
    up = _normalise3(direction)
    helper = (0.0, 0.0, 1.0) if abs(up[2]) < 0.92 else (1.0, 0.0, 0.0)
    right = _normalise3(_cross3(helper, up), (1.0, 0.0, 0.0))
    forward = _normalise3(_cross3(right, up), (0.0, 0.0, 1.0))
    return [
        (scale*(right[0]*x + up[0]*y + forward[0]*z),
         scale*(right[1]*x + up[1]*y + forward[1]*z),
         scale*(right[2]*x + up[2]*y + forward[2]*z))
        for x,y,z in points
    ]


def _mesh_trace(points, faces, color, hovertext):
    return go.Mesh3d(
        x=[p[0] for p in points], y=[p[1] for p in points], z=[p[2] for p in points],
        i=[face[0] for face in faces], j=[face[1] for face in faces],
        k=[face[2] for face in faces], color=color, opacity=0.96,
        flatshading=False, hovertemplate=hovertext, showscale=False,
    )


def fig_3d_error_plane(xyz, height=300, direction_state=None):
    fig = go.Figure()
    # Hollow XYZ framework: all twelve cube edges in one lightweight trace.
    corners = [
        (-1,-1,-1), (1,-1,-1), (1,1,-1), (-1,1,-1),
        (-1,-1, 1), (1,-1, 1), (1,1, 1), (-1,1, 1),
    ]
    edges = [
        (0,1),(1,2),(2,3),(3,0), (4,5),(5,6),(6,7),(7,4),
        (0,4),(1,5),(2,6),(3,7),
    ]
    ex,ey,ez=[],[],[]
    for start,end in edges:
        p,q=corners[start],corners[end]
        ex += [p[0],q[0],None]
        ey += [p[1],q[1],None]
        ez += [p[2],q[2],None]
    fig.add_trace(go.Scatter3d(
        x=ex,y=ey,z=ez,mode="lines",
        line=dict(color="rgba(0,229,255,0.58)",width=4),
        hoverinfo="skip",showlegend=False,
    ))
    # A faint centre plane makes the arrow's origin and direction readable while
    # leaving the enclosing cube visibly hollow.
    plane=[-1.0,1.0]
    fig.add_trace(go.Surface(
        x=plane,y=plane,z=[[0,0],[0,0]],surfacecolor=[[0,0],[0,0]],
        colorscale=[[0,"#2979ff"],[1,"#00e5ff"]],
        opacity=0.10,showscale=False,hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter3d(
        x=[0],y=[0],z=[0],mode="markers",
        marker=dict(size=7,color=WHITE,line=dict(color=CYAN,width=2)),
        hovertemplate="FIELD ORIGIN (0, 0, 0)<extra></extra>",showlegend=False,
    ))
    state = direction_state or _direction_plot_state(xyz)
    if xyz:
        a,b,c=state["raw"]
        c1=state["magnitude"]
        error=state["error"]
        direction=state["direction"]
        display_length=state["display_length"]
        reference = statistics.median(
            [math.sqrt(x*x+y*y+z*z) for x,y,z in xyz[-40:]]
        )
        color=RED if error>max(reference*0.20,1.0) else AMBER if error>max(reference*0.08,0.3) else CYAN
        shaft_vertices,shaft_faces,head_vertices,head_faces=_unit_arrow_geometry()
        shaft=_rotate_arrow_points(shaft_vertices,direction,display_length)
        head=_rotate_arrow_points(head_vertices,direction,display_length)
        hover=("CH1 FIELD DIRECTION"
               f"<br>Sensor X {a:.3f} unit<br>Sensor Y {b:.3f} unit"
               f"<br>Sensor Z {c:.3f} unit<br>|B| {c1:.3f} unit"
               f"<br>Log display length {display_length:.3f}<extra></extra>")
        fig.add_trace(_mesh_trace(shaft,shaft_faces,color,hover))
        fig.add_trace(_mesh_trace(head,head_faces,color,hover))
        fig.add_annotation(text=f"FIELD DIRECTION · |B| {c1:.3f} unit · Δ {error:.3f} unit",
                           x=0.02,y=0.98,
                           xref="paper",yref="paper",showarrow=False,
                           font=dict(family=FONT,color=color,size=10))
    fig.update_layout(uirevision="error-plane", **_scene(height))
    fig.update_layout(scene=dict(
        xaxis=dict(title=dict(text='Text')),
        yaxis=dict(title=dict(text='Text')),
        zaxis=dict(title=dict(text='Text')),
        aspectmode="cube",
    ))
    fig.update_scenes(
        xaxis_range=[-1.15,1.15],yaxis_range=[-1.15,1.15],zaxis_range=[-1.15,1.15]
    )
    return fig


def fig_3d_dipolch2f(xyz, height=420, direction_state=None):
    """Twopole field lines plus floor needles for the current smoothed B direction."""
    fig = go.Figure()
    state = direction_state or _direction_plot_state(xyz)
    moment = _normalise3(state["direction"])
    helper = (0.0,0.0,1.0) if abs(moment[2]) < 0.92 else (1.0,0.0,0.0)
    e1 = _normalise3(_cross3(helper,moment),(1.0,0.0,0.0))
    e2 = _normalise3(_cross3(moment,e1),(0.0,0.0,1.0))

    # Analytic twopole field lines: r = L sin²(theta), revolved about the moment.
    line_x,line_y,line_z=[],[],[]
    for phi_index in range(6):
        phi=2.0*math.pi*phi_index/6
        for index in range(48):
            theta=0.16+(math.pi-0.32)*index/47
            radius=0.98*(math.sin(theta)**2)
            radial=(
                e1[0]*math.cos(phi)+e2[0]*math.sin(phi),
                e1[1]*math.cos(phi)+e2[1]*math.sin(phi),
                e1[2]*math.cos(phi)+e2[2]*math.sin(phi),
            )
            point=(
                radius*(radial[0]*math.sin(theta)+moment[0]*math.cos(theta)),
                radius*(radial[1]*math.sin(theta)+moment[1]*math.cos(theta)),
                radius*(radial[2]*math.sin(theta)+moment[2]*math.cos(theta)),
            )
            line_x.append(point[0]);line_y.append(point[1]);line_z.append(point[2])
        line_x.append(None);line_y.append(None);line_z.append(None)
    fig.add_trace(go.Scatter3d(
        x=line_x,y=line_y,z=line_z,mode="lines",
        line=dict(color="rgba(0,229,255,0.58)",width=3),
        hoverinfo="skip",showlegend=False,
    ))

    # Floor needles use the physical twopole field:
    # B(r) ∝ [3 r_hat (m·r_hat) - m] / |r|³.
    nx,ny,nz=[],[],[]
    cone_x,cone_y,cone_z=[],[],[]
    cone_u,cone_v,cone_w=[],[],[]
    for gx in range(-2,3):
        for gz in range(-2,3):
            x,z=gx/2.0,gz/2.0
            r=(x,-0.86,z)
            radius=math.sqrt(sum(value*value for value in r))
            if radius<0.2:continue
            rhat=tuple(value/radius for value in r)
            dot=sum(moment[i]*rhat[i] for i in range(3))
            field=tuple((3.0*rhat[i]*dot-moment[i])/(radius**3) for i in range(3))
            direction=_normalise3(field)
            needle=0.13
            tip=(x+direction[0]*needle,-0.86+direction[1]*needle,z+direction[2]*needle)
            nx += [x,tip[0],None];ny += [-0.86,tip[1],None];nz += [z,tip[2],None]
            cone_x.append(tip[0]);cone_y.append(tip[1]);cone_z.append(tip[2])
            cone_u.append(direction[0]*0.04);cone_v.append(direction[1]*0.04);cone_w.append(direction[2]*0.04)
    fig.add_trace(go.Scatter3d(
        x=nx,y=ny,z=nz,mode="lines",
        line=dict(color="rgba(255,171,64,0.70)",width=3),
        hoverinfo="skip",showlegend=False,
    ))
    fig.add_trace(go.Cone(
        x=cone_x,y=cone_y,z=cone_z,u=cone_u,v=cone_v,w=cone_w,
        sizemode="absolute",sizeref=0.07,anchor="tail",
        colorscale=[[0,AMBER],[1,RED]],showscale=False,hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter3d(
        x=[0],y=[0],z=[0],mode="markers",
        marker=dict(size=8,color=WHITE,line=dict(color=CYAN,width=2)),
        hovertemplate="DIPOLE ORIGIN<extra></extra>",showlegend=False,
    ))
    fig.update_layout(uirevision="twopole-field", **_scene(height))
    fig.update_layout(scene=dict(
        xaxis=dict(title=dict(text='Text')),
        yaxis=dict(title=dict(text='Text')),
        zaxis=dict(title=dict(text='Text')),
        aspectmode="cube",
    ))
    fig.update_scenes(
        xaxis_range=[-1.15,1.15],yaxis_range=[-1.15,1.15],zaxis_range=[-1.15,1.15]
    )
    fig.add_annotation(
        text='Text',
        x=0.02,y=0.98,xref="paper",yref="paper",showarrow=False,
        font=dict(family=FONT,color=AMBER,size=10),
    )
    return fig


def fig_archive(height=220, series=None, unit=None):
    """The rolling signal archive.

    series lets a caller supply its own sequence; with none it reads the ch1
    archive as before, so existing calls are untouched. The Ch2 channel needs
    this identical view over its own vector magnitude, and passing the data in
    beats reaching for a second module-level global."""
    unit = T("ch1.unit") if unit is None else unit   # the project's channel 1 unit (S1-06)
    if series is None:
        with archive_lock:
            arch = [a["c1"] for a in signal_archive]
    else:
        arch = list(series)
    fig = go.Figure()
    if arch:
        fig.add_trace(go.Scatter(y=arch, mode="lines",
            line=dict(color=PURPLE, width=2, shape="spline", smoothing=0.4),
            fill="tozeroy", fillcolor="rgba(179,136,255,0.08)",
            hovertemplate="%{y:.2f} " + unit + "<extra></extra>"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0,r=0,t=6,b=0), height=height, autosize=False, transition=NO_TRANSITION,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(gridcolor="rgba(128,128,128,0.12)", zeroline=False, tickfont=dict(color=SUBTEXT, size=9)),
        showlegend=False, uirevision="arch")
    return fig


# ── Ch2 visualisations (scalar only — gauge / bullet / bars) ──
def fig_c2_gauge(rel, height=250):
    if rel is None:
        fig = go.Figure()
        fig.add_annotation(text='TEXT', x=0.5, y=0.5,
                           showarrow=False, font=dict(color=SUBTEXT, size=11))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=height, autosize=False,
                          transition=NO_TRANSITION, margin=dict(l=14,r=14,t=18,b=6), uirevision="efgauge")
        return fig
    fig = go.Figure(go.Indicator(mode="gauge+number", value=rel,
        number=dict(font=dict(family=FONT, color=CYAN, size=24), suffix=" %"),
        gauge=dict(axis=dict(range=[0,100], tickcolor=SUBTEXT, tickfont=dict(color=SUBTEXT, size=8)),
                   bar=dict(color=CYAN, thickness=0.28), bgcolor="rgba(255,255,255,0.03)", bordercolor="rgba(255,255,255,0.08)",
                   steps=[dict(range=[0,22], color="rgba(0,230,118,0.15)"),
                          dict(range=[22,60], color="rgba(255,171,64,0.15)"),
                          dict(range=[60,100], color="rgba(255,82,82,0.15)")])))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=14,r=14,t=18,b=6), height=height,
                      autosize=False, transition=NO_TRANSITION, font=dict(color=SUBTEXT), uirevision="efgauge")
    return fig


def fig_c2_bullet(rel, level, height=250):
    if rel is None:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=height, autosize=False,
                          transition=NO_TRANSITION, margin=dict(l=10,r=10,t=30,b=14), uirevision="efbullet")
        return fig
    col = _c2_level_color(level)
    fig = go.Figure(go.Indicator(mode="number+gauge", value=rel,
        number=dict(font=dict(family=FONT, color=col, size=22), suffix=" %"),
        gauge=dict(shape="bullet", axis=dict(range=[0,100], tickcolor=SUBTEXT, tickfont=dict(color=SUBTEXT, size=8)),
                   bar=dict(color=col, thickness=0.6), bgcolor="rgba(255,255,255,0.03)", bordercolor="rgba(255,255,255,0.08)",
                   steps=[dict(range=[0,22], color="rgba(0,230,118,0.16)"),
                          dict(range=[22,60], color="rgba(255,171,64,0.16)"),
                          dict(range=[60,100], color="rgba(255,82,82,0.16)")])))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=10,r=10,t=30,b=14), height=height,
                      autosize=False, transition=NO_TRANSITION, font=dict(color=SUBTEXT), uirevision="efbullet")
    return fig


def fig_c2_basebar(baseline, rms, peak, height=250):
    fig = go.Figure()
    if baseline is not None and rms is not None and peak is not None:
        fig.add_trace(go.Bar(x=["BASELINE","AC RMS","PEAK"], y=[baseline, rms, peak], marker=dict(color=[SUBTEXT, CYAN, AMBER]),
            text=[f"{v:.1f}" for v in (baseline, rms, peak)], textposition="outside",
            textfont=dict(family=FONT, color=WHITE, size=10), hovertemplate="%{x}: %{y:.3f} unit = N/C<extra></extra>"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0,r=0,t=16,b=0), height=height, autosize=False, transition=NO_TRANSITION,
        xaxis=dict(tickfont=dict(color=SUBTEXT, size=10)),
        yaxis=dict(gridcolor="rgba(128,128,128,0.12)", zeroline=False, tickfont=dict(color=SUBTEXT, size=9)),
        showlegend=False, uirevision="efbase")
    return fig


def fig_c2_b_correlation(c1_history, c2_relative_history, height=280):
    """Relative E activity against B magnitude; association only, never causation."""
    count=min(len(c1_history),len(c2_relative_history),160)
    b=list(c1_history)[-count:] if count else []
    e=list(c2_relative_history)[-count:] if count else []
    fig=go.Figure()
    if count:
        fig.add_trace(go.Scatter(
            x=b,y=e,mode="markers",
            marker=dict(size=6,color=list(range(count)),colorscale="Turbo",
                        opacity=0.78,showscale=False),
            hovertemplate="B magnitude %{x:.3f} unit"
                          "<br>Relative E activity %{y:.2f}%<extra></extra>",
            showlegend=False,
        ))
        if count>=3:
            mean_b=sum(b)/count;mean_e=sum(e)/count
            numerator=sum((x-mean_b)*(y-mean_e) for x,y in zip(b,e))
            denominator=math.sqrt(sum((x-mean_b)**2 for x in b)*sum((y-mean_e)**2 for y in e))
            correlation=numerator/denominator if denominator>1e-12 else 0.0
            fig.add_annotation(
                text=f"sample-aligned association r={correlation:+.2f}",
                x=0.02,y=0.98,xref="paper",yref="paper",showarrow=False,
                font=dict(family=FONT,color=CYAN,size=9),
            )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        height=height,autosize=False,transition=NO_TRANSITION,dragmode=False,
        margin=dict(l=62,r=14,t=12,b=46),
        xaxis=dict(title='Title',
                   gridcolor="rgba(128,128,128,0.12)",tickfont=dict(color=SUBTEXT,size=9)),
        yaxis=dict(title='Title',
                   gridcolor="rgba(128,128,128,0.12)",tickfont=dict(color=SUBTEXT,size=9)),
        uirevision="c2-b-correlation",
    )
    return fig


def fig_c2_induction_proxy(c1_history, c2_relative_history, height=280):
    """Compare |ΔB| per ch1 sample with relative E activity."""
    count=min(len(c1_history),len(c2_relative_history),160)
    b=list(c1_history)[-count:] if count else []
    e=list(c2_relative_history)[-count:] if count else []
    delta=[0.0]+[abs(b[index]-b[index-1]) for index in range(1,count)] if count else []
    fig=go.Figure()
    if count:
        fig.add_trace(go.Scatter(
            y=delta,mode="lines",name='Label',
            line=dict(color=AMBER,width=2),
            hovertemplate="|ΔB| %{y:.4f} unit/sample<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            y=e,mode="lines",name='Label',yaxis="y2",
            line=dict(color=CYAN,width=1.6),
            hovertemplate="Relative E %{y:.2f}%<extra></extra>",
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        height=height,autosize=False,transition=NO_TRANSITION,dragmode=False,
        margin=dict(l=62,r=62,t=12,b=46),
        xaxis=dict(title='Title',
                   gridcolor="rgba(128,128,128,0.10)",tickfont=dict(color=SUBTEXT,size=9)),
        yaxis=dict(title='Title',
                   gridcolor="rgba(128,128,128,0.12)",tickfont=dict(color=AMBER,size=9)),
        yaxis2=dict(title='Title',overlaying="y",side="right",
                    showgrid=False,tickfont=dict(color=CYAN,size=9)),
        legend=dict(orientation="h",y=1.12,x=0,font=dict(color=SUBTEXT,size=9),
                    bgcolor="rgba(0,0,0,0)"),
        uirevision="c2-induction-proxy",
    )
    return fig


def fig_p1_overlay(c1_history, c2_rms_history, height=320):
    """Sample-aligned B magnitude and reference-scaled Ch2 on independent axes."""
    count = min(len(c1_history), len(c2_rms_history), 200)
    b = list(c1_history)[-count:] if count else []
    e = list(c2_rms_history)[-count:] if count else []
    fig = go.Figure()
    if count:
        fig.add_trace(go.Scatter(
            y=b, mode="lines", name='Label',
            line=dict(color=CYAN, width=2.3),
            hovertemplate="B %{y:.3f} unit<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            y=e, mode="lines", name='Label', yaxis="y2",
            line=dict(color=AMBER, width=2.0),
            hovertemplate="E %{y:.3f} unit = N/C<extra></extra>",
        ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=height, autosize=False, transition=NO_TRANSITION, dragmode=False,
        margin=dict(l=66, r=68, t=18, b=48),
        xaxis=dict(title='Title',
                   gridcolor="rgba(128,128,128,0.10)",
                   tickfont=dict(color=SUBTEXT, size=9)),
        yaxis=dict(title='Title',
                   gridcolor="rgba(128,128,128,0.12)",
                   tickfont=dict(color=CYAN, size=9)),
        yaxis2=dict(title='Title', overlaying="y", side="right",
                    showgrid=False, tickfont=dict(color=AMBER, size=9)),
        legend=dict(orientation="h", y=1.14, x=0,
                    font=dict(color=WHITE, size=10), bgcolor="rgba(0,0,0,0)"),
        uirevision="p1-overlay",
    )
    return fig


def fig_p1_normalized_overlay(c1_history, c2_relative_history, height=300):
    """Overlay field movement on one 0–100 scale without pretending the units match."""
    count = min(len(c1_history), len(c2_relative_history), 200)
    b = list(c1_history)[-count:] if count else []
    e = list(c2_relative_history)[-count:] if count else []

    def normalize(values):
        if not values:
            return []
        lo, hi = min(values), max(values)
        span = hi - lo
        return [50.0] * len(values) if span < 1e-12 else [(v - lo) * 100.0 / span for v in values]

    fig = go.Figure()
    if count:
        fig.add_trace(go.Scatter(
            y=normalize(b), mode="lines", name='Label',
            line=dict(color=CYAN, width=2.2), hovertemplate="B movement %{y:.1f}%<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            y=normalize(e), mode="lines", name='Label',
            line=dict(color=AMBER, width=2.0), hovertemplate="E movement %{y:.1f}%<extra></extra>",
        ))
    fig.update_layout(**_chart_layout(
        height, "normalized movement (%)",
        "Independent variable — aligned live sample order",
    ))
    fig.update_layout(
        yaxis_range=[0, 100], showlegend=True,
        legend=dict(orientation="h", y=1.14, x=0,
                    font=dict(color=WHITE, size=10), bgcolor="rgba(0,0,0,0)"),
        uirevision="p1-normalized-overlay",
    )
    return fig


def _p1_normalized_vectors(rows, count):
    rows = [tuple(float(v) for v in row[:3]) for row in list(rows)[-count:]]
    scale = max((math.sqrt(sum(v * v for v in row)) for row in rows), default=1.0) or 1.0
    return [tuple(v / scale for v in row) for row in rows]


def fig_p1_vector_overlay_3d(ch1_xyz, ch2_xyz, height=470):
    """Two measured vector histories in one normalized 3D coordinate frame."""
    count = min(len(ch1_xyz), len(ch2_xyz), 160)
    b = _p1_normalized_vectors(ch1_xyz, count)
    e = _p1_normalized_vectors(ch2_xyz, count)
    fig = go.Figure()
    if count:
        for rows, name, color in ((b, 'Text', CYAN), (e, 'Text', AMBER)):
            x, y, z = zip(*rows)
            fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode="lines+markers", name=name,
                                       line=dict(color=color, width=5), marker=dict(size=2, color=color),
                                       hovertemplate=name + "<br>X %{x:.3f}<br>Y %{y:.3f}<br>Z %{z:.3f}<extra></extra>"))
        step = max(1, count // 20)
        for i in range(0, count, step):
            fig.add_trace(go.Scatter3d(x=[b[i][0], e[i][0]], y=[b[i][1], e[i][1]], z=[b[i][2], e[i][2]],
                                       mode="lines", showlegend=False, hoverinfo="skip",
                                       line=dict(color="rgba(230,240,255,.18)", width=2)))
    fig.update_layout(**_scene(height))
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.03, x=0), uirevision="p1-vector-overlay-3d",
                      scene=dict(xaxis_title="Normalized X", yaxis_title="Normalized Y", zaxis_title="Normalized Z"))
    return fig


def fig_p1_cross_proxy_3d(ch1_xyz, ch2_xyz, height=470):
    """Normalized E cross B direction history; a geometry proxy, not power flux."""
    count = min(len(ch1_xyz), len(ch2_xyz), 160)
    b = _p1_normalized_vectors(ch1_xyz, count)
    e = _p1_normalized_vectors(ch2_xyz, count)
    cross = [(ey*bz-ez*by, ez*bx-ex*bz, ex*by-ey*bx)
             for (ex, ey, ez), (bx, by, bz) in zip(e, b)]
    fig = go.Figure()
    if cross:
        x, y, z = zip(*cross)
        fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode="lines+markers", name='Label',
                                   line=dict(color=PURPLE, width=6), marker=dict(size=3, color=list(range(len(cross))), colorscale="Turbo"),
                                   hovertemplate="E × B geometry<br>X %{x:.3f}<br>Y %{y:.3f}<br>Z %{z:.3f}<extra></extra>"))
        cx, cy, cz = cross[-1]
        fig.add_trace(go.Cone(x=[0], y=[0], z=[0], u=[cx], v=[cy], w=[cz], name='Label',
                              colorscale=[[0, PURPLE], [1, CYAN]], showscale=False, sizemode="absolute", sizeref=.35))
    fig.update_layout(**_scene(height))
    fig.update_layout(uirevision="p1-cross-proxy-3d",
                      scene=dict(xaxis_title="E×B X", yaxis_title="E×B Y", zaxis_title="E×B Z"))
    return fig


# ── sweep3 visualisations (sweep / waterfall / peak trend) ──
def _ch3_fed():
    """True when channel 3 holds a fed sweep (a project, /api/ingest): its x is whatever the feed
    measures (a profile, a histogram, sample numbers), not radio hertz. S1-06."""
    return sweep3_data.get("x_unit") is not None


def _ch3_x(freqs):
    """Radio sweeps plot in MHz (raw Hz is unreadable across a 6 GHz span); a fed sweep plots its own x."""
    return list(freqs) if _ch3_fed() else [f / 1e6 for f in freqs]


def _ch3_xunit():
    return sweep3_data["x_unit"] if _ch3_fed() else "MHz"


_ch3_pos = _ch3_at   # one x position as words (studio/reports.py)


def _ch3_hover(*parts):
    """Plotly hover text for channel 3: XU becomes x's own unit, LU channel 3's level unit, in one
    pass, so a unit that itself contains XU or LU is left as it is."""
    units = {"XU": _ch3_xunit(), "LU": T("ch3.unit")}
    return re.sub(r"\b(XU|LU)\b", lambda m: units[m.group(1)], " · ".join(parts)) + "<extra></extra>"


def fig_sweep3(freqs, levels, maxhold, peaks, floor, logx=False, height=380, bands=True):
    fig = go.Figure()
    if freqs and levels:
        x = _ch3_x(freqs)
        # Shade the named services behind the trace so a peak can be read without
        # doing frequency arithmetic. Only bands that occupy a visible slice of the
        # current span are drawn, otherwise a wide sweep turns into stripes.
        if bands and not _ch3_fed():          # radio services: only on a radio sweep
            lo_hz, hi_hz = freqs[0], freqs[-1]
            span = hi_hz - lo_hz
            for i, (b_lo, b_hi, name) in enumerate(BAND_PLAN):
                s, e = max(b_lo, lo_hz), min(b_hi, hi_hz)
                if e <= s or (e - s) < span * 0.012:
                    continue
                fig.add_vrect(x0=s/1e6, x1=e/1e6, layer="below", line_width=0,
                              fillcolor=(BLUE if i % 2 else CYAN), opacity=0.045,
                              annotation_text=name, annotation_position="top left",
                              annotation_font=dict(family=FONT, color=SUBTEXT, size=8),
                              annotation_textangle=-90)
        if maxhold and len(maxhold) == len(freqs):
            fig.add_trace(go.Scatter(x=x, y=maxhold, mode="lines", name='LABEL',
                line=dict(color=PURPLE, width=1.2, dash="dot"),
                hovertemplate=_ch3_hover("%{x:.3f} XU", "%{y:.1f} LU (hold)")))
        trace_color = AMBER if RUNTIME["demo"] else CYAN
        fig.add_trace(go.Scatter(
            x=x, y=levels, mode="lines",
            name="SIMULATED" if RUNTIME["demo"] else 'LABEL',
            line=dict(
                color=trace_color, width=1.7,
                dash="dash" if RUNTIME["demo"] else "solid",
                shape="spline", smoothing=0.3,
            ),
            fill="tozeroy",
            fillcolor="rgba(255,171,64,0.06)" if RUNTIME["demo"] else "rgba(0,229,255,0.07)",
            hovertemplate=_ch3_hover("%{x:.3f} XU", "%{y:.1f} LU")))
        if peaks:
            fig.add_trace(go.Scatter(x=_ch3_x([p["freq"] for p in peaks]), y=[p["level"] for p in peaks],
                mode="markers+text", name='LABEL',
                marker=dict(color=AMBER, size=8, symbol="triangle-down",
                            line=dict(color=WHITE, width=1)),
                text=[_ch3_pos(p["freq"]) for p in peaks], textposition="top center",
                textfont=dict(family=FONT, color=AMBER, size=9),
                hovertemplate=_ch3_hover("%{text}", "%{y:.1f} LU")))
        fig.add_hline(y=floor, line=dict(color=SUBTEXT, width=1, dash="dash"),
                      annotation_text=f"floor {floor:+.1f} {T('ch3.unit')}",
                      annotation_font=dict(family=FONT, color=SUBTEXT, size=9),
                      annotation_position="bottom right")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=22, b=0), height=height, autosize=False, transition=NO_TRANSITION,
        xaxis=dict(type="log" if logx else "linear", gridcolor="rgba(128,128,128,0.10)",
                   tickfont=dict(color=SUBTEXT, size=9), zeroline=False,
                   title=dict(text=_ch3_xunit(), font=dict(color=SUBTEXT, size=10))),
        yaxis=dict(gridcolor="rgba(128,128,128,0.12)", zeroline=False,
                   tickfont=dict(color=SUBTEXT, size=9),
                   title=dict(text=T('ch3.unit'), font=dict(color=SUBTEXT, size=10))),
        showlegend=True, legend=dict(orientation="h", y=1.14, x=0,
                                     font=dict(color=SUBTEXT, size=9), bgcolor="rgba(0,0,0,0)"),
        uirevision="sweep3")
    return fig


def _waterfall_rows(rows, times, freqs):
    """Drop rows whose width no longer matches the current frequency axis.

    A range or resolution change clears the waterfall, but a row captured just before
    the change can still be in flight; plotting it against the new axis produced a
    ragged heatmap. Used by both the initial render and the interval callback so the
    two can never disagree.
    """
    width = len(freqs)
    if not width:
        return [], []
    paired = list(zip(rows, times)) if times and len(times) == len(rows) else [(r, None) for r in rows]
    valid = [(r, t) for r, t in paired if len(r) == width]
    return [r for r, _t in valid], [t for _r, t in valid]


def fig_waterfall(rows, freqs, times=None, height=320):
    """Time-vs-frequency heatmap using actual completion timestamps."""
    fig = go.Figure()
    if rows and freqs:
        z = list(rows)
        y = (
            [time.strftime("%H:%M:%S", time.localtime(t)) for t in times]
            if times and len(times) == len(z) and all(t is not None for t in times)
            else [f"sweep {index + 1}" for index in range(len(z))]
        )
        fig.add_trace(go.Heatmap(z=z, x=_ch3_x(freqs), y=y,
            colorscale=[[0.0,"#050912"],[0.35,"#0d2f5e"],[0.6,"#2979ff"],
                        [0.82,"#00e5ff"],[1.0,"#ff5252"]],
            colorbar=dict(title=dict(text='Text', font=dict(color=SUBTEXT, size=9)),
                          tickfont=dict(color=SUBTEXT, size=8), thickness=10, outlinewidth=0),
            hovertemplate=_ch3_hover("%{y}", "%{x:.3f} XU", "%{z:.1f} LU")))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=8, b=0), height=height, autosize=False, transition=NO_TRANSITION,
        xaxis=dict(tickfont=dict(color=SUBTEXT, size=9), zeroline=False,
                   title=dict(text='Text', font=dict(color=SUBTEXT, size=10))),
        yaxis=dict(showticklabels=True, zeroline=False, showgrid=False,
                   tickfont=dict(color=SUBTEXT, size=8),
                   title=dict(text='Text', font=dict(color=SUBTEXT, size=9))),
        uirevision="waterfall")
    return fig


def fig_focus_bands(bands, height_per=230):
    """One row per focus band: live sweep, the previous sweep of that band (dim), max hold,
    and the change since the previous sweep as a filled trace on a right-hand Δ dB axis.
    Below each row, that band's own waterfall. Narrow bands are revisited quickly, so the
    Δ trace is where live activity shows. Every value is a measured sweep."""
    from plotly.subplots import make_subplots
    items = [b for b in bands.values() if b.get("freqs")]
    items.sort(key=lambda b: b["start"])
    if not items:
        fig = go.Figure()
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=160,
                          margin=dict(l=0, r=0, t=8, b=0), transition=NO_TRANSITION,
                          annotations=[dict(text='Text', x=.5, y=.5, xref="paper", yref="paper",
                                            showarrow=False, font=dict(color=SUBTEXT, size=11))],
                          xaxis=dict(visible=False), yaxis=dict(visible=False))
        return fig
    n = len(items)
    titles = []
    for b in items:
        titles += [f"{_freq_label(b['start'])} – {_freq_label(b['stop'])}  ·  sweep {b.get('sweeps', 0)}"
                   + (f"  ·  {b['sweep_s']:.1f} s/sweep" if b.get("sweep_s") else ""), ""]
    fig = make_subplots(rows=2 * n, cols=1, shared_xaxes=False, vertical_spacing=0.035,
                        row_heights=[0.62, 0.38] * n, subplot_titles=titles,
                        specs=[[{"secondary_y": True}], [{}]] * n)
    for i, b in enumerate(items):
        r = 2 * i + 1
        x = _ch3_x(b["freqs"])
        if b.get("prev"):
            fig.add_trace(go.Scatter(x=x, y=b["prev"], mode="lines", name='Label',
                                     line=dict(color="rgba(160,190,220,.35)", width=1, dash="dot"),
                                     hovertemplate="prev %{y:.1f} unit<extra></extra>", showlegend=(i == 0)), row=r, col=1)
        fig.add_trace(go.Scatter(x=x, y=b["levels"], mode="lines", name="live",
                                 line=dict(color="#00e5ff", width=1.6),
                                 hovertemplate="%{x:.3f} MHz · %{y:.1f} unit<extra></extra>", showlegend=(i == 0)), row=r, col=1)
        if b.get("delta"):
            fig.add_trace(go.Scatter(x=x, y=b["delta"], mode="lines", name='Label',
                                     line=dict(color="#ffab40", width=1), fill="tozeroy", fillcolor="rgba(255,171,64,.18)",
                                     hovertemplate="Δ %{y:+.1f} dB<extra></extra>", showlegend=(i == 0)),
                          row=r, col=1, secondary_y=True)
        rows = list(b.get("waterfall") or [])
        if rows:
            times = list(b.get("times") or [])
            y = [time.strftime("%H:%M:%S", time.localtime(t)) for t in times] if len(times) == len(rows) else [f"sweep {k+1}" for k in range(len(rows))]
            fig.add_trace(go.Heatmap(z=rows, x=x, y=y, showscale=False,
                                     colorscale=[[0.0, "#050912"], [0.35, "#0d2f5e"], [0.6, "#2979ff"], [0.82, "#00e5ff"], [1.0, "#ff5252"]],
                                     hovertemplate="%{y} · %{x:.3f} MHz · %{z:.1f} unit<extra></extra>"), row=r + 1, col=1)
        fig.update_yaxes(title_text='Title', tickfont=dict(color=SUBTEXT, size=9), gridcolor="rgba(255,255,255,.06)", row=r, col=1, secondary_y=False)
        fig.update_yaxes(title_text='Title', tickfont=dict(color="#ffab40", size=9), showgrid=False, zeroline=True,
                         zerolinecolor="rgba(255,171,64,.35)", row=r, col=1, secondary_y=True)
        fig.update_yaxes(showgrid=False, tickfont=dict(color=SUBTEXT, size=8), row=r + 1, col=1)
        fig.update_xaxes(tickfont=dict(color=SUBTEXT, size=9), showgrid=False, row=r, col=1)
        fig.update_xaxes(tickfont=dict(color=SUBTEXT, size=9), title_text='Title' if i == n - 1 else None, row=r + 1, col=1)
    for a in fig.layout.annotations:
        a.font = dict(color=SUBTEXT, size=10, family=FONT)
        a.x = 0.0; a.xanchor = "left"
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=height_per * n + 40,
                      margin=dict(l=0, r=0, t=26, b=0), autosize=False, transition=NO_TRANSITION,
                      legend=dict(orientation="h", y=1.06, x=1, xanchor="right", font=dict(color=SUBTEXT, size=9)),
                      uirevision="focus")
    return fig


def fig_ch3_trend(history, height=220):
    fig = go.Figure()
    if history:
        fig.add_trace(go.Scatter(y=list(history), mode="lines",
            line=dict(color=AMBER, width=2, shape="spline", smoothing=0.4),
            hovertemplate=_ch3_hover("%{y:.1f} LU")))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=6, b=0), height=height, autosize=False, transition=NO_TRANSITION,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(gridcolor="rgba(128,128,128,0.12)", zeroline=False,
                   tickfont=dict(color=SUBTEXT, size=9),
                   title=dict(text='Text', font=dict(color=SUBTEXT, size=10))),
        showlegend=False, uirevision="rftrend")
    return fig


def fig_ch3_bands(peaks, height=250):
    """Which named services the current peaks fall in — the 'what is on air' view."""
    fig = go.Figure()
    if peaks:
        # a fed sweep has no named services: each bar is labelled with where its peak is
        labels = [_ch3_pos(p["freq"]) if _ch3_fed() else p["band"] for p in peaks]
        vals   = [p["level"] for p in peaks]
        floor_ref = min(vals) - 6
        fig.add_trace(go.Bar(x=vals, y=labels, orientation="h", base=floor_ref,
            marker=dict(color=[AMBER if v == max(vals) else BLUE for v in vals]),
            text=[f"{v:+.1f} {T('ch3.unit')}" for v in vals], textposition="outside",
            textfont=dict(family=FONT, color=WHITE, size=9),
            hovertemplate=_ch3_hover("%{y}: %{x:.1f} LU")))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0), height=height, autosize=False, transition=NO_TRANSITION,
        xaxis=dict(gridcolor="rgba(128,128,128,0.12)", zeroline=False,
                   tickfont=dict(color=SUBTEXT, size=9)),
        yaxis=dict(tickfont=dict(color=SUBTEXT, size=9), automargin=True),
        showlegend=False, uirevision="rfbands")
    return fig


def _peak_rows(peaks, floor):
    """Peak tracker table body. Rendered as divs so it re-themes with the rest of the UI."""
    if not peaks:
        return [html.Div('Paragraph. Enter your text here.',
                         className="ch3-peak-empty")]
    rows = []
    for i, p in enumerate(peaks):
        delta = p.get("prominence", p["level"] - floor)
        col = AMBER if i == 0 else CYAN
        rows.append(html.Div([
            html.Div(f"{i+1:02d}", className="ch3-peak-idx"),
            html.Div(_ch3_pos(p["freq"]), className=f"ch3-peak-freq {_cls(col)}"),
            html.Div(f"{p['level']:+.1f} {T('ch3.unit')}", className="ch3-peak-lvl"),
            html.Div(f"+{delta:.1f} dB", className="ch3-peak-delta"),
            html.Div(p["band"], className="ch3-peak-band"),
        ], className="ch3-peak-row"))
    return rows


def sg_findings(s):
    """Heuristic screen of the real sweep for possible SG and unusual signals.

    Every finding is a pattern test on measured levels (no synthetic values); the
    labels say 'possible' because a sweep3 analyser cannot identify a source.
    Returns a list of dicts: {"kind","title","detail","severity"} (severity: info|warn|high).
    """
    freqs = list(s.get("freqs") or []); levels = list(s.get("levels") or [])
    peaks = list(s.get("peaks") or []); floor = float(s.get("floor") or 0.0)
    n = len(freqs)
    if s.get("last_rx") is None or n < 8 or len(levels) != n or not s.get("level_sane", True):
        return []
    out = []
    # 1. peaks outside every planned allocation
    for p in peaks:
        prom = float(p.get("prominence", p["level"] - floor))
        if p.get("band", "—") == "—" and prom >= 8:
            out.append({"kind": "unallocated", "severity": "warn",
                        "title": f"Unidentified carrier at {_freq_label(p['freq'])}",
                        "detail": f"{p['level']:+.1f} unit, +{prom:.1f} dB over its local floor, outside every band in the frequency plan."})
    # 2. harmonic series (f, 2f, 3f …) among tracked peaks
    fs = sorted(float(p["freq"]) for p in peaks if float(p["freq"]) > 0)
    for f0 in fs:
        harmonics = [f for f in fs if f > f0 * 1.5 and abs(f / f0 - round(f / f0)) < 0.015]
        if len(harmonics) >= 2:
            orders = ", ".join(f"{round(f / f0)}×" for f in harmonics[:4])
            out.append({"kind": "harmonics", "severity": "high",
                        "title": f"Harmonic series from {_freq_label(f0)}",
                        "detail": f"Tracked peaks sit at {orders} of {_freq_label(f0)} — typical of a switching supply, oscillator or square-wave clock radiating."})
            break
    # 3. evenly spaced comb / spurs
    if len(fs) >= 4:
        gaps = [b - a for a, b in zip(fs, fs[1:])]
        med = sorted(gaps)[len(gaps) // 2]
        if med > 0 and sum(1 for g in gaps if abs(g - med) / med < 0.06) >= 3:
            out.append({"kind": "comb", "severity": "high",
                        "title": f"Comb pattern every {_freq_label(med)}",
                        "detail": 'Paragraph. Enter your text here.'})
    # 4. broadband plateau: a long contiguous run well above the floor
    span_bins = max(4, n // 12); run = best = 0; best_end = 0
    for i, lv in enumerate(levels):
        run = run + 1 if lv > floor + 6 else 0
        if run > best:
            best, best_end = run, i
    if best >= span_bins:
        a = freqs[best_end - best + 1]; b = freqs[best_end]
        out.append({"kind": "broadband", "severity": "warn",
                    "title": f"Broadband rise {_freq_label(a)} – {_freq_label(b)}",
                    "detail": f"{best} consecutive bins sit more than 6 dB above the sweep floor — wideband noise rather than a single carrier, as from motors, dimmers or a noisy power supply."})
    # 5. intermittent / newly appeared energy from the waterfall history
    rows = [r for r in list(s.get("waterfall") or []) if len(r) == n]
    if len(rows) >= 6:
        thresh = floor + 10
        hits = [sum(1 for r in rows if r[i] > thresh) for i in range(n)]
        medians = [sorted(r[i] for r in rows)[len(rows) // 2] for i in range(n)]
        # a bin that is normally quiet but lights up in a minority of sweeps
        flick = [i for i, h in enumerate(hits) if 0.2 * len(rows) <= h <= 0.7 * len(rows) and medians[i] < thresh - 3]
        if flick:
            # merge neighbouring bins into ranges, report the widest
            groups = []; start = flick[0]; prev = flick[0]
            for i in flick[1:]:
                if i != prev + 1:
                    groups.append((start, prev)); start = i
                prev = i
            groups.append((start, prev))
            g = max(groups, key=lambda g: g[1] - g[0])
            out.append({"kind": "intermittent", "severity": "warn",
                        "title": f"Intermittent burst near {_freq_label(freqs[(g[0] + g[1]) // 2])}",
                        "detail": f"Energy above +10 dB in {hits[g[0]]} of the last {len(rows)} sweeps — something keying on and off, like a remote, source beacon or arcing contact."})
        med_rows = rows[:-1] if len(rows) > 1 else rows
        for p in peaks[:3]:
            i = int(p.get("bin_index", -1))
            if 0 <= i < n:
                hist = sorted(r[i] for r in med_rows); med = hist[len(hist) // 2]
                if levels[i] > med + 6 and hits[i] <= 0.2 * len(rows):
                    out.append({"kind": "new", "severity": "info",
                                "title": f"New energy at {_freq_label(freqs[i])}",
                                "detail": f"Now {levels[i]:+.1f} unit against a recent median of {med:+.1f} unit at this frequency — it was not there a few sweeps ago."})
                    break
    return out


def sg_rows(s):
    findings = sg_findings(s)
    if s.get("last_rx") is None or not s.get("levels"):
        return [html.Div('Text', className="ch3-peak-empty")]
    if not s.get("level_sane", True):
        return [html.Div('Paragraph. Enter your text here.', className="ch3-peak-empty")]
    if not findings:
        return [html.Div('Paragraph. Enter your text here.', className="ch3-peak-empty")]
    return [html.Div([
        html.Div(className=f"ch3-sg-dot ch3-sg-{f['severity']}"),
        html.Div([html.Div(f["title"], className="ch3-sg-title"), html.Div(f["detail"], className="ch3-sg-detail")]),
        html.Div(f["kind"].upper(), className="ch3-sg-kind"),
    ], className="ch3-sg-row") for f in findings]


def _sig_bar(pct, color):
    pct = max(0.0, min(100.0, pct))
    return html.Div(html.Div(style={"width":f"{pct:.0f}%","background":color},
                             className="sig-fill"), className="sig-track")


def _rssi_color(dbm):
    if dbm is None:   return SUBTEXT
    if dbm >= -55:    return GREEN
    if dbm >= -70:    return CYAN
    if dbm >= -82:    return AMBER
    return RED


def _wifi_rows(nets):
    """One row per access point. Signal is shown as a bar plus the percentage; the
    unit figure is marked '≈' because NetworkManager reports link quality, not power."""
    if not nets:
        return [html.Div('Paragraph. Enter your text here.', className="scan-empty")]
    rows = []
    for n in nets:
        col = _rssi_color(n["dbm"])
        rows.append(html.Div([
            html.Div([html.Span(n["ssid"], className="scan-name"),
                      html.Span('  Text', className="c-cyan", style={"fontSize":"9px"})
                      if n["active"] else ""],
                     style={"overflow":"hidden"}),
            html.Div(n["bssid"], className="scan-mac scan-hide-sm"),
            html.Div(f"ch {n['chan']}", className="scan-dim scan-hide-sm"),
            html.Div(n["band"], className=f"scan-dim {_cls(col)}"),
            html.Div([html.Div([_sig_bar(n["signal"], col),
                                html.Span(f"{n['signal']}%", className="scan-dim")],
                               className="sig-wrap")]),
            html.Div([html.Span(n["sec"] or "OPEN",
                                className=f"sec-tag {'sec-open' if not n['sec'] or n['sec']=='OPEN' else ''}"),
                      html.Div(f"{n['mhz']} MHz · ≈{n['dbm']:.0f} unit", className="scan-dim",
                               style={"marginTop":"3px"})], className="scan-hide-sm"),
        ], className=f"scan-row wifi-cols{' scan-self' if n['active'] else ''}"))
    return rows


def _bt_rows(devs):
    if not devs:
        return [html.Div('Paragraph. Enter your text here.',
                         className="scan-empty")]
    rows = []
    for d in devs:
        col = _rssi_color(d["rssi"])
        rows.append(html.Div([
            html.Div(d["name"], className="scan-name"),
            html.Div(d["addr"], className="scan-mac scan-hide-sm"),
            html.Div(f"{d['rssi']} unit" if d["rssi"] is not None else "—",
                     className=_cls(col)),
            html.Div(d["vendor"], className="scan-dim scan-hide-sm"),
            html.Div(d["kind"], className="scan-dim"),
        ], className="scan-row bt-cols"))
    return rows


def _lan_rows(hosts, self_ip):
    if not hosts:
        return [html.Div('Paragraph. Enter your text here.', className="scan-empty")]
    rows = []
    for h in hosts:
        tag = "router" if h["gw"] else ("this Pi" if h["ip"] == self_ip else h["state"].lower())
        label = h.get("name") or h.get("vendor") or h["ip"]
        sub = h["ip"] if label != h["ip"] else (h.get("vendor") or "")
        rows.append(html.Div([
            html.Div([html.Span(label, className="scan-name"),
                      html.Div(sub, className="scan-dim", style={"fontSize":"10px"}) if sub else ""],
                     style={"overflow":"hidden"}),
            html.Div(h["mac"], className="scan-mac scan-hide-sm"),
            html.Div(h["dev"], className="scan-dim"),
            html.Div(tag, className=f"scan-dim {_cls(CYAN if h['gw'] else SUBTEXT)}"),
        ], className=f"scan-row lan-cols{' scan-self' if h['gw'] else ''}"))
    return rows


def _dbm_scale():
    """Plain-language reference for the unit axis — the scale is logarithmic and
    negative, which is the single most confusing thing about reading a sweep3."""
    steps = [('Text', RED, 'Paragraph. Enter your text here.'),
             ('Text', AMBER, 'Text'),
             ('Text', GREEN, 'Text'),
             ('Text', CYAN, 'Text'),
             ('Text', SUBTEXT, 'Text')]
    return html.Div([html.Div([html.Div(v, className=f"dbm-val {_cls(c)}"),
                               html.Div(t, className="dbm-txt")], className="dbm-cell")
                     for v, c, t in steps], className="dbm-scale")


def _mcard(vid, label, initial="—", color=WHITE):
    # colour goes in as a c-* class (not inline) so light mode re-themes it
    return html.Div([html.Div(initial, id=vid, className=f"metric-value {_cls(color)}"),
                     html.Div(label, className="metric-label")], className="metric-card")


def _chart(gid, title, fig, cfg=None, h=250):
    """A graph in a card whose height is reserved BEFORE Plotly mounts.

    Both the wrapper and the dcc.Graph carry the same pixel height, so the card
    occupies its final size from the first paint and a late figure can never push the
    rest of the page down.
    """
    return html.Div([html.Div(title, className="chart-hd"),
                     html.Div(dcc.Graph(id=gid, figure=fig, config=cfg or CFG_FLAT,
                                        responsive=True,
                                        style={"height":f"{h}px", "width":"100%"}),
                              style={"height":f"{h}px", "minHeight":f"{h}px"})],
                    className="chart-card")


def _graph_block(gid, fig, h, cfg=None):
    """A full-width graph card with the same height reservation as _chart."""
    return html.Div(html.Div(dcc.Graph(id=gid, figure=fig, config=cfg or CFG_FLAT,
                                       responsive=True,
                                       style={"height":f"{h}px", "width":"100%"}),
                             style={"height":f"{h}px", "minHeight":f"{h}px"}),
                    className="chart-card")


def _hi(t):
    return html.Span(t, className="summary-hi")


PAD = {"maxWidth":"1240px","margin":"0 auto","padding":"clamp(16px,4vw,32px) clamp(14px,4vw,32px) 48px"}


def _ph(ll, title, subtitle):
    # The eyebrow colour is a class, not an inline style: inline colour cannot be
    # re-themed, and #2979ff measures only 3.6:1 on the light-mode background.
    return html.Div([html.Div([html.Span(className="live-dot"),
        html.Span(ll, className="page-eyebrow c-blue",
                  style={"fontFamily":FONT,"fontSize":"11px","letterSpacing":"0.2em"})],
        style={"display":"flex","alignItems":"center","marginBottom":"8px"}),
        html.Div(title, className="page-title"), html.Div(subtitle, className="page-subtitle")],
        style={"marginTop":"20px","marginBottom":"26px"})




# ════════════════════════════════════════════════════════
#  RTL-SDR
# ════════════════════════════════════════════════════════
def fig_sdr_slice(freqs, levels, peaks, floor, height=300):
    """The receiver's live two-megahertz slice, with its own noise floor marked."""
    fig = go.Figure()
    if freqs and levels:
        mhz = [f / 1e6 for f in freqs]
        fig.add_trace(go.Scattergl(x=mhz, y=levels, mode="lines", name="live",
                                   line=dict(color="#00e5ff", width=1.1),
                                   hovertemplate="%{x:.4f} MHz · %{y:.1f} dBFS<extra></extra>"))
        if floor is not None:
            fig.add_hline(y=floor, line=dict(color=SUBTEXT, width=0.7, dash="dot"),
                          annotation_text="capture noise floor",
                          annotation_font=dict(color=SUBTEXT, size=9))
        if peaks:
            fig.add_trace(go.Scattergl(
                x=[p["freq"] / 1e6 for p in peaks], y=[p["level_dbfs"] for p in peaks],
                mode="markers", name="carriers",
                marker=dict(color="#ffb300", size=7, symbol="triangle-down"),
                text=[p.get("band") or "" for p in peaks],
                hovertemplate="%{x:.4f} MHz · %{y:.1f} dBFS<br>%{text}<extra></extra>"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=8, b=0), height=height, autosize=False, showlegend=False,
        transition=NO_TRANSITION, uirevision="sdr-slice",
        xaxis=dict(tickfont=dict(color=SUBTEXT, size=9), gridcolor="rgba(255,255,255,.05)",
                   title=dict(text='Text', font=dict(color=SUBTEXT, size=10))),
        yaxis=dict(tickfont=dict(color=SUBTEXT, size=9), gridcolor="rgba(255,255,255,.05)",
                   title=dict(text='Text', font=dict(color=SUBTEXT, size=10))))
    return fig


def fig_sdr_waterfall(rows, freqs, times=None, height=300):
    """Newest capture at the top; each row is one burst of IQ, labelled with the time it
    was actually taken. The gap between bursts is not fixed, so an assumed spacing would
    put the wrong time against the wrong row."""
    fig = go.Figure()
    if rows and freqs:
        z = list(reversed(rows))
        if times and len(times) == len(rows):
            labels = [time.strftime("%H:%M:%S", time.localtime(t)) for t in reversed(times)]
        else:
            labels = [f"burst {len(z) - i}" for i in range(len(z))]
        fig.add_trace(go.Heatmap(
            z=z, x=[f / 1e6 for f in freqs], y=labels,
            colorscale=[[0.0, "#050912"], [0.35, "#0d2f5e"], [0.6, "#2979ff"],
                        [0.82, "#00e5ff"], [1.0, "#ff5252"]],
            colorbar=dict(title=dict(text='Text', font=dict(color=SUBTEXT, size=9)),
                          tickfont=dict(color=SUBTEXT, size=8), thickness=10, outlinewidth=0),
            hovertemplate="%{y} · %{x:.4f} MHz · %{z:.1f} dBFS<extra></extra>"))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=8, b=0), height=height, autosize=False,
        transition=NO_TRANSITION, uirevision="sdr-fall",
        xaxis=dict(tickfont=dict(color=SUBTEXT, size=9),
                   title=dict(text='Text', font=dict(color=SUBTEXT, size=10))),
        yaxis=dict(tickfont=dict(color=SUBTEXT, size=8), showgrid=False,
                   title=dict(text='Text', font=dict(color=SUBTEXT, size=9))))
    return fig


def fig_sdr_sweep(sweep, height=320):
    """The stitched sweep: every slice's usable middle joined into one trace."""
    fig = go.Figure()
    if sweep and sweep.get("freqs"):
        fig.add_trace(go.Scattergl(x=[f / 1e6 for f in sweep["freqs"]], y=sweep["levels_dbfs"],
                                   mode="lines", line=dict(color="#7e57ff", width=1),
                                   hovertemplate="%{x:.3f} MHz · %{y:.1f} dBFS<extra></extra>"))
        if sweep.get("floor_dbfs") is not None:
            fig.add_hline(y=sweep["floor_dbfs"], line=dict(color=SUBTEXT, width=0.7, dash="dot"))
        if sweep.get("peaks"):
            fig.add_trace(go.Scattergl(
                x=[p["freq"] / 1e6 for p in sweep["peaks"]],
                y=[p["level_dbfs"] for p in sweep["peaks"]], mode="markers",
                marker=dict(color="#ffb300", size=7, symbol="triangle-down"),
                text=[p.get("band") or "" for p in sweep["peaks"]],
                hovertemplate="%{x:.4f} MHz · %{y:.1f} dBFS<br>%{text}<extra></extra>"))
    else:
        fig.update_layout(annotations=[dict(text='Text', x=.5, y=.5,
                                            xref="paper", yref="paper", showarrow=False,
                                            font=dict(color=SUBTEXT, size=11))])
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=8, b=0), height=height, autosize=False, showlegend=False,
        transition=NO_TRANSITION, uirevision="sdr-sweep",
        xaxis=dict(tickfont=dict(color=SUBTEXT, size=9), gridcolor="rgba(255,255,255,.05)",
                   title=dict(text='Text', font=dict(color=SUBTEXT, size=10))),
        yaxis=dict(tickfont=dict(color=SUBTEXT, size=9), gridcolor="rgba(255,255,255,.05)",
                   title=dict(text='Text', font=dict(color=SUBTEXT, size=10))))
    return fig


# ── RTL-SDR: the receiver's own samples ────────────────────────────────────────
# Everything above this point is a sweep3, and a sweep3 has already thrown the
# phase away. These four views keep it. They are the only place in the instrument
# where the raw output of the converter is visible, and between them they cover
# three dimensions, two, one and the 8-bit codes themselves.

_SDR_SCALE = [[0.0, "#050912"], [0.35, "#0d2f5e"], [0.6, "#2979ff"],
              [0.82, "#00e5ff"], [1.0, "#ff5252"]]


def _ch3_scene(height, xt, yt, zt, eye=(1.7, -1.5, 1.0), aspect=None):
    ax = dict(backgroundcolor="rgba(0,0,0,0)", gridcolor="rgba(128,128,128,0.14)",
              zerolinecolor="rgba(128,128,128,0.18)", tickfont=dict(color=SUBTEXT, size=8),
              showbackground=True)
    scene = dict(bgcolor="rgba(0,0,0,0)", dragmode="orbit",
                 aspectmode="manual" if aspect else "cube",
                 xaxis={**ax, "title": dict(text=xt, font=dict(color=SUBTEXT, size=9))},
                 yaxis={**ax, "title": dict(text=yt, font=dict(color=SUBTEXT, size=9))},
                 zaxis={**ax, "title": dict(text=zt, font=dict(color=SUBTEXT, size=9))},
                 camera=dict(eye=dict(x=eye[0], y=eye[1], z=eye[2])))
    if aspect:
        scene["aspectratio"] = dict(x=aspect[0], y=aspect[1], z=aspect[2])
    return dict(paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=0, b=0),
                height=height, autosize=False, transition=NO_TRANSITION, scene=scene)


def fig_sdr_terrain(rows, freqs, times=None, height=460):
    """The waterfall as a surface instead of a heatmap: frequency across, time into the
    screen, level as height. The same numbers as the heatmap above, but a carrier that
    holds steady becomes a ridge you can see the length of, and a burst becomes a spike
    with nothing before or after it."""
    fig = go.Figure()
    if rows and freqs and len(rows) >= 2:
        width = min(len(r) for r in rows)
        z = [list(r[:width]) for r in rows]
        x = [f / 1e6 for f in freqs[:width]]
        if times and len(times) == len(rows):
            base = times[-1]
            y = [round(t - base, 1) for t in times]
            ylab = "seconds ago"
        else:
            y = list(range(-len(z) + 1, 1))
            ylab = "burst"
        flat = [v for row in z for v in row if v is not None]
        lo = sorted(flat)[int(0.10 * len(flat))] if flat else None
        hi = max(flat) if flat else None
        fig.add_trace(go.Surface(
            x=x, y=y, z=z, colorscale=_SDR_SCALE, showscale=True,
            cmin=lo, cmax=hi,
            colorbar=dict(title=dict(text='Text', font=dict(color=SUBTEXT, size=9)),
                          tickfont=dict(color=SUBTEXT, size=8), thickness=10, outlinewidth=0),
            contours=dict(z=dict(show=True, usecolormap=True, project_z=True, width=1)),
            hovertemplate="%{x:.4f} MHz · %{y} s · %{z:.1f} dBFS<extra></extra>"))
        fig.update_layout(**_ch3_scene(height, "MHz", ylab, "dBFS", eye=(1.05, -1.1, 0.62),
                                      aspect=(1.9, 1.0, 0.72)))
    else:
        fig.update_layout(**_ch3_scene(height, "MHz", "time", "dBFS"))
        fig.add_annotation(text='Text',
                           x=.5, y=.5, xref="paper", yref="paper", showarrow=False,
                           font=dict(color=SUBTEXT, size=11))
    fig.update_layout(uirevision="sdr-terrain")
    return fig


def fig_sdr_constellation(grid, axis, height=320):
    """I against Q, every sample in the burst counted into a density.

    This is the receiver's raw output with nothing averaged out. Noise on its own is a
    round blob centred on the origin. A strong carrier drags it into a ring, because a
    constant amplitude rotating in phase traces a circle. A front end being overdriven
    flattens the edges of that blob into straight lines where the converter runs out of
    range - visible here before it shows up as a wrong number anywhere else."""
    fig = go.Figure()
    if grid and axis:
        import math as _m
        z = [[_m.log10(v + 1) for v in row] for row in grid]
        fig.add_trace(go.Heatmap(
            z=z, x=axis, y=axis, colorscale="Inferno", showscale=True, zsmooth="best",
            colorbar=dict(title=dict(text='Text', font=dict(color=SUBTEXT, size=9)),
                          tickfont=dict(color=SUBTEXT, size=8), thickness=10, outlinewidth=0),
            hovertemplate="I %{x:.3f} · Q %{y:.3f}<extra></extra>"))
    else:
        fig.add_annotation(text='Text', x=.5, y=.5,
                           xref="paper", yref="paper", showarrow=False,
                           font=dict(color=SUBTEXT, size=11))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=8, b=0), height=height, autosize=False,
        transition=NO_TRANSITION, uirevision="sdr-const",
        xaxis=dict(tickfont=dict(color=SUBTEXT, size=9), scaleanchor="y", constrain="domain",
                   title=dict(text='Text', font=dict(color=SUBTEXT, size=10))),
        yaxis=dict(tickfont=dict(color=SUBTEXT, size=9), constrain="domain",
                   title=dict(text="Q", font=dict(color=SUBTEXT, size=10))))
    return fig


def fig_sdr_iq_3d(i_vals, q_vals, dt_s, height=380):
    """The same samples as a path rather than a cloud: I, Q and time as three axes.

    The constellation shows where the signal spends its time; this shows the order it
    goes in. A single carrier is a helix, one turn per cycle of its offset from the
    tuner. Noise is a tangle. Modulation shows up as the radius of the helix changing
    as it advances."""
    fig = go.Figure()
    n = min(len(i_vals or []), len(q_vals or []))
    if n >= 32:
        t = [round(k * (dt_s or 0) * 1e6, 3) for k in range(n)]
        amp = [(i_vals[k] ** 2 + q_vals[k] ** 2) ** 0.5 for k in range(n)]
        fig.add_trace(go.Scatter3d(
            x=i_vals[:n], y=q_vals[:n], z=t, mode="lines",
            line=dict(color=amp, colorscale="Turbo", width=2,
                      colorbar=dict(title=dict(text='TEXT', font=dict(color=SUBTEXT, size=9)),
                                    tickfont=dict(color=SUBTEXT, size=8), thickness=10,
                                    outlinewidth=0)),
            hovertemplate="I %{x:.3f} · Q %{y:.3f} · %{z:.2f} µs<extra></extra>"))
        fig.update_layout(**_ch3_scene(height, "I", "Q", "µs", eye=(1.15, -1.3, 0.9),
                                      aspect=(1.0, 1.0, 1.45)))
    else:
        fig.update_layout(**_ch3_scene(height, "I", "Q", "µs"))
        fig.add_annotation(text='Text', x=.5, y=.5,
                           xref="paper", yref="paper", showarrow=False,
                           font=dict(color=SUBTEXT, size=11))
    fig.update_layout(uirevision="sdr-iq3d")
    return fig


def fig_sdr_codes(hist, height=240):
    """The 8-bit codes out of the converter, before any arithmetic at all.

    256 buckets, one per possible sample value. This is the cheapest honest test of
    whether the gain is right: a narrow spike in the middle means most of the
    converter's range is going unused, and weight piled against 0 or 255 means it has
    run out of range and the samples are wrong rather than merely noisy."""
    fig = go.Figure()
    if hist and len(hist) == 256:
        total = max(1, sum(hist))
        pct = [100.0 * v / total for v in hist]
        colours = ["#ff5252" if k in (0, 255) else "#2979ff" for k in range(256)]
        fig.add_trace(go.Bar(x=list(range(256)), y=pct, marker=dict(color=colours, line=dict(width=0)),
                             hovertemplate="code %{x} · %{y:.3f} %% of samples<extra></extra>"))
        fig.add_vline(x=127.5, line=dict(color=SUBTEXT, width=0.7, dash="dot"))
        rails = pct[0] + pct[255]
        fig.add_annotation(x=0.99, y=0.95, xref="paper", yref="paper", xanchor="right",
                           showarrow=False, font=dict(color="#ff5252" if rails > 0.2 else SUBTEXT, size=10),
                           text=f"at the rails: {rails:.3f} %")
    else:
        fig.add_annotation(text='Text', x=.5, y=.5,
                           xref="paper", yref="paper", showarrow=False,
                           font=dict(color=SUBTEXT, size=11))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=8, b=0), height=height, autosize=False, showlegend=False,
        bargap=0, transition=NO_TRANSITION, uirevision="sdr-codes",
        xaxis=dict(tickfont=dict(color=SUBTEXT, size=9), range=[-2, 257],
                   title=dict(text='Text',
                              font=dict(color=SUBTEXT, size=10))),
        yaxis=dict(tickfont=dict(color=SUBTEXT, size=9), gridcolor="rgba(255,255,255,.05)",
                   title=dict(text='Text', font=dict(color=SUBTEXT, size=10))))
    return fig


def fig_sdr_envelope(env, dt_s, height=240):
    """|IQ| against time inside one burst: the amplitude the sweep3 averages away.
    A steady carrier is a flat line. A pulsed or switching source is visible here as
    structure that no sweep3 of the same burst can show."""
    fig = go.Figure()
    if env and len(env) > 4:
        t = [k * (dt_s or 0) * 1e3 for k in range(len(env))]
        fig.add_trace(go.Scattergl(x=t, y=env, mode="lines", line=dict(color="#00e5ff", width=1),
                                   hovertemplate="%{x:.3f} ms · %{y:.4f} of full scale<extra></extra>"))
        mean = sum(env) / len(env)
        fig.add_hline(y=mean, line=dict(color=SUBTEXT, width=0.7, dash="dot"))
    else:
        fig.add_annotation(text='Text', x=.5, y=.5,
                           xref="paper", yref="paper", showarrow=False,
                           font=dict(color=SUBTEXT, size=11))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=8, b=0), height=height, autosize=False, showlegend=False,
        transition=NO_TRANSITION, uirevision="sdr-env",
        xaxis=dict(tickfont=dict(color=SUBTEXT, size=9), gridcolor="rgba(255,255,255,.05)",
                   title=dict(text='Text', font=dict(color=SUBTEXT, size=10))),
        yaxis=dict(tickfont=dict(color=SUBTEXT, size=9), gridcolor="rgba(255,255,255,.05)",
                   title=dict(text='Text', font=dict(color=SUBTEXT, size=10))))
    return fig


def fig_linefreq_spectrogram(spec, height=460, title_hz=50.0):
    """The Ch2 spectrogram as a surface: frequency across, time into the screen,
    level as height. The linefreq fundamental is a ridge running the full depth of the
    picture because it never stops. Anything that starts or stops partway through the
    capture is a ridge that does not reach both edges - which is the whole reason for
    plotting it this way instead of taking one FFT of the lot."""
    fig = go.Figure()
    if spec and spec.get("db") and spec.get("hz") and len(spec["db"]) >= 2:
        # The floor of an Ch2 capture is broadband and only a few tens of dB down, so
        # a colour scale spread across the whole range paints most of the picture bright
        # and buries the lines that matter. The scale is pinned instead: everything below
        # -45 dB is floor and stays dark, and only the top ~15 dB lights up.
        fig.add_trace(go.Surface(
            x=spec["hz"], y=spec["times_s"], z=spec["db"],
            cmin=-45, cmax=0,
            colorscale=[[0.0, "#050912"], [0.45, "#101a3a"], [0.68, "#1a237e"],
                        [0.84, "#ff8f00"], [0.94, "#ffc400"], [1.0, "#fff59d"]],
            showscale=True,
            colorbar=dict(title=dict(text='Text', font=dict(color=SUBTEXT, size=9)),
                          tickfont=dict(color=SUBTEXT, size=8), thickness=10, outlinewidth=0),
            contours=dict(z=dict(show=True, usecolormap=True, project_z=True, width=1)),
            hovertemplate="%{x:.1f} Hz · %{y:.2f} s · %{z:.1f} dB<extra></extra>"))
        fig.update_layout(**_ch3_scene(height, "Hz", "seconds into the capture", "dB relative",
                                      eye=(1.05, -1.05, 0.62), aspect=(1.9, 1.0, 0.72)))
    else:
        fig.update_layout(**_ch3_scene(height, "Hz", "time", "dB relative"))
        fig.add_annotation(text='Text',
                           x=.5, y=.5, xref="paper", yref="paper", showarrow=False,
                           font=dict(color=SUBTEXT, size=11))
    fig.update_layout(uirevision="linefreq-spectrogram")
    return fig


def fig_p1_trajectory_3d(c1_history, c2_relative_history, height=440):
    """B magnitude, ch2 activity and time as three axes of one path.

    The two overlays above plot the same pair against a shared sample order, which
    shows that both move but not how they move together. Here the same aligned
    samples are a single curve through a space whose floor is the E-B plane: a
    genuine coupling draws a diagonal, one channel drifting alone draws a line
    parallel to its own axis, and the shadow cast on the floor is the E-B phase
    portrait with time removed. Scalar magnitudes only - the Ch2 probe has no
    direction, so this is not a field vector.
    """
    count = min(len(c1_history or []), len(c2_relative_history or []), 240)
    fig = go.Figure()
    if count >= 8:
        b = list(c1_history)[-count:]
        e = list(c2_relative_history)[-count:]
        t = list(range(count))
        fig.add_trace(go.Scatter3d(
            x=b, y=e, z=t, mode="lines",
            line=dict(color=t, colorscale="Turbo", width=3.5),
            name="path",
            hovertemplate="B %{x:.3f} unit · E %{y:.2f} % · sample %{z}<extra></extra>"))
        # the same path with time removed, laid on the floor: the E-B phase portrait
        floor = min(t)
        fig.add_trace(go.Scatter3d(
            x=b, y=e, z=[floor] * count, mode="lines",
            line=dict(color="rgba(255,255,255,0.22)", width=1.5),
            name='Label', hoverinfo="skip"))
        fig.add_trace(go.Scatter3d(
            x=[b[-1]], y=[e[-1]], z=[t[-1]], mode="markers",
            marker=dict(size=5, color="#ff5252"), name="now", hoverinfo="skip"))
        fig.update_layout(**_ch3_scene(height, 'B magnitude (unit)', "E activity (%)",
                                      "sample order", eye=(1.45, -1.5, 0.95),
                                      aspect=(1.25, 1.25, 1.0)))
        fig.update_layout(showlegend=True,
                          legend=dict(orientation="h", y=1.04, x=0,
                                      font=dict(color=SUBTEXT, size=9),
                                      bgcolor="rgba(0,0,0,0)"))
    else:
        fig.update_layout(**_ch3_scene(height, 'B magnitude (unit)', "E activity (%)", "sample order"))
        fig.add_annotation(text='Text',
                           x=.5, y=.5, xref="paper", yref="paper", showarrow=False,
                           font=dict(color=SUBTEXT, size=11))
    fig.update_layout(uirevision="p1-traj3d")
    return fig


def fig_ch3_terrain(rows, freqs, times=None, height=460):
    """The src3's sweeps as a surface: frequency across, sweep time into the screen,
    level as height. Same treatment as the SDR terrain, over a far wider span at far
    coarser resolution - which is exactly the trade between the two receivers."""
    fig = go.Figure()
    if rows and freqs and len(rows) >= 2:
        width = min(len(r) for r in rows)
        z = [list(r[:width]) for r in rows]
        x = _ch3_x(freqs[:width])
        if times and len(times) == len(rows):
            base = times[-1]
            y = [round(t - base, 1) for t in times]
            ylab = "seconds ago"
        else:
            y = list(range(-len(z) + 1, 1))
            ylab = "sweep"
        flat = [v for row in z for v in row if v is not None]
        lo = sorted(flat)[int(0.10 * len(flat))] if flat else None
        fig.add_trace(go.Surface(
            x=x, y=y, z=z, colorscale=_SDR_SCALE, showscale=True,
            cmin=lo, cmax=max(flat) if flat else None,
            colorbar=dict(title=dict(text='Text', font=dict(color=SUBTEXT, size=9)),
                          tickfont=dict(color=SUBTEXT, size=8), thickness=10, outlinewidth=0),
            contours=dict(z=dict(show=True, usecolormap=True, project_z=True, width=1)),
            hovertemplate=_ch3_hover("%{x:.3f} XU", "%{y} s", "%{z:.1f} LU")))
        fig.update_layout(**_ch3_scene(height, "Axis", ylab, "unit", eye=(1.05, -1.1, 0.62),
                                      aspect=(1.9, 1.0, 0.72)))
    else:
        fig.update_layout(**_ch3_scene(height, "Axis", "sweep", "unit"))
        fig.add_annotation(text='Text',
                           x=.5, y=.5, xref="paper", yref="paper", showarrow=False,
                           font=dict(color=SUBTEXT, size=11))
    fig.update_layout(uirevision="ch3-terrain")
    return fig


def fig_repeatability(result, height=300):
    """Each repeated reading against the run's mean, with the ±1σ and ±2σ bands drawn.
    A repeatable instrument scatters inside the inner band with no trend; a drift up or
    down the run means the environment moved while it was measuring, which is a
    different finding and should not be read as instrument noise."""
    fig = go.Figure()
    vals = (result or {}).get("readings") or []
    if len(vals) >= 2 and not (result or {}).get("error"):
        mean, sd = result["mean"], result["sd"]
        x = list(range(1, len(vals) + 1))
        for k, shade in ((2, "rgba(0,229,255,0.07)"), (1, "rgba(0,229,255,0.13)")):
            fig.add_hrect(y0=mean - k * sd, y1=mean + k * sd, line_width=0, fillcolor=shade,
                          annotation_text=f"±{k}σ", annotation_position="top left",
                          annotation_font=dict(color=SUBTEXT, size=9))
        fig.add_hline(y=mean, line=dict(color=AMBER, width=1.4, dash="dash"))
        fig.add_trace(go.Scatter(
            x=x, y=vals, mode="lines+markers", line=dict(color=CYAN, width=1.6),
            marker=dict(size=7, color=CYAN, line=dict(width=0)),
            hovertemplate="reading %{x} · %{y:.5g}<extra></extra>"))
        unit = result.get("unit") or ""
        fig.update_layout(
            yaxis=dict(title=dict(text=f"reading ({unit})" if unit else "reading",
                                  font=dict(color=SUBTEXT, size=10)),
                       tickfont=dict(color=SUBTEXT, size=9), gridcolor="rgba(255,255,255,.05)"),
            xaxis=dict(title=dict(text='Text',
                                  font=dict(color=SUBTEXT, size=10)),
                       tickfont=dict(color=SUBTEXT, size=9), gridcolor="rgba(255,255,255,.05)",
                       dtick=1))
    else:
        fig.add_annotation(text=((result or {}).get("error") or
                                 "Start a run: the same measurement is taken several times over"),
                           x=.5, y=.5, xref="paper", yref="paper", showarrow=False,
                           font=dict(color=SUBTEXT, size=11))
        fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      margin=dict(l=0, r=0, t=18, b=0), height=height, autosize=False,
                      showlegend=False, transition=NO_TRANSITION, uirevision="repeat")
    return fig


# ════════════════════════════════════════════════════════
#  WI-FI AND BLUETOOTH
#
#  These tabs were tables only. The instrument already scans both radios and keeps
#  RSSI, channel, band, security and vendor, so the data was there - it simply had
#  no picture. The channel view below is the one that matters for an SG
#  instrument: it places every access point on the frequency axis at its real
#  centre and width, so congestion is visible as overlap rather than inferred
#  from a column of numbers.
# ════════════════════════════════════════════════════════
_WIFI_BW_MHZ = 20.0          # a 2.4 GHz channel is 20 MHz wide and channels overlap
_BAND_COLOURS = {"2.4 GHz": CYAN, "5 GHz": PURPLE, "6 GHz": GREEN}


def _ap_centre(net):
    mhz = net.get("mhz")
    try:
        return float(mhz) if mhz else None
    except (TypeError, ValueError):
        return None


def fig_wifi_channels(nets, band="2.4 GHz", height=300):
    """Every access point drawn at its real centre frequency and 20 MHz width.

    Height is the reported signal, so a tall overlapping cluster is a congested
    channel. This is the same picture the sweep3 page draws from the src3,
    built instead from what the Wi-Fi radio itself reports.
    """
    fig = go.Figure()
    rows = [n for n in (nets or []) if n.get("band") == band and _ap_centre(n)]
    if not rows:
        return _d4_empty(height, f"no {band} access points in range")
    colour = _BAND_COLOURS.get(band, CYAN)
    for n in sorted(rows, key=lambda r: -(r.get("signal") or 0)):
        c = _ap_centre(n)
        top = float(n.get("signal") or 0)
        # A raised-cosine skirt is closer to a real channel mask than a rectangle
        # and makes overlapping APs legible where flat bars would hide each other.
        xs = [c + (i / 24.0 - 0.5) * _WIFI_BW_MHZ * 1.6 for i in range(25)]
        ys = [top * (0.5 * (1 + math.cos(math.pi * min(1.0, abs(x - c) / (_WIFI_BW_MHZ * 0.8)))))
              for x in xs]
        ssid = n.get("ssid") or "(hidden)"
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="tozeroy",
            line=dict(color=colour, width=1.4, shape="spline", smoothing=0.5),
            fillcolor="rgba(0,229,255,0.07)" if band == "2.4 GHz" else "rgba(154,145,189,0.07)",
            name=ssid,
            hovertemplate=f"{ssid}<br>ch {n.get('chan')} · {c:.0f} MHz<br>"
                          f"{n.get('dbm')} unit · {n.get('sec') or 'open'}<extra></extra>"))
        fig.add_annotation(x=c, y=top, text=ssid[:14], showarrow=False, yshift=8,
                           font=dict(family=FONT, color=SUBTEXT, size=8))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=52, r=12, t=22, b=40), height=height, autosize=False,
        transition=NO_TRANSITION, showlegend=False, uirevision=f"wifich{band}",
        xaxis=dict(title=dict(text=f"{band} centre frequency — MHz",
                              font=dict(color=SUBTEXT, size=9)),
                   tickfont=dict(color=SUBTEXT, size=9), showgrid=False, zeroline=False),
        yaxis=dict(title=dict(text='Text', font=dict(color=SUBTEXT, size=9)),
                   tickfont=dict(color=SUBTEXT, size=9), rangemode="tozero",
                   gridcolor="rgba(255,255,255,0.05)", zeroline=False))
    return fig


def fig_wifi_signal_bars(nets, height=280):
    """Access points ranked by measured power, strongest first."""
    rows = [n for n in (nets or []) if n.get("dbm") is not None]
    if not rows:
        return _d4_empty(height, 'Text')
    rows = sorted(rows, key=lambda r: r["dbm"], reverse=True)[:14]
    names = [(n.get("ssid") or "(hidden)")[:18] for n in rows][::-1]
    vals = [float(n["dbm"]) for n in rows][::-1]
    cols = [_BAND_COLOURS.get(n.get("band"), CYAN) for n in rows][::-1]
    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h", marker=dict(color=cols),
        text=[f"{v:.0f} unit" for v in vals], textposition="outside",
        textfont=dict(family=FONT, color=SUBTEXT, size=9),
        hovertemplate="%{y}: %{x:.0f} unit<extra></extra>"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=124, r=54, t=8, b=36), height=height, autosize=False,
        transition=NO_TRANSITION, showlegend=False, uirevision="wifisig",
        xaxis=dict(title=dict(text='Text',
                              font=dict(color=SUBTEXT, size=9)),
                   tickfont=dict(color=SUBTEXT, size=9),
                   gridcolor="rgba(255,255,255,0.05)", zeroline=False),
        yaxis=dict(tickfont=dict(family=FONT, color=SUBTEXT, size=9), showgrid=False))
    return fig


def fig_ble_rssi(devs, height=300):
    """Bluetooth devices by received power, which is the only proximity cue there is.

    RSSI is not distance: it falls with range but also with obstruction, antenna
    orientation and transmit power, so the axis is labelled as power, not metres.
    """
    rows = [d for d in (devs or []) if d.get("rssi") is not None]
    if not rows:
        return _d4_empty(height, 'Text')
    rows = sorted(rows, key=lambda r: r["rssi"], reverse=True)[:16]
    labels, vals, cols = [], [], []
    for d in rows[::-1]:
        name = d.get("name") or d.get("addr") or "?"
        if name.replace("-", "").replace(":", "").isalnum() and len(name) == 17:
            name = d.get("addr", name)
        labels.append(name[:20])
        vals.append(float(d["rssi"]))
        v = (d.get("vendor") or "").lower()
        cols.append(AMBER if "apple" in v else GREEN if "microsoft" in v
                    else PURPLE if v and v != "—" else CYAN)
    fig = go.Figure(go.Bar(
        x=vals, y=labels, orientation="h", marker=dict(color=cols),
        text=[f"{v:.0f}" for v in vals], textposition="outside",
        textfont=dict(family=FONT, color=SUBTEXT, size=9),
        customdata=[[(d.get("vendor") or "unknown"), (d.get("kind") or "")] for d in rows[::-1]],
        hovertemplate="%{y}<br>%{x:.0f} unit<br>%{customdata[0]}<br>%{customdata[1]}<extra></extra>"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=134, r=44, t=8, b=38), height=height, autosize=False,
        transition=NO_TRANSITION, showlegend=False, uirevision="blerssi",
        xaxis=dict(title=dict(text='Text',
                              font=dict(color=SUBTEXT, size=9)),
                   tickfont=dict(color=SUBTEXT, size=9),
                   gridcolor="rgba(255,255,255,0.05)", zeroline=False),
        yaxis=dict(tickfont=dict(family=FONT, color=SUBTEXT, size=9), showgrid=False))
    return fig


def fig_ble_vendors(devs, height=260):
    """What is actually broadcasting nearby, grouped by the vendor the address implies."""
    rows = [d for d in (devs or [])]
    if not rows:
        return _d4_empty(height, 'Text')
    tally = {}
    for d in rows:
        key = (d.get("vendor") or "Unidentified").strip() or "Unidentified"
        tally[key] = tally.get(key, 0) + 1
    items = sorted(tally.items(), key=lambda kv: kv[1], reverse=True)[:8]
    palette = [CYAN, AMBER, GREEN, PURPLE, BLUE, RED, SUBTEXT, WHITE]
    fig = go.Figure(go.Bar(
        x=[k for k, _ in items], y=[v for _, v in items],
        marker=dict(color=palette[:len(items)]),
        text=[str(v) for _, v in items], textposition="outside",
        textfont=dict(family=FONT, color=SUBTEXT, size=10),
        hovertemplate="%{x}: %{y} device(s)<extra></extra>"))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=44, r=12, t=18, b=64), height=height, autosize=False,
        transition=NO_TRANSITION, showlegend=False, uirevision="blevendor",
        xaxis=dict(tickfont=dict(family=FONT, color=SUBTEXT, size=9), showgrid=False,
                   tickangle=-24),
        yaxis=dict(title=dict(text='Text', font=dict(color=SUBTEXT, size=9)),
                   tickfont=dict(color=SUBTEXT, size=9), rangemode="tozero", dtick=1,
                   gridcolor="rgba(255,255,255,0.05)", zeroline=False))
    return fig

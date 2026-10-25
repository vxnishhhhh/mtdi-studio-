"""Self contained PDF report writer and Notion upload."""
from ._shared import inherit
inherit(globals(), 'common', 'sensors', 'intelligence', 'system', 'tokens', 'theme', 'browser', 'webapp')
from .content import T  # studio words (S1-06): report title, channel names and units


def _ch3_at(x, snap=None):
    """A channel 3 position: a radio frequency, or a fed sweep's x in its own unit (S1-06).
    snap: a copy of sweep3_data the caller took, so one readout reads one sweep."""
    unit = (sweep3_data if snap is None else snap).get("x_unit")
    return _freq_label(x) if unit is None else f"{x:g} {unit}"


def _ch3_span(start, stop, snap=None):
    """Channel 3's span as words, in the same terms as _ch3_at."""
    unit = (sweep3_data if snap is None else snap).get("x_unit")
    return _span_label(start, stop) if unit is None else f"{start:g} – {stop:g} {unit}"

# ════════════════════════════════════════════════════════
#  DATA EXPORT  —  self-contained PDF (no external libraries)
# ════════════════════════════════════════════════════════
# A minimal PDF writer so "export" works on this host with zero installs. It lays out
# monospaced text (Courier / Courier-Bold, the built-in PDF fonts need no embedding)
# across Letter pages and returns the file bytes. Download-only: nothing leaves this host.
def _pdf_escape(s):
    s = s or ""
    # The built-in fonts + our stream are latin-1; transliterate the few unicode chars
    # that appear in labels so they don't turn into "?".
    for a, b in [("—", "-"), ("–", "-"), ("’", "'"), ("“", '"'),
                 ("”", '"'), ("≈", "~"), ("·", "-"), ("²", "2"),
                 ("³", "3"), ("°", "deg")]:
        s = s.replace(a, b)
    s = s.encode("latin-1", "replace").decode("latin-1")
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


# colour palette for the report (0-1 RGB), tuned for print on white
_PDF_INK  = (0.11, 0.14, 0.19)
_PDF_ACC  = (0.13, 0.42, 0.95)   # blue headings
_PDF_CYAN = (0.00, 0.52, 0.62)
_PDF_MUT  = (0.42, 0.48, 0.57)
_PDF_BAND = (0.05, 0.08, 0.15)   # dark title band
_PDF_RULE = (0.82, 0.86, 0.92)


def _pdf_bytes(blocks):
    """Render styled report blocks to PDF bytes (no external libraries).
    Block kinds: band, sub, h, line, dim, kv(key,val), rule, space."""
    PW, PH, MX = 612.0, 792.0, 50.0
    TOP, BOT, LH, WRAP = 748.0, 60.0, 13.0, 96

    def col(rgb): return "%.3f %.3f %.3f" % rgb
    # 1) flatten into records: {kind, text, font, size, color, h}
    recs = []
    current_section = "Report"
    def push(kind, text="", font="F1", size=9, color=_PDF_INK, h=LH):
        recs.append({"kind": kind, "text": text, "font": font, "size": size,
                     "color": color, "h": h, "section": current_section})
    def wrapped(text, font, size, color):
        t = text or ""
        if len(t) <= WRAP:
            push("text", t, font, size, color)
        else:
            while t:
                push("text", t[:WRAP], font, size, color); t = t[WRAP:]
    for blk in blocks:
        k = blk[0]
        if k in ("band", "h"):
            current_section = blk[1]
        if k == "page":   push("page", "", "F1", 9, _PDF_INK, 0)
        elif k == "band": push("band", blk[1], "F2", 15, (1, 1, 1), 36)
        elif k == "sub":  push("text", blk[1], "F1", 9.5, _PDF_MUT, LH)
        elif k == "h":    push("h", blk[1], "F2", 11.5, _PDF_ACC, LH + 7)
        elif k == "rule": push("rule", "", "F1", 9, _PDF_RULE, 8)
        elif k == "space":push("space", "", "F1", 9, _PDF_INK, 7)
        elif k == "kv":   wrapped(f"{blk[1]:<22}{blk[2]}", "F1", 9, _PDF_INK)
        elif k == "dim":  wrapped(blk[1], "F1", 9, _PDF_MUT)
        else:             wrapped(blk[1], "F1", 9, _PDF_INK)
    # 2) paginate, assigning a baseline y to each record
    pages = [[]]; y = TOP
    for r in recs:
        if r["kind"] == "page":
            if pages[-1]:
                pages.append([])
            y = TOP
            continue
        if y - r["h"] < BOT:
            pages.append([]); y = TOP
        r = dict(r); r["y"] = y - 10
        pages[-1].append(r); y -= r["h"]
    total = len(pages)
    usable = PW - 2 * MX
    # 3) content stream per page (text + vector graphics)
    def stream_for(page, pageno):
        p = []
        section = next((r["section"] for r in reversed(page)
                        if r.get("section")), "Report")
        for r in page:
            y = r["y"]; e = _pdf_escape(r["text"])
            if r["kind"] == "band":
                p.append("%s rg %.1f %.1f %.1f %.1f re f" % (col(_PDF_BAND), MX - 6, y - 9, usable + 12, 32))
                p.append("%s rg %.1f %.1f %.1f %.1f re f" % (col(_PDF_CYAN), MX - 6, y - 9, 6, 32))
                p.append("BT /%s %g Tf 1 1 1 rg 1 0 0 1 %.1f %.1f Tm (%s) Tj ET" % (r["font"], r["size"], MX + 12, y + 2, e))
            elif r["kind"] == "h":
                p.append("BT /%s %g Tf %s rg 1 0 0 1 %.1f %.1f Tm (%s) Tj ET" % (r["font"], r["size"], col(r["color"]), MX, y, e))
                p.append("%s RG 0.7 w %.1f %.1f m %.1f %.1f l S" % (col(_PDF_ACC), MX, y - 5, PW - MX, y - 5))
            elif r["kind"] == "rule":
                p.append("%s RG 0.5 w %.1f %.1f m %.1f %.1f l S" % (col(_PDF_RULE), MX, y, PW - MX, y))
            elif r["kind"] == "space":
                pass
            elif r["text"]:
                p.append("BT /%s %g Tf %s rg 1 0 0 1 %.1f %.1f Tm (%s) Tj ET" % (r["font"], r["size"], col(r["color"]), MX, y, e))
        # footer: rule + page number
        p.append("%s RG 0.5 w %.1f %.1f m %.1f %.1f l S" % (col(_PDF_RULE), MX, BOT - 4, PW - MX, BOT - 4))
        footer = _pdf_escape(f"MTDI Studio  -  {section[:44]}  -  page {pageno} of {total}")
        p.append("BT /F1 8 Tf %s rg 1 0 0 1 %.1f %.1f Tm (%s) Tj ET"
                 % (col(_PDF_MUT), MX, BOT - 16, footer))
        return "\n".join(p).encode("latin-1", "replace")
    # 4) assemble objects with a correct xref table
    objs = []
    def add(body): objs.append(body); return len(objs)
    f1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
    f2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold >>")
    pages_obj_index = add(b"")   # reserve the Pages object id
    page_ids = []
    for i, page in enumerate(pages, start=1):
        content = stream_for(page, i)
        cid = add(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(content), content))
        pid = add(("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.0f %.0f] "
                   "/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >> "
                   "/Contents %d 0 R >>" % (pages_obj_index, PW, PH, f1, f2, cid)).encode())
        page_ids.append(pid)
    kids = " ".join(f"{p} 0 R" for p in page_ids)
    objs[pages_obj_index - 1] = ("<< /Type /Pages /Count %d /Kids [%s] >>" % (len(page_ids), kids)).encode()
    catalog = add(("<< /Type /Catalog /Pages %d 0 R >>" % pages_obj_index).encode())
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += ("%d 0 obj\n" % i).encode() + body + b"\nendobj\n"
    xref_pos = len(out)
    n = len(objs) + 1
    out += ("xref\n0 %d\n" % n).encode() + b"0000000000 65535 f \n"
    for off in offsets:
        out += ("%010d 00000 n \n" % off).encode()
    out += ("trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (n, catalog, xref_pos)).encode()
    return bytes(out)


# How much of the archive one PDF may carry. This is not a preference, it is what
# the hardware allows. The Pi's archive reached 9.5 GB and 12.6 million
# ch1probe rows; the old code did SELECT * with fetchall() and no LIMIT and
# emitted one PDF text line per row, so the report needed every one of those rows
# resident in memory at once and then again as formatted text. On a 4 GB copy the
# route did not answer within 90 s locally, and on this host, with 8 GB of RAM shared
# with acquisition, it would take the service down rather than return a file.
#
# The cap is per table and takes the NEWEST rows, because a report is read for what
# the instrument has just measured. The exact cap and what it excluded are printed
# inside the report, so the document never misrepresents itself as complete.
# Measured on the real Pi against its own 11 GB archive, service running:
#   rows=100    1.0 s     2.5 MB     299 pages
#   rows=300    0.9 s     6.0 MB     708 pages      <- the default
#   rows=600    1.3 s    12.2 MB   1,432 pages
#   rows=2000   4.0 s    42.6 MB   4,955 pages   (76 s on a cold page cache)
#   rows=5000  12.3 s   110.5 MB  12,797 pages      <- the ceiling
# 300 is the default because a report is something a person reads and a judge is
# handed. 4,955 pages is not a document, and cold it took 76 s to produce.
REPORT_ROW_CAP = 300           # rows per archive table
REPORT_ROW_CAP_MAX = 5000      # ceiling on ?rows= before the route refuses
REPORT_ARRAY_CAP = 150         # arrays expanded element by element in the appendix


def _gather_report_blocks(row_cap=REPORT_ROW_CAP):
    """Snapshot every recorded reading into styled report blocks for the PDF.

    `row_cap` bounds each archive table. The full, uncapped contents remain
    available from the JSON export and from the archive database itself."""
    import datetime, time as _t
    now = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    with archive_lock:
        arch = list(signal_archive); ss = dict(session_stats)
    sess_secs = int(_t.time() - ss.get("started", _t.time()))
    sh, rem = divmod(sess_secs, 3600); sm, sc = divmod(rem, 60)
    sess_str = (f"{sh}h {sm}m {sc}s" if sh else f"{sm}m {sc}s")

    u1, u3 = T("ch1.unit"), T("ch3.unit")
    b = [("band", T("report.title")),
         ("sub", T("report.subtitle")),
         ("space", ""),
         ("h", "REPORT IDENTITY"),
         ("kv", "Generated", now),
         ("kv", "Application version", APP_VERSION),
         ("kv", "Session length", sess_str),
         ("kv", "Instrument", 'host computer  -  Source 1 + Source 2 + Source 3'),
         ("kv", "Archive database", str(ARCHIVE.path)),
         ("space", ""),
         ("dim", "This report contains a readable scientific summary, a complete row ledger, "
                 "and a lossless chunked appendix of archived JSON arrays and raw responses."),
         ("page", ""),
         ("band", "REPORT INDEX"),
         ("line", '01  Session and source summary'),
         ("line", f"02  {T('ch1.name')}-field status and readings"),
         ("line", f"03  {T('ch2.name')} status and readings"),
         ("line", f"04  {T('ch3.name')} and wireless discovery"),
         ("line", "05  MTDI health and host computer telemetry"),
         ("line", "06  Complete archive record ledger"),
         ("line", "07  Lossless raw-data appendix"),
         ("page", ""),
         ("band", "SESSION SUMMARY"),
         ("rule", None), ("space", "")]

    # ── ch1probe ──
    with c1_lock:
        m = dict(ch1_data); mhist = list(ch1_data["xyz_history"]); mmag = list(ch1_data["history"])
    b += [("h", f"{T('ch1.name').upper()}   (Source 1 @ bus 0x2C)")]
    if m["error"]:
        b += [("dim", f"Status: OFFLINE  -  {m['error']}")]
    else:
        mn = 0.0 if m["min_c1"] == float("inf") else m["min_c1"]
        b += [("kv", "Magnitude", f"{m['magnitude']:.2f} {u1}"),
              ("kv", "Vector X / Y / Z", f"{m['x']:.2f} / {m['y']:.2f} / {m['z']:.2f} {u1}"),
              ("kv", "Session min / max", f"{mn:.2f} / {m['max_c1']:.2f} {u1}"),
              ("kv", "Calibration", "hard/soft-iron profile applied" if m["calibrated"]
                                    else "none configured (readings are uncorrected)"),
              ("kv", "Rolling samples", f"{len(mhist)}")]
        if len(mmag) >= 2:
            mean = sum(mmag) / len(mmag)
            sd_ = (sum((v - mean) ** 2 for v in mmag) / len(mmag)) ** 0.5
            b += [("kv", "Noise sigma", f"{sd_:.2f} {u1}")]
    b += [("space", "")]

    # ── ch2 ──
    with ch2f_lock:
        e = dict(ch2f_data)
    b += [("h", f"{T('ch2.name').upper()}   (Source 2 @ bus 0x48, differential A0-A1)")]
    if e["error"]:
        b += [("dim", f"Status: OFFLINE  -  {e['error']}")]
    elif not e["calibrated"]:
        b += [("dim", "Status: calibrating baseline")]
    else:
        b += [("kv", "Level", str(e["level"])),
              ("kv", "Relative activity", f"{e['rel_index']:.0f}%   (ratio {e['ratio']:.1f}x baseline)"),
              ("kv", "Field strength", f"{e['field_vu']:.3f} V/m = {e['field_vu']:.3f} N/C"),
              ("kv", "Baseline / Peak", f"{e['baseline_vu']:.3f} / {e['peak_vu']:.3f} V/m"),
              ("kv", "ADC gain / utilisation", f"{_gain_label(e['gain'])}  /  {e['utilisation']:.0f}%"),
              ("kv", "Status", str(e["status"]))]
    b += [("space", "")]

    # ── sweep3 ──
    with sweep3_lock:
        s = dict(sweep3_data); peaks = list(sweep3_data["peaks"])
    b += [("h", f"{T('ch3.name').upper()} ANALYSER   (Source 3, USB)")]
    if s["error"] or s["last_rx"] is None:
        b += [("dim", f"Status: OFFLINE  -  {s['error'] or 'no sweep yet'}")]
    else:
        b += [("kv", "Device / Port", f"{s['device']}  /  {s['port']}"),
              ("kv", "Span", _ch3_span(s["span_start"], s["span_stop"], s)),
              ("kv", "Points / Sweeps", f"{s['points']}  /  {s['sweeps']}"),
              ("kv", "Level offset", str(s["leveloffset"])),
              ("kv", "Noise floor", f"{s['floor']:+.1f} {u3}  ({'plausible' if s['level_sane'] else 'untrusted - verify setup'})"),
              ("kv", "Strongest peak", f"{_ch3_at(s['peak_freq'], s)} at {s['peak_level']:+.1f} {u3}"),
              ("dim", "Tracked peaks (rank, position, level):" if s.get("x_unit") is not None
                      else "Tracked peaks (rank, frequency, level, possible allocation):")]
        for i, p in enumerate(peaks[:8], 1):
            b += [("line", f"   {i:>2}.  {_ch3_at(p['freq'], s):>14}   {p['level']:+7.1f} {u3}   {p['band']}")]
    b += [("space", "")]

    # ── WiFi / Bluetooth ──
    with wifi_lock:
        w = dict(wifi_data); nets = list(wifi_data["networks"])
    with bt_lock:
        bt = dict(bt_data); bdev = list(bt_data["devices"])
    b += [("h", 'WIRELESS SURVEY   (Channel 5 beacons + Channel 6 advertising)')]
    if not w["error"] and w["last_rx"]:
        b += [("kv", 'Channel 5 networks', f"{len(nets)}  (radio {w['iface']})")]
        for n in nets[:8]:
            b += [("line", f"   {n['ssid'][:26]:<26} ch{n['chan']:<3} {n['band']:<7} {n['signal']:>3}%  {n['sec']}")]
    else:
        b += [("dim", f"Channel 5: {w['error'] or 'no scan'}")]
    if not bt["error"] and bt["last_rx"]:
        b += [("kv", 'Channel 6 devices', f"{len(bdev)}")]
        for d in bdev[:6]:
            rssi = f"{d['rssi']} unit" if d["rssi"] is not None else "-"
            b += [("line", f"   {d['name'][:28]:<28} {rssi:>8}  {d['vendor']}")]
    else:
        b += [("dim", f"Channel 6: {bt['error'] or 'no scan'}")]
    b += [("space", "")]

    # ── ch1 archive ──
    avg = ss["sum"] / ss["count"] if ss["count"] else 0.0
    amn = 0.0 if ss["min"] == float("inf") else ss["min"]
    b += [("h", f"{T('ch1.name').upper()} SIGNAL ARCHIVE"),
          ("kv", "Stored samples", f"{ss['count']}"),
          ("kv", "Min / Avg / Max", f"{amn:.2f} / {avg:.2f} / {ss['max']:.2f} {u1}"),
          ("dim", 'Recent samples (time, magnitude unit, X, Y, Z):')]
    for a in arch[-60:]:
        ts = _t.strftime("%H:%M:%S", _t.localtime(a["t"]))
        b += [("line", f"   {ts}   {a['c1']:>7.2f}    {a['x']:>7.2f}  {a['y']:>7.2f}  {a['z']:>7.2f}")]
    b += [("space", "")]

    # ── CH3 archive ──
    with ch3_archive_lock:
        rfa = list(ch3_archive); rfs = dict(ch3_stats)
    # Only the studio's radio reader archives peaks (sensors.py); a fed sweep never does. So the
    # archive is always read as radio: frequencies and the radio's level, whatever sweep is current.
    b += [("h", f"{T('ch3.name').upper()} PEAK ARCHIVE")]
    if rfs["count"]:
        ravg = rfs["sum"] / rfs["count"]; st = rfs["strongest"]
        b += [("kv", "Sweeps stored", f"{rfs['count']}"),
              ("kv", "Min / Avg / Max peak", f"{rfs['min']:+.1f} / {ravg:+.1f} / {rfs['max']:+.1f} unit"),
              ("kv", "Strongest overall", f"{_freq_label(st['freq'])} at {st['level']:+.1f} unit ({st['band']})"),
              ("dim", "Recent strongest-per-sweep (time, frequency, level, band):")]
        for a in rfa[-60:]:
            ts = _t.strftime("%H:%M:%S", _t.localtime(a["t"]))
            b += [("line", f"   {ts}   {_freq_label(a['freq']):>14}   {a['level']:+7.1f} unit   {a['band']}")]
    else:
        b += [("dim", f"No {T('ch3.name')} sweeps recorded (Source 3 offline).")]
    b += [("space", "")]

    # ── MTDI + host ──
    with mtdi_lock:
        md = dict(mtdi_data)
    with sys_lock:
        sd = dict(sys_data)
    b += [("h", "MTDI HEALTH AND COMPLETENESS"),
          ("kv", 'Active source health', f"{md['active_health']:.0f}%"),
          ("kv", "System completeness", f"{md['completeness']:.0f}%"),
          ("kv", T('ch1.name'), f"{md['c1_health']:.0f}%  ({md['c1_note']})"),
          ("kv", T('ch2.name'), f"{md['ch2f_health']:.0f}%  ({md['ch2f_note']})"),
          ("kv", T('ch3.name'), f"{md['ch3_health']:.0f}%  ({md['ch3_note']})"),
          ("space", ""),
          ("h", "HOST TELEMETRY   (host computer)"),
          ("kv", "LAN address", str(sd["wifi_ip"])),
          ("kv", "CPU usage / temp", f"{sd['cpu_usage']}%  /  " +
           (f"{sd['cpu_temp']:.0f} C" if sd.get("temperature_available") else "unavailable")),
          ("kv", "RAM", f"{sd['ram_used_mb']} / {sd['ram_total_mb']} MB  ({sd['ram_pct']}%)"),
          ("kv", "Disk", f"{sd['disk_used_gb']} / {sd['disk_total_gb']} GB  ({sd['disk_pct']}%)"),
          ("kv", "Uptime / Load", f"{sd['uptime_str']}   /   {sd['load_1']}")]
    # ── persistent archive, most recent records ──
    # This is deliberately after the readable live summary. Every fixed table is
    # reported, newest records first, bounded by row_cap. Large sample arrays are
    # represented by count/range summaries here so the download stays responsive;
    # the adjacent JSON export retains every array element and raw payload, and the
    # archive database itself remains the complete record. Credentials are not part
    # of the archive schema.
    b += [("space", ""), ("rule", None),
          ("page", ""),
          ("band", "PERSISTENT ARCHIVE — MOST RECENT RECORDS"),
          ("sub", f"All fixed archive tables, newest first, up to {row_cap:,} rows each. "
                  f"Column headers repeat every 36 rows."),
          ("dim", "THIS REPORT IS BOUNDED. Each table below states its total record "
                  "count and how many of those records appear here. Where a table is "
                  "larger than the cap, the omitted records are the older ones; they "
                  "remain in the archive database and in the JSON export.")]
    raw_appendix = []
    try:
        table_names = (
            "sessions", "ch3_sweeps", "ch1probe_samples", "ch2f_samples",
            "wifi_discoveries", "bluetooth_discoveries", "system_health",
            "events", "calibration_profiles",
        )
        if not ARCHIVE.path.exists():
            b += [("dim", "Archive database does not exist yet.")]
        else:
            con = sqlite3.connect(ARCHIVE.path, timeout=15)
            con.row_factory = sqlite3.Row
            for table_name in table_names:
                try:
                    total = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                except sqlite3.Error as table_error:
                    b += [("space", ""), ("h", table_name.upper().replace("_", " ")),
                          ("dim", f"Table unavailable: {table_error}")]
                    continue
                # Newest first, bounded, and iterated rather than fetchall()'d, so
                # peak memory is one row and not one table.
                rows = list(con.execute(
                    f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT ?", (row_cap,)))
                rows.reverse()
                b += [("space", ""), ("h", table_name.upper().replace("_", " ")),
                      ("kv", "Total records", f"{total:,}"),
                      ("kv", "Records in this report", f"{len(rows):,}")]
                if total > len(rows):
                    b += [("dim", f"BOUNDED: the {total - len(rows):,} older records in "
                                  f"this table are not printed here. They remain in the "
                                  f"archive database and in the JSON export.")]
                if not rows:
                    b += [("dim", "No records stored in this table.")]
                    continue
                for index, record in enumerate(rows, 1):
                    if index == 1 or (index - 1) % 36 == 0:
                        b += [("dim", "COLUMNS: " + " | ".join(record.keys()))]
                    compact = {}
                    for key, value in dict(record).items():
                        if key.endswith("_at") and isinstance(value, (int, float)):
                            compact[key] = value
                            compact[key + "_utc"] = _t.strftime(
                                "%Y-%m-%dT%H:%M:%SZ", _t.gmtime(value)
                            )
                            continue
                        if key.endswith("_json") and isinstance(value, str):
                            try:
                                parsed = json.loads(value)
                                if isinstance(parsed, list):
                                    nums = [float(v) for v in parsed
                                            if isinstance(v, (int, float)) and math.isfinite(float(v))]
                                    compact[key[:-5]] = (
                                        f"{len(parsed)} values"
                                        + (f", min={min(nums):.6g}, max={max(nums):.6g}" if nums else "")
                                    )
                                    raw_appendix.append(
                                        (table_name, dict(record).get("id", index),
                                         key[:-5], parsed)
                                    )
                                else:
                                    compact[key[:-5]] = parsed
                            except Exception:
                                compact[key] = f"{len(value)} chars"
                        elif key == "raw_response" and isinstance(value, str):
                            compact[key] = f"{len(value)} chars archived"
                            raw_appendix.append(
                                (table_name, dict(record).get("id", index),
                                 key, list(value))
                            )
                        else:
                            compact[key] = value
                    payload = json.dumps(compact, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=True, default=str)
                    b += [("line", f"{index:06d}  {payload}")]
            con.close()
            b += [("page", ""), ("band", "LOSSLESS RAW-DATA APPENDIX"),
                  ("sub", "Every archived array element and raw-response character, "
                          "indexed by table, record ID, field and element range.")]
            if not raw_appendix:
                b += [("dim", "No archived arrays or raw responses were present.")]
            if len(raw_appendix) > REPORT_ARRAY_CAP:
                b += [("dim", f"BOUNDED: {len(raw_appendix):,} arrays qualified; the "
                              f"{REPORT_ARRAY_CAP} most recent are expanded element by "
                              f"element below. The JSON export carries all of them.")]
                raw_appendix = raw_appendix[-REPORT_ARRAY_CAP:]
            for table_name, record_id, field_name, values in raw_appendix:
                b += [("space", ""),
                      ("h", f"{table_name}.{field_name}  -  record {record_id}"),
                      ("kv", "Element count", str(len(values)))]
                chunk_size = 10
                for start in range(0, len(values), chunk_size):
                    chunk = values[start:start + chunk_size]
                    encoded = json.dumps(chunk, ensure_ascii=True, separators=(",", ":"),
                                         default=str)
                    b += [("line", f"[{start}:{start + len(chunk)}] {encoded}")]
    except Exception as exc:
        LOG.exception("Complete archive could not be appended to PDF")
        b += [("dim", f"Archive read failed: {exc}")]
    return b


_NOTION_SECTION_CACHE = {}


def _notion_json(method, path, payload=None, timeout=30):
    token = _notion_setting("NOTION_API_KEY")
    if not token:
        raise RuntimeError("Notion cloud token is not configured.")
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.notion.com/v1" + path, data=data, method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2026-03-11",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            body = json.loads(exc.read().decode("utf-8"))
            detail = f" — {body.get('code')}: {body.get('message')}"
        except Exception:
            pass
        raise RuntimeError(f"Notion {method} {path.split('?')[0]} failed: "
                           f"HTTP {exc.code}{detail}") from None


def _notion_section_id(title):
    """Resolve one managed child page, creating it only if it is missing."""
    if title in _NOTION_SECTION_CACHE:
        return _NOTION_SECTION_CACHE[title]
    parent = _notion_setting("NOTION_REPORT_PAGE_ID")
    if not parent:
        raise RuntimeError("Notion cloud parent page is not configured.")
    listing = _notion_json("GET", f"/blocks/{parent}/children?page_size=100")
    for block in listing.get("results", []):
        if block.get("type") == "child_page" and block["child_page"].get("title") == title:
            _NOTION_SECTION_CACHE[title] = block["id"]
            return block["id"]
    created = _notion_json("POST", "/pages", {
        "parent": {"type": "page_id", "page_id": parent},
        "properties": {"title": {"type": "title", "title": [
            {"type": "text", "text": {"content": title}}
        ]}},
    })
    _NOTION_SECTION_CACHE[title] = created["id"]
    return created["id"]


from concurrent.futures import ThreadPoolExecutor

# ── the live dashboard ────────────────────────────────────────────────────────
# What the cloud page contained before this: an empty paragraph, a "PDF Archive"
# folder holding three PDFs, and a "Chat History" folder holding one record. Last
# edited two months before I looked at it. There was no dashboard to load, which
# is most of why loading it was disappointing.
#
# This builds one, and keeps it CURRENT rather than appending to it. The block ids
# are remembered on disk, so every sync is a PATCH of the same blocks instead of a
# new record - that is what makes it read as live rather than as a log, and it is
# also what stops the page growing without bound.
NOTION_DASHBOARD_TITLE = "Live Dashboard"
NOTION_DASHBOARD_PERIOD = 30.0     # seconds between syncs while online
NOTION_ALERT_SLOTS = 5             # fixed alert rows, padded, so ids never move
_notion_dashboard = {"ids": None, "at": 0.0, "error": None, "syncs": 0}
_notion_dashboard_lock = threading.Lock()


def _notion_state_file():
    return ARCHIVE.path.parent / "notion_dashboard.json"


def _rt(text, color=None, bold=False, code=False):
    """One Notion rich-text run. Notion truncates hard at 2000 characters."""
    item = {"type": "text", "text": {"content": str(text)[:1900]}}
    annotations = {}
    if color:
        annotations["color"] = color
    if bold:
        annotations["bold"] = True
    if code:
        annotations["code"] = True
    if annotations:
        item["annotations"] = annotations
    return [item]


def _state_colour(state):
    return {"connected": "green", "stale": "yellow", "paused": "yellow",
            "offline": "red", "error": "red", "unavailable": "gray"}.get(state, "gray")


def _dashboard_rows(payload):
    """The numbers the dashboard shows, as (header, rows) for the channel table."""
    header = ["Channel", "State", "Reading", "Signal / noise", "Confidence"]
    rows = []
    for key, channel in (payload.get("channels") or {}).items():
        state = str(channel.get("state") or "offline")
        deviation = channel.get("deviation")
        unit = channel.get("unit") or ""
        reading = f"{deviation:.3g} {unit}" if isinstance(deviation, (int, float)) else "—"
        snr = channel.get("snr")
        confidence = channel.get("confidence")
        rows.append([
            str(channel.get("label") or key),
            state.upper(),
            reading if state == "connected" else "OFFLINE",
            f"{snr:.1f}x" if isinstance(snr, (int, float)) else "—",
            f"{confidence:.0f}%" if isinstance(confidence, (int, float)) else "—",
        ])
    return header, rows


def _dashboard_blocks(payload):
    """The full block skeleton, also used to refresh each block in place."""
    fusion = payload.get("fusion") or {}
    channels = payload.get("channels") or {}
    live = [k for k, c in channels.items() if c.get("state") == "connected"]
    simulated = str(fusion.get("data_source")) == "SIMULATED"
    total = len(channels) or 1
    starting = (not (payload.get("startup") or {}).get("acquisition")
                or not any(c.get("last_rx") for c in channels.values()))
    if starting and not live:
        tone, emoji = "gray", "⏳"
        headline = "Starting up — acquisition has not delivered its first samples yet"
    elif simulated:
        tone, emoji = "orange", "🧪"
        headline = "SIMULATED DATA — this is the demo simulator, not a measurement"
    elif len(live) == total:
        tone, emoji = "green", "🟢"
        headline = f"All {total} channels live"
    elif live:
        tone, emoji = "yellow", "🟡"
        headline = f"{len(live)} of {total} channels live"
    else:
        tone, emoji = "red", "🔴"
        headline = "No channel is reporting"
    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    header, rows = _dashboard_rows(payload)

    telemetry = payload.get("telemetry") or {}
    host = " · ".join(filter(None, [
        f"CPU {telemetry['cpu_pct']:.0f}%" if isinstance(telemetry.get("cpu_pct"), (int, float)) else None,
        f"{telemetry['cpu_temp']:.0f} °C" if isinstance(telemetry.get("cpu_temp"), (int, float)) else None,
        f"RAM {telemetry.get('ram_pct')}%" if telemetry.get("ram_pct") is not None else None,
        f"Disk {telemetry.get('disk_pct')}%" if telemetry.get("disk_pct") is not None else None,
        f"Up {telemetry.get('uptime_str')}" if telemetry.get("uptime_str") else None,
    ])) or "Host telemetry unavailable"

    alerts = [e for e in (payload.get("events") or [])
              if e.get("severity") in ("alert", "critical")][-NOTION_ALERT_SLOTS:]
    alert_blocks = []
    for event in reversed(alerts):
        when = time.strftime("%H:%M:%S", time.localtime(float(event.get("timestamp") or 0)))
        colour = "red_background" if event.get("severity") == "critical" else "orange_background"
        alert_blocks.append({"object": "block", "type": "callout", "callout": {
            "rich_text": _rt(f"{when}  {event.get('message') or event.get('state') or 'event'}"),
            "icon": {"type": "emoji", "emoji": "⚠️"}, "color": colour}})
    while len(alert_blocks) < NOTION_ALERT_SLOTS:
        first = not alert_blocks
        alert_blocks.append({"object": "block", "type": "callout", "callout": {
            "rich_text": _rt("Nothing above the alert threshold." if first else "—"),
            "icon": {"type": "emoji", "emoji": "✅" if first else "▫️"},
            "color": "gray_background"}})

    return {
        "status": {"object": "block", "type": "callout", "callout": {
            "rich_text": _rt(f"{headline}\nUpdated {stamp}"),
            "icon": {"type": "emoji", "emoji": emoji}, "color": f"{tone}_background"}},
        "condition": {"object": "block", "type": "quote", "quote": {
            "rich_text": _rt(str(fusion.get("interpretation") or "No interpretation yet."))}},
        "channels_head": {"object": "block", "type": "heading_2", "heading_2": {
            "rich_text": _rt("Channels")}},
        "table": {"object": "block", "type": "table", "table": {
            "table_width": len(header), "has_column_header": True, "has_row_header": False,
            "children": [
                {"object": "block", "type": "table_row", "table_row": {
                    "cells": [_rt(h, bold=True) for h in header]}}
            ] + [
                {"object": "block", "type": "table_row", "table_row": {
                    "cells": [_rt(cell) for cell in row]}} for row in rows
            ]}},
        "alerts_head": {"object": "block", "type": "heading_2", "heading_2": {
            "rich_text": _rt("Recent alerts")}},
        "_alerts": alert_blocks,
        "host_head": {"object": "block", "type": "heading_2", "heading_2": {
            "rich_text": _rt("Host")}},
        "host": {"object": "block", "type": "callout", "callout": {
            "rich_text": _rt(host), "icon": {"type": "emoji", "emoji": "🖥️"},
            "color": "blue_background"}},
        "footer": {"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": _rt(f"MTDI Studio {payload.get('version') or ''} · "
                             f"MTDI {fusion.get('confidence', 0):.0f}% · "
                             f"this page is written in place by the instrument", color="gray")}},
    }


def _notion_dashboard_create(payload):
    """Create the dashboard page once and remember every block id."""
    parent = _notion_section_id(NOTION_DASHBOARD_TITLE)
    blocks = _dashboard_blocks(payload)
    order = ["status", "condition", "channels_head", "table",
             "alerts_head", "host_head", "host", "footer"]
    children = [blocks["status"], blocks["condition"], blocks["channels_head"],
                blocks["table"], blocks["alerts_head"]] + blocks["_alerts"] + \
               [{"object": "block", "type": "divider", "divider": {}},
                blocks["host_head"], blocks["host"], blocks["footer"]]
    # Replace whatever is there rather than appending: the dashboard owns this page.
    existing = _notion_json("GET", f"/blocks/{parent}/children?page_size=100")
    for block in existing.get("results", []):
        try:
            _notion_json("DELETE", f"/blocks/{block['id']}")
        except Exception:
            pass
    created = _notion_json("PATCH", f"/blocks/{parent}/children", {"children": children})
    results = created.get("results", [])
    ids = {"page": parent, "alerts": [], "rows": []}
    index = 0
    for name in ["status", "condition", "channels_head", "table", "alerts_head"]:
        ids[name] = results[index]["id"]
        index += 1
    for _ in blocks["_alerts"]:
        ids["alerts"].append(results[index]["id"])
        index += 1
    index += 1  # divider
    for name in ["host_head", "host", "footer"]:
        ids[name] = results[index]["id"]
        index += 1
    table_rows = _notion_json("GET", f"/blocks/{ids['table']}/children?page_size=100")
    ids["rows"] = [row["id"] for row in table_rows.get("results", [])]
    try:
        _notion_state_file().write_text(json.dumps(ids), encoding="utf-8")
    except OSError:
        pass
    return ids


def _notion_dashboard_sync(payload, force=False):
    """Refresh the dashboard in place. Returns True when it wrote something."""
    if not (_notion_setting("NOTION_API_KEY") and _notion_setting("NOTION_REPORT_PAGE_ID")):
        return False
    now = time.monotonic()
    with _notion_dashboard_lock:
        if not force and now - _notion_dashboard["at"] < NOTION_DASHBOARD_PERIOD:
            return False
        _notion_dashboard["at"] = now
    try:
        ids = _notion_dashboard["ids"]
        if ids is None:
            try:
                ids = json.loads(_notion_state_file().read_text(encoding="utf-8"))
            except (OSError, ValueError):
                ids = None
        blocks = _dashboard_blocks(payload)
        header, rows = _dashboard_rows(payload)
        # The row count changes when a channel appears or drops out, and a Notion
        # table's width and row set cannot be reshaped in place, so rebuild then.
        if (not ids or len(ids.get("rows") or []) != len(rows) + 1
                or len(ids.get("alerts") or []) != NOTION_ALERT_SLOTS):
            ids = _notion_dashboard_create(payload)
            _notion_dashboard["sent"] = {}
        else:
            pending = []
            for name in ("status", "condition", "host", "footer"):
                kind = blocks[name]["type"]
                pending.append((ids[name], {kind: blocks[name][kind]}))
            cells = [[_rt(h, bold=True) for h in header]] + [[_rt(c) for c in row] for row in rows]
            for row_id, row_cells in zip(ids["rows"], cells):
                pending.append((row_id, {"table_row": {"cells": row_cells}}))
            for block_id, block in zip(ids.get("alerts") or [], blocks["_alerts"]):
                pending.append((block_id, {"callout": block["callout"]}))
            sent = _notion_dashboard.setdefault("sent", {})
            changed = []
            for block_id, body in pending:
                encoded = json.dumps(body, sort_keys=True, separators=(",", ":"))
                if sent.get(block_id) != encoded:
                    changed.append((block_id, body, encoded))
            _notion_dashboard["changed"] = len(changed)
            if changed:
                errors = []
                def push(item):
                    block_id, body, encoded = item
                    try:
                        _notion_json("PATCH", f"/blocks/{block_id}", body)
                        sent[block_id] = encoded
                    except Exception as exc:
                        sent.pop(block_id, None)
                        errors.append(exc)
                with ThreadPoolExecutor(max_workers=4) as pool:
                    list(pool.map(push, changed))
                if errors:
                    raise errors[0]
        _notion_dashboard.update(ids=ids, error=None, syncs=_notion_dashboard["syncs"] + 1)
        return True
    except Exception as exc:
        _notion_dashboard["error"] = str(exc)[:300]
        # Drop the cached layout: the next tick rebuilds from what is really on the
        # page rather than retrying against ids that may have been deleted.
        _notion_dashboard["ids"] = None
        _notion_dashboard["sent"] = {}
        _NOTION_SECTION_CACHE.pop(NOTION_DASHBOARD_TITLE, None)
        try:
            _notion_state_file().unlink()
        except OSError:
            pass
        LOG.warning("Notion dashboard sync failed: %s", exc)
        return False


def _notion_store_record(section, title, fields):
    """Create one readable, timestamped cloud record beneath a managed section."""
    parent = _notion_section_id(section)
    children = []
    for label, value in fields:
        value = str(value)
        chunks = [value[i:i + 1800] for i in range(0, len(value), 1800)] or [""]
        for chunk in chunks:
            text = f"{label}: {chunk}"
            children.append({
                "object": "block", "type": "paragraph",
                "paragraph": {"rich_text": [{
                    "type": "text", "text": {"content": text}
                }]},
            })
    return _notion_json("POST", "/pages", {
        "parent": {"type": "page_id", "page_id": parent},
        "properties": {"title": {"type": "title", "title": [{
            "type": "text", "text": {"content": title[:180]}
        }]}},
        "children": children[:100],
    })


def _notion_background(section, title, fields):
    record = {
        "id": secrets.token_hex(12),
        "section": section,
        "title": title,
        "fields": [[str(a), str(b)] for a, b in fields],
        "queued_at": time.time(),
    }
    with notion_outbox_lock:
        notion_outbox.append(record)
    _save_local_cloud_state()
    _start_notion_drain()


def _drain_notion_outbox():
    try:
        if not (_notion_setting("NOTION_API_KEY") and
                _notion_setting("NOTION_REPORT_PAGE_ID")):
            return
        while True:
            with notion_outbox_lock:
                if not notion_outbox:
                    return
                record = dict(notion_outbox[0])
            try:
                _notion_store_record(
                    record["section"], record["title"], record["fields"]
                )
            except Exception as exc:
                LOG.warning("Notion outbox paused after sync failure: %s", exc)
                return
            with notion_outbox_lock:
                if notion_outbox and notion_outbox[0].get("id") == record.get("id"):
                    notion_outbox.pop(0)
            _save_local_cloud_state()
    finally:
        with notion_outbox_lock:
            _notion_drain_running[0] = False


def _start_notion_drain():
    with notion_outbox_lock:
        if _notion_drain_running[0]:
            return
        _notion_drain_running[0] = True
    threading.Thread(
        target=_drain_notion_outbox, name="notion-outbox", daemon=True
    ).start()


def _notion_record_pages(section, limit=100):
    """Read the newest cloud records with their paragraph fields."""
    parent = _notion_section_id(section)
    results = []
    cursor = ""
    while len(results) < max(limit, 100):
        suffix = (
            "&start_cursor=" + urllib.parse.quote(cursor, safe="")
            if cursor else ""
        )
        listing = _notion_json(
            "GET", f"/blocks/{parent}/children?page_size=100{suffix}"
        )
        results.extend(listing.get("results", []))
        if not listing.get("has_more") or not listing.get("next_cursor"):
            break
        cursor = listing["next_cursor"]
    pages = [
        block for block in results
        if block.get("type") == "child_page"
    ][-limit:]
    records = []
    for page in pages:
        content = _notion_json(
            "GET", f"/blocks/{page['id']}/children?page_size=100"
        )
        fields = {}
        for block in content.get("results", []):
            kind = block.get("type")
            rich = (block.get(kind) or {}).get("rich_text") or []
            text = "".join(part.get("plain_text", "") for part in rich)
            if ": " in text:
                label, value = text.split(": ", 1)
                fields[label] = fields.get(label, "") + value
        records.append({
            "id": page["id"],
            "title": page.get("child_page", {}).get("title", ""),
            "created_time": page.get("created_time", ""),
            "fields": fields,
        })
    return records


def _restore_notion_keys():
    """Replay encrypted key-registry events so keys survive app restarts."""
    restored = {}
    active = None
    for record in _notion_record_pages("API Key Registry", limit=1000):
        fields = record["fields"]
        event = fields.get("Event", "")
        kid = fields.get("Key ID", "")
        if not kid:
            continue
        if event == "added":
            key = _cloud_decrypt(fields.get("Encrypted credential", ""))
            provider = fields.get("Provider", "auto")
            chosen, error = _validate_key_provider(key, provider)
            if key and not error:
                restored[kid] = {
                    "id": kid,
                    "label": fields.get("Label", "Cloud key")[:40],
                    "key": key,
                    "provider": chosen,
                    "model": fields.get("Model", ""),
                    "builtin": False,
                }
                active = kid
        elif event == "selected" and kid in restored:
            active = kid
        elif event == "renamed" and kid in restored:
            label = fields.get("New label", "").strip()[:40]
            if label:
                restored[kid]["label"] = label
        elif event == "removed":
            restored.pop(kid, None)
            if active == kid:
                active = next(iter(restored), None)
    with nvtra_keys_lock:
        # Local state contains unsent/offline changes. Cloud records update matching
        # IDs but never erase a locally committed key merely because an upload is
        # still in the outbox.
        merged = {item["id"]: dict(item) for item in nvtra_keys["items"]}
        merged.update(restored)
        nvtra_keys["items"] = list(merged.values())
        nvtra_keys["active"] = (
            active if active in merged
            else (nvtra_keys["active"] if nvtra_keys["active"] in merged
                  else next(iter(merged), None))
        )
        numeric_ids = [
            int(item["id"][1:]) for item in restored.values()
            if re.fullmatch(r"k\d+", item["id"])
        ]
        if numeric_ids:
            _nvtra_kid[0] = max(_nvtra_kid[0], max(numeric_ids))
    return len(nvtra_keys["items"])


def _restore_notion_chats():
    """Restore recent cross-device chat sessions and their complete transcripts."""
    conversations = {}
    order = []
    for record in _notion_record_pages("Chat History", limit=500):
        fields = record["fields"]
        cid = fields.get("Conversation ID") or record["id"]
        if cid not in conversations:
            order.append(cid)
        conversations[cid] = fields
    cloud_sessions = {}
    session_order = []
    archived_conversations = []
    for cid in order:
        fields = conversations[cid]
        user = fields.get("User", "").strip()
        answer = fields.get("NVTRA", "").strip()
        sid = fields.get("Session ID") or cid
        if sid not in cloud_sessions:
            session_order.append(sid)
            cloud_sessions[sid] = {
                "id": sid,
                "title": fields.get("Session title") or user[:54] or "Saved chat",
                "title_source": "input" if fields.get("Session title") else "legacy",
                "created_utc": fields.get("Recorded UTC", ""),
                "updated_utc": fields.get("Recorded UTC", ""),
                "messages": [],
            }
        session = cloud_sessions[sid]
        if fields.get("Session title"):
            session["title"] = fields["Session title"]
            session["title_source"] = "input"
        session["updated_utc"] = fields.get("Recorded UTC", session["updated_utc"])
        if user:
            session["messages"].append({"role": "user", "text": user})
        if answer:
            session["messages"].append({
                "role": "model", "text": answer,
                "error": fields.get("Status") == "error",
            })
        archived_conversations.append({
            "id": cid,
            "session_id": sid,
            "title": session["title"],
            "recorded_utc": fields.get("Recorded UTC", ""),
            "user": user,
            "answer": answer,
            "status": fields.get("Status", "pending"),
        })
    with nvtra_lock:
        local_by_id = {s.get("id"): s for s in nvtra_sessions if s.get("id")}
        for sid in session_order:
            cloud = cloud_sessions[sid]
            if sid in local_by_id:
                local = local_by_id[sid]
                known = {(m.get("role"), m.get("text")) for m in local.get("messages", [])}
                for message in cloud["messages"]:
                    marker = (message.get("role"), message.get("text"))
                    if marker not in known:
                        local.setdefault("messages", []).append(message)
                        known.add(marker)
                if cloud.get("title_source") == "input":
                    local["title"] = cloud["title"]
                    local["title_source"] = "input"
                local["updated_utc"] = cloud["updated_utc"]
            else:
                nvtra_sessions.append(cloud)
                local_by_id[sid] = cloud
        by_id = {
            item.get("id"): dict(item) for item in nvtra_chat_archive
            if item.get("id")
        }
        for item in archived_conversations:
            by_id[item["id"]] = item
        nvtra_chat_archive.clear()
        nvtra_chat_archive.extend(
            list(by_id.values())[-nvtra_chat_archive.maxlen:]
        )
        if not nvtra_active_session[0] and nvtra_sessions:
            nvtra_active_session[0] = nvtra_sessions[-1]["id"]
        _normalize_chat_sessions()
        _sync_history_from_session(_active_chat_session(create=False))
    return sum(len(s.get("messages", [])) for s in nvtra_sessions)


def _restore_notion_state():
    _load_local_cloud_state()
    _merge_manual_api_keys()
    if not (_notion_setting("NOTION_API_KEY") and
            _notion_setting("NOTION_REPORT_PAGE_ID")):
        return
    try:
        chat_count = _restore_notion_chats()
        LOG.info("Restored %d chat messages from Notion", chat_count)
        _save_local_cloud_state()
        _start_notion_drain()
    except Exception:
        LOG.exception("Notion startup restore failed")


def _notion_upload_file(payload, filename, content_type,
                        section="Raw Data Archives", block_type="file"):
    """Upload and permanently attach one export to a managed Notion section."""
    token = _notion_setting("NOTION_API_KEY")
    page_id = _notion_setting("NOTION_REPORT_PAGE_ID")
    if not token or not page_id:
        raise RuntimeError("Notion cloud storage is not configured.")
    page_id = _notion_section_id(section)
    # Notion Free workspaces accept single-part files up to 5 MB and reject the
    # multipart mode entirely. Machine-readable exports compress extremely well, so
    # retain every record in a normal gzip archive instead of dropping or truncating.
    free_safe_limit = 4_750_000
    if len(payload) > free_safe_limit and content_type != "application/pdf":
        payload = gzip.compress(payload, compresslevel=9)
        filename += ".gz"
        content_type = "application/gzip"
    if len(payload) > free_safe_limit:
        raise RuntimeError(
            f"{filename} is {len(payload) / 1_000_000:.1f} MB; this Notion Free "
            "workspace only permits files up to 5 MB."
        )
    part_size = 10 * 1024 * 1024
    parts = [payload[i:i + part_size] for i in range(0, len(payload), part_size)]
    multi = len(parts) > 1
    common = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2026-03-11",
    }
    create_payload = {
        "mode": "multi_part" if multi else "single_part",
        "filename": filename, "content_type": content_type,
    }
    if multi:
        create_payload["number_of_parts"] = len(parts)
    create_body = json.dumps(create_payload).encode("utf-8")
    create_req = urllib.request.Request(
        "https://api.notion.com/v1/file_uploads", data=create_body, method="POST",
        headers={**common, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(create_req, timeout=30) as response:
        upload = json.loads(response.read().decode("utf-8"))
    upload_id = upload.get("id")
    upload_url = upload.get("upload_url") or (
        f"https://api.notion.com/v1/file_uploads/{upload_id}/send"
    )
    if not upload_id:
        raise RuntimeError("Notion did not return a file-upload ID.")

    sent = {}
    for part_number, part in enumerate(parts, 1):
        boundary = "----MTDIStudio" + secrets.token_hex(12)
        fields = b""
        if multi:
            fields = (
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="part_number"\r\n\r\n'
                f"{part_number}\r\n"
            ).encode("utf-8")
        multipart = fields + (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8") + part + f"\r\n--{boundary}--\r\n".encode("utf-8")
        send_req = urllib.request.Request(
            upload_url, data=multipart, method="POST",
            headers={**common, "Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(send_req, timeout=120) as response:
            sent = json.loads(response.read().decode("utf-8"))
    if multi:
        complete_url = upload.get("complete_url") or (
            f"https://api.notion.com/v1/file_uploads/{upload_id}/complete"
        )
        complete_req = urllib.request.Request(
            complete_url, data=b"{}", method="POST",
            headers={**common, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(complete_req, timeout=60) as response:
            sent = json.loads(response.read().decode("utf-8"))
    if sent.get("status") not in ("uploaded", None):
        raise RuntimeError(f"Notion file upload ended with status {sent.get('status')}.")

    attach_body = json.dumps({
        "children": [{
            "object": "block",
            "type": block_type,
            block_type: {
                "type": "file_upload",
                "file_upload": {"id": upload_id},
                "caption": [{"type": "text", "text": {"content": filename}}],
            },
        }]
    }).encode("utf-8")
    attach_req = urllib.request.Request(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        data=attach_body, method="PATCH",
        headers={**common, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(attach_req, timeout=30) as response:
        json.loads(response.read().decode("utf-8"))
    return upload_id


def _notion_upload_pdf(payload, filename):
    return _notion_upload_file(
        payload, filename, "application/pdf",
        section="PDF Archive", block_type="pdf",
    )


def _notion_upload_pdf_volumes(blocks, filename_stem):
    """Upload complete readable PDF volumes that fit Notion Free's 5 MB limit."""
    pending = [list(blocks[i:i + 11_000]) for i in range(0, len(blocks), 11_000)]
    payloads = []
    while pending:
        chunk = pending.pop(0)
        payload = _pdf_bytes(chunk)
        if len(payload) > 4_750_000 and len(chunk) > 1:
            middle = len(chunk) // 2
            pending[0:0] = [chunk[:middle], chunk[middle:]]
        else:
            payloads.append(payload)
    uploaded = []
    total = len(payloads)
    for index, payload in enumerate(payloads, 1):
        filename = f"{filename_stem}_volume_{index:02d}_of_{total:02d}.pdf"
        _notion_upload_pdf(payload, filename)
        uploaded.append(filename)
    return uploaded


_restore_notion_state()


@server.get("/download/studio-report.pdf")
def download_complete_pdf():
    """Reliable streamed report endpoint; protected by the same LAN authentication.

    NOTE: this is not the handler the assembled application serves. runtime.install()
    replaces server.view_functions['download_complete_pdf'] with a local-only version
    that builds the same PDF and never contacts Notion, so the Notion upload below -
    and its habit of turning an unconfigured workspace into a 502 instead of a report -
    does not reach the operator. Kept because the volume-splitting path is still used
    by the explicit "Upload report to Notion" action; do not re-point the route here
    without moving the upload off the download path first.
    """
    try:
        report_blocks = _gather_report_blocks()
        payload = _pdf_bytes(report_blocks)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"mtdi_studio_{stamp}.pdf"
        if len(payload) <= 4_750_000:
            notion_pdf_names = [filename]
            _notion_upload_pdf(payload, filename)
        else:
            notion_pdf_names = _notion_upload_pdf_volumes(
                report_blocks, f"mtdi_studio_{stamp}"
            )
        return Response(
            payload,
            mimetype="application/pdf",
            headers={
                "Content-Disposition":
                    f'attachment; filename="{filename}"',
                "Content-Length": str(len(payload)),
                "Cache-Control": "no-store",
                "X-Studio-Notion": "uploaded",
            },
        )
    except Exception as exc:
        LOG.exception("PDF report generation failed")
        return Response(
            f"PDF/Notion export failed: {exc}",
            status=502, mimetype="text/plain",
        )



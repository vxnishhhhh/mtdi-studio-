"""I3_D4_Validation_Report.pdf: generated from the live D4 packet, the trial store and the
reference database with matplotlib (the only PDF capable library on this host). Every number is
one the engine measured; sections without data say so instead of inventing a figure."""
from __future__ import annotations

import io
import time

import numpy as np


def _fig_text(pdf, title, lines, plt):
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.text(0.08, 0.94, title, fontsize=16, weight="bold")
    y = 0.90
    for line in lines:
        if y < 0.06:
            pdf.savefig(fig); plt.close(fig)
            fig = plt.figure(figsize=(8.27, 11.69)); y = 0.94
        size = 9 if not line.startswith("## ") else 12
        fig.text(0.08, y, line.replace("## ", ""), fontsize=size, family="monospace" if not line.startswith("## ") else None,
                 weight="bold" if line.startswith("## ") else None)
        y -= 0.021 if size == 9 else 0.03
    pdf.savefig(fig); plt.close(fig)


def build_report(runtime):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    d4s = runtime.d4
    p = d4s.snapshot(force=True)
    cfg = d4s.config
    inst = runtime.snapshot()
    buf = io.BytesIO()
    sim = " (SIMULATED DATA)" if p.get("simulated") else ""
    with PdfPages(buf) as pdf:
        # ── cover / summary ──
        ch = inst.get("channels", {})
        lines = [
            f"Generated {time.strftime('%Y-%m-%d %H:%M:%S')}{sim}",
            f"Instrument version {inst.get('version')} · source {inst.get('source')}",
            "", "## Equipment",
            'Source 1 three axis channel 1 (bus), Source 2 Channel 2 plate (860 SPS), channel 4 on Source 2, Source 3 (USB), host computer',
            *[f"{k:>10}: {v.get('state')} · {v.get('message', '')[:70]}" for k, v in ch.items()],
            "", "## Configuration (i3_config.json)",
            f"source: {cfg.get('source')}",
            f"weights: {cfg.get('mtdi_weights')}",
            f"thresholds: CH 3 {cfg.get('ch3_threshold_db')} dB · anomaly {cfg.get('anomaly_sigma')} sigma · event {cfg.get('event_mtdi')} · transient {cfg.get('transient_threshold')} x MAD",
            f"baseline: {cfg.get('baseline_method')} alpha {cfg.get('baseline_alpha')} · reference {cfg.get('linefreq_hz')} Hz · channel 1 ODR {cfg.get('c1_odr_hz')} Hz",
            "", "## Calibration",
            f"offsets (unit): {cfg.get('c1_offsets')} · scale {cfg.get('c1_scale')} · quality {cfg.get('c1_calibration_quality')}",
            f"health: {(p.get('calibration_health') or {}).get('status')} · spread {(p.get('calibration_health') or {}).get('magnitude_spread_pct')} % · {(p.get('calibration_health') or {}).get('recalibration', '')}",
            "", "## MTDI 2.0 at report time",
            f"MTDI {p.get('mtdi')} · confidence {p.get('confidence')} % · agreement {p.get('consensus')} %",
            f"scores: {p.get('scores')}",
            f"z: {p.get('z')}",
            f"confidence factors: {', '.join(p.get('confidence_factors') or [])}",
        ]
        _fig_text(pdf, "MTDI Studio · D4 Validation Report", lines, plt)

        # ── measurements: linefreq, CH3, noise, transients, correlation ──
        m = p.get("linefreq") or {}; mm = p.get("linefreq_ch1") or {}; r = p.get("ch3") or {}
        pn = p.get("power_network") or {}
        lines = ['## Power network analysis (Channel 2 ADC)']
        if m.get("error"):
            lines.append(m["error"])
        else:
            lines += [f"sample rate {m.get('fs')} Hz · Nyquist {m.get('nyquist_hz')} Hz · window {m.get('contiguous_s')} s",
                      f"fundamental {m.get('fundamental_hz')} Hz (detected: {m.get('fundamental_detected')}) · THD {m.get('thd_pct')} %",
                      "harmonics: " + (", ".join(f"{h['hz']} Hz ({h['rel_db']} dB)" for h in m.get('harmonics', []) if h.get('present')) or "none")]
        lines += ["", '## Channel 1 stream', (mm.get("error") or f"fs {mm.get('fs')} Hz · fundamental {mm.get('fundamental_hz')} Hz · THD {mm.get('thd_pct')} %") if mm else "no data"]
        lines += ["", "## Findings"] + [f"- {f}" for f in pn.get("findings", [])] + [f"! {a}" for a in pn.get("abnormal", [])]
        lines += ["", '## channel 3']
        if r.get("error"):
            lines.append(r["error"])
        else:
            lines += [f"primary peak {r.get('primary_peak_hz')} Hz · {r.get('primary_peak_dbm')} unit · floor {r.get('noise_floor_dbm')} unit · SNR {r.get('snr_db')} dB",
                      f"OBW {r.get('occupied_bandwidth_hz')} Hz · occupancy {r.get('occupancy_pct')} % · {r.get('interference_islands')} islands", r.get("band_note", ""),
                      f"trusted sweep: {r.get('trusted')}"]
        ne, nm = p.get("noise_ch2") or {}, p.get("noise_ch1") or {}
        lines += ["", "## Noise characterisation",
                  f"Channel 2 ADC: RMS {ne.get('rms')} · peak {ne.get('peak')} · sigma {ne.get('std')} · NSD {ne.get('nsd_per_sqrt_hz')} /sqrt(Hz)" if ne else 'Channel 2: no data',
                  f"channel 1: RMS {nm.get('rms')} unit · peak {nm.get('peak')} unit · NSD {nm.get('nsd_per_sqrt_hz')} unit/sqrt(Hz)" if nm else 'channel 1: no data']
        tr = p.get("transients") or {}
        lines += ["", "## Transients", f"{tr.get('count', 0)} events in {tr.get('window_s')} s · threshold {tr.get('threshold')} · repetition {tr.get('repetition_hz')} Hz"]
        lines += ["", "## Correlation"] + [f"{k}: r = {v.get('r')} · {v.get('text')}" for k, v in (p.get("correlation") or {}).items()]
        fp = p.get("fingerprint") or {}; chg = p.get("fingerprint_change") or {}
        lines += ["", "## Environmental fingerprint", f"channel 1 {fp.get('ch1_val')} unit · channel 2 {fp.get('ch2')} · CH 3 floor {fp.get('ch3_floor_dbm')} unit · transients {fp.get('transient_rate_per_min')} /min",
                  f"vs reference: {chg}" if p.get("fingerprint_reference") else "no reference recorded"]
        _fig_text(pdf, "Measurements", lines, plt)

        # ── figures ──
        sp = m.get("sweep3") or {}
        if sp.get("hz"):
            fig, ax = plt.subplots(figsize=(8.27, 4.5))
            ax.semilogy(sp["hz"], np.maximum(1e-9, np.array(sp["amp"], dtype=float)), lw=.8)
            for h in m.get("harmonics", []):
                if h.get("present"):
                    ax.axvline(h["hz"], color="orange", lw=.6, ls=":")
            ax.set_xlim(0, min(450, m.get("nyquist_hz") or 450)); ax.set_xlabel("Hz"); ax.set_title(f"Channel 2 channel 3{sim}"); ax.grid(alpha=.3)
            pdf.savefig(fig); plt.close(fig)
        sweep = d4s._sweep3() or {}
        if sweep.get("freqs"):
            fig, ax = plt.subplots(figsize=(8.27, 4.5))
            ax.plot(np.array(sweep["freqs"]) / 1e6, sweep["levels"], lw=.8)
            ax.set_xlabel("MHz"); ax.set_ylabel("dBm"); ax.set_title(f"CH 3 sweep{' (untrusted)' if not sweep.get('trusted') else ''}{sim}"); ax.grid(alpha=.3)
            pdf.savefig(fig); plt.close(fig)
        cal = d4s.last_calibration
        if cal and cal.get("raw"):
            fig = plt.figure(figsize=(8.27, 4.5))
            ax1 = fig.add_subplot(1, 2, 1, projection="3d"); ax2 = fig.add_subplot(1, 2, 2, projection="3d")
            raw = np.array(cal["raw"], dtype=float); cor = np.array(cal["corrected"], dtype=float)
            ax1.scatter(raw[:, 0], raw[:, 1], raw[:, 2], s=2, c="r"); ax1.set_title(f"raw · residual {cal['residual_before_pct']} %")
            ax2.scatter(cor[:, 0], cor[:, 1], cor[:, 2], s=2, c="c"); ax2.set_title(f"corrected · {cal['residual_after_pct']} % · quality {cal['quality']} %")
            pdf.savefig(fig); plt.close(fig)
        hist = d4s._histories()
        fig, axes = plt.subplots(3, 1, figsize=(8.27, 8), sharex=False)
        for ax, key in zip(axes, ("ch1", "ch2", "ch3")):
            rows = hist.get(key) or []
            if rows:
                t0 = rows[0][0]
                ax.plot([t - t0 for t, _, _ in rows], [v for _, v, _ in rows], lw=.8)
            ax.set_title(f"{key} deviation (recent window)"); ax.grid(alpha=.3)
        fig.tight_layout(); pdf.savefig(fig); plt.close(fig)

        # ── validation trials ──
        trials = d4s.trials
        from . import d4 as d4mod
        stats = d4mod.validation_stats([t["value"] for t in trials if t.get("value") is not None], [(t["detected"], t["actual"]) for t in trials])
        lines = ["## Trials", f"{len(trials)} recorded"]
        if stats.get("measurements"):
            ms = stats["measurements"]
            lines += [f"n {ms['n']} · mean {ms['mean']} · median {ms['median']} · sigma {ms['std']} · CV {ms['cv_pct']} % · 95% CI {ms['ci95']}"]
        if stats.get("detection"):
            ds = stats["detection"]
            lines += [f"detection rate {ds['detection_rate_pct']} % · false positive rate {ds['false_positive_rate_pct']} % · precision {ds['precision_pct']} % · recall {ds['recall_pct']} % · F1 {ds['f1_pct']} %"]
        refs = [(t["value"], t["reference"]) for t in trials if t.get("value") is not None and t.get("reference") is not None]
        if refs:
            err = d4mod.sensor_error([v for v, _ in refs], [r for _, r in refs])
            lines += [f"error vs reference: mean abs {err['mean_abs_error']} · {err['mean_pct_error']} % · bias {err['bias']} · RMSE {err['rmse']}"]
            if stats.get("measurements"):
                u = d4mod.uncertainty(stats["measurements"]["mean"], 0.0, stats["measurements"]["std"], nm.get("rms") or 0.0, abs(err["bias"] or 0))
                lines += [f"result: {u['text']} (k = 2; budget {u['budget']})"]
        lines += ["", "## Recommendations"] + [f"- {r['text']}" for r in d4mod.test_recommendations(trials)]
        lines += ["", "## Reference profiles (similarity, not identification)"] + [f"{k}: recorded {time.strftime('%Y-%m-%d %H:%M', time.localtime(v.get('recorded_at') or 0))} · {v.get('note', '')}" for k, v in d4s.references.items()] or ["none recorded"]
        sim_rows = p.get("similarity") or []
        if sim_rows:
            lines += ["closest now: " + ", ".join(f"{q['name']} {q['similarity_pct']} %" for q in sim_rows[:3])]
        lines += ["", "## Conclusions",
                  "MTDI 2.0, confidence, consensus and every figure above are computed from the samples the instrument recorded in this session.",
                  "Sections reading 'no data' or 'not detected' reflect the measurement, not a fault in the report.",
                  "Simulated runs are watermarked and must not be quoted as measurements." if p.get("simulated") else "This report was generated from hardware acquisition."]
        _fig_text(pdf, "Validation", lines, plt)
        if trials and any(t.get("value") is not None for t in trials):
            fig, ax = plt.subplots(figsize=(8.27, 4))
            vals = [t["value"] for t in trials if t.get("value") is not None]
            ax.plot(vals, "o-", lw=.8); ax.axhline(np.mean(vals), color="orange", lw=.8, label="mean")
            if stats.get("measurements"):
                ax.axhspan(stats["measurements"]["ci95"][0], stats["measurements"]["ci95"][1], color="orange", alpha=.15, label="95 % CI")
            ax.set_title("Trial values"); ax.legend(); ax.grid(alpha=.3)
            pdf.savefig(fig); plt.close(fig)
    return buf.getvalue()

"""GLOBAL_CSS: the complete stylesheet, light mode and the startup intro component."""
from ._shared import inherit
inherit(globals(), 'common', 'sensors', 'intelligence', 'system', 'tokens')
from .content import T  # studio words (S1-06)

GLOBAL_CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:auto;-webkit-overflow-scrolling:touch;scrollbar-gutter:stable;overflow-y:scroll}}
/* NOTE: no overflow-x:hidden on body. It turns body into a scroll container, which
   breaks `position:sticky` for every descendant (the startup intro's stopper) and
   makes ScrollTrigger misdetect the scroller. Horizontal overflow is prevented
   structurally instead — min-width:0 on grid/flex children and scrollable wrappers
   on wide tables — and is asserted in the navigation checks. */
body{{background:{BG};color:{WHITE};font-family:{FONTUI};-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;text-rendering:optimizeLegibility}}
::-webkit-scrollbar{{width:4px}}::-webkit-scrollbar-track{{background:{BG}}}::-webkit-scrollbar-thumb{{background:{BORDER};border-radius:2px}}

@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.35}}}}
@keyframes pulseSoft{{0%,100%{{opacity:0.85}}50%{{opacity:1}}}}
@keyframes ringSpin{{0%{{transform:rotate(0deg)}}100%{{transform:rotate(360deg)}}}}
@keyframes glowBreathe{{0%,100%{{opacity:0.85}}50%{{opacity:1}}}}
@keyframes barGrow{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
@keyframes radarRing{{0%{{transform:translate(-50%,-50%) scale(1);opacity:0.8}}100%{{transform:translate(-50%,-50%) scale(3.5);opacity:0}}}}
@keyframes pillRing{{0%{{transform:scale(1);opacity:0.4}}100%{{transform:scale(2.2);opacity:0}}}}
@keyframes alertShow{{0%{{opacity:0;transform:translateX(16px)}}8%{{opacity:1;transform:translateX(0)}}80%{{opacity:1;transform:translateX(0)}}100%{{opacity:0;transform:translateX(16px)}}}}
@keyframes cursorBlink{{0%,100%{{opacity:1}}50%{{opacity:0}}}}
@keyframes popIn{{from{{opacity:0;transform:translateY(-6px) scale(0.97)}}to{{opacity:1;transform:translateY(0) scale(1)}}}}
@keyframes navProgress{{0%{{transform:translateX(-100%)}}100%{{transform:translateX(0)}}}}

/* Page entry is intentionally inert — see RENDERING NOTES. */
.page-enter{{animation:none!important;opacity:1!important;transform:none!important}}

/* ── the one place a "loading" state is allowed: a 2px bar under the header.
      It never blanks the page, so the previous content stays readable until the
      new content is ready to be swapped in atomically. ── */
#nav-progress{{position:fixed;top:54px;left:0;right:0;height:2px;z-index:120;pointer-events:none;
  background:linear-gradient(90deg,{BLUE},{CYAN});transform:translateX(-100%);opacity:0}}
html.nav-busy #nav-progress{{opacity:1;animation:navProgress 1.4s cubic-bezier(0.2,0.8,0.2,1) forwards}}

#fixed-credit{{position:fixed;bottom:24px;right:28px;z-index:9999;font-family:{FONT};font-size:10px;letter-spacing:0.22em;color:rgba(0,229,255,0.7);text-shadow:0 0 10px rgba(0,229,255,0.3);text-transform:uppercase;pointer-events:none;user-select:none}}
#typewriter-bar{{position:fixed;bottom:24px;left:28px;z-index:9999;font-family:{FONT};font-size:10px;letter-spacing:0.18em;color:rgba(0,229,255,0.5);text-transform:uppercase;pointer-events:none;user-select:none;white-space:nowrap}}
#typewriter-cursor{{animation:cursorBlink 1s step-end infinite;color:rgba(0,229,255,0.7);margin-left:2px}}
#nvtra-alert-stack{{position:fixed;top:66px;right:20px;z-index:9998;display:flex;flex-direction:column;gap:8px;pointer-events:none;align-items:flex-end}}
.nvtra-alert-item{{font-family:{FONT};font-size:11px;letter-spacing:0.18em;color:#00e5ff;text-transform:uppercase;background:rgba(7,9,15,0.96);border:1px solid rgba(0,229,255,0.4);border-radius:10px;padding:10px 20px;text-shadow:0 0 10px rgba(0,229,255,0.5);box-shadow:0 0 24px rgba(0,229,255,0.15);white-space:nowrap;animation:alertShow 5.4s forwards}}

/* ── Nav / Header — permanently fixed liquid-glass instrument chrome ── */
.site-header{{position:fixed;top:0;left:0;right:0;width:100%;z-index:100001;
  background:linear-gradient(180deg,rgba(12,17,29,0.78),rgba(7,9,15,0.62));
  border-bottom:1px solid rgba(255,255,255,0.10);
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.08),0 8px 30px rgba(0,0,0,0.22);
  backdrop-filter:blur(10px) saturate(140%);-webkit-backdrop-filter:blur(10px) saturate(140%);
  padding:0 32px;height:54px;min-height:54px;display:flex;align-items:center;
  justify-content:space-between;box-sizing:border-box;contain:layout style}}
.nav-glass-wrap{{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);z-index:10}}
.nav-glass{{display:flex;align-items:center;gap:2px;padding:4px;border-radius:16px;
  background:linear-gradient(145deg,rgba(255,255,255,0.105),rgba(255,255,255,0.035));
  border:1px solid rgba(255,255,255,0.13);
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.16),inset 0 -1px 0 rgba(0,0,0,0.18),0 6px 24px rgba(0,0,0,0.28);
  backdrop-filter:blur(8px) saturate(150%);-webkit-backdrop-filter:blur(8px) saturate(150%);
  position:relative;overflow:hidden}}
.nav-glass::before{{content:'';position:absolute;top:0;left:10%;right:10%;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,0.25),transparent);pointer-events:none}}
.nav-glass-btn{{font-family:{FONT};font-size:10px;letter-spacing:0.18em;text-transform:uppercase;color:rgba(232,238,255,0.5);padding:6px 16px;border-radius:12px;border:1px solid transparent;background:transparent;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;gap:7px;transition:color 0.2s,background 0.2s;position:relative;z-index:1;white-space:nowrap;user-select:none}}
.nav-glass-btn .nav-dot{{width:5px;height:5px;border-radius:50%;flex-shrink:0;background:{SUBTEXT};transition:background 0.2s,box-shadow 0.2s}}
.nav-glass-btn:hover{{color:rgba(232,238,255,0.9);background:rgba(255,255,255,0.06)}}
.nav-glass-btn:hover .nav-dot{{background:{CYAN};box-shadow:0 0 6px {CYAN}}}
.nav-glass-btn.nav-active{{color:{CYAN};background:linear-gradient(135deg,rgba(0,229,255,0.12) 0%,rgba(41,121,255,0.08) 100%);border-color:rgba(0,229,255,0.22);text-shadow:0 0 12px rgba(0,229,255,0.5)}}
.nav-glass-btn.nav-active .nav-dot{{background:{CYAN};box-shadow:0 0 8px {CYAN};animation:pulseSoft 2s ease-in-out infinite}}
.nav-glass-sep{{width:1px;height:16px;flex-shrink:0;background:linear-gradient(to bottom,transparent,rgba(255,255,255,0.1),transparent)}}
.header-brand{{font-family:{FONT};font-size:11px;letter-spacing:0.18em;color:{CYAN};user-select:none;display:inline-flex;align-items:center;gap:8px;text-transform:uppercase;padding:6px 14px;border:1px solid rgba(0,229,255,0.35);border-radius:6px;background:rgba(0,229,255,0.04);text-shadow:0 0 12px rgba(0,229,255,0.5);white-space:nowrap}}
.header-brand::before{{content:'';width:6px;height:6px;border-radius:50%;background:{CYAN};box-shadow:0 0 10px {CYAN};animation:pulseSoft 2.2s ease-in-out infinite}}
.header-pills{{display:flex;gap:8px;align-items:center;flex-wrap:nowrap;min-height:26px}}
.status-pill{{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07);border-radius:20px;padding:4px 12px;font-family:{FONT};font-size:10px;color:{SUBTEXT};letter-spacing:0.08em;transition:border-color 0.25s}}
.status-pill .pill-val{{color:{WHITE};font-size:11px}}
.pill-dot{{width:6px;height:6px;border-radius:50%;flex-shrink:0}}
.pill-ok{{background:{GREEN};box-shadow:0 0 6px {GREEN};position:relative}}
.pill-ok::after{{content:'';position:absolute;inset:-3px;border-radius:50%;border:1px solid {GREEN};opacity:0.3;animation:pillRing 2.4s ease-out infinite}}
.pill-warn{{background:{AMBER};box-shadow:0 0 6px {AMBER};animation:pulse 2s infinite}}
.pill-high{{background:{RED};box-shadow:0 0 6px {RED};animation:pulse 1.2s infinite}}
.pill-off{{background:{SUBTEXT}}}

/* ── the routed area. Reserving a viewport of height here is what stops the document
      from jumping when a tall page is replaced by a short one. ── */
#page-content{{position:relative;z-index:1;min-height:100vh;padding-top:54px;
  box-sizing:border-box;contain:layout style}}

/* ════ SURFACES (no backdrop-filter — see RENDERING NOTES) ════ */
.cards-3d-container{{/* perspective removed: no 3D entry tilt */}}
.module-card{{background:{SURFACE2};border:1px solid rgba(255,255,255,0.08);border-top-color:rgba(255,255,255,0.14);box-shadow:inset 0 1px 0 rgba(255,255,255,0.07),0 8px 32px rgba(0,0,0,0.3);border-radius:20px;padding:28px;flex:1;min-width:0;min-height:236px;transition:border-color 0.3s,box-shadow 0.3s,transform 0.3s;position:relative;overflow:hidden;display:flex;flex-direction:column}}
.module-card:hover{{border-color:rgba(0,229,255,0.35);box-shadow:inset 0 1px 0 rgba(0,229,255,0.12),0 16px 48px rgba(41,121,255,0.22);transform:translateY(-4px)}}
.sys-card{{background:{SURFACE};border:1px solid rgba(255,255,255,0.07);border-top-color:rgba(255,255,255,0.11);border-radius:16px;padding:20px 22px;min-height:104px;transition:border-color 0.25s,transform 0.25s;contain:layout style}}
.sys-card:hover{{border-color:rgba(41,121,255,0.35);transform:translateY(-2px)}}
.metric-card{{background:{SURFACE};border:1px solid rgba(255,255,255,0.07);border-top-color:rgba(255,255,255,0.11);border-radius:16px;padding:18px 22px;min-width:150px;min-height:86px;display:inline-block;transition:border-color 0.25s,transform 0.25s;position:relative;overflow:hidden;contain:layout style}}
.metric-card:hover{{border-color:rgba(41,121,255,0.4);transform:translateY(-2px)}}
.metric-card::before{{content:'';position:absolute;top:0;left:12%;right:12%;height:2px;border-radius:2px;
  background:linear-gradient(90deg,transparent,rgba(0,229,255,0.55),transparent);
  transform:scaleX(0);transition:transform .35s ease}}
.metric-card:hover::before{{transform:scaleX(1)}}
.sensor-conf-card{{background:{SURFACE};border:1px solid rgba(255,255,255,0.07);border-radius:16px;padding:20px 22px;min-height:132px;transition:border-color 0.3s,transform 0.3s;position:relative;contain:layout style}}
.sensor-conf-card:hover{{border-color:rgba(41,121,255,0.4);transform:translateY(-2px)}}
.online-bar{{display:flex;align-items:center;gap:10px;background:{SURFACE};border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px 22px;margin-bottom:24px;min-height:50px}}
.panel{{border-radius:14px;overflow:hidden;background:{SURFACE};border:1px solid rgba(255,255,255,0.07)}}
.summary-panel{{background:{SURFACE};border:1px solid rgba(255,255,255,0.07);border-left:3px solid {BLUE};border-radius:14px;padding:22px 26px;margin-top:24px;position:relative;overflow:hidden}}
.summary-panel::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,{BLUE},transparent);opacity:0.5}}
.error-box{{background:rgba(58,20,26,0.85);border:1px solid rgba(255,82,82,0.3);color:#ff8a9a;border-radius:12px;padding:16px 20px;font-family:{FONT};font-size:12px;letter-spacing:0.04em}}

.module-live-val{{font-family:{FONT};font-size:22px;color:{CYAN};margin:12px 0 4px;letter-spacing:-0.02em}}
.module-live-label{{font-family:{FONT};font-size:10px;color:{SUBTEXT};letter-spacing:0.15em;text-transform:uppercase}}
.open-btn{{background:rgba(41,121,255,0.10);border:1px solid rgba(41,121,255,0.3);color:{BLUE};border-radius:10px;padding:11px 22px;font-size:11px;font-family:{FONT};cursor:pointer;margin-top:auto;letter-spacing:0.12em;transition:all 0.25s;width:100%}}
.open-btn:hover{{background:{BLUE};color:#fff;box-shadow:0 0 32px {GLOW}}}
.back-btn{{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);color:{SUBTEXT};border-radius:8px;padding:8px 18px;font-size:11px;font-family:{FONT};cursor:pointer;letter-spacing:0.08em;transition:all 0.25s}}
.back-btn:hover{{border-color:{BLUE};color:{WHITE}}}
.metric-value{{font-family:{FONT};font-size:32px;font-weight:300;color:{WHITE};letter-spacing:-0.02em;line-height:1}}
.metric-label{{font-size:10px;color:{SUBTEXT};letter-spacing:0.16em;text-transform:uppercase;margin-top:8px;font-family:{FONT}}}
.live-dot{{width:7px;height:7px;background:{BLUE};border-radius:50%;display:inline-block;margin-right:8px;box-shadow:0 0 10px {BLUE};animation:pulse 1.8s ease-in-out infinite;position:relative}}
.live-dot::after{{content:'';position:absolute;top:50%;left:50%;width:7px;height:7px;border-radius:50%;background:transparent;border:1px solid #2979ff;transform:translate(-50%,-50%) scale(1);animation:radarRing 2s ease-out infinite;pointer-events:none}}
.page-title{{font-size:28px;font-weight:300;letter-spacing:-0.01em;color:{WHITE}}}
.page-subtitle{{font-size:12px;color:{SUBTEXT};margin-top:6px;font-family:{FONT};letter-spacing:0.05em}}
.section-label{{font-family:{FONT};font-size:10px;letter-spacing:0.22em;color:{SUBTEXT};margin-bottom:12px;text-transform:uppercase}}
.divider{{border:none;border-top:1px solid rgba(255,255,255,0.05);margin:24px 0}}
.summary-tag{{font-family:{FONT};font-size:10px;letter-spacing:0.24em;color:{BLUE};text-transform:uppercase;margin-bottom:12px}}
.summary-text{{font-size:13px;color:{WHITE};line-height:1.9;font-family:{FONTUI};opacity:0.9}}
.summary-hi{{color:{CYAN};font-family:{FONT}}}
.tab-bar{{display:flex;gap:4px;margin-bottom:28px;border-bottom:1px solid rgba(255,255,255,0.06);min-height:41px}}
.tab-btn{{background:transparent;border:none;border-bottom:2px solid transparent;color:{SUBTEXT};font-family:{FONT};font-size:11px;letter-spacing:0.18em;padding:10px 20px;cursor:pointer;margin-bottom:-1px;transition:color 0.25s,border-color 0.25s}}
.tab-btn:hover{{color:{WHITE}}}
.tab-btn.active{{color:{CYAN};border-bottom-color:{CYAN};text-shadow:0 0 12px rgba(0,229,255,0.5)}}
.online-dot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
.online-dot.on{{background:{GREEN};box-shadow:0 0 10px {GREEN};animation:pulseSoft 2.4s ease-in-out infinite}}
.online-dot.warn{{background:{AMBER};box-shadow:0 0 10px {AMBER};animation:pulse 2s infinite}}
.online-dot.off{{background:{RED};box-shadow:0 0 10px {RED};animation:pulse 1.2s infinite}}
.online-text{{font-family:{FONT};font-size:12px;letter-spacing:0.18em}}
.sys-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px;margin-top:14px;min-height:104px}}
.sys-name{{font-family:{FONT};color:{BLUE};font-size:9px;letter-spacing:0.2em;margin-bottom:10px;text-transform:uppercase}}
.sys-value{{font-family:{FONT};color:{WHITE};font-size:22px;margin-bottom:4px;letter-spacing:-0.02em}}
.sys-sub{{color:{SUBTEXT};font-size:11px;line-height:1.6;font-family:{FONT}}}
.sys-bar-track{{width:100%;height:4px;background:rgba(255,255,255,0.06);border-radius:2px;margin-top:10px;overflow:hidden}}
.sys-bar-fill{{height:4px;border-radius:2px;animation:barGrow 1s cubic-bezier(0.16,1,0.3,1) forwards;transform-origin:left}}
.conf-ring{{width:160px;height:160px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:{SURFACE};border:4px solid rgba(255,255,255,0.1);position:relative;flex-direction:column;animation:glowBreathe 4s ease-in-out infinite;transition:border-color 0.5s,box-shadow 0.5s}}
.conf-ring::before{{content:'';position:absolute;inset:-8px;border-radius:50%;background:conic-gradient(from 0deg,transparent,rgba(0,229,255,0.15),transparent);animation:ringSpin 8s linear infinite;z-index:-1}}
.conf-ring-val{{font-family:{FONT};font-size:36px;color:{WHITE}}}
.conf-ring-sub{{font-family:{FONT};font-size:9px;color:{SUBTEXT};letter-spacing:0.18em;margin-top:4px;text-align:center;padding:0 10px}}
.sensor-conf-name{{font-family:{FONT};color:{BLUE};font-size:10px;letter-spacing:0.18em;margin-bottom:10px}}
.sensor-conf-val{{font-family:{FONT};font-size:28px;letter-spacing:-0.02em}}
.sensor-conf-note{{color:{SUBTEXT};font-size:11px;font-family:{FONT};margin-top:6px;line-height:1.5;min-height:33px}}

/* ════ INSTRUMENT MODULES title ════ */
.instrument-modules-title{{font-family:{FONT};font-size:clamp(18px,3vw,26px);color:{CYAN};letter-spacing:0.28em;text-transform:uppercase;text-shadow:0 0 20px rgba(0,229,255,0.6),0 0 50px rgba(0,229,255,0.35);padding:16px 32px;border:1px solid rgba(0,229,255,0.35);border-radius:14px;background:rgba(0,229,255,0.04);box-shadow:0 0 40px rgba(0,229,255,0.15),inset 0 0 30px rgba(0,229,255,0.04);display:inline-block;margin-bottom:10px}}
.art-line{{font-family:{FONTUI};font-size:12px;color:{SUBTEXT};letter-spacing:0.08em;margin-top:8px;line-height:1.6}}
.art-line .art-em{{color:{CYAN};font-family:{FONT};font-size:11px;font-style:italic;text-shadow:0 0 8px rgba(0,229,255,0.4)}}

/* ════ PILLAR CHIPS ════ */
.pillar{{display:flex;flex-direction:column;background:{SURFACE};border:1px solid rgba(255,255,255,0.07);border-top-color:rgba(255,255,255,0.11);border-radius:16px;overflow:hidden;position:relative;transition:border-color 0.3s,box-shadow 0.3s,transform 0.3s}}
.pillar:hover{{border-color:rgba(0,229,255,0.35);box-shadow:0 12px 40px rgba(0,229,255,0.1);transform:translateY(-3px)}}
.pillar::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,rgba(0,229,255,0.5),transparent);opacity:0;transition:opacity 0.3s}}
.pillar:hover::before{{opacity:1}}
.pillar-header{{padding:20px 20px 14px;border-bottom:1px solid rgba(255,255,255,0.06);display:flex;align-items:flex-start;gap:14px}}
.pillar-num{{font-family:{FONT};font-size:10px;letter-spacing:0.12em;color:{BLUE};background:rgba(41,121,255,0.10);border:1px solid rgba(41,121,255,0.25);border-radius:6px;padding:4px 9px;flex-shrink:0;margin-top:2px;transition:background 0.3s,border-color 0.3s}}
.pillar:hover .pillar-num{{background:rgba(0,229,255,0.12);border-color:rgba(0,229,255,0.35);color:{CYAN}}}
.pillar-title{{font-family:{FONT};font-size:13px;color:{WHITE};letter-spacing:0.12em;text-transform:uppercase;line-height:1.3;transition:color 0.3s}}
.pillar:hover .pillar-title{{color:{CYAN}}}
.pillar-chips{{display:flex;flex-direction:column;padding:10px 0 4px;flex:1}}
.pillar-chip{{font-family:{FONT};font-size:10px;color:{SUBTEXT};padding:10px 20px;letter-spacing:0.03em;display:flex;align-items:center;gap:10px;border-bottom:1px solid rgba(255,255,255,0.04);transition:color 0.2s,background 0.2s,text-shadow 0.2s;line-height:1.4;cursor:pointer;user-select:none;position:relative}}
.cc-areas{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:18px;margin-top:18px}}.cc-mod{{justify-content:space-between}}.cc-mod-state{{font-size:9px;letter-spacing:.08em;text-transform:uppercase}}.cc-mod-state.ok{{color:#00e676}}.cc-mod-state.bad{{color:#ff5252}}
.pillar-chip:last-child{{border-bottom:none}}
.pillar-chip::before{{content:'';width:4px;height:4px;border-radius:50%;flex-shrink:0;background:rgba(0,229,255,0.25);transition:background 0.2s,box-shadow 0.2s}}
.pillar-chip:hover{{color:{WHITE}!important;background:rgba(0,229,255,0.06);text-shadow:0 0 12px rgba(0,229,255,0.3)}}
.pillar-chip:hover::before{{background:{CYAN};box-shadow:0 0 10px rgba(0,229,255,0.9)}}
.pillar-chip.active-chip{{background:rgba(0,229,255,0.08);color:{CYAN}!important;border-left:2px solid rgba(0,229,255,0.5);text-shadow:0 0 10px rgba(0,229,255,0.35)}}
.pillar-chip.active-chip::before{{background:{CYAN};box-shadow:0 0 8px {CYAN}}}
.pillar-flow,.pillar-arrow{{display:none}}

/* ════ CHIP POPUP ════ */
.chip-popup{{position:fixed;z-index:9990;max-width:290px;min-width:240px;animation:popIn 0.28s cubic-bezier(0.16,1,0.3,1) both}}
.chip-popup-inner{{background:rgba(7,9,15,0.98);border:1px solid rgba(0,229,255,0.3);border-top:2px solid {CYAN};border-radius:14px;padding:16px 18px;box-shadow:0 20px 60px rgba(0,0,0,0.6),0 0 28px rgba(0,229,255,0.12)}}
.chip-popup-header{{display:flex;align-items:flex-start;gap:10px;margin-bottom:12px}}
.chip-popup-icon{{font-family:{FONT};font-size:22px;color:{CYAN};min-width:30px;text-shadow:0 0 12px rgba(0,229,255,0.7);line-height:1}}
.chip-popup-title{{font-family:{FONT};font-size:10.5px;color:{WHITE};letter-spacing:0.1em;line-height:1.4}}
.chip-popup-field{{font-family:{FONT};font-size:8.5px;color:{SUBTEXT};letter-spacing:0.22em;text-transform:uppercase;margin-top:3px}}
.chip-popup-close{{margin-left:auto;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);color:{SUBTEXT};cursor:pointer;font-size:10px;padding:3px 6px;border-radius:5px;transition:color 0.2s,background 0.2s;flex-shrink:0;line-height:1}}
.chip-popup-close:hover{{color:{WHITE};background:rgba(255,255,255,0.12)}}
.chip-popup-body{{font-family:{FONTUI};font-size:11.5px;color:rgba(232,238,255,0.8);line-height:1.72;margin-bottom:12px}}
.chip-popup-tag{{font-family:{FONT};font-size:10px;color:{CYAN};background:rgba(0,229,255,0.06);border:1px solid rgba(0,229,255,0.18);border-radius:6px;padding:5px 10px;text-shadow:0 0 6px rgba(0,229,255,0.3);letter-spacing:0.06em}}

/* ════ DISC ARCH ════ */
.disc-block{{position:relative;margin:0 0 40px;padding:40px 0 0}}
.disc-svg-host{{position:absolute;inset:0;pointer-events:none;z-index:0;overflow:visible}}
.disc-root{{position:relative;z-index:2;display:flex;flex-direction:column;align-items:center}}
.disc-eyebrow{{font-family:{FONT};font-size:9px;letter-spacing:0.38em;color:{BLUE};text-transform:uppercase;margin-bottom:18px;display:flex;align-items:center;gap:10px}}
.disc-eyebrow::before,.disc-eyebrow::after{{content:'';display:inline-block;width:28px;height:1px;background:linear-gradient(90deg,transparent,{BLUE})}}
.disc-eyebrow::after{{background:linear-gradient(90deg,{BLUE},transparent)}}
.disc-title-card{{position:relative;padding:28px 48px 24px;border:1px solid rgba(0,229,255,0.30);border-radius:18px;background:linear-gradient(160deg,rgba(17,26,43,0.94) 0%,rgba(7,9,15,0.97) 100%);box-shadow:0 0 40px rgba(0,229,255,0.08),inset 0 1px 0 rgba(0,229,255,0.12);text-align:center}}
.disc-title-card::before{{content:'';position:absolute;top:0;left:15%;right:15%;height:1px;background:linear-gradient(90deg,transparent,rgba(0,229,255,0.5),transparent)}}
.disc-title-word{{font-family:{FONT};font-size:42px;font-weight:500;letter-spacing:0.05em;color:{CYAN};text-transform:uppercase;display:block;margin-bottom:8px;text-shadow:0 0 24px rgba(0,229,255,0.6),0 0 48px rgba(0,229,255,0.3)}}
.disc-under{{font-family:{FONTUI};font-size:12px;color:{SUBTEXT};letter-spacing:0.04em;margin-bottom:20px;line-height:1.6}}
.disc-stats{{display:flex;align-items:center;justify-content:center;border-top:1px solid rgba(255,255,255,0.06);padding-top:16px;margin-top:4px}}
.disc-stat{{display:flex;flex-direction:column;align-items:center;padding:0 24px}}
.disc-stat-val{{font-family:{FONT};font-size:22px;color:{WHITE};letter-spacing:-0.02em;line-height:1}}
.disc-stat-key{{font-family:{FONT};font-size:8px;color:{SUBTEXT};letter-spacing:0.22em;text-transform:uppercase;margin-top:4px}}
.disc-stat-sep{{width:1px;height:32px;background:linear-gradient(to bottom,transparent,rgba(255,255,255,0.08),transparent)}}
.pillar-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;padding-top:90px;position:relative;z-index:2}}
@media(max-width:900px){{.pillar-grid{{grid-template-columns:repeat(2,1fr);padding-top:70px}}}}

/* ════ HERO ════ */
.hero-wrap{{max-width:1320px;margin:0 auto;padding:20px 40px 32px;position:relative}}
.hero-title{{font-family:{FONT};font-size:clamp(42px,5.8vw,80px);font-weight:500;letter-spacing:-0.01em;line-height:1.0;color:{CYAN};text-transform:uppercase;display:inline-block;padding:22px 38px;border:1px solid rgba(0,229,255,0.35);border-radius:14px;background:rgba(0,229,255,0.04);text-shadow:0 0 24px rgba(0,229,255,0.5),0 0 48px rgba(0,229,255,0.3);box-shadow:0 0 40px rgba(0,229,255,0.15),inset 0 0 30px rgba(0,229,255,0.04);animation:glowBreathe 5s ease-in-out infinite}}
.hero-title-wrap{{display:flex;flex-direction:column;align-items:flex-start;gap:16px;margin-bottom:30px}}
.hero-tag{{font-family:{FONT};font-size:11.5px;letter-spacing:0.28em;color:{WHITE};text-transform:uppercase;display:inline-block;padding:7px 18px;border:1px solid rgba(232,238,255,0.25);border-radius:6px;background:rgba(232,238,255,0.04);margin-left:1px}}
.hero-tag .i3{{font-family:{FONT};color:{CYAN};font-size:13px;letter-spacing:0;text-shadow:0 0 12px rgba(0,229,255,0.6)}}
.hero-tag sup{{font-size:8px;vertical-align:super;color:{CYAN}}}
.hero-sub{{font-family:{FONTUI};font-size:15.5px;color:#aab6cc;line-height:1.9;max-width:1180px;letter-spacing:0.005em}}
.hero-sub .hi{{color:{CYAN};font-family:{FONT};font-size:13.5px;letter-spacing:0.02em;padding:1px 4px;background:rgba(0,229,255,0.035);border-radius:3px}}
.hero-spec{{display:flex;flex-wrap:wrap;gap:20px 28px;margin-top:36px;padding-top:28px;border-top:1px solid rgba(255,255,255,0.06)}}
.hero-spec .k{{font-family:{FONT};font-size:9.5px;letter-spacing:0.22em;color:{SUBTEXT};text-transform:uppercase}}
.hero-spec .v{{font-family:{FONT};font-size:12px;color:{WHITE};margin-top:4px;letter-spacing:0.04em}}

/* ════ MTDI CARDS ════ */
.mtdi-field-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:18px 0 34px}}
@media(max-width:1050px){{.mtdi-field-grid{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:640px){{.mtdi-field-grid{{grid-template-columns:1fr}}}}
.mtdi-field-link{{text-decoration:none;color:inherit;display:block}}
.mtdi-field-card{{height:100%;min-height:150px;background:{SURFACE};border:1px solid rgba(255,255,255,0.08);border-top:2px solid var(--acc,#2979ff);border-radius:18px;padding:20px;position:relative;overflow:hidden;transition:transform .25s,border-color .25s,box-shadow .25s}}
.mtdi-field-card:hover{{transform:translateY(-4px);border-color:var(--acc,#2979ff);box-shadow:0 20px 60px var(--glow,rgba(41,121,255,0.15))}}
.mtdi-field-num{{font-family:{FONT};font-size:10px;letter-spacing:.22em;color:var(--acc,#2979ff);margin-bottom:14px;text-transform:uppercase}}
.mtdi-field-title{{font-family:{FONT};font-size:13px;letter-spacing:.1em;color:#e8eeff;text-transform:uppercase;margin-bottom:10px;line-height:1.35}}
.mtdi-field-desc{{font-family:{FONTUI};font-size:11.5px;line-height:1.7;color:#9aa7bc}}
.mtdi-section-card{{scroll-margin-top:80px;background:linear-gradient(145deg,rgba(18,25,40,0.72),rgba(13,19,32,0.7));border:1px solid rgba(255,255,255,0.075);border-top:1px solid var(--acc,#2979ff);border-radius:22px;padding:28px;margin-bottom:28px;position:relative;overflow:hidden;box-shadow:0 18px 64px rgba(0,0,0,0.20)}}
.mtdi-section-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--acc,#2979ff),transparent);opacity:.65}}
.mtdi-section-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;margin-bottom:22px;position:relative;z-index:1}}
.mtdi-section-kicker{{font-family:{FONT};font-size:9px;letter-spacing:.34em;color:var(--acc,#2979ff);text-transform:uppercase;margin-bottom:8px}}
.mtdi-section-title{{font-family:{FONT};font-size:25px;letter-spacing:.11em;color:#e8eeff;text-transform:uppercase;line-height:1.25;text-shadow:0 0 18px var(--glow,rgba(41,121,255,0.25))}}
.mtdi-section-copy{{font-family:{FONTUI};font-size:13px;line-height:1.9;color:#aab6cc;max-width:900px;opacity:.92}}
.layer-pill{{font-family:{FONT};font-size:9px;letter-spacing:.2em;color:var(--acc,#2979ff);border:1px solid var(--soft,rgba(41,121,255,0.25));background:var(--softbg,rgba(41,121,255,0.06));border-radius:999px;padding:7px 13px;text-transform:uppercase;white-space:nowrap}}
.confidence-shell{{display:grid;grid-template-columns:240px 1fr;gap:18px;align-items:center;margin-top:20px}}
@media(max-width:900px){{.confidence-shell{{grid-template-columns:1fr}}}}
.aether-verse{{font-family:{FONTUI};font-size:15px;line-height:2.05;color:#e8eeff;opacity:.9;max-width:980px}}
.aether-verse .heat{{color:#ff5252;text-shadow:0 0 16px rgba(255,82,82,0.35)}}
.i3-principle-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:18px}}
@media(max-width:800px){{.i3-principle-grid{{grid-template-columns:1fr}}}}
.i3-principle{{background:rgba(179,136,255,0.06);border:1px solid rgba(179,136,255,0.17);border-left:3px solid #b388ff;border-radius:14px;padding:18px 20px}}
.i3-principle h4{{font-family:{FONT};font-size:12px;letter-spacing:.18em;color:#b388ff;text-transform:uppercase;margin:0 0 8px}}
.i3-principle p{{font-family:{FONTUI};font-size:12px;line-height:1.75;color:#e8eeff;opacity:.82;margin:0}}

.inspo-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;margin-bottom:16px;border:1px solid rgba(255,255,255,0.08);border-radius:12px;overflow:hidden;background:rgba(255,255,255,0.08)}}
@media(max-width:900px){{.inspo-grid{{grid-template-columns:1fr}}}}
.inspo-card{{background:#0d131f;border:0;border-radius:0;padding:20px 22px;position:relative;overflow:hidden;box-shadow:none}}
.inspo-card::before{{display:none}}
.inspo-card-kicker{{font-family:{FONT};font-size:9px;letter-spacing:0.24em;color:#8d99ad!important;margin-bottom:10px;position:relative;z-index:1}}
.inspo-card-quote{{font-family:{FONTUI};font-size:12.5px;color:#dce3ee;line-height:1.75;opacity:0.82;position:relative;z-index:1}}
.inspo-card-by{{font-family:{FONT};font-size:9px;letter-spacing:.08em;color:var(--c-sub);margin-top:10px;position:relative;z-index:1}}
.power-layer-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:18px}}
@media(max-width:1100px){{.power-layer-grid{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:640px){{.power-layer-grid{{grid-template-columns:1fr}}}}
.power-layer-link{{text-decoration:none;color:inherit;display:block}}
.power-layer-card{{background:{SURFACE};border:1px solid rgba(255,255,255,0.075);border-top:2px solid var(--acc,#ffca28);border-radius:16px;padding:18px 18px 20px;min-height:180px;position:relative;overflow:hidden;transition:transform .22s,border-color .22s,box-shadow .22s;cursor:pointer}}
.power-layer-card:hover{{transform:translateY(-5px);border-color:var(--acc,#ffca28);box-shadow:0 18px 52px var(--glow,rgba(255,202,40,0.16))}}
.power-layer-card::after{{content:'';position:absolute;top:-60px;right:-60px;width:160px;height:160px;background:radial-gradient(circle,var(--glow,rgba(41,121,255,0.12)),transparent 70%);pointer-events:none}}
.power-layer-short{{font-family:{FONT};font-size:17px;letter-spacing:0.12em;text-transform:uppercase;position:relative;z-index:1}}
.power-layer-title{{font-family:{FONT};font-size:9.5px;letter-spacing:0.22em;color:#e9eefc;text-transform:uppercase;margin:8px 0 12px;position:relative;z-index:1}}
.power-layer-copy{{font-family:{FONTUI};font-size:12px;line-height:1.78;color:#cbd4e6;position:relative;z-index:1}}
.validation-hero-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-top:12px}}
@media(max-width:1100px){{.validation-hero-grid{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:640px){{.validation-hero-grid{{grid-template-columns:1fr}}}}
.validation-hero-card{{background:{SURFACE};border:1px solid rgba(255,255,255,0.08);border-top:2px solid var(--acc,#2979ff);border-radius:18px;padding:20px 18px;min-height:200px;position:relative;overflow:hidden}}
.validation-hero-card::after{{content:'';position:absolute;top:-54px;right:-54px;width:140px;height:140px;background:radial-gradient(circle,rgba(41,121,255,0.18),transparent 72%);pointer-events:none}}
.sort-title{{font-family:{FONT};font-size:10px;letter-spacing:.18em;color:var(--acc,#2979ff);text-transform:uppercase;margin-bottom:8px}}
.sort-body{{font-family:{FONTUI};font-size:12px;line-height:1.75;color:#e8eeff;opacity:.82}}
.sort-foot{{font-family:{FONT};font-size:8.5px;letter-spacing:0.12em;color:var(--acc,#2979ff);text-transform:uppercase;margin-top:10px;opacity:0.75}}
.validation-subcopy{{font-family:{FONTUI};font-size:12px;color:#92a5c6;line-height:1.7;margin:10px 0 14px}}
.validation-live-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start}}
@media(max-width:900px){{.validation-live-grid{{grid-template-columns:1fr}}}}
.validation-live-block{{background:{SURFACE};border:1px solid rgba(255,255,255,0.07);border-radius:16px;padding:18px 18px 16px}}
.aether-manifesto{{font-family:{FONT};font-size:11px;letter-spacing:0.14em;color:{RED};text-transform:uppercase;line-height:1.9;margin-bottom:18px;opacity:.92}}
.aether-grid{{display:grid;grid-template-columns:1.25fr 1fr;gap:18px;align-items:start;margin:14px 0 20px}}
@media(max-width:900px){{.aether-grid{{grid-template-columns:1fr}}}}
.aether-block{{display:flex;flex-direction:column;gap:14px}}
.aether-journal{{font-family:{FONTUI};font-size:13px;line-height:1.9;color:#e8eeff;opacity:0.89;background:{SURFACE};border:1px solid rgba(255,255,255,0.07);border-left:2px solid rgba(255,82,82,0.5);border-radius:14px;padding:16px 18px}}
.aether-journal.large{{margin-top:4px}}
.aether-claim{{font-family:{FONT};font-size:9.5px;letter-spacing:0.16em;color:{WHITE};text-transform:uppercase;background:linear-gradient(135deg,rgba(255,82,82,0.14),rgba(20,28,45,0.7));border:1px solid rgba(255,82,82,0.20);border-radius:12px;padding:14px 16px}}

/* ════ NVTRA identity block ════ */
.nvtra-intel-card{{background:rgba(7,9,15,0.82);border:1px solid rgba(0,229,255,0.14);border-top:2px solid rgba(0,229,255,0.55);box-shadow:0 0 0 1px rgba(0,229,255,0.04) inset,0 16px 64px rgba(0,0,0,0.5);border-radius:20px;overflow:hidden;margin-bottom:24px;position:relative}}
.nvtra-intel-header{{display:flex;align-items:center;justify-content:space-between;padding:18px 26px 16px;border-bottom:1px solid rgba(255,255,255,0.05)}}
.nvtra-logo-ring{{width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,rgba(0,229,255,0.12) 0%,rgba(41,121,255,0.08) 100%);border:1px solid rgba(0,229,255,0.35);display:flex;align-items:center;justify-content:center;font-family:{FONT};font-size:10px;letter-spacing:0.06em;color:{CYAN};box-shadow:0 0 16px rgba(0,229,255,0.2),inset 0 0 12px rgba(0,229,255,0.06);flex-shrink:0;animation:pulseSoft 3.5s ease-in-out infinite}}
.nvtra-badge{{font-family:{FONT};font-size:9px;letter-spacing:0.28em;text-transform:uppercase;color:{CYAN};background:rgba(0,229,255,0.05);border:1px solid rgba(0,229,255,0.2);border-radius:20px;padding:5px 14px;text-shadow:0 0 10px rgba(0,229,255,0.5);flex-shrink:0}}
.nvtra-stats-row{{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.05)}}
@media(max-width:700px){{.nvtra-stats-row{{grid-template-columns:repeat(2,1fr)}}}}
.nvtra-stat{{background:rgba(7,9,15,0.9);padding:16px 14px;position:relative;overflow:hidden}}
.nvtra-stat::after{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--acc,{CYAN}),transparent);opacity:0.5}}
.nvtra-stat-val{{font-family:{FONT};font-size:20px;color:var(--acc,{CYAN});letter-spacing:-0.02em;line-height:1;margin-bottom:4px}}
.nvtra-stat-key{{font-family:{FONT};font-size:8px;color:{SUBTEXT};letter-spacing:0.2em;text-transform:uppercase}}
.nvtra-stat-desc{{font-family:{FONTUI};font-size:9px;color:rgba(92,110,138,0.5);margin-top:3px;font-style:italic}}
.nvtra-identity-panel{{padding:30px 34px 28px;background:linear-gradient(135deg,rgba(0,229,255,0.025) 0%,rgba(7,9,15,0) 60%)}}
.nvtra-identity-kicker{{font-family:{FONT};font-size:8px;letter-spacing:0.34em;color:rgba(0,229,255,0.72);text-transform:uppercase;margin-bottom:12px}}
.nvtra-identity-title{{font-family:{FONT};font-size:30px;color:{CYAN};letter-spacing:0.18em;text-transform:uppercase;text-shadow:0 0 22px rgba(0,229,255,0.55),0 0 46px rgba(0,229,255,0.22);margin-bottom:10px}}
.nvtra-identity-text{{font-family:{FONTUI};font-size:13px;color:rgba(232,238,255,0.82);line-height:1.85;max-width:760px}}
.nvtra-house-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:22px}}
@media(max-width:900px){{.nvtra-house-grid{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:560px){{.nvtra-house-grid{{grid-template-columns:1fr}}}}
.nvtra-house-card{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px 14px 13px;position:relative;overflow:hidden}}
.nvtra-house-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--acc,{CYAN}),transparent);opacity:0.65}}
.nvtra-house-name{{font-family:{FONT};font-size:13px;color:var(--acc,{CYAN});letter-spacing:0.16em;text-transform:uppercase;margin-bottom:6px}}
.nvtra-house-role{{font-family:{FONT};font-size:8px;color:{SUBTEXT};letter-spacing:0.22em;text-transform:uppercase;margin-bottom:8px}}
.nvtra-house-desc{{font-family:{FONTUI};font-size:11px;color:rgba(232,238,255,0.68);line-height:1.65}}

/* ════ SETTINGS ════ */
.settings-stack{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;align-items:start}}
@media(max-width:880px){{.settings-stack{{grid-template-columns:1fr}}}}
.settings-group{{min-width:0}}
.settings-group .section-label{{margin-top:0!important;margin-bottom:12px}}
.settings-page>.section-label{{padding:0 0 10px;border-bottom:1px solid rgba(0,229,255,.20);
  color:#bfefff;letter-spacing:.25em}}
.settings-page>.page-subtitle{{padding:0 2px;color:#9fb0c7!important}}
.settings-page .key-btn{{min-height:40px;display:inline-flex;align-items:center;justify-content:center}}
.set-card{{background:linear-gradient(145deg,rgba(17,25,39,.92),rgba(10,16,27,.90));
  border:1px solid rgba(125,156,196,.22);border-top-color:rgba(0,229,255,.30);
  border-radius:18px;padding:10px 24px;box-shadow:0 16px 44px rgba(0,0,0,.18)}}
.set-row{{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px 0;border-bottom:1px solid rgba(255,255,255,0.06);flex-wrap:wrap}}
.set-row:last-child{{border-bottom:none}}
.set-row .set-lab b{{display:block;font-size:14px;font-weight:500;margin-bottom:3px;color:{WHITE}}}
.set-row .set-lab span{{font-size:12px;color:{SUBTEXT};font-family:{FONTUI}}}
.set-seg{{display:flex;gap:4px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:3px}}
.set-seg button{{font-family:{FONT};font-size:10px;letter-spacing:0.12em;text-transform:uppercase;color:{SUBTEXT};background:transparent;border:1px solid transparent;border-radius:7px;padding:8px 16px;cursor:pointer;transition:all 0.2s}}
.set-seg button:hover{{color:{WHITE}}}
.set-seg button.seg-active{{color:{CYAN};background:rgba(0,229,255,0.10);border-color:rgba(0,229,255,0.32);text-shadow:0 0 10px rgba(0,229,255,0.35)}}
"""

# ── theme / reduced-motion overrides (raw string; toggled by Settings) ──
GLOBAL_CSS += r"""

/* ===== MOTION KILL SWITCH (Settings -> Animations -> Off) ===== */
html.no-anim *,html.no-anim *::before,html.no-anim *::after{animation:none!important;transition:none!important}
html.no-anim #page-shader-canvas,html.no-anim #nvtra-mascot-canvas{display:none!important}
html.no-anim #nav-progress{display:none!important}

/* ===== SMOOTH VALUE UPDATES (no jitter, no reflow) ===== */
.metric-value,.sys-value,.module-live-val,.conf-ring-val,.sensor-conf-val,.nvtra-stat-val,
.disc-stat-val,.pill-val,.arch-stat-val,.ch3-dev-val,.ch3-peak-lvl,.ch3-peak-freq{
  font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}

/* ===== NO MOVEMENT ON LIVE REFRESH =====
   These regions are fully regenerated by Dash callbacks every 0.6-4s. Any entry
   animation on their contents reads as the block "fading in and jumping up" on each
   update, so every animation is suppressed inside them and each one reserves a
   minimum height so a shorter render cannot collapse the layout. */
#header-pills,#header-pills *,
#esp-sys-grid,#esp-sys-grid *,
#mtdi-sys-grid,#mtdi-sys-grid *,
#settings-sys-grid,#settings-sys-grid *,
#mtdi-sensor-grid,#mtdi-sensor-grid *,
#mtdi-overall,#mtdi-overall *,
#c2-warn,#c2-warn *,#c2-error,#c2-error *,
#c1-error,#c1-error *,#mag3d-error,#mag3d-error *,
#ch3-peak-body,#ch3-peak-body *,#ch3-dev-strip,#ch3-dev-strip *,
#ch3-warn,#ch3-warn *,#ch3-error,#ch3-error *,#ch3-arch-stats,#ch3-arch-stats *,
#wf-body,#wf-body *,#bt-body,#bt-body *,#lan-body,#lan-body *,
#key-list,#key-list *,#nvtra-key-bar,#nvtra-key-bar *,
.arch-stats,.arch-stats *,
.metric-value,.sys-value,.module-live-val,.conf-ring-val,.sensor-conf-val{
  animation:none!important;
}
#mtdi-overall{min-height:168px}
#ch3-peak-body{min-height:66px}
#wf-body,#bt-body,#lan-body{min-height:64px}
#key-list{min-height:64px}
#nvtra-key-bar{min-height:38px}
#c1-error,#mag3d-error,#c2-error,#c2-warn,#ch3-error,#ch3-warn,#wf-error,#bt-error,#lan-error{min-height:0}

/* ===== CHART GRID / PANELS ===== */
.chart-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:6px}
.chart-grid-primary{grid-template-columns:minmax(0,1fr)}
@media(max-width:820px){.chart-grid{grid-template-columns:1fr}}
.chart-grid>*,.threeup>*{min-width:0}
.chart-card{background:rgba(16,23,38,0.74);border:1px solid rgba(255,255,255,0.07);border-radius:16px;padding:16px 18px;overflow:hidden;min-width:0;transition:border-color .3s,box-shadow .3s;contain:layout style}
.chart-card:hover{border-color:rgba(0,229,255,0.28);box-shadow:0 10px 34px rgba(0,229,255,0.06)}
.chart-card .chart-hd{font-family:'DM Mono','Courier New',monospace;font-size:9px;letter-spacing:0.22em;color:var(--c-sub);text-transform:uppercase;margin-bottom:8px;min-height:12px}
/* Plotly injects its own wrappers after mount. Forcing them to fill the height the
   dcc.Graph already reserved is what stops the "graph pops in and pushes everything
   down" shift on first paint and on every figure swap. */
.chart-card .dash-graph,.chart-card .js-plotly-plot,.chart-card .plot-container{width:100%;min-width:0}
.js-plotly-plot .plotly .modebar{transition:none!important}
.threeup{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media(max-width:980px){.threeup{grid-template-columns:1fr}}
.threeup .chart-card{padding:10px}

/* ===== SIGNAL ARCHIVE ===== */
.arch-shell{background:linear-gradient(145deg,rgba(12,32,44,0.76),rgba(16,23,38,0.74));border:1px solid rgba(0,229,255,0.16);border-radius:18px;padding:22px 24px;position:relative;overflow:hidden}
.arch-shell::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,rgba(0,229,255,0.5),transparent)}
.arch-stats{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin-top:14px}
.arch-stat{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px 16px;min-height:74px;transition:border-color .25s}
.arch-stat:hover{border-color:rgba(0,229,255,0.3)}
.arch-stat-val{font-family:'DM Mono','Courier New',monospace;font-size:20px;color:#e8eeff;letter-spacing:-0.02em}
.arch-stat-key{font-family:'DM Mono','Courier New',monospace;font-size:8px;color:var(--c-sub);letter-spacing:0.2em;text-transform:uppercase;margin-top:6px}

/* ===== NVTRA CHAT ===== */
.nvtra-chat-workspace{display:grid;grid-template-columns:220px minmax(0,1fr);margin:30px;
  min-height:590px;border:1px solid rgba(0,229,255,.14);border-radius:18px;overflow:hidden;
  background:radial-gradient(circle at 72% 12%,rgba(179,136,255,.08),transparent 34%),
  linear-gradient(145deg,rgba(8,14,25,.98),rgba(3,6,12,.98));box-shadow:0 22px 60px rgba(0,0,0,.3)}
.nvtra-session-sidebar{display:flex;flex-direction:column;min-width:0;padding:18px 12px;
  border-right:1px solid rgba(255,255,255,.07);background:rgba(7,12,21,.7)}
.session-sidebar-head{padding:3px 3px 12px}.session-sidebar-label{font-family:'DM Mono',monospace;
  color:var(--c-sub);font-size:7px;letter-spacing:.24em;margin:0 4px 10px}
.new-session-btn{width:100%;padding:11px 12px;border-radius:10px;border:1px solid rgba(0,229,255,.24);
  background:linear-gradient(135deg,rgba(0,229,255,.12),rgba(179,136,255,.08));color:#c9f8ff;
  font:700 8px 'DM Mono',monospace;letter-spacing:.14em;cursor:pointer;text-align:left}
.new-session-btn:hover{border-color:rgba(0,229,255,.55);box-shadow:0 0 18px rgba(0,229,255,.1)}
.session-list{display:flex;flex-direction:column;gap:4px;overflow-y:auto;max-height:525px;margin-top:8px}
.chat-session{display:flex;flex-direction:column;gap:5px;width:100%;padding:10px 11px;border:1px solid transparent;
  border-radius:11px;background:transparent;color:#dce8f8;text-align:left;cursor:pointer;min-width:0}
.chat-session:hover{background:rgba(255,255,255,.035);border-color:rgba(255,255,255,.07)}
.chat-session.active{background:rgba(0,229,255,.075);border-color:rgba(0,229,255,.23)}
.session-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font:600 11px 'Inter',sans-serif}
.session-meta{font:7px 'DM Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--c-sub)}
.nvtra-chat-main{min-width:0;padding:24px 28px}.chat-main-head{text-align:left;padding:2px 2px 20px}
.chat-main-brand{font:700 11px 'DM Mono',monospace;letter-spacing:.35em;color:#E3B945;display:flex;align-items:center;gap:10px}
.nvtra-mark{height:18px;width:auto;display:block;filter:drop-shadow(0 0 6px rgba(227,185,69,.35))}
.chat-session-title{font:600 22px 'Inter',sans-serif;color:#f4f7ff;margin-top:8px}
.nvtra-model-picker{position:relative;margin:10px 12px 4px;width:min(360px,calc(100% - 24px))}
.nvtra-model-picker summary{display:flex;align-items:center;gap:8px;list-style:none;cursor:pointer;
  min-height:38px;padding:0 11px;border:1px solid rgba(115,145,184,.22);border-radius:11px;
  background:linear-gradient(135deg,rgba(19,29,46,.94),rgba(10,16,28,.94));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04);transition:border-color .18s,background .18s}
.nvtra-model-picker summary:hover{border-color:rgba(0,229,255,.35);background:linear-gradient(135deg,rgba(22,36,54,.96),rgba(11,19,32,.96))}
.nvtra-model-picker[open] summary{border-color:rgba(179,136,255,.44);background:rgba(179,136,255,.09)}
.nvtra-model-picker summary::-webkit-details-marker{display:none}.model-picker-cap{font:700 7px 'DM Mono',monospace;
  letter-spacing:.18em;color:#b388ff}.model-picker-current{min-width:0;flex:1;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap;font:500 11px 'Inter',sans-serif;color:#e6eefb}.model-picker-chevron{color:#8ea2bd;transition:transform .18s}
.nvtra-model-picker[open] .model-picker-chevron{transform:rotate(180deg)}
.model-picker-menu{position:absolute;left:0;width:min(360px,calc(100vw - 70px));bottom:calc(100% + 8px);z-index:50;padding:8px;
  border:1px solid rgba(179,136,255,.3);border-radius:13px;background:linear-gradient(155deg,#101827,#070c16);
  box-shadow:0 22px 55px rgba(0,0,0,.62),0 0 28px rgba(179,136,255,.08);display:flex;flex-direction:column;gap:4px;max-height:280px;overflow:auto}
.model-choice{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:3px 8px;padding:9px 10px;border:1px solid transparent;
  border-radius:8px;background:transparent;color:#e6eefb;text-align:left;cursor:pointer}
.model-choice:hover{background:rgba(255,255,255,.045);border-color:rgba(255,255,255,.08)}
.model-choice.active{background:linear-gradient(135deg,rgba(0,229,255,.10),rgba(179,136,255,.08));border-color:rgba(0,229,255,.25)}
.model-choice-name{font:600 10px 'Inter',sans-serif}.model-choice-id{grid-column:1;font:7px 'DM Mono',monospace;color:var(--c-sub)}
.model-choice-check{grid-column:2;grid-row:1/3;align-self:center;color:#00e5ff}.model-config-link{padding:9px 10px;
  color:#8ceeff;text-decoration:none;font:8px 'DM Mono',monospace;letter-spacing:.1em}
/* NVTRA model switching: a larger target, clearer current selection and a menu
   wide enough to read provider/model names without precision clicking. */
.nvtra-model-picker{width:min(520px,calc(100% - 24px))}
.nvtra-model-picker summary{min-height:48px;padding:0 15px;border-color:rgba(0,229,255,.28)}
.model-picker-cap{font-size:8px}.model-picker-current{font-size:12px}
.model-picker-menu{position:static;left:auto;bottom:auto;width:100%;max-height:300px;
  margin-top:8px;padding:10px;gap:6px;box-shadow:0 14px 34px rgba(0,0,0,.42)}
.model-choice{min-height:50px;padding:11px 13px;border-color:rgba(255,255,255,.055)}
.model-choice-name{font-size:12px}.model-choice-id{font-size:8px;margin-top:2px}
.model-choice-check{font-size:16px}.model-config-link{font-size:9px;padding:12px 13px}

@media(max-width:760px){.nvtra-chat-workspace{grid-template-columns:1fr;margin:14px 10px}
  .nvtra-session-sidebar{border-right:0;border-bottom:1px solid rgba(255,255,255,.07)}
  .session-list{max-height:135px}.nvtra-chat-main{padding:18px 14px}}
.nvtra-history-drawer{position:fixed;right:18px;top:86px;z-index:780;width:48px;max-height:calc(100vh - 110px);
  border:1px solid rgba(0,229,255,.28);border-radius:14px;background:rgba(6,11,20,.96);
  box-shadow:0 18px 55px rgba(0,0,0,.42),0 0 24px rgba(0,229,255,.06);overflow:hidden;
  transition:width .22s ease}
.nvtra-history-drawer[open]{width:min(430px,calc(100vw - 28px))}
.nvtra-history-drawer summary{height:46px;display:flex;align-items:center;justify-content:center;gap:9px;
  padding:0 13px;list-style:none;cursor:pointer;white-space:nowrap;font-family:'DM Mono',monospace;
  font-size:8px;letter-spacing:.18em;color:#9cefff;background:linear-gradient(135deg,rgba(0,229,255,.11),rgba(41,121,255,.06))}
.nvtra-history-drawer summary::-webkit-details-marker{display:none}
.nvtra-history-drawer:not([open]) summary span:first-child{display:none}
.history-count{display:grid;place-items:center;min-width:20px;height:20px;border-radius:7px;
  background:rgba(0,229,255,.12);border:1px solid rgba(0,229,255,.24);color:#dffcff;letter-spacing:0}
.nvtra-history-scroll{max-height:calc(100vh - 158px);overflow-y:auto;padding:10px}
.nvtra-history-record{padding:13px 14px;margin-bottom:9px;border:1px solid rgba(255,255,255,.075);
  border-radius:12px;background:linear-gradient(145deg,rgba(16,25,40,.88),rgba(8,14,24,.9))}
.nvtra-history-time{font-family:'DM Mono',monospace;font-size:7px;letter-spacing:.12em;color:var(--c-sub);margin-bottom:8px}
.nvtra-history-question{font-size:12px;font-weight:600;line-height:1.45;color:#eaf5ff;margin-bottom:8px}
.nvtra-history-answer{font-size:11.5px;line-height:1.55;color:#9fb3cd;border-left:2px solid rgba(0,229,255,.35);padding-left:9px}
.nvtra-history-answer.history-error{border-color:#ffab40;color:#e8bc87}
.nvtra-history-empty{padding:20px 14px;color:#8395ad;font-size:12px;line-height:1.55}
@media(max-width:700px){.nvtra-history-drawer{right:8px;top:72px}.nvtra-history-drawer[open]{width:calc(100vw - 16px)}}
.nvtra-unified-main{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(300px,0.95fr);gap:0;border-bottom:1px solid rgba(255,255,255,0.055)}
@media(max-width:950px){.nvtra-unified-main{grid-template-columns:1fr}}
.nvtra-robot-panel{display:flex;align-items:center;justify-content:center;min-height:360px;background:radial-gradient(circle at 50% 45%,rgba(0,229,255,0.08) 0%,rgba(41,121,255,0.035) 35%,transparent 68%);position:relative;overflow:hidden;border-left:1px solid rgba(255,255,255,0.055)}
@media(max-width:950px){.nvtra-robot-panel{border-left:none;border-top:1px solid rgba(255,255,255,0.055)}}
.nvtra-robot-panel::after{content:'NVTRA · OPERATOR-SUPPLIED AI';position:absolute;bottom:16px;left:50%;transform:translateX(-50%);font-family:'DM Mono',monospace;font-size:8px;letter-spacing:0.32em;color:rgba(0,229,255,0.34);text-transform:uppercase;white-space:nowrap;pointer-events:none}
.nvtra-spline-host{position:relative;z-index:2;width:100%;height:620px;min-height:560px;overflow:hidden}
#nvtra-spline-canvas{display:block;width:100%;height:100%;background:transparent;position:relative;z-index:2;touch-action:none}
.nvtra-spline-loading{position:absolute;inset:0;z-index:5;display:grid;place-items:center;background:#050507;pointer-events:none;overflow:hidden;transition:opacity .35s ease}
#nvtra-loader-canvas{display:block;width:min(360px,92%);aspect-ratio:1;border-radius:20px;background:#050507}
.nvtra-loader-caption{position:absolute;left:50%;bottom:28px;translate:-50% 0;color:rgba(232,238,255,.66);font:8px 'DM Mono',monospace;letter-spacing:.28em;text-transform:uppercase;white-space:nowrap}
.nvtra-mascot-label{z-index:4}
@media(max-width:950px){.nvtra-spline-host{height:560px;min-height:500px}}
.p1-mode-tabs{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px!important;padding:6px!important;margin:0 0 24px!important;min-height:58px;border:1px solid rgba(124,157,199,.22)!important;border-radius:16px;background:linear-gradient(180deg,rgba(16,25,40,.94),rgba(8,14,24,.94));box-shadow:inset 0 1px 0 rgba(255,255,255,.045),0 14px 34px rgba(0,0,0,.18);overflow:visible!important}
.p1-mode-tabs .tab-btn{display:flex;align-items:center;justify-content:center;min-width:0!important;width:100%;min-height:44px;margin:0!important;padding:10px 12px!important;border:1px solid transparent!important;border-radius:11px!important;line-height:1.25;white-space:normal;text-align:center;color:#91a3bc;background:transparent}
.p1-mode-tabs .tab-btn:hover{color:#eaf8ff;background:rgba(255,255,255,.045)}
.p1-mode-tabs .tab-btn.active{color:#eaffff!important;border-color:rgba(0,229,255,.35)!important;background:linear-gradient(135deg,rgba(0,229,255,.16),rgba(41,121,255,.12))!important;box-shadow:inset 0 1px 0 rgba(255,255,255,.07),0 0 22px rgba(0,229,255,.09);text-shadow:none!important}
@media(max-width:760px){.p1-mode-tabs{overflow:visible!important;scroll-snap-type:none!important}.p1-mode-tabs .tab-btn{min-width:0!important;font-size:10px!important}}
.nvtra-chat-wrap{padding:18px 22px 22px;position:relative}
.nvtra-chat-label{display:flex;align-items:center;gap:8px;margin-bottom:14px;font-family:'DM Mono',monospace;font-size:8px;letter-spacing:0.22em;text-transform:uppercase;color:#71829b}
.nvtra-chat-label .nl-dot{width:5px;height:5px;border-radius:50%;background:#5c6e8a;flex-shrink:0}
.nvtra-live-chat{position:relative;display:flex;flex-direction:column;background:rgba(5,9,16,.62);border:1px solid rgba(0,229,255,0.12);border-radius:16px;overflow:visible;box-shadow:inset 0 1px 0 rgba(255,255,255,0.035)}
.nvtra-msgs{position:relative;z-index:2;flex:1;min-height:285px;max-height:520px;overflow-y:auto;padding:24px;display:flex;flex-direction:column;gap:15px}
.nvtra-msg-ai{align-self:flex-start;background:rgba(0,229,255,0.045);border:1px solid rgba(0,229,255,0.13);border-radius:13px 13px 13px 4px;padding:11px 14px;font-family:'Inter',sans-serif;font-size:12.5px;color:rgba(232,238,255,0.92);max-width:82%;line-height:1.65;white-space:pre-wrap}
.nvtra-msg-user{align-self:flex-end;background:linear-gradient(135deg,rgba(41,121,255,0.22),rgba(41,121,255,0.14));
  border:1px solid rgba(41,121,255,0.4);border-radius:13px 13px 4px 13px;padding:9px 14px;
  font-family:'Inter',sans-serif;font-size:12.5px;color:#eaf1ff;max-width:88%;line-height:1.62}
.nvtra-msg-sender{font-family:'DM Mono',monospace;font-size:8px;letter-spacing:0.24em;text-transform:uppercase;margin-bottom:5px;color:rgba(0,229,255,0.8)}
.nvtra-live-text{white-space:pre-wrap}
.nvtra-caret{display:inline-block;color:#00e5ff;animation:cursorBlink 1s step-end infinite;font-weight:700}
.nvtra-msg-err{border-color:rgba(255,171,64,0.4);background:rgba(255,171,64,0.08);color:rgba(255,220,180,0.95)}
.nvtra-msg-err .nvtra-msg-sender{color:rgba(255,171,64,0.9)}
.nvtra-sug-row{display:flex;flex-wrap:wrap;gap:7px;padding:10px 12px 2px;position:relative;z-index:2;
  border-top:1px solid rgba(255,255,255,0.05)}
.nvtra-sug{font-family:'Inter',sans-serif;font-size:11px;letter-spacing:0.01em;font-weight:500;
  color:#8fe9ff;background:rgba(0,229,255,0.07);border:1px solid rgba(0,229,255,0.24);border-radius:14px;
  padding:7px 13px;cursor:pointer;transition:all .18s;line-height:1.25}
.nvtra-sug:hover{background:rgba(0,229,255,0.16);color:#d6f7ff;box-shadow:0 0 14px rgba(0,229,255,0.2);
  border-color:rgba(0,229,255,0.45)}
.nvtra-sug:active{transform:scale(0.96)}
.nvtra-sug:disabled{opacity:0.4;cursor:not-allowed}
.nvtra-input-bar{position:relative;z-index:2;display:flex;flex-direction:column;align-items:stretch;
  margin:12px;padding:0;background:linear-gradient(145deg,rgba(12,19,31,.96),rgba(5,10,18,.96));
  border:1px solid rgba(0,229,255,.30);border-radius:16px;overflow:hidden;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.055),0 12px 32px rgba(0,0,0,.26),0 0 28px rgba(0,229,255,.055)}
.nvtra-composer-meta{display:flex;align-items:center;gap:8px;padding:9px 13px 7px;
  border-bottom:1px solid rgba(255,255,255,.055);font-family:'DM Mono',monospace;
  font-size:7.5px;letter-spacing:.22em;text-transform:uppercase;color:#75dff2}
.nvtra-composer-meta::before{content:'I³';display:grid;place-items:center;width:22px;height:17px;
  border:1px solid rgba(0,229,255,.34);border-radius:6px;background:rgba(0,229,255,.08);
  color:#d8fbff;font-weight:700;letter-spacing:0;box-shadow:0 0 12px rgba(0,229,255,.12)}
.nvtra-composer-row{display:flex;align-items:center;gap:10px;padding:9px 11px 11px}
.nvtra-composer-status{display:flex;align-items:center;gap:6px;flex:0 0 auto;font-family:'DM Mono',monospace;
  font-size:7px;letter-spacing:.16em;color:#6f839f;text-transform:uppercase}
.nvtra-composer-status::before{content:'';width:5px;height:5px;border-radius:50%;background:#00e676;
  box-shadow:0 0 9px rgba(0,230,118,.65)}
.nvtra-input-bar .nvtra-composer-row>input{display:block;min-width:0;flex:1;background:#080f1b!important;border:1px solid rgba(255,255,255,.07)!important;
  outline:none!important;box-shadow:none!important;font-family:'Inter',sans-serif;font-size:14px;font-weight:500;
  line-height:1.45;color:#f4f8ff!important;-webkit-text-fill-color:#f4f8ff!important;opacity:1!important;
  letter-spacing:.005em;padding:10px 12px!important;border-radius:10px!important;caret-color:#00e5ff!important;color-scheme:dark;-webkit-appearance:none}
.nvtra-input-bar input::selection{color:#061019;background:#66efff}
.nvtra-input-bar input::placeholder{color:#899ab2!important;-webkit-text-fill-color:#899ab2!important;opacity:1!important}
.nvtra-input-bar input:disabled{color:#728097!important;-webkit-text-fill-color:#728097!important;opacity:.72!important}
.nvtra-send{width:34px;height:34px;border-radius:11px;background:rgba(92,110,138,0.35);border:1px solid rgba(255,255,255,.08);display:flex;align-items:center;justify-content:center;color:#0a0f18;font-size:15px;font-weight:700;flex-shrink:0;cursor:not-allowed}
.nvtra-send:not(:disabled){background:#00e5ff;cursor:pointer;box-shadow:0 0 14px rgba(0,229,255,0.4);
  transition:transform .15s,box-shadow .2s}
.nvtra-send:not(:disabled):hover{box-shadow:0 0 22px rgba(0,229,255,0.6)}
.nvtra-send:not(:disabled):active{transform:scale(0.9)}
@media(max-width:560px){.nvtra-composer-status{display:none}.nvtra-input-bar{margin:10px}.nvtra-composer-meta{letter-spacing:.14em}}
.nvtra-badge.nvtra-live{color:#00e676;border-color:rgba(0,230,118,0.35);background:rgba(0,230,118,0.06)}
.nvtra-mascot-wrap{width:100%;max-width:300px;height:300px;position:relative;display:flex;align-items:center;justify-content:center}
#nvtra-mascot-canvas{width:100%;height:100%;display:block}
.nvtra-mascot-label{position:absolute;bottom:6px;left:50%;transform:translateX(-50%);font-family:'DM Mono',monospace;
  font-size:8px;letter-spacing:0.28em;color:rgba(0,229,255,0.5);text-transform:uppercase;white-space:nowrap;pointer-events:none}

/* ===== API KEY MANAGER ===== */
.key-mgr{display:flex;flex-direction:column;gap:10px}
.key-row{display:flex;align-items:center;gap:12px;padding:12px 14px;border:1px solid rgba(255,255,255,0.08);
  border-radius:12px;background:rgba(255,255,255,0.03);transition:border-color .2s,background .2s}
.key-row.key-active{border-color:rgba(0,229,255,0.4);background:rgba(0,229,255,0.05)}
.key-radio{width:20px;height:20px;border-radius:50%;border:2px solid rgba(255,255,255,0.25);flex-shrink:0;
  cursor:pointer;display:flex;align-items:center;justify-content:center;background:transparent;padding:0;transition:border-color .2s}
.key-row.key-active .key-radio{border-color:#00e5ff}
.key-radio-dot{width:9px;height:9px;border-radius:50%;background:#00e5ff;box-shadow:0 0 8px #00e5ff}
.key-info{flex:1;min-width:0}
.key-label{font-family:'Inter',sans-serif;font-size:13px;color:#e8eeff;font-weight:500;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.key-name-edit{min-width:120px;max-width:240px;flex:1;background:transparent!important;border:1px solid transparent!important;
  border-radius:7px!important;padding:4px 7px!important;outline:none!important;box-shadow:none!important;
  font-family:'Inter',sans-serif!important;font-size:13px!important;font-weight:500!important;
  color:#e8eeff!important;-webkit-text-fill-color:#e8eeff!important;caret-color:#00e5ff!important}
.key-name-edit:hover,.key-name-edit:focus{background:rgba(0,229,255,.055)!important;border-color:rgba(0,229,255,.28)!important}
.key-mask{font-family:'DM Mono',monospace;font-size:11px;color:var(--c-sub);margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.key-badge{font-family:'DM Mono',monospace;font-size:8px;letter-spacing:0.2em;text-transform:uppercase;color:#00e5ff;
  border:1px solid rgba(0,229,255,0.3);border-radius:5px;padding:2px 7px;flex-shrink:0}
.key-prov{font-family:'DM Mono',monospace;font-size:8px;letter-spacing:0.16em;text-transform:uppercase;color:#b388ff;
  border:1px solid rgba(179,136,255,0.32);border-radius:5px;padding:2px 7px;flex-shrink:0}
.key-model{font-family:'DM Mono',monospace;font-size:7px;letter-spacing:.08em;color:var(--c-sub);
  border:1px solid rgba(125,145,173,.24);border-radius:5px;padding:2px 7px;flex-shrink:0}
.key-name-save{background:rgba(0,229,255,.07);border:1px solid rgba(0,229,255,.25);color:#8feeff;
  border-radius:8px;padding:8px 10px;font-family:'DM Mono',monospace;font-size:7px;letter-spacing:.12em;
  white-space:nowrap;cursor:pointer}
.key-name-save:hover{background:rgba(0,229,255,.16);border-color:rgba(0,229,255,.5);color:#e4fcff}
.key-del{background:rgba(255,82,82,0.08);border:1px solid rgba(255,82,82,0.25);color:#ff5252;border-radius:8px;
  width:32px;height:32px;cursor:pointer;flex-shrink:0;font-size:13px;transition:background .2s}
.key-del:hover{background:rgba(255,82,82,0.2)}
.key-add-row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px}
.key-add-row input{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:10px;
  padding:11px 13px;color:#e8eeff;font-family:'DM Mono',monospace;font-size:12px;outline:none;transition:border-color .2s;caret-color:#00e5ff}
.key-add-row input:focus{border-color:rgba(0,229,255,0.4)}
.key-add-row input::placeholder{color:rgba(140,168,200,0.6)}
#key-add-input{flex:1;min-width:240px}
#key-label-input{width:150px;flex-shrink:0}
.key-provider-select{width:190px;min-width:170px;font-family:'DM Mono',monospace;font-size:11px}
.key-provider-select .Select-control{background:#0e1725!important;border:1px solid #40516b!important;
  color:#f4f7ff!important;border-radius:10px!important;height:40px}
.key-provider-select .Select-value-label,.key-provider-select .Select-placeholder{color:#dce7f7!important}
.key-provider-select .Select-menu-outer{background:#111b2b!important;border-color:#40516b!important;color:#eef4ff!important;z-index:20}
.key-provider-select .VirtualizedSelectOption{background:#111b2b!important;color:#dce7f7!important}
.key-provider-select .VirtualizedSelectFocusedOption{background:#17324a!important;color:#fff!important}
.key-btn{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:0.12em;text-transform:uppercase;
  padding:11px 16px;border-radius:10px;cursor:pointer;transition:all .2s;border:1px solid;white-space:nowrap}
.key-btn:active{transform:scale(0.96)}
.key-btn-add{background:rgba(0,229,255,0.1);border-color:rgba(0,229,255,0.35);color:#00e5ff}
.key-btn-add:hover{background:#00e5ff;color:#04121a;box-shadow:0 0 18px rgba(0,229,255,0.3)}
.key-btn.export-generating{pointer-events:none;opacity:.78;color:#04121a;background:#00e5ff}
.key-btn-test{background:rgba(255,255,255,0.04);border-color:rgba(255,255,255,0.15);color:#9fb2cc}
.key-btn-test:hover{border-color:rgba(0,229,255,0.35);color:#e8eeff}
.key-status{font-family:'DM Mono',monospace;font-size:11px;color:var(--c-sub);min-height:32px;letter-spacing:0.03em;line-height:1.5}
.key-empty{padding:16px;border:1px dashed rgba(0,229,255,.30);border-radius:12px;
  color:#b8c8dc;font:11px/1.6 'DM Mono',monospace;background:rgba(0,229,255,.035)}
.nvtra-key-bar{display:flex;align-items:center;gap:7px;flex-wrap:wrap;padding:10px 14px;
  border-top:1px solid rgba(255,255,255,0.05);position:relative;z-index:2}
.nvtra-key-cap{font-family:'DM Mono',monospace;font-size:8px;letter-spacing:0.24em;text-transform:uppercase;color:var(--c-sub);margin-right:2px}
.nvtra-key-pill{font-family:'DM Mono',monospace;font-size:9.5px;letter-spacing:0.04em;color:#8fa8c8;
  background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:20px;padding:5px 12px;cursor:pointer;transition:all .18s}
.nvtra-key-pill:hover{border-color:rgba(0,229,255,0.35);color:#e8eeff}
.nvtra-key-pill.nkp-active{color:#00e5ff;background:rgba(0,229,255,0.1);border-color:rgba(0,229,255,0.4);
  box-shadow:0 0 10px rgba(0,229,255,0.15)}

/* High-contrast form and slider controls. Dash's slider defaults were nearly
   invisible against the instrument panel, especially on the host computer display. */
.key-mask,.key-status,.nvtra-key-cap{color:#aebdd2}
.key-row{background:#111927;border-color:#334258}
.key-add-row input{background:#0e1725;border-color:#40516b;color:#f4f7ff}
.key-add-row input::placeholder{color:#91a3bd}
.c1-slider-wrap{min-width:320px;flex:1;padding:2px 14px 0}
.c1-slider-wrap{position:relative;border:1px solid rgba(77,112,156,.30);border-radius:14px;
  padding:16px 20px 10px;background:
  linear-gradient(180deg,rgba(5,10,19,.72),rgba(13,22,36,.54));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.035),inset 0 -12px 30px rgba(0,0,0,.16)}
.c1-slider-wrap::before{content:'FIELD OPTICS  ·  ZOOM';position:absolute;left:18px;top:7px;
  color:#7189aa;font:7px/1 'DM Mono',monospace;letter-spacing:.24em}
.c1-slider-wrap::after{content:'';position:absolute;left:20px;right:20px;bottom:10px;height:1px;
  background:linear-gradient(90deg,transparent,rgba(0,215,239,.35),transparent);pointer-events:none}
.c1-slider-wrap .dash-slider-container{padding:10px 10px 30px!important;min-height:48px;overflow:visible!important}
.c1-slider-wrap .dash-slider-wrapper{overflow:visible!important}
.c1-slider-wrap .dash-range-slider-input{display:none!important}
.c1-slider-wrap .dash-slider-tooltip{display:none!important}
.c1-slider-wrap .dash-slider-root{height:8px!important;margin:0 8px!important}
.c1-slider-wrap .dash-slider-track{height:7px!important;top:7px!important;background:#536985!important;
  border-radius:8px!important}
.c1-slider-wrap .dash-slider-range{height:7px!important;top:7px!important;
  background:linear-gradient(90deg,#2979ff,#00d7ef)!important;border-radius:8px!important}
.c1-slider-wrap .dash-slider-thumb{width:19px!important;height:19px!important;top:1px!important;
  border:3px solid #00d7ef!important;background:#f8fcff!important;
  box-shadow:0 0 0 3px rgba(0,215,239,.12),0 0 10px rgba(0,215,239,.30)!important}
.c1-slider-wrap .dash-slider-thumb:focus-visible{outline:2px solid #fff!important;outline-offset:3px!important}
.c1-slider-wrap .dash-slider-mark{top:27px!important;color:#d6e1f0!important;
  font-family:'DM Mono',monospace!important;font-size:11px!important;font-weight:600!important;
  white-space:nowrap!important;text-shadow:0 1px 2px #000!important}
.c1-slider-wrap .dash-slider-mark-outside-selection{color:#b7c6da!important;opacity:1!important}
.c1-slider-wrap .rc-slider{padding:10px 10px 28px!important;min-height:46px}
.c1-slider-wrap .rc-slider-rail{height:7px!important;background:#536985!important;border-radius:9px!important}
.c1-slider-wrap .rc-slider-track{height:7px!important;background:linear-gradient(90deg,#2979ff,#00d7ef)!important;border-radius:9px!important}
.c1-slider-wrap .rc-slider-handle{width:19px!important;height:19px!important;margin-top:-6px!important;
  opacity:1!important;border:3px solid #00d7ef!important;background:#f8fcff!important;
  box-shadow:0 0 0 3px rgba(0,215,239,.12),0 0 10px rgba(0,215,239,.30)!important}
.c1-slider-wrap .rc-slider-handle:focus{box-shadow:0 0 0 4px rgba(0,215,239,.22),0 0 12px rgba(0,215,239,.36)!important}
.c1-slider-wrap .rc-slider-dot{width:10px!important;height:10px!important;bottom:-1px!important;
  border:2px solid #7288a6!important;background:#0d1624!important}
.c1-slider-wrap .rc-slider-dot-active{border-color:#00d7ef!important;background:#eaffff!important}
.c1-slider-wrap .rc-slider-mark-text{color:#d6e1f0!important;font-family:'DM Mono',monospace!important;
  font-size:11px!important;font-weight:600!important;margin-top:5px;white-space:nowrap;text-shadow:0 1px 2px #000}
.c1-slider-wrap .rc-slider-mark-text-active{color:#ffffff!important}
.c1-slider-wrap .rc-slider-mark-text:first-of-type{transform:translateX(-15%)!important}
.c1-slider-wrap .rc-slider-mark-text:last-of-type{transform:translateX(-85%)!important}
.rc-slider-tooltip-inner{background:#f4f7ff!important;color:#07101a!important;font-family:'DM Mono',monospace!important}
@media(max-width:700px){
  .c1-slider-wrap{min-width:100%;width:100%;padding:18px 12px 10px}
  .c1-slider-wrap .rc-slider-mark-text{font-size:10px!important}
  .key-provider-select{width:100%}
}

/* ===== MTDI: i1 radial orbital pillar selector ===== */
.mtdi-landing{width:100%}
.mtdi-orbit{height:680px;max-width:940px;margin:10px auto 14px;position:relative;display:grid;place-items:center;overflow:hidden;isolation:isolate}
.mtdi-orbit::before{content:'';position:absolute;width:520px;height:520px;border:1px solid rgba(145,164,194,.22);border-radius:50%}
.mtdi-orbit::after{content:'';position:absolute;width:390px;height:390px;border:1px dashed rgba(145,164,194,.10);border-radius:50%}
.mtdi-orbit-core{position:absolute;z-index:4;width:112px;height:112px;border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#111927;border:1px solid rgba(167,187,217,.28)}
.mtdi-orbit-core::before,.mtdi-orbit-core::after{display:none}
.mtdi-core-mark{font-family:'DM Mono',monospace;font-size:17px;letter-spacing:.12em;color:#eef3fb}
.mtdi-core-sub{font-family:'DM Mono',monospace;font-size:7px;letter-spacing:.25em;color:var(--c-sub);margin-top:5px}
.mtdi-orbit-stage{--o100:260px;--o92:240px;--o70:184px;--o38:100px;--on100:-260px;--on92:-240px;--on70:-184px;--on38:-100px;position:absolute;width:520px;height:520px;z-index:3}
.mtdi-enter-card{position:absolute;left:50%;top:50%;width:226px;height:172px;margin:-86px 0 0 -113px;padding:0;border:0;background:transparent;color:inherit;font-family:inherit;cursor:pointer;text-align:left;overflow:visible;animation:mtdiPlanetOrbit 56s linear infinite;animation-delay:calc(var(--i) * -14s);animation-play-state:running!important;will-change:transform}
.mtdi-enter-card::before{content:'';position:absolute;left:-7px;top:50%;width:7px;height:7px;margin-top:-3px;border-radius:50%;background:var(--acc,#fff);z-index:2}
.mtdi-enter-card-inner{width:100%;height:100%;box-sizing:border-box;padding:20px 21px;background:#101827;border:1px solid rgba(157,185,225,.16);border-top:2px solid var(--acc,#cbd5e1);border-radius:12px;box-shadow:0 14px 34px rgba(0,0,0,.24);transition:border-color .25s,background .25s,scale .25s;position:relative;overflow:hidden}
.mtdi-enter-card-inner::before,.mtdi-enter-card-inner::after{display:none}
.mtdi-enter-card:hover .mtdi-enter-card-inner,.mtdi-enter-card:focus-visible .mtdi-enter-card-inner{scale:1.035;background:#151f30;border-color:var(--acc,#fff)}
.mtdi-enter-num{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.25em;color:var(--acc,#cbd5e1);margin-bottom:10px}
.mtdi-enter-title{font-family:'DM Mono',monospace;font-size:15px;letter-spacing:.07em;color:#eef3fb;text-transform:uppercase;margin-bottom:8px;white-space:nowrap}
.mtdi-enter-desc{font-family:'Inter',sans-serif;font-size:10.5px;line-height:1.55;color:#8794a8;max-width:100%}
.mtdi-enter-go{font-family:'DM Mono',monospace;font-size:8px;letter-spacing:.17em;color:#c4cedd;margin-top:11px;text-transform:uppercase}
/* A position-only circular path. No rotate() is ever applied to a card, so every
   face remains physically upright while it revolves around the MTDI core. */
@keyframes mtdiPlanetOrbit{
  0%{transform:translate3d(var(--o100),0,0)}
  6.25%{transform:translate3d(var(--o92),var(--o38),0)}
  12.5%{transform:translate3d(var(--o70),var(--o70),0)}
  18.75%{transform:translate3d(var(--o38),var(--o92),0)}
  25%{transform:translate3d(0,var(--o100),0)}
  31.25%{transform:translate3d(var(--on38),var(--o92),0)}
  37.5%{transform:translate3d(var(--on70),var(--o70),0)}
  43.75%{transform:translate3d(var(--on92),var(--o38),0)}
  50%{transform:translate3d(var(--on100),0,0)}
  56.25%{transform:translate3d(var(--on92),var(--on38),0)}
  62.5%{transform:translate3d(var(--on70),var(--on70),0)}
  68.75%{transform:translate3d(var(--on38),var(--on92),0)}
  75%{transform:translate3d(0,var(--on100),0)}
  81.25%{transform:translate3d(var(--o38),var(--on92),0)}
  87.5%{transform:translate3d(var(--o70),var(--on70),0)}
  93.75%{transform:translate3d(var(--o92),var(--on38),0)}
  100%{transform:translate3d(var(--o100),0,0)}
}
.mtdi-pane{animation:mtdiPaneEnter .34s cubic-bezier(.16,1,.3,1) both}
@keyframes mtdiPaneEnter{from{opacity:0;transform:translateY(18px)}to{opacity:1;transform:none}}
.mtdi-launch-ghost{position:fixed!important;z-index:10000!important;margin:0!important;padding:0!important;border:0!important;background:transparent!important;pointer-events:none!important;overflow:hidden!important;animation:none!important}
.mtdi-launch-ghost .mtdi-enter-card-inner{width:100%;height:100%;scale:1!important;border-radius:12px;background:#101827;border-color:rgba(157,185,225,.22);box-shadow:0 24px 60px rgba(0,0,0,.34);transition:none!important}
@media(max-width:760px){
  .mtdi-orbit{height:480px;width:100%;margin-top:6px;border-radius:20px}
  .mtdi-orbit::before{width:270px;height:270px}
  .mtdi-orbit::after{width:204px;height:204px}
  .mtdi-orbit-core{display:flex;width:76px;height:76px}
  .mtdi-orbit-core::before{inset:-10px}.mtdi-orbit-core::after{inset:-20px}
  .mtdi-core-mark{font-size:12px}.mtdi-core-sub{font-size:5px;letter-spacing:.18em;margin-top:3px}
  .mtdi-orbit-stage{--o100:135px;--o92:125px;--o70:95px;--o38:52px;--on100:-135px;--on92:-125px;--on70:-95px;--on38:-52px;width:270px;height:270px}
  .mtdi-enter-card{width:148px;height:126px;margin:-63px 0 0 -74px}
  .mtdi-enter-card::before{left:-6px;width:6px;height:6px;margin-top:-3px}
  .mtdi-enter-card-inner{padding:13px 14px;border-radius:12px}
  .mtdi-enter-num{font-size:7px;margin-bottom:6px}
  .mtdi-enter-title{font-size:10.5px;margin-bottom:6px;white-space:normal}
  .mtdi-enter-desc{font-size:8px;line-height:1.4}
  .mtdi-enter-go{font-size:6px;margin-top:7px}
}
/* Pillar panes appear instantly — no reveal animation (see RENDERING NOTES). */
.mtdi-pane-in{animation:none}

/* ===== MTDI ORBIT V2 — standalone prototype integrated into Dash ===== */
.mtdi-v2-hero{padding:46px 0 20px;max-width:900px}
.mtdi-v2-kicker{font-family:'DM Mono',monospace;font-size:9px;line-height:1.4;letter-spacing:.34em;text-transform:uppercase;color:#8ea0b8}
.mtdi-v2-title{font-family:'DM Mono',monospace;font-size:clamp(34px,5.4vw,66px);line-height:1;letter-spacing:-.045em;color:#e8eef7;margin:14px 0}
.mtdi-v2-copy{font-family:'Inter',sans-serif;font-size:13px;line-height:1.8;color:#8290a5;max-width:720px}
.mtdi-v2-meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}
.mtdi-v2-meta span{padding:6px 9px;border:1px solid rgba(180,198,224,.14);color:#a8b4c5;font-family:'DM Mono',monospace;font-size:8px;line-height:1;letter-spacing:.14em;text-transform:uppercase}
.mtdi-v2-caption{position:absolute;left:0;top:28px;z-index:2;transition:opacity .2s}
.mtdi-v2-caption b{display:block;font-family:'DM Mono',monospace;font-size:9px;line-height:1;letter-spacing:.26em;text-transform:uppercase;color:#dfe7f2}
.mtdi-v2-caption span{display:block;margin-top:7px;color:var(--c-sub);font-family:'Inter',sans-serif;font-size:11px}
.mtdi-orbit-scene{position:relative;left:50%;translate:-50% 0;height:940px;width:min(1400px,100vw);max-width:none;margin:0;overflow:visible;
  transition:height .72s cubic-bezier(.22,1,.36,1)}
.mtdi-orbit-scene.is-constellation-expanded{height:1180px}
.mtdi-orbit-ring-v2{position:absolute;width:var(--orbit-diameter,520px);height:var(--orbit-diameter,520px);left:50%;top:50%;translate:-50% -50%;border:1px solid rgba(180,198,224,.14);border-radius:50%;pointer-events:none;transition:opacity .2s}
.mtdi-orbit-ring-v2::before,.mtdi-orbit-ring-v2::after{content:'';position:absolute;width:5px;height:5px;border:1px solid #75849a;border-radius:50%;background:#070a10}
.mtdi-orbit-ring-v2::before{left:50%;top:-3px}.mtdi-orbit-ring-v2::after{left:50%;bottom:-3px}
.mtdi-orbit-core-v2{position:absolute;left:50%;top:50%;translate:-50% -50%;width:102px;height:102px;z-index:20;border:1px solid rgba(180,198,224,.25);border-radius:50%;background:#090e16;display:grid;place-items:center;text-align:center;transition:opacity .2s}
.mtdi-orbit-core-v2 b{display:block;font-family:'DM Mono',monospace;font-size:15px;line-height:1;letter-spacing:.14em;color:#e8eef7}
.mtdi-orbit-core-v2 span{display:block;margin-top:6px;color:var(--c-sub);font-family:'DM Mono',monospace;font-size:7px;line-height:1;letter-spacing:.22em}
.mtdi-orbit-card{--acc:#7f92ad;position:absolute;left:50%;top:50%;width:300px;height:200px;margin:-100px 0 0 -150px;border:1px solid rgba(180,198,224,.14);border-top:2px solid var(--acc);border-radius:12px;background:#0e141f;color:#e8eef7;cursor:pointer;overflow:hidden;box-shadow:0 16px 34px rgba(0,0,0,.26);transition:border-color .2s,background .2s,opacity .2s;will-change:transform;outline:none}
.mtdi-orbit-card:hover,.mtdi-orbit-card:focus-visible{border-color:var(--acc);background:#121a27}
.mtdi-orbit-card:focus-visible{outline:2px solid #d6e2f2;outline-offset:3px}
.mtdi-card-summary{height:198px;padding:24px 25px 20px;position:relative;opacity:1;transform:translateY(0);transition:opacity .24s ease,transform .44s cubic-bezier(.22,1,.36,1)}
.mtdi-card-top{display:flex;justify-content:space-between;align-items:center;gap:12px}
.mtdi-card-index{color:var(--acc);font-family:'DM Mono',monospace;font-size:9px;line-height:1;letter-spacing:.2em}
.mtdi-card-role{color:var(--c-sub);font-family:'DM Mono',monospace;font-size:7px;line-height:1;letter-spacing:.16em;text-transform:uppercase}
.mtdi-card-title{margin-top:16px;font-family:'DM Mono',monospace;font-size:16px;line-height:1.15;letter-spacing:.07em;text-transform:uppercase;color:#e8eef7}
.mtdi-card-short{margin-top:9px;color:#8290a5;font-family:'Inter',sans-serif;font-size:11.5px;line-height:1.6}
.mtdi-card-enter{position:absolute;right:22px;bottom:17px;color:#aebaca;font-family:'DM Mono',monospace;font-size:8px;line-height:1;letter-spacing:.15em;text-transform:uppercase}
.mtdi-orbit-detail{visibility:hidden;opacity:0;height:0;overflow:hidden;padding:0 clamp(20px,4vw,58px) 54px;transform:translateY(12px);transition:opacity .32s ease,transform .46s cubic-bezier(.22,1,.36,1)}
.mtdi-detail-nav{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid rgba(180,198,224,.14);padding:16px 0;position:sticky;top:0;background:#070a10;z-index:30}
.mtdi-detail-close{border:0;background:transparent;color:#b7c2d1;cursor:pointer;padding:8px 0;font-family:'DM Mono',monospace;font-size:8px;line-height:1;letter-spacing:.18em;text-transform:uppercase}
.mtdi-detail-close:hover{color:#fff}
.mtdi-detail-id{color:var(--c-sub);font-family:'DM Mono',monospace;font-size:8px;line-height:1;letter-spacing:.17em;text-transform:uppercase}
.mtdi-orbit-detail>.mtdi-section-card{border:0!important;border-radius:0!important;background:transparent!important;box-shadow:none!important;margin:0!important;padding:34px 0 0!important;overflow:visible!important}
.mtdi-orbit-detail>.mtdi-section-card::before{display:none!important}
.mtdi-orbit-card.is-detached{position:fixed;margin:0;z-index:10020;cursor:default;transform:none!important;will-change:left,top,width,height,border-radius;transition:left .68s cubic-bezier(.22,1,.36,1),top .68s cubic-bezier(.22,1,.36,1),width .68s cubic-bezier(.22,1,.36,1),height .68s cubic-bezier(.22,1,.36,1),border-radius .68s cubic-bezier(.22,1,.36,1),background .32s ease;opacity:1!important}
.mtdi-orbit-card.is-detached:not(.is-expanded) .mtdi-card-summary{opacity:.38;transform:translateY(-6px)}
.mtdi-orbit-card.is-expanded{overflow:auto;background:#070a10;border-color:rgba(180,198,224,.14);border-top-color:var(--acc)}
.mtdi-orbit-card.is-expanded .mtdi-card-summary{position:absolute;visibility:hidden;opacity:0;pointer-events:none}
.mtdi-orbit-card.is-expanded .mtdi-orbit-detail{visibility:visible;opacity:1;height:auto;min-height:100%;overflow:visible;transform:translateY(0)}
.mtdi-orbit-card.is-closing .mtdi-orbit-detail{opacity:0;transform:translateY(8px);pointer-events:none}
.mtdi-orbit-card.is-closing .mtdi-card-summary{opacity:0}
body.mtdi-detail-open{overflow:hidden!important}
body.mtdi-detail-open #page-content{contain:none!important;z-index:10000!important}
/* `translate` on the orbit scene otherwise becomes the containing block for its
   fixed child, clipping a supposedly fullscreen pillar to the scene rectangle. */
body.mtdi-detail-open .mtdi-landing,
body.mtdi-detail-open #mtdi-pillar-grid,
body.mtdi-detail-open .mtdi-orbit-scene{
  transform:none!important;translate:none!important;contain:none!important}
body.mtdi-detail-open .mtdi-orbit-scene{
  left:0!important;width:100%!important;max-width:none!important;overflow:visible!important}
body.mtdi-detail-open .mtdi-orbit-card.is-detached{
  position:fixed!important;max-width:none!important;max-height:none!important}
body.mtdi-detail-open .mtdi-orbit-card.is-expanded{
  overflow-y:auto!important;overflow-x:hidden!important;overscroll-behavior:contain;
  scrollbar-gutter:stable}
body.mtdi-detail-open .mtdi-orbit-detail>.mtdi-section-card{
  width:min(1280px,100%);max-width:1280px;margin:0 auto!important;padding-top:88px!important}
body.mtdi-detail-open #fixed-credit,body.mtdi-detail-open #typewriter-bar{opacity:0!important;pointer-events:none!important}
body.mtdi-detail-open .mtdi-v2-hero,body.mtdi-detail-open .mtdi-v2-caption,body.mtdi-detail-open .mtdi-orbit-ring-v2,body.mtdi-detail-open .mtdi-orbit-core-v2,body.mtdi-detail-open .mtdi-module-back,body.mtdi-detail-open .mtdi-orbit-card:not(.is-detached){opacity:0!important;pointer-events:none!important}
@media(max-width:760px){
  .mtdi-v2-hero{padding-top:34px}.mtdi-v2-title{font-size:clamp(32px,10vw,46px)}
  .mtdi-orbit-scene{height:560px}.mtdi-orbit-scene.is-constellation-expanded{height:780px}.mtdi-v2-caption{top:12px}
  .mtdi-orbit-card{width:154px;height:130px;margin:-65px 0 0 -77px}
  .mtdi-card-summary{height:128px;padding:13px 14px}.mtdi-card-title{margin-top:9px;font-size:10px}.mtdi-card-short{margin-top:6px;font-size:8px;line-height:1.4}.mtdi-card-enter{right:10px;bottom:9px;font-size:5.5px}.mtdi-card-index,.mtdi-card-role{font-size:6px}
  .mtdi-orbit-core-v2{width:70px;height:70px}.mtdi-orbit-core-v2 b{font-size:11px}.mtdi-orbit-core-v2 span{font-size:5px}
  .mtdi-orbit-detail{padding:0 18px 40px}.mtdi-orbit-detail>.mtdi-section-card{padding-top:24px!important}
}
@media(prefers-reduced-motion:reduce){.mtdi-orbit-card.is-detached{transition-duration:.01ms}.mtdi-orbit-detail{transition-duration:.01ms}}

/* ===== HOME: four instrument modules on the MTDI orbital selector =====
   The path changes position only; card faces never rotate, so labels stay upright. */
.home-module-orbit{position:relative;height:940px;width:100%;max-width:1400px;margin:-18px auto 0;overflow:visible}
.home-module-orbit-stage{--o100:360px;--o92:333px;--o70:255px;--o38:138px;
  --on100:-360px;--on92:-333px;--on70:-255px;--on38:-138px;
  position:absolute;left:50%;top:50%;width:720px;height:720px;translate:-50% -50%;z-index:3}
.home-module-orbit-card.mtdi-orbit-card{display:block;text-decoration:none;
  width:300px;height:200px;margin:-100px 0 0 -150px;
  animation:none!important;will-change:transform}
.home-module-orbit-card .mtdi-card-summary{box-sizing:border-box;
  height:198px;padding:24px 25px 20px;
  background:linear-gradient(145deg,rgba(255,255,255,.018),transparent 55%)}
.home-module-orbit-card .mtdi-card-title{font-size:16px;margin-top:16px}
.home-module-orbit-card .mtdi-card-short{font-size:11.5px;line-height:1.6}
.home-module-orbit-card .mtdi-card-enter{font-size:8px;right:22px;bottom:17px}
.home-module-orbit-card .mtdi-card-index{font-size:10px}.home-module-orbit-card .mtdi-card-role{font-size:8px}
.home-module-orbit-card:hover,.home-module-orbit-card:focus-visible{
  box-shadow:0 18px 42px rgba(0,0,0,.30)}
.home-module-live{margin-top:9px;font-family:'DM Mono',monospace;font-size:11px;line-height:1;
  letter-spacing:.08em;color:var(--acc,#cbd5e1)}
.home-module-live small{margin-left:6px;color:var(--c-sub);font-size:7px;letter-spacing:.14em;text-transform:uppercase}
.home-module-core{z-index:5;isolation:isolate;width:350px;height:350px;overflow:visible;
  background:transparent;border:0;box-shadow:none}
.home-module-core::before,.home-module-core::after{display:none}
#home-module-globe{display:block;width:330px;height:330px;border-radius:50%;touch-action:none;cursor:default}
.home-module-key{display:flex;justify-content:center;align-items:center;flex-wrap:wrap;gap:8px 18px;
  margin:17px auto 0;font-family:'DM Mono',monospace;font-size:8px;line-height:1;
  letter-spacing:.14em;text-transform:uppercase;color:#69788e}
.home-module-key span{display:inline-flex;align-items:center;gap:7px;white-space:nowrap}
.home-module-key i{width:6px;height:6px;border-radius:50%;background:var(--acc);
  font-style:normal}
@media(max-width:760px){
  .home-module-orbit{height:560px;margin-top:-8px;overflow:hidden}
  .home-module-orbit-stage{--o100:148px;--o92:137px;--o70:105px;--o38:57px;
    --on100:-148px;--on92:-137px;--on70:-105px;--on38:-57px;width:296px;height:296px}
  .home-module-orbit-card.mtdi-orbit-card{width:154px;height:130px;margin:-65px 0 0 -77px}
  .home-module-orbit-card .mtdi-card-summary{height:128px;padding:13px 14px}
  .home-module-orbit-card .mtdi-card-title{font-size:10px;margin-top:9px}
  .home-module-orbit-card .mtdi-card-short{font-size:8px;line-height:1.4}
  .home-module-orbit-card .mtdi-card-enter{font-size:5.5px;right:10px;bottom:9px}
  .home-module-orbit-card .mtdi-card-index,.home-module-orbit-card .mtdi-card-role{font-size:6px}
  .home-module-live{font-size:8px;margin-top:6px}.home-module-live small{font-size:5.5px}
  .home-module-key{gap:8px 12px;font-size:6.5px;margin-top:14px}
  .home-module-core{width:140px;height:140px}#home-module-globe{width:128px;height:128px}
}

/* MTDI diagnostic constellation. It lives in the framework core instead of a
   separate boxed section, and is deliberately allowed to layer over captions. */
.mtdi-constellation-core{width:420px;height:420px;padding:0;overflow:visible;cursor:grab;
  z-index:42;background:transparent;border-color:transparent;box-shadow:none;
  transition:width .72s cubic-bezier(.22,1,.36,1),height .72s cubic-bezier(.22,1,.36,1),
             filter .3s ease}
.mtdi-constellation-core:active{cursor:grabbing}
.mtdi-constellation-core:hover{filter:brightness(1.08)}
.mtdi-constellation-core:focus-visible{outline:1px solid rgba(103,203,213,.52);outline-offset:6px;border-radius:50%}
.instrument-constellation-canvas{position:absolute;inset:50% auto auto 50%;translate:-50% -50%;
  width:100%;height:100%;display:block;z-index:1;touch-action:none;overflow:visible}
.i3-hand-vision-status{position:fixed;right:18px;bottom:210px;z-index:12001;max-width:330px;padding:11px 14px;border:1px solid rgba(0,229,255,.3);border-radius:11px;background:rgba(5,9,16,.94);box-shadow:0 16px 45px rgba(0,0,0,.4);color:#d9faff;font:9px 'DM Mono',monospace;letter-spacing:.08em;line-height:1.5;text-transform:uppercase;pointer-events:none}
.i3-hand-vision-status.error{border-color:rgba(255,82,82,.45);color:#ffb6b6}
.i3-hand-vision-status.live{border-color:rgba(0,230,118,.42);color:#8fffc1}
.i3-hand-vision-preview{position:fixed;right:18px;bottom:18px;z-index:12000;width:240px;height:180px;overflow:hidden;border:1px solid rgba(0,229,255,.34);border-radius:14px;background:#050910;box-shadow:0 18px 55px rgba(0,0,0,.48)}
.i3-hand-vision-video,.i3-hand-vision-overlay{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transform:scaleX(-1)}
.i3-hand-vision-overlay{z-index:2;pointer-events:none}
@media(max-width:600px){.i3-hand-vision-preview{width:180px;height:135px;right:10px;bottom:10px}.i3-hand-vision-status{right:10px;bottom:153px;max-width:260px}}
.mtdi-constellation-label{position:absolute;left:50%;top:50%;translate:-50% -50%;z-index:3;
  width:88px;text-align:center;pointer-events:none;text-shadow:0 2px 10px #05080d}
.mtdi-constellation-label b{display:block;font-family:'DM Mono',monospace;font-size:13px;
  line-height:1;letter-spacing:.16em;color:#edf3fa}
.mtdi-constellation-label span{display:block;margin-top:6px;font-family:'DM Mono',monospace;
  font-size:5.5px;line-height:1.3;letter-spacing:.16em;color:var(--c-sub);text-transform:uppercase}
.mtdi-constellation-label em{display:block;margin-top:7px;font-family:'DM Mono',monospace;
  font-size:5px;line-height:1;letter-spacing:.13em;color:var(--c-sub);font-style:normal;text-transform:uppercase}
.mtdi-orbit-scene.is-constellation-expanded .mtdi-constellation-core{width:500px;height:500px;z-index:55}
.mtdi-orbit-scene.is-constellation-expanded .mtdi-constellation-label{width:116px}
.mtdi-orbit-scene.is-constellation-expanded .mtdi-constellation-label b{font-size:17px}
.mtdi-orbit-scene.is-constellation-expanded .mtdi-constellation-label span{font-size:6.5px}
.mtdi-orbit-scene.is-constellation-expanded .mtdi-constellation-label em{font-size:5.5px}
@media(max-width:760px){
  .mtdi-constellation-core{width:170px;height:170px}
  .mtdi-orbit-scene.is-constellation-expanded .mtdi-constellation-core{width:min(340px,72vw);height:min(340px,72vw)}
  .mtdi-constellation-label{width:64px}.mtdi-constellation-label b{font-size:9px}
  .mtdi-constellation-label span{font-size:4px}.mtdi-constellation-label em{font-size:3.8px;margin-top:5px}
  .mtdi-orbit-scene.is-constellation-expanded .mtdi-constellation-label{width:78px}
  .mtdi-orbit-scene.is-constellation-expanded .mtdi-constellation-label b{font-size:11px}
}

/* ===== BUTTON FEEL ===== */
.open-btn,.back-btn,.tab-btn,.set-seg button,.nav-glass-btn,.ch3-btn{transition:all .2s cubic-bezier(0.16,1,0.3,1)}
.open-btn:active,.back-btn:active,.set-seg button:active,.nav-glass-btn:active{transform:scale(0.96)}
.tab-btn:active{transform:translateY(1px)}
button:focus-visible{outline:2px solid var(--c-cyan);outline-offset:2px;border-radius:6px}
"""

# ── colour variables, CH3 + scan tables, reduced motion ──
GLOBAL_CSS += r"""
/* ===== THEME COLOUR VARIABLES (auto-swap in light mode) ===== */
:root{--c-cyan:#00e5ff;--c-blue:#2979ff;--c-green:#00e676;--c-amber:#ffab40;
      --c-red:#ff5252;--c-yellow:#ffd166;--c-purple:#b388ff;--c-white:#e8eeff;--c-sub:#7d8ea8}
.c-cyan{color:var(--c-cyan)!important}.c-blue{color:var(--c-blue)!important}
.c-green{color:var(--c-green)!important}.c-amber{color:var(--c-amber)!important}
.c-red{color:var(--c-red)!important}.c-yellow{color:var(--c-yellow)!important}
.c-purple{color:var(--c-purple)!important}.c-white{color:var(--c-white)!important}
.c-sub{color:var(--c-sub)!important}

/* transform-only sweep => stays on the compositor, no per-frame layout/paint */
@keyframes scanSweep{0%{transform:translateX(-120%)}100%{transform:translateX(640%)}}
.online-bar{position:relative;overflow:hidden}
.online-bar>*{position:relative;z-index:1}
.online-bar::after{content:'';position:absolute;top:0;bottom:0;width:16%;left:0;pointer-events:none;
  background:linear-gradient(90deg,transparent,rgba(0,229,255,0.06),transparent);
  transform:translateX(-120%);animation:scanSweep 6s linear infinite}

/* ===== CH3 CONTROL BAR ===== */
.ch3-ctl-bar{display:flex;flex-wrap:wrap;gap:18px;align-items:flex-end;
  background:rgba(16,23,38,0.74);border:1px solid rgba(255,255,255,0.07);
  border-radius:16px;padding:16px 18px;margin-bottom:18px}
.ch3-ctl-group{display:flex;flex-direction:column;gap:8px}
.ch3-ctl-label{font-family:'DM Mono','Courier New',monospace;font-size:8px;letter-spacing:0.26em;
  color:var(--c-sub);text-transform:uppercase}
.ch3-ctl-row{display:flex;gap:4px;flex-wrap:wrap;align-items:center;background:rgba(255,255,255,0.04);
  border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:3px}
.ch3-ctl-row input{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:7px;
  padding:7px 10px;width:110px;color:#e8eeff;font-family:'DM Mono',monospace;font-size:10px;outline:none;caret-color:#00e5ff}
.ch3-ctl-row input:focus{border-color:rgba(0,229,255,0.4)}
.ch3-btn{font-family:'DM Mono','Courier New',monospace;font-size:9.5px;letter-spacing:0.12em;
  text-transform:uppercase;color:var(--c-sub);background:transparent;border:1px solid transparent;
  border-radius:7px;padding:8px 13px;cursor:pointer;white-space:nowrap}
.ch3-btn:hover{color:#e8eeff;background:rgba(255,255,255,0.05)}
.ch3-btn:active{transform:scale(0.96)}
.ch3-btn.ch3-on{color:#00e5ff;background:rgba(0,229,255,0.10);border-color:rgba(0,229,255,0.32);
  text-shadow:0 0 10px rgba(0,229,255,0.35)}
#ch3-custom-status{margin:0 0 0 8px}

/* ===== PEAK TRACKER ===== */
.ch3-peak-table{background:rgba(16,23,38,0.74);border:1px solid rgba(255,255,255,0.07);
  border-radius:16px;overflow:hidden}
.ch3-peak-head,.ch3-peak-row{display:grid;
  grid-template-columns:42px minmax(96px,1.1fr) minmax(84px,0.9fr) minmax(72px,0.7fr) minmax(120px,1.4fr);
  gap:10px;align-items:center;padding:11px 18px;
  font-family:'DM Mono','Courier New',monospace;font-size:11px}
.ch3-peak-head{font-size:8px;letter-spacing:0.22em;color:var(--c-sub);text-transform:uppercase;
  border-bottom:1px solid rgba(255,255,255,0.07);background:rgba(255,255,255,0.02)}
.ch3-peak-row{border-bottom:1px solid rgba(255,255,255,0.04);transition:background 0.2s;min-height:41px}
.ch3-peak-row:last-child{border-bottom:none}
.ch3-peak-row:hover{background:rgba(0,229,255,0.05)}
.ch3-peak-idx{color:var(--c-sub);font-size:9px;letter-spacing:0.1em}
.ch3-peak-freq{font-size:12.5px;letter-spacing:-0.01em}
.ch3-peak-lvl{color:#e8eeff}
.ch3-peak-delta{color:#00e676;font-size:10px}
.ch3-peak-band{color:var(--c-sub);font-size:10px;letter-spacing:0.04em;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.ch3-peak-empty{font-family:'DM Mono','Courier New',monospace;font-size:11px;color:var(--c-sub);
  padding:22px 18px;text-align:center;letter-spacing:0.04em}
@media(max-width:760px){
  .ch3-peak-head,.ch3-peak-row{grid-template-columns:32px 1fr 84px;row-gap:4px}
  .ch3-peak-delta,.ch3-peak-band{display:none}
}

/* ===== CH3 DEVICE STRIP ===== */
.ch3-dev-strip{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;
  background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.07);
  border-radius:14px;overflow:hidden;margin-bottom:18px}
.ch3-dev-cell{background:rgba(7,9,15,0.9);padding:13px 15px;min-height:56px}
.ch3-dev-key{font-family:'DM Mono','Courier New',monospace;font-size:7.5px;letter-spacing:0.24em;
  color:var(--c-sub);text-transform:uppercase;margin-bottom:5px}
.ch3-dev-val{font-family:'DM Mono','Courier New',monospace;font-size:12px;color:#e8eeff;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}

/* ===== SCAN TABLES (WiFi / Bluetooth / LAN) ===== */
.scan-table{background:rgba(16,23,38,0.74);border:1px solid rgba(255,255,255,0.07);
  border-radius:16px;overflow:hidden;margin-bottom:8px}
.scan-head,.scan-row{display:grid;gap:10px;align-items:center;padding:11px 18px;
  font-family:'DM Mono','Courier New',monospace;font-size:11px}
.scan-head{font-size:8px;letter-spacing:0.22em;color:var(--c-sub);text-transform:uppercase;
  border-bottom:1px solid rgba(255,255,255,0.07);background:rgba(255,255,255,0.02)}
.scan-row{border-bottom:1px solid rgba(255,255,255,0.04);transition:background 0.2s;min-height:42px}
.scan-row:last-child{border-bottom:none}
.scan-row:hover{background:rgba(0,229,255,0.05)}
.scan-row.scan-self{background:rgba(0,229,255,0.06);border-left:2px solid rgba(0,229,255,0.55)}
.wifi-cols{grid-template-columns:minmax(130px,1.7fr) minmax(120px,1.2fr) 62px 78px
  minmax(74px,0.8fr) minmax(96px,1fr)}
.bt-cols{grid-template-columns:minmax(140px,1.8fr) minmax(120px,1.3fr) 78px
  minmax(84px,0.9fr) 64px}
.lan-cols{grid-template-columns:minmax(110px,1.1fr) minmax(130px,1.3fr) 78px minmax(90px,0.9fr)}
.scan-name{color:#e8eeff;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.scan-mac{color:var(--c-sub);font-size:10px;letter-spacing:0.02em}
.scan-dim{color:var(--c-sub);font-size:10px}
.scan-empty{font-family:'DM Mono','Courier New',monospace;font-size:11px;color:var(--c-sub);
  padding:22px 18px;text-align:center;letter-spacing:0.04em;line-height:1.7}
.sec-tag{font-size:9px;padding:2px 7px;border-radius:4px;display:inline-block;
  background:rgba(41,121,255,0.12);color:#2979ff;border:1px solid rgba(41,121,255,0.25)}
.sec-tag.sec-open{background:rgba(255,82,82,0.10);color:#ff5252;border-color:rgba(255,82,82,0.25)}
.sig-wrap{display:flex;align-items:center;gap:7px}
.sig-track{flex:1;min-width:34px;height:4px;background:rgba(255,255,255,0.07);border-radius:2px;overflow:hidden}
.sig-fill{height:4px;border-radius:2px}
@media(max-width:820px){
  .wifi-cols{grid-template-columns:1fr 70px 90px}
  .bt-cols{grid-template-columns:1fr 78px 64px}
  .lan-cols{grid-template-columns:1fr 78px}
  .scan-hide-sm{display:none}
}

/* ===== dBm REFERENCE STRIP ===== */
.dbm-scale{display:grid;grid-template-columns:repeat(auto-fit,minmax(128px,1fr));gap:1px;
  background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.07);
  border-radius:14px;overflow:hidden;margin-top:12px}
.dbm-cell{background:rgba(7,9,15,0.9);padding:12px 14px}
.dbm-val{font-family:'DM Mono','Courier New',monospace;font-size:13px;margin-bottom:4px}
.dbm-txt{font-family:'DM Mono','Courier New',monospace;font-size:9px;color:var(--c-sub);line-height:1.5}

/* ===== HEADER PILL FIT =====
   The centre nav is absolutely positioned, so it does not reserve space and the
   right-hand pill strip would slide under it as the viewport narrows. Drop the least
   diagnostic pill first, keep MTDI health to the end. */
.header-pills{gap:6px}
.status-pill{padding:4px 10px;gap:5px;white-space:nowrap}
@media(max-width:1440px){.status-pill.pill-c2{display:none}}   /* 4 -> 3 pills */
@media(max-width:1220px){.status-pill.pill-c1{display:none}}  /* 3 -> 2 pills */
@media(max-width:990px){.status-pill.pill-ch3{display:none}}    /* 2 -> 1 pill  */
@media(max-width:780px){.header-pills{display:none}}           /* nav only     */
/* The centre nav is absolutely positioned and therefore reserves no width, so below
   ~1000px it slides underneath the brand badge and the two overlap. The brand is
   redundant next to a nav that already has HOME, so it is dropped first. */
@media(max-width:1000px){.header-brand{display:none}}
/* ===== LIGHT MODE — full tailoring pass ===== */

/* ===== ACCESSIBILITY: honour the OS "reduce motion" setting =====
   Everything decorative stops. Functional colour and layout are untouched. */
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}
  #page-shader-canvas,#nvtra-mascot-canvas,#nav-progress{display:none!important}
  .module-card:hover,.sys-card:hover,.metric-card:hover,.pillar:hover,
  .mtdi-enter-card:hover,.power-layer-card:hover{transform:none!important}
}
/* The MTDI orbital selector is an instrument-state visual, not a page transition.
   Keep its slow, GPU-composited rotation continuous even when decorative motion is off. */
html .mtdi-enter-card{animation:mtdiPlanetOrbit 56s linear infinite!important;animation-delay:calc(var(--i) * -14s)!important;animation-play-state:running!important}
"""

# ── STARTUP INTRO ─────────────────────────────────────────────────────────────
# Adapted from startup_intro_only.html: a self-scrolling fixed startup takeover,
# WebGL shader, title words, project-overview glass card, item blocks.
#
# It lives in the permanent application shell (app.layout), outside #page-content, so:
#   · a full document load / refresh creates it exactly once and it plays,
#   · the routing callback only ever writes page-content.children, so switching
#     modules can never rebuild, restart or replay it,
#   · no Store, localStorage or sessionStorage is involved in showing or hiding it.
#
# Only two things were changed from the supplied file, both required to coexist:
#   1. Selectors are scoped under #startup-intro so the intro's own :root variables
#      and .intro-* rules cannot bleed into the dashboard's styling.
#   2. The scroll distance is inside a fixed overlay. Once consumed, the overlay is
#      removed, so it can never become reachable again by scrolling the document.
GLOBAL_CSS += r"""
#startup-intro{
  --i-bg:#07090f;--i-card:rgba(13,19,32,0.72);--i-white:#e8eeff;--i-subtext:#71829f;
  --i-cyan:#00e5ff;--i-blue:#2979ff;
  position:fixed;inset:0;z-index:100000;width:100%;height:100vh;height:100dvh;
  overflow-x:hidden;overflow-y:auto;overscroll-behavior:contain;
  scrollbar-width:none;background:transparent;opacity:1;
  transition:opacity .22s cubic-bezier(.22,1,.36,1);transform:translateZ(0)}
#startup-intro::-webkit-scrollbar{display:none}
#startup-intro::after{content:"";display:block;height:180vh;pointer-events:none}
body.intro-active,body.mode-gate-locked{height:100vh;height:100dvh;overflow:hidden!important}
body.intro-active #app-shell{
  transform:translate3d(0,var(--intro-home-y,100vh),0);
  will-change:transform;backface-visibility:hidden}
body.intro-active #fixed-credit,body.intro-active #typewriter-bar,
body.intro-active #nvtra-alert-stack,body.intro-active #simulation-watermark,
body.intro-active #nav-progress{opacity:0!important;pointer-events:none!important}

/* The stage remains sticky while the overlay's own 180vh spacer supplies the scrub. */
#startup-intro .intro-stage{
  position:sticky;top:0;width:100%;height:100vh;height:100dvh;display:grid;place-items:center;
  overflow:hidden;
  background:transparent;
  opacity:1;visibility:visible;contain:layout paint;
  transform:translateZ(0);backface-visibility:hidden}

/* The original intro shader is restored at full strength, but its opacity is scrubbed
   to zero before Home begins entering. Home therefore keeps only the shared shader. */
#intro-shader{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;
  display:block;opacity:.38;image-rendering:auto;transform:translateZ(0);backface-visibility:hidden;
  will-change:opacity;mix-blend-mode:screen}

#startup-intro .intro-eyebrow{position:absolute;top:calc(50% - clamp(170px,15vw,235px));left:24px;right:24px;
  z-index:2;color:var(--i-cyan);font:11px/1.5 'DM Mono',monospace;letter-spacing:0.36em;
  text-align:center;text-transform:uppercase}
#startup-intro .intro-eyebrow::before,#startup-intro .intro-eyebrow::after{
  content:"";display:inline-block;width:40px;height:1px;margin:0 16px;vertical-align:middle;
  background:linear-gradient(90deg,transparent,var(--i-cyan));opacity:0.55}
#startup-intro .intro-eyebrow::after{background:linear-gradient(90deg,var(--i-cyan),transparent)}

#startup-intro .intro-title{position:absolute;left:0;right:0;z-index:3;
  font-size:clamp(58px,11vw,172px);font-weight:500;letter-spacing:-0.055em;line-height:0.88;
  text-align:center;user-select:none;transform:translateZ(0);backface-visibility:hidden;
  will-change:transform,opacity}
#startup-intro .intro-title-top{top:calc(50% - clamp(100px,9vw,160px));color:var(--i-white);
  text-shadow:0 0 12px rgba(255,255,255,0.75),0 0 42px rgba(0,229,255,0.65),0 0 110px rgba(0,229,255,0.25)}
#startup-intro .intro-title-bottom{top:calc(50% + 10px);color:transparent;
  background:linear-gradient(135deg,var(--i-white),var(--i-cyan) 58%,var(--i-blue));
  background-clip:text;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
  filter:drop-shadow(0 0 20px rgba(0,229,255,0.65))}

#startup-intro .intro-card{position:relative;z-index:2;width:min(88vw,500px);min-height:520px;
  padding:34px 30px;display:flex;flex-direction:column;
  border:1px solid rgba(0,229,255,0.25);border-radius:28px;
  background:linear-gradient(160deg,rgba(17,26,43,0.70),var(--i-card));
  box-shadow:0 24px 96px rgba(41,121,255,0.25),0 0 72px rgba(0,229,255,0.10);
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
  transform:scale(0.64);opacity:1;will-change:transform,opacity,filter;
  backface-visibility:hidden;transform-style:preserve-3d}

#startup-intro .intro-card-kicker,#startup-intro .hardware-label{
  color:var(--i-cyan);font:9px/1.5 'DM Mono',monospace;letter-spacing:0.28em;text-transform:uppercase}
#startup-intro .intro-card-title{margin-top:8px;font-size:32px;font-weight:600;
  background:linear-gradient(135deg,var(--i-white),var(--i-cyan));
  background-clip:text;-webkit-background-clip:text;-webkit-text-fill-color:transparent}
#startup-intro .intro-description{margin-top:22px;color:#aab6cc;font-size:13px;line-height:1.75}
#startup-intro .hardware-label{margin:25px 0 10px;color:var(--i-subtext)}
#startup-intro .hardware-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
#startup-intro .hardware-item{padding:10px;border:1px solid rgba(255,255,255,0.08);
  border-radius:8px;background:rgba(41,121,255,0.06)}
#startup-intro .hardware-name{color:var(--i-cyan);font:10px/1.4 'DM Mono',monospace;letter-spacing:0.08em}
#startup-intro .hardware-role{margin-top:4px;color:var(--i-subtext);font:9px/1.4 'DM Mono',monospace}
#startup-intro .intro-credit{margin-top:auto;padding-top:18px;
  border-top:1px solid rgba(255,255,255,0.07);color:var(--i-subtext);
  font:10px/1.5 'DM Mono',monospace;letter-spacing:0.12em}
#startup-intro .intro-credit strong{color:var(--i-white);font-weight:400}

@media (max-width:650px){
  #startup-intro .intro-eyebrow::before,#startup-intro .intro-eyebrow::after{display:none}
  #startup-intro .intro-card{min-height:470px;padding:28px 22px}
  #startup-intro .hardware-grid{grid-template-columns:repeat(2,1fr)}
}

/* Reduced motion: the section is hidden by CSS and removed by JS, and the dashboard
   is shown immediately. Same for the in-app Animations=Off switch. */
@media (prefers-reduced-motion: reduce){#startup-intro{display:none!important}}
html.no-anim #startup-intro{display:none!important}
"""

# ════════════════════════════════════════════════════════
#  UI CORRECTION LAYER  (v2.0.6)
#
#  Appended last so it wins on equal specificity. Everything here is presentation
#  only — no callback, worker, archive or figure-data change.
#
#  It exists as one block rather than edits scattered through the 1,200 lines above
#  so the whole UI change is a single reviewable diff and can be deleted in one cut.
#
#  Four problems it fixes:
#   1. COLLISIONS. The header centred its nav with position:absolute, which reserves
#      no width, so the nav slid underneath the brand and the status pills. The old
#      workaround hid the brand and then the pills one at a time as the viewport
#      narrowed. Replaced with a real three-column grid: the columns cannot overlap
#      at any width, so hiding a pill is now a density choice, not a repair.
#   2. CONTRAST. Micro-labels were 7-9px in a colour measuring 3.5:1. Type floor is
#      now 10px and the token is 5.5:1 (see SUBTEXT). Light mode never re-themed
#      Plotly, which renders its axis text as SVG with a fill baked in from the dark
#      palette; that is corrected here by fill overrides on tick/title/legend text.
#   3. OVERLAY BLEED. Decorative fixed elements sat directly on top of readable
#      content with no reserved space and no viewport clamping.
#   4. SEAM. The intro, the orbits, the chat and the section cards each shipped
#      their own radius, border, surface and easing, so they read as separate demos
#      embedded in a dashboard. They now share one token set.
# ════════════════════════════════════════════════════════
GLOBAL_CSS += r"""
/* ═══ SHARED TOKENS ═══════════════════════════════════════════════════════════
   One scale for every surface in the app, including the features that previously
   hardcoded their own. */
:root{
  --hdr-h:54px;
  --r-sm:10px; --r-md:14px; --r-lg:20px; --r-pill:999px;
  --ease:cubic-bezier(.16,1,.3,1);
  --dur-fast:.18s; --dur:.26s;
  --surface-1:rgba(16,23,38,.74);
  --surface-2:rgba(21,30,49,.80);
  --surface-3:rgba(12,18,30,.92);
  --line:rgba(255,255,255,.09);
  --line-strong:rgba(255,255,255,.15);
  --shadow-1:0 8px 32px rgba(0,0,0,.30);
  --shadow-2:0 18px 56px rgba(0,0,0,.38);
  --focus:#00e5ff;
  --gutter:clamp(16px,3vw,32px);
}

/* ═══ 1. HEADER — real grid, no absolute centring ════════════════════════════ */
.site-header{
  display:grid!important;
  grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);
  align-items:center;
  column-gap:14px;
  padding:0 var(--gutter)!important;
  justify-content:initial!important}
.site-header > a{grid-column:1;justify-self:start;min-width:0}
.nav-glass-wrap{
  position:static!important;
  transform:none!important;
  grid-column:2;
  justify-self:center;
  min-width:0;
  display:flex}
/* justify-self:end with content wider than the track lets the box extend LEFT out
   of its own column and straight under the nav, and overflow:hidden then clips
   the box rather than the column. Stretching to the track width instead means an
   unexpectedly long reading is clipped at the edge, never overlapped. */
.header-pills{
  grid-column:3;justify-self:stretch;width:100%;
  display:flex;justify-content:flex-end;
  min-width:0;flex-wrap:nowrap;overflow:hidden}
/* Defensive: any child other than the three real ones (a stray render from a
   non-visual component) is parked rather than auto-placed into a new row. */
.site-header > :not(a):not(.nav-glass-wrap):not(.header-pills){
  grid-row:1;grid-column:1;width:0;height:0;overflow:hidden;pointer-events:none}
.header-brand{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.nav-glass{min-width:0;flex-wrap:nowrap}
.nav-glass-btn{white-space:nowrap}

/* Progressive density. The grid guarantees no overlap; these only trade detail
   for breathing room, and they now trigger far later than the old collision
   workarounds did.
   The min-width rules come first and are load-bearing: the original stylesheet
   hid the Ch2 pill below 1440px, the ch1probe pill below 1220px and the
   brand below 1000px. Adding a *later* max-width rule cannot undo an earlier one,
   so without these the old thresholds silently kept winning. */
   Thresholds are derived, not guessed. With equal 1fr side tracks the header needs
       viewport >= 2 x (widest side column) + nav + 2 x gutter + 2 x gap
   Measured in the browser: nav 510, gutter 32, gap 14, brand 165, and pills
   118/117/104/95 with 6px gaps. That gives 1506 for four pills, 1260 for three,
   1012 for two and 792 for one; the values below add headroom for longer readings
   such as "C1 100.00 uT". */
@media(min-width:1561px){.status-pill.pill-c2{display:inline-flex!important}}
@media(min-width:1301px){.status-pill.pill-c1{display:inline-flex!important}}
@media(min-width:1051px){.status-pill.pill-ch3{display:inline-flex!important}}
@media(min-width:941px){
  .header-brand{display:inline-flex!important}
  .site-header > a{display:block!important}}
@media(min-width:831px){.header-pills{display:flex!important}}
@media(max-width:1560px){.status-pill.pill-c2{display:none}}
@media(max-width:1300px){.status-pill.pill-c1{display:none}}
@media(max-width:1050px){
  .status-pill.pill-ch3{display:none}
  .nav-glass-btn{padding:6px 12px;letter-spacing:.12em}}
@media(max-width:940px){
  .header-brand{display:none!important}
  .site-header > a{display:none!important}
  .nav-glass-sep{display:none}}
@media(max-width:830px){.header-pills{display:none!important}}
@media(max-width:720px){
  .site-header{grid-template-columns:minmax(0,1fr)}
  .nav-glass-wrap{grid-column:1;justify-self:center;max-width:100%}
  .nav-glass{overflow-x:auto;scrollbar-width:none}
  .nav-glass::-webkit-scrollbar{display:none}}

/* ═══ 2. TYPE FLOOR AND CONTRAST ═════════════════════════════════════════════
   Nothing the operator has to read is below 10px any more. The values below
   replace 7px-9px settings; letter-spacing is trimmed to compensate so the
   labels occupy roughly the same width they did before. */
.mtdi-card-role,.mtdi-card-index,.mtdi-card-enter,
.nvtra-stat-key,.nvtra-stat-desc,.nvtra-house-role,
.session-meta,.session-sidebar-label,.new-session-btn,
.model-picker-cap,.model-choice-id,.model-config-link,
.nvtra-key-cap,.nvtra-composer-meta,.nvtra-composer-status,
.nvtra-msg-sender,.nvtra-identity-kicker,
.arch-stat-key,.disc-stat-key,.ch3-dev-key,.dbm-txt,
.scan-head,.ch3-peak-head,.sort-foot,.layer-pill,
.mtdi-section-kicker,.mtdi-field-num,.power-layer-title,
.hero-spec .k,.sys-name,.chip-popup-field,
.chart-hd,.mtdi-v2-kicker,.mtdi-v2-meta span,.mtdi-detail-id,.mtdi-detail-close,
.mtdi-constellation-label span,.mtdi-constellation-label em,
.home-module-key,.home-module-live small,
.inspo-card-kicker,.inspo-card-by,.key-badge,.key-prov,.key-model,
.key-name-save,.ch3-ctl-label,.mtdi-card-short,.pillar-chip,
.section-label,.metric-label,.summary-tag{
  font-size:10px!important;letter-spacing:.14em}
.mtdi-card-short,.nvtra-house-desc,.nvtra-stat-desc,.inspo-card-by,
.sys-sub,.scan-dim,.scan-mac,.key-mask,.dbm-txt,.mtdi-field-desc,
.power-layer-copy,.validation-subcopy,.sensor-conf-note,.pillar-chip{
  font-size:11.5px!important;letter-spacing:.01em;line-height:1.6}
.mtdi-card-title{font-size:15px!important}
.hero-sub{font-size:15px}
.session-name{font-size:12px}

/* Muted text everywhere resolves through the token, so it lifts with SUBTEXT. */
.sys-sub,.scan-dim,.scan-mac,.key-mask,.key-status,.nvtra-key-cap,
.metric-label,.section-label,.page-subtitle,.arch-stat-key,
.mtdi-card-short,.mtdi-card-role,.validation-subcopy,.dbm-txt,
.chip-popup-field,.disc-stat-key,.ch3-dev-key,.sensor-conf-note,
.nvtra-stat-key,.nvtra-house-role,.session-meta,.hero-spec .k,
.ch3-peak-band,.ch3-peak-idx,.scan-empty,.ch3-peak-empty{color:var(--c-sub)!important}
.nvtra-stat-desc{color:var(--c-sub)!important;opacity:.85;font-style:normal}
.mtdi-v2-copy,.mtdi-section-copy,.hero-sub,.nvtra-identity-text,
.summary-text,.aether-verse,.inspo-card-quote,.sort-body,
.mtdi-field-desc,.power-layer-copy,.nvtra-house-desc,.i3-principle p{
  color:#c3cede}
/* ═══ 2b. BACKGROUND LEGIBILITY ══════════════════════════════════════════════
   The shader ran at 0.28 with no scrim, so paragraph text sat directly on moving
   high-contrast line art — the single worst readability problem in the UI, and
   the reason the hero copy looked like it was floating over a screensaver rather
   than printed on the instrument. Dropping the opacity alone left the lines still
   crossing letterforms, so a fixed scrim sits between the shader and the content:
   the motion stays visible at the edges and is damped where text lives. */
#page-shader-canvas{opacity:.36!important}
body::after{
  content:'';position:fixed;inset:0;z-index:0;pointer-events:none;
  background:
    radial-gradient(ellipse 105% 62% at 50% 0%,rgba(0,229,255,.012),rgba(7,13,25,.24) 62%,rgba(5,9,19,.43) 100%)}
body{
  background:
    radial-gradient(circle at 16% 4%,rgba(41,121,255,.16) 0%,rgba(18,48,82,.10) 24%,transparent 46%),
    radial-gradient(circle at 86% 24%,rgba(0,229,255,.09) 0%,rgba(16,43,70,.06) 22%,transparent 40%),
    linear-gradient(155deg,#091728 0%,#07111f 48%,#050b16 100%)}
/* The root carries the same ground as the body: while a scrub hero pins the body with
   position:fixed the body background stops painting the viewport, and without this the
   browser's default grey shows behind the hero. */
html{background:linear-gradient(155deg,#091728 0%,#07111f 48%,#050b16 100%) fixed}
html.no-anim body::after{display:none}

/* ═══ 3. FIXED OVERLAYS ══════════════════════════════════════════════════════ */
/* Reserve the strip the corner captions occupy so they never sit on a table row
   or the last chart of a page. */
#page-content{padding-bottom:56px}
#fixed-credit,#typewriter-bar{
  bottom:16px;z-index:60;
  padding:5px 10px;border-radius:var(--r-sm);
  background:var(--surface-3);border:1px solid var(--line);
  max-width:min(42vw,420px);overflow:hidden;text-overflow:ellipsis}
#fixed-credit{right:var(--gutter)}
#typewriter-bar{left:var(--gutter)}
@media(max-width:900px),(max-height:620px){
  #fixed-credit,#typewriter-bar{display:none}
  #page-content{padding-bottom:24px}}

/* The alert stack sat at a fixed 66px and could cover the first card of a page. */
#nvtra-alert-stack{top:calc(var(--hdr-h) + 12px);right:var(--gutter);max-width:min(90vw,420px)}
.nvtra-alert-item{white-space:normal;word-break:break-word}

/* Popup was placed with hand-computed coordinates that ran off the bottom-right.
   JS now clamps the origin; this caps the box itself. */
.chip-popup{max-width:min(300px,calc(100vw - 24px));max-height:calc(100vh - 120px)}
.chip-popup-inner{max-height:calc(100vh - 120px);overflow:auto}

/* Dead rules for markup that no longer renders. `.page-enter` is intentionally
   excluded: older routed markup may still carry it, and hiding it creates a dark
   frame while Dash swaps the Home page. */
.nvtra-history-drawer,.nvtra-sug-row{display:none!important}

/* ═══ 4. ONE SURFACE LANGUAGE ════════════════════════════════════════════════
   These panels previously each declared their own background, border and radius,
   which is what made the orbits, the intro and the chat read as pasted-in demos. */
.module-card,.mtdi-section-card,.arch-shell,.validation-live-block,
.validation-hero-card,.nvtra-intel-card,.set-card,.pillar,
.mtdi-field-card,.power-layer-card,.summary-panel,.chart-card,
.sys-card,.metric-card,.sensor-conf-card,.panel,.online-bar,
.ch3-ctl-bar,.ch3-peak-table,.scan-table,.ch3-dev-strip,.dbm-scale,
.nvtra-chat-workspace,.mtdi-orbit-card,#startup-intro .intro-card{
  border-color:var(--line)}
.module-card,.mtdi-section-card,.nvtra-intel-card,.nvtra-chat-workspace,
#startup-intro .intro-card{border-radius:var(--r-lg)}
.chart-card,.sys-card,.metric-card,.sensor-conf-card,.arch-shell,
.validation-live-block,.validation-hero-card,.set-card,.pillar,
.mtdi-field-card,.power-layer-card,.summary-panel,.panel,
.ch3-ctl-bar,.ch3-peak-table,.scan-table,.ch3-dev-strip,.dbm-scale,
.mtdi-orbit-card{border-radius:var(--r-md)}

/* Orbit cards hardcoded #0e141f / #101827, so they alone stayed dark in light
   mode and sat a shade off every neighbouring card in dark mode. */
.mtdi-orbit-card,.home-module-orbit-card{
  background:var(--surface-2)!important;
  box-shadow:var(--shadow-1)}
.mtdi-orbit-card:hover,.mtdi-orbit-card:focus-visible,
.home-module-orbit-card:hover,.home-module-orbit-card:focus-visible{
  background:var(--surface-2)!important;
  border-color:var(--acc,var(--c-cyan))!important;
  box-shadow:var(--shadow-2)}
.mtdi-orbit-card.is-expanded{background:rgba(7,13,24,.84)!important}
.mtdi-detail-nav{background:rgba(7,13,24,.93)!important;border-bottom-color:var(--line)}
.home-module-orbit>.mtdi-orbit-ring-v2,
#mtdi-orbit-stage-v2>.mtdi-orbit-ring-v2{display:block!important}
.home-module-core,.mtdi-constellation-core{
  border-color:transparent!important;background:transparent!important;box-shadow:none!important}
.home-module-core::before,.home-module-core::after,
.mtdi-constellation-core::before,.mtdi-constellation-core::after{display:none!important}
.mtdi-orbit-core-v2,.mtdi-orbit-ring-v2{border-color:var(--line-strong)}
.mtdi-orbit-core-v2{background:var(--surface-3)}

/* The chat workspace carried a stray purple radial that matched nothing else. */
.nvtra-chat-workspace{
  background:var(--surface-2)!important;
  border-color:var(--line)!important;
  box-shadow:var(--shadow-1)!important}
.nvtra-session-sidebar{background:transparent;border-right-color:var(--line)}
.nvtra-live-chat{background:var(--surface-3);border-color:var(--line)}
.nvtra-input-bar{background:var(--surface-1);border-color:var(--line-strong)}

/* The intro card used a 28px radius and its own private palette variables. */
#startup-intro .intro-card{
  border-color:var(--line-strong);
  box-shadow:var(--shadow-2)}
#startup-intro .hardware-item{border-radius:var(--r-sm);border-color:var(--line)}

/* Motion: one curve and two durations instead of a dozen ad-hoc values. */
.module-card,.sys-card,.metric-card,.sensor-conf-card,.pillar,
.chart-card,.mtdi-field-card,.power-layer-card,.mtdi-orbit-card,
.open-btn,.back-btn,.tab-btn,.ch3-btn,.key-btn,.nav-glass-btn,
.set-seg button,.chat-session,.model-choice,.nvtra-key-pill{
  transition-timing-function:var(--ease);
  transition-duration:var(--dur)}

/* ═══ 4b. ORBIT FALLBACK — a grid when no overlap-free orbit exists ══════════
   orbitFit() in the browser layer adds .is-linear when the scene is too small to
   hold a ring of cards clear of the core. Rather than letting the cards pile onto
   the globe (the old behaviour), the whole thing becomes an ordinary responsive
   grid. Nothing is hidden and every card stays clickable. */
.home-module-orbit.is-linear,.mtdi-orbit-scene.is-linear{height:auto!important;padding:8px 0 24px}
.home-module-orbit.is-linear .mtdi-orbit-ring-v2,
.mtdi-orbit-scene.is-linear .mtdi-orbit-ring-v2{display:none}
.home-module-orbit.is-linear .home-module-core,
.mtdi-orbit-scene.is-linear .mtdi-constellation-core{
  position:relative!important;left:auto!important;top:auto!important;
  translate:none!important;margin:0 auto 24px;display:block}
.mtdi-orbit-scene.is-linear .mtdi-constellation-label{
  position:static!important;translate:none!important;margin:0 auto 18px;width:auto}
.mtdi-orbit-scene.is-linear .mtdi-v2-caption{position:static!important;margin-bottom:16px}
.home-module-orbit.is-linear .home-module-orbit-stage{
  position:static!important;translate:none!important;
  width:auto!important;height:auto!important;
  display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));gap:14px}
.mtdi-orbit-scene.is-linear{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));gap:14px;
  width:100%!important;left:auto!important;translate:none!important}
.home-module-orbit.is-linear .mtdi-orbit-card:not(.is-detached),
.mtdi-orbit-scene.is-linear .mtdi-orbit-card:not(.is-detached){
  position:static!important;margin:0!important;
  width:auto!important;height:auto!important;min-height:172px;
  transform:none!important;opacity:1!important}
.home-module-orbit.is-linear .mtdi-orbit-card:not(.is-detached) .mtdi-card-summary,
.mtdi-orbit-scene.is-linear .mtdi-orbit-card:not(.is-detached) .mtdi-card-summary{height:auto!important;min-height:172px}
.mtdi-orbit-scene.is-linear .mtdi-constellation-core,
.mtdi-orbit-scene.is-linear .mtdi-constellation-label,
.mtdi-orbit-scene.is-linear .mtdi-v2-caption{grid-column:1/-1}
/* An expanded card is fixed-position, so it is unaffected by the grid above. */
.mtdi-orbit-scene.is-linear .mtdi-orbit-card.is-detached{
  position:fixed!important;transform:none!important}

/* ═══ 5. METRIC ROWS — grid instead of ragged flex wrap ══════════════════════ */
.metric-row{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(168px,1fr));
  gap:14px;margin-bottom:20px}
.metric-row .metric-card{min-width:0;width:100%;display:block}

/* ═══ 6. FORM CONTROLS — one appearance ══════════════════════════════════════ */
/* Editing surfaces remain dark in both site themes. Native controls and browser
   autofill must never produce white-on-white text. */
input:not([type="checkbox"]):not([type="radio"]):not([type="range"]):not([type="button"]):not([type="submit"]),
textarea,select,[contenteditable="true"]{
  background:#0c121e!important;background-color:#0c121e!important;
  color:#e8eeff!important;-webkit-text-fill-color:#e8eeff!important;
  caret-color:#00e5ff!important;border-color:#35435a!important;
  color-scheme:dark!important}
input:not([type="checkbox"]):not([type="radio"]):not([type="range"])::placeholder,
textarea::placeholder{
  color:#8fa0b9!important;-webkit-text-fill-color:#8fa0b9!important;
  opacity:1!important}
input:-webkit-autofill,input:-webkit-autofill:hover,input:-webkit-autofill:focus,
textarea:-webkit-autofill,select:-webkit-autofill{
  -webkit-box-shadow:0 0 0 1000px #0c121e inset!important;
  box-shadow:0 0 0 1000px #0c121e inset!important;
  -webkit-text-fill-color:#e8eeff!important;caret-color:#00e5ff!important}
input:disabled,textarea:disabled,select:disabled{
  background:#111827!important;color:#9aa9bf!important;
  -webkit-text-fill-color:#9aa9bf!important;opacity:1!important}
.key-add-row input,.ch3-ctl-row input,.nvtra-input-bar .nvtra-composer-row>input,
.key-name-edit{
  background:#0c121e!important;
  border:1px solid var(--line-strong)!important;
  border-radius:var(--r-sm)!important;
  color:var(--c-white)!important;
  -webkit-text-fill-color:var(--c-white)!important;
  caret-color:var(--focus)!important;
  padding:10px 12px!important;
  font-size:13px!important;
  transition:border-color var(--dur-fast) var(--ease),box-shadow var(--dur-fast) var(--ease)}
.key-add-row input::placeholder,.ch3-ctl-row input::placeholder,
.nvtra-input-bar input::placeholder{
  color:var(--c-sub)!important;-webkit-text-fill-color:var(--c-sub)!important;opacity:1!important}
.key-add-row input:focus,.ch3-ctl-row input:focus,
.nvtra-input-bar .nvtra-composer-row>input:focus,.key-name-edit:focus{
  border-color:var(--focus)!important;
  box-shadow:0 0 0 3px color-mix(in srgb,var(--focus) 22%,transparent)!important;
  outline:none!important}
/* Dash 4 rewrote dcc.Dropdown onto a Radix button (.dash-dropdown-*). Every
   .Select-* rule in this file targets the old react-select v1 markup and matches
   nothing, so the control fell back to a white background while inheriting the
   app's near-white text — the provider name was rendering white-on-white and was
   completely unreadable. The old selectors are kept for older Dash builds; these
   style what actually renders here. */
.key-provider-select .Select-control{
  background:#0c121e!important;
  border:1px solid var(--line-strong)!important;
  border-radius:var(--r-sm)!important;height:42px}
.key-provider-select .Select-value-label,
.key-provider-select .Select-placeholder{color:var(--c-white)!important}
.dash-dropdown{
  background:#0c121e!important;
  border:1px solid var(--line-strong)!important;
  border-radius:var(--r-sm)!important;
  color:var(--c-white)!important;
  min-height:42px;padding:0 12px;
  font-family:'DM Mono','Courier New',monospace;font-size:12px;
  text-align:left;cursor:pointer;
  transition:border-color var(--dur-fast) var(--ease)}
.dash-dropdown:hover{border-color:var(--focus)!important}
.dash-dropdown[data-state="open"]{border-color:var(--focus)!important}
.dash-dropdown-value,.dash-dropdown-value-item,.dash-dropdown-value-item span{
  color:var(--c-white)!important;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.dash-dropdown-placeholder{color:var(--c-sub)!important}
.dash-dropdown-trigger-icon{color:var(--c-sub);flex-shrink:0}
/* The listbox is portalled to <body>, so it is styled outside the field itself. */
[role="listbox"],.dash-dropdown-menu,.dash-dropdown-content{
  background:#0c121e!important;
  border:1px solid var(--line-strong)!important;
  border-radius:var(--r-sm)!important;
  color:var(--c-white)!important;
  box-shadow:var(--shadow-2)!important;
  font-family:'DM Mono','Courier New',monospace;font-size:12px;z-index:100002}
[role="option"]{color:var(--c-white)!important;padding:9px 12px;cursor:pointer}
[role="option"][data-highlighted],[role="option"]:hover{
  background:color-mix(in srgb,var(--focus) 18%,transparent)!important;
  color:var(--c-white)!important;outline:none}
[role="option"][data-state="checked"]{color:var(--focus)!important}
/* Form fields deliberately stay dark even when the surrounding dashboard uses
   its light palette, so typed and selected values retain strong contrast. */

/* Visible keyboard focus on everything interactive, not just buttons. */
a:focus-visible,button:focus-visible,input:focus-visible,
summary:focus-visible,[tabindex]:focus-visible{
  outline:2px solid var(--focus);outline-offset:2px;border-radius:6px}

/* ═══ 7. TABLE AND CHART OVERFLOW ════════════════════════════════════════════
   Wide tables previously widened the document instead of scrolling themselves. */
.ch3-peak-table,.scan-table{overflow-x:auto}
.ch3-peak-head,.ch3-peak-row,.scan-head,.scan-row{min-width:560px}
@media(max-width:820px){.ch3-peak-head,.ch3-peak-row,.scan-head,.scan-row{min-width:0}}
.chart-grid,.threeup,.sys-grid,.arch-stats{min-width:0}
.chart-card{min-width:0;overflow:hidden}
/* ═══ 7b. LIGHT-MODE CONTRAST HOLES ══════════════════════════════════════════
   Measured in the browser after the token change: these are the selectors that
   still fell below 4.5:1 on a white surface, either because the colour was baked
   in as a literal or because it comes from an inline --acc chosen for a dark
   background. */
/* Pillar accents are pastels tuned for a dark card and drop to ~1.9:1 on white.
   Mixing each one toward ink keeps its hue — so a pillar is still identifiable by
   colour — while clearing AA. */
/* Same accents on the dark card land at 4.37-4.43:1 — just under AA. Lifting them
   toward white clears it without changing the hue that identifies each module. */
.mtdi-card-index,.home-module-key span,.home-module-live,.home-module-live span,
.layer-pill,.mtdi-section-kicker,.mtdi-field-num{
  color:color-mix(in srgb,var(--acc,var(--c-cyan)) 88%,#ffffff)}

/* ═══ 8. PAGE RHYTHM ═════════════════════════════════════════════════════════ */
.section-label{margin-top:0;margin-bottom:12px;color:var(--c-sub)!important}
.divider{margin:28px 0}
.summary-panel{margin-top:20px}
.sg-analysis-panel{margin-top:22px;padding:22px;border:1px solid rgba(255,202,40,.28);
  border-radius:var(--r-md);background:linear-gradient(145deg,rgba(255,202,40,.055),rgba(8,14,24,.72))}
.sg-analysis-head{display:flex;align-items:flex-start;justify-content:space-between;gap:18px}
.sg-live-state{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:18px 0}
.sg-live-chip{padding:11px 13px;border:1px solid var(--line);border-radius:var(--r-sm);
  background:var(--surface-2);font:10px/1.55 'DM Mono',monospace;color:var(--c-sub)}
.sg-live-chip b{display:block;color:var(--c-white);font-size:13px;font-weight:500}
.sg-controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.sg-action{width:auto!important;margin:0!important;min-height:42px}
.sg-result{margin-top:18px;min-height:130px;padding:18px;border:1px solid var(--line-strong);
  border-radius:var(--r-sm);background:#080f1b;color:var(--c-white);
  font:12px/1.75 'DM Mono',monospace;white-space:pre-wrap;overflow-wrap:anywhere}
@media(max-width:760px){
  .sg-analysis-panel{padding:15px}.sg-analysis-head{display:block}
  .sg-analysis-head .nvtra-badge{margin-top:12px;display:inline-flex}
  .sg-live-state{grid-template-columns:1fr}.sg-controls{display:grid;grid-template-columns:1fr}
  .sg-action{width:100%!important}.sg-result{font-size:11px;padding:14px}
}
.nvtra-ml-panel{margin:0 24px 24px;padding:20px;border:1px solid rgba(255,202,40,.25);border-radius:16px;background:linear-gradient(145deg,rgba(255,202,40,.07),rgba(7,9,15,.72))}
.nvtra-ml-head{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;margin-bottom:16px}
.nvtra-ml-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.nvtra-ml-sample{padding:13px;border:1px solid rgba(255,255,255,.08);border-radius:12px;background:rgba(255,255,255,.025)}
.nvtra-ml-sample b{display:block;color:var(--c-white);font:600 11px 'DM Mono',monospace;letter-spacing:.1em;margin-bottom:5px}
.nvtra-ml-sample span{color:var(--muted);font:10px 'DM Mono',monospace}
.nvtra-ml-result{margin-top:12px;padding:15px;border-radius:12px;border:1px solid rgba(0,229,255,.2);background:rgba(0,229,255,.045);white-space:pre-line;color:var(--c-white);font:11px 'DM Mono',monospace;line-height:1.65}
@media(max-width:700px){.nvtra-ml-panel{margin:0 12px 18px;padding:15px}.nvtra-ml-head{display:block}.nvtra-ml-head .nvtra-badge{display:inline-flex;margin-top:10px}.nvtra-ml-grid{grid-template-columns:1fr}}

/* ═══ 9. PHONE PERFORMANCE + TOUCH LAYOUT ═══════════════════════════════════ */
/* Landscape phones keep the complete desktop composition, with touch-sized
   controls layered on top of it. */
/* A phone shows the desktop composition and nothing else: no enlarged header, no
   grown controls, no floating refresh button. Those made the phone render a layout
   the PC never shows, which is exactly what this view is supposed to avoid. The only
   phone-specific rule left is touch-action, which removes the 300 ms tap delay and
   changes no geometry. */
html.phone-desktop button,html.phone-desktop a,html.phone-desktop input,
html.phone-desktop select,html.phone-desktop .dash-dropdown{
  touch-action:manipulation}
html.phone-desktop .mtdi-orbit-card{cursor:pointer}
/* Phone stage: the drag-to-rotate views (3D boards, globe, constellation, 3D charts) keep a
   sideways drag and give an up/down drag to the page. On a phone they span whole cards, so
   claiming every drag left nowhere to scroll from. The upright stage applies the same rule
   in the /phone shell, which scrolls it. */
html.phone-stage #nvtra-spline-canvas,html.phone-stage #home-module-globe,
html.phone-stage .instrument-constellation-canvas,html.phone-stage .i3-lunar-canvas,
html.phone-stage .i3-vector,html.phone-stage .i3-sc-canvas,html.phone-stage .i3-sc-boards,
html.phone-stage .i3-tab-board canvas,html.phone-stage .js-plotly-plot canvas{touch-action:pan-y!important}
#mobile-refresh-btn{display:none}

/* ===== SCROLL ANCHORING =====
   The instrument is a live dashboard: blocks above the fold gain and lose height on
   every tick as readings arrive, a status line wraps, a table gains a row, a sweep
   block appears. Browser scroll anchoring reacts by moving scrollTop to hold the
   view steady - measured on the Sweep3 page, the document grew 9629 -> 10457 px
   and the scroll position was pushed 4000 -> 4998 to match.

   That is the "cannot scroll back up" behaviour: each upward scroll is partly undone
   by the next re-anchor, so the page fights the operator. Turning anchoring off makes
   the scroll position mean exactly what the operator set it to. Content above may
   shift under a re-render, which is the lesser problem: scrolling always works. */
#page-content,#page-content *{overflow-anchor:none}
html,body{overflow-anchor:none}

@media(max-width:760px){
  html{scrollbar-gutter:auto;overflow-x:hidden}
  body{overflow-x:hidden;text-rendering:optimizeSpeed}
  #page-shader-canvas,#nvtra-mascot-canvas,#intro-shader,
  .disc-svg-host,.mtdi-orbit-ring-v2{display:none!important}
  #startup-intro{display:none!important}
  .site-header{top:auto!important;bottom:0;height:calc(64px + env(safe-area-inset-bottom));
    min-height:64px;padding:5px 6px env(safe-area-inset-bottom);
    background:#090f1a!important;backdrop-filter:none!important;
    -webkit-backdrop-filter:none!important;border-top:1px solid rgba(255,255,255,.12);
    border-bottom:0;box-shadow:0 -8px 28px rgba(0,0,0,.32)}
  #page-content{padding-top:0;padding-bottom:calc(76px + env(safe-area-inset-bottom));
    contain:none;min-width:0}
  .nav-glass-wrap{position:static!important;transform:none!important;width:100%;max-width:100%}
  .nav-glass{width:100%;height:54px;justify-content:space-between;padding:2px;gap:2px;
    border:0;background:transparent;box-shadow:none;
    backdrop-filter:none!important;-webkit-backdrop-filter:none!important}
  .nav-glass-btn{min-width:0;min-height:48px;padding:6px 3px!important;font-size:8px;
    line-height:1.15;letter-spacing:.04em;justify-content:center;flex:1;
    flex-direction:column;gap:4px;border-radius:10px;color:#a7b4c8}
  .nav-glass-btn .nav-dot{display:block!important;width:6px;height:6px}
  .nav-glass-btn.nav-active{background:rgba(0,229,255,.1);text-shadow:none}
  .nav-glass-sep{display:none}
  #fixed-credit,#typewriter-bar,#nvtra-alert-stack{display:none!important}
  #simulation-watermark{left:auto!important;right:8px!important;top:8px!important;
    bottom:auto!important;width:auto!important;padding:5px 7px!important;border-radius:6px;
    font-size:7px!important;letter-spacing:.08em!important;box-shadow:none!important;
    pointer-events:none}
  .hero-wrap{padding-top:24px!important;min-width:0}
  .hero-title-wrap{min-width:0;width:100%}
  .hero-title{font-size:clamp(24px,7.2vw,36px)!important;line-height:1.08!important;
    letter-spacing:0!important;white-space:nowrap!important;max-width:100%;
    padding:14px 18px!important;box-sizing:border-box}
  .hero-tag{font-size:9px!important;line-height:1.5;letter-spacing:.12em!important}

  /* A readable card grid replaces overlapping, continuously moving orbit cards. */
  .home-module-orbit{height:auto!important;min-height:0;margin:8px 0 18px!important;
    display:flex;flex-direction:column;overflow:visible!important}
  .home-module-core{position:relative!important;left:auto!important;top:auto!important;
    translate:none!important;order:0;margin:8px auto 18px;width:150px!important;height:150px!important}
  #home-module-globe{width:144px!important;height:144px!important;touch-action:pan-y!important}
  .home-module-orbit-stage{position:static!important;left:auto!important;top:auto!important;
    translate:none!important;width:100%!important;height:auto!important;order:1;
    display:grid!important;grid-template-columns:1fr!important;gap:12px;padding:0 2px}
  .home-module-orbit-card.mtdi-orbit-card{position:relative!important;left:auto!important;top:auto!important;
    width:100%!important;height:auto!important;min-height:154px!important;margin:0!important;
    transform:none!important;animation:none!important;will-change:auto!important;touch-action:manipulation}
  .home-module-orbit-card .mtdi-card-summary{height:auto!important;min-height:152px!important;padding:18px!important}
  .home-module-orbit-card .mtdi-card-title{font-size:16px!important;margin-top:10px}
  .home-module-orbit-card .mtdi-card-short{font-size:12px!important;line-height:1.5}
  .home-module-orbit-card .mtdi-card-enter{font-size:10px!important;right:16px;bottom:14px}
  .home-module-live{font-size:12px!important}.home-module-live small{font-size:9px!important}
  .home-module-key{order:2;font-size:9px!important;line-height:1.5;margin:16px 8px 0}

  /* MTDI uses the same dependable tap-first list on a phone. Expanded pillars
     still open as full-screen detail views, so no desktop capability is removed. */
  .mtdi-v2-hero{padding:24px 0 12px!important;text-align:left}
  .mtdi-v2-meta{justify-content:flex-start;gap:6px}
  .mtdi-orbit-scene{height:auto!important;min-height:0!important;left:auto!important;
    width:100%!important;display:flex!important;flex-direction:column;gap:12px;
    padding:4px 0 18px!important;overflow:visible!important}
  .mtdi-orbit-scene .mtdi-constellation-core{position:relative!important;left:auto!important;
    top:auto!important;translate:none!important;order:0;margin:8px auto 14px;
    width:190px!important;height:190px!important;touch-action:pan-y!important}
  .mtdi-orbit-scene .mtdi-constellation-label,.mtdi-v2-caption{position:static!important;
    translate:none!important;order:1;margin:0 auto 8px!important;text-align:center}
  .mtdi-orbit-scene .mtdi-orbit-card:not(.is-detached){position:relative!important;
    left:auto!important;top:auto!important;width:100%!important;height:auto!important;
    min-height:154px;margin:0!important;transform:none!important;order:2;
    animation:none!important;will-change:auto!important;touch-action:manipulation}
  .mtdi-orbit-scene .mtdi-orbit-card:not(.is-detached) .mtdi-card-summary{
    height:auto!important;min-height:152px!important;padding:18px!important}
  body.mtdi-detail-open .mtdi-orbit-card.is-detached{
    inset:0!important;width:100vw!important;height:100dvh!important;max-width:none!important;
    border-radius:0!important;padding-bottom:calc(70px + env(safe-area-inset-bottom));
    background:#070b13!important;opacity:1!important}
  .mtdi-detail-nav{top:0!important;padding:10px 12px!important;min-height:54px}
  .mtdi-detail-close{min-width:44px;min-height:44px}

  .metric-row,.sys-grid,.chart-grid,.threeup,.arch-stats,
  .pillar-grid,.mtdi-field-grid{grid-template-columns:1fr!important;gap:12px!important}
  .tab-bar{display:flex;overflow-x:auto;overflow-y:hidden;gap:4px;margin:0 -2px 20px;
    padding:0 2px;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;
    scrollbar-width:none}
  .tab-bar::-webkit-scrollbar{display:none}
  .tab-btn{flex:0 0 auto;min-width:44%;min-height:48px;padding:10px 12px!important;
    white-space:normal;line-height:1.35;scroll-snap-align:start}
  .module-card,.chart-card,.mtdi-section-card,.summary-panel{padding:16px!important;border-radius:14px}
  .metric-card,.sys-card{padding:15px!important;min-width:0!important;width:100%}
  .metric-value{font-size:28px}.page-title{font-size:clamp(27px,9vw,42px)!important}
  .page-subtitle,.hero-sub{font-size:13px!important;line-height:1.65}
  .nvtra-chat-workspace{margin:8px 0!important;border-radius:12px}
  .nvtra-session-sidebar{display:flex!important;flex-direction:row!important;gap:8px;
    max-height:none!important;overflow-x:auto!important;overflow-y:hidden!important;
    padding:10px!important;border-right:0!important;border-bottom:1px solid var(--line);
    scroll-snap-type:x proximity;-webkit-overflow-scrolling:touch}
  .nvtra-session-sidebar>*{flex:0 0 min(78vw,280px);scroll-snap-align:start}
  .nvtra-chat-main{min-width:0}
  .nvtra-msgs{padding:14px 10px!important}
  .nvtra-msg-user,.nvtra-msg-ai{max-width:94%!important;padding:12px!important}
  .nvtra-input-bar{position:sticky;bottom:0;margin:6px!important;padding:10px!important}
  .nvtra-composer-row input{min-width:0;font-size:16px!important}
  button,a,input,select,.dash-dropdown{touch-action:manipulation}
  button,.back-btn,.open-btn,.key-btn,.ch3-btn{min-height:44px}
  .js-plotly-plot,.plot-container,.svg-container{max-width:100%!important}
  .chart-card,.mtdi-section-card,.arch-shell{content-visibility:auto;
    contain-intrinsic-size:auto 420px}
  .ch3-ctl-row,.key-add-row{display:grid!important;grid-template-columns:1fr!important;gap:10px}
  .settings-stack,.set-card{min-width:0!important}
  .set-card{padding:16px!important}
  .ch3-peak-table,.scan-table{margin-left:-6px;margin-right:-6px}
  *{animation-duration:.01ms!important;animation-iteration-count:1!important;
    transition-duration:.12s!important}
  body:has(input:focus) .site-header,body:has(textarea:focus) .site-header{display:none!important}
  body:has(input:focus) #page-content,body:has(textarea:focus) #page-content{padding-bottom:12px}
}
"""


def startup_intro():
    """The supplied startup intro, as Dash components.

    Rendered once per document load as part of the permanent shell. The routing
    callback never touches it — it only writes page-content.children.
    """
    hardware = [
        ("ITEM 1", "Text"),
        ("ITEM 2", "Text"),
        ("ITEM 3", "Text"),
        ("ITEM 4", "Text"),
        ("ITEM 5", "Text"),
        ("ITEM 6", "Text"),
    ]
    return html.Section([
        html.Div([
            html.Canvas(id="intro-shader"),
            html.Div(T("intro.eyebrow"), className="intro-eyebrow"),
            html.Div(T("intro.title_top"), className="intro-title intro-title-top"),
            html.Div(T("intro.title_bottom"), className="intro-title intro-title-bottom"),
            html.Article([
                html.Div(T("intro.kicker"), className="intro-card-kicker"),
                html.H1(T("intro.heading"), className="intro-card-title"),
                html.P(T("intro.description"),
                       className="intro-description"),
                html.Div('Label', className="hardware-label"),
                html.Div([
                    html.Div([html.Div(name, className="hardware-name"),
                              html.Div(role, className="hardware-role")], className="hardware-item")
                    for name, role in hardware
                ], className="hardware-grid"),
                html.Div(["by ", html.Strong("Author")], className="intro-credit"),
            ], className="intro-card"),
        ], className="intro-stage"),
    ], id="startup-intro", **{"aria-label": 'Text'})


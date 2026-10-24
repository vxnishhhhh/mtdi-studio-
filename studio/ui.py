"""Instrument presentation and browser state."""

import base64
import json
import re

from .content import T  # studio words (S1-06)
import zlib

CSS = r'''
:root {
 --i3-css-ready: 238;
 --i3-bg:#050b16; --i3-surface:#0b1628; --i3-raised:#112440; --i3-soft:#081222;
 --i3-ink:#edf6ff; --i3-muted:#9db4cf; --i3-accent:#39c8ff; --i3-accent-ink:#021b32;
 --i3-hover:#203e48; --i3-active:#245463; --i3-border:#304b55; --i3-grid:#263d46;
 --i3-good:#6fddb2; --i3-warn:#f2c778; --i3-error:#ff9995; --i3-disabled:#76919b;
 --i3-shadow:0 12px 32px #00000038; --i3-focus:0 0 0 3px #31d7e650;
 --i3-shader-ink:0.19,0.84,0.90; --i3-shader-bg:0.031,0.071,0.090;
 --i3-chart-1:#31d7e6; --i3-chart-2:#91aaf5; --i3-chart-3:#f2c778;
 --c-cyan:var(--i3-accent);--c-blue:var(--i3-chart-2);--c-white:var(--i3-ink);--c-sub:var(--i3-muted);--c-green:var(--i3-good);--c-red:var(--i3-error);--c-amber:var(--i3-warn);
 --i3-font:'Space Grotesk','DM Sans',Inter,Arial,Helvetica,sans-serif; --i3-mono:'DM Mono',ui-monospace,'Courier New',monospace;
}
html:not([data-i3-ready]) #app-shell,html:not([data-i3-ready]) #startup-intro,html:not([data-i3-ready]) .site-header {visibility:hidden;}
#startup-intro {z-index:2147483000;}
body.intro-active .site-header,body.intro-active #i3-field-background {opacity:0!important;pointer-events:none!important;}
#i3-boot {position:fixed;inset:0;z-index:2147483646;display:grid;place-content:center;justify-items:center;gap:clamp(18px,3vh,34px);padding:32px;background:radial-gradient(120% 90% at 50% 0%,#0b1f3a 0%,#050b16 62%);color:var(--i3-ink);font-family:var(--i3-font);}
.i3-boot-eyebrow {letter-spacing:.26em;font:600 clamp(11px,1.3vw,15px) var(--i3-mono);color:#60a5fa;}
.i3-boot-title {font-size:clamp(40px,8vw,84px);letter-spacing:-.04em;font-weight:700;line-height:1;} .i3-boot-title span{color:#38bdf8;}
/* Liquid loader: seven gradient columns driven by three summed sine waves. */
.i3-liquid {display:flex;align-items:flex-end;gap:22px;height:min(340px,38vh);perspective:900px;}
.i3-liquid-col {position:relative;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;}
.i3-liquid .i3-bar {display:block;width:clamp(36px,4.2vw,58px);height:min(120px,14vh);border-radius:999px;background:radial-gradient(ellipse at 34% 14%,rgba(255,255,255,.58),rgba(255,255,255,0) 24%),linear-gradient(90deg,color-mix(in srgb,var(--c1) 78%,#020617),var(--c2) 42%,color-mix(in srgb,var(--c1) 70%,#020617));border:1px solid rgba(190,235,255,.22);transform-origin:50% 100%;transform:scaleY(.1);box-shadow:0 12px 24px rgba(0,0,0,.34),0 0 22px color-mix(in srgb,var(--c1) 42%,transparent),inset 8px 0 12px rgba(0,0,0,.22),inset -6px 0 12px rgba(255,255,255,.12);position:relative;overflow:hidden;will-change:transform;backface-visibility:hidden;}
.i3-liquid .i3-bar s {position:absolute;left:7%;right:7%;top:2px;height:17%;border-radius:50%;background:radial-gradient(ellipse at 42% 30%,rgba(255,255,255,.72),rgba(180,230,255,.2) 46%,rgba(0,20,55,.18) 75%);box-shadow:inset 0 -2px 5px rgba(0,0,0,.22);}
.i3-liquid .i3-bar u {position:absolute;top:9%;bottom:9%;left:18%;width:18%;border-radius:999px;background:linear-gradient(to bottom,rgba(255,255,255,.05),rgba(255,255,255,.42) 42%,rgba(255,255,255,.10));filter:blur(.4px);}
.i3-liquid .i3-drop {display:block;width:22px;height:22px;border-radius:50%;margin-bottom:16px;background:linear-gradient(90deg,var(--c1),var(--c2));opacity:0;transform:translateY(10px) scale(.5);transition:opacity .5s ease-out,transform .5s ease-out;box-shadow:0 0 15px color-mix(in srgb,var(--c1) 45%,transparent);will-change:transform,opacity;}
.i3-liquid .i3-drop.on {opacity:1;transform:translateY(0) scale(1);}
.i3-liquid .i3-base {display:block;width:16px;height:16px;border-radius:50%;margin-top:14px;background:linear-gradient(90deg,var(--c1),var(--c2));box-shadow:0 2px 8px color-mix(in srgb,var(--c1) 40%,transparent);animation:i3Base 3s ease-in-out infinite;}
.i3-liquid-col:nth-child(2) .i3-base{animation-delay:.3s}.i3-liquid-col:nth-child(3) .i3-base{animation-delay:.6s}.i3-liquid-col:nth-child(4) .i3-base{animation-delay:.9s}.i3-liquid-col:nth-child(5) .i3-base{animation-delay:1.2s}.i3-liquid-col:nth-child(6) .i3-base{animation-delay:1.5s}.i3-liquid-col:nth-child(7) .i3-base{animation-delay:1.8s}
@keyframes i3Shimmer {0%,100%{transform:translateX(-8px)}50%{transform:translateX(8px)}}
@keyframes i3Base {0%,100%{transform:scale(.7);opacity:.6}50%{transform:scale(1);opacity:1}}
/* Box loader: four cubes on an isometric track. */
.i3-boot-row {display:grid;justify-items:center;gap:30px;}
.i3-boxes {--size:clamp(28px,3.4vw,44px);--duration:800ms;height:calc(var(--size)*2);width:calc(var(--size)*3);position:relative;transform-style:preserve-3d;transform-origin:50% 50%;margin:calc(var(--size)*1.2) 0 calc(var(--size)*.6);transform:rotateX(60deg) rotateZ(45deg) rotateY(0deg) translateZ(0);}
.i3-box {width:var(--size);height:var(--size);top:0;left:0;position:absolute;transform-style:preserve-3d;}
.i3-box-1{transform:translate(100%,0);animation:i3Box1 var(--duration) linear infinite}
.i3-box-2{transform:translate(0,100%);animation:i3Box2 var(--duration) linear infinite}
.i3-box-3{transform:translate(100%,100%);animation:i3Box3 var(--duration) linear infinite}
.i3-box-4{transform:translate(200%,0);animation:i3Box4 var(--duration) linear infinite}
.i3-face {position:absolute;width:100%;height:100%;background:var(--i3-accent);}
.i3-front{transform:rotateY(0deg) translateZ(calc(var(--size)/2));background:#3b82f6}
.i3-right{transform:rotateY(90deg) translateZ(calc(var(--size)/2));background:#1e40af}
.i3-top{transform:rotateX(90deg) translateZ(calc(var(--size)/2));background:#93c5fd}
.i3-back{transform:rotateY(180deg) translateZ(calc(var(--size)/2));background:#1e3a8a}
@keyframes i3Box1{0%,50%{transform:translate(100%,0)}100%{transform:translate(200%,0)}}
@keyframes i3Box2{0%{transform:translate(0,100%)}50%{transform:translate(0,0)}100%{transform:translate(100%,0)}}
@keyframes i3Box3{0%,50%{transform:translate(100%,100%)}100%{transform:translate(0,100%)}}
@keyframes i3Box4{0%{transform:translate(200%,0)}50%{transform:translate(200%,100%)}100%{transform:translate(100%,100%)}}
/* Progress */
.i3-progress-wrap {width:min(680px,86vw);display:grid;gap:10px;}
.i3-progress-head {display:flex;justify-content:space-between;gap:16px;font:500 clamp(12px,1.35vw,15px)/1.5 var(--i3-mono);letter-spacing:.035em;color:var(--i3-muted);min-height:24px;} #i3-boot-percent{font:600 clamp(18px,2.4vw,26px) var(--i3-mono);color:var(--i3-ink);font-variant-numeric:tabular-nums;} #i3-boot-detail{font:11px var(--i3-mono);color:var(--i3-muted);letter-spacing:.04em;min-height:18px;font-variant-numeric:tabular-nums;}
.i3-progress {height:14px;border-radius:999px;background:color-mix(in srgb,var(--i3-ink) 10%,transparent);overflow:hidden;border:1px solid var(--i3-border);}
.i3-progress-fill {height:100%;width:0%;border-radius:999px;background:linear-gradient(90deg,#1d4ed8,#3b82f6,#38bdf8,#22d3ee);transition:width .35s cubic-bezier(.2,.8,.2,1);position:relative;overflow:hidden;box-shadow:0 0 16px color-mix(in srgb,var(--i3-accent) 50%,transparent);}
.i3-progress-shine {position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.55),transparent);width:40%;animation:i3Shine 1.4s linear infinite;}
@keyframes i3Shine {0%{transform:translateX(-120%)}100%{transform:translateX(320%)}}
.i3-progress-steps {display:flex;justify-content:space-between;font:600 clamp(10px,1.1vw,12px) var(--i3-mono);letter-spacing:.14em;text-transform:uppercase;color:var(--i3-muted);}
.i3-progress-steps span.done {color:#60a5fa;}
#i3-boot [hidden] {display:none!important;}
/* Wilderness scene: seventeen mountain and fog layers moving with the pointer. */
.i3-scene {position:absolute;inset:0;overflow:hidden;--scene-scale:1;background:linear-gradient(to bottom,#030712,#0b1f3a);}
.i3-scene img {position:absolute;pointer-events:none;transform:translate3d(-50%,-50%,0);will-change:transform;backface-visibility:hidden;user-select:none;image-rendering:auto;}
.i3-scene {animation:i3Breathe 26s ease-in-out infinite alternate;}
@keyframes i3Breathe {from{transform:scale(1.02)}to{transform:scale(1.07)}}
.i3-boot-panel {position:relative;display:grid;justify-items:center;gap:clamp(12px,2.2vh,22px);padding:clamp(20px,3.4vh,38px) clamp(24px,4.5vw,56px);border-radius:28px;background:linear-gradient(160deg,rgba(10,26,58,.55),rgba(3,10,26,.62));border:1px solid rgba(96,165,250,.22);backdrop-filter:blur(14px) saturate(130%);-webkit-backdrop-filter:blur(14px) saturate(130%);box-shadow:0 40px 100px rgba(0,0,0,.5),inset 0 1px 0 rgba(255,255,255,.08);transition:opacity .62s ease,transform .72s cubic-bezier(.16,1,.3,1);}
.i3-boot-panel.leaving {opacity:0;transform:translateY(-48px) scale(.97);}
.i3-boot-panel::before {content:'';position:absolute;inset:-1px;border-radius:29px;padding:1px;background:linear-gradient(135deg,rgba(125,211,252,.55),transparent 40%,transparent 60%,rgba(59,130,246,.45));-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;pointer-events:none;}
#i3-mode {padding:clamp(20px,3.4vh,38px) clamp(24px,4.5vw,56px);border-radius:28px;background:linear-gradient(160deg,rgba(10,26,58,.55),rgba(3,10,26,.62));border:1px solid rgba(96,165,250,.22);backdrop-filter:blur(14px) saturate(130%);box-shadow:0 40px 100px rgba(0,0,0,.5);transition:opacity .72s ease,transform .82s cubic-bezier(.16,1,.3,1);}
#i3-mode.entering {opacity:0;transform:translateY(56px) scale(.97);}
.i3-mode-card {backdrop-filter:none;}
.i3-scene-vignette {position:absolute;inset:0;z-index:200;pointer-events:none;background:radial-gradient(ellipse at center,rgba(8,20,45,.35) 40%,rgba(2,6,23,.9)),linear-gradient(to bottom,rgba(15,40,90,.25),rgba(3,7,18,.35));}
#i3-boot > :not(.i3-scene) {position:relative;z-index:300;}
#i3-boot {background:#030712;}
.i3-boot-title,.i3-mode-title {text-shadow:0 4px 30px rgba(0,0,0,.6);}
.i3-progress-wrap,.i3-mode-grid {backdrop-filter:none;-webkit-backdrop-filter:none;}
.i3-progress-wrap {padding:0;}
.i3-liquid {height:min(220px,26vh);} .i3-liquid .i3-bar {height:min(90px,11vh);}
.i3-boot-eyebrow,.i3-boot-title,.i3-mode-sub,.i3-progress-head,.i3-progress-steps,.i3-mode-hint,#i3-boot-detail {color:#e2e8f0;}
.i3-boot-eyebrow,.i3-progress-steps span.done {color:#93c5fd;}
.i3-boot-title span {color:#7dd3fc;}
#i3-boot {overflow:auto;}
#i3-mode {display:grid;gap:22px;justify-items:center;text-align:center;max-width:min(880px,92vw);}
#i3-mode[hidden] {display:none;}
.i3-mode-title {font-size:clamp(26px,4vw,40px);font-weight:700;letter-spacing:-.03em;}
.i3-mode-sub {color:var(--i3-muted);font-size:clamp(13px,1.5vw,16px);min-height:22px;}
.i3-mode-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;width:100%;}
.i3-mode-card {position:relative;display:grid;gap:10px;text-align:left;padding:26px 24px 24px;border-radius:18px;border:1px solid rgba(96,165,250,.28);background:linear-gradient(160deg,rgba(29,78,216,.18),rgba(8,15,30,.78));color:var(--i3-ink);cursor:pointer;font:inherit;transition:transform .2s,border-color .2s,box-shadow .2s;overflow:hidden;isolation:isolate;}
.i3-mode-card strong {font-size:clamp(22px,2.6vw,30px);letter-spacing:-.02em;}
.i3-mode-card span:not(.i3-mode-key) {color:var(--i3-muted);font-size:clamp(13px,1.4vw,15px);line-height:1.5;}
.i3-mode-card em {font:600 11px var(--i3-mono);letter-spacing:.1em;text-transform:uppercase;color:#60a5fa;min-height:14px;}
.i3-mode-card .i3-mode-key {position:absolute;top:14px;right:14px;width:30px;height:30px;border-radius:8px;border:1px solid rgba(96,165,250,.5);display:grid;place-items:center;font:600 13px var(--i3-mono);color:#93c5fd;}
.i3-mode-card.recommended::after {content:'recommended';position:absolute;left:24px;bottom:12px;font:600 10px var(--i3-mono);letter-spacing:.14em;text-transform:uppercase;color:#60a5fa;}
.i3-mode-card:hover,.i3-mode-card.selected {border-color:#3b82f6;box-shadow:0 0 0 2px rgba(59,130,246,.35),0 18px 40px rgba(29,78,216,.25);transform:translateY(-2px);}
.i3-mode-card:focus-visible {outline:2px solid #60a5fa;outline-offset:3px;}
.i3-mode-hint {font:12px var(--i3-mono);letter-spacing:.06em;color:var(--i3-muted);}
@media(max-width:640px){.i3-mode-grid{grid-template-columns:1fr;}}
@media(prefers-reduced-motion:reduce){.i3-liquid .i3-bar u,.i3-base,.i3-box,.i3-progress-shine{animation:none!important;}}
@media(max-width:600px){.i3-liquid{height:170px;gap:10px}.i3-liquid .i3-bar{width:28px}}
#i3-field-background {position:fixed;inset:0;width:100%;height:100%;pointer-events:none;z-index:0;opacity:.3;}
#react-entry-point {position:relative;z-index:1;}
:is(button,input,select,textarea) {font:inherit;}
:is(button,.btn,.key-btn,.back-btn,.set-seg-btn,.nav-glass-btn):not(.key-radio) {min-height:44px;touch-action:manipulation;}
.key-radio {min-height:0 !important;height:20px !important;}
.i3-tool {min-height:34px !important;height:34px !important;width:34px !important;}
.i3-tool.i3-tool-text {width:auto !important;}
.i3-voice-key-input {flex:1;min-width:220px;}
/* scrub heroes */
.i3-scrub-hero {position:relative;height:100dvh;width:100vw;margin:0 0 0 calc(50% - 50vw);overflow:hidden;background:transparent;}
.i3-scrub-stage {position:absolute;inset:0;will-change:transform,opacity;transform-origin:50% 40%;}
.i3-hero-hidden {display:none !important;}
main.i3-page > .i3-scrub-hero:first-child {margin-top:-158px;}
.i3-scrub-hero[data-i3-scrub=skyline] .i3-scrub-tag {align-items:flex-end;padding-bottom:20vh;}
.i3-scrub-hero[data-i3-scrub=skyline] .i3-scrub-tag p {font-size:clamp(15px,1.8vw,22px);color:#cfe9ff;}
.i3-scrub-video {position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block;opacity:0;transition:opacity .6s ease;transform-origin:50% 50%;will-change:transform;-webkit-mask-image:linear-gradient(to bottom,#000 84%,transparent 100%);mask-image:linear-gradient(to bottom,#000 84%,transparent 100%);}
.i3-scrub-video.ready {opacity:1;}
.i3-scrub-canvas {position:absolute;inset:0;width:100%;height:100%;display:block;-webkit-mask-image:linear-gradient(to bottom,#000 84%,transparent 100%);mask-image:linear-gradient(to bottom,#000 84%,transparent 100%);}
.i3-scrub-grad {display:none;}
.i3-scrub-title-long h1 {font-size:clamp(22px,4.2vw,60px);line-height:1.12;max-width:1100px;}
.i3-page-body.i3-page-body-flat {margin-top:0;border-radius:0;box-shadow:none;}
.i3-page-body.i3-page-body-flat::before {display:none;}
.mtdi-page-shell .parallax__pin {margin-top:-54px;}
.mtdi-page-shell .i3-page-body {padding-top:24px;margin-top:-60vh;position:relative;z-index:2;}
.i3-sg-card {display:grid;grid-template-columns:minmax(220px,1.1fr) minmax(280px,1fr);gap:18px;align-items:start;}
.i3-sg-two {display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.i3-sg-two > .i3-audio:first-child:nth-last-child(3) {grid-column:1 / -1;}
@media (max-width:900px){.i3-sg-two{grid-template-columns:1fr;}}
.i3-sg-listen h4 {margin:0 0 8px;font:600 14px Inter,sans-serif;display:flex;justify-content:space-between;gap:8px;}
.i3-sg-listen .i3-meter {width:100%;height:14px;border-radius:7px;display:block;margin:6px 0;}
.i3-sg-listen .i3-row {display:flex;justify-content:space-between;font-size:12px;padding:3px 0;color:var(--i3-muted);}
.i3-sg-listen .i3-form {display:flex;gap:8px;flex-wrap:wrap;margin:8px 0;}
.i3-sg-listen input[type=range] {width:100%;accent-color:var(--i3-accent);}
@media (max-width:760px){.i3-sg-card{grid-template-columns:1fr;}}
.i3-scrub-scrim {position:absolute;inset:0;pointer-events:none;background:radial-gradient(ellipse 62% 44% at 50% 50%,rgba(5,7,13,.68),rgba(5,7,13,0) 72%);}
.i3-scrub-title,.i3-scrub-tag {position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:0 6%;text-align:center;pointer-events:none;will-change:transform,opacity;}
.i3-scrub-title h1 {margin:0;font:500 clamp(26px,4vw,52px)/1.12 'DM Mono',monospace;letter-spacing:-.02em;color:#f2f4f8;text-shadow:0 4px 30px rgba(0,0,0,.55);}
.i3-scrub-tag {opacity:0;padding:0 8%;}
.i3-scrub-tag p {margin:0;font:400 clamp(15px,1.8vw,22px)/1.5 'DM Mono',monospace;letter-spacing:-.01em;color:#eaf4ff;text-shadow:0 4px 24px rgba(0,0,0,.6);}
.i3-scrub-hint {position:absolute;bottom:clamp(20px,6vh,48px);left:50%;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:8px;color:rgba(234,244,255,.72);font:600 clamp(10px,1.4vw,12px) Inter,sans-serif;letter-spacing:.3em;transition:opacity .4s;pointer-events:none;}
.i3-scrub-hint svg {opacity:.7;}
@keyframes i3-scrub-bounce {0%,100%{transform:translateY(0);opacity:.5}50%{transform:translateY(5px);opacity:1}}
.i3-scrub-skip {position:absolute;left:50%;top:84px;transform:translateX(-50%);z-index:3;border:1px solid var(--i3-border);border-radius:6px;padding:8px 16px;font:400 11px 'DM Mono',monospace;letter-spacing:.08em;color:var(--i3-ink);background:var(--i3-surface);opacity:0;transition:opacity .2s;cursor:pointer;}
.i3-scrub-skip {opacity:.55;}
.i3-scrub-skip:hover,.i3-scrub-skip:focus-visible {opacity:1;}
.i3-scrub-rail {position:absolute;left:0;right:0;bottom:0;height:2px;background:rgba(255,255,255,.12);transition:opacity .4s;}
.i3-scrub-hero.i3-scrub-done .i3-scrub-rail,.i3-scrub-hero.i3-scrub-done .i3-scrub-skip {opacity:0;pointer-events:none;}
.i3-scrub-bar {height:100%;width:100%;transform-origin:left center;transform:scaleX(0);background:linear-gradient(90deg,rgba(120,190,255,.45),rgba(214,236,255,.95));}
@media (prefers-reduced-motion: reduce){.i3-scrub-hint svg{animation:none;}}
/* ── UI polish pass ── */
#page-content {padding-bottom:150px !important;}                      /* the island never covers the last row */
.metric-row {grid-template-columns:repeat(auto-fit,minmax(150px,1fr)) !important;}
.metric-value {font-size:clamp(20px,2.1vw,30px) !important;overflow-wrap:anywhere;}
.i3-summary {height:auto !important;min-height:264px;contain:layout !important;}
.i3-summary>div:first-child {height:auto !important;}
.i3-summary .i3-condition {height:auto !important;min-height:48px;}
.i3-evidence {height:auto !important;max-height:150px;}
.i3-rotate-track {padding:0 34vw 0 8vw !important;}                  /* first pillar card fully in view */
.i3-scrub-hint {bottom:clamp(96px,14vh,130px) !important;}          /* clear of the island */
.i3-scrub-title h1 {font-size:clamp(26px,4vw,52px);}
.i3-scrub-title-long h1 {font-size:clamp(20px,2.8vw,36px);line-height:1.15;max-width:960px;}
.i3-scrub-tag p {font-size:clamp(15px,1.8vw,22px);max-width:900px;margin:0 auto;}
.i3-scrub-skip {top:70px;}
.i3-hand-vision-status {transition:opacity .4s;}
.i3-hand-vision-status.i3-fade {opacity:0;pointer-events:none;}
body.intro-active .i3-hand-vision-status {display:none;}

/* zoom bars: the same plain range control as the audio gain */
.ch3-ctl-bar:has(.i3-zoom-wrap) {display:grid;grid-template-columns:minmax(200px,.8fr) minmax(320px,1.6fr);align-items:center;gap:12px 24px;padding:14px 18px;}
.ch3-ctl-bar:has(.i3-zoom-wrap) .validation-subcopy {font-size:12px;line-height:1.45;}
.i3-zoom-wrap {display:grid;gap:4px;padding:6px 4px 0;}
.i3-zoom-dash {position:absolute;width:1px;height:1px;overflow:hidden;opacity:0;pointer-events:none;}
.i3-zoom-wrap {position:relative;}
.i3-zoom-face input[type=range] {width:100%;accent-color:#2979ff;min-height:34px;margin:0;background:transparent;border:0;display:block;}
.i3-audio input[type=range],.i3-sg-listen .i3-audio input[type=range] {accent-color:#2979ff;}
.i3-zoom-ticks {display:flex;justify-content:space-between;font:10px/1 'DM Mono',monospace;letter-spacing:.08em;color:var(--i3-muted);padding:0 2px;}

/* zoom bars: one row, label left, slider fills the rest */
.ch3-ctl-bar:has(.c1-slider-wrap) {display:grid;grid-template-columns:minmax(200px,.8fr) minmax(320px,1.6fr);align-items:center;gap:12px 24px;padding:14px 18px;}
.ch3-ctl-bar:has(.c1-slider-wrap) .validation-subcopy {font-size:12px;line-height:1.45;}
.c1-slider-wrap {min-width:0;padding:22px 20px 10px;background:transparent;border-color:rgba(77,112,156,.22);box-shadow:none;}
.c1-slider-wrap .rc-slider {padding:8px 0 26px !important;}
.c1-slider-wrap .rc-slider-rail {background:rgba(83,105,133,.45) !important;}
.c1-slider-wrap .rc-slider-mark-text {font-size:10px !important;transform:translateX(-50%) !important;}
.c1-slider-wrap .rc-slider-mark-text:first-of-type {transform:translateX(-50%) !important;}

/* compact listen cards: plain page surface (no raised tint), controls in one row */
.i3-sg-card {padding:14px 16px;grid-template-columns:minmax(200px,.9fr) minmax(300px,1.4fr);gap:14px 20px;}
.i3-sg-card .validation-subcopy {font-size:12px;line-height:1.5;}
.i3-sg-listen .i3-audio {background:transparent;border:0;padding:0;min-height:0;gap:6px;display:grid;grid-template-columns:1fr auto;grid-template-areas:"head head" "meter meter" "rows rows" "form gain" "audio audio";align-items:center;}
.i3-sg-listen .i3-audio h4 {grid-area:head;font-size:13px;margin:0;}
.i3-sg-listen .i3-audio .i3-meter {grid-area:meter;height:10px;border-radius:5px;margin:0;}
.i3-sg-listen .i3-audio .i3-row {display:inline-flex;gap:6px;font-size:11px;padding:0;margin-right:12px;color:var(--i3-muted);}
.i3-sg-listen .i3-audio .i3-row .i3-label::after {content:':';}
.i3-sg-listen .i3-audio .i3-row:nth-of-type(2) {grid-area:rows;display:none;}
.i3-sg-listen .i3-audio form {display:contents;}
.i3-sg-listen .i3-audio .i3-form {grid-area:form;display:flex;gap:6px;margin:0;}
.i3-sg-listen .i3-audio .i3-form .i3-btn {padding:6px 12px;min-height:34px;font-size:12px;}
.i3-sg-listen .i3-audio label {grid-area:gain;display:flex;align-items:center;gap:8px;font-size:11px;color:var(--i3-muted);margin:0;}
.i3-sg-listen .i3-audio input[type=range] {width:120px;min-height:34px;}
.i3-sg-listen .i3-audio .i3-inline-result {grid-area:audio;height:auto;min-height:0;font-size:11px;}
.i3-sg-listen .i3-audio audio {display:none;}
.i3-sg-two {gap:10px 24px;}
.i3-sg-two > .i3-audio.i3-p1-mix-block {grid-column:1 / -1;}


#i3-rotate-banner {position:fixed;top:72px;left:50%;transform:translate(-50%,-20px);opacity:0;pointer-events:none;z-index:9000;display:flex;flex-direction:column;align-items:center;gap:2px;padding:10px 22px;border-radius:14px;background:rgba(6,14,32,.82);border:1px solid rgba(0,229,255,.6);box-shadow:0 0 24px rgba(0,229,255,.35);color:#e8f6ff;font-family:'Inter',sans-serif;transition:opacity .2s,transform .25s;}
#i3-rotate-banner.on {opacity:1;transform:translate(-50%,0);}
#i3-fm-toast {position:fixed;top:72px;left:50%;transform:translate(-50%,-20px);opacity:0;pointer-events:none;z-index:9000;padding:8px 18px;border-radius:12px;background:rgba(6,14,32,.85);border:1px solid rgba(255,255,255,.25);color:#e8f6ff;font:600 12px/1.4 'Inter',sans-serif;letter-spacing:.14em;transition:opacity .2s,transform .25s;}
#i3-fm-toast.on {opacity:1;transform:translate(-50%,0);}
#i3-pause-banner {position:fixed;bottom:110px;left:50%;transform:translate(-50%,20px);opacity:0;pointer-events:none;z-index:9000;display:flex;flex-direction:column;align-items:center;gap:2px;padding:10px 22px;border-radius:14px;background:rgba(6,14,32,.85);border:1px solid rgba(255,171,64,.6);box-shadow:0 0 24px rgba(255,171,64,.25);color:#fff3e0;font-family:'Inter',sans-serif;transition:opacity .2s,transform .25s;}
#i3-pause-banner.on {opacity:1;transform:translate(-50%,0);}
#i3-pause-banner b {font-size:13px;letter-spacing:.22em;color:#ffab40;}
#i3-pause-banner span {font-size:11px;color:#ffd9a8;}
#i3-rotate-banner b {font-size:13px;letter-spacing:.22em;color:#22d3ee;}
#i3-rotate-banner span {font-size:11px;color:#9fd8ff;}
canvas.i3-rotating {outline:2px solid rgba(0,229,255,.75);outline-offset:4px;box-shadow:0 0 30px rgba(0,229,255,.4);border-radius:12px;}
.i3-voice-select {flex:1;min-width:240px;min-height:44px;border:1px solid var(--i3-border);border-radius:8px;background:var(--i3-raised);color:var(--i3-ink);padding:8px 10px;font:inherit;}
:is(button,input,select,textarea,a,summary):focus-visible {outline:2px solid var(--i3-accent)!important;outline-offset:3px;box-shadow:var(--i3-focus)!important;}
:is(button,input,select,textarea):disabled {opacity:.58;cursor:not-allowed!important;color:var(--i3-disabled)!important;box-shadow:none!important;}
:is(.sys-card,.metric-card) {height:158px;overflow:auto;contain:strict;content-visibility:auto;}
:is(.chart-card,.graph-card) {overflow:hidden;contain:layout style;}
:is(.validation-hero-card,.i3-principle) {min-height:190px;}
#mobile-refresh-btn {display:none!important;}
#typewriter-bar{width:300px;max-width:40vw;overflow:hidden;}#typewriter-text{display:inline-block;width:260px;max-width:34vw;}#typewriter-cursor{position:absolute;right:10px;}
.site-header {grid-template-columns:minmax(0,1fr) auto minmax(0,1fr) auto!important;}
.site-header > .i3-header-tools {display:flex!important;align-items:center;gap:6px;grid-row:1!important;grid-column:4!important;justify-self:end;width:auto!important;height:auto!important;overflow:visible!important;pointer-events:auto!important;}
.i3-tool {flex:0 0 34px;} .i3-tool-offline{color:#f59e0b!important;border-color:#f59e0b!important;} .i3-tool[hidden] {display:none!important;} .i3-tool-text {flex-basis:auto;}
.site-header .header-pills {grid-column:3;}
@media(max-width:760px){.site-header{display:flex!important;} .i3-header-tools{order:2;margin-left:auto;}}
.site-header .header-pills {display:none!important;}
.i3-tool {width:34px;height:34px;min-height:34px;border-radius:50%;border:1px solid var(--i3-border);background:transparent;color:var(--i3-muted);font-size:15px;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;padding:0;}
.i3-tool:hover {color:var(--i3-accent);border-color:var(--i3-accent);}
.i3-tool[aria-pressed=true] {color:var(--i3-accent);border-color:var(--i3-accent);box-shadow:0 0 10px var(--i3-accent);}
.i3-tool-text {width:auto;border-radius:17px;padding:0 12px;font:600 10px var(--i3-mono);letter-spacing:.12em;text-transform:uppercase;text-decoration:none;}
.i3-toast {position:fixed;left:50%;bottom:26px;transform:translate(-50%,20px);opacity:0;pointer-events:none;z-index:2147483002;max-width:min(560px,90vw);padding:10px 16px;border-radius:10px;background:var(--i3-surface);color:var(--i3-ink);border:1px solid var(--i3-border);box-shadow:var(--i3-shadow);font:13px/1.5 var(--i3-font);transition:opacity .25s,transform .25s;}
.i3-toast.show {opacity:1;transform:translate(-50%,0);}
body.intro-active .i3-header-tools,body.intro-active #i3-orb,html:not([data-i3-ready]) #i3-orb {opacity:0;pointer-events:none;}
.i3-btn {display:inline-flex;align-items:center;justify-content:center;gap:6px;border:1px solid var(--i3-border);border-radius:8px;background:var(--i3-raised);padding:9px 15px;min-height:38px;color:var(--i3-ink);cursor:pointer;font:500 12px/1 var(--i3-mono);letter-spacing:.08em;text-transform:uppercase;text-decoration:none;margin:4px 8px 4px 0;transition:border-color .18s,box-shadow .18s,background .18s;}
.i3-btn:hover {border-color:rgba(49,215,230,.55);box-shadow:0 0 0 1px rgba(49,215,230,.18),0 0 18px rgba(49,215,230,.12);}
.i3-btn:focus-visible {outline:2px solid var(--i3-accent);outline-offset:2px;}
.i3-card p {margin:0 0 12px;color:var(--i3-muted);font-size:13px;line-height:1.55;}
.i3-form :is(input,select),.i3-card :is(input[type=text],input[type=number],input[type=password],select) {background:var(--i3-soft);color:var(--i3-ink);font:13px var(--i3-mono);border:1px solid var(--i3-border);border-radius:7px;color-scheme:dark;}
.i3-form :is(input,select):focus {outline:none;border-color:rgba(49,215,230,.6);box-shadow:0 0 0 2px rgba(49,215,230,.15);}
.i3-form label {font:500 11px/1.3 var(--i3-mono);letter-spacing:.06em;text-transform:uppercase;}
.i3-form .dash-input-container,.i3-card .dash-input-container {background:var(--i3-soft);border:1px solid var(--i3-border);border-radius:7px;color-scheme:dark;}
.i3-form .dash-input-container .dash-input-element,.i3-card .dash-input-container .dash-input-element {background:transparent;border:0;color:var(--i3-ink);font:13px var(--i3-mono);}
.dash-input-container .dash-input-stepper {background:var(--i3-raised);color:var(--i3-muted);border:0;border-left:1px solid var(--i3-border);font:14px var(--i3-mono);cursor:pointer;}
.dash-input-container .dash-input-stepper:hover {color:var(--i3-accent);}
.i3-details,.i3-timeline {background:var(--i3-soft);border:1px solid var(--i3-border);border-radius:10px;padding:12px 14px;}
.i3-camera-preview-wrap,.i3-camera-frame {background:var(--i3-soft);border:1px solid var(--i3-border);border-radius:10px;}
.i3-primary {background:var(--i3-accent)!important;color:var(--i3-accent-ink)!important;font-weight:650;}
.i3-mute {color:var(--i3-muted);font-size:12px;line-height:1.5;}
.parallax__pin {height:160vh;height:160svh;margin:-104px 0 0 calc(50% - 50vw);width:100vw;position:relative;z-index:0;}
.parallax__pin.i3-parallax-complete {height:60vh;height:60svh;pointer-events:none;}
.parallax__pin.i3-parallax-complete .parallax__header {display:none;}
.i3-page-body {position:relative;z-index:2;background:transparent;margin-top:0;padding-top:28px;}
.i3-page-body {animation:i3SectionIn .58s cubic-bezier(.22,1,.36,1) both;}
@keyframes i3SectionIn {from{opacity:0;transform:translate3d(0,18px,0)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){.i3-page-body{animation:none}}
.sweep3-sweep-action {display:flex;align-items:center;gap:12px;margin:0 0 16px;padding:12px 14px;border:1px solid var(--i3-border);border-radius:12px;background:rgba(8,20,44,.72);}
.i3-page3-document {max-width:1500px;margin:0 auto;border-top:1px solid var(--i3-border);}
.i3-page3-section {padding:34px 0;border-bottom:1px solid var(--i3-border);}
.i3-page3-section>h2 {margin:0 0 7px;color:var(--i3-ink);font:600 clamp(18px,2vw,25px) Inter,sans-serif;letter-spacing:-.02em;}
.i3-page3-section>p {margin:0 0 20px;color:var(--i3-muted);font:13px/1.7 var(--i3-mono);}
.i3-page3-summary {margin:30px 0 8px;}
.i3-page3-overview {padding-top:24px}.i3-page3-definitions {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:18px;}
.i3-page3-definition {display:grid;gap:7px;padding:16px;border:1px solid var(--i3-border);border-radius:10px;background:rgba(8,20,44,.58);}
.i3-page3-definition b {font:700 10px var(--i3-mono);letter-spacing:.18em;color:var(--i3-accent)}.i3-page3-definition span {font:13px/1.55 var(--i3-font);color:var(--i3-ink)}
@media(max-width:700px){.i3-page3-definitions{grid-template-columns:1fr}}
.nvtra-source-items {display:flex;flex-wrap:wrap;gap:6px;margin-top:10px;}
.nvtra-source-item {display:grid!important;width:min(230px,100%)!important;gap:3px;padding:6px 8px;border:1px solid var(--i3-border);border-radius:5px;background:rgba(29,78,216,.10);color:var(--i3-muted);font:9px/1.25 var(--i3-mono);}
.nvtra-source-item b {color:var(--i3-ink);font-size:9px}.nvtra-source-item small {color:var(--i3-muted);font-size:8px;line-height:1.35}
.i3-page-body::before {display:none;}
.parallax__header {position:sticky;top:0;height:100vh;height:100svh;width:100vw;margin:0;overflow:hidden;background:transparent;}
.parallax__veil {display:none;position:absolute;inset:0;z-index:6;pointer-events:none;opacity:0;background:none;backdrop-filter:blur(calc(var(--i3-scroll,0) * 10px));-webkit-backdrop-filter:blur(calc(var(--i3-scroll,0) * 10px));transition:opacity .2s;}
.parallax__layer-img {transform:translate3d(-50%,-50%,0);backface-visibility:hidden;}
.parallax__visuals {position:absolute;inset:0;}
.parallax__layers {position:absolute;inset:0;will-change:transform,opacity;transform-origin:50% 45%;}
.parallax__layer-img,.parallax__layer-title {position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);will-change:transform;}
.parallax__layer-img {pointer-events:none;object-fit:cover;width:100%;height:130%;min-width:100%;}
.parallax__layer-title {width:auto;text-align:center;white-space:nowrap;z-index:3;}
.i3-page .parallax__title,.parallax__title {margin:0;font-family:'DM Mono',monospace;font-size:clamp(38px,7vw,96px);font-weight:500;letter-spacing:-.05em;line-height:1;color:var(--i3-ink);text-shadow:0 8px 40px rgba(0,0,0,.35);}
.parallax__black-line-overflow {display:none;}
.parallax__fade {display:none;}
.parallax__header + header {opacity:0;transform:translateY(40px);transition:opacity .25s,transform .25s;will-change:opacity,transform;position:relative;z-index:2;}
.parallax__header + header {display:none;}
/* CH3 sweep layout and instrument sliders */
.ch3-layout {display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px;margin:18px 0;align-items:stretch;}
.ch3-guide {display:grid;gap:10px;align-content:start;}
.ch3-guide .summary-panel {height:100%;}
.ch3-controls {display:grid;gap:0;padding:16px 18px;align-content:start;}
.ch3-controls .ch3-dev-strip {margin-top:6px;}
.ch3-controls .ch3-ctl-bar {background:transparent!important;border:0!important;padding:0!important;box-shadow:none!important;}
@media(max-width:980px){.ch3-layout{grid-template-columns:1fr;}}
.i3-page .c1-slider-wrap,.c1-slider-wrap {padding:26px 26px 30px!important;border-radius:14px!important;}
.c1-slider-wrap::before {top:9px!important;left:22px!important;}
.c1-slider-wrap::after {display:none!important;}
.c1-slider-wrap .dash-slider-container {padding:8px 6px 26px!important;min-height:40px!important;}
.c1-slider-wrap .dash-slider-root,.c1-slider-wrap .rc-slider {height:8px!important;margin:0 10px!important;padding:0!important;position:relative;}
/* Dash draws its track from the handle to the right; painting the rail as the fill and the track as the remainder keeps the filled part on the left. */
.c1-slider-wrap .dash-slider-rail,.c1-slider-wrap .rc-slider-rail {height:8px!important;top:0!important;border-radius:999px!important;background:linear-gradient(90deg,#1d4ed8,#22d3ee)!important;box-shadow:0 0 12px rgba(34,211,238,.35)!important;}
.c1-slider-wrap .dash-slider-track,.c1-slider-wrap .rc-slider-track {height:8px!important;top:0!important;border-radius:0 999px 999px 0!important;background:rgba(9,18,36,.92)!important;box-shadow:none!important;}
.c1-slider-wrap .dash-slider-handle,.c1-slider-wrap .rc-slider-handle {width:22px!important;height:22px!important;top:0!important;margin-top:-7px!important;margin-left:-11px!important;border:2px solid #22d3ee!important;background:radial-gradient(circle at 40% 35%,#e0f2fe,#38bdf8 55%,#0e7490)!important;box-shadow:0 0 0 4px rgba(34,211,238,.18),0 0 18px rgba(34,211,238,.6)!important;opacity:1!important;transform:none!important;}
.c1-slider-wrap .dash-slider-handle:active,.c1-slider-wrap .rc-slider-handle:active {box-shadow:0 0 0 8px rgba(34,211,238,.22),0 0 24px rgba(34,211,238,.8)!important;}
.c1-slider-wrap .dash-slider-step,.c1-slider-wrap .rc-slider-step {height:8px!important;top:0!important;}
.c1-slider-wrap .dash-slider-dot,.c1-slider-wrap .rc-slider-dot {width:6px!important;height:6px!important;bottom:auto!important;top:1px!important;margin-left:-3px!important;border:1px solid rgba(120,150,190,.5)!important;background:#0b1220!important;}
.c1-slider-wrap .dash-slider-dot-active,.c1-slider-wrap .rc-slider-dot-active {border-color:#22d3ee!important;background:#22d3ee!important;}
.c1-slider-wrap .dash-slider-mark,.c1-slider-wrap .rc-slider-mark {top:16px!important;}
.c1-slider-wrap .dash-slider-mark-text,.c1-slider-wrap .rc-slider-mark-text {font:600 9px var(--i3-mono)!important;letter-spacing:.14em;color:#7d8ea8!important;transform:translateX(-50%)!important;}
.c1-slider-wrap .dash-slider-mark-text-active,.c1-slider-wrap .rc-slider-mark-text-active {color:#22d3ee!important;}
/* Cards rotate slider */
.i3-rotate {position:relative;width:100vw;margin:24px 0 24px calc(50% - 50vw);overflow-x:clip;}
.i3-rotate-sticky {position:sticky;top:0;height:100vh;height:100svh;display:flex;align-items:center;overflow:hidden;perspective:1200px;}
.i3-rotate-eyebrow {position:absolute;top:84px;left:clamp(16px,4vw,48px);}
.i3-rotate-hint {position:absolute;bottom:22px;left:50%;transform:translateX(-50%);font:600 10px var(--i3-mono);letter-spacing:.14em;text-transform:uppercase;color:var(--i3-muted);padding:8px 14px;border:1px solid var(--i3-border);border-radius:999px;background:color-mix(in srgb,var(--i3-bg) 60%,transparent);}
.i3-rotate-track {display:flex;align-items:center;height:100%;gap:5vw;padding:0 31vw;transform-style:preserve-3d;will-change:transform;}
.i3-rotate-wrap {position:relative;display:flex;align-items:center;justify-content:center;flex:0 0 auto;width:38vw;height:45vh;transform-style:preserve-3d;}
.i3-rotate-card {position:absolute;inset:0;transform-origin:right center;overflow:hidden;border-radius:14px;border:1px solid rgba(147,197,253,.25);box-shadow:0 30px 60px rgba(2,6,23,.6);background:#050b16;transform-style:preserve-3d;will-change:transform,opacity;}
.i3-rotate-img {position:absolute;inset:0;width:100%;height:100%;object-fit:cover;}
.i3-rotate-caption {position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);display:grid;gap:6px;justify-items:center;color:#f5f5f5;text-align:center;font:600 clamp(18px,1.6vw,30px) var(--i3-font);letter-spacing:-.02em;text-shadow:0 .15vw .35vw rgba(0,0,0,.35),0 .45vw 1.2vw rgba(0,0,0,.35);white-space:nowrap;}
.i3-rotate-index {font:600 11px var(--i3-mono);letter-spacing:.2em;color:#93c5fd;}
@media(max-width:1025px){.i3-rotate-track{gap:8vw;padding:0 22vw;} .i3-rotate-wrap{width:55vw;height:40vh;}}
@media(max-width:640px){.i3-rotate-track{gap:12vw;padding:0 12vw;} .i3-rotate-wrap{width:75vw;height:35vh;}}
/* Particle nebula background for the Page 3 page */
/* the system pointer is hidden only in IV-cursor mode (see html.i3-cursor below) */
.i3-hand-vision-status {display:none!important;}
.i3-lunar-card {display:grid;grid-template-columns:minmax(220px,.9fr) minmax(0,1.3fr);gap:0;padding:0!important;overflow:hidden;min-height:440px;background:#000!important;border-color:rgba(255,255,255,.08)!important;border-radius:28px;box-shadow:0 30px 100px rgba(0,0,0,.4);margin-top:16px;}
.i3-lunar-text {display:flex;flex-direction:column;justify-content:center;padding:40px 24px 40px 44px;position:relative;z-index:2;pointer-events:none;background:linear-gradient(90deg,#000 55%,rgba(0,0,0,0));}
.i3-lunar-title {font-size:clamp(48px,6vw,80px);font-weight:700;letter-spacing:-.045em;line-height:.9;margin:0 0 20px;}
.i3-lunar-t1 {color:#fafafa;} .i3-lunar-t2 {background:linear-gradient(180deg,#fff,#a1a1aa 50%,#27272a);-webkit-background-clip:text;background-clip:text;color:transparent;}
.i3-lunar-copy {font-size:15px;line-height:1.6;color:#a1a1aa;max-width:340px;margin:0 0 14px;font-weight:500;}
.i3-lunar-meta {font:11px var(--i3-mono);letter-spacing:.18em;text-transform:uppercase;color:#52525b;}
.i3-lunar-open {position:relative;width:100vw;margin:-24px 0 8px calc(50% - 50vw);height:clamp(380px,56vh,620px);background:transparent;}
.i3-lunar-open .i3-lunar-stage {min-height:0;height:100%;}
.i3-lunar-stage {position:relative;min-height:440px;} .i3-lunar-canvas {position:absolute;inset:0;width:100%!important;height:100%!important;display:block;cursor:grab;touch-action:none;}
.i3-lunar-canvas.i3-rotating {outline:none;box-shadow:inset 0 0 0 2px rgba(34,211,238,.55);}
@media(max-width:820px){.i3-lunar-card{grid-template-columns:1fr;} .i3-lunar-text{padding:32px 28px 8px;background:none;} .i3-lunar-stage{min-height:360px;}}
#i3-finger-cursor {position:fixed;left:0;top:0;width:26px;height:26px;margin:-13px 0 0 -13px;border-radius:50%;border:1.5px solid #22d3ee;box-shadow:0 0 14px rgba(34,211,238,.55),inset 0 0 8px rgba(34,211,238,.2);pointer-events:none;z-index:2147483647;opacity:0;transition:opacity .2s,width .12s,height .12s,margin .12s,border-color .12s;will-change:transform;}
#i3-finger-cursor.hover {width:40px;height:40px;margin:-20px 0 0 -20px;border-color:#7dd3fc;}
#i3-finger-cursor .i3-cursor-dot {position:absolute;left:50%;top:50%;width:6px;height:6px;margin:-3px 0 0 -3px;padding:0;border:0;border-radius:50%;background:#22d3ee;box-shadow:none;}
#i3-finger-cursor::before,#i3-finger-cursor::after,#i3-finger-cursor .i3-cursor-dot::before,#i3-finger-cursor .i3-cursor-dot::after {content:none!important;}
html.i3-cursor #i3-finger-cursor {background:transparent;filter:none;}
.d4-section {display:flex;flex-direction:column;gap:14px;padding:6px 0 40px;}
.d4-hero {padding:6px 0 4px;}
.d4-headline {display:flex!important;flex-direction:row!important;flex-wrap:wrap;gap:14px;align-items:flex-end;width:100%;}
.d4-big {flex:1 1 150px;min-width:120px;padding:12px 16px;border:1px solid rgba(255,255,255,.08);border-radius:14px;background:rgba(8,14,26,.55);}
.d4-big-k {font:9px 'DM Mono',monospace;letter-spacing:.28em;color:#7d8ea8;}
.d4-big-v {font:600 34px/1.1 'DM Mono',monospace;color:#00e5ff;margin-top:4px;} .d4-big-v.small{font-size:16px;color:#e8eeff;}
.d4-weights {flex-basis:100%;}
/* minmax(360px,1fr) cannot go below its floor, so on a 343px phone the track stayed
   360px and every D4 card overflowed its section. min(360px,100%) lets the floor
   collapse to the container on narrow screens and behaves identically above it. */
.d4-grid {display:grid;gap:14px;} .d4-grid.two{grid-template-columns:repeat(auto-fit,minmax(min(360px,100%),1fr));} .d4-grid.three{grid-template-columns:repeat(auto-fit,minmax(min(300px,100%),1fr));} .d4-grid.one{grid-template-columns:1fr;}
.d4-card {min-width:0;}
.d4-table {width:100%;border-collapse:collapse;font:11.5px/1.5 'DM Mono',monospace;margin-top:6px;}
.d4-table td {padding:5px 8px 5px 0;vertical-align:top;border-bottom:1px solid rgba(255,255,255,.05);}
.d4-k {color:#7d8ea8;white-space:nowrap;width:34%;letter-spacing:.04em;} .d4-v {color:#e8eeff;word-break:break-word;}
.d4-bar-row {display:grid;grid-template-columns:86px 1fr 48px 70px;gap:8px;align-items:center;margin:6px 0;font:11px 'DM Mono',monospace;color:#c9d4e6;}
.d4-bar {height:10px;border-radius:5px;background:rgba(255,255,255,.06);overflow:hidden;} .d4-bar i{display:block;height:100%;background:linear-gradient(90deg,#2979ff,#00e5ff);transition:width .5s;}
.d4-bar-val {text-align:right;color:#00e5ff;} .d4-bar-z{color:#7d8ea8;}
.d4-line {font:12px/1.5 'DM Mono',monospace;color:#e8eeff;margin:8px 0 4px;}
.d4-list {margin:4px 0 6px 16px;padding:0;font:11.5px/1.6 'DM Mono',monospace;color:#c9d4e6;}
.d4-pre {white-space:pre-wrap;font:12px/1.55 'DM Mono',monospace;color:#e8eeff;background:rgba(0,0,0,.25);border:1px solid rgba(255,255,255,.06);border-radius:10px;padding:10px 12px;margin:8px 0;} .d4-pre.small{font-size:10.5px;color:#aebdd2;}
.d4-event {padding:8px 0;border-bottom:1px solid rgba(255,255,255,.05);font:11.5px 'DM Mono',monospace;color:#e8eeff;}
#i3-buddy {position:fixed;left:0;top:0;width:220px;height:380px;pointer-events:none;z-index:2147483000;opacity:0;transition:opacity .8s,filter .3s;will-change:transform;filter:drop-shadow(0 14px 22px rgba(0,0,0,.55));}
/* The body stays click-through, but the character itself is a target: clicking it
   with the finger cursor is what puts it in gesture-mirroring mode. */
#i3-buddy.on canvas {pointer-events:auto;cursor:pointer;}
#i3-buddy.i3-buddy-engaged {filter:drop-shadow(0 14px 22px rgba(0,0,0,.55)) drop-shadow(0 0 26px rgba(125,211,252,.85));}
#i3-buddy.i3-buddy-engaged #i3-buddy-label {opacity:1;transform:none;}
#i3-buddy.on {opacity:1;}
#i3-buddy.on.i3-buddy-home {opacity:.58;}
#i3-buddy:not(.on) {opacity:0;}
#i3-buddy.i3-buddy-alert {filter:drop-shadow(0 14px 22px rgba(0,0,0,.55)) drop-shadow(0 0 25px rgba(255,171,64,.72));}
#i3-buddy-label {position:absolute;right:96%;top:18%;width:max-content;max-width:260px;padding:8px 11px;border:1px solid var(--i3-border);border-radius:9px;background:rgba(5,12,24,.92);color:var(--i3-ink);font:600 10px/1.45 var(--i3-mono);letter-spacing:.08em;text-transform:uppercase;opacity:0;transform:translateX(8px);transition:opacity .25s,transform .25s;box-shadow:var(--i3-shadow);}
#i3-buddy.i3-buddy-alert #i3-buddy-label,#i3-buddy.i3-buddy-guide #i3-buddy-label {opacity:1;transform:none;}
#i3-buddy.listening {filter:drop-shadow(0 14px 22px rgba(0,0,0,.55)) drop-shadow(0 0 18px rgba(34,211,238,.55));}
#i3-buddy.talking {filter:drop-shadow(0 14px 22px rgba(0,0,0,.55)) drop-shadow(0 0 22px rgba(165,243,252,.8));}
#i3-buddy canvas {display:block;width:100%!important;height:100%!important;background:transparent;}
body.intro-active #i3-buddy {opacity:0!important;}
.nvtra-spline-host {pointer-events:auto;}
@media(max-width:700px){#i3-buddy{display:none;}}
#i3-finger-cursor.visible {opacity:1;}
/* MAC mode: the hand steers a macOS-style arrow (a web page cannot move the OS pointer itself). */
html:not(.i3-cursor) #i3-finger-cursor {width:22px;height:30px;margin:-2px 0 0 -3px;border:0;border-radius:0;box-shadow:none;background:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 22 30'><path d='M3 2 L3 24 L8.5 18.8 L12.3 27.5 L16.2 25.8 L12.5 17.2 L20 17.2 Z' fill='white' stroke='black' stroke-width='1.6' stroke-linejoin='round'/></svg>") no-repeat center/contain;filter:drop-shadow(0 1px 2px rgba(0,0,0,.6));}
html:not(.i3-cursor) #i3-finger-cursor .i3-cursor-dot {display:none;}
html:not(.i3-cursor) #i3-finger-cursor.hover {width:24px;height:33px;margin:-2px 0 0 -3px;filter:drop-shadow(0 0 6px rgba(34,211,238,.8));}
html:not(.i3-cursor) #i3-finger-cursor.click {width:20px;height:27px;margin:-2px 0 0 -3px;background-color:transparent;}
html.i3-cursor,html.i3-cursor *,html.i3-cursor *::before,html.i3-cursor *::after {cursor:none!important;}
html.i3-cursor #i3-finger-cursor {opacity:1;}
@media(hover:none){html,body,a,button,input,select,textarea,summary,label,[role=button]{cursor:auto!important;} #i3-finger-cursor:not(.on){display:none;}}
#i3-finger-cursor.click {width:22px;height:22px;margin:-11px 0 0 -11px;background:rgba(34,211,238,.35);}
/* camera preview: cool instrument tint, no geometric distortion */
.i3-hand-vision-preview {width:300px!important;height:225px!important;border-radius:14px!important;overflow:hidden!important;border:1px solid rgba(34,211,238,.6)!important;animation:i3Ch2 2.2s ease-in-out infinite;}
@keyframes i3Ch2 {0%,100%{box-shadow:0 0 0 2px rgba(34,211,238,.25),0 0 22px rgba(34,211,238,.55),0 0 60px rgba(34,211,238,.25),0 20px 50px rgba(0,0,0,.5);}50%{box-shadow:0 0 0 2px rgba(125,211,252,.45),0 0 32px rgba(34,211,238,.85),0 0 90px rgba(34,211,238,.35),0 20px 50px rgba(0,0,0,.5);}}
.i3-hand-vision-preview::after {content:'';position:absolute;inset:0;pointer-events:none;border-radius:14px;background:linear-gradient(120deg,transparent 30%,rgba(34,211,238,.18) 50%,transparent 70%) 0 0/300% 100%;animation:i3Arc 3s linear infinite;}
@keyframes i3Arc {from{background-position:150% 0}to{background-position:-150% 0}}
.i3-cam-hud {position:absolute;left:10px;top:10px;z-index:3;padding:6px 10px;border-radius:8px;background:rgba(2,6,23,.6);color:#7dd3fc;font:600 11px var(--i3-mono);letter-spacing:.06em;pointer-events:none;}
@media(max-width:600px){.i3-hand-vision-preview{width:220px!important;height:165px!important;}}
/* NVTRA agent orb */
#i3-orb {position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:2147483004;display:grid;gap:10px;width:min(680px,94vw);padding:12px 16px;border-radius:30px;background:rgba(10,12,18,.86);border:1px solid rgba(255,255,255,.08);box-shadow:0 30px 70px rgba(0,0,0,.6),inset 0 1px 0 rgba(255,255,255,.06);backdrop-filter:blur(30px) saturate(160%);-webkit-backdrop-filter:blur(30px) saturate(160%);color:#f5f5f7;text-align:left;transition:width .5s cubic-bezier(.34,1.3,.64,1),padding .45s cubic-bezier(.34,1.3,.64,1),border-radius .45s,transform .45s cubic-bezier(.34,1.3,.64,1),box-shadow .4s;transform-origin:50% 100%;}
#i3-orb.collapsed {width:auto;min-width:210px;padding:7px 16px 7px 8px;border-radius:999px;cursor:pointer;box-shadow:0 12px 30px rgba(0,0,0,.5),inset 0 1px 0 rgba(255,255,255,.06);}
#i3-orb.collapsed:hover {transform:translateX(-50%) scale(1.03);}
#i3-orb.collapsed .i3-orb-text,#i3-orb.collapsed .i3-orb-form,#i3-orb.collapsed .i3-island-pills .i3-island-pill:not(.pill-mtdi),#i3-orb.collapsed .i3-voice-bars {display:none;}
#i3-orb.hidden {transform:translate(-50%,140%);}
#i3-orb .i3-orb-text,#i3-orb .i3-orb-form {animation:i3IslandIn .45s cubic-bezier(.2,.8,.2,1) both;}
@keyframes i3IslandIn {from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.i3-island-top {display:flex;align-items:center;gap:12px;}
#i3-orb-canvas {width:44px;height:44px;flex:0 0 44px;filter:drop-shadow(0 0 10px rgba(59,130,246,.55));}
#i3-orb:not(.collapsed) #i3-orb-canvas {width:64px;height:64px;flex-basis:64px;}
.i3-orb-robot {width:64px;height:64px;flex:0 0 64px;} .i3-orb-robot[hidden]{display:none;} .i3-orb-robot .nvtra-spline-host,.i3-orb-robot canvas{width:100%!important;height:100%!important;}
.i3-island-head {display:grid;gap:2px;min-width:0;}
.i3-orb-name {font:600 10px var(--i3-mono);letter-spacing:.32em;color:#67e8f9;}
.i3-orb-state {font:12px var(--i3-font);color:#94a3b8;min-height:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.i3-island-pills {display:flex;gap:6px;margin-left:auto;flex-wrap:wrap;justify-content:flex-end;}
.i3-island-pill {display:inline-flex;align-items:center;gap:7px;padding:6px 12px;border-radius:999px;border:0;background:rgba(255,255,255,.08);font:600 10px var(--i3-mono);letter-spacing:.1em;color:#f5f5f7;white-space:nowrap;}
.i3-island-pill .pill-key {color:#98a2b3;}
.i3-orb-name {color:#8ee7ff;} .i3-orb-state {color:#98a2b3;}
.i3-orb-form input {background:rgba(255,255,255,.07)!important;border:1px solid rgba(255,255,255,.08)!important;color:#f5f5f7!important;border-radius:14px!important;}
.i3-orb-form .i3-btn {border-radius:14px;}
.i3-island-pill .pill-key {color:#7d8ea8;} .i3-island-pill .pill-val {font-variant-numeric:tabular-nums;}
.i3-island-pill .pill-dot {width:6px;height:6px;border-radius:50%;background:#7d8ea8;} .i3-island-pill .pill-dot.pill-ok{background:#6fddb2;} .i3-island-pill .pill-dot.pill-warn{background:#f2c778;} .i3-island-pill .pill-dot.pill-high{background:#ff9995;} .i3-island-pill .pill-dot.pill-off{background:#5b6b7f;}
.i3-orb-text {font:15px/1.4 var(--i3-font);font-weight:600;letter-spacing:-.01em;min-height:20px;max-height:66px;overflow:auto;}
.i3-orb-text.guess {opacity:.55;font-style:italic;font-weight:500;}
.i3-orb-form {display:flex;gap:8px;}
.i3-orb-tools {display:flex;gap:8px;align-items:center;margin-top:8px;}
#i3-orb.collapsed .i3-orb-tools {display:none;}
.i3-orb-engine {flex:1;min-width:0;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.08);color:#f5f5f7;border-radius:12px;padding:7px 10px;font:12px var(--i3-mono);letter-spacing:.04em;}
.i3-orb-engine option {color:#0b1220;}
.i3-orb-stop {border-radius:12px;background:rgba(255,82,82,.14)!important;border:1px solid rgba(255,82,82,.35)!important;color:#ffb4b4!important;}
.i3-orb-form input {flex:1;min-height:36px;border-radius:10px;border:1px solid rgba(96,165,250,.35);background:rgba(2,6,23,.6);color:#e2e8f0;padding:0 14px;font:14px var(--i3-font);}
.i3-tool[aria-pressed=true]#i3-agent-toggle {color:#22d3ee;border-color:#22d3ee;box-shadow:0 0 10px #22d3ee;}
#i3-nebula {position:fixed;inset:0;width:100vw;height:100vh;height:100dvh;z-index:0;pointer-events:none;opacity:0;transition:opacity .8s;}
#i3-nebula.on {opacity:1;}
.i3-page {max-width:1240px;margin:auto;padding:104px clamp(16px,3vw,30px) 60px;font-family:var(--i3-font);color:var(--i3-ink);}
.i3-pillars,.i3-pillars .i3-card,.i3-pillars .i3-row,.i3-pillars .i3-value {font-family:var(--i3-font);}
.i3-hand-vision-status{z-index:2147483001;}
/* Light mode, toned down: soft grey blue surfaces instead of white on white. */
.i3-eyebrow {color:var(--i3-accent);font:600 11px var(--i3-mono);letter-spacing:.15em;text-transform:uppercase;}
.i3-page h1 {font-size:clamp(32px,4vw,48px);line-height:1.1;font-weight:650;letter-spacing:-.04em;margin:14px 0;font-family:var(--i3-font);}
.i3-page h2 {font-size:21px;font-weight:600;letter-spacing:-.02em;margin:0 0 8px;}
.i3-page h3 {font-size:16px;margin:0 0 16px;font-weight:650;}
.i3-page .i3-eyebrow {font-family:var(--i3-mono);}
.i3-page p {color:var(--i3-muted);line-height:1.65;}
.i3-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin:18px 0;}
.i3-channels {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:18px 0;}
.i3-card {color:var(--i3-ink);padding:18px 20px;height:360px;overflow:auto;contain:strict;content-visibility:auto;}
.i3-card-title {margin-bottom:12px;}
.i3-summary {background:rgba(16,23,38,0.74);border:1px solid rgba(255,255,255,0.07);box-shadow:none;border-radius:16px;}
.i3-card.compact {height:300px;}
.i3-card.tall {height:510px;}
.i3-card.wide {grid-column:1/-1;}
.i3-audio-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:12px;}
.i3-audio-grid.three {grid-template-columns:repeat(3,minmax(0,1fr));}
@media(max-width:1100px){.i3-audio-grid.three {grid-template-columns:repeat(2,minmax(0,1fr));}}
@media(max-width:760px){.i3-audio-grid {grid-template-columns:1fr;} .i3-card.wide.tall{height:auto;min-height:510px;}}
.i3-summary {height:264px;display:grid;grid-template-columns:1fr 210px;gap:24px;align-items:center;padding:24px;overflow:auto;contain:strict;}
.i3-summary>div:first-child {height:192px;overflow:auto;}
.header-pills {contain:layout style;height:28px;}
.pill-mtdi .pill-val {width:4ch;text-align:right;}
.pill-ch3 .pill-val {width:12ch;text-align:right;}
.metric-value {min-height:1em;}
.i3-condition {font-size:clamp(23px,3vw,34px);line-height:1.2;letter-spacing:-.025em;font-weight:600;}
.i3-summary .i3-condition {height:82px;overflow:auto;}
.i3-confidence {text-align:center;border-left:1px solid var(--i3-border);padding-left:24px;}
.i3-confidence strong {display:block;font:500 40px var(--i3-mono);color:var(--i3-accent);font-variant-numeric:tabular-nums;white-space:nowrap;}
.i3-value {font:500 29px var(--i3-mono);letter-spacing:-.045em;font-variant-numeric:tabular-nums;color:var(--i3-ink);margin:14px 0 6px;min-height:38px;}
.i3-value>span {display:block;height:36px;white-space:nowrap;overflow:hidden;}
.i3-value>span:last-child {height:20px;font:12px var(--i3-font);letter-spacing:0;color:var(--i3-muted);}
.i3-row {display:flex;justify-content:space-between;gap:16px;border-bottom:1px solid var(--i3-border);padding:9px 0;line-height:1.45;font-size:12px;}
.i3-row>span:last-child {text-align:right;overflow-wrap:anywhere;font-variant-numeric:tabular-nums;}
.i3-label {color:var(--i3-muted);}
.i3-state {color:var(--i3-accent);font:600 10px var(--i3-mono);text-transform:uppercase;letter-spacing:.07em;}
.i3-evidence {height:72px;overflow:auto;margin-top:12px;line-height:1.55;color:var(--i3-muted);font-size:13px;}
.i3-form {display:flex;align-items:end;gap:10px;flex-wrap:wrap;margin:14px 0;}
.i3-form label {display:flex;flex-direction:column;gap:7px;font-size:12px;flex:1;min-width:120px;color:var(--i3-muted);}
.i3-form :is(input,select) {border:1px solid var(--i3-border);border-radius:7px;min-height:44px;padding:8px;max-width:100%;width:100%;}
.i3-inline-result {height:52px;overflow:auto;font-size:12px;line-height:1.6;color:var(--i3-muted);}
.i3-vector {width:100%;height:230px;display:block;touch-action:none;border-radius:8px;background:var(--i3-soft);}
.i3-mini-trace {width:100%;height:58px;display:block;margin:12px 0;}
.i3-breakdown {height:252px;overflow:auto;}
.i3-health {width:100%;border-collapse:collapse;font-size:12px;}
.i3-health th {text-align:left;color:var(--i3-muted);font-weight:500;}
.i3-health td,.i3-health th {padding:11px 8px;border-bottom:1px solid var(--i3-border);}
.i3-details {height:100%;overflow:auto;font:12px/1.7 var(--i3-mono);white-space:pre-wrap;overflow-wrap:anywhere;}
.i3-notice {font-size:12px;line-height:1.65;color:var(--i3-muted);border-left:3px solid var(--i3-accent);padding:2px 14px;margin:16px 0;}
.i3-pillars {border-top:1px solid var(--i3-border);padding-top:20px;margin-top:22px;}
.i3-camera-frame {height:230px;position:relative;border-radius:8px;background:var(--i3-soft);display:grid;place-items:center;}
.i3-camera-frame img {position:absolute;inset:0;}
.i3-camera-preview:not([src]) {display:none;}
.i3-camera-preview {width:100%;height:230px;object-fit:contain;background:var(--i3-soft);border-radius:8px;}
.i3-performance {font:11px var(--i3-mono);color:var(--i3-muted);}
/* The D4 engine moved here from the MTDI orbit, so its cards are styled by the d4-*
   rules in theme.py rather than the i3-* system around them. This host only supplies
   the seam: the section rule's own top margin plus a separating line. */
.i3-d4-host {margin:22px 0 0;padding-top:20px;border-top:1px solid var(--i3-border);}
.i3-d4-host > .i3-eyebrow {margin-bottom:10px;}
.i3-d4-host .d4-section {margin-top:0;}
.i3-d4-host .d4-hero {margin-bottom:18px;}
.i3-meter {width:100%;height:18px;display:block;border-radius:4px;background:var(--i3-soft);}
.i3-audio {display:grid;gap:10px;padding:14px;border:1px solid var(--i3-border);border-radius:10px;background:var(--i3-raised);min-height:196px;contain:layout style;}
.i3-audio h4 {margin:0;font-size:14px;font-weight:650;display:flex;justify-content:space-between;align-items:center;gap:8px;}
.i3-audio .i3-form {margin:0;}
.i3-audio input[type=range] {width:100%;accent-color:var(--i3-accent);min-height:44px;}
.i3-audio audio {width:100%;height:36px;}
.i3-timeline {height:100%;overflow:auto;font:12px/1.7 var(--i3-mono);white-space:pre-wrap;}
.i3-channels.four {grid-template-columns:repeat(4,minmax(0,1fr));}
@media(max-width:1100px){.i3-channels.four {grid-template-columns:repeat(2,minmax(0,1fr));}}
@media(max-width:760px){.i3-channels.four {grid-template-columns:1fr;}}
@media(max-width:760px) {
 html.phone-desktop,html.phone-desktop body {min-width:0!important;width:100%!important;}
 #i3-orb {bottom:calc(76px + env(safe-area-inset-bottom));}  /* sit above the bottom tab bar, not on it */
 /* The phone header is the fixed bottom tab bar defined in studio/theme.py (max-width:760px).
    An older rule here forced it back to the top as a relative, wrapping block, so it overlapped
    the page, which reserves space at the bottom, not the top. */
 .header-pills {min-height:28px;}
 .i3-toolbar {padding:8px 16px;}
 .i3-grid,.i3-channels {grid-template-columns:1fr;}
 .i3-summary {grid-template-columns:1fr;grid-template-rows:206px 60px;gap:12px;height:316px;padding:18px;}
 .i3-summary>div:first-child {height:206px;}
 .i3-confidence {display:flex;align-items:center;justify-content:space-between;border-left:0;border-top:1px solid var(--i3-border);padding:8px 0;height:60px;}
 .i3-confidence strong {font-size:32px;}
 .i3-card {padding:18px;height:360px;}
 .i3-card.tall {height:530px;}
 .i3-page {padding-top:20px;} .i3-toolbar{margin-top:12px!important;}
 :is(.c1-grid,.chart-grid,.validation-live-grid,.sys-grid,.i3-principle-grid) {grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr))!important;}
 .home-module-orbit-stage,.mtdi-orbit-scene {min-width:0!important;width:100%!important;}
 .mtdi-orbit-card.is-expanded {width:100vw!important;}
 .i3-health {font-size:11px;}
}
@media(prefers-reduced-motion:reduce) {
 *,*::before,*::after {animation:none!important;transition:none!important;scroll-behavior:auto!important;}
 #i3-field-background {opacity:.18;}
}
html.no-anim *,html.no-anim *::before,html.no-anim *::after {animation:none!important;transition:none!important;}

/* ── hand calibration + gesture debug ── */
#i3-hand-calib {position:fixed;inset:0;z-index:2147483005;display:grid;place-items:center;background:rgba(3,7,18,.72);backdrop-filter:blur(6px);}
.i3-calib-card {width:min(520px,92vw);padding:26px 28px;border-radius:18px;border:1px solid var(--i3-border);background:var(--i3-surface);color:var(--i3-ink);display:grid;gap:12px;text-align:center;box-shadow:var(--i3-shadow);}
.i3-calib-kicker {font:600 10px var(--i3-mono);letter-spacing:.3em;color:var(--i3-accent);}
.i3-calib-step {font:700 20px var(--i3-mono);letter-spacing:.12em;}
.i3-calib-hint {font:14px/1.5 var(--i3-font);color:var(--i3-muted);}
.i3-calib-bar {height:6px;border-radius:999px;background:var(--i3-border);overflow:hidden;}
.i3-calib-bar i {display:block;height:100%;width:0;background:var(--i3-accent);transition:width .1s linear;}
.i3-calib-seen {font:600 10px var(--i3-mono);letter-spacing:.16em;color:var(--i3-muted);}
.i3-hand-profiles {display:grid;gap:6px;}
.i3-hp-row {display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:8px 12px;border:1px solid var(--i3-border);border-radius:10px;background:var(--i3-soft);}
.i3-hp-row.on {border-color:rgba(49,215,230,.55);}
.i3-hp-name {font:600 12px var(--i3-mono);letter-spacing:.06em;color:var(--i3-ink);} .i3-hp-name i {font-style:normal;font-size:9px;color:var(--i3-accent);letter-spacing:.2em;margin-left:6px;}
.i3-hp-meta {font:11px var(--i3-mono);color:var(--i3-muted);flex:1;}
.i3-hp-acts {display:flex;gap:6px;} .i3-hp-acts button {font:600 10px var(--i3-mono);letter-spacing:.12em;padding:6px 10px;border-radius:7px;border:1px solid var(--i3-border);background:var(--i3-raised);color:var(--i3-ink);cursor:pointer;} .i3-hp-acts button:hover {border-color:var(--i3-accent);}
/* ── Sensor showcase (Home): spatial product layout, left/right switcher, 3D models ── */
.i3-showcase {margin:0 auto;max-width:1180px;padding:10px 0 60px;}
.i3-sc-sub {text-align:center;color:var(--i3-muted);font:14px/1.5 var(--i3-font);margin:8px 0 34px;}
.i3-sc-stage {display:flex;align-items:center;justify-content:center;gap:clamp(28px,6vw,120px);min-height:480px;transition:flex-direction 0s;}
.i3-sc-stage[data-i3-showcase="ch2"] {}
.i3-sc-visual {position:relative;width:min(440px,80vw);aspect-ratio:1;flex-shrink:0;display:grid;place-items:center;}
.i3-sc-zoom {position:absolute;right:4%;bottom:4%;z-index:3;display:flex;flex-direction:column;gap:6px;}
.i3-sc-zoom button {width:34px;height:34px;border-radius:50%;border:1px solid rgba(255,255,255,.14);background:rgba(8,14,26,.72);color:#d8faff;font:600 16px/1 system-ui,sans-serif;cursor:pointer;backdrop-filter:blur(8px);transition:background .18s,transform .18s;}
.i3-sc-zoom button:hover {background:rgba(49,215,230,.22);transform:scale(1.06);}
.i3-sc-canvas {position:relative;z-index:2;touch-action:none;cursor:grab;width:100%;height:100%;border-radius:50%;border:1px solid rgba(255,255,255,.06);background:rgba(0,0,0,.18);box-shadow:0 30px 80px rgba(0,0,0,.45);}
/* The two real boards need a rectangle: one is 14 mm square and the other is
   45 x 112 mm, so a circular frame would crop the tall one badly. The ring and
   glow behind it stay circular and read as a lens behind the hardware. */
.i3-sc-boards {position:relative;z-index:2;touch-action:none;cursor:grab;width:100%;height:100%;
  border-radius:18px;border:1px solid rgba(255,255,255,.07);background:rgba(4,10,18,.35);
  box-shadow:0 30px 80px rgba(0,0,0,.45);display:block;}
.i3-sc-boards:active {cursor:grabbing;}
.home-globe-research[hidden]{display:none}.home-globe-research {position:absolute;left:50%;bottom:-58px;translate:-50% 0;width:min(360px,88vw);min-height:48px;padding:9px 12px;border:1px solid var(--i3-border);border-radius:10px;background:rgba(5,12,24,.9);box-shadow:var(--i3-shadow);text-align:left;pointer-events:none;z-index:8;}
.home-globe-research b {display:block;font:700 8px var(--i3-mono);letter-spacing:.2em;color:var(--i3-accent);margin-bottom:4px}.home-globe-research span {display:block;font:10px/1.45 var(--i3-mono);color:var(--i3-muted);}
@media(max-width:700px){.home-globe-research{bottom:-72px}}
.i3-sc-visual:has(.i3-sc-boards) {width:min(560px,88vw);aspect-ratio:4/3;}
.i3-sc-visual-split {width:min(680px,92vw)!important;aspect-ratio:auto!important;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;align-items:stretch;}
.i3-sc-board-slot {height:360px;min-width:0;display:grid;grid-template-rows:auto 1fr;gap:8px;padding:10px;border:1px solid var(--i3-border);border-radius:14px;background:rgba(5,14,30,.62);}
.i3-sc-board-label {font:700 9px/1.2 var(--i3-mono);letter-spacing:.18em;color:var(--i3-muted);text-align:center;}
.i3-sc-board-slot .i3-sc-boards {min-height:0;}
@media(max-width:760px){.i3-sc-visual-split{grid-template-columns:1fr}.i3-sc-board-slot{height:280px}}
/* One board beside the measurement it takes. The canvas has no intrinsic size,
   so the wrapper must carry a real height or boards.js draws into 300x150 and
   the panel looks empty with nothing in the markup to explain why. */
.i3-tab-board {position:relative;width:100%;height:260px;margin-bottom:14px;}
.i3-tab-board canvas {width:100%;height:100%;display:block;touch-action:none;cursor:grab;}
.i3-tab-board canvas:active {cursor:grabbing;}
@media(max-width:760px){.i3-tab-board{height:200px;}}
.i3-sc-ring {position:absolute;inset:-14%;border-radius:50%;border:1px dashed rgba(255,255,255,.12);animation:i3ScSpin 26s linear infinite;pointer-events:none;}
.i3-sc-stage[data-i3-showcase="ch1"] .i3-sc-ring {border-left-color:rgba(49,215,230,.55);}
.i3-sc-stage[data-i3-showcase="ch2"] .i3-sc-ring {border-right-color:rgba(0,230,118,.55);}
.i3-sc-glow {position:absolute;inset:6%;border-radius:50%;filter:blur(40px);opacity:.38;animation:i3ScBreathe 4s ease-in-out infinite;pointer-events:none;background:linear-gradient(135deg,#1d5fd6,#0c2a66);transition:background .8s;}
.i3-sc-stage[data-i3-showcase="ch2"] .i3-sc-glow {background:linear-gradient(135deg,#2979ff,#071f4d);}
@keyframes i3ScSpin {to{transform:rotate(360deg)}} @keyframes i3ScBreathe {0%,100%{transform:scale(1)}50%{transform:scale(1.05)}}
.i3-sc-detail-wrap {position:relative;width:min(460px,100%);min-height:420px;}
.i3-sc-details {position:absolute;inset:0;display:flex;flex-direction:column;align-items:flex-start;text-align:left;opacity:0;pointer-events:none;transform:translateY(16px);filter:blur(8px);transition:opacity .35s,transform .5s cubic-bezier(.2,.8,.2,1),filter .5s;}
.i3-sc-details.on {opacity:1;pointer-events:auto;transform:none;filter:none;}
.i3-sc-stage[data-i3-showcase="ch2"] .i3-sc-details {align-items:flex-end;text-align:right;}
.i3-sc-kicker {font:700 10px var(--i3-mono);letter-spacing:.24em;color:var(--i3-muted);margin-bottom:8px;}
.i3-sc-title {margin:0 0 10px;font:600 clamp(28px,3.6vw,44px)/1.05 var(--i3-font);letter-spacing:-.02em;background:linear-gradient(180deg,#fff,#8ea4b5);-webkit-background-clip:text;background-clip:text;color:transparent;}
.i3-sc-desc {margin:0 0 22px;max-width:380px;color:var(--i3-muted);font:14px/1.6 var(--i3-font);}
.i3-sc-panel {width:100%;display:grid;gap:18px;padding:22px;border-radius:18px;border:1px solid rgba(255,255,255,.07);background:rgba(16,23,38,.55);backdrop-filter:blur(6px);}
.i3-sc-frow {display:flex;justify-content:space-between;align-items:center;font:12px var(--i3-mono);color:var(--i3-ink);margin-bottom:8px;}
.i3-sc-stage[data-i3-showcase="ch2"] .i3-sc-frow {flex-direction:row-reverse;}
.i3-sc-flabel {letter-spacing:.06em;} .i3-sc-fvalue {color:var(--i3-muted);font-variant-numeric:tabular-nums;}
.i3-sc-bar {position:relative;height:6px;border-radius:999px;background:rgba(255,255,255,.08);overflow:hidden;}
.i3-sc-bar i {position:absolute;top:0;bottom:0;left:0;width:0;border-radius:999px;background:var(--i3-accent);opacity:.85;transition:width .9s cubic-bezier(.2,.8,.2,1);}
.i3-sc-stage[data-i3-showcase="ch2"] .i3-sc-bar i {left:auto;right:0;background:#00e676;}
.i3-sc-open {display:inline-flex;gap:8px;align-items:center;font:600 11px var(--i3-mono);letter-spacing:.16em;color:var(--i3-ink);text-decoration:none;} .i3-sc-open:hover span:last-child {transform:translateX(4px);} .i3-sc-open span:last-child {transition:transform .2s;}
.i3-sc-stage[data-i3-showcase="ch2"] .i3-sc-open {margin-left:auto;}
.i3-sc-status {margin-top:16px;display:inline-flex;gap:8px;align-items:center;padding:8px 14px;border-radius:999px;border:1px solid rgba(255,255,255,.08);background:rgba(6,12,24,.8);font:600 10px var(--i3-mono);letter-spacing:.18em;text-transform:uppercase;color:var(--i3-muted);}
.i3-sc-dot {color:var(--i3-accent);animation:i3CalibPulse 1.6s ease-in-out infinite;font-size:8px;} .i3-sc-status[data-off] .i3-sc-dot {color:#ffab40;animation:none;}
.i3-sc-switch {display:flex;justify-content:center;margin-top:34px;}
.i3-sc-switch {gap:4px;padding:6px;border-radius:999px;background:rgba(16,23,38,.8);border:1px solid rgba(255,255,255,.1);width:max-content;margin-left:auto;margin-right:auto;box-shadow:0 20px 60px rgba(0,0,0,.5);}
.i3-sc-btn {position:relative;min-width:140px;height:44px;border-radius:999px;border:0;background:transparent;color:var(--i3-muted);font:500 13px var(--i3-font);cursor:pointer;transition:color .3s;}
.i3-sc-btn.on {color:#fff;background:linear-gradient(180deg,rgba(255,255,255,.12),rgba(255,255,255,.05));box-shadow:inset 0 1px 0 rgba(255,255,255,.12);}
.i3-sc-btn.on::after {content:'';position:absolute;left:50%;bottom:-3px;width:24px;height:3px;margin-left:-12px;border-radius:999px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.7),transparent);}
@media(max-width:860px){.i3-sc-stage,.i3-sc-stage[data-i3-showcase="ch2"]{flex-direction:column;} .i3-sc-details,.i3-sc-stage[data-i3-showcase="ch2"] .i3-sc-details{align-items:center;text-align:center;} .i3-sc-detail-wrap{min-height:460px;}}
/* Open MTDI pillar: the nav row sticks just below the site header (it used to slide under it)
   and BACK is a real pill button, on every pillar page */
body.mtdi-detail-open .mtdi-orbit-card.is-expanded .mtdi-detail-nav {top:calc(env(safe-area-inset-top,0px) + 66px);padding:10px 0;background:linear-gradient(180deg,#070a10 70%,rgba(7,10,16,0));border-bottom:0;z-index:40;}
body.mtdi-detail-open .mtdi-orbit-card.is-expanded .mtdi-detail-close {padding:11px 16px;border:1px solid rgba(255,255,255,.14);border-radius:10px;background:rgba(6,12,24,.88);color:var(--i3-ink);font:600 10px var(--i3-mono);letter-spacing:.18em;box-shadow:0 10px 30px rgba(0,0,0,.45);}
body.mtdi-detail-open .mtdi-orbit-card.is-expanded .mtdi-detail-close:hover {border-color:rgba(49,215,230,.6);color:#fff;}
@media(max-width:760px){body.mtdi-detail-open .mtdi-orbit-card.is-expanded .mtdi-detail-nav{top:8px;}}
.i3-calib-demo {width:min(300px,70vw);height:auto;justify-self:center;border-radius:14px;background:radial-gradient(ellipse at 50% 40%,rgba(49,215,230,.10),transparent 70%);}
.i3-calib-status {display:flex;align-items:center;justify-content:center;gap:8px;min-height:18px;}
.i3-calib-dot {width:8px;height:8px;border-radius:50%;background:var(--i3-muted);opacity:.5;}
.i3-calib-dot.scan {background:var(--i3-accent);opacity:1;animation:i3CalibPulse .8s ease-in-out infinite;}
.i3-calib-dot.ok {background:#00e676;opacity:1;box-shadow:0 0 12px #00e676aa;}
.i3-calib-dot.ok + .i3-calib-seen {color:#00e676;}
@keyframes i3CalibPulse {0%,100%{transform:scale(.7);opacity:.5}50%{transform:scale(1.2);opacity:1}}
.i3-calib-steps {display:flex;justify-content:center;gap:6px;flex-wrap:wrap;}
.i3-calib-steps span {font:600 9px var(--i3-mono);letter-spacing:.14em;padding:4px 8px;border-radius:999px;border:1px solid var(--i3-border);color:var(--i3-muted);}
.i3-calib-steps span.now {border-color:var(--i3-accent);color:var(--i3-accent);}
.i3-calib-steps span.done {border-color:#00e67666;color:#00e676;}
.i3-calib-cancel {justify-self:center;padding:10px 18px;border-radius:999px;border:1px solid var(--i3-border);background:transparent;color:var(--i3-ink);font:600 11px var(--i3-mono);letter-spacing:.16em;cursor:pointer;}
#i3-hand-debug {position:fixed;left:14px;bottom:calc(env(safe-area-inset-bottom,0px) + 110px);z-index:2147483004;margin:0;padding:10px 12px;border-radius:10px;border:1px solid var(--i3-border);background:color-mix(in srgb,var(--i3-surface) 88%,transparent);color:var(--i3-ink);font:11px/1.5 var(--i3-mono);white-space:pre;pointer-events:none;max-width:min(560px,92vw);overflow:hidden;}
/* ── NVTRA logo mark ── */
.nvtra-logo-mark {width:60px;height:42px;object-fit:contain;flex-shrink:0;filter:drop-shadow(0 0 10px #d4b25a55);animation:i3LogoIn .9s cubic-bezier(.2,.8,.2,1) both;}
@keyframes i3LogoIn {from{opacity:0;transform:scale(.72) rotate(-8deg);filter:drop-shadow(0 0 0 transparent);}to{opacity:1;transform:none;}}
/* ── subtle system notices (Judge detected / EI) ── */
.i3-sys-note {position:fixed;left:50%;top:calc(env(safe-area-inset-top,0px) + 72px);transform:translateX(-50%) translateY(-6px);z-index:2147483005;pointer-events:none;font:500 10px var(--i3-mono);letter-spacing:.2em;text-transform:uppercase;color:var(--i3-muted);padding:7px 14px;border:1px solid var(--i3-border);border-radius:999px;background:color-mix(in srgb,var(--i3-surface) 82%,transparent);backdrop-filter:blur(10px);opacity:0;transition:opacity .35s ease,transform .35s ease;}
.i3-sys-note.on {opacity:1;transform:translateX(-50%) translateY(0);}
.i3-sys-note::before {content:'';display:inline-block;width:5px;height:5px;border-radius:50%;background:var(--i3-accent);margin-right:9px;vertical-align:1px;box-shadow:0 0 8px var(--i3-accent);}
.i3-sys-note.i3-sys-note-big {top:50%;transform:translate(-50%,-50%) scale(.96);font-size:12px;letter-spacing:.16em;text-transform:none;padding:16px 26px;border-radius:14px;color:var(--i3-ink);border-color:color-mix(in srgb,var(--i3-accent) 40%,var(--i3-border));box-shadow:0 0 40px #31d7e622,var(--i3-shadow);max-width:min(88vw,560px);text-align:center;line-height:1.5;}
.i3-sys-note.i3-sys-note-big.on {transform:translate(-50%,-50%) scale(1);}
/* ── Aether terminal ── */
.aether-term-card {border:1px solid var(--i3-border);border-radius:16px;background:linear-gradient(180deg,color-mix(in srgb,var(--i3-surface) 92%,#000) 0%,var(--i3-soft) 100%);box-shadow:var(--i3-shadow);overflow:hidden;position:relative;}
.aether-term-card::before {content:'';position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,transparent 0 3px,#ffffff04 3px 4px);mix-blend-mode:screen;}
.aether-term-head {display:flex;justify-content:space-between;align-items:center;gap:12px;padding:14px 18px;border-bottom:1px solid var(--i3-border);flex-wrap:wrap;}
.aether-term-title {display:block;font:600 11px var(--i3-mono);letter-spacing:.22em;color:var(--i3-ink);}
.aether-term-sub {display:block;font:500 9px var(--i3-mono);letter-spacing:.16em;color:var(--i3-muted);margin-top:4px;}
.aether-term-status {display:flex;align-items:center;gap:8px;font:500 9px var(--i3-mono);letter-spacing:.16em;color:var(--i3-muted);}
.aether-term-led {width:7px;height:7px;border-radius:50%;background:var(--i3-warn);box-shadow:0 0 8px var(--i3-warn);transition:background .3s,box-shadow .3s;}
.aether-term-card.is-ready .aether-term-led {background:var(--i3-good);box-shadow:0 0 8px var(--i3-good);}
.aether-term-card.is-busy .aether-term-led {background:var(--i3-accent);box-shadow:0 0 8px var(--i3-accent);animation:pulseSoft .8s ease-in-out infinite;}
.aether-terminal {padding:14px 18px 12px;cursor:text;}
.aether-term-out {margin:0;min-height:150px;max-height:min(46vh,380px);overflow:auto;font:13px/1.55 var(--i3-mono);color:var(--i3-ink);white-space:pre-wrap;word-break:break-word;scrollbar-width:thin;outline:none;}
.aether-term-out .t-sys {color:var(--i3-accent);}
.aether-term-out .t-dim {color:var(--i3-muted);}
.aether-term-out .t-err {color:var(--i3-error);}
.aether-term-out .t-in {color:var(--i3-good);}
.aether-term-out .t-warn {color:var(--i3-warn);}
.aether-term-line {display:flex;align-items:flex-start;gap:10px;margin-top:8px;padding-top:10px;border-top:1px dashed var(--i3-border);}
.aether-terminal:focus-within .aether-term-in {flex:1;}
.aether-terminal:not(:focus-within) .aether-term-in:placeholder-shown {flex:0 0 auto;width:0;min-width:0;}
.aether-terminal:not(:focus-within) .aether-term-in:not(:placeholder-shown) {flex:0 1 auto;}
.aether-term-prompt {font:600 13px/1.55 var(--i3-mono);color:var(--i3-accent);flex-shrink:0;}
.aether-term-in {flex:1;background:transparent;border:0;outline:none;resize:none;padding:0;margin:0;font:13px/1.55 var(--i3-mono);color:var(--i3-ink);caret-color:var(--i3-accent);min-height:20px;max-height:120px;overflow:auto;}
.aether-term-in:focus,.aether-term-in:focus-visible {outline:none!important;box-shadow:none!important;border:0!important;background:transparent!important;}
.aether-term-in::placeholder {color:color-mix(in srgb,var(--i3-muted) 55%,transparent);}
.aether-term-caret {display:block;width:8px;height:15px;background:var(--i3-accent);opacity:.85;animation:aetherBlink 1.05s steps(1) infinite;pointer-events:none;margin-top:3px;flex-shrink:0;}
.aether-terminal:focus-within .aether-term-caret {display:none;}
@keyframes aetherBlink {0%,49%{opacity:.9}50%,100%{opacity:0}}
.aether-term-foot {display:flex;gap:18px;flex-wrap:wrap;padding:8px 18px 12px;font:500 9px var(--i3-mono);letter-spacing:.14em;color:var(--i3-muted);border-top:1px solid var(--i3-border);}
.aether-nano {border:1px solid var(--i3-border);border-radius:10px;overflow:hidden;background:color-mix(in srgb,var(--i3-soft) 85%,#000);margin-bottom:10px;}
.aether-nano[hidden] {display:none;}
.aether-nano-head,.aether-nano-foot {display:flex;justify-content:space-between;gap:14px;padding:6px 10px;font:600 10px var(--i3-mono);letter-spacing:.14em;background:color-mix(in srgb,var(--i3-accent) 16%,var(--i3-surface));color:var(--i3-ink);}
.aether-nano-foot {justify-content:flex-start;background:var(--i3-surface);color:var(--i3-muted);font-weight:500;}
.aether-nano-body {display:block;width:100%;min-height:200px;max-height:46vh;resize:vertical;border:0;outline:none!important;box-shadow:none!important;background:transparent!important;padding:10px 12px;font:13px/1.55 var(--i3-mono);color:var(--i3-ink);tab-size:4;caret-color:var(--i3-accent);}
.i3-judge-alert.freq {color:var(--i3-warn);text-shadow:0 0 30px #f2c77888,0 0 80px #f2c77833;font-size:clamp(28px,5.6vw,70px);}
/* ── NVTRA pillar entrance (reuses the boot liquid loader) ── */
#i3-nvtra-boot {position:absolute;inset:0;z-index:40;display:grid;place-content:center;justify-items:center;gap:22px;background:radial-gradient(120% 90% at 50% 0%,#0b1f3a 0%,#030712 60%);color:var(--i3-ink);transition:opacity .55s ease;}
#i3-nvtra-boot.out {opacity:0;pointer-events:none;}
#i3-nvtra-boot svg {width:min(420px,70vw);height:auto;overflow:visible;filter:drop-shadow(0 0 18px #d4b25a55);}
#i3-nvtra-boot .lg-stroke {stroke-dasharray:700;stroke-dashoffset:700;animation:i3LogoDraw 1.1s cubic-bezier(.4,0,.2,1) forwards;}
#i3-nvtra-boot .lg-stroke.s2 {animation-delay:.18s}#i3-nvtra-boot .lg-stroke.s3 {animation-delay:.36s}
#i3-nvtra-boot .lg-tip {opacity:0;transform:translateY(-10px);animation:i3LogoTip .45s ease forwards;animation-delay:1.05s}
#i3-nvtra-boot .lg-tip.s2 {animation-delay:1.2s}#i3-nvtra-boot .lg-tip.s3 {animation-delay:1.35s}
#i3-nvtra-boot .lg-glow {opacity:0;animation:i3LogoGlow 1.2s ease forwards;animation-delay:1.3s}
#i3-nvtra-boot .i3-boot-eyebrow {opacity:0;animation:i3LogoTip .6s ease forwards;animation-delay:1.5s}
@keyframes i3LogoDraw {to{stroke-dashoffset:0}}
@keyframes i3LogoTip {to{opacity:1;transform:none}}
@keyframes i3LogoGlow {0%{opacity:0}40%{opacity:.9}100%{opacity:.35}}
#i3-nvtra-boot .i3-boot-eyebrow {font:600 10px var(--i3-mono);letter-spacing:.3em;color:#7dd3fc;}
#i3-nvtra-boot .i3-boot-title {font-size:clamp(30px,5vw,54px);}
.i3-freq-note {position:fixed;left:50%;top:calc(env(safe-area-inset-top,0px) + 96px);transform:translateX(-50%);z-index:2147483005;pointer-events:none;text-align:center;font:800 clamp(22px,4.2vw,46px)/1 var(--i3-mono);letter-spacing:.14em;color:var(--i3-warn);text-shadow:0 0 22px #f2c77888,0 0 60px #f2c77833;opacity:0;animation:i3FreqIn 2.6s ease both;}
.i3-freq-note small {display:block;font:600 10px/1.8 var(--i3-mono);letter-spacing:.3em;color:var(--i3-ink);margin-top:10px;text-shadow:none;}
@keyframes i3FreqIn {0%{opacity:0;transform:translate(-50%,-14px) scale(.92)}8%{opacity:1;transform:translate(-50%,0) scale(1.04)}12%{transform:translate(-52%,1px) scale(1)}16%{transform:translate(-48%,-1px)}20%{transform:translate(-50%,0)}80%{opacity:1}100%{opacity:0;transform:translate(-50%,-10px)}}
/* ── CH3: possible SG findings ── */
.ch3-sg-list {display:grid;gap:8px;}
.ch3-sg-row {display:grid;grid-template-columns:14px 1fr auto;gap:12px;align-items:start;padding:12px 14px;border:1px solid var(--i3-border);border-radius:12px;background:color-mix(in srgb,var(--i3-surface) 80%,transparent);}
.ch3-sg-dot {width:9px;height:9px;border-radius:50%;margin-top:4px;background:var(--i3-accent);box-shadow:0 0 8px var(--i3-accent);}
.ch3-sg-dot.ch3-sg-warn {background:var(--i3-warn);box-shadow:0 0 8px var(--i3-warn);}
.ch3-sg-dot.ch3-sg-high {background:var(--i3-error);box-shadow:0 0 8px var(--i3-error);}
.ch3-sg-title {font:600 12px var(--i3-mono);letter-spacing:.06em;color:var(--i3-ink);}
.ch3-sg-detail {font:12px/1.5 var(--i3-font);color:var(--i3-muted);margin-top:3px;}
.ch3-sg-kind {font:600 9px var(--i3-mono);letter-spacing:.18em;color:var(--i3-muted);padding:4px 8px;border:1px solid var(--i3-border);border-radius:999px;white-space:nowrap;}
/* ── classified resource ── */
.aether-classified {position:relative;margin:0 18px 18px;padding:22px 18px 18px;border:1px solid color-mix(in srgb,var(--i3-error) 45%,var(--i3-border));border-radius:14px;background:color-mix(in srgb,var(--i3-error) 6%,var(--i3-soft));text-align:center;animation:i3LogoIn .5s ease both;}
.aether-classified-title {font:600 11px var(--i3-mono);letter-spacing:.26em;color:var(--i3-error);}
.aether-classified-qr {width:180px;height:180px;margin:16px auto;padding:10px;background:#fff;border-radius:10px;box-shadow:0 0 30px #ff999522;}
.aether-classified-qr img {width:100%;height:100%;display:block;image-rendering:pixelated;}
.aether-classified-warn {font:500 9px var(--i3-mono);letter-spacing:.24em;color:var(--i3-muted);}
.aether-classified-close {position:absolute;top:8px;right:10px;width:28px;height:28px;border-radius:50%;border:1px solid var(--i3-border);background:var(--i3-surface);color:var(--i3-ink);font:16px/1 var(--i3-mono);cursor:pointer;}
/* ── Fieldrun frame ── */
.aether-game {position:fixed;inset:0;z-index:2147483005;background:#071014;display:flex;flex-direction:column;}
.aether-game[hidden],.aether-classified[hidden] {display:none;}
.aether-game-frame {flex:1;min-height:0;}
.aether-game-frame iframe {width:100%;height:100%;border:0;display:block;background:#071014;}
.aether-game-close {display:none;position:absolute;top:calc(env(safe-area-inset-top,0px) + 12px);left:50%;transform:translateX(-50%);z-index:2;padding:8px 14px;border-radius:999px;border:1px solid #48736b;background:#102023dd;color:#b7c9c8;font:600 10px var(--i3-mono);letter-spacing:.14em;cursor:pointer;}
/* ── Judge mode ── */
#i3-judge-dim {position:fixed;inset:0;z-index:2147483005;background:#000;opacity:0;pointer-events:none;transition:opacity .45s ease;}
#i3-judge-dim.on {opacity:.62;pointer-events:auto;}
#i3-judge-hud {position:fixed;inset:0;z-index:2147483006;display:flex;align-items:center;justify-content:center;pointer-events:none;opacity:0;transition:opacity .3s ease;}
#i3-judge-hud.on {opacity:1;}
.i3-judge-alert {font:800 clamp(34px,7vw,88px)/1 var(--i3-mono);letter-spacing:.12em;color:var(--i3-error);text-shadow:0 0 30px #ff999588,0 0 80px #ff999533;animation:i3JudgeShake .35s ease-in-out infinite;text-align:center;padding:0 16px;}
.i3-judge-alert small {display:block;font:600 11px/1.8 var(--i3-mono);letter-spacing:.3em;color:var(--i3-ink);margin-top:14px;animation:none;text-shadow:none;}
@keyframes i3JudgeShake {0%,100%{transform:translate(0,0)}25%{transform:translate(-3px,2px)}50%{transform:translate(3px,-2px)}75%{transform:translate(-2px,-3px)}}
.i3-judge-hud-proto {text-align:center;font:600 clamp(14px,2.6vw,26px)/1.7 var(--i3-mono);letter-spacing:.24em;color:var(--i3-accent);text-shadow:0 0 24px #31d7e666;}
.i3-judge-hud-proto b {display:block;color:var(--i3-ink);font-size:1.4em;letter-spacing:.3em;}
.i3-judge-hud-proto em {display:block;font-style:normal;color:var(--i3-warn);font-size:.8em;margin-top:10px;}
#i3-judge-flash {position:fixed;inset:0;z-index:2147483007;background:#fff;opacity:0;pointer-events:none;}
#i3-judge-panel {position:fixed;inset:0;z-index:2147483005;background:var(--i3-bg);color:var(--i3-ink);display:none;flex-direction:column;padding:calc(env(safe-area-inset-top,0px) + 22px) 22px 22px;gap:18px;overflow:auto;}
#i3-judge-panel.on {display:flex;}
.i3-judge-top {display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;}
.i3-judge-top h1 {margin:0;font:700 18px var(--i3-mono);letter-spacing:.28em;color:var(--i3-ink);}
.i3-judge-top h1 span {display:block;font:500 9px var(--i3-mono);letter-spacing:.2em;color:var(--i3-muted);margin-top:6px;}
.i3-judge-exit {padding:12px 20px;border-radius:999px;border:1px solid var(--i3-accent);background:color-mix(in srgb,var(--i3-accent) 14%,transparent);color:var(--i3-ink);font:700 11px var(--i3-mono);letter-spacing:.2em;cursor:pointer;}
.i3-judge-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;}
.i3-judge-tile {border:1px solid var(--i3-border);border-radius:16px;padding:18px;background:var(--i3-surface);min-height:120px;display:flex;flex-direction:column;justify-content:space-between;}
.i3-judge-tile .k {font:600 9px var(--i3-mono);letter-spacing:.22em;color:var(--i3-muted);}
.i3-judge-tile .v {font:700 clamp(28px,4.2vw,44px)/1.1 var(--i3-mono);color:var(--i3-ink);margin:12px 0 6px;word-break:break-word;}
.i3-judge-tile .v small {font-size:.45em;color:var(--i3-muted);margin-left:6px;}
.i3-judge-tile .s {font:500 10px var(--i3-mono);letter-spacing:.1em;color:var(--i3-muted);}
.i3-judge-tile.ok .k::before,.i3-judge-tile.warn .k::before,.i3-judge-tile.bad .k::before {content:'';display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:8px;vertical-align:1px;}
.i3-judge-tile.ok .k::before {background:var(--i3-good);box-shadow:0 0 8px var(--i3-good);}
.i3-judge-tile.warn .k::before {background:var(--i3-warn);box-shadow:0 0 8px var(--i3-warn);}
.i3-judge-tile.bad .k::before {background:var(--i3-error);box-shadow:0 0 8px var(--i3-error);}
.i3-judge-tile.wide {grid-column:1/-1;min-height:0;}
.i3-judge-tile.wide .v,.i3-judge-tile.text .v {font-size:18px;line-height:1.4;font-weight:600;letter-spacing:.06em;}
.i3-judge-tile ul {margin:10px 0 0;padding-left:18px;font:500 12px/1.6 var(--i3-mono);color:var(--i3-ink);}
@media (prefers-reduced-motion: reduce){.i3-judge-alert,.aether-term-caret,.nvtra-logo-mark{animation:none!important;}}
'''

BOOT_HTML = '''<div id="i3-boot" role="status" aria-live="polite">
<div class="i3-scene" id="i3-scene" aria-hidden="true"><img src="/assets/parallax/background.webp" alt="" loading="eager" decoding="async" data-sx="0.03" data-sy="0.038" data-sz="0" data-rot="0" style="z-index:1;top:calc(50% - 50px);left:calc(50% + 0px);width:calc(3200px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/fog-7.webp" alt="" loading="eager" decoding="async" data-sx="0.27" data-sy="0.32" data-sz="0" data-rot="0" style="z-index:2;top:calc(50% - 100px);left:calc(50% + 300px);width:calc(1900px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/mountain-10.webp" alt="" loading="eager" decoding="async" data-sx="0.095" data-sy="0.005" data-sz="0" data-rot="0" style="z-index:3;top:calc(50% + 169px);left:calc(50% + 330px);width:calc(1200px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/fog-6.webp" alt="" loading="eager" decoding="async" data-sx="0.25" data-sy="0.28" data-sz="0" data-rot="0" style="z-index:4;top:calc(50% + 285px);left:calc(50%);width:calc(2200px * var(--scene-scale));opacity:0.3"><img data-src="/assets/parallax/mountain-9.webp" alt="" loading="eager" decoding="async" data-sx="0.125" data-sy="0.155" data-sz="0.15" data-rot="0.02" style="z-index:51;top:calc(50% + 313px);left:calc(50% - 557px);width:calc(670px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/fog-5.webp" alt="" loading="eager" decoding="async" data-sx="0.16" data-sy="0.105" data-sz="0" data-rot="0" style="z-index:7;top:calc(50% + 360px);left:calc(50% + 40px);width:calc(650px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/mountain-7.webp" alt="" loading="eager" decoding="async" data-sx="0.1" data-sy="0.1" data-sz="0" data-rot="0.09" style="z-index:19;top:calc(50% + 223px);left:calc(50% + 495px);width:calc(738px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/mountain-6.webp" alt="" loading="eager" decoding="async" data-sx="0.065" data-sy="0.05" data-sz="0.05" data-rot="0.12" style="z-index:18;top:calc(50% + 120px);left:calc(50% + 590px);width:calc(408px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/fog-4.webp" alt="" loading="eager" decoding="async" data-sx="0.135" data-sy="0.1" data-sz="0" data-rot="0" style="z-index:11;top:calc(50% + 223px);left:calc(50% + 460px);width:calc(590px * var(--scene-scale));opacity:0.5"><img data-src="/assets/parallax/mountain-5.webp" alt="" loading="eager" decoding="async" data-sx="0.08" data-sy="0.05" data-sz="0.13" data-rot="0.1" style="z-index:12;top:calc(50% + 320px);left:calc(50% + 230px);width:calc(725px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/fog-3.webp" alt="" loading="eager" decoding="async" data-sx="0.11" data-sy="0.018" data-sz="0" data-rot="0" style="z-index:113;top:calc(50% + 210px);left:calc(50% + 5px);width:calc(1600px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/mountain-4.webp" alt="" loading="eager" decoding="async" data-sx="0.059" data-sy="0.024" data-sz="0.35" data-rot="0.14" style="z-index:15;top:calc(50% + 196px);left:calc(50% - 698px);width:calc(1100px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/mountain-3.webp" alt="" loading="eager" decoding="async" data-sx="0.04" data-sy="0.018" data-sz="0.32" data-rot="0.05" style="z-index:20;top:calc(50% - 20px);left:calc(50% + 750px);width:calc(630px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/fog-2.webp" alt="" loading="eager" decoding="async" data-sx="0.15" data-sy="0.0115" data-sz="0" data-rot="0" style="z-index:16;top:calc(50% - 20px);left:calc(50% + 698px);width:calc(1100px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/mountain-2.webp" alt="" loading="eager" decoding="async" data-sx="0.0235" data-sy="0.013" data-sz="0.42" data-rot="0.15" style="z-index:17;top:calc(50% + 256px);left:calc(50% + 528px);width:calc(800px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/mountain-1.webp" alt="" loading="eager" decoding="async" data-sx="0.027" data-sy="0.018" data-sz="0.53" data-rot="0.2" style="z-index:18;top:calc(50% + 196px);left:calc(50% - 728px);width:calc(1100px * var(--scene-scale));opacity:1"><img data-src="/assets/parallax/fog-1.webp" alt="" loading="eager" decoding="async" data-sx="0.12" data-sy="0.01" data-sz="0" data-rot="0" style="z-index:21;top:calc(100% - 355px);left:calc(50% + 100px);width:calc(1900px * var(--scene-scale));opacity:0.5"><div class="i3-scene-vignette"></div></div>
<div class="i3-boot-panel">
<div class="i3-boot-eyebrow">I³ · INDUCTION · INTERFERENCE · INTELLIGENCE</div>
<div class="i3-liquid" aria-hidden="true">
 <div class="i3-liquid-col" style="--c1:#1e3a8a;--c2:#3b82f6"><i class="i3-drop"></i><b class="i3-bar"><s></s><u></u></b><i class="i3-base"></i></div>
 <div class="i3-liquid-col" style="--c1:#1d4ed8;--c2:#60a5fa"><i class="i3-drop"></i><b class="i3-bar"><s></s><u></u></b><i class="i3-base"></i></div>
 <div class="i3-liquid-col" style="--c1:#2563eb;--c2:#38bdf8"><i class="i3-drop"></i><b class="i3-bar"><s></s><u></u></b><i class="i3-base"></i></div>
 <div class="i3-liquid-col" style="--c1:#0284c7;--c2:#22d3ee"><i class="i3-drop"></i><b class="i3-bar"><s></s><u></u></b><i class="i3-base"></i></div>
 <div class="i3-liquid-col" style="--c1:#0891b2;--c2:#67e8f9"><i class="i3-drop"></i><b class="i3-bar"><s></s><u></u></b><i class="i3-base"></i></div>
 <div class="i3-liquid-col" style="--c1:#4f46e5;--c2:#818cf8"><i class="i3-drop"></i><b class="i3-bar"><s></s><u></u></b><i class="i3-base"></i></div>
 <div class="i3-liquid-col" style="--c1:#0e7490;--c2:#22d3ee"><i class="i3-drop"></i><b class="i3-bar"><s></s><u></u></b><i class="i3-base"></i></div>
</div>
<div class="i3-boot-title">{BOOT_TITLE}</div>
<div class="i3-boot-row">
 <div class="i3-progress-wrap">
  <div class="i3-progress-head"><span id="i3-boot-state">Preparing the interface</span><span id="i3-boot-percent">0%</span></div>
  <div class="i3-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div class="i3-progress-fill" id="i3-boot-progress"><div class="i3-progress-shine"></div></div></div>
  <div id="i3-boot-detail"></div>
  <div class="i3-progress-steps" id="i3-boot-steps"><span>Fonts</span><span>Theme</span><span>Graphics</span><span>Status</span><span>Interface</span></div>
 </div>
</div>
</div>
<div id="i3-mode" hidden>
 <div class="i3-boot-eyebrow">I³ · INDUCTION · INTERFERENCE · INTELLIGENCE</div>
 <div class="i3-boot-title" style="font-size:clamp(30px,5vw,54px)">{BOOT_TITLE}</div>
 <div class="i3-mode-title">How should the studio run?</div>
 <div class="i3-mode-sub" id="i3-mode-sub">Checking the internet connection</div>
 <div class="i3-mode-grid">
  <button type="button" class="i3-mode-card" data-mode="online"><span class="i3-mode-key">O</span><strong>Online</strong><span>Cloud assistant providers, Notion export and updates. Needs internet.</span></button>
  <button type="button" class="i3-mode-card" data-mode="offline"><span class="i3-mode-key">F</span><strong>Offline</strong><span>Nothing leaves this device. Chat runs on the local model, exports stay local.</span><em id="i3-mode-local"></em></button>
 </div>
 <div class="i3-mode-hint">Press O or F, or Enter for the highlighted choice. You can change this later from the mode icon.</div>
</div>
</div><canvas id="i3-field-background" aria-hidden="true"></canvas>
<script>(function(){var scene=document.getElementById('i3-scene');if(!scene)return;var imgs=Array.from(scene.querySelectorAll('img')),W=innerWidth,H=innerHeight,tx=W/2,ty=H/2,px=tx,py=ty,last=performance.now(),idle=true,t0=last;function fit(){W=innerWidth;H=innerHeight;scene.style.setProperty('--scene-scale',String(Math.max(.45,Math.min(1,W/1920))));tx=Math.max(0,Math.min(W,tx));ty=Math.max(0,Math.min(H,ty));}fit();addEventListener('resize',fit,{passive:true});function apply(cx,cy){var x=cx-W/2,y=cy-H/2,rot=(x/Math.max(1,W/2))*6;for(var i=0;i<imgs.length;i++){var el=imgs[i],d=el.dataset,left=el.offsetLeft,isLeft=left<W/2?1:-1,z=Math.max(-36,Math.min(36,(cx-left)*isLeft*.045*+d.sz)),dx=-x*+d.sx,dy=y*+d.sy;el.style.transform='translate3d(calc(-50% + '+dx.toFixed(2)+'px),calc(-50% + '+dy.toFixed(2)+'px),'+z.toFixed(2)+'px) rotateY('+(rot*+d.rot).toFixed(2)+'deg)';}}function aim(x,y){idle=false;tx=Math.max(0,Math.min(W,x));ty=Math.max(0,Math.min(H,y));}addEventListener('mousemove',function(e){aim(e.clientX,e.clientY);},{passive:true});addEventListener('touchmove',function(e){var t=e.touches[0];if(t)aim(t.clientX,t.clientY);},{passive:true});if(window.DeviceOrientationEvent)addEventListener('deviceorientation',function(e){if(e.gamma==null)return;aim(W/2+Math.max(-45,Math.min(45,e.gamma))/45*W*.38,H/2+Math.max(-45,Math.min(45,e.beta-40))/45*H*.3);},{passive:true});function tick(now){if(!document.getElementById('i3-scene'))return;var dt=Math.min(.05,Math.max(.001,(now-last)/1000));last=now;if(idle){var t=(now-t0)*.001;tx=W/2+Math.sin(t*.22)*W*.11;ty=H/2+Math.cos(t*.18)*H*.07;}var ease=1-Math.exp(-dt*8);px+=(tx-px)*ease;py+=(ty-py)*ease;if(!document.hidden)apply(px,py);requestAnimationFrame(tick);}requestAnimationFrame(tick);})();</script>
<script>window.__i3FailedScripts=[];addEventListener('error',function(e){if(e.target&&e.target.tagName==='SCRIPT'&&e.target.src)window.__i3FailedScripts.push(e.target.src.split('/').pop().split('?')[0]);},true);(function(){var cols=document.querySelectorAll('.i3-liquid-col'),fill=document.getElementById('i3-boot-progress'),pct=document.getElementById('i3-boot-percent'),st=document.getElementById('i3-boot-state'),bar=fill&&fill.parentElement;var reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;function tick(){if(!document.getElementById('i3-boot'))return;var t=performance.now()*.001;if(!reduced&&!window.__i3BootLiquid)for(var i=0;i<cols.length;i++){var d=i*.72,level=.16+.84*(.5+.5*Math.sin(t*1.15+d)+Math.sin(t*2.3+d)*.06);level=Math.max(.12,Math.min(1,level));cols[i].querySelector('.i3-bar').style.transform='scaleY('+level.toFixed(3)+')';cols[i].querySelector('.i3-drop').classList.toggle('on',level>.9);}if(!window.__i3BootTaken){var sizes=window.I3_BUNDLES||{},detail=document.getElementById('i3-boot-detail'),total=0,got=0,count=0,done=0,failed=window.__i3FailedScripts||[];for(var j=0;j<document.scripts.length;j++){var src=document.scripts[j].src;if(!src)continue;var path=src.replace(location.origin,'').split('?')[0],size=sizes[path]||0;if(!size)continue;count++;total+=size;var e=performance.getEntriesByName(src);if(e.length&&e[0].responseEnd>0){got+=size;done++;}}var frac=total?got/total*.55:0;var value=Math.round(frac*100);fill.style.width=(frac*100).toFixed(2)+'%';pct.textContent=value+'%';if(bar)bar.setAttribute('aria-valuenow',String(value));var mb=function(b){return (b/1048576).toFixed(2);};var stalled=(failed.length||(done>=count&&count&&performance.now()>45000))&&!window.__i3BootReloading;if(stalled){var n=0;try{n=+(sessionStorage.getItem('i3-boot-retry')||0);}catch(e){}if(n<3){window.__i3BootReloading=true;try{sessionStorage.setItem('i3-boot-retry',String(n+1));}catch(e){}setTimeout(function(){location.reload();},1200);}}st.textContent=window.__i3BootReloading?'A module did not arrive intact; reloading':failed.length?'A module failed to load: '+failed[0]+'. Reload to retry.':(done<count?'Receiving interface modules':'Interface modules received');if(detail)detail.textContent=total?mb(got)+' / '+mb(total)+' MB received or cache-ready · '+done+' / '+count+' modules':'Measuring interface modules';}requestAnimationFrame(tick);}requestAnimationFrame(tick);})();</script>'''

def boot_html():
    """The boot screen with this studio's words (S1-06), escaped for HTML."""
    from html import escape
    title = f'{escape(T("boot.title"))} <span>{escape(T("boot.title_accent"))}</span>'
    return BOOT_HTML.replace("{BOOT_TITLE}", title)


HEAD_JS = r'''
window.__i3ReadyPromise=new Promise(function(resolve){window.__i3ResolveReady=resolve;});
(function(){try{localStorage.removeItem('i3-theme');}catch(error){}})();
'''

JS = r'''
(function(){
'use strict';
const root=document.documentElement, motion=matchMedia('(prefers-reduced-motion: reduce)');
const state={packet:null,source:null,pending:null,paint:0,vector:[0,0,0],traces:new Map(),traceProfiles:new Map(),nodes:[],lastMessage:0,streamVersion:0};
const metrics={frames:[],work:[],longTasks:0,layoutShift:0,readyMs:null,streamMessages:0};
window.__i3Metrics=metrics;window.__i3Errors=[];window.__i3Debug={};addEventListener('error',e=>{window.__i3Errors.push(String(e.message)+' @'+e.lineno);});
try {new PerformanceObserver(list=>list.getEntries().forEach(entry=>{if(!entry.hadRecentInput)metrics.layoutShift+=entry.value;})).observe({type:'layout-shift',buffered:true});}catch(error){}
try {new PerformanceObserver(list=>{metrics.longTasks+=list.getEntries().length;}).observe({type:'longtask',buffered:true});}catch(error){}
const reduced=()=>motion.matches||root.classList.contains('no-anim');
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const finite=v=>typeof v==='number'&&Number.isFinite(v);
const get=(obj,path)=>path.split('.').reduce((v,k)=>v==null?undefined:v[k],obj);
const clean=v=>{const s=String(v??'Unavailable');
 /* A value that is nothing but a dash is a placeholder meaning "no reading",
    not prose punctuation. The dash-stripping below is a typographic rule for
    sentences; applied to a placeholder it leaves an empty cell, which reads as
    a rendering failure rather than as a deliberate absence. 180 of these exist
    across the pages -- every offline channel, uncalibrated axis and empty stat. */
 if(/^\s*[\u2014\u2013\u002d]\s*$/.test(s))return s;
 return s.replace(/\u002d(?=\d)/g,'−').replace(/[\u2014\u2013\u002d]/g,' ');};
const numberFormat=new Intl.NumberFormat(undefined,{maximumSignificantDigits:3});
const fmt=(value,kind)=>{
 if(value===null||value===undefined)return 'Unavailable';
 if(kind==='time')return value?new Date(Number(value)*1000).toLocaleString():'Not calibrated';
 if(kind==='percent')return finite(value)?value.toFixed(1)+' %':clean(value);
 if(kind==='fraction')return finite(value)?Math.round(value*100)+' %':clean(value);
 if(kind==='baseline')return value.settling?'Settling':value.frozen?'Frozen':'Tracking ambient';
 if(kind==='baseline_window')return (value.settling?'Settling':value.frozen?'Frozen':'Tracking ambient')+' · '+numberFormat.format(value.window)+' s';
 if(kind==='number')return finite(value)?numberFormat.format(value).replace(/\u002d/g,'−'):clean(value);
 if(kind==='json')return JSON.stringify(value,null,2).replace(/\u002d(?=\d)/g,'−').replace(/[\u2014\u2013\u002d]/g,' ');
 if(Array.isArray(value))return value.map(x=>finite(x)?numberFormat.format(x).replace(/\u002d/g,'−'):typeof x==='object'?JSON.stringify(x):clean(x)).join(' · ');
 if(typeof value==='object')return Object.entries(value).map(([k,v])=>clean(k)+': '+fmt(v)).join(' · ');
 return clean(value);
};
let toastTimer=0;function text(el,value){if(!el)return;if(el.textContent!==value)el.textContent=value;if(el.id==='i3-control-result'&&value){el.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('show'),4500);}}
function normalizeProse(scope){const walker=document.createTreeWalker(scope,NodeFilter.SHOW_TEXT);let node;while((node=walker.nextNode())){if(node.parentElement?.closest('script,style,code,pre,textarea'))continue;const value=clean(node.nodeValue);if(value!==node.nodeValue)node.nodeValue=value;}}
const panelViews=new Map();
const panelObserver=new IntersectionObserver(entries=>{let revealed=false;for(const entry of entries){panelViews.set(entry.target,entry.isIntersecting);revealed ||= entry.isIntersecting;}if(revealed&&state.packet)drawPacket(state.packet,false);});
function visiblePanel(el){return panelViews.get(el.__i3Panel||el.closest('.i3-card'))!==false;}
function mountPlotlyHand3d(){
 if(!window.Plotly)return;
 document.querySelectorAll('.js-plotly-plot').forEach(plot=>{
  if(!plot._fullLayout?.scene)return;
  let controls=plot.__i3HandControls;
  if(!controls){
   let yaw=.72,pitch=.35,radius=1.75,vy=0,vp=0,raf=0;
   const apply=()=>{const cp=Math.cos(pitch);window.Plotly.relayout(plot,{'scene.dragmode':'orbit','scene.camera.eye':{x:radius*cp*Math.cos(yaw),y:radius*cp*Math.sin(yaw),z:radius*Math.sin(pitch)}}).catch(()=>{});};
   const coast=()=>{if(raf)return;const tick=()=>{raf=0;if(!plot.isConnected)return;vy*=.92;vp*=.88;if(Math.abs(vy)+Math.abs(vp)<.00008)return;yaw+=vy;pitch=clamp(pitch+vp,-1.25,1.25);apply();raf=requestAnimationFrame(tick);};raf=requestAnimationFrame(tick);};
   controls={
    physics(delta){vp=clamp(delta[0]*.55,-.07,.07);vy=clamp(delta[1]*.55,-.09,.09);pitch=clamp(pitch+delta[0],-1.25,1.25);yaw+=delta[1];apply();coast();},
    rotate(dx,dy){dy=dy||0;vy=clamp(dx*.035,-.09,.09);vp=clamp(-dy*.032,-.07,.07);yaw+=dx*4.19;pitch=clamp(pitch-dy*3.84,-1.25,1.25);apply();coast();},
    zoom(scale){radius=clamp(2/Math.max(.55,scale),.65,4.5);apply();},
    reset(){yaw=.72;pitch=.35;radius=1.75;vy=vp=0;apply();}
   };
   plot.__i3HandControls=controls;
  }
  /* Plotly uses stacked WebGL canvases. The visible hit target is not always the
     first one, so every canvas receives the same Earth-style hand contract. */
  plot.querySelectorAll('canvas').forEach(canvas=>{canvas.__i3LegacyHandControls=controls;canvas.style.touchAction='none';canvas.title='Drag to orbit · scroll or pinch to zoom · pinch with hand vision to hold';});
 });
}
function retargetHandVision(){mountPlotlyHand3d();const candidates=Array.from(document.querySelectorAll('canvas')).filter(c=>c.__i3LegacyHandControls&&c.isConnected);const target=candidates.sort((a,b)=>{const ar=a.getBoundingClientRect(),br=b.getBoundingClientRect();const ac=Math.abs((ar.top+ar.bottom)/2-innerHeight/2)+(ar.bottom<0||ar.top>innerHeight?1e6:0);const bc=Math.abs((br.top+br.bottom)/2-innerHeight/2)+(br.bottom<0||br.top>innerHeight?1e6:0);return ac-bc;})[0];if(target&&window.__i3HandControls!==target.__i3LegacyHandControls)window.__i3HandControls=target.__i3LegacyHandControls;}
addEventListener('scroll',()=>requestAnimationFrame(retargetHandVision),{passive:true});
window.__i3RefreshHandControls=retargetHandVision;window.__i3HoldActive=()=>fingerMouse.hold;window.__i3PhysicsHold=()=>fingerMouse.hold&&!fingerMouse.peaceNow;
/* Plotly may consume trackpad wheel events even with scrollZoom disabled. On the
   Sweep3 route that strands page scrolling over large CH3/SDR/Wi-Fi/BLE charts.
   Hand ordinary wheel travel back to the document; ctrl+wheel remains available
   as an explicit chart/trackpad zoom gesture. */
addEventListener('wheel',event=>{if(location.pathname!=='/page-2'||event.ctrlKey)return;const plot=event.target?.closest?.('.js-plotly-plot');if(!plot)return;/* Keep Plotly from treating the gesture as chart input. With no preventDefault, the browser retains native page scrolling, momentum and both directions. */event.stopImmediatePropagation();},{capture:true,passive:true});
function httpsLink(){const port=state.packet?.telemetry?.https_port||8443;return 'https://'+location.hostname+':'+port+location.pathname;}
function syncNav(){retargetHandVision();const btn=document.getElementById('nav-page3');if(!btn)return;const active=location.pathname==='/page-3';const className='nav-glass-btn'+(active?' nav-active':'');if(btn.className!==className)btn.className=className;}
function cacheNodes(){syncNav();parallaxScroll();layoutRotate();nebulaSync();mountPlotlyHand3d();const nodes=Array.from(document.querySelectorAll('[data-i3-bind]'));const changed=nodes.length!==state.nodes.length||nodes.some((el,i)=>el!==state.nodes[i]);if(!changed){mountCanvases();return;}normalizeProse(document.getElementById('page-content')||document.body);state.nodes=nodes;for(const [panel] of panelViews)if(!panel.isConnected){panelObserver.unobserve(panel);panelViews.delete(panel);}for(const panel of document.querySelectorAll('.i3-card'))if(!panelViews.has(panel)){panelViews.set(panel,true);panelObserver.observe(panel);}for(const el of state.nodes)el.__i3Panel=el.closest('.i3-card');if(state.packet)drawPacket(state.packet,false);mountCanvases();mountPlotlyHand3d();}
function syncModeButton(){const btn=document.getElementById('i3-mode-toggle');if(!btn)return;const mode=state.packet?.mode?.mode||'online';const title=(mode==='offline'?'Offline mode (nothing leaves this device). Click for online':'Online mode. Click for offline');if(btn.title!==title){btn.title=title;btn.setAttribute('aria-label',title);btn.textContent=mode==='offline'?'⊘':'⇅';}btn.classList.toggle('i3-tool-offline',mode==='offline');}
function syncCameraButton(){syncModeButton();const enabled=!!window.__i3HandVisionRunning||!!window.__i3HandVisionStarting||!!state.packet?.camera?.enabled;document.querySelectorAll('[data-i3-action="hand_tracking"]').forEach(b=>{const l='HAND TRACKING: '+(enabled?'ON':'OFF');if(b.textContent!==l)b.textContent=l;b.classList.toggle('on',enabled);});const btn=document.getElementById('i3-camera-toggle');if(!btn)return;const title=enabled?'Disable camera. Shortcut C':'Enable camera (hand tracking). Shortcut C';if(btn.title!==title){btn.title=title;btn.setAttribute('aria-label',title);}if(btn.getAttribute('aria-pressed')!==String(enabled))btn.setAttribute('aria-pressed',String(enabled));}
function drawHeader(packet){
 for(const [name,selector] of [['ch1','.pill-c1'],['ch2','.pill-c2'],['ch3','.pill-rf']]){
  const channel=packet.channels?.[name];if(!channel)continue;for(const pill of document.querySelectorAll(selector)){
  const online=channel.state==='connected',quality=!online?'pill-off':channel.clipped?'pill-high':'pill-ok';
  const unit=name==='ch2'?'mV':channel.unit;const value=name==='ch1'?channel.display?.magnitude:name==='ch2'?channel.display?.rms_mv:channel.deviation;
  text(pill.querySelector('.pill-val'),online?fmt(value,'number')+' '+unit:'OFFLINE');
  const dot=pill.querySelector('.pill-dot'),className='pill-dot '+quality;if(dot&&dot.className!==className)dot.className=className;
  if(pill.title!==channel.uncertainty)pill.title=channel.uncertainty;
 }}
 const confidence=packet.fusion?.confidence||0;
 for(const pill of document.querySelectorAll('.pill-mtdi')){text(pill.querySelector('.pill-val'),confidence.toFixed(1)+' %');const dot=pill.querySelector('.pill-dot'),className='pill-dot '+(confidence>80?'pill-ok':confidence>50?'pill-warn':'pill-high');if(dot&&dot.className!==className)dot.className=className;}
 // Alerting is the engine's job, not the browser's. The fixed 80 unit / 3 unit test
 // that used to live here has moved to AnalysisEngine, which compares each channel
 // against its own measured noise AND an absolute change, on all four channels.
}
function drawPacket(packet,append=true){
 try{drawPacketInner(packet,append);}catch(error){window.__i3Errors.push('draw: '+error.message);}
 try{fastNumbers(packet);}catch(error){window.__i3Errors.push('fast: '+error.message);}
}
function drawPacketInner(packet,append){
 const started=performance.now();state.packet=packet;window.__i3Instrument=packet;
 const traceCanvases=Array.from(traceViews.keys()).filter(canvas=>traceViews.get(canvas).visible);
 const traceDimensions=new Map(traceCanvases.map(canvas=>[canvas,traceViews.get(canvas).dim]));
 drawHeader(packet);
 buddyReadEvents(packet);
 for(const el of state.nodes){if(!el.isConnected||!visiblePanel(el))continue;let value=get(packet,el.dataset.i3Bind);text(el,fmt(value,el.dataset.i3Format));}
 syncCameraButton();
 document.querySelectorAll('[data-i3-camera-preview]').forEach(img=>{const source=packet.camera?.state==='connected'?'/api/camera/stream':'';if(source&&!img.getAttribute('src'))img.setAttribute('src',source);if(!source&&img.getAttribute('src'))img.removeAttribute('src');});
 const v=packet.fusion?.vector;if(v&&[v.x,v.y,v.z].every(finite))state.vector=[v.x,v.y,v.z];else state.vector=[0,0,0];
 if(packet.camera?.enabled&&!state.trackingSource){state.trackingSource=new EventSource('/api/tracking');state.trackingSource.onmessage=e=>{try{physics.sample(JSON.parse(e.data));}catch(error){}};}
 if(!packet.camera?.enabled&&state.trackingSource){state.trackingSource.close();state.trackingSource=null;}
 if(!state.trackingSource&&packet.camera?.tracking)physics.sample(packet.camera.tracking);
 if(append){for(const [name,ch] of Object.entries(packet.channels||{})){if(!finite(ch.deviation))continue;const profile=ch.unit+'|'+(ch.calibration?.timestamp||'');let list=state.traceProfiles.get(name)===profile?(state.traces.get(name)||[]):[];state.traceProfiles.set(name,profile);const timestamp=ch.last_rx??ch.timestamp??ch.last_update??packet.timestamp;if(!list.length||timestamp!==list.at(-1).t){list.push({v:ch.deviation,t:timestamp});if(list.length>160)list.shift();state.traces.set(name,list);}}}
 const breakdown=packet.fusion?.breakdown||{};
 document.querySelectorAll('[data-i3-breakdown]').forEach(el=>{if(!visiblePanel(el))return;const content=Object.entries(breakdown).map(([key,val])=>clean(key)+'   '+fmt(val)).join('\n');text(el,content||'Waiting for confidence evidence');});
 for(const canvas of traceCanvases){const list=state.traces.get(canvas.dataset.i3Trace)||[];const last=list.at(-1)?.t;if(canvas.__i3TraceTime!==last){canvas.__i3TraceTime=last;drawTrace(canvas,list,traceDimensions.get(canvas));}}
 for(const canvas of document.querySelectorAll('[data-i3-meter]')){if(!visiblePanel(canvas))continue;const source=packet.audition?.sources?.[canvas.dataset.i3Meter];const level=finite(source?.level_dbfs)?source.level_dbfs:null;const key=(level===null?'off':level.toFixed(1))+(source?.clipped?'c':'')+colors.accent;if(canvas.__i3MeterKey===key)continue;canvas.__i3MeterKey=key;drawMeter(canvas,level,!!source?.clipped);
  const audio=document.querySelector('[data-i3-audio="'+canvas.dataset.i3Meter+'"]');if(audio&&source&&!source.enabled&&audio.getAttribute('src')){audio.pause();audio.removeAttribute('src');audio.load();}}
 const timeline=document.querySelector('[data-i3-timeline]');if(timeline&&visiblePanel(timeline)){const rows=(packet.events||[]).slice(-14).reverse().map(e=>new Date(Number(e.timestamp)*1000).toLocaleTimeString()+'  '+clean(e.channel||e.source||'')+'  '+(finite(e.deviation)?fmt(e.deviation,'number')+' '+clean(e.unit||''):clean(e.message||''))+(e.state?'  '+clean(e.state):'')).join('\n');text(timeline,rows||'No events yet');}
 
 metrics.packetWorkMs=performance.now()-started;
 document.querySelectorAll('[data-i3-cloud]').forEach(el=>text(el,fmt(packet.cloud)));
}
const two=v=>finite(v)?v.toFixed(2).replace(/\u002d/g,'−'):'—';
function fastNumbers(packet){window.__i3Debug.fast=(window.__i3Debug.fast||0)+1;
 /* Direct readouts driven by the 5 Hz stream instead of server callbacks. */
 const c1=packet.channels?.ch1,d=c1?.display||{};
 const c1On=c1?.state==='connected';
 text(document.getElementById('mv-x'),c1On?two(d.x):'—');text(document.getElementById('mv-y'),c1On?two(d.y):'—');text(document.getElementById('mv-z'),c1On?two(d.z):'—');
 text(document.getElementById('mv-c1'),c1On?two(d.magnitude):'—');text(document.getElementById('mv-delta'),c1On?two(c1.deviation):'—');
 const sm=document.getElementById('sum-c1');if(sm)text(sm,c1On?two(d.magnitude)+' unit':'—');
 const ef=packet.channels?.ch2,e=ef?.display||{};const efOn=ef?.state==='connected';const uno=ef?.data_source==='ARDUINO_UNO_USB';
 const x=document.getElementById('ev-level'),y=document.getElementById('ev-index'),rms=document.getElementById('ev-rms'),gain=document.getElementById('ev-gain'),axes=e.axes||{};
 const vm=e.axes_vu||{};
 [[x,vm.x,'X'],[y,vm.y,'Y'],[rms,vm.z,'Z'],[gain,e.magnitude_vu,'MAGNITUDE']].forEach(([node,value,label])=>{text(node,efOn&&finite(value)?two(value):'—');const l=node?.parentElement?.querySelector('.metric-label');if(l)text(l,label);});
 const base=ef?.baseline_vu ?? ef?.baseline?.value;text(document.getElementById('ev-base-top'),efOn&&finite(base)?two(base):'—');text(document.getElementById('ev-delta-top'),efOn&&finite(e.magnitude_vu)?two(Math.abs(e.magnitude_vu-(finite(base)?base:0))):'—');
 const peak=document.getElementById('ev-peak');if(peak){text(peak,uno?'—':(efOn?two(e.peak_mv):'—'));const key=peak.parentElement?.querySelector('.arch-stat-key');text(key,uno?'PEAK — NOT VOLTAGE CALIBRATED':'PEAK mV');}
 if(!uno){const idx=document.getElementById('ev-index');if(idx){const base=ef?.baseline?.value;const ratio=finite(base)&&finite(e.rms_mv)?e.rms_mv/Math.max(Math.abs(base),.008):null;text(idx,efOn&&ratio!==null?Math.round(clamp((ratio-1)/9*100,0,100))+' %':'—');}}
}
function schedulePacket(packet){state.pending=packet;state.lastMessage=Date.now();metrics.streamMessages++;if(!state.paint)state.paint=requestAnimationFrame(()=>{state.paint=0;const next=state.pending;state.pending=null;drawPacket(next);});}
async function snapshot(){const response=await fetch('/api/instrument?compact=1',{cache:'no-store',credentials:'same-origin',signal:AbortSignal.timeout(8000)});if(!response.ok)throw Error('Sensor service returned '+response.status);return response.json();}
function applyStreamChanges(current,patch){
 if(!current||current.sequence!==patch.base)throw Error('Stream reference unavailable');
 for(const path of patch.removed){let parent=current;for(const key of path.slice(0,-1))parent=parent[key];delete parent[path.at(-1)];}
 for(const [path,value] of patch.changes){let parent=current;for(const key of path.slice(0,-1))parent=parent[key];Object.defineProperty(parent,path.at(-1),{value,writable:true,enumerable:true,configurable:true});}
 current.sequence=patch.sequence;return current;
}
function connect(){
 if(state.source)state.source.close();const source=new EventSource('/api/events?delta=1');state.source=source;let current=null;
 const receive=event=>{try{current=JSON.parse(event.data);metrics.streamBytes=(metrics.streamBytes||0)+event.data.length;schedulePacket(current);}catch(error){text(document.getElementById('i3-stream-state'),'Invalid stream packet');}};
 source.onmessage=receive;source.addEventListener('snapshot',receive);source.addEventListener('instrument',receive);source.addEventListener('sensor',receive);
 source.addEventListener('sensor_patch',event=>{try{current=applyStreamChanges(current,JSON.parse(event.data));metrics.streamBytes=(metrics.streamBytes||0)+event.data.length;metrics.streamPatches=(metrics.streamPatches||0)+1;schedulePacket(current);}catch(error){source.close();text(document.getElementById('i3-stream-state'),'Restoring stream snapshot');setTimeout(()=>{if(state.source===source)connect();},250);}});
 source.onopen=()=>{text(document.getElementById('i3-stream-state'),'Connected');};
 source.onerror=()=>text(document.getElementById('i3-stream-state'),'Reconnecting');
}

async function control(payload,result){
 try{const response=await fetch('/api/control',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(12000)});const data=await response.json();if(!response.ok||data.ok===false)throw Error(data.error||data.message||'Control unavailable');if(result)text(result,clean(data.message||'Applied'));snapshot().then(schedulePacket).catch(()=>{});return data;}catch(error){if(result)text(result,clean(error.message));throw error;}
}
/* Live PCM streaming through Web Audio. A chunked WAV stream in an <audio> element is
   refused by Safari ("operation is not supported"), so the stream is read with fetch and
   scheduled onto an AudioContext as it arrives; the <audio> element is only a fallback. */
const i3Stream={ctx:null,players:{},
 prime(){const AC=window.AudioContext||window.webkitAudioContext;if(!AC)return;if(!this.ctx)this.ctx=new AC();this.ctx.resume().catch(()=>{});/* Safari needs a sound started inside the gesture itself */try{const b=this.ctx.createBuffer(1,1,this.ctx.sampleRate);const src=this.ctx.createBufferSource();src.buffer=b;src.connect(this.ctx.destination);src.start(0);}catch(e){}},
 start(key,url,result,audioEl){this.stop(key);const AC=window.AudioContext||window.webkitAudioContext;if(!AC){if(audioEl){audioEl.src=url;audioEl.play().catch(error=>text(result,'Browser blocked playback: '+clean(error.message)));}return;}
  if(!this.ctx)this.ctx=new AC();const ctx=this.ctx;ctx.resume().catch(()=>{});if(ctx.state!=='running')text(result,'Tap Start again to allow sound');const gain=ctx.createGain();gain.connect(ctx.destination);const p={gain,nextT:0,abort:new AbortController(),rate:16000,header:null,rest:new Uint8Array(0),sources:[]};this.players[key]=p;
  fetch(url,{signal:p.abort.signal}).then(async r=>{if(!r.ok||!r.body)throw Error('stream '+r.status);const reader=r.body.getReader();text(result,'Playing');while(true){const {value,done}=await reader.read();if(done)break;if(!value)continue;let bytes=value;if(p.rest.length){const merged=new Uint8Array(p.rest.length+bytes.length);merged.set(p.rest);merged.set(bytes,p.rest.length);bytes=merged;p.rest=new Uint8Array(0);}
    if(!p.header){if(bytes.length<44){p.rest=bytes;continue;}const dv=new DataView(bytes.buffer,bytes.byteOffset,44);p.rate=dv.getUint32(24,true)||16000;p.header=true;bytes=bytes.subarray(44);}
    const even=bytes.length-(bytes.length%2);if(bytes.length>even)p.rest=bytes.slice(even);const pcm=new Int16Array(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+even));if(!pcm.length)continue;
    const buf=ctx.createBuffer(1,pcm.length,p.rate);const ch=buf.getChannelData(0);for(let i=0;i<pcm.length;i++)ch[i]=pcm[i]/32768;const src=ctx.createBufferSource();src.buffer=buf;src.connect(gain);const now=ctx.currentTime;if(p.nextT<now+.05)p.nextT=now+.12;src.start(p.nextT);p.nextT+=buf.duration;p.sources.push(src);src.onended=()=>{const i=p.sources.indexOf(src);if(i>=0)p.sources.splice(i,1);};}
  }).catch(error=>{if(error.name!=='AbortError')text(result,'Stream ended: '+clean(error.message));});},
 stop(key){const p=this.players[key];if(!p)return;try{p.abort.abort();}catch(e){}for(const s of p.sources){try{s.stop();}catch(e){}}try{p.gain.disconnect();}catch(e){}delete this.players[key];},
 mute(key,muted){const p=this.players[key];if(p)p.gain.gain.value=muted?0:1;}};
function setupControls(){
 document.addEventListener('click',event=>{
 const button=event.target.closest('[data-i3-action]');if(!button)return;
 const action=button.dataset.i3Action,form=button.closest('form'),result=form?.querySelector('[data-i3-result]')||document.getElementById('i3-control-result');
 let payload={action};
 if(action==='agent'){agentToggle();return;}
 if(action==='mode_toggle'){const next=state.packet?.mode?.mode==='offline'?'online':'offline';payload.mode=next;payload.action='mode';button.disabled=true;control(payload,result).then(()=>text(result,'Instrument mode: '+next)).catch(()=>{}).finally(()=>{button.disabled=false;});return;}
 if(action==='camera'){
  if(window.__i3HandVisionRunning||window.__i3HandVisionStarting){window.__i3StopHandVision?.();window.__i3HandVisionRunning=false;window.__i3HandVisionStarting=false;try{localStorage.setItem('i3-camera','off');}catch(error){}text(result,'Browser camera released');syncCameraButton();return;}
  try{localStorage.setItem('i3-camera','on');}catch(error){}
  if(!navigator.mediaDevices?.getUserMedia&&location.protocol!=='https:'){text(result,'Switching to the secure page for the camera');setTimeout(()=>{location.href=httpsLink();},400);return;}
  if(navigator.mediaDevices?.getUserMedia&&window.__i3StartHandVision){
   retargetHandVision();const target=Array.from(document.querySelectorAll('canvas')).find(c=>c.__i3LegacyHandControls===window.__i3HandControls);
   window.__i3StartHandVision(target||null,target?.__i3LegacyHandControls||{rotate:function(dx){physics.impulse(dx*3,0);},zoom:function(){}});
   text(result,'Requesting the browser camera');setTimeout(syncCameraButton,1500);return;
  }
  payload.enabled=!state.packet?.camera?.enabled;
  button.disabled=true;control(payload,result).then(()=>{setTimeout(()=>{const cam=state.packet?.camera;if(payload.enabled&&cam&&cam.state!=='connected'&&cam.state!=='initialising')text(result,'No camera on the instrument ('+clean(cam.error||cam.state)+'). The browser camera needs http://localhost or HTTPS.');},2500);}).catch(()=>{}).finally(()=>{button.disabled=false;});return;
 }
 if(action==='baseline'){
  const selected=form?.elements.namedItem('channel')?.value;payload.channel=selected==='all'?null:selected;
  const op=button.dataset.i3Op;const windowValue=Number(form?.elements.namedItem('window')?.value);if(op==='window'&&finite(windowValue)&&windowValue>0)payload.window=windowValue;
  if(op==='relock')payload.relock=true;if(op==='freeze')payload.freeze=true;if(op==='resume')payload.freeze=false;
 }
 if(action==='calibrate'){
  if(!form.reportValidity())return;
  for(const name of ['channel','unit','method'])payload[name]=form.elements.namedItem(name).value;
  payload.raw_reference=['raw_low','raw_high'].map(name=>Number(form.elements.namedItem(name).value));payload.known_reference=['known_low','known_high'].map(name=>Number(form.elements.namedItem(name).value));payload.uncertainty=Number(form.elements.namedItem('uncertainty').value);
 }
 if(action==='reset_calibration')payload.channel=form.elements.namedItem('channel').value;
 if(action==='agent_stop'){agentInterrupt('stopped');return;}
 if(action==='hand_calibrate'){handCalibrate();return;}
 if(action==='left_handed'){setLeftHanded(!leftHanded());fmToast(leftHanded()?'LEFT-HANDED · left hand points, right hand scrolls':'RIGHT-HANDED · right hand points, left hand scrolls');return;}
 if(action==='hand_tracking'){document.getElementById('i3-camera-toggle')?.click();setTimeout(syncCameraButton,400);return;}
 if(action==='cursor_mode'){setCursorMode(cursorMode()==='iv'?'mac':'iv');fmToast(cursorMode()==='iv'?'IV CURSOR · system pointer hidden':'MAC CURSOR · IV cursor only for the hand');return;}
 if(action==='buddy_toggle'){setBuddyEnabled(!buddyOn());fmToast(buddyOn()?'NVTRA CHARACTER ON':'NVTRA CHARACTER OFF');return;}
 if(action==='hand_debug'){fingerMouse.debug=!fingerMouse.debug;try{localStorage.setItem('i3-hand-debug',fingerMouse.debug?'on':'off');}catch(e){}syncHandProfileNote();if(!fingerMouse.debug)handDebug([],{},{});return;}
 if(action==='hand_profile_reset'){hpReset();syncHandProfileNote();fmToast('HAND PROFILE RESET');return;}
 if(action==='hand3d'){fingerMouse.hand3d=!fingerMouse.hand3d;try{localStorage.setItem('i3-hand3d',fingerMouse.hand3d?'on':'off');}catch(e){}if(!fingerMouse.hand3d&&fingerMouse.hold)fmHold(null);syncHand3d();return;}
 if(action==='elevenlabs_key')payload.key=form.elements.namedItem('key').value;
 if(action==='elevenlabs_voice'){payload.voice=form.elements.namedItem('voice').value;if(!payload.voice){text(result,'Pick a voice first');return;}}
 if(action==='voice_preview'){const voice=form.elements.namedItem('voice').value;if(!voice){text(result,'Pick a voice first');return;}button.disabled=true;text(result,'Fetching a sample…');fetch('/api/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:'Hi, I am NVTRA, your studio voice. All channels steady.',voice}),signal:AbortSignal.timeout(20000)}).then(async r=>{if(!r.ok){const d=await r.json().catch(()=>({}));throw Error(d.error||'Voice unavailable');}return r.blob();}).then(b=>{const a=new Audio(URL.createObjectURL(b));a.play();text(result,'Playing sample');}).catch(e=>text(result,clean(e.message))).finally(()=>{button.disabled=false;});return;}
 if(action==='audition'){
  const key=button.dataset.i3Source,op=button.dataset.i3Op;payload.source=key;if(op==='start')i3Stream.prime();
  if(key==='p1'){const form2=form;const both=['ch2f','c1'];button.disabled=true;
   if(op==='start'){(async()=>{for(const k of both){try{await control({action:'audition',source:k,enabled:true,gain:k==='ch2f'?4:1},result);i3Stream.start(k,'/api/audition/'+k+'.wav?t='+Date.now(),result,null);}catch(e){}}})().finally(()=>{button.disabled=false;});return;}
   if(op==='stop'){both.forEach(k=>i3Stream.stop(k));(async()=>{for(const k of both){try{await control({action:'audition',source:k,enabled:false},result);}catch(e){}}})().finally(()=>{button.disabled=false;});return;}
   if(op==='mute'){const muted=button.getAttribute('aria-pressed')!=='true';button.setAttribute('aria-pressed',String(muted));both.forEach(k=>i3Stream.mute(k,muted));button.disabled=false;return;}}
  const audio=document.querySelector('[data-i3-audio="'+key+'"]');
  if(op==='start'){payload.enabled=true;payload.gain=Number(form.elements.namedItem('gain')?.value)||1;}
  if(op==='stop'){payload.enabled=false;i3Stream.stop(key);if(audio){audio.pause();audio.removeAttribute('src');audio.load();}}
  if(op==='mute'){const muted=button.getAttribute('aria-pressed')!=='true';payload.mute=muted;button.setAttribute('aria-pressed',String(muted));i3Stream.mute(key,muted);if(audio)audio.muted=muted;}
  if(op==='tune'){payload.frequency_hz=Number(form.elements.namedItem('frequency_mhz').value)*1e6;payload.mode=form.elements.namedItem('mode').value;}
  button.disabled=true;control(payload,result).then(()=>{if(op==='start')i3Stream.start(key,'/api/audition/'+key+'.wav?t='+Date.now(),result,audio);}).catch(()=>{}).finally(()=>{button.disabled=false;});return;
 }
 button.disabled=true;control(payload,result).catch(()=>{}).finally(()=>{button.disabled=false;});
 });
 document.addEventListener('change',event=>{const form=event.target.closest('[data-i3-form=calibration]');if(form&&event.target.name==='channel')form.elements.namedItem('unit').value={ch1:'unit',ch2:'V/m',ch3:'dB',current:'A'}[event.target.value];});
 let gainTimer=null;document.addEventListener('input',event=>{if(!event.target.classList?.contains('i3-gain'))return;const key=(event.target.closest('[data-i3-form]')?.dataset.i3Form||'').replace('audition-','');if(!key)return;clearTimeout(gainTimer);gainTimer=setTimeout(()=>control({action:'audition',source:key,gain:Number(event.target.value)}).catch(()=>{}),120);});
 document.addEventListener('submit',event=>{if(event.target?.matches?.('[data-i3-form]'))event.preventDefault();});

 function syncHand3d(){document.querySelectorAll('[data-i3-action=hand3d]').forEach(b=>{b.setAttribute('aria-pressed',String(fingerMouse.hand3d));text(b,fingerMouse.hand3d?'3D HAND CONTROL: ON':'3D HAND CONTROL: OFF');});const note=document.querySelector('[data-i3-hand3d-note]');if(note)text(note,fingerMouse.hand3d?'Pinch on the Earth or the constellation to hold, spin and zoom it with your hands.':'Hand gestures leave the 3D objects alone; pinching one is a plain click. Cursor, clicks and scrolling still work.');}
 new MutationObserver(()=>syncHand3d()).observe(document.body,{childList:true,subtree:true});syncHand3d();
 /* Zoom faces: a native range mirrors into the hidden Dash slider through its number input. */
 function mountZoomFaces(){document.querySelectorAll('[data-i3-zoom-face]:empty').forEach(face=>{const id=face.dataset.i3ZoomFace;const dash=document.getElementById(id);const inp=dash?.querySelector('input');const thumb=dash?.querySelector('[role=slider]');const range=document.createElement('input');range.type='range';range.min='-1';range.max='3';range.step='0.25';range.value=inp?.value||'0';range.setAttribute('aria-label','Zoom');face.appendChild(range);const push=async()=>{const thumb=document.getElementById(id)?.querySelector('[role=slider]');if(!thumb||push.busy)return;push.busy=true;try{const target=Number(range.value),step=.25,min=-1;const key=e=>{thumb.dispatchEvent(new KeyboardEvent('keydown',{key:e,bubbles:true,cancelable:true}));return new Promise(r=>setTimeout(r,16));};/* Dash commits slider values on keyboard steps: jump to the start, then step up */let cur=Number(thumb.getAttribute('aria-valuenow'));if(Math.abs(cur-target)<1e-6)return;const fromStart=Math.round((target-min)/step),fromCur=Math.round((target-cur)/step);if(Math.abs(fromCur)<=fromStart){for(let i=0;i<Math.abs(fromCur);i++)await key(fromCur>0?'ArrowRight':'ArrowLeft');}else{await key('Home');for(let i=0;i<fromStart;i++)await key('ArrowRight');}}finally{push.busy=false;if(Number(document.getElementById(id)?.querySelector('[role=slider]')?.getAttribute('aria-valuenow'))!==Number(range.value))setTimeout(push,60);}};let t=0;range.addEventListener('input',()=>{clearTimeout(t);t=setTimeout(push,120);});range.addEventListener('change',push);const thumb2=document.getElementById(id)?.querySelector('[role=slider]');if(thumb2)new MutationObserver(()=>{const v=thumb2.getAttribute('aria-valuenow');if(v!==null&&document.activeElement!==range&&range.value!==v)range.value=v;}).observe(thumb2,{attributes:true,attributeFilter:['aria-valuenow']});});}
 new MutationObserver(()=>mountZoomFaces()).observe(document.body,{childList:true,subtree:true});mountZoomFaces();
 /* Lunar Gravity loads three.js only when its card is on the page */
 const loadScript=(src,ready)=>new Promise((res,rej)=>{if(ready?.()){res();return;}const found=document.querySelector('script[src="'+src+'"]');if(found){found.addEventListener('load',res,{once:true});found.addEventListener('error',rej,{once:true});return;}const s=document.createElement('script');s.src=src;s.onload=()=>{s.dataset.ready='1';res();};s.onerror=rej;document.head.appendChild(s);});
 function mountLunar(){const host=document.querySelector('[data-i3-lunar]:not([data-lunar-init])');if(!host)return;host.dataset.lunarInit='0';loadScript('/assets/lunar/three.min.js',()=>!!window.THREE).then(()=>loadScript('/assets/lunar/lunar.js',()=>typeof window.__i3LunarMount==='function')).then(()=>{window.__i3LunarMount(host);retargetHandVision();}).catch(()=>{host.textContent='Could not load the 3D module.';});}
 new MutationObserver(()=>mountLunar()).observe(document.body,{childList:true,subtree:true});mountLunar();
 /* Settings voice picker: filled from /api/voices whenever the select appears on the page. */
 async function fillVoices(){const sel=document.querySelector('select[data-i3-voices]:not([data-filled])');if(!sel)return;sel.dataset.filled='1';try{const data=await(await fetch('/api/voices')).json();const voices=data.voices||[];if(!voices.length){sel.innerHTML='<option value="">Save a voice key first</option>';return;}sel.innerHTML='';for(const v of voices){const o=document.createElement('option');o.value=v.id;o.textContent=v.name+(v.description?' · '+v.description:'')+(v.gender||v.accent?' ('+[v.gender,v.accent].filter(Boolean).join(', ')+')':'')+(v.free?'':' · paid plan');o.selected=v.id===data.active;sel.appendChild(o);}}catch(error){sel.innerHTML='<option value="">Voices unavailable</option>';}}
 new MutationObserver(()=>fillVoices()).observe(document.body,{childList:true,subtree:true});fillVoices();
 /* NVTRA engine picker in the island: the local model plus every stored key; offline lists the local model only */
 async function fillEngines(){const sels=document.querySelectorAll('select[data-i3-engine]');if(!sels.length)return;try{const data=await(await fetch('/api/engines')).json();const list=data.engines||[];sels.forEach(sel=>{sel.innerHTML='';for(const e of list){const o=document.createElement('option');o.value=e.id;o.textContent=(e.id==='local'?'Local · ':'')+e.label+' · '+e.model+(e.available?'':' (not running)');o.selected=!!e.active;o.disabled=!e.available;sel.appendChild(o);}sel.dataset.filled='1';});}catch(error){}}
 window.__i3FillEngines=fillEngines;
 document.addEventListener('change',event=>{const sel=event.target.closest('select[data-i3-engine]');if(!sel||!sel.value)return;control({action:'ai_engine',id:sel.value},null).then(()=>{fillEngines();orbShow('Engine · '+sel.options[sel.selectedIndex].textContent,'');setTimeout(orbHide,1600);}).catch(()=>{});});
 setTimeout(fillEngines,1500);
 document.addEventListener('keydown',event=>{if(event.target?.matches?.('input,textarea,select')||event.altKey||event.ctrlKey||event.metaKey)return;if(event.key==='c'){document.getElementById('i3-camera-toggle')?.click();}if(event.key==='n'){if(agent.listening&&!agent.busy){orbShow('Listening','');agent.awake=true;agent.awakeAt=performance.now();}else agentToggle();}});
}
/* ---------------------------------------------------------------------------
   SCRUB HEROES. A port of two scroll-locked, scrub-driven heroes ("Airlock" and
   "Skyline") to plain JS for this Dash page. While a hero owns the screen the
   body is pinned with position:fixed and wheel, touch, key and hand-scroll input
   is spent on the hero's progress instead of the page; once the sequence ends
   and the reader keeps pushing, the page is handed back. Climbing back to the
   top takes the lock again at full progress so the sequence runs backwards.
   Instead of stock footage each hero paints its own sequence on a canvas from
   the instrument's own imagery: the fieldsphere (Home) and a skyline of
   transmission masts under a setting field (Page 3). Works offline.
   --------------------------------------------------------------------------- */
const scrub={hero:null,locked:false,lockedY:0,released:false,lastY:0,target:0,shown:0,moved:false,raf:0,painter:null,el:{}};
const SCRUB_DISTANCE=3200,HOLD_DISTANCE=1100;
function scrubActive(){return !!scrub.hero&&scrub.hero.isConnected&&!scrub.hero.classList.contains('i3-hero-hidden');}
function scrubLock(){if(scrub.locked)return;scrub.locked=true;scrub.released=false;scrub.lockedY=scrollY;const b=document.body.style;b.position='fixed';b.top='-'+scrub.lockedY+'px';b.left='0';b.right='0';b.width='100%';b.minHeight='100vh';document.documentElement.classList.add('i3-scrub-locked');}
function scrubRelease(settle){if(!scrub.locked)return;scrub.locked=false;const y=scrub.lockedY;const b=document.body.style;b.position='';b.top='';b.left='';b.right='';b.width='';b.minHeight='';document.documentElement.classList.remove('i3-scrub-locked');scrollTo(0,y);scrub.released=true;scrub.lastY=y;scrub.cooldownUntil=performance.now()+700;
 if(settle&&scrub.hero){const top=Math.max(0,scrub.hero.offsetTop-72);scrub.hero.classList.add('i3-hero-hidden');cancelAnimationFrame(scrub.raf);scrollTo(0,top);scrub.lastY=top;}}
/* Spends a gesture on the hero. True means the hero used it and the caller must swallow the event. */
function scrubConsume(deltaY){if(!scrub.locked)return false;if(scrub.target>=1&&scrub.shown>.98&&deltaY>0){scrubRelease(true);return true;}scrub.target=clamp(scrub.target+deltaY/(SCRUB_DISTANCE+HOLD_DISTANCE),0,1);if(scrub.target>.001)scrub.moved=true;return true;}
window.__i3ScrubConsume=scrubConsume;
function scrubPaint(p){const share=SCRUB_DISTANCE/(SCRUB_DISTANCE+HOLD_DISTANCE);const v=clamp(p/share,0,1);const e=scrub.el;if(scrub.painter)scrub.painter(v,p);
 const titleA=1-clamp(v/.35,0,1),tagA=clamp((v-.82)/.18,0,1);
 if(e.scrim)e.scrim.style.opacity=String(Math.max(titleA,tagA));
 if(e.title){e.title.style.opacity=String(titleA);e.title.style.transform='translateY('+((1-titleA)*-24).toFixed(1)+'px)';}
 if(e.tag){e.tag.style.opacity=String(tagA);e.tag.style.transform='translateY('+((1-tagA)*20).toFixed(1)+'px)';}
 if(e.hint)e.hint.style.opacity=scrub.moved?'0':'1';
 if(e.bar)e.bar.style.transform='scaleX('+p.toFixed(4)+')';}
function scrubFrame(now){if(!scrubActive()){scrub.raf=0;return;}const dt=scrub.lastFrame?Math.min(50,now-scrub.lastFrame):1000/60;scrub.lastFrame=now;const previous=scrub.shown;scrub.shown+=(scrub.target-scrub.shown)*(1-Math.pow(.82,dt/(1000/60)));if(Math.abs(scrub.target-scrub.shown)<.00001)scrub.shown=scrub.target;if(scrub.shown!==previous||!scrub.painted){scrubPaint(scrub.shown);scrub.painted=true;}
 /* watchdog: a finished sequence that is still holding the page after a moment lets go on its own */
 if(scrub.locked&&scrub.target>=1&&scrub.shown>.985){scrubRelease(true);return;}
 scrub.raf=requestAnimationFrame(scrubFrame);}
const SCRUB_KEYS={ArrowDown:140,ArrowUp:-140,PageDown:700,PageUp:-700,' ':700,End:1e9,Home:-1e9};
addEventListener('wheel',e=>{if(!scrubActive())return;if(scrubConsume(e.deltaY))e.preventDefault();},{passive:false});
let scrubTouchY=0;addEventListener('touchstart',e=>{scrubTouchY=e.touches[0]?.clientY??0;},{passive:true});
addEventListener('touchmove',e=>{if(!scrubActive())return;const y=e.touches[0]?.clientY??scrubTouchY;const d=scrubTouchY-y;scrubTouchY=y;if(scrubConsume(d))e.preventDefault();},{passive:false});
addEventListener('keydown',e=>{if(!scrubActive()||e.target.matches?.('input,textarea,select'))return;if(e.key==='Escape'&&scrub.locked){scrub.target=scrub.shown=1;scrub.moved=true;scrubPaint(1);scrubRelease(true);return;}const step=SCRUB_KEYS[e.key];if(step===undefined)return;if(scrubConsume(step))e.preventDefault();});
function scrubExit(){if(!scrubActive()||scrub.locked)return;const h=scrub.hero.offsetHeight||1;const k=clamp((scrollY-scrub.hero.offsetTop)/h,0,1);const st=scrub.el.stage;if(st){st.style.transform='translate3d(0,'+(-k*22).toFixed(2)+'vh,0) scale('+(1+k*.28).toFixed(3)+')';st.style.opacity=String(1-k*1.15);}}
addEventListener('scroll',scrubExit,{passive:true});
function scrubTeardown(){if(scrub.locked)scrubRelease();scrub.doneSince=0;cancelAnimationFrame(scrub.raf);scrub.raf=0;
 /* React reuses the hero node across pages: strip everything this mount injected so the next
    page's opening never draws on top of (or inherits) the previous one. */
 if(scrub.hero){scrub.hero.querySelectorAll('.i3-scrub-stage,.i3-scrub-grad,.i3-scrub-skip,.i3-scrub-rail,.i3-scrub-video').forEach(n=>n.remove());}
 scrub.hero=null;scrub.kind=null;scrub.painter=null;scrub.el={};}
/* Page effects play once per page load (startup or refresh), never again when switching tabs. */
const heroSeenSet=new Set();function heroSeen(key){return heroSeenSet.has(key);}function heroMarkSeen(key){heroSeenSet.add(key);}
function scrubMount(hero){scrubTeardown();heroMarkSeen('hero:'+hero.dataset.i3Scrub);hero.classList.remove('i3-hero-hidden');scrub.hero=hero;scrub.kind=hero.dataset.i3Scrub;scrub.lastFrame=0;scrub.painted=false;scrub.target=scrub.shown=0;scrub.moved=false;scrub.released=false;
 const kind=hero.dataset.i3Scrub;const stage=document.createElement('div');stage.className='i3-scrub-stage';hero.appendChild(stage);const c=document.createElement('canvas');c.className='i3-scrub-canvas';stage.appendChild(c);
 const grad=document.createElement('div');grad.className='i3-scrub-grad';hero.appendChild(grad);
 const scrim=document.createElement('div');scrim.className='i3-scrub-scrim';stage.appendChild(scrim);
 const title=document.createElement('div');title.className='i3-scrub-title'+(hero.dataset.i3Title.length>40?' i3-scrub-title-long':'');{const h1=document.createElement('h1');h1.textContent=hero.dataset.i3Title;title.appendChild(h1);}stage.appendChild(title);
 const tag=document.createElement('div');tag.className='i3-scrub-tag';{const para=document.createElement('p');para.textContent=hero.dataset.i3Tagline;tag.appendChild(para);}stage.appendChild(tag);
 const hint=document.createElement('div');hint.className='i3-scrub-hint';hint.innerHTML='<span>SCROLL</span><svg width="14" height="18" viewBox="0 0 14 18" aria-hidden="true"><path d="M7 1 L7 17 M2 12 L7 17 L12 12" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>';stage.appendChild(hint);
 const skip=document.createElement('button');skip.type='button';skip.className='i3-scrub-skip';skip.textContent='Skip';skip.addEventListener('click',()=>{scrub.target=scrub.shown=1;scrub.moved=true;scrubPaint(1);scrubRelease(true);});hero.appendChild(skip);
 const rail=document.createElement('div');rail.className='i3-scrub-rail';const bar=document.createElement('div');bar.className='i3-scrub-bar';rail.appendChild(bar);hero.appendChild(rail);
 scrub.el={canvas:c,scrim,title,tag,hint,bar,stage};
 scrub.painter=kind==='airlock'?airlockPainter(c,stage,hero):(kind==='skyline'?skylinePainter:(kind==='mtdi-flow'?mtdiFlowPainter:(kind==='p1-vector'?emVectorPainter:fieldPainter)))(c);
 const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)').matches;
 if(reducedMotion){hero.classList.add('i3-hero-hidden');return;}
 /* Lock once the startup intro is gone and the hero is at the top of the page. */
 const tryLock=()=>{if(scrub.hero!==hero||!hero.isConnected)return;if(document.getElementById('startup-intro')){setTimeout(tryLock,300);return;}/* a freshly opened page starts on its hero */if(scrollY>hero.offsetTop+1&&performance.now()-scrub.mountedAt<1500)scrollTo(0,hero.offsetTop);if(scrollY<=hero.offsetTop+1)scrubLock();else{scrub.released=true;scrub.lastY=scrollY;scrub.target=scrub.shown=1;scrub.moved=true;scrubPaint(1);}};scrub.mountedAt=performance.now();tryLock();
 scrub.raf=requestAnimationFrame(scrubFrame);}
/* One opening per page kind, keyed by data-i3-scrub rather than by DOM node: the node is
   often the same element re-labelled by React when the route changes. */
window.__i3Scrub=scrub;
function scrubSync(){const hero=document.querySelector('[data-i3-scrub]');
 if(scrub.hero&&(!hero||hero!==scrub.hero||hero.dataset.i3Scrub!==scrub.kind))scrubTeardown();
 if(!hero)return;const kind=hero.dataset.i3Scrub;
 if(scrub.hero===hero)return;
 if(heroSeen('hero:'+kind)){hero.classList.add('i3-hero-hidden');hero.querySelectorAll('.i3-scrub-stage,.i3-scrub-grad,.i3-scrub-skip,.i3-scrub-rail,.i3-scrub-video').forEach(n=>n.remove());return;}
 scrubMount(hero);}
new MutationObserver(()=>{scrubSync();
 const pin=document.querySelector('.parallax__pin:not([data-i3-seen])');if(pin){pin.dataset.i3Seen='1';const key='parallax:'+location.pathname;if(heroSeen(key))pin.classList.add('i3-parallax-complete');else heroMarkSeen(key);}}).observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['data-i3-scrub']});
/* --- painters -------------------------------------------------------------- */
function scrubSize(c){const r=c.parentElement.getBoundingClientRect(),ratio=Math.min(devicePixelRatio||1,2);const w=Math.max(1,Math.round(r.width*ratio)),h=Math.max(1,Math.round(r.height*ratio));if(c.width!==w||c.height!==h){c.width=w;c.height=h;}return {w:r.width,h:r.height,ratio};}
function seeded(n){let s=n>>>0;return()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296;};}
function mtdiFlowPainter(c){
 const nodes=[
  {x:.18,y:.22,w:.25,title:'CHANNEL 1',copy:'TEXT · TEXT · UNIT',at:.02},
  {x:.50,y:.22,w:.25,title:'CHANNEL 2',copy:'TEXT · TEXT · UNIT',at:.07},
  {x:.82,y:.22,w:.25,title:'CHANNEL 3',copy:'TEXT · TEXT · UNIT',at:.12},
  {x:.31,y:.44,w:.35,title:'VALIDATION CHAMBER',copy:'TEXT · TEXT · TEXT',at:.30},
  {x:.69,y:.44,w:.35,title:'ENVIRONMENTAL INTELLIGENCE',copy:'TEXT · TEXT',at:.36},
  {x:.50,y:.64,w:.48,title:'MTDI FUSION LAYER',copy:'TEXT · TEXT · TEXT',at:.55,core:true},
  {x:.29,y:.83,w:.35,title:'I³ DASHBOARD',copy:'TEXT · TEXT · TEXT',at:.76},
  {x:.71,y:.83,w:.35,title:'NVTRA EXPLANATION',copy:'TEXT · TEXT',at:.82}
 ];
 const links=[[0,3],[1,3],[1,4],[2,4],[3,5],[4,5],[5,6],[5,7]];
 const ease=x=>x<=0?0:x>=1?1:x*x*(3-2*x);
 return function(v){const {w,h,ratio}=scrubSize(c),ctx=c.getContext('2d');if(!(w>0&&h>0))return;ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,w,h);
  const compact=w<650,top=compact?h*.13:h*.08,usable=h*(compact?.78:.84),boxH=Math.min(compact?62:76,h*.1);ctx.lineCap='round';
  function pos(n){return {x:n.x*w,y:top+n.y*usable};}
  for(let i=0;i<links.length;i++){const a=nodes[links[i][0]],b=nodes[links[i][1]],pa=pos(a),pb=pos(b),q=ease((v-(.18+i*.045))/.22);if(q<=0)continue;const sy=pa.y+boxH/2,ey=pb.y-boxH/2,mid=(sy+ey)/2;ctx.strokeStyle='rgba(86,208,236,'+(.22+.65*q)+')';ctx.lineWidth=1.2;ctx.beginPath();ctx.moveTo(pa.x,sy);ctx.lineTo(pa.x,mid);ctx.lineTo(pb.x,mid);ctx.lineTo(pb.x+(pa.x-pb.x)*(1-q),ey+(mid-ey)*(1-q));ctx.stroke();if(q>.92){ctx.fillStyle='#8ff5ff';ctx.beginPath();ctx.arc(pb.x,ey,2.2,0,7);ctx.fill();}}
  nodes.forEach((n,i)=>{const a=ease((v-n.at)/.18);if(a<=0)return;const p=pos(n),bw=Math.min(n.w*w,compact?w*.42:360),bh=boxH;ctx.save();ctx.globalAlpha=a;ctx.translate(0,(1-a)*18);ctx.fillStyle=n.core?'rgba(17,64,88,.94)':'rgba(10,28,48,.90)';ctx.strokeStyle=n.core?'rgba(75,230,241,.94)':'rgba(106,178,230,.64)';ctx.lineWidth=n.core?1.7:1;ctx.beginPath();ctx.roundRect(p.x-bw/2,p.y-bh/2,bw,bh,10);ctx.fill();ctx.stroke();if(n.core){ctx.shadowColor='rgba(49,215,230,.45)';ctx.shadowBlur=24;ctx.stroke();ctx.shadowBlur=0;}ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle='#eaf7ff';ctx.font='700 '+(compact?9:12)+'px DM Mono,monospace';ctx.fillText(n.title,p.x,p.y-9);ctx.fillStyle='rgba(178,205,224,.82)';ctx.font=(compact?7:9)+'px DM Mono,monospace';ctx.fillText(n.copy,p.x,p.y+11);ctx.restore();});
  ctx.textAlign='center';ctx.fillStyle='rgba(150,189,211,'+ease((v-.86)/.12)+')';ctx.font='italic '+(compact?8:10)+'px DM Mono,monospace';ctx.fillText('ENTER YOUR TEXT HERE.',w/2,h*.965);
 };}
/* Fieldsphere: Earth and twopole field lines; no decorative star field. */
/* Airlock: the sequence is a video, scrubbed by seeking. Seeks queue behind the one in
   flight, and the last 40 ms are never requested because seeking to the very end paints
   black in some browsers. The poster covers the wait for the first decodable frame. */
function airlockPainter(c,stage,hero){c.remove();const video=document.createElement('video');video.className='i3-scrub-video';video.muted=true;video.playsInline=true;video.preload='auto';video.setAttribute('aria-hidden','true');video.poster=hero.dataset.i3Poster||'';video.src=hero.dataset.i3Video;stage.insertBefore(video,stage.firstChild);
 let duration=0,seeking=false,queued=null;const seek=t=>{if(seeking){queued=t;return;}seeking=true;video.currentTime=t;};
 video.addEventListener('seeked',()=>{seeking=false;if(queued!==null){const t=queued;queued=null;seeking=true;video.currentTime=t;}});
 video.addEventListener('loadeddata',()=>{duration=video.duration||0;video.classList.add('ready');seek(0);});
 video.addEventListener('loadedmetadata',()=>{duration=video.duration||0;});
 return function(v){if(duration>0)seek(Math.min(v*duration,duration-.04));video.style.transform='scale('+(1+v*.06).toFixed(3)+')';};}
function fieldPainter(c){
 /* Fieldsphere: a shaded Earth drawn as an instrument would draw it (graticule, terminator,
    atmosphere rim) with twopole field lines that trace in as the scene scrubs. Decorative:
    nothing here is measured. Static geometry is cached per size. */
 let cache=null;
 return function(v){const {w,h,ratio}=scrubSize(c);const ctx=c.getContext('2d');
  /* Before layout gives the canvas a size, R is 0 and the rim radius below (R minus half a
     line width, floored at 1.2) goes negative, which throws IndexSizeError. There is also
     nothing worth painting into a zero-sized canvas; the next frame repaints at full size. */
  if(!(w>0&&h>0))return;
  ctx.setTransform(ratio,0,0,ratio,0,0);
  ctx.clearRect(0,0,w,h);
  const R=Math.min(w,h)*(.40+v*.12),cx=w*.5,cy=h*(1.08-v*.30);
  /* outer atmosphere */
  const glow=ctx.createRadialGradient(cx,cy,R*.92,cx,cy,R*1.42);glow.addColorStop(0,'rgba(49,215,230,.30)');glow.addColorStop(.45,'rgba(41,121,255,.10)');glow.addColorStop(1,'rgba(41,121,255,0)');ctx.fillStyle=glow;ctx.beginPath();ctx.arc(cx,cy,R*1.42,0,7);ctx.fill();
  /* body: lit from upper left, deep limb */
  const body=ctx.createRadialGradient(cx-R*.42,cy-R*.46,R*.05,cx,cy,R*1.02);body.addColorStop(0,'#3d8fe8');body.addColorStop(.35,'#1b57b8');body.addColorStop(.72,'#0b2a66');body.addColorStop(1,'#030b1e');ctx.fillStyle=body;ctx.beginPath();ctx.arc(cx,cy,R,0,7);ctx.fill();
  ctx.save();ctx.beginPath();ctx.arc(cx,cy,R,0,7);ctx.clip();
  /* graticule: meridians and parallels of a sphere tilted 23 degrees, drawn as ellipses */
  const tilt=-.40;ctx.save();ctx.translate(cx,cy);ctx.rotate(tilt);ctx.lineWidth=1;
  for(let i=1;i<6;i++){const y=R*Math.sin((i-3)*Math.PI/6.5);const rx=Math.sqrt(Math.max(0,R*R-y*y));ctx.strokeStyle='rgba(160,220,255,'+(i===3?.22:.12)+')';ctx.beginPath();ctx.ellipse(0,y,rx,rx*.16,0,0,7);ctx.stroke();}
  for(let i=0;i<7;i++){const a=i*Math.PI/7+v*.9;const rx=Math.abs(Math.cos(a))*R;ctx.strokeStyle='rgba(160,220,255,'+(.08+.10*Math.abs(Math.sin(a)))+')';ctx.beginPath();ctx.ellipse(0,0,Math.max(.6,rx),R,0,0,7);ctx.stroke();}
  ctx.restore();
  /* terminator: night side falls off to the lower right */
  const night=ctx.createLinearGradient(cx-R*.2,cy-R*.6,cx+R*.9,cy+R*.6);night.addColorStop(0,'rgba(2,8,24,0)');night.addColorStop(.55,'rgba(2,8,24,.35)');night.addColorStop(1,'rgba(2,8,24,.92)');ctx.fillStyle=night;ctx.fillRect(cx-R,cy-R,2*R,2*R);
  /* specular */
  const spec=ctx.createRadialGradient(cx-R*.5,cy-R*.52,0,cx-R*.5,cy-R*.52,R*.5);spec.addColorStop(0,'rgba(230,250,255,.28)');spec.addColorStop(1,'rgba(230,250,255,0)');ctx.fillStyle=spec;ctx.fillRect(cx-R,cy-R,2*R,2*R);
  ctx.restore();
  /* atmosphere rim: thin bright limb, brighter on the lit side */
  const rim=ctx.createLinearGradient(cx-R,cy-R,cx+R,cy+R);rim.addColorStop(0,'rgba(140,235,255,.85)');rim.addColorStop(.6,'rgba(49,215,230,.35)');rim.addColorStop(1,'rgba(49,215,230,.08)');ctx.strokeStyle=rim;ctx.lineWidth=Math.max(1.2,R*.012);ctx.beginPath();ctx.arc(cx,cy,Math.max(0,R-ctx.lineWidth*.5),0,7);ctx.stroke();
  /* twopole field lines r = L cos^2(lat), tapering and fading with distance, drawn in with progress */
  for(let k=0;k<7;k++){const L=R*(1.22+k*.30);const frac=clamp(v*1.35-k*.05,0,1);if(frac<=0)continue;
   for(const side of [1,-1]){ctx.beginPath();const steps=110;let started=false;for(let i=0;i<=steps*frac;i++){const lat=-Math.PI/2+Math.PI*i/steps;const r=L*Math.cos(lat)*Math.cos(lat);if(r<R*.99){started=false;continue;}const x=cx+side*r*Math.cos(lat),y=cy-r*Math.sin(lat);if(!started){ctx.moveTo(x,y);started=true;}else ctx.lineTo(x,y);}
    ctx.lineWidth=1.6-k*.14;ctx.strokeStyle='rgba(49,215,230,'+(.55-k*.065).toFixed(2)+')';ctx.stroke();}
   /* particles riding the outermost visible line */
   if(k<3){const n=4;for(let j=0;j<n;j++){const u=((v*1.2+j/n+k*.13)%1);const lat=-Math.PI/2+Math.PI*u;const r=L*Math.cos(lat)*Math.cos(lat);if(r<R*1.02)continue;for(const side of [1,-1]){const x=cx+side*r*Math.cos(lat),y=cy-r*Math.sin(lat);ctx.fillStyle='rgba(200,245,255,'+(.7*frac).toFixed(2)+')';ctx.beginPath();ctx.arc(x,y,1.6,0,7);ctx.fill();}}}}
  /* scan sweep */
  const sweep=ctx.createLinearGradient(0,0,w,0);sweep.addColorStop(clamp(v-.1,0,1),'rgba(0,0,0,0)');sweep.addColorStop(clamp(v,0,1),'rgba(49,215,230,.10)');sweep.addColorStop(clamp(v+.1,0,1),'rgba(0,0,0,0)');ctx.fillStyle=sweep;ctx.fillRect(0,0,w,h);};}

/* Skyline: a field sun setting behind wireframe transmission masts on a perspective ground
   grid while the PAGE 3 mark composes above them. Drawn as line work, not silhouettes. */
/* A purpose-built E/B scroll scene: orthogonal vectors and flux loops meet as a travelling wavefront. */
function emVectorPainter(c){
 return function(v,p){const {w,h,ratio}=scrubSize(c),ctx=c.getContext('2d');if(!(w>0&&h>0))return;
  ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,w,h);const ease=x=>x<=0?0:x>=1?1:x*x*(3-2*x);
  const reveal=ease(v),cx=w*.5,cy=h*.54,span=Math.min(w*.72,h*.78),phase=(p||0)*.85;
  const wash=ctx.createRadialGradient(cx,cy,0,cx,cy,span*.72);wash.addColorStop(0,'rgba(24,92,196,.18)');wash.addColorStop(1,'rgba(2,8,24,0)');ctx.fillStyle=wash;ctx.fillRect(0,0,w,h);
  ctx.save();ctx.translate(cx,cy);ctx.rotate(-.12);ctx.lineCap='round';
  for(let i=-6;i<=6;i++){const x=i*span/14,local=ease((reveal-(i+6)*.025)/.46);if(local<=0)continue;const height=span*(.22+.22*Math.cos(i*.42+phase));ctx.strokeStyle='rgba(57,220,244,'+(.18+.62*local)+')';ctx.lineWidth=1.2;ctx.beginPath();ctx.moveTo(x,-height);ctx.lineTo(x,height);ctx.stroke();for(const y of [-height*.45,height*.45]){const dir=y<0?-1:1;ctx.fillStyle='rgba(136,245,255,'+(.45*local)+')';ctx.beginPath();ctx.moveTo(x,y+dir*7);ctx.lineTo(x-4,y-dir);ctx.lineTo(x+4,y-dir);ctx.closePath();ctx.fill();}}
  for(let i=0;i<7;i++){const local=ease((reveal-.22-i*.045)/.42);if(local<=0)continue;const rx=span*(.12+i*.047),ry=rx*.35;ctx.strokeStyle='rgba(74,126,255,'+(.16+.58*local)+')';ctx.lineWidth=1+i*.08;ctx.beginPath();ctx.ellipse(0,0,rx,ry,0,Math.PI*(1-local),Math.PI*(1+local));ctx.stroke();}
  const front=-span*.48+span*.96*ease((reveal-.45)/.5);ctx.strokeStyle='rgba(224,247,255,'+ease((reveal-.42)/.3)+')';ctx.lineWidth=2;ctx.shadowColor='rgba(74,210,255,.8)';ctx.shadowBlur=18;ctx.beginPath();for(let i=0;i<=70;i++){const x=-span*.48+i/70*span*.96,y=Math.sin(i*.42-phase*2)*span*.04*Math.exp(-Math.abs(x-front)/span*.22);i?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.stroke();ctx.restore();
  ctx.fillStyle='rgba(196,230,248,'+ease((v-.72)/.22)+')';ctx.font='600 '+Math.max(9,Math.min(12,w/90))+'px DM Mono,monospace';ctx.textAlign='center';ctx.fillText('TEXT  ·  TEXT',cx,h*.87);
 };}
function skylinePainter(c){const rnd=seeded(23);const far=[],near=[];let x=-.05;while(x<1.08){far.push({x,h:.10+rnd()*.16,w:.012+rnd()*.012,kind:rnd()});x+=.05+rnd()*.05;}x=-.02;while(x<1.05){near.push({x,h:.22+rnd()*.34,w:.018+rnd()*.02,kind:rnd(),arms:2+Math.floor(rnd()*3)});x+=.10+rnd()*.14;}
 function mast(ctx,mx,base,mh,mw,m,alpha,lit,p){
  const legL=mx-mw,legR=mx+mw,topL=mx-mw*.22,topR=mx+mw*.22,top=base-mh;
  ctx.strokeStyle='rgba(150,215,240,'+alpha+')';ctx.lineWidth=1;
  ctx.beginPath();ctx.moveTo(legL,base);ctx.lineTo(topL,top);ctx.moveTo(legR,base);ctx.lineTo(topR,top);ctx.stroke();
  /* lattice braces */
  const rows=Math.max(4,Math.round(mh/ (mw*1.6)));ctx.beginPath();for(let i=0;i<rows;i++){const t0=i/rows,t1=(i+1)/rows;const l0=legL+(topL-legL)*t0,r0=legR+(topR-legR)*t0,l1=legL+(topL-legL)*t1,r1=legR+(topR-legR)*t1;const y0=base-mh*t0,y1=base-mh*t1;ctx.moveTo(l0,y0);ctx.lineTo(r1,y1);ctx.moveTo(r0,y0);ctx.lineTo(l1,y1);ctx.moveTo(l1,y1);ctx.lineTo(r1,y1);}ctx.stroke();
  if(m.kind<.55){/* pylon: crossarms with insulators */
   for(let a=0;a<m.arms;a++){const t=.62+a*.13;const y=base-mh*t;const half=mw*(2.4-a*.4);ctx.beginPath();ctx.moveTo(mx-half,y);ctx.lineTo(mx+half,y);ctx.stroke();ctx.fillStyle='rgba(150,215,240,'+alpha+')';for(const sx of [-1,1]){ctx.beginPath();ctx.arc(mx+sx*half*.85,y+3,1.4,0,7);ctx.fill();}}
  }else{/* mast: antenna tip and panel antennas */
   ctx.beginPath();ctx.moveTo(mx,top);ctx.lineTo(mx,top-mh*.14);ctx.stroke();for(let a=0;a<3;a++){const y=top+mh*(.06+a*.1);const sx=a%2?1:-1;ctx.fillStyle='rgba(150,215,240,'+(alpha*.8)+')';ctx.fillRect(mx+sx*mw*.35-(sx<0?mw*.5:0),y,mw*.5,mh*.045);}}
  if(lit>0){const on=.55+.45*Math.sin(p*38+mx*.05);ctx.fillStyle='rgba(255,90,90,'+(lit*on).toFixed(2)+')';ctx.beginPath();ctx.arc(mx,(m.kind<.55?top:top-mh*.14)-2,2,0,7);ctx.fill();ctx.fillStyle='rgba(255,90,90,'+(lit*on*.25).toFixed(2)+')';ctx.beginPath();ctx.arc(mx,(m.kind<.55?top:top-mh*.14)-2,6,0,7);ctx.fill();}}
 return function(v,p){const {w,h,ratio}=scrubSize(c);const ctx=c.getContext('2d');ctx.setTransform(ratio,0,0,ratio,0,0);
  const dusk=clamp(v/.78,0,1);ctx.clearRect(0,0,w,h);const base=h*.84;
  /* sky */
  const sky=ctx.createLinearGradient(0,0,0,base);sky.addColorStop(0,'rgba(4,10,20,0)');sky.addColorStop(1,'rgba(12,77,119,'+(.30*(1-dusk)).toFixed(2)+')');ctx.fillStyle=sky;ctx.fillRect(0,0,w,base);
  /* Sparse antenna propagation schematic, explicitly decorative. */
  const sx=w*.5,sy=base-h*.26;
  ctx.save();ctx.beginPath();ctx.rect(0,0,w,base);ctx.clip();
  ctx.lineWidth=1;ctx.strokeStyle='rgba(49,215,230,.18)';
  for(let ring=1;ring<=4;ring++){ctx.beginPath();ctx.arc(sx,sy,Math.min(w,h)*(.10+ring*.075),Math.PI*1.08,Math.PI*1.92);ctx.stroke();}
  ctx.restore();
  /* ground: perspective grid receding to the horizon */
  ctx.fillStyle='#040a14';ctx.fillRect(0,base,w,h-base);
  ctx.strokeStyle='rgba(49,215,230,'+(.10+dusk*.18).toFixed(2)+')';ctx.lineWidth=1;ctx.beginPath();for(let i=0;i<9;i++){const yy=base+Math.pow(i/8,1.8)*(h-base);ctx.moveTo(0,yy);ctx.lineTo(w,yy);}for(let i=-8;i<=8;i++){ctx.moveTo(sx+i*w*.07,base);ctx.lineTo(sx+i*w*.24,h);}ctx.stroke();
  ctx.strokeStyle='rgba(120,225,245,'+(.35+dusk*.3).toFixed(2)+')';ctx.beginPath();ctx.moveTo(0,base+.5);ctx.lineTo(w,base+.5);ctx.stroke();
  /* brand mark composes above the masts */
  const t=clamp((p-.80)/.13,0,1);if(t>0){ctx.save();ctx.globalAlpha=t;ctx.font='700 '+Math.min(w*.062,h*.13)+'px Inter,-apple-system,Segoe UI,Roboto,sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillStyle='#eaf6ff';ctx.shadowColor='rgba(49,215,230,.6)';ctx.shadowBlur=36*t;ctx.letterSpacing=((1-t)*.25*40+6)+'px';ctx.fillText(String((scrub.hero&&scrub.hero.dataset.i3Title)||'Title').toUpperCase(),w/2,h*.40-(1-t)*16);ctx.restore();}
  const lit=clamp((dusk-.3)/.5,0,1);
  for(const m of far)mast(ctx,m.x*w,base,m.h*h,m.w*w,m,.22,lit*.5,p);
  for(const m of near)mast(ctx,m.x*w,base,m.h*h,m.w*w,m,.55,lit,p);};}
function pageBg(){const v=getComputedStyle(document.documentElement).getPropertyValue('--i3-bg').trim();return v||'#05070d';}
function mix(a,b,t){const pa=parseInt(a.slice(1),16),pb=parseInt(b.slice(1),16);const ch=(s)=>Math.round(((pa>>s)&255)*(1-t)+((pb>>s)&255)*t);return 'rgb('+ch(16)+','+ch(8)+','+ch(0)+')';}

class OneEuro {
 constructor(minCutoff=1.2,beta=.12,dCutoff=1){this.min=minCutoff;this.beta=beta;this.dc=dCutoff;this.last=null;this.dx=0;this.t=null;}
 alpha(c,dt){const r=2*Math.PI*c*dt;return r/(r+1);}
 filter(value,t){if(this.t===null){this.last=value;this.t=t;return value;}const dt=clamp(t-this.t,.001,.5),d=(value-this.last)/dt;this.dx+=this.alpha(this.dc,dt)*(d-this.dx);this.last+=this.alpha(this.min+this.beta*Math.abs(this.dx),dt)*(value-this.last);this.t=t;return this.last;}
}
class GesturePhysics {
 /* Hand velocity sets the target angular velocity while a hand is tracked (a hard push
    means a high velocity). When tracking drops, whether the hand left the frame or
    the detector lost it in a corner, the last velocity persists and decays with light
    damping, so the object coasts instead of stopping. Fixed 120 Hz steps, semi implicit
    Euler, independent of the render rate. */
 constructor(){this.filters=[new OneEuro(.9,.12,1),new OneEuro(.9,.12,1),new OneEuro(.9,.12,1)];this.position=[0,0,0];this.velocity=[0,0,0];this.acceleration=[0,0,0];this.angular=[0,0,0];this.angularVelocity=[0,0,0];this.input=null;this.lastT=null;this.lastPacket=null;this.lastWall=0;this.confidence=0;this.tracking=false;this.accumulator=0;this.stepSize=1/120;this.dampingFree=.45;this.dampingTracking=.5;this.gain=[2.6,2.6,0];this.maxVelocity=14;}
 sample(tracking){
  const p=tracking.position||[tracking.x,tracking.y,tracking.z||0],t=Number(tracking.monotonic??tracking.timestamp);if(!finite(t)||t===this.lastPacket||!p.every(finite))return;this.lastPacket=t;this.lastWall=performance.now();
  const c=clamp(Number(tracking.confidence)||0,0,1);this.confidence=c;
  if(c===0){this.tracking=false;this.lastT=null;return;}
  const f=tracking.filtered?p.slice():p.map((v,i)=>this.filters[i].filter(v,t));
  if(this.lastT!==null){const dt=t-this.lastT;if(dt>0&&dt<.5){for(let i=0;i<3;i++){const vel=(f[i]-this.input[i])/dt;this.acceleration[i]=(vel-this.velocity[i])/dt;this.velocity[i]=vel;this.position[i]=f[i];}
   /* Screen x drives yaw (mirrored, as in the original), screen y drives pitch. */
   /* Slap model: only fast motion adds momentum; a slow retraction of the hand is
      ignored, so slap, pull back, slap again keeps building speed in one direction. */
   const slap=v=>Math.abs(v)<.22?0:(Math.abs(v)-.22)*Math.sign(v);
   const push=[slap(this.velocity[1])*this.gain[0],-slap(this.velocity[0])*this.gain[1],0];
   for(let i=0;i<3;i++){this.angularVelocity[i]=clamp(this.angularVelocity[i]+push[i]*dt*4.5,-this.maxVelocity,this.maxVelocity);}}}
  this.tracking=true;this.input=f;this.lastT=t;
 }
 impulse(dx,dy){this.angularVelocity[0]+=dy;this.angularVelocity[1]+=dx;}
 advance(delta){
  if(this.tracking&&performance.now()-this.lastWall>350){this.tracking=false;this.lastT=null;}
  this.accumulator+=Math.min(delta,.1);
  while(this.accumulator>=this.stepSize){const damping=this.tracking?this.dampingTracking:this.dampingFree;const decay=Math.exp(-damping*this.stepSize);for(let i=0;i<3;i++){this.angularVelocity[i]*=decay;if(Math.abs(this.angularVelocity[i])<1e-4)this.angularVelocity[i]=0;this.angular[i]+=this.angularVelocity[i]*this.stepSize;}this.accumulator-=this.stepSize;}
 }
}
const physics=new GesturePhysics();window.__i3Physics=physics;window.__i3PhysicsClasses={GesturePhysics,OneEuro};
const vectorViews=new Map(),traceViews=new Map();
function palette(){const s=getComputedStyle(root);return{ink:s.getPropertyValue('--i3-ink').trim(),muted:s.getPropertyValue('--i3-muted').trim(),grid:s.getPropertyValue('--i3-grid').trim(),accent:s.getPropertyValue('--i3-accent').trim(),x:s.getPropertyValue('--i3-chart-1').trim(),y:s.getPropertyValue('--i3-chart-2').trim(),z:s.getPropertyValue('--i3-chart-3').trim()};}
let colors=palette();
function sizeCanvas(canvas){const rect=canvas.getBoundingClientRect(),ratio=Math.min(devicePixelRatio||1,1.25);const w=Math.max(1,Math.round(rect.width*ratio)),h=Math.max(1,Math.round(rect.height*ratio));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}return {w:rect.width,h:rect.height,ratio};}
function drawMeter(canvas,level,clipped){const {w,h,ratio}=sizeCanvas(canvas);const ctx=canvas.getContext('2d');if(!ctx)return;ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,w,h);ctx.fillStyle=colors.grid;ctx.fillRect(0,0,w,h);if(level===null)return;const frac=clamp((level+60)/60,0,1);ctx.fillStyle=clipped?getComputedStyle(root).getPropertyValue('--i3-error').trim():colors.accent;ctx.fillRect(0,0,w*frac,h);for(const mark of [-40,-20,-6]){const x=w*(mark+60)/60;ctx.fillStyle=colors.ink;ctx.fillRect(x,0,1,h);}}
function drawTrace(canvas,values,dimensions){const ctx=canvas.getContext('2d');if(!ctx)return;const {w,h,ratio}=dimensions;ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,w,h);ctx.strokeStyle=colors.grid;ctx.beginPath();ctx.moveTo(0,h/2);ctx.lineTo(w,h/2);ctx.stroke();if(values.length<2)return;const max=Math.max(1e-9,...values.map(x=>Math.abs(x.v)));ctx.strokeStyle=colors.accent;ctx.lineWidth=1.5;ctx.beginPath();values.forEach((item,i)=>{const x=i/(values.length-1)*w,y=h/2-item.v/max*h*.42;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();}
function mountCanvases(){
 for(const [canvas,view] of traceViews){if(!canvas.isConnected){view.observer.disconnect();view.visibility.disconnect();traceViews.delete(canvas);}}
 for(const canvas of document.querySelectorAll('[data-i3-trace]')){if(traceViews.has(canvas))continue;const view={dim:sizeCanvas(canvas),visible:true};
  const redraw=()=>{if(!view.visible)return;const list=state.traces.get(canvas.dataset.i3Trace)||[];drawTrace(canvas,list,view.dim);canvas.__i3TraceTime=list.at(-1)?.t;};
  view.observer=new ResizeObserver(()=>{view.dim=sizeCanvas(canvas);redraw();});view.observer.observe(canvas);
  view.visibility=new IntersectionObserver(entries=>{view.visible=entries[0].isIntersecting;if(view.visible)redraw();});view.visibility.observe(canvas);traceViews.set(canvas,view);
 }
 for(const [canvas,view] of vectorViews){if(!canvas.isConnected){view.observer.disconnect();view.visibility.disconnect();vectorViews.delete(canvas);}}
 for(const canvas of document.querySelectorAll('[data-i3-vector]')){if(vectorViews.has(canvas))continue;const ctx=canvas.getContext('2d');if(!ctx)continue;const view={ctx,dim:sizeCanvas(canvas),visible:true};view.observer=new ResizeObserver(()=>{view.dim=sizeCanvas(canvas);});view.observer.observe(canvas);view.visibility=new IntersectionObserver(entries=>{view.visible=entries[0].isIntersecting;});view.visibility.observe(canvas);vectorViews.set(canvas,view);let point=null;
  canvas.addEventListener('pointerdown',e=>{point={x:e.clientX,y:e.clientY,t:e.timeStamp};canvas.setPointerCapture(e.pointerId);});
  canvas.addEventListener('pointermove',e=>{if(!point)return;const dt=Math.max(.001,(e.timeStamp-point.t)/1000);physics.impulse((e.clientX-point.x)/Math.max(100,canvas.clientWidth)*4,(e.clientY-point.y)/Math.max(100,canvas.clientHeight)*4);point={x:e.clientX,y:e.clientY,t:e.timeStamp};});
  canvas.addEventListener('pointerup',()=>{point=null;});canvas.addEventListener('pointercancel',()=>{point=null;});
 }
}
let smoothVector=[0,0,0];
function drawVector(canvas,view,dt){
 const signature=smoothVector.concat(physics.angular).map(v=>v.toFixed(4)).join(',')+colors.accent+view.dim.w+view.dim.h;if(view.lastSignature===signature)return;view.lastSignature=signature;
 const ctx=view.ctx,{w,h,ratio}=view.dim;ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,w,h);
 const angle=physics.angular,yaw=.55+angle[1],pitch=-.45+angle[0];
 const project=p=>{const x=p[0]*Math.cos(yaw)+p[2]*Math.sin(yaw),z=-p[0]*Math.sin(yaw)+p[2]*Math.cos(yaw),y=p[1]*Math.cos(pitch)-z*Math.sin(pitch),zz=p[1]*Math.sin(pitch)+z*Math.cos(pitch),scale=3.5/(3.5-zz);return [w/2+x*h*.31*scale,h/2-y*h*.31*scale];};
 function line(a,b,color,width){const p=project(a),q=project(b);ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...q);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke();return q;}
 for(let i=-4;i<=4;i++){line([i/4,0,-1],[i/4,0,1],colors.grid,.65);line([-1,0,i/4],[1,0,i/4],colors.grid,.65);}
 [[1,0,0],[0,1,0],[0,0,1]].forEach((axis,i)=>{const end=line([0,0,0],axis,[colors.x,colors.y,colors.z][i],1.1);ctx.fillStyle=colors.muted;ctx.font='12px monospace';ctx.fillText(['X','Y','Z'][i],end[0]+4,end[1]-5);});
 const magnitude=Math.hypot(...smoothVector);const confidence=Number(state.packet?.fusion?.vector?.confidence)||0;
 if(magnitude>1e-9&&confidence>0){const unit=smoothVector.map(v=>v/magnitude*.88);const q=line([0,0,0],unit,colors.accent,3);const origin=project([0,0,0]),theta=Math.atan2(q[1]-origin[1],q[0]-origin[0]);ctx.fillStyle=colors.accent;ctx.beginPath();ctx.moveTo(...q);ctx.lineTo(q[0]-12*Math.cos(theta-.4),q[1]-12*Math.sin(theta-.4));ctx.lineTo(q[0]-12*Math.cos(theta+.4),q[1]-12*Math.sin(theta+.4));ctx.closePath();ctx.fill();}else{ctx.fillStyle=colors.muted;ctx.font='12px sans-serif';ctx.textAlign='center';ctx.fillText('Direction unavailable at this confidence',w/2,h-13);ctx.textAlign='left';}
}
/* Quantum nebula: 24k additive points on this host (48k on desktop class GPUs). Motion is
   a divergence free swirl evaluated per vertex from three phase shifted sines plus a
   mouse repulsion term, so the CPU never touches the particle buffer. Soft sprites with
   additive blending stand in for the bloom pass. */
let nebula=null;
function nebulaSync(){/* particle field retired at the operator's request; the code stays for the pillar cards' backdrop only if re enabled */const el=document.getElementById('i3-nebula');if(el)el.classList.remove('on');if(nebula)nebula.active=false;}
function createNebula(){
 let canvas=document.getElementById('i3-nebula');if(!canvas){canvas=document.createElement('canvas');canvas.id='i3-nebula';document.body.appendChild(canvas);}
 const gl=canvas.getContext('webgl',{alpha:true,antialias:false,depth:false,premultipliedAlpha:false,powerPreference:'low-power'});if(!gl){nebula={active:false};return;}
 const count=(navigator.hardwareConcurrency||4)>=8?48000:24000;const data=new Float32Array(count*4);
 for(let i=0;i<count;i++){data[i*4]=(Math.random()-.5)*5;data[i*4+1]=(Math.random()-.5)*5;data[i*4+2]=(Math.random()-.5)*5;data[i*4+3]=Math.random();}
 const vs='attribute vec4 seed;uniform float time;uniform vec2 mouse;uniform float aspect;uniform float ratio;varying float vHue;varying float vGlow;'
 +'vec3 swirl(vec3 p,float t){return normalize(vec3(sin(p.y*1.2+t),cos(p.z*1.2+t*1.1),sin(p.x*1.2+t*.9)));}'
 +'void main(){vec3 p=seed.xyz;float t=time*.1;vec3 v=swirl(p,t);p+=v*sin(t*2.0+seed.w*6.283)*.35+swirl(p*.5,t*.7)*.25;'
 +'vec3 m=vec3(mouse*2.5,0.0);vec3 d=p-m;float dist=length(d);if(dist<2.0){p+=normalize(d)*(2.0-dist)*.35;}'
 +'p.x=mod(p.x+2.5,5.0)-2.5;p.y=mod(p.y+2.5,5.0)-2.5;p.z=mod(p.z+2.5,5.0)-2.5;'
 +'float depth=5.0-(p.z+2.5);vec2 screen=vec2(p.x/aspect,p.y)/(depth*.55);gl_Position=vec4(screen,0.0,1.0);'
 +'gl_PointSize=max(1.0,(6.0/depth)*ratio*(0.5+seed.w*.9));vHue=seed.w;vGlow=1.0/depth;}';
 const fs='precision mediump float;varying float vHue;varying float vGlow;'
 +'void main(){float r=length(gl_PointCoord-vec2(.5));if(r>.5)discard;float a=smoothstep(.5,.0,r);vec3 c=mix(vec3(.13,.55,1.0),vec3(.4,.95,1.0),vHue);gl_FragColor=vec4(c*a*(0.45+vGlow),a*.55);}';
 const prog=gl.createProgram();for(const [type,src] of [[gl.VERTEX_SHADER,vs],[gl.FRAGMENT_SHADER,fs]]){const sh=gl.createShader(type);gl.shaderSource(sh,src);gl.compileShader(sh);if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS)){window.__i3Errors.push('nebula: '+gl.getShaderInfoLog(sh));nebula={active:false};return;}gl.attachShader(prog,sh);}
 gl.linkProgram(prog);gl.useProgram(prog);const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW);const loc=gl.getAttribLocation(prog,'seed');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,4,gl.FLOAT,false,0,0);
 gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE);
 nebula={gl,canvas,prog,count,active:true,mouse:[0,0],target:[0,0],u:{time:gl.getUniformLocation(prog,'time'),mouse:gl.getUniformLocation(prog,'mouse'),aspect:gl.getUniformLocation(prog,'aspect'),ratio:gl.getUniformLocation(prog,'ratio')}};
 addEventListener('mousemove',e=>{nebula.target=[(e.clientX/innerWidth)*2-1,-(e.clientY/innerHeight)*2+1];},{passive:true});
 addEventListener('touchmove',e=>{const t=e.touches[0];if(t)nebula.target=[(t.clientX/innerWidth)*2-1,-(t.clientY/innerHeight)*2+1];},{passive:true});
}
function drawNebula(now){if(!nebula||!nebula.active||!nebula.gl)return;const {gl,canvas,u}=nebula;const ratio=Math.min(devicePixelRatio||1,1.25);const w=Math.round(innerWidth*Math.min(1,Math.sqrt(1100000/Math.max(1,innerWidth*innerHeight)))),h=Math.round(w*innerHeight/innerWidth);if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);}
 nebula.mouse[0]+=(nebula.target[0]-nebula.mouse[0])*.05;nebula.mouse[1]+=(nebula.target[1]-nebula.mouse[1])*.05;
 gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.uniform1f(u.time,now/1000);gl.uniform2f(u.mouse,nebula.mouse[0],nebula.mouse[1]);gl.uniform1f(u.aspect,innerWidth/innerHeight);gl.uniform1f(u.ratio,ratio);gl.drawArrays(gl.POINTS,0,nebula.count);}
let glState=null;
function createGL(){const canvas=document.getElementById('i3-field-background');try{const gl=canvas.getContext('webgl',{antialias:false,alpha:false,powerPreference:'low-power',depth:false,stencil:false});if(!gl)throw Error('WebGL unavailable');glState={gl,canvas,program:null};canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();glState.program=null;root.dataset.i3Webgl='context lost';});canvas.addEventListener('webglcontextrestored',()=>{compileGL();});root.dataset.i3Webgl='created';return true;}catch(error){root.dataset.i3Webgl='unavailable';return false;}}
function compileGL(){
 if(!glState)return;const {gl,canvas}=glState;
 try{const program=gl.createProgram();const source=[['VERTEX_SHADER','attribute vec2 position;void main(){gl_Position=vec4(position,0.,1.);}'],['FRAGMENT_SHADER','precision mediump float;uniform vec2 resolution;uniform float time;uniform vec3 ink;uniform vec3 paper;void main(){vec2 uv=gl_FragCoord.xy/resolution;float wave=sin(uv.x*17.+uv.y*6.+time*.2)*.5+.5;float field=exp(-abs(uv.y-.45-sin(uv.x*4.+time*.05)*.13)*27.);float grid=step(.985,fract(uv.x*28.))*step(.985,fract(uv.y*18.));gl_FragColor=vec4(mix(paper,ink,field*.065*wave+grid*.12),1.);}']];
 for(const [type,text] of source){const shader=gl.createShader(gl[type]);gl.shaderSource(shader,text);gl.compileShader(shader);if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(shader));gl.attachShader(program,shader);gl.deleteShader(shader);}gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);const position=gl.getAttribLocation(program,'position');gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);glState.program=program;glState.uniforms={resolution:gl.getUniformLocation(program,'resolution'),time:gl.getUniformLocation(program,'time'),ink:gl.getUniformLocation(program,'ink'),paper:gl.getUniformLocation(program,'paper')};resizeGL();themeGL();root.dataset.i3Webgl='active';}catch(error){root.dataset.i3Webgl='shader unavailable';glState.program=null;}
}
function resizeGL(){if(!glState?.program)return;glState.dirty=true;const {gl,canvas,uniforms}=glState;/* full device resolution on a capable machine; a pixel budget on small hosts (this host's own screen) */const budget=(navigator.hardwareConcurrency||4)>=8?4800000:1200000;const ratio=Math.min(devicePixelRatio||1,2,Math.sqrt(budget/Math.max(1,innerWidth*innerHeight)));canvas.width=Math.max(1,Math.round(innerWidth*ratio));canvas.height=Math.max(1,Math.round(innerHeight*ratio));gl.viewport(0,0,canvas.width,canvas.height);gl.uniform2f(uniforms.resolution,canvas.width,canvas.height);}
function themeGL(){if(!glState?.program)return;glState.dirty=true;const s=getComputedStyle(root),{gl,uniforms}=glState;gl.uniform3fv(uniforms.ink,s.getPropertyValue('--i3-shader-ink').split(',').map(Number));gl.uniform3fv(uniforms.paper,s.getPropertyValue('--i3-shader-bg').split(',').map(Number));}
let lastFrame=0;
/* Delivered frame cadence of THIS browser: the median gap between consecutive animation
   frames, snapped to the nearest common panel rate. Reported to /api/performance so a
   60 Hz-capped browser can be told apart from the site (which never limits below 144). */
function refreshEstimate(){const gaps=metrics.frames.slice(-240).filter(g=>g>2&&g<100).sort((a,b)=>a-b);if(gaps.length<30)return 0;const med=gaps[gaps.length>>1];const hz=1000/med;const rates=[30,48,50,60,72,75,90,100,120,144,165,240];return rates.reduce((a,b)=>Math.abs(b-hz)<Math.abs(a-hz)?b:a,rates[0]);}
window.__i3RefreshEstimate=refreshEstimate;
function frame(now){requestAnimationFrame(frame);if(document.hidden){lastFrame=now;return;}const begin=performance.now(),dt=Math.max(0,Math.min(.1,(now-(lastFrame||now))/1000));if(lastFrame){metrics.frames.push(now-lastFrame);if(metrics.frames.length>600)metrics.frames.shift();}lastFrame=now;const prior=physics.angular.slice();physics.advance(dt);const delta=physics.angular.map((v,i)=>v-prior[i]);if(!reduced()&&delta.some(v=>Math.abs(v)>1e-8)){const target=fingerMouse.holdCanvas?.__i3LegacyHandControls||window.__i3HandControls;if(target?.physics)target.physics(delta);}
 for(let i=0;i<3;i++)smoothVector[i]+=(state.vector[i]-smoothVector[i])*(1-Math.exp(-dt*10));
 /* The secondary field grid is a static underlay. The existing page shader owns motion;
    drawing both full-screen WebGL layers every frame doubled the background work. */
 if(glState?.program&&glState.dirty){const {gl,uniforms}=glState;gl.uniform1f(uniforms.time,0);gl.drawArrays(gl.TRIANGLES,0,6);glState.dirty=false;}
 drawNebula(now);
 for(const [canvas,view] of vectorViews)if(view.visible)drawVector(canvas,view,dt);
 metrics.work.push(performance.now()-begin);if(metrics.work.length>600)metrics.work.shift();
}
/* ── Plotly redraw gate ────────────────────────────────────────────────────────
   Every dcc.Interval below re-renders a set of Plotly graphs (the EM page alone replots
   eleven figures every 2–3 s, ~50 ms of main-thread work each burst, enough to drop
   frames of any animation running at the time). An interval is switched off while none of
   its graphs is near the viewport (hidden tab, scrolled away) and back on as soon as one
   returns. Server sampling is untouched: this only stops the browser asking for figures it
   cannot show. Number cards keep their own intervals and are never gated. */
const INTERVAL_GRAPHS={'c1-chart-int':['g-line','g-axis','g-pie','g-gauge','g-bar','g-scatter','g-delta'],'c1-3d-int':['g3d-surface','g3d-terrain'],'c1-dir-int':['g3d-plane','g3d-twopole'],'c1-arch-int':['g-archive'],'c2-chart-int':['c2-line','c2-index-line','c2-gauge','c2-basebar','c2-bullet','c2-b-correlation','c2-induction-proxy'],'p1-overlay-int':['p1-overlay','p1-normalized-overlay','p1-coupling','p1-correlation'],'ch3-chart-int':['ch3-sweep-graph','ch3-bands-graph','ch3-trend-graph'],'ch3-wf-int':['ch3-waterfall-graph'],'ch3-focus-int':['ch3-focus-graph']};
const gateState={observer:null,visible:new Map(),applied:new Map(),timer:0};
function gateApply(){gateState.timer=0;const setProps=window.dash_clientside?.set_props;if(typeof setProps!=='function')return;
 for(const [intervalId,graphIds] of Object.entries(INTERVAL_GRAPHS)){/* dcc.Interval renders no DOM node: its page is present when its graphs are */
  const anyMounted=graphIds.some(id=>document.getElementById(id));if(!anyMounted){gateState.applied.delete(intervalId);continue;}
  const shown=graphIds.some(id=>gateState.visible.get(id));const disabled=!shown;
  gateState.applied.set(intervalId,disabled);
  try{setProps(intervalId,{disabled});}catch(e){}}}
/* set_props is a no-op while Dash is still mounting a fresh layout, so the wanted state is asserted again on a slow timer. */
setInterval(()=>{if(gateState.visible.size)gateApply();},2500);
function gateSchedule(){if(gateState.timer)return;gateState.timer=setTimeout(gateApply,120);}
function mountGate(){if(!('IntersectionObserver' in window))return;
 if(!gateState.observer)gateState.observer=new IntersectionObserver(entries=>{for(const e of entries)gateState.visible.set(e.target.id,e.isIntersecting&&e.target.getClientRects().length>0);gateSchedule();},{rootMargin:'160px 0px'});
 let fresh=false;for(const ids of Object.values(INTERVAL_GRAPHS))for(const id of ids){const el=document.getElementById(id);if(el&&!el.dataset.i3Gated){el.dataset.i3Gated='1';fresh=true;gateState.visible.set(id,false);gateState.observer.observe(el);}}
 /* a re-rendered tab remounts its dcc.Interval with the layout default (enabled): forget what was applied and assert again */
 if(fresh)gateState.applied.clear();
 gateSchedule();}
/* display:none (an inactive tab) does not fire IntersectionObserver reliably in every engine; re-check on tab clicks and resizes. */
document.addEventListener('click',e=>{if(e.target.closest('[id^="p1-tab-"],[id^="sp-tab-"],.i3-tab,[role="tab"]'))setTimeout(()=>{for(const [id] of gateState.visible){const el=document.getElementById(id);if(el)gateState.visible.set(id,el.getClientRects().length>0&&el.getBoundingClientRect().bottom>-160&&el.getBoundingClientRect().top<innerHeight+160);}gateSchedule();},80);},true);
addEventListener('resize',gateSchedule,{passive:true});
window.__i3Gate=gateState;
function mountMotion(){mountGate();hpStoreRender();mountShowcase();applyCursorMode();syncLeftHanded();syncBuddyButton();if(embeddedNvtraVisible())buddyUnmount();else if(buddyOn())setTimeout(buddyMount,250);if(document.querySelector('[data-i3-action="hand_calibrate"]'))h3Load();
 if(!window.gsap||reduced())return;
 const nodes=document.querySelectorAll('.i3-card:not([data-i3-revealed]),.i3-summary:not([data-i3-revealed])');
 const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(!entry.isIntersecting)return;entry.target.dataset.i3Revealed='true';window.gsap.fromTo(entry.target,{y:10,opacity:.9},{y:0,opacity:1,duration:.45,ease:'power2.out',clearProps:'transform,opacity'});observer.unobserve(entry.target);}),{threshold:.08});nodes.forEach(el=>observer.observe(el));
}
let scrollQueued=false;
const parallaxRates={'1':70,'2':55,'3':40,'4':10};
/* Cards rotate slider. The outer section is as tall as the horizontal travel plus one
   viewport; the sticky inner pans the track while each card runs its own in/settle/out
   timeline from its position across the viewport. Values follow the reference
   component per breakpoint; reduced motion flattens rotation to 15 percent. */
function rotateConfig(){const w=innerWidth;const mobile=w<640,tablet=!mobile&&w<1025;return{step:mobile?2:tablet?6:10,rotIn:mobile?-60:tablet?-80:-100,rotOut:mobile?50:tablet?65:80,scale:reduced()?.15:1};}
function layoutRotate(){const outer=document.querySelector('[data-i3-rotate]');const track=outer?.querySelector('[data-i3-track]');if(!outer||!track)return;const travel=Math.max(0,track.scrollWidth-innerWidth);outer.style.height=(travel+innerHeight)+'px';outer.__i3Travel=travel;rotateScroll();}
function rotateScroll(){const outer=document.querySelector('[data-i3-rotate]');const track=outer?.querySelector('[data-i3-track]');if(!outer||!track)return;const travel=outer.__i3Travel||0;const rect=outer.getBoundingClientRect();const progress=clamp(-rect.top/Math.max(1,travel),0,1);const x=-progress*travel;track.style.transform='translate3d('+x.toFixed(1)+'px,0,0)';
 const cfg=rotateConfig(),cards=track.querySelectorAll('[data-i3-card]'),total=cards.length,mid=Math.floor(total/2),vw=innerWidth;
 cards.forEach((card,index)=>{const wrap=card.parentElement;const left=wrap.offsetLeft+x,right=left+wrap.offsetWidth;const t=clamp((vw-left)/(vw+wrap.offsetWidth),0,1);
  const offset=(index<mid?-((mid-index)*cfg.step):(index-mid+1)*cfg.step)*1.2;const rotX=(offset<0?5:-5)*cfg.scale;let ry,op,y;
  if(t<.5){const k=t/.5;ry=cfg.rotIn*cfg.scale*1.1*(1-k);op=.8+.2*k;y=offset*(1-k);}else{const k=(t-.5)/.5;ry=cfg.rotOut*cfg.scale*1.1*k;op=1-.1*k;y=-offset*k;}
  card.style.transform='translateY('+y.toFixed(2)+'vh) rotateX('+(rotX*(1-Math.min(1,Math.abs(t-.5)*2))).toFixed(2)+'deg) rotateY('+ry.toFixed(2)+'deg)';card.style.opacity=op.toFixed(3);});}
function parallaxScroll(){const wrap=document.querySelector('[data-parallax-layers]');if(!wrap)return;const header=wrap.closest('.parallax__header');const pin=header.closest('.parallax__pin')||header;if(pin.classList.contains('i3-parallax-complete'))return;const rect=pin.getBoundingClientRect();if(rect.bottom<=72){const content=pin.nextElementSibling,before=content?.getBoundingClientRect().top;pin.classList.add('i3-parallax-complete');const after=content?.getBoundingClientRect().top;if(Number.isFinite(before)&&Number.isFinite(after))scrollBy({top:after-before,left:0,behavior:'auto'});return;}const progress=clamp((-rect.top)/Math.max(1,rect.height-innerHeight),0,1);
 for(const el of wrap.querySelectorAll('[data-parallax-layer]')){const y=progress*(parallaxRates[el.dataset.parallaxLayer]||0);const isTitle=el.dataset.parallaxLayer==='3';const scale=isTitle?1+progress*.35:1;const px=Math.round(y/100*el.offsetHeight);el.style.transform='translate3d(-50%,calc(-50% + '+px+'px),0) scale('+scale.toFixed(3)+')';if(isTitle)el.style.opacity=String(clamp(1-progress*1.6,0,1));}
 header.style.setProperty('--i3-scroll',progress.toFixed(3));wrap.style.transform='translate3d(0,'+(-progress*18).toFixed(2)+'vh,0) scale('+(1+progress*.18).toFixed(3)+')';wrap.style.opacity=String(clamp(1-progress*1.25,0,1));}
addEventListener('resize',()=>{layoutRotate();},{passive:true});
addEventListener('scroll',()=>{if(scrollQueued)return;scrollQueued=true;requestAnimationFrame(()=>{scrollQueued=false;parallaxScroll();rotateScroll();if(reduced())return;const el=document.querySelector('.i3-page>header');if(el){const y=clamp(scrollY*.025,0,12);if(window.gsap)window.gsap.set(el,{y});else el.style.transform='translateY('+y+'px)';}});},{passive:true});
new MutationObserver(()=>{colors=palette();themeGL();if(window.Plotly)document.querySelectorAll('.js-plotly-plot').forEach(plot=>{if(!plot._fullLayout)return;window.Plotly.relayout(plot,{'paper_bgcolor':'rgba(0,0,0,0)','plot_bgcolor':'rgba(0,0,0,0)','font.color':colors.ink,'xaxis.gridcolor':colors.grid,'yaxis.gridcolor':colors.grid}).catch(()=>{});});}).observe(root,{attributes:true,attributeFilter:['class']});
addEventListener('resize',resizeGL,{passive:true});
addEventListener('online',()=>{connect();snapshot().then(schedulePacket).catch(()=>{});});
/* Warm the browser cache with the hand model (~12 MB, served compressed and immutable)
   while the page is idle, so pressing the camera button later starts within a second. */
function prefetchHandModel(){if(prefetchHandModel.done)return;prefetchHandModel.done=true;const files=['hands.js','hands_solution_simd_wasm_bin.js','hands_solution_simd_wasm_bin.wasm','hands_solution_packed_assets_loader.js','hands_solution_packed_assets.data','hands.binarypb','hand_landmark_lite.tflite'];let i=0;const next=()=>{if(i>=files.length)return;fetch('/assets/mediapipe/'+files[i++]+'?v=__I3_VERSION__',{priority:'low',cache:'force-cache'}).catch(()=>{}).finally(next);};next();}
(window.requestIdleCallback||(f=>setTimeout(f,4000)))(()=>prefetchHandModel(),{timeout:8000});
document.addEventListener('visibilitychange',()=>{if(!document.hidden){fingerMouse.warmUntil=performance.now()+700;fingerMouse.fx=new OneEuro(1.6,.4,1);fingerMouse.fy=new OneEuro(1.6,.4,1);fingerMouse.contactAt=0;fingerMouse.pinchSince=0;fingerMouse.clicked=false;fingerMouse.tilt=null;fingerMouse.lastPalmT=0;SS.dir=0;SS.peak=0;SS.prevDir=0;SS.prevPeak=0;physics.sample({position:[0,0,0],timestamp:performance.now()/1000,confidence:0});connect();snapshot().then(schedulePacket).catch(()=>{});lastFrame=0;}});
addEventListener('pagehide',()=>{state.source?.close();state.trackingSource?.close();state.trackingSource=null;});
addEventListener('pageshow',e=>{if(e.persisted){connect();snapshot().then(schedulePacket).catch(()=>{});}});
function chooseMode(packet){
 return new Promise(resolve=>{
  const panel=document.getElementById('i3-mode');
  if(!panel){document.body.classList.remove('mode-gate-locked');resolve();return;}
  /* A mode is already part of the instrument packet and can be changed later
     from the visible toolbar control.  A first-load modal made the whole
     instrument appear broken -- it intercepted every tab until the operator
     made an unrelated cloud/privacy choice.  Reuse a deliberate local choice
     when there is one, otherwise retain the server mode and let the dashboard
     become interactive immediately. */
  let remembered=null;try{remembered=localStorage.getItem('i3-mode');}catch(e){}
  const active=remembered==='online'||remembered==='offline'?remembered:packet?.mode?.mode;
  if(active==='online'||active==='offline'){
   panel.hidden=true;document.body.classList.remove('mode-gate-locked');resolve(active);return;
  }
  /* The chooser is a fixed full-screen overlay, but the page behind it scrolls
     freely -- and this is the one screen where somebody lingers, reading two
     options. Scroll here and the instrument appears already scrolled down once
     the overlay clears, which reads as a gap above the content.

     Its own class rather than intro-active: that one is removed by whichever
     bootIntro() path runs, and when the intro is skipped or already consumed
     none of them do, which left the whole instrument unscrollable. This lock
     lives exactly as long as the chooser does, released in finish() below. */
  document.body.classList.add('mode-gate-locked');
  try{window.scrollTo(0,0);}catch(e){}
  const boot=document.getElementById('i3-boot');
  const loading=boot.querySelector('.i3-boot-panel');loading?.classList.add('leaving');panel.classList.add('entering');
  setTimeout(()=>{if(loading)loading.hidden=true;panel.hidden=false;requestAnimationFrame(()=>requestAnimationFrame(()=>panel.classList.remove('entering')));},620);cancelAnimationFrame(liquidRafGlobal);
  const cards=Array.from(panel.querySelectorAll('.i3-mode-card'));
  const internet=packet?.mode?.internet,local=packet?.mode?.local_ai||{};
  const sub=document.getElementById('i3-mode-sub');
  text(sub,internet===false?'No internet reaches this host right now. Offline is recommended.':internet===true?'Internet is reachable from this host.':'Internet status unknown.');
  text(document.getElementById('i3-mode-local'),local.available?'Local model ready · '+clean(local.model):'Local model not installed yet');
  let selected=null;const recommended=internet===false||(!internet&&local.available)?'offline':'online';
  cards.forEach(card=>card.classList.toggle('recommended',card.dataset.mode===recommended));
  const paint=()=>cards.forEach(card=>card.classList.toggle('selected',card.dataset.mode===selected));paint();
  const finish=async mode=>{cleanup();document.body.classList.remove('mode-gate-locked');selected=mode;paint();try{await control({action:'mode',mode});}catch(error){}try{localStorage.setItem('i3-mode',mode);}catch(error){}resolve(mode);};
  const onKey=event=>{const key=event.key.toLowerCase();if(key==='o'){event.preventDefault();finish('online');}else if(key==='f'){event.preventDefault();finish('offline');}else if(key==='enter'){event.preventDefault();if(selected)finish(selected);}else if(key==='arrowleft'||key==='arrowright'){selected=selected==='online'?'offline':'online';paint();}};
  const cleanup=()=>{document.removeEventListener('keydown',onKey,true);};
  document.addEventListener('keydown',onKey,true);
  cards.forEach(card=>card.addEventListener('click',()=>finish(card.dataset.mode),{once:true}));
  cards.forEach(card=>card.addEventListener('mouseenter',()=>{selected=card.dataset.mode;paint();}));
 });
}
/* Finger mouse. A pointing hand (index extended, other fingers curled) moves an on
   screen cursor; a pinch of index and thumb clicks; a finger snap (thumb and middle
   finger touch then fly apart) toggles the mode on and off. Distance is estimated from
   the knuckle width against a nominal 8 cm hand and a 62 degree webcam. */
/* ══════════════════════════════════════════════════════════
   HAND PROFILE. Every gesture threshold lives here instead of being a magic number in a
   detector. Defaults are the hand-tuned values; the calibration wizard in Settings
   measures the operator's own hand and overrides them (localStorage + /api/hand-profile).
   ══════════════════════════════════════════════════════════ */
const HP_DEFAULT={ext:1.25,curl:1.15,pinchOn:.24,pinchOff:.34,thumbDy:.6,straight:.7,spread:.16,thumbOut:.6,edge:.08,cursorMin:.7,cursorBeta:.5,swipeMin:.12,swipeGain:1,calibrated:false};
const HP=Object.assign({},HP_DEFAULT);
function hpApply(profile){if(!profile||typeof profile!=='object')return;for(const k of Object.keys(HP_DEFAULT))if(Number.isFinite(Number(profile[k]))||typeof profile[k]==='boolean')HP[k]=profile[k];
 if(window.__i3FM){const fm=window.__i3FM;fm.fx=new OneEuro(HP.cursorMin,HP.cursorBeta,1);fm.fy=new OneEuro(HP.cursorMin,HP.cursorBeta,1);}}
function hpLoad(){try{const local=JSON.parse(localStorage.getItem('i3-hand-profile')||'null');if(local)hpApply(local);}catch(e){}
 fetch('/api/hand-profile',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(p=>{if(p&&p.profile&&p.profile.calibrated&&!HP.calibrated)hpApply(p.profile);}).catch(()=>{});}
function hpSave(profile){hpApply(profile);try{localStorage.setItem('i3-hand-profile',JSON.stringify(HP));}catch(e){}
 fetch('/api/hand-profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile:HP})}).catch(()=>{});}
function hpReset(localOnly){for(const k of Object.keys(HP_DEFAULT))HP[k]=HP_DEFAULT[k];try{localStorage.removeItem('i3-hand-profile');}catch(e){}if(!localOnly)fetch('/api/hand-profile',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile:null})}).then(()=>hpStoreLoad()).catch(()=>{});hpApply(HP);}
window.__i3HandProfile={get:()=>Object.assign({},HP),save:hpSave,reset:hpReset};
/* ── Named calibrations: several people (or lighting setups) each keep their own thresholds ── */
const hpStore={profiles:{},active:null};
function hpStoreRender(){document.querySelectorAll('[data-i3-hand-profiles]').forEach(host=>{const names=Object.keys(hpStore.profiles);if(!names.length){if(host.textContent!=='No saved calibrations yet.')host.textContent='No saved calibrations yet.';return;}
 const html=names.map(n=>{const on=n===hpStore.active;const p=hpStore.profiles[n]||{};return '<div class="i3-hp-row'+(on?' on':'')+'" data-name="'+n.replace(/"/g,'&quot;')+'"><span class="i3-hp-name">'+n.replace(/</g,'&lt;')+(on?' <i>ACTIVE</i>':'')+'</span><span class="i3-hp-meta">pinch '+(p.pinchOn??0).toFixed(2)+' · swipe '+(p.swipeMin??0).toFixed(2)+'</span><span class="i3-hp-acts"><button type="button" data-hp="use">USE</button><button type="button" data-hp="rename">RENAME</button><button type="button" data-hp="delete">DELETE</button></span></div>';}).join('');
 if(host.dataset.i3Rendered!==html){host.dataset.i3Rendered=html;host.innerHTML=html;}});}
async function hpStoreOp(body){try{const r=await fetch('/api/hand-profiles',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const d=await r.json();if(!r.ok)throw Error(d.error||'failed');hpStore.profiles=d.profiles||{};hpStore.active=d.active||null;if(d.profile)hpApply(d.profile);else if(!d.active)hpReset(true);try{localStorage.setItem('i3-hand-profile',JSON.stringify(HP));}catch(e){}hpStoreRender();syncHandProfileNote();return d;}catch(e){fmToast('PROFILE: '+e.message);return null;}}
function hpStoreLoad(){fetch('/api/hand-profiles',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{if(!d)return;hpStore.profiles=d.profiles||{};hpStore.active=d.active||null;hpStoreRender();}).catch(()=>{});}
document.addEventListener('click',async e=>{const b=e.target.closest('[data-hp]');if(!b)return;const row=b.closest('.i3-hp-row');const name=row?.dataset.name;if(!name)return;const op=b.dataset.hp;
 if(op==='use'){await hpStoreOp({op:'select',name});fmToast('USING '+name.toUpperCase());}
 else if(op==='rename'){const to=prompt('Rename calibration',name);if(to&&to.trim()&&to.trim()!==name)await hpStoreOp({op:'rename',name,to:to.trim()});}
 else if(op==='delete'){if(confirm('Delete calibration "'+name+'"?'))await hpStoreOp({op:'delete',name});}});
window.__i3HandProfiles={store:hpStore,op:hpStoreOp,load:hpStoreLoad};
/* Gate: a boolean that must hold for onMs before it turns on and for offMs before it turns off,
   so one misread frame can never flip a mode. */
const gates={};function gate(key,want,onMs,offMs,now){const g=gates[key]||(gates[key]={state:false,since:0,last:want});if(want!==g.last){g.last=want;g.since=now;}if(want!==g.state&&now-g.since>=(want?onMs:offMs))g.state=want;return g.state;}
/* Raw measurements used by both the detectors and the calibration wizard. */
function handMetrics(h){const w=h[0];const size=Math.max(.02,dist(h[0],h[9]));const pairs=[[8,6],[12,10],[16,14],[20,18]];const ext=pairs.map(([t,p])=>dist(h[t],w)/Math.max(1e-4,dist(h[p],w)));
 const straight=[[5,6,8],[9,10,12],[13,14,16],[17,18,20]].map(([m,p,t])=>{const a=[h[p].x-h[m].x,h[p].y-h[m].y],b=[h[t].x-h[p].x,h[t].y-h[p].y];const la=Math.hypot(a[0],a[1]),lb=Math.hypot(b[0],b[1]);return la&&lb?(a[0]*b[0]+a[1]*b[1])/(la*lb):0;});
 const spread=[dist(h[8],h[12]),dist(h[12],h[16]),dist(h[16],h[20])].map(d=>d/size);const thumbLen=dist(h[4],h[2]);
 return {size,ext,straight,spread,pinch:dist(h[8],h[4])/size,thumbDy:thumbLen>0?(h[4].y-h[2].y)/thumbLen:0,thumbLen:thumbLen/size,thumbOut:dist(h[4],h[9])/size};}
/* ── Calibration wizard ──────────────────────────────────────────────────────────
   Five actions, each shown by an animated hand and captured the moment the detector sees
   it held steady (no timer to wait out). Coarse geometric checks decide when a pose is
   present, then the medians of the captured frames set the thresholds midway between poses.
   The SWIPE step records the operator's natural palm-swipe speed for scrolling. */
const calib={active:false};
/* Trusted (hardware) input only: the synthetic events the finger cursor dispatches are untrusted. */
const physicalInput={at:-1e9,kind:''};
for(const [type,kind] of [['mousemove','mouse'],['wheel','trackpad'],['mousedown','mouse'],['keydown','keyboard'],['touchstart','touch'],['pointerdown','pointer']])
 addEventListener(type,e=>{if(!e.isTrusted)return;if(type==='mousemove'&&e.movementX===0&&e.movementY===0)return;physicalInput.at=performance.now();physicalInput.kind=kind;},{capture:true,passive:true});
function i3Log(source,message){try{fetch('/api/log',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source,message}),keepalive:true}).catch(()=>{});}catch(e){}}
window.__i3Log=i3Log;
const CALIB_STEPS=[
 {key:'open',name:'OPEN HAND',hint:'Hold one hand open, fingers spread, palm to the camera.',pose:'open'},
 {key:'fist',name:'FIST',hint:'Close the same hand into a fist.',pose:'fist'},
 {key:'pinch',name:'PINCH',hint:'Touch your index fingertip to your thumb tip.',pose:'pinch'},
 {key:'thumb',name:'THUMBS UP',hint:'Fist with the thumb pointing straight up.',pose:'thumb'},
 {key:'swipe',name:'SWIPE',hint:'Open hand: swipe down, then up, at the speed you would scroll.',pose:'swipe'}];
/* Animated hand: palm + five finger chains with per-finger curl, drawn in 2.5D with a
   light from the upper left. pose(t) returns finger curls, thumb angle, spread and offset. */
function calibPose(pose,t){const ease=x=>x<0?0:x>1?1:x*x*(3-2*x);const cyc=(t%2.6)/2.6;const k=ease(cyc<.5?cyc/.42:1-(cyc-.5)/.42);
 const base={curl:[0,0,0,0],thumb:0,spread:1,dy:0,dx:0,pinch:0};
 if(pose==='open')return Object.assign(base,{spread:.6+.4*k});
 if(pose==='fist')return Object.assign(base,{curl:[k,k,k,k],thumb:k*.9,spread:1-.6*k});
 if(pose==='pinch')return Object.assign(base,{curl:[k*.55,.15*k,.2*k,.25*k],thumb:k*.7,pinch:k,spread:.7});
 if(pose==='thumb')return Object.assign(base,{curl:[k,k,k,k],thumb:-k,spread:1-.6*k});
 if(pose==='swipe'){const s=(t%2.4)/2.4;const y=s<.5?ease(s/.5):1-ease((s-.5)/.5);return Object.assign(base,{spread:.9,dy:(y-.5)*2});}
 return base;}
function drawCalibHand2D(canvas,pose,t){const ctx=canvas.getContext('2d');const w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);const P=calibPose(pose,t);const s=Math.min(w,h)/260;
 ctx.save();ctx.translate(w/2+P.dx*40*s,h*.58-P.dy*60*s);ctx.scale(s,s);
 const skin=ctx.createLinearGradient(-60,-120,60,60);skin.addColorStop(0,'#2c7bd1');skin.addColorStop(1,'#0c2f66');const edge='rgba(160,225,255,.9)';
 const seg=(x0,y0,x1,y1,r)=>{ctx.beginPath();ctx.lineCap='round';ctx.lineWidth=r*2;ctx.strokeStyle=skin;ctx.moveTo(x0,y0);ctx.lineTo(x1,y1);ctx.stroke();ctx.lineWidth=r*2-2.5;ctx.strokeStyle='rgba(120,200,255,.22)';ctx.stroke();};
 /* palm */
 ctx.beginPath();ctx.moveTo(-42,-10);ctx.quadraticCurveTo(-46,40,-30,62);ctx.lineTo(30,62);ctx.quadraticCurveTo(48,40,44,-6);ctx.quadraticCurveTo(30,-30,0,-30);ctx.quadraticCurveTo(-30,-30,-42,-10);ctx.closePath();ctx.fillStyle=skin;ctx.fill();ctx.lineWidth=1.5;ctx.strokeStyle=edge;ctx.stroke();
 /* fingers: base positions across the palm top, lengths, curl folds each joint */
 const bases=[[-30,-26],[-10,-31],[10,-30],[30,-24]],lens=[[30,24,18],[34,26,20],[32,25,19],[26,20,16]];
 bases.forEach((b,i)=>{const c=P.curl[i];const spreadA=(i-1.5)*.16*P.spread;let x=b[0],y=b[1],a=-Math.PI/2+spreadA;const r=[9,8,7];
  for(let j=0;j<3;j++){a+=c*(j===0?.9:1.25);const nx=x+Math.cos(a)*lens[i][j],ny=y+Math.sin(a)*lens[i][j];seg(x,y,nx,ny,r[j]);x=nx;y=ny;}
  if(P.pinch&&i===0){ctx.beginPath();ctx.arc(x,y,4+P.pinch*3,0,7);ctx.fillStyle='rgba(255,220,120,'+(.5*P.pinch)+')';ctx.fill();}});
 /* thumb: from the palm's lower left, angle from horizontal-out (0) to folded across (+) or up (-) */
 {let x=-40,y=26;const r=[10,9,8];const L=[26,22,18];let a=P.thumb>=0?-Math.PI*.72+P.thumb*Math.PI*.55:-Math.PI*.72+Math.abs(P.thumb)*Math.PI*.22;for(let j=0;j<3;j++){if(j)a+=P.thumb>0?.45*P.thumb:.08;const nx=x+Math.cos(a)*L[j],ny=y+Math.sin(a)*L[j];seg(x,y,nx,ny,r[j]);x=nx;y=ny;}}
 /* wrist */
 ctx.beginPath();ctx.moveTo(-28,62);ctx.lineTo(-24,100);ctx.lineTo(24,100);ctx.lineTo(28,62);ctx.fillStyle=skin;ctx.fill();ctx.strokeStyle=edge;ctx.stroke();
 if(pose==='swipe'){ctx.strokeStyle='rgba(120,225,255,.8)';ctx.lineWidth=2;ctx.setLineDash([6,6]);ctx.beginPath();ctx.moveTo(80,-70);ctx.lineTo(80,70);ctx.stroke();ctx.setLineDash([]);const ay=P.dy>0?70:-70;ctx.beginPath();ctx.moveTo(80,ay);ctx.lineTo(74,ay-Math.sign(ay)*10);ctx.moveTo(80,ay);ctx.lineTo(86,ay-Math.sign(ay)*10);ctx.stroke();}
 ctx.restore();}
/* ── 3D calibration hand (Three.js): the articulated robotic model is shown only by
   the wizard. It follows calibPose(), faces the camera, and mirrors to the detected hand. */
const H3={ready:false,loading:false,failed:false};
function h3Build(canvas){
 const rig=window.I3RobotHand.create(canvas);
 /* Face the palm squarely toward the camera. The pose animator moves the joints; the
    calibration model must not slowly rotate away from the pose the operator must copy. */
 rig.yaw=0;rig.pitch=-.04;rig.zoom=8.5;rig.playing=true;rig.calibrationHand=leftHanded()?'left':'right';
 return rig;}
function h3Pose(rig,pose,t){window.I3RobotHand.pose(rig,calibPose(pose,t));/* Palm-facing mirror: the operator's right thumb appears on screen-right. */rig.root.scale.x=rig.calibrationHand==='left'?1:-1;}
function h3Load(){if(H3.ready||H3.loading||H3.failed)return;H3.loading=true;
 const load=(src,ready)=>ready()?Promise.resolve():new Promise((resolve,reject)=>{let el=document.querySelector('script[src="'+src+'"]');if(!el){el=document.createElement('script');el.src=src;document.head.appendChild(el);}if(ready()){resolve();return;}el.addEventListener('load',resolve,{once:true});el.addEventListener('error',reject,{once:true});});
 load('/assets/lunar/three.min.js',()=>!!window.THREE).then(()=>load('/assets/hand/robot-hand.js',()=>!!window.I3RobotHand)).then(()=>{H3.ready=!!window.I3RobotHand;H3.failed=!H3.ready;H3.loading=false;}).catch(()=>{H3.failed=true;H3.loading=false;});}
window.__i3Hand3dLoad=h3Load;
function drawCalibHand(canvas,pose,t){
 if(H3.ready&&window.I3RobotHand){if(!canvas.__rig&&!canvas.__rigFailed){try{canvas.__rig=h3Build(canvas);}catch(e){canvas.__rigFailed=true;console.warn('[studio] robotic calibration hand unavailable',e);}}if(canvas.__rig){h3Pose(canvas.__rig,pose,t);return;}}
 if(!H3.failed&&!canvas.__rigFailed){h3Load();return;}
 drawCalibHand2D(canvas,pose,t);}
/* ── Sensor showcase: procedural 3D sensor models (Three.js) + live channel figures ── */
const SC={rig:null,side:'ch1',raf:0};
function scModels(T){
 /* Sensor model study (supplied): SRC1 breakout and the rough Ch2 probe. Every
    dimension lives here; the shapes are illustrative, not mechanical drawings. */
 const mat=(c,metal=.2,rough=.4,emit=0)=>new T.MeshStandardMaterial({color:c,metalness:metal,roughness:rough,emissive:emit,emissiveIntensity:emit?0.5:0});
 const roundedBox=(w,h,d,r,material)=>{const shape=new T.Shape();const x=-w/2,y=-h/2;shape.moveTo(x+r,y);shape.lineTo(x+w-r,y);shape.quadraticCurveTo(x+w,y,x+w,y+r);shape.lineTo(x+w,y+h-r);shape.quadraticCurveTo(x+w,y+h,x+w-r,y+h);shape.lineTo(x+r,y+h);shape.quadraticCurveTo(x,y+h,x,y+h-r);shape.lineTo(x,y+r);shape.quadraticCurveTo(x,y,x+r,y);const g=new T.ExtrudeGeometry(shape,{depth:d,bevelEnabled:true,bevelSize:r*.35,bevelThickness:r*.35,bevelSegments:3});g.translate(0,0,-d/2);return new T.Mesh(g,material);};
 const textSprite=(text,color)=>{const c=document.createElement('canvas');c.width=360;c.height=80;const x=c.getContext('2d');x.font='24px monospace';x.fillStyle=color;x.fillText(text,12,45);const sp=new T.Sprite(new T.SpriteMaterial({map:new T.CanvasTexture(c),transparent:true}));sp.scale.set(1.6,.35,1);return sp;};
 const ch1=()=>{const root=new T.Group(),board=mat(0x123b58,.25,.46),dark=mat(0x111b27,.75,.28),metal=mat(0xc2d2dd,.8,.24),cyan=mat(0x58e8ee,.55,.25,0x124d5d);root.add(roundedBox(3.1,2.2,.16,.16,board));const chip=roundedBox(.75,.58,.2,.08,dark);chip.position.z=.2;root.add(chip);
  for(const x of [-1.28,1.28])for(const y of [-.82,.82]){const p=new T.Mesh(new T.CylinderGeometry(.08,.08,.08,16),metal);p.rotation.x=Math.PI/2;p.position.set(x,y,.15);root.add(p);}
  for(let i=0;i<3;i++){const ring=new T.Mesh(new T.TorusGeometry(.34+i*.17,.015,8,48),cyan);ring.rotation.x=Math.PI/2;ring.position.z=.34;root.add(ring);}
  for(const [txt,x,y,z] of [['SRC1',-0.53,-.08,.34],['X',1.15,.3,.28],['Y',1.15,0,.28],['Z',1.15,-.3,.28]]){const sp=textSprite(txt,txt==='SRC1'?'#d8faff':'#58e8ee');sp.position.set(x,y,z);sp.scale.set(txt==='SRC1'?1.15:.3,.23,1);root.add(sp);}
  const axes=new T.AxesHelper(1.2);axes.position.set(0,0,.42);root.add(axes);root.scale.setScalar(.8);return root;};
 const ch2=()=>{const root=new T.Group(),body=mat(0x182d43,.68,.3),shell=mat(0x9aaebe,.72,.27),cyan=mat(0x54e5ef,.5,.22,0x0d4a59),wire=mat(0xbac8d1,.8,.2);const tube=roundedBox(1.25,2.75,.7,.18,body);tube.rotation.z=-.18;root.add(tube);
  const collar=new T.Mesh(new T.CylinderGeometry(.48,.48,.18,32),shell);collar.rotation.z=-.18;collar.position.set(.2,1.27,0);root.add(collar);
  const probe=new T.Mesh(new T.ConeGeometry(.27,.72,32),cyan);probe.rotation.z=-.18;probe.position.set(.35,1.72,0);root.add(probe);
  const board=roundedBox(1.45,.95,.14,.1,body);board.position.set(-.15,-.85,.42);root.add(board);
  for(let i=0;i<6;i++){const pin=new T.Mesh(new T.CylinderGeometry(.035,.035,.3,8),wire);pin.rotation.x=Math.PI/2;pin.position.set(-.62+i*.2,-.85,.55);root.add(pin);}
  for(let i=0;i<4;i++){const t=new T.Mesh(new T.TorusGeometry(.4+i*.12,.012,8,40),cyan);t.rotation.x=Math.PI/2;t.position.set(.35,1.72,.4);root.add(t);}
  const label=textSprite('CHANNEL 2','#d8faff');label.position.set(-.7,-1.05,.52);label.scale.set(1.2,.23,1);root.add(label);root.scale.setScalar(.7);return root;};
 return {ch1:ch1(),ch2:ch2()};}
function scBuild(canvas){const T=window.THREE;const renderer=new T.WebGLRenderer({canvas,alpha:true,antialias:true});renderer.setPixelRatio(Math.min(2,devicePixelRatio||1));renderer.outputColorSpace=T.SRGBColorSpace;const size=()=>{const r=canvas.getBoundingClientRect();renderer.setSize(Math.max(1,r.width),Math.max(1,r.height),false);cam.aspect=r.width/Math.max(1,r.height);cam.updateProjectionMatrix();};
 const scene=new T.Scene();const cam=new T.PerspectiveCamera(35,1,.1,100);cam.position.set(0,0,7);
 scene.add(new T.HemisphereLight(0xdff8ff,0x081221,1.7));const key=new T.DirectionalLight(0xffffff,3);key.position.set(-3,4,6);scene.add(key);const rim=new T.DirectionalLight(0x35d7e6,2);rim.position.set(4,1,-4);scene.add(rim);
 const models=scModels(T);const holder=new T.Group();models.ch1.position.x=-2.05;models.ch2.position.x=2.05;holder.add(models.ch1,models.ch2);scene.add(holder);
 const rig={renderer,scene,cam,holder,models,side:'ch1',size,yaw:.12,pitch:-.12,zoom:8.2,velYaw:0,velPitch:0,drag:null,touchedAt:0};size();addEventListener('resize',size,{passive:true});
 /* Orbit: drag or hand movement turns the model, wheel (when grabbed) or hand spread zooms;
    momentum coasts after release. The same controls the globe and constellation expose. */
 canvas.addEventListener('pointerdown',e=>{rig.drag=[e.clientX,e.clientY];rig.touchedAt=performance.now();try{canvas.setPointerCapture(e.pointerId);}catch(err){}});
 canvas.addEventListener('pointermove',e=>{if(!rig.drag)return;const dx=(e.clientX-rig.drag[0])*.009,dy=(e.clientY-rig.drag[1])*.009;rig.yaw+=dx;rig.pitch=clamp(rig.pitch+dy,-1.3,1.3);rig.velYaw=dx;rig.velPitch=dy;rig.drag=[e.clientX,e.clientY];rig.touchedAt=performance.now();});
 const up=()=>{rig.drag=null;};canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',up);
 /* Wheel zooms while the pointer rests on the model (trackpad pinch arrives as ctrl+wheel); a wheel that
    starts as a page scroll passing over the canvas keeps scrolling the page. */
 canvas.addEventListener('pointerenter',()=>{rig.hoverAt=performance.now();});canvas.addEventListener('pointerleave',()=>{rig.hoverAt=0;rig.drag=null;});
 canvas.addEventListener('wheel',e=>{const rested=rig.hoverAt&&performance.now()-rig.hoverAt>350;if(!e.ctrlKey&&!rested&&performance.now()-rig.touchedAt>3000)return;e.preventDefault();rig.zoom=clamp(rig.zoom+e.deltaY*(e.ctrlKey?.02:.006),3.2,12);rig.touchedAt=performance.now();},{passive:false});
 const ctl=document.createElement('div');ctl.className='i3-sc-zoom';ctl.innerHTML='<button type="button" data-z="in" title="Zoom in">+</button><button type="button" data-z="out" title="Zoom out">−</button><button type="button" data-z="reset" title="Reset view">⟲</button>';canvas.parentElement.appendChild(ctl);
 ctl.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const z=b.dataset.z;if(z==='in')rig.zoom=clamp(rig.zoom-1.2,3.2,12);else if(z==='out')rig.zoom=clamp(rig.zoom+1.2,3.2,12);else{rig.zoom=7;rig.yaw=.35;rig.pitch=-.18;rig.velYaw=rig.velPitch=0;}rig.touchedAt=performance.now();});
 /* Hand contract shared with the globe and constellation: `physics` receives the GesturePhysics angular delta
    (momentum, damping, two-hand pitch) while the model is held; `zoom` takes the two-hand spread. */
 canvas.__i3LegacyHandControls={physics:function(delta){rig.yaw+=delta[1];rig.pitch=clamp(rig.pitch+delta[0],-1.3,1.3);rig.velYaw=clamp(delta[1]*.6,-.08,.08);rig.velPitch=clamp(delta[0]*.6,-.06,.06);rig.touchedAt=performance.now();},rotate:function(screenDx){rig.yaw+=screenDx*3.2;rig.velYaw=clamp(screenDx*.05,-.08,.08);rig.touchedAt=performance.now();},zoom:function(handScale){rig.zoom=clamp(7/Math.max(.5,handScale),3.2,12);rig.touchedAt=performance.now();}};
 canvas.title='Drag to orbit · scroll or pinch to zoom · pinch with the hand to hold';return rig;}
function scShow(side){const rig=SC.rig;if(!rig)return;rig.side=side;
 for(const key of ['ch1','ch2']){const selected=key===side;rig.models[key].traverse(o=>{if(!o.material)return;const mats=Array.isArray(o.material)?o.material:[o.material];mats.forEach(m=>{if(!m.userData.i3Base){m.userData.i3Base={opacity:m.opacity,emissiveIntensity:m.emissiveIntensity};}m.transparent=true;m.opacity=selected?m.userData.i3Base.opacity:m.userData.i3Base.opacity*.48;if('emissiveIntensity' in m)m.emissiveIntensity=m.userData.i3Base.emissiveIntensity*(selected?1.3:.45);});});}}
function scFrame(t){SC.raf=requestAnimationFrame(scFrame);const rig=SC.rig;if(!rig||document.hidden)return;const canvas=rig.renderer.domElement;if(!canvas.isConnected){cancelAnimationFrame(SC.raf);SC.raf=0;SC.rig=null;return;}const r=canvas.getBoundingClientRect();if(r.bottom<0||r.top>innerHeight)return;
 if(!rig.drag){rig.yaw+=rig.velYaw;rig.pitch=clamp(rig.pitch+rig.velPitch,-1.3,1.3);rig.velYaw*=.94;rig.velPitch*=.9;if(performance.now()-rig.touchedAt>2500)rig.yaw+=.0025;}
 for(const model of Object.values(rig.models))model.rotation.set(rig.pitch,rig.yaw,0);rig.holder.position.y=Math.sin(t*.0011)*.08;rig.cam.position.z+=(rig.zoom-rig.cam.position.z)*.15;rig.renderer.render(rig.scene,rig.cam);}
function scLive(){const packet=window.__i3Instrument;const stage=document.querySelector('[data-i3-showcase]');if(!stage||!packet)return;
 for(const side of ['ch1','ch2']){const ch=packet.channels?.[side];const det=stage.querySelector('[data-i3-sc-side="'+side+'"]');if(!det)continue;
  const fmt=(k)=>{if(!ch)return ['—',0];if(k==='sample_rate'){const v=ch.sample_rate;return finite(v)?[v.toFixed(1)+' Hz',clamp(v/(side==='ch1'?12:120)*100,0,100)]:['—',0];}
   if(k==='snr'){const v=ch.snr;return finite(v)?[v.toFixed(2),clamp(v/6*100,0,100)]:['—',0];}
   if(k==='confidence'){const v=ch.confidence;return finite(v)?[v.toFixed(0)+' %',clamp(v,0,100)]:['—',0];}return ['—',0];};
  det.querySelectorAll('[data-i3-sc-value]').forEach(el=>{const [txt,pct]=fmt(el.dataset.i3ScValue);if(el.textContent!==txt)el.textContent=txt;const bar=det.querySelector('[data-i3-sc-bar="'+el.dataset.i3ScValue+'"]');if(bar)bar.style.width=pct.toFixed(0)+'%';});
  const st=det.querySelector('[data-i3-sc-state]');const status=det.querySelector('.i3-sc-status');if(st){const state=ch?String(ch.state||'offline'):'waiting';const label=state==='connected'?(ch.data_source==='SIMULATED'?'Simulated · connected':'Connected · '+(finite(ch.deviation)?ch.deviation.toFixed(2)+' '+(ch.unit||''):'live')):state;if(st.textContent!==label)st.textContent=label;if(state==='connected')status.removeAttribute('data-off');else status.setAttribute('data-off','1');}}}
function mountShowcase(){const stage=document.querySelector('[data-i3-showcase]');if(!stage)return;
 /* .i3-sc-boards belongs to boards.js, which self-scans for canvas[data-i3-boards]
    and mounts its own WebGL renderer. Building a second renderer on that same
    canvas does not fail loudly -- a canvas only ever has one WebGL context, so
    THREE hands the second renderer the first one's, and the two then corrupt each
    other's state. Only the older single-model .i3-sc-canvas is ours. */
 const canvas=stage.querySelector('.i3-sc-canvas');
 const root=stage.closest('.i3-showcase')||stage;if(!stage.dataset.i3ScInit){stage.dataset.i3ScInit='1';root.querySelectorAll('[data-i3-sc]').forEach(b=>b.addEventListener('click',()=>{SC.side=b.dataset.i3Sc;stage.dataset.i3Showcase=SC.side;root.querySelectorAll('[data-i3-sc]').forEach(x=>x.classList.toggle('on',x===b));stage.querySelectorAll('.i3-sc-details').forEach(d=>d.classList.toggle('on',d.dataset.i3ScSide===SC.side));scShow(SC.side);}));
  stage.querySelectorAll('.i3-sc-details').forEach(d=>d.classList.toggle('on',d.dataset.i3ScSide===SC.side));setInterval(scLive,1000);scLive();}
 if(canvas&&!SC.rig){h3Load();if(window.THREE){try{SC.rig=scBuild(canvas);scShow(SC.side);if(!SC.raf)SC.raf=requestAnimationFrame(scFrame);if(typeof retargetHandVision==='function')retargetHandVision();}catch(e){console.warn('[studio] showcase 3D unavailable',e);}}else setTimeout(mountShowcase,400);}}
/* Is this frame the pose we are waiting for? Coarse and relative to what was captured before. */
function calibMatches(key,m,r){const minExt=Math.min(...m.ext),maxExt=Math.max(...m.ext);
 if(key==='open')return minExt>1.12&&Math.min(...m.straight)>.5&&m.pinch>.45;
 const openExt=r.open?med(r.open.map(x=>Math.min(...x.ext))):1.4;
 if(key==='fist')return maxExt<Math.min(1.05,openExt-.2);
 if(key==='pinch'){const po=r.open?med(r.open.map(x=>x.pinch)):.8;return m.pinch<po*.45&&m.ext[1]>1.0;}
 if(key==='thumb')return maxExt<Math.min(1.08,openExt-.15)&&m.thumbDy<-.45&&m.thumbLen>.5;
 return false;}
function med(a){const b=a.filter(Number.isFinite).sort((x,y)=>x-y);return b.length?b[Math.floor(b.length/2)]:NaN;}
function handCalibrate(){if(calib.active)return;h3Load();i3Log('gesture','Hand calibration wizard started');if(!window.__i3HandVisionRunning){fmToast('TURN THE CAMERA ON FIRST (shortcut C)');return;}
 const el=document.createElement('div');el.id='i3-hand-calib';el.innerHTML='<div class="i3-calib-card"><div class="i3-calib-kicker">HAND CALIBRATION</div><div class="i3-calib-step"></div><canvas class="i3-calib-demo" width="300" height="240" aria-hidden="true"></canvas><div class="i3-calib-hint"></div><div class="i3-calib-status"><span class="i3-calib-dot"></span><span class="i3-calib-seen"></span></div><div class="i3-calib-steps"></div><button type="button" class="i3-calib-cancel">CANCEL</button></div>';document.body.appendChild(el);
 const stepEl=el.querySelector('.i3-calib-step'),hintEl=el.querySelector('.i3-calib-hint'),seenEl=el.querySelector('.i3-calib-seen'),dot=el.querySelector('.i3-calib-dot'),demo=el.querySelector('.i3-calib-demo'),stepsEl=el.querySelector('.i3-calib-steps');
 stepsEl.innerHTML=CALIB_STEPS.map(st=>'<span data-step="'+st.key+'">'+st.name+'</span>').join('');
 Object.assign(calib,{active:true,index:0,phase:'wait',phaseAt:performance.now(),samples:[],results:{},el,swipe:{peak:0,down:0,up:0,lastY:null,lastT:0}});
 const showStep=()=>{const st=CALIB_STEPS[calib.index];if(!st)return;stepEl.textContent=(calib.index+1)+' / '+CALIB_STEPS.length+' · '+st.name;hintEl.textContent=st.hint;stepsEl.querySelectorAll('span').forEach(sp=>sp.classList.toggle('now',sp.dataset.step===st.key));};showStep();seenEl.textContent='WAITING FOR YOUR HAND';
 let raf=0;const anim=(t)=>{if(!calib.active)return;raf=requestAnimationFrame(anim);const st=CALIB_STEPS[calib.index];if(st)drawCalibHand(demo,st.pose,t/1000);};raf=requestAnimationFrame(anim);
 const setState=(cls,text)=>{dot.className='i3-calib-dot '+cls;seenEl.textContent=text;};
 const finish=(ok)=>{calib.active=false;cancelAnimationFrame(raf);el.remove();if(!ok){fmToast('CALIBRATION CANCELLED');return;}
  const r=calib.results;
  const openExt=med(r.open.map(m=>Math.min(...m.ext))),fistExt=med(r.fist.map(m=>Math.max(...m.ext)));
  const pinchOpen=med(r.open.map(m=>m.pinch)),pinchClosed=med(r.pinch.map(m=>m.pinch));
  const openStraight=med(r.open.map(m=>Math.min(...m.straight))),openSpread=med(r.open.map(m=>Math.min(...m.spread)));
  const thumbUp=med(r.thumb.map(m=>m.thumbDy)),thumbOutOpen=med(r.open.map(m=>m.thumbOut));
  const span=Math.max(.15,openExt-fistExt);
  const peak=calib.swipe.peak;
  const profile={ext:Math.max(1.05,fistExt+span*.55),curl:Math.max(1.0,fistExt+span*.4),
   pinchOn:Math.max(.12,pinchClosed+(pinchOpen-pinchClosed)*.26),pinchOff:Math.max(.2,pinchClosed+(pinchOpen-pinchClosed)*.45),
   thumbDy:clamp(Math.abs(thumbUp)*.7,.35,.7),straight:clamp(openStraight-.12,.45,.85),spread:clamp(openSpread*.6,.08,.2),thumbOut:clamp(thumbOutOpen*.7,.4,.8),
   swipeMin:peak>0?clamp(peak*.28,.05,.2):HP.swipeMin,swipeGain:peak>0?clamp(.45/peak,.8,2.6):HP.swipeGain,calibrated:true};
  if(![openExt,fistExt,pinchOpen,pinchClosed,thumbUp].every(Number.isFinite)){fmToast('CALIBRATION FAILED · a pose was not captured');return;}
  hpApply(profile);try{localStorage.setItem('i3-hand-profile',JSON.stringify(HP));}catch(e){}
  const n=Object.keys(hpStore.profiles).length+1;const suggested=hpStore.active&&!hpStore.profiles[hpStore.active]?hpStore.active:'Profile '+n;
  const name=(prompt('Calibration complete. Name this profile:',suggested)||suggested).trim().slice(0,40)||suggested;
  hpStoreOp({op:'save',name,profile:HP}).then(()=>{fmToast('HAND CALIBRATED · '+name.toUpperCase());});
  i3Log('gesture','Hand calibration saved as "'+name+'" (swipe peak '+peak.toFixed(2)+')');syncHandProfileNote();};
 el.querySelector('.i3-calib-cancel').addEventListener('click',()=>finish(false));
 const advance=(now)=>{stepsEl.querySelector('[data-step="'+CALIB_STEPS[calib.index].key+'"]').classList.add('done');calib.index++;calib.phase='wait';calib.phaseAt=now;calib.samples=[];if(calib.index>=CALIB_STEPS.length)finish(true);else{showStep();setState('','WAITING FOR '+CALIB_STEPS[calib.index].name);}};
 calib.feed=(sets,handedness)=>{if(!calib.active)return;const now=performance.now();const st=CALIB_STEPS[calib.index];if(!st)return;stepEl.textContent=(calib.index+1)+' / '+CALIB_STEPS.length+' · '+st.name;hintEl.textContent=st.hint;
  stepsEl.querySelectorAll('span').forEach(sp=>sp.classList.toggle('now',sp.dataset.step===st.key));
  const h=sets.length?sets.reduce((a,b)=>dist(a[0],a[9])>=dist(b[0],b[9])?a:b):null;
  if(h){const i=sets.indexOf(h),entry=handedness?.[i]?.label?handedness[i]:handedness?.[i]?.[0],hand=entry?.label==='Left'?'right':entry?.label==='Right'?'left':null;if(hand){calib.visualHand=hand;if(demo.__rig)demo.__rig.calibrationHand=hand;}}
  if(calib.phase==='captured')return;
  if(!h){setState('','NO HAND IN VIEW');calib.samples=[];calib.swipe.lastY=null;return;}
  const m=handMetrics(h);
  if(st.key==='swipe'){const y=(h[0].y+h[9].y)/2;const sw=calib.swipe;if(sw.lastY!==null){const dt=(now-sw.lastT)/1000;if(dt>0&&dt<.3){const vy=(y-sw.lastY)/dt;const open=Math.min(...m.ext)>1.05;if(open){if(vy>.25&&Math.abs(vy)>sw.down){sw.down=Math.abs(vy);}if(vy<-.25&&Math.abs(vy)>sw.up){sw.up=Math.abs(vy);}}}}sw.lastY=y;sw.lastT=now;
   sw.peak=Math.min(sw.down||0,sw.up||0)||Math.max(sw.down,sw.up);
   if(sw.down&&sw.up){setState('ok','SWIPE CAPTURED · '+sw.peak.toFixed(2));calib.phase='captured';calib.phaseAt=now;setTimeout(()=>{if(calib.active&&calib.phase==='captured')advance(performance.now());},750);return;}
   setState('scan',sw.down?'DOWN SEEN · NOW SWIPE UP':sw.up?'UP SEEN · NOW SWIPE DOWN':'SCANNING · SWIPE DOWN');return;}
  if(calibMatches(st.key,m,calib.results)){calib.samples.push(m);const n=calib.samples.length;setState('scan','SCANNING · HOLD IT · '+Math.min(100,Math.round(n/10*100))+'%');
   if(n>=10){calib.results[st.key]=calib.samples.slice();setState('ok','CAPTURED ✓');calib.phase='captured';calib.phaseAt=now;setTimeout(()=>{if(calib.active&&calib.phase==='captured')advance(performance.now());},750);}}
  else{if(calib.samples.length)calib.samples.length=Math.max(0,calib.samples.length-2);const waited=now-calib.phaseAt;setState('',waited>6000?'NOT RECOGNISED YET · MATCH THE HAND SHOWN':'WAITING FOR '+st.name);}};}
function syncHandProfileNote(){const note=HP.calibrated?'Calibrated to your hand · pinch '+HP.pinchOn.toFixed(2)+'/'+HP.pinchOff.toFixed(2)+' · extend '+HP.ext.toFixed(2)+' · thumb '+HP.thumbDy.toFixed(2)+' · swipe '+HP.swipeMin.toFixed(2)+'×'+HP.swipeGain.toFixed(1):'Using default thresholds. Calibrate once with the camera on for reliable pinch, thumbs and pause.';document.querySelectorAll('[data-i3-hand-profile-note]').forEach(n=>{if(n.textContent!==note)n.textContent=note;});
 const label='GESTURE DEBUG: '+(fingerMouse.debug?'ON':'OFF');document.querySelectorAll('[data-i3-action="hand_debug"]').forEach(b=>{if(b.textContent!==label)b.textContent=label;if(b.getAttribute('aria-pressed')!==String(!!fingerMouse.debug))b.setAttribute('aria-pressed',String(!!fingerMouse.debug));});}
/* ── Debug overlay: what the detector believes about each hand, updated ~12×/s ── */
function handDebug(sets,hands,extra){if(!fingerMouse.debug){const d=document.getElementById('i3-hand-debug');if(d)d.remove();return;}let d=document.getElementById('i3-hand-debug');if(!d){d=document.createElement('pre');d.id='i3-hand-debug';document.body.appendChild(d);}const now=performance.now();if(now-(fingerMouse.debugAt||0)<80)return;fingerMouse.debugAt=now;
 const lines=['HAND VISION · '+(extra.fps||0).toFixed(0)+' fps · profile '+(HP.calibrated?'calibrated':'default')];
 for(const [label,h] of [['R',hands.right],['L',hands.left]]){if(!h){lines.push(label+': —');continue;}const m=handMetrics(h);const flags=[fmPointing(h)?'point':'',fmPeace(h)?'peace':'',fmThumb(h)>0?'thumb↑':fmThumb(h)<0?'thumb↓':'',fmPinky(h)?'pinky':'',fmFullyOpen(h)?'OPEN':'',fmFist(h)?'fist':''].filter(Boolean).join(' ');
  lines.push(label+': pinch '+m.pinch.toFixed(2)+' (on<'+HP.pinchOn+' off>'+HP.pinchOff+')  ext '+m.ext.map(v=>v.toFixed(2)).join('/')+'  thumb '+m.thumbDy.toFixed(2)+'  '+flags);}
 lines.push('mode: '+(fingerMouse.paused?'PAUSED':fingerMouse.hold?(fingerMouse.peaceNow?'ROTATE':'HOLD'):fingerMouse.on?'cursor':'cursor off')+(fingerMouse.pinching?' · pinching':'')+(fingerMouse.thumbDir?' · scroll '+(fingerMouse.thumbDir>0?'up':'down'):'')+(extra.hands?' · hands '+extra.hands:''));
 d.textContent=lines.join('\n');}
const fingerMouse={hand3d:(()=>{try{return localStorage.getItem('i3-hand3d')!=='off';}catch(e){return true;}})(),debug:(()=>{try{return localStorage.getItem('i3-hand-debug')==='on';}catch(e){return false;}})(),on:true,hold:false,holdCanvas:null,cursor:null,fx:new OneEuro(.9,.35,1),fy:new OneEuro(.9,.35,1),lastSnapAt:0,contactAt:0,contactPos:null,pinchSince:0,clicked:false,ripple:null};
window.__i3FM=fingerMouse;window.__i3FmOpen=fmFullyOpen;hpLoad();hpStoreLoad();new MutationObserver(()=>syncHandProfileNote()).observe(document.body,{childList:true,subtree:true});
function fmCursor(){if(!fingerMouse.cursor){const el=document.createElement('div');el.id='i3-finger-cursor';el.setAttribute('aria-hidden','true');el.innerHTML='<span class="i3-cursor-dot"></span>';document.body.appendChild(el);fingerMouse.cursor=el;}return fingerMouse.cursor;}
/* One cursor position shared by the hand and the pointer, always clamped to the viewport. In
   IV-cursor mode the system pointer is hidden and this element follows whichever input moved
   last (pointer immediately, hand after a short blend); in Mac mode it appears only for the hand. */
const cursorPos={x:innerWidth/2,y:innerHeight/2,by:'none'};
function cursorMode(){try{return localStorage.getItem('i3-cursor-mode')||'iv';}catch(e){return 'iv';}}
/* Autonomous NVTRA character. It lives at the edge of the instrument, moves beside the
   interface only when context calls for it, and points toward real event/readout targets.
   Pointer events pass through it: the operator never puppets the character. */
const buddy={el:null,x:innerWidth,y:innerHeight,vx:0,vy:0,tx:0,ty:0,app:null,ready:false,raf:0,tries:0,mode:'home',until:0,pose:null,lastEvent:null,parked:true,homeAt:0,
 queue:[],clip:null,clipName:'',clipAt:0,clipRoot:null,pointing:null,engaged:false,engagedAt:0};
/* Opt-out, remembered per browser. Off removes the character from the page entirely
   rather than hiding it, so it costs nothing while it is not wanted. */
function buddyOn(){try{return localStorage.getItem('i3-buddy')!=='off';}catch(e){return true;}}
function setBuddyEnabled(on){try{localStorage.setItem('i3-buddy',on?'on':'off');}catch(e){}
 if(on){buddyMount();}else{buddyUnmount();}
 syncBuddyButton();}
function syncBuddyButton(){const label='NVTRA CHARACTER: '+(buddyOn()?'ON':'OFF');
 document.querySelectorAll('[data-i3-action="buddy_toggle"]').forEach(b=>{
   if(b.textContent!==label)b.textContent=label;
   b.setAttribute('aria-pressed',buddyOn()?'true':'false');});}
function embeddedNvtraVisible(){const h=document.getElementById('nvtra-spline-host');if(!h||!h.isConnected)return false;const r=h.getBoundingClientRect();return r.width>0&&r.height>0;}
function buddyMount(){if(buddy.el||embeddedNvtraVisible()||!buddyOn()||matchMedia('(pointer:coarse)').matches||reduced())return;const el=document.createElement('div');el.id='i3-buddy';el.className='i3-buddy-home';el.setAttribute('aria-hidden','true');const label=document.createElement('div');label.id='i3-buddy-label';el.appendChild(label);const c=document.createElement('canvas');el.appendChild(c);document.body.appendChild(el);buddy.el=el;
 // Click him - with the mouse or with the camera's finger cursor - to engage.
 // While engaged he copies your gestures back instead of them driving the page.
 c.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();buddyEngage(!buddy.engaged);});
 const start=()=>{const A=window.__NvtraSplineApplication;if(!A)return false;try{const app=new A(c,{wasmPath:'/_i3'});buddy.app=app;Promise.resolve(app.load('/_i3/nvtra-robot.splinecode')).then(()=>{try{app.setBackgroundColor('rgba(0,0,0,0)');}catch(e){}const objects=app.getAllObjects?.()||[];buddy.pose=buddyBind(objects);buddy.ready=true;
 try{app.addEventListener('mouseDown',ev=>{const part=String(ev?.target?.name||'').toLowerCase();const move=/foot|shin|leg/.test(part)?'jump':/hand|arm|elbow/.test(part)?'wave':/head|neck/.test(part)?'nod':'salute';buddyPerform(move);text(label,(part?part.toUpperCase()+' · ':'')+move.toUpperCase());});}catch(e){}
 i3Log('buddy','rig bound: '+Object.keys(buddy.pose).join(', '));buddyHome(true);}).catch(err=>{buddyRetry(err);});}catch(err){buddyRetry(err);}return true;};
 if(!start()){import('/_i3/spline-runtime.js').then(m=>{window.__NvtraSplineApplication=m.Application;if(buddy.el)start();}).catch(()=>{buddyUnmount();});}
 if(!buddy.raf)buddy.raf=requestAnimationFrame(buddyFrame);}
function buddyRetry(err){console.warn('[studio] NVTRA buddy failed to load',err);buddyUnmount();if(buddy.tries++<3)setTimeout(buddyMount,4000*buddy.tries);}
function buddyUnmount(){if(buddy.raf)cancelAnimationFrame(buddy.raf);buddy.raf=0;try{buddy.app?.dispose?.();}catch(e){}buddy.app=null;buddy.ready=false;buddy.el?.remove();buddy.el=null;}
// ── the character's skeleton ──────────────────────────────────────────────────
// The Spline scene has a full humanoid rig - Body, Neck, Head, arm, elbow,
// forearm, Hand, Hand LEFT, Leg Left (and its mirrored Instance), shin, Foot -
// but only four of those were ever bound, so the character had no legs to move
// and could do nothing but point. Every joint the scene exposes is bound here.
//
// Names are matched loosely because Spline lets you rename anything: each entry
// is tried in order and the first object whose name matches wins. `mirror` picks
// the second match instead of the first, which is how the right limb is found
// when the scene stores it as an Instance of the left.
// The scene stores mirrored limbs as a named object plus an "Instance" of it, and
// several objects share a name outright - there are two "arm", two "elbow", two
// "shin", two "Foot" and two "Leg Left" (one of them "Leg Left Instance"). Binding
// by name alone therefore aliases: the first version of this bound legL and legR to
// the SAME object, so the backflip tucked one leg twice and the other never moved.
//
// `used` fixes that. Each rig key takes the first object matching one of its
// patterns that no other key has already claimed, so the second "arm" naturally
// becomes the left arm. Order matters: right-side keys are listed before their left
// counterparts, because the scene's primary (non-Instance) object is the right one.
const BUDDY_JOINTS = [
 ['head',    [/^head$/i, /head/i]],
 ['neck',    [/^neck$/i, /neck/i]],
 ['body',    [/^body$/i, /^bodyg$/i, /torso/i]],
 ['armR',    [/^arm$/i, /shoulder/i]],
 ['elbowR',  [/^elbow$/i]],
 ['forearmR',[/^forearm$/i]],
 ['handR',   [/^hand$/i]],
 ['armL',    [/^arm$/i, /shoulder/i]],
 ['elbowL',  [/^elbow$/i]],
 ['forearmL',[/^forearm$/i]],
 ['handL',   [/hand\s*left/i, /^hand/i]],
 ['legL',    [/^leg\s*left$/i, /^leg/i]],
 ['legR',    [/leg\s*left\s*instance/i, /^leg/i]],
 ['shinL',   [/^shin$/i]],
 ['shinR',   [/^shin$/i]],
 ['footL',   [/^foot$/i]],
 ['footR',   [/^foot$/i]],
];
function buddyBind(objects){
 const rig={},used=new Set();
 const pool=objects.filter(o=>o&&o.rotation);
 for(const [key,patterns] of BUDDY_JOINTS){
  for(const re of patterns){
   const pick=pool.find(o=>!used.has(o)&&re.test(o.name||''));
   if(pick){used.add(pick);rig[key]=pick;break;}
  }
 }
 for(const o of Object.values(rig)){
  if(o&&!o.__i3Base)o.__i3Base={x:o.rotation.x,y:o.rotation.y,z:o.rotation.z};
 }
 return rig;}

// ── clips ─────────────────────────────────────────────────────────────────────
// A clip is a duration plus two functions of normalised time k in [0,1]:
//   pose(k)  -> {jointName:{x,y,z}} rotation OFFSETS from the joint's rest pose
//   root(k)  -> {x,y,rot,scale}     whole-body motion, applied to the element
// Offsets rather than absolutes, so a clip cannot destroy the rest pose and any
// joint the scene happens not to have is simply skipped.
const ease=k=>k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;
const BUDDY_CLIPS={
 // A real wave: the upper arm lifts and stays lifted while the forearm and hand
 // oscillate. Waving from the shoulder looks like semaphore, not a greeting.
 wave:{ms:2200,label:'WAVING',pose:k=>{
  const lift=Math.min(1,k*6)*Math.min(1,(1-k)*6),s=Math.sin(k*Math.PI*7);
  return {armR:{z:-1.9*lift,x:.25*lift},elbowR:{z:-.75*lift+s*.55*lift},
          forearmR:{z:s*.45*lift},handR:{z:s*.7*lift,y:s*.3*lift},
          body:{y:0},neck:{y:0},head:{y:0,x:-.08*lift}};}},
 backflip:{ms:1600,label:'BACKFLIP',
  // Crouch, launch, tuck through a full rotation, land, absorb. The rotation is
  // root motion on the element; the tuck is the joints.
  root:k=>{
   const launch=Math.min(1,Math.max(0,(k-.12)/.10));
   const air=Math.min(1,Math.max(0,(k-.12)/.76));
   return {rot:-360*ease(air), y:-Math.sin(Math.PI*air)*150*launch,
           x:-Math.sin(Math.PI*air)*26,
           scale:1-.12*Math.max(0,Math.sin(Math.PI*Math.min(1,k/.12)))
                   -.10*Math.max(0,Math.sin(Math.PI*Math.max(0,(k-.9)/.1)))};},
  pose:k=>{
   const crouch=Math.max(0,Math.sin(Math.PI*Math.min(1,k/.12)));
   const tuck=Math.max(0,Math.sin(Math.PI*Math.min(1,Math.max(0,(k-.12)/.76))));
   const land=Math.max(0,Math.sin(Math.PI*Math.max(0,(k-.88)/.12)));
   const bend=crouch*.9+tuck*1.5+land*.8;
   return {legL:{x:-bend},legR:{x:-bend},shinL:{x:bend*1.3},shinR:{x:bend*1.3},
           footL:{x:-bend*.5},footR:{x:-bend*.5},
           armR:{z:-1.5*tuck-.6*crouch},elbowR:{z:-1.1*tuck},
           armL:{z:1.5*tuck+.6*crouch},elbowL:{z:1.1*tuck},
           handL:{z:1.3*tuck},body:{x:.45*tuck+.3*crouch},head:{x:.5*tuck}};}},
 thumbsup:{ms:1500,label:'THUMBS UP',pose:k=>{
  const up=Math.min(1,k*5)*Math.min(1,(1-k)*5);
  return {armR:{z:-1.15*up,x:.5*up},elbowR:{z:-1.5*up},forearmR:{z:-.5*up},
          handR:{x:-.5*up},head:{y:.16*up,x:-.12*up}};}},
 thumbsdown:{ms:1500,label:'THUMBS DOWN',pose:k=>{
  const d=Math.min(1,k*5)*Math.min(1,(1-k)*5);
  return {armR:{z:-.55*d,x:-.35*d},elbowR:{z:-.5*d},handR:{x:.9*d},
          head:{x:.2*d},body:{x:.12*d}};}},
 peace:{ms:1500,label:'PEACE',pose:k=>{
  const up=Math.min(1,k*5)*Math.min(1,(1-k)*5);
  return {armR:{z:-1.7*up,x:.3*up},elbowR:{z:-1.1*up},handR:{z:.25*up},
          head:{y:.2*up}};}},
 point:{ms:1400,label:'POINTING',pose:k=>{
  const p=Math.min(1,k*6)*Math.min(1,(1-k)*6);
  return {armR:{z:-.9*p,x:.35*p},elbowR:{z:-.45*p},forearmR:{z:-.25*p},
          head:{y:.3*p}};}},
 fist:{ms:1300,label:'FIST',pose:k=>{
  const f=Math.min(1,k*6)*Math.min(1,(1-k)*6);
  return {armR:{z:-1.25*f,x:.15*f},elbowR:{z:-1.3*f},body:{y:.14*f},
          head:{x:-.1*f}};}},
 nod:{ms:1200,label:'NOD',pose:k=>({head:{x:Math.sin(k*Math.PI*4)*.4},
          neck:{x:Math.sin(k*Math.PI*4)*.16}})},
 shake:{ms:1200,label:'NO',pose:k=>({head:{y:Math.sin(k*Math.PI*5)*.5},
          neck:{y:Math.sin(k*Math.PI*5)*.18}})},
 bow:{ms:1600,label:'BOW',pose:k=>{
  const b=Math.sin(Math.PI*k);
  return {body:{x:.7*b},head:{x:.5*b},armR:{z:-.5*b},legL:{x:-.25*b},legR:{x:-.25*b}};},
  root:k=>({y:18*Math.sin(Math.PI*k)})},
 jump:{ms:1100,label:'JUMP',
  root:k=>({y:-Math.sin(Math.PI*k)*110,scale:1-.1*Math.max(0,Math.sin(Math.PI*Math.min(1,k/.15)))}),
  pose:k=>{const t=Math.sin(Math.PI*k);
   return {legL:{x:-1.1*t},legR:{x:-1.1*t},shinL:{x:1.2*t},shinR:{x:1.2*t},
           armR:{z:-1.6*t},armL:{z:1.6*t},handL:{z:1.4*t}};}},
 spin:{ms:1400,label:'SPIN',root:k=>({rot:360*ease(k)}),
  pose:k=>({armR:{z:-1.2*Math.sin(Math.PI*k)},armL:{z:1.2*Math.sin(Math.PI*k)},
            handL:{z:1.2*Math.sin(Math.PI*k)}})},
 dance:{ms:3000,label:'DANCING',pose:k=>{
  const s=Math.sin(k*Math.PI*8),c=Math.cos(k*Math.PI*8);
  return {body:{y:s*.3,z:c*.12},head:{y:-s*.25,x:c*.1},
          armR:{z:-1.1+s*.7,x:c*.4},elbowR:{z:-.7+c*.6},
          armL:{z:1.1-s*.7,x:-c*.4},elbowL:{z:.7-c*.6},handL:{z:1.0-s*.6},
          legL:{x:s*.35},legR:{x:-s*.35}};},
  root:k=>({x:Math.sin(k*Math.PI*4)*14,y:-Math.abs(Math.sin(k*Math.PI*8))*10})},
 salute:{ms:1500,label:'SALUTE',pose:k=>{
  const u=Math.min(1,k*6)*Math.min(1,(1-k)*6);
  return {armR:{z:-1.5*u,x:.7*u},elbowR:{z:-1.9*u},forearmR:{z:-.7*u},
          head:{x:-.12*u},body:{x:-.08*u}};}},
};
const BUDDY_CLIP_NAMES=Object.keys(BUDDY_CLIPS);

// Apply rotation offsets to whatever joints exist. `pointing` keeps the old
// look-at behaviour and is layered under any clip that is playing.
function buddyPose(pointing,offsets){
 const rig=buddy.pose;if(!rig)return;
 for(const [key,o] of Object.entries(rig)){
  if(!o||!o.__i3Base)continue;const b=o.__i3Base;
  let dx=0,dy=0,dz=0;
  if(key==='head'){dy+=(pointing?.side||0)*.32;dx+=(pointing?.up||0)*.16;}
  else if(key==='armR'){dz+=(pointing?-.72:0);dx+=(pointing?.up||0)*.28;}
  else if(key==='elbowR'||key==='forearmR'){dz+=(pointing?-.42:0);}
  const d=offsets&&offsets[key];
  if(d){dx+=d.x||0;dy+=d.y||0;dz+=d.z||0;}
  o.rotation.x=b.x+dx;o.rotation.y=b.y+dy;o.rotation.z=b.z+dz;
 }
}
// Where the character belongs when nothing is happening. It is resident only where
// NVTRA itself is: inside the NVTRA panel, or while the voice bot is awake or
// speaking. Everywhere else on the instrument it waits off the edge of the screen,
// and only a real measured alert summons it in. Returns a rect to dock beside, the
// string 'voice', or null for "stay off screen".
function buddyAnchor(){
 if(agent&&(agent.speaking||agent.awake||agent.busy))return 'voice';
 const panel=document.querySelector('.nvtra-chat-workspace');
 if(panel&&panel.isConnected){const r=panel.getBoundingClientRect();
  if(r.width>0&&r.bottom>80&&r.top<innerHeight-60)return r;}
 return null;}
function buddyHome(immediate=false){const el=buddy.el,w=el?.offsetWidth||220,h=el?.offsetHeight||380;
 buddy.mode='home';buddy.until=0;buddy.pointing=null;buddyPose(null,null);
 const anchor=buddyAnchor();
 // The character lives on the RIGHT of the screen and nowhere else. It was free
 // to dock on whichever side had room, which put it on the left whenever the
 // NVTRA panel sat left of centre.
 if(anchor==='voice'){buddy.tx=Math.max(8,innerWidth-w-20);buddy.ty=Math.max(8,innerHeight-h-92);buddy.parked=false;}
 else if(anchor){buddy.tx=innerWidth-w-14;
  buddy.ty=clamp(anchor.top+anchor.height*.08,48,innerHeight-h-16);buddy.parked=false;}
 else{// Parked: always off the RIGHT edge, so it can only ever enter from there.
  buddy.tx=innerWidth+24;
  buddy.ty=clamp(buddy.y,48,innerHeight-h-16);buddy.parked=true;}
 if(immediate){buddy.x=buddy.tx;buddy.y=buddy.ty;}
 el?.classList.remove('i3-buddy-alert','i3-buddy-guide');
 el?.classList.add('i3-buddy-home');
 el?.classList.toggle('on',!buddy.parked);}
// Summon the character to one element and point at it. If it is parked off screen
// it enters from the edge nearest that element, so the motion reads as "something
// arrived to show you this" rather than a widget fading in on the spot.
function buddyReact(message,target,kind='alert'){
 if(!buddy.el){buddyMount();setTimeout(()=>buddyReact(message,target,kind),900);return;}
 const rect=typeof target==='string'?document.querySelector(target)?.getBoundingClientRect():target?.getBoundingClientRect?.();
 const w=buddy.el.offsetWidth||220,h=buddy.el.offsetHeight||380;
 let tx=innerWidth-w-14,ty=clamp((rect?.top??innerHeight*.42)-h*.18,48,innerHeight-h-12);
 // It stays on the right half of the screen whatever it is pointing at, and
 // points leftward toward the target instead of walking round to its far side.
 if(rect)tx=innerWidth-w-14;
 if(buddy.parked){// Always enters from the right edge.
  buddy.x=innerWidth+24;buddy.y=ty;buddy.vx=buddy.vy=0;buddy.parked=false;}
 // Bring the thing it is pointing at into view, or it points off the fold.
 if(rect&&(rect.bottom<0||rect.top>innerHeight))try{
  (typeof target==='string'?document.querySelector(target):target)?.scrollIntoView({block:'center',behavior:'smooth'});}catch(e){}
 buddy.tx=tx;buddy.ty=ty;buddy.mode=kind;
 buddy.until=performance.now()+(kind==='alert'?7200:4200);
 text(buddy.el.querySelector('#i3-buddy-label'),message);
 buddy.el.classList.remove('i3-buddy-home','i3-buddy-alert','i3-buddy-guide');
 buddy.el.classList.add('on',kind==='alert'?'i3-buddy-alert':'i3-buddy-guide');
 const side=rect?(rect.left+rect.width/2<tx?-1:1):1,
       up=rect?clamp((rect.top+rect.height/2-ty)/innerHeight,-1,1):0;
 buddy.pointing={side,up};buddyPose(buddy.pointing,null);}
// ── engaging ──────────────────────────────────────────────────────────────────
// Gesture mirroring is deliberately not always-on. Thumbs up already scrolls the
// page, an open palm already interrupts NVTRA, and a pointing finger already
// stops it speaking - if the character copied every gesture all the time, every
// one of those controls would fire a stray animation. So you engage him first by
// clicking him, and while he is engaged those gestures go to him instead of to
// the page. Clicking again, or 25 s of nothing, releases him.
const BUDDY_ENGAGE_TIMEOUT=25000;
function buddyEngage(on){
 if(!buddy.el)return;
 buddy.engaged=!!on;buddy.engagedAt=performance.now();
 buddy.el.classList.toggle('i3-buddy-engaged',buddy.engaged);
 if(buddy.engaged){
  buddy.el.classList.add('on');buddy.parked=false;
  buddy.until=Math.max(buddy.until,performance.now()+BUDDY_ENGAGE_TIMEOUT);
  text(buddy.el.querySelector('#i3-buddy-label'),'WATCHING YOU · SHOW ME A GESTURE');
  try{fmToast('NVTRA IS WATCHING YOUR HANDS');}catch(e){}
  buddyPerform('nod');
 }else{
  text(buddy.el.querySelector('#i3-buddy-label'),'');
  buddy.lastMirror='';buddy.mirrorSince=0;
 }}
// Map a detected gesture to the clip he answers with.
const BUDDY_MIRROR={thumbsup:'thumbsup',thumbsdown:'thumbsdown',peace:'peace',
 point:'point',fist:'fist',open:'wave',wave:'wave'};
function buddyMirror(gesture,now){
 if(!buddy.engaged||!gesture)return false;
 buddy.until=Math.max(buddy.until,now+BUDDY_ENGAGE_TIMEOUT);
 // One answer per gesture: hold a thumbs up and he waves once, not forty times.
 if(buddy.lastMirror===gesture&&now-buddy.mirrorSince<2600)return true;
 buddy.lastMirror=gesture;buddy.mirrorSince=now;
 const clip=BUDDY_MIRROR[gesture];
 if(clip)buddyPerform(clip,{replace:true});
 return true;}

// ── performing ────────────────────────────────────────────────────────────────
// buddyPerform takes one clip name or a list and queues them, so "backflip and
// wave after" is one call and the moves run in the order they were asked for.
// Performing pulls the character on screen and holds it there until the queue
// drains, otherwise it would park itself off screen mid-somersault.
function buddyPerform(names,opts){
 const list=(Array.isArray(names)?names:[names])
   .map(n=>String(n||'').toLowerCase().replace(/[^a-z]/g,''))
   .filter(n=>BUDDY_CLIPS[n]);
 if(!list.length)return false;
 if(!buddy.el){buddyMount();setTimeout(()=>buddyPerform(names,opts),900);return true;}
 const replace=!!(opts&&opts.replace);
 buddy.queue=(replace?[]:buddy.queue).concat(list);
 if(replace||!buddy.clip){buddy.clip=null;buddyNextClip(performance.now());}
 return true;}
function buddyNextClip(now){
 const name=buddy.queue.shift();
 if(!name){buddy.clip=null;buddy.clipRoot=null;buddyPose(buddy.pointing,null);
  // Hold a moment after the last move so it does not vanish on the final frame.
  buddy.until=Math.max(buddy.until,now+1400);return;}
 buddy.clip=BUDDY_CLIPS[name];buddy.clipName=name;buddy.clipAt=now;
 buddy.mode='perform';buddy.until=0;
 buddy.el?.classList.remove('i3-buddy-home');
 buddy.el?.classList.add('on','i3-buddy-guide');
 buddy.parked=false;
 // Come on screen to perform, on the right, clear of the bottom chrome.
 const w=buddy.el?.offsetWidth||220,h=buddy.el?.offsetHeight||380;
 buddy.tx=Math.max(8,innerWidth-w-24);
 buddy.ty=clamp(innerHeight*.28,48,innerHeight-h-24);
 if(buddy.x>innerWidth-4){buddy.x=innerWidth+24;buddy.vx=buddy.vy=0;}
 text(buddy.el?.querySelector('#i3-buddy-label'),buddy.clip.label||name.toUpperCase());}
function buddyFrame(now){buddy.raf=requestAnimationFrame(buddyFrame);const el=buddy.el;if(!el||document.hidden)return;if(embeddedNvtraVisible()){buddyUnmount();return;}
 // A clip in progress owns the character: no homing, no alert timeout.
 let rootOffset=null;
 if(buddy.clip){
  const k=(now-buddy.clipAt)/buddy.clip.ms;
  if(k>=1){buddyNextClip(now);}
  else{
   const t=Math.max(0,Math.min(1,k));
   buddyPose(null,buddy.clip.pose?buddy.clip.pose(t):null);
   rootOffset=buddy.clip.root?buddy.clip.root(t):null;
  }
 }
 else if(buddy.until&&now>buddy.until)buddyHome();
 else if(buddy.mode==='home'&&now-buddy.homeAt>400){buddy.homeAt=now;buddyHome();}
 const tx=buddy.tx,ty=buddy.ty;
 const k=.075,d=.76;buddy.vx=(buddy.vx+(tx-buddy.x)*k)*d;buddy.vy=(buddy.vy+(ty-buddy.y)*k)*d;buddy.x+=buddy.vx;buddy.y+=buddy.vy;
 const tilt=clamp(buddy.vx*.9,-14,14);
 const rx=rootOffset?.x||0,ry=rootOffset?.y||0,rot=rootOffset?.rot||0,sc=rootOffset?.scale;
 el.style.transform='translate3d('+(buddy.x+rx).toFixed(1)+'px,'+(buddy.y+ry).toFixed(1)+'px,0) rotate('
   +(tilt+rot).toFixed(1)+'deg)'+(sc?' scale('+sc.toFixed(3)+')':'');
 el.classList.toggle('talking',!!agent.speaking);el.classList.toggle('listening',!!agent.awake||!!agent.busy);}
const BUDDY_TARGETS={ch1:'.pill-c1',ch2:'.pill-c2',ch3:'.pill-rf',current:'.pill-mtdi'};
function buddyReadEvents(packet){
 const rows=(packet.events||[]).filter(e=>e&&(e.severity==='alert'||e.severity==='critical'));
 const event=rows.at(-1);if(!event)return;
 const stamp=String(event.timestamp||'')+'|'+clean(event.message||event.state||'');
 // The first packet after a page load is history, not news.
 if(buddy.lastEvent===null){buddy.lastEvent=stamp;return;}
 if(stamp===buddy.lastEvent)return;buddy.lastEvent=stamp;
 if(Date.now()/1000-Number(event.timestamp||0)>20)return;
 const channel=clean(event.channel||event.source||'field');
 const description=clean(event.message||event.state||'event');
 buddyReact(channel.toUpperCase()+' · '+description,BUDDY_TARGETS[channel]||'.pill-mtdi','alert');}
/* The character used to fly to the heading of every page you opened, so it followed the
   operator around the instrument and announced what they had just clicked - which they
   could already read. It now stays in its corner for navigation and moves only when a
   real measured event calls for it (buddyReadEvents), which is the one case where its
   pointing carries information the operator does not already have. */
window.__i3Buddy=buddy;window.__i3BuddyMount=buddyMount;window.__i3BuddyReact=buddyReact;
window.__i3BuddyPerform=buddyPerform;window.__i3BuddyClips=BUDDY_CLIP_NAMES;
window.__i3BuddyEngage=buddyEngage;window.__i3BuddyMirror=buddyMirror;window.__i3Gesture=fmGesture;
function setCursorMode(mode){try{localStorage.setItem('i3-cursor-mode',mode);}catch(e){}applyCursorMode();}
function applyCursorMode(){const iv=cursorMode()==='iv';document.documentElement.classList.toggle('i3-cursor',iv);const el=fmCursor();if(iv){fmPlace(cursorPos.x,cursorPos.y,cursorPos.by);el.classList.add('visible');}else{el.classList.remove('visible');}
 const label='CURSOR: '+(iv?'IV':'MAC');document.querySelectorAll('[data-i3-action="cursor_mode"]').forEach(b=>{if(b.textContent!==label)b.textContent=label;});}
function fmPlace(x,y,by){const m=4;x=clamp(x,m,innerWidth-m);y=clamp(y,m,innerHeight-m);cursorPos.x=x;cursorPos.y=y;if(by)cursorPos.by=by;const el=fmCursor();el.style.transform='translate('+x.toFixed(1)+'px,'+y.toFixed(1)+'px)';el.classList.add('visible');}
addEventListener('resize',()=>fmPlace(cursorPos.x,cursorPos.y),{passive:true});
function fmToggle(force){fingerMouse.on=force===undefined?!fingerMouse.on:force;i3Log('gesture','Finger cursor '+(fingerMouse.on?'on':'off'));const el=fmCursor();el.classList.toggle('on',fingerMouse.on);fmToast(fingerMouse.on?'CURSOR ON':'CURSOR OFF · snap to turn it back on');text(document.getElementById('i3-control-result'),fingerMouse.on?'Finger cursor on. Pinch to click, pinch a 3D module to hold it.':'Finger cursor off');}
function fmToast(msg){let t=document.getElementById('i3-fm-toast');if(!t){t=document.createElement('div');t.id='i3-fm-toast';document.body.appendChild(t);}t.textContent=msg;t.classList.add('on');clearTimeout(fmToast.timer);fmToast.timer=setTimeout(()=>t.classList.remove('on'),1800);}
function fmBanner(on){let b=document.getElementById('i3-rotate-banner');if(!b){b=document.createElement('div');b.id='i3-rotate-banner';b.innerHTML='<b>HOLDING</b><span>move, swipe, spread two hands to zoom · two fingers up to rotate · pinch to exit</span>';document.body.appendChild(b);}b.classList.toggle('on',on);}
function fmHold(canvas){const prev=fingerMouse.holdCanvas;fingerMouse.hold=!!canvas;fingerMouse.holdCanvas=canvas||null;fingerMouse.holdAt=performance.now();if(prev)prev.classList.remove('i3-rotating');if(canvas){canvas.classList.add('i3-rotating');window.__i3HandControls=canvas.__i3LegacyHandControls;fmCursor().classList.remove('visible');fingerMouse.tilt=null;fingerMouse.palm=null;fingerMouse.ch3=null;fingerMouse.peaceNow=false;fmBanner(true);camHud('holding the object');}else{fmBanner(false);fingerMouse.peaceNow=false;fingerMouse.tilt=null;fingerMouse.palm=null;if(window.__i3Physics)window.__i3Physics.sample({position:[0,0,0],timestamp:performance.now()/1000,confidence:0});camHud('released');}}
const dist=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
/* Index finger pointed, the other three curled: the stop sign for NVTRA. It only acts while
   NVTRA is speaking or thinking, so an ordinary pointing cursor hand never triggers it. */
function fmPoint(h){const w=h[0];const ext=(tip,pip)=>dist(h[tip],w)>dist(h[pip],w)*HP.ext;const curled=(tip,pip)=>dist(h[tip],w)<dist(h[pip],w)*(HP.curl-.05);return ext(8,6)&&curled(12,10)&&curled(16,14)&&curled(20,18);}
function fmPeace(h){const w=h[0];const ext=(tip,pip)=>dist(h[tip],w)>dist(h[pip],w)*(HP.ext-.07);const curled=(tip,pip)=>dist(h[tip],w)<dist(h[pip],w)*HP.curl;return ext(8,6)&&ext(12,10)&&curled(16,14)&&curled(20,18);}
/* Rotation follows the tilt of the peace sign directly (no momentum): the fingertips'
   offset from the wrist, scaled by the palm width, is the tilt; its change per frame
   turns the object. Tilting down then up spins one way, the reverse the other. */
function fmTilt(h){const pw=Math.max(.02,dist(h[5],h[17]));return [((h[8].x+h[12].x)/2-h[0].x)/pw,((h[8].y+h[12].y)/2-h[0].y)/pw];}
function fmRotate(h,now){const controls=fingerMouse.holdCanvas&&fingerMouse.holdCanvas.__i3LegacyHandControls;if(!controls||!controls.physics)return;
 if(!fingerMouse.ch3||now-fingerMouse.tiltT>300){fingerMouse.ch3=new OneEuro(.8,.02,1);fingerMouse.palm=null;}
 const raw=(h[0].x+h[5].x+h[9].x+h[13].x+h[17].x)/5;
 if(fingerMouse.palm!==null&&Math.abs(raw-fingerMouse.rawPalm)>.12){fingerMouse.rawPalm=raw;return;}
 fingerMouse.rawPalm=raw;const x=fingerMouse.ch3.filter(raw,now/1000);
 if(fingerMouse.palm!==null){const dx=(x-fingerMouse.palm)*2.6;if(Math.abs(dx)>.0008)controls.physics([0,-dx,0]);}
 fingerMouse.palm=x;fingerMouse.tiltT=now;}
/* Thumb out, four fingers curled. The thumb tip well above the knuckles is thumbs up,
   well below is thumbs down; anything in between is neither. */
function fmThumb(h){const w=h[0];const size=Math.max(.02,dist(h[0],h[9]));const curled=(tip,pip)=>dist(h[tip],w)<dist(h[pip],w)*(HP.curl+.15);if(!(curled(8,6)&&curled(12,10)&&curled(16,14)&&curled(20,18)))return 0;const len=dist(h[4],h[2]);if(len<size*.45)return 0;/* thumb direction from its base to its tip: clearly up or clearly down */const dy=(h[4].y-h[2].y)/len;return dy<-HP.thumbDy?1:dy>HP.thumbDy?-1:0;}
/* Only the pinky extended: right hand rewinds (history back), left hand goes forward. */
function fmPinky(h){const w=h[0];const ext=(tip,pip)=>dist(h[tip],w)>dist(h[pip],w)*HP.ext;const curled=(tip,pip)=>dist(h[tip],w)<dist(h[pip],w)*HP.curl;return ext(20,18)&&curled(8,6)&&curled(12,10)&&curled(16,14);}
function fmNav(hands,now){const want=(hands.right&&fmPinky(hands.right))||(hands.left&&fmPinky(hands.left))?'back':'';if(!want){fingerMouse.navSince=0;fingerMouse.navWant='';return;}if(fingerMouse.navWant!==want){fingerMouse.navWant=want;fingerMouse.navSince=now;return;}if(now-fingerMouse.navSince>280&&now-(fingerMouse.navAt||0)>1500){fingerMouse.navAt=now;fmToast('◀ REWIND');history.back();}}
/* Pause: both hands open and facing the camera for 0.4 s freezes hand control so the
   computer can be used normally; both hands closed at the same time resumes. A single
   clap (two hands snapping together, then apart) wakes NVTRA to listen. */
function fmOpen(h){const w=h[0];return [8,12,16,20].every((tip,k)=>dist(h[tip],w)>dist(h[[6,10,14,18][k]],w)*(HP.ext-.05));}
/* Fully open hand: every finger extended AND straight (tip, pip and mcp nearly collinear), fingers
   spread apart, thumb out. Used for the pause gesture so a relaxed or half-open hand never triggers it. */
function fmFullyOpen(h){const w=h[0];const size=Math.max(.02,dist(h[0],h[9]));const straight=(mcp,pip,tip)=>{const a=[h[pip].x-h[mcp].x,h[pip].y-h[mcp].y],b=[h[tip].x-h[pip].x,h[tip].y-h[pip].y];const la=Math.hypot(a[0],a[1]),lb=Math.hypot(b[0],b[1]);if(!la||!lb)return false;return (a[0]*b[0]+a[1]*b[1])/(la*lb)>HP.straight;};
 const fingers=[[5,6,8],[9,10,12],[13,14,16],[17,18,20]];if(!fingers.every(([m,p,t])=>dist(h[t],w)>dist(h[p],w)*HP.curl&&straight(m,p,t)))return false;
 const spread=dist(h[8],h[12])>size*HP.spread&&dist(h[12],h[16])>size*HP.spread*.8&&dist(h[16],h[20])>size*HP.spread*.8;const thumbOut=dist(h[4],h[9])>size*HP.thumbOut;return spread&&thumbOut;}
/* A wave is an open hand swinging sideways, which no single frame can show: it is
   a motion, not a pose. Track the palm's horizontal position and count reversals -
   two direction changes inside a second, each with real travel, is a wave. Travel
   is required because a hand held still jitters across the midpoint and would
   otherwise read as an infinitely fast wave. */
const waveTrack={x:0,dir:0,turns:0,t:0,last:0,x0:0};
function fmWave(h,now){
 if(!h||!fmFullyOpen(h))
  {if(now-waveTrack.t>500){waveTrack.turns=0;waveTrack.dir=0;}return false;}
 const x=(h[0].x+h[9].x)/2,size=Math.max(.02,dist(h[0],h[9]));
 if(now-waveTrack.t>500){waveTrack.x=x;waveTrack.x0=x;waveTrack.dir=0;waveTrack.turns=0;}
 waveTrack.t=now;
 const dx=x-waveTrack.x;
 const dir=dx>size*.06?1:dx<-size*.06?-1:0;
 if(dir){
  if(waveTrack.dir&&dir!==waveTrack.dir&&Math.abs(x-waveTrack.x0)>size*.30){
   waveTrack.turns++;waveTrack.x0=x;
  }
  if(!waveTrack.dir)waveTrack.x0=x;
  waveTrack.dir=dir;
 }
 waveTrack.x=x;
 if(waveTrack.turns>=2&&now-waveTrack.last>1800){
  waveTrack.last=now;waveTrack.turns=0;return true;
 }
 return false;}
/* What is this hand doing, as one word, for the character to copy. Wave is tested
   first because a wave IS an open palm and would otherwise always read as 'open'. */
function fmGesture(hands,now){
 for(const h of [hands.right,hands.left]){if(h&&fmWave(h,now))return 'wave';}
 for(const h of [hands.right,hands.left]){
  if(!h)continue;
  const t=fmThumb(h);
  if(t>0)return 'thumbsup';
  if(t<0)return 'thumbsdown';
  if(fmPeace(h))return 'peace';
  if(fmPointing(h))return 'point';
  if(fmFist(h))return 'fist';
 }
 return '';}
function fmFist(h){const w=h[0];return [8,12,16,20].every((tip,k)=>dist(h[tip],w)<dist(h[[6,10,14,18][k]],w)*HP.curl);}
function fmPauseBanner(on){let b=document.getElementById('i3-pause-banner');if(!b){b=document.createElement('div');b.id='i3-pause-banner';b.innerHTML='<b>HAND CONTROL PAUSED</b><span>cover the camera with an open hand again, or close both hands, to resume</span>';document.body.appendChild(b);}b.classList.toggle('on',on);}
function fmSetPaused(on){if(fingerMouse.paused===on)return;fingerMouse.paused=on;fmPauseBanner(on);if(on){if(fingerMouse.hold)fmHold(null);fmCursor().classList.remove('visible');fmToast('HAND CONTROL PAUSED');}else fmToast('HAND CONTROL RESUMED');}
/* Pause / resume vote over the last ~450 ms of frames instead of demanding an unbroken run:
   one frame where a finger reads as bent no longer restarts the timer, which is why the
   gesture used to need a second try. Any two detected hands count, whatever role they hold. */
function fmTwoHands(hands,sets,now){const A=hands.left||sets[0],B=hands.right||sets.find(x=>x!==A);if(!A||!B||A===B){fingerMouse.bothVotes=[];fingerMouse.clapNear=0;return;}
 const kind=fmFullyOpen(A)&&fmFullyOpen(B)?'open':fmFist(A)&&fmFist(B)?'fist':'';
 const votes=fingerMouse.bothVotes=(fingerMouse.bothVotes||[]).filter(v=>now-v[0]<450);votes.push([now,kind]);
 const share=k=>votes.filter(v=>v[1]===k).length/votes.length;const span=now-votes[0][0];
 if(fingerMouse.paused&&span>180&&votes.length>=3&&share('fist')>=.6){fmSetPaused(false);fingerMouse.bothVotes=[];}
 /* clap: the two palms come within one hand width of each other quickly, then part again */
 const c=h=>[(h[0].x+h[9].x)/2,(h[0].y+h[9].y)/2];const a=c(hands.left),b=c(hands.right);const size=Math.max(dist(hands.left[0],hands.left[9]),dist(hands.right[0],hands.right[9]));const d=Math.hypot(a[0]-b[0],a[1]-b[1]);
 if(d<size*1.1){if(!fingerMouse.clapNear)fingerMouse.clapNear=now;}else if(fingerMouse.clapNear){if(now-fingerMouse.clapNear<400&&now-(fingerMouse.clapAt||0)>2000&&fingerMouse.clapFar&&now-fingerMouse.clapFar<900){fingerMouse.clapAt=now;fmToast('👏 NVTRA, LISTENING');if(!agent.listening)agentStart();agent.awake=true;agent.awakeAt=now;orbShow('Go ahead','');}fingerMouse.clapNear=0;}
 if(d>size*2.2)fingerMouse.clapFar=now;}
/* Hand driven sliders. Dash's rc-slider follows real mouse events, so the pinch is turned into
   mousedown / mousemove / mouseup on the rail; native range inputs get their value set directly. */
function fmSliderAt(target){const dash=target.closest('.dash-slider-container');if(dash)return {kind:'dash',el:dash};const rc=target.closest('.rc-slider');if(rc)return {kind:'rc',el:rc};const range=target.closest('input[type=range]');if(range)return {kind:'range',el:range};return null;}
function fmMouse(el,type,x,y){el.dispatchEvent(new MouseEvent(type,{bubbles:true,cancelable:true,clientX:x,clientY:y,button:0,buttons:type==='mouseup'?0:1}));}
function fmSliderStart(s,x,y){if(s.kind==='dash'){fmSliderMove(s,x,y);}else if(s.kind==='rc'){const rail=s.el.querySelector('.rc-slider-rail')||s.el;const r=rail.getBoundingClientRect();fmMouse(rail,'mousedown',x,r.top+r.height/2);}else fmSliderMove(s,x,y);fmToast('SLIDER · move left or right');}
function fmSliderMove(s,x,y){if(s.kind==='dash'){/* Dash 4 slider: its number input is the reliable way in; the thumb reports the scale */const root=s.el.querySelector('.dash-slider-root'),thumb=s.el.querySelector('[role=slider]'),inp=s.el.querySelector('input');if(!root||!thumb||!inp)return;const r=root.getBoundingClientRect();const t=clamp((x-r.left)/Math.max(1,r.width),0,1);const min=Number(thumb.getAttribute('aria-valuemin')),max=Number(thumb.getAttribute('aria-valuemax')),step=Number(inp.step||1)||1;const v=Math.round((min+t*(max-min))/step)*step;const val=String(Number(v.toFixed(6)));if(inp.value!==val){const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;setter.call(inp,val);inp.dispatchEvent(new Event('input',{bubbles:true}));inp.dispatchEvent(new Event('change',{bubbles:true}));}return;}if(s.kind==='rc'){fmMouse(document,'mousemove',x,y);}else{const r=s.el.getBoundingClientRect();const t=clamp((x-r.left)/Math.max(1,r.width),0,1);const min=Number(s.el.min||0),max=Number(s.el.max||100),step=Number(s.el.step||1)||1;const v=Math.round((min+t*(max-min))/step)*step;if(String(v)!==s.el.value){s.el.value=v;s.el.dispatchEvent(new Event('input',{bubbles:true}));}}}
function fmSliderEnd(s,x,y){if(s.kind==='dash'){const inp=s.el.querySelector('input');if(inp){inp.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));inp.dispatchEvent(new Event('blur',{bubbles:true}));}return;}if(s.kind==='rc'){fmMouse(document,'mouseup',x,y);}else s.el.dispatchEvent(new Event('change',{bubbles:true}));}
function fmPointing(h){const w=h[0];const ext=(tip,pip)=>dist(h[tip],w)>dist(h[pip],w)*(HP.ext-.03);const curled=(tip,pip)=>dist(h[tip],w)<dist(h[pip],w)*1.12;return ext(8,6)&&curled(12,10)&&curled(16,14)&&curled(20,18);}
function camHud(message){const preview=document.querySelector('.i3-hand-vision-preview');if(!preview)return;let hud=preview.querySelector('.i3-cam-hud');if(!hud){hud=document.createElement('div');hud.className='i3-cam-hud';preview.appendChild(hud);}text(hud,message);}
/* Hand roles. With two hands on screen the role is purely positional: the hand shown on
   the right of the (mirrored) preview is the right hand (cursor, pinch, hold), the one on
   the left is the left hand (open palm scrolling). A lone hand uses MediaPipe's label,
   whose "Left" is the operator's right hand because the raw feed is not mirrored. */
/* Smart scrolling: the deliberate swipe is the fast one. Each stroke's peak speed is kept;
   a stroke in the opposite direction that follows within 900 ms only scrolls once it is
   faster than 85% of that peak, so the hand's slower return (or a small wind-up before
   the swipe) is ignored while a genuinely fast swipe the other way still works. */
const SS={dir:0,peak:0,prevDir:0,prevPeak:0,endT:0};
const palmVel=new OneEuro(2.2,.1,1);
function smartScroll(vyRaw,dt,now){const vy=vyRaw;const speed=Math.abs(vy);if(speed<HP.swipeMin){if(SS.dir){SS.prevDir=SS.dir;SS.prevPeak=SS.peak;SS.endT=now;SS.dir=0;SS.peak=0;}return;}const dir=vy>0?1:-1;
 if(SS.dir!==dir){if(SS.dir){SS.prevDir=SS.dir;SS.prevPeak=SS.peak;SS.endT=now;}SS.dir=dir;SS.peak=0;}
 SS.peak=Math.max(SS.peak,speed);
 const recent=now-SS.endT<600&&SS.prevDir===-dir;
 if(recent&&SS.peak<SS.prevPeak*.5)return;
 i3ScrollBy(-vy*innerHeight*1.25*HP.swipeGain*dt*scrollGain());}
/* Hand scrolling goes through the scrub hero first when one holds the page. */
/* Scroll whatever scrolls under the IV cursor: an expanded pillar, a terminal, a card with its
   own overflow, otherwise the page. Windows scrollBy alone did nothing inside those panels. */
function scrollTargetAt(x,y){let el=document.elementFromPoint(clamp(x,1,innerWidth-1),clamp(y,1,innerHeight-1));while(el&&el!==document.body&&el!==document.documentElement){const cs=getComputedStyle(el);if(/(auto|scroll)/.test(cs.overflowY)&&el.scrollHeight>el.clientHeight+2)return el;el=el.parentElement;}return null;}
function i3ScrollBy(top){if(window.__i3ScrubConsume&&window.__i3ScrubConsume(top))return;
 /* an open MTDI pillar locks the body and scrolls itself: it is the target wherever the cursor is */
 const pillar=document.querySelector('body.mtdi-detail-open .mtdi-orbit-card.is-expanded');
 const box=pillar||scrollTargetAt(cursorPos.x,cursorPos.y)||document.querySelector('.aether-game:not([hidden]) .aether-term-out, #i3-hand-calib');
 if(box){const before=box.scrollTop;box.scrollTop+=top;if(Math.abs(box.scrollTop-before)>.5||pillar)return;}scrollBy({top,behavior:'auto'});}
/* The Page 3 pillar track turns vertical scroll into a long horizontal pan, so a
   swipe there moves the page further to cover the same visual distance. */
function scrollGain(){const outer=document.querySelector('[data-i3-rotate]');if(!outer)return 1;const r=outer.getBoundingClientRect();const inside=r.top<=0&&r.bottom>=innerHeight;return inside?1.8:1;}
/* Roles stick to the hand: once a hand has been the cursor (right) or scroll (left) hand,
   it keeps that role while it stays roughly where it was, so a wobbling handedness label
   from MediaPipe cannot switch the cursor off mid-move. Labels decide only for new hands. */
const roleMemory={right:null,left:null,t:0};
/* Left-handed mode swaps the roles: the left hand becomes the cursor/pinch/hold hand and the
   right hand scrolls. 'right'/'left' below therefore mean cursor hand / scroll hand. */
function leftHanded(){try{return localStorage.getItem('i3-left-handed')==='1';}catch(e){return false;}}
function setLeftHanded(on){try{localStorage.setItem('i3-left-handed',on?'1':'0');}catch(e){}roleMemory.right=roleMemory.left=null;syncLeftHanded();}
function syncLeftHanded(){const label='LEFT-HANDED: '+(leftHanded()?'ON':'OFF');document.querySelectorAll('[data-i3-action="left_handed"]').forEach(b=>{if(b.textContent!==label)b.textContent=label;b.setAttribute('aria-pressed',String(leftHanded()));});}
function splitHands(sets,handedness){const out={right:null,left:null};const now=performance.now();const centre=h=>[(h[0].x+h[9].x)/2,(h[0].y+h[9].y)/2];const near=(c,m)=>m&&now-roleMemory.t<2500&&Math.hypot(c[0]-m[0],c[1]-m[1])<.34;
 /* Two hands on screen: position decides, nothing else. The preview is mirrored, so the hand
    the operator sees on the right of the screen is the one with the smaller raw x: that is
    the right hand (cursor); the other is the left hand (scroll). Labels and role memory
    are ignored here because MediaPipe's handedness flips when the second hand comes in. */
 if(sets.length>=2){const ordered=sets.map(h=>({h,cx:centre(h)[0]})).sort((a,b)=>a.cx-b.cx);out.right=ordered[0].h;out.left=ordered[ordered.length-1].h;if(leftHanded()){const t=out.right;out.right=out.left;out.left=t;}roleMemory.right=centre(out.right);roleMemory.left=centre(out.left);roleMemory.t=now;return out;}
 const used=new Set();
 /* 1. continuity: hands close to where a role was last seen keep it */
 for(const role of ['right','left']){let best=null,bd=1;sets.forEach((h,i)=>{if(used.has(i))return;const c=centre(h);if(near(c,roleMemory[role])){const d=Math.hypot(c[0]-roleMemory[role][0],c[1]-roleMemory[role][1]);if(d<bd){bd=d;best=i;}}});if(best!==null){out[role]=sets[best];used.add(best);}}
 /* 2. new hands: the label when confident, an open palm on a lone hand means scroll hand, else position */
 sets.forEach((h,i)=>{if(used.has(i))return;const entry=handedness?.[i]?.label?handedness[i]:handedness?.[i]?.[0];const label=entry?.label;const score=Number(entry?.score??1);const openPalm=[8,12,16,20].every((tip,k)=>dist(h[tip],h[0])>dist(h[[6,10,14,18][k]],h[0])*1.2);let isRight;const lastRole=roleMemory.lastLone;if(sets.length===1&&lastRole&&now-roleMemory.t<4000&&score<.9&&!openPalm)isRight=lastRole==='right';else if(label&&(sets.length>1||label==='Left'||score>=.9||openPalm))isRight=label==='Left';else{const cx=(h[0].x+h[9].x)/2;isRight=sets.length===1?true:cx<=sets.reduce((m,o)=>Math.min(m,(o[0].x+o[9].x)/2),1)+1e-6;}if(isRight&&!out.right)out.right=h;else if(!isRight&&!out.left)out.left=h;else if(!out.left)out.left=h;else if(!out.right)out.right=h;});
 if(leftHanded()){const t=out.right;out.right=out.left;out.left=t;}
 roleMemory.right=out.right?centre(out.right):null;roleMemory.left=out.left?centre(out.left):null;if(sets.length===1)roleMemory.lastLone=out.right?'right':'left';roleMemory.t=now;return out;}
window.__i3SplitHands=splitHands;window.__i3HandCalibrate=handCalibrate;window.__i3DrawCalibHand=drawCalibHand;
window.__i3HandGesture=function(setsIn,overlay,handednessIn){
 const now=performance.now();
 /* MediaPipe sometimes reports the same hand twice; keep the higher-scored one when two
    detections overlap, otherwise a phantom 'left hand' scrolls the page on its own. */
 let sets=setsIn,handedness=handednessIn;
 /* Only act on hands the detector is sure about: a low score means a guessed hand. */
 if(sets.length&&handedness&&handedness.length===sets.length){const keep=sets.map((_,i)=>Number((handedness[i]?.label?handedness[i]:handedness[i]?.[0])?.score??1)>=.45);if(keep.some(k=>!k)){sets=sets.filter((_,i)=>keep[i]);handedness=handedness.filter((_,i)=>keep[i]);}}
 if(sets.length>1){const c=sets.map(h=>[(h[0].x+h[9].x)/2,(h[0].y+h[9].y)/2,Math.max(.02,dist(h[0],h[9]))]);const sc=i=>Number((handedness?.[i]?.label?handedness[i]:handedness?.[i]?.[0])?.score??.5);const keep=sets.map(()=>true);for(let i=0;i<sets.length;i++)for(let j=i+1;j<sets.length;j++){if(!keep[i]||!keep[j])continue;const d=Math.hypot(c[i][0]-c[j][0],c[i][1]-c[j][1]);if(d<Math.max(c[i][2],c[j][2])*1.6){if(sc(i)>=sc(j))keep[j]=false;else keep[i]=false;}}if(keep.some(k=>!k)){sets=sets.filter((_,i)=>keep[i]);handedness=handedness?handedness.filter((_,i)=>keep[i]):handedness;}}
 fingerMouse.frameT=fingerMouse.frameT||[];fingerMouse.frameT.push(now);while(fingerMouse.frameT.length>30)fingerMouse.frameT.shift();
 if(calib.active){calib.feed(sets,handedness);fmCursor().classList.remove('visible');return true;}
 /* Physical input wins: while the mouse, trackpad, keyboard or touch has been used in the
    last 1.5 s the hand is tracked but drives nothing (no cursor, clicks, scroll or hold). */
 if(now-physicalInput.at<1500){if(cursorMode()!=='iv')fmCursor().classList.remove('visible');if(fingerMouse.slider){fingerMouse.slider=null;}camHud('hand paused · '+physicalInput.kind+' in use');fingerMouse.pinchSince=0;fingerMouse.clicked=false;fingerMouse.lastPalmT=0;fingerMouse.thumbSince=0;fingerMouse.thumbDir=0;return true;}
 if(!sets.length){/* the cursor stays where the hand left it; only physical input (above) or the hand returning moves it */camHud('no hand in view · cursor held'); fingerMouse.thumbSince=0;fingerMouse.thumbDir=0;fingerMouse.lastPalmT=0;handDebug(sets,{},{fps:0,hands:0});return false;}
 const hands=splitHands(sets,handedness);const h=hands.right||sets[0];const size=Math.max(.02,dist(h[0],h[9]));fingerMouse.handSeen=now;
 if(fingerMouse.debug){const ft=fingerMouse.frameT;handDebug(sets,hands,{fps:ft.length>1?(ft.length-1)*1000/(ft[ft.length-1]-ft[0]):0,hands:sets.length});}
 /* Pause: one open hand held close to the camera so it covers most of the frame (its box
    spans 80 % of the width or height). Same gesture again resumes; so do two fists. */
 {const covering=sets.some(hand=>{let x0=1,x1=0,y0=1,y1=0;for(const p of hand){x0=Math.min(x0,p.x);x1=Math.max(x1,p.x);y0=Math.min(y0,p.y);y1=Math.max(y1,p.y);}return (x1-x0>=.8||y1-y0>=.8)&&fmFullyOpen(hand);});
  const votes=fingerMouse.coverVotes=(fingerMouse.coverVotes||[]).filter(v=>now-v[0]<450);votes.push([now,covering]);const span=now-votes[0][0];const share=votes.filter(v=>v[1]).length/votes.length;
  if(span>280&&votes.length>=4&&share>=.6&&now-(fingerMouse.coverAt||0)>1500){fingerMouse.coverAt=now;fingerMouse.coverVotes=[];fmSetPaused(!fingerMouse.paused);}}
 fmTwoHands(hands,sets,now);if(fingerMouse.paused){camHud('paused · cover the camera with an open hand, or close both hands, to resume');return true;}
 /* snap: thumb tip to middle tip contact, then rapid separation */
 const tm=dist(h[4],h[12])/size;
 if(tm<.25&&!fingerMouse.contactAt){fingerMouse.contactAt=now;fingerMouse.contactSize=size;fingerMouse.contactFrames=0;}
 if(fingerMouse.contactAt&&tm<.25)fingerMouse.contactFrames++;
 if(fingerMouse.contactAt&&now-fingerMouse.contactAt<300&&tm>1.05){const pinching=dist(h[8],h[4])/size<.4,steady=Math.abs(size-fingerMouse.contactSize)/fingerMouse.contactSize<.25;if(fingerMouse.contactFrames>=2&&!pinching&&steady&&now-fingerMouse.lastSnapAt>1500&&!fingerMouse.hold){fingerMouse.lastSnapAt=now;fmToggle();}fingerMouse.contactAt=0;}
 if(fingerMouse.contactAt&&now-fingerMouse.contactAt>=300)fingerMouse.contactAt=0;
 /* HUD on the preview canvas: estimated distance and mode */
 camHud((hands.right?'right ':'')+(hands.left?'left ':'')+'hand'+(sets.length>1?'s':'')+(fingerMouse.hold?' · holding':fingerMouse.thumbDir?(fingerMouse.thumbDir>0?' · scroll up':' · scroll down'):fingerMouse.on?' · cursor':''));
 /* While the character is engaged your gestures belong to him, not to the page:
    he copies them back and the page controls stay out of the way. */
 let mirrored=false;
 if(buddy.engaged){
  if(now-buddy.engagedAt>BUDDY_ENGAGE_TIMEOUT)buddyEngage(false);
  else{const g=fmGesture(hands,now);if(g){buddyMirror(g,now);buddy.engagedAt=now;}
   mirrored=!!(hands.left||hands.right);
   camHud('NVTRA is watching'+(g?' · '+g:''));}
 }
 /* thumbs up scrolls up, thumbs down scrolls down, with either hand; steady speed while held */
 if(!fingerMouse.hold&&!mirrored){let dir=0;for(const hand of [hands.left,hands.right]){if(hand){const t=fmThumb(hand);if(t){dir=t;break;}}}
  if(!dir&&fingerMouse.thumbDir&&now-(fingerMouse.thumbLastSeen||0)<140)dir=fingerMouse.thumbDir;else if(dir)fingerMouse.thumbLastSeen=now;
  if(dir){if(!fingerMouse.thumbSince||fingerMouse.thumbDir!==dir){fingerMouse.thumbSince=now;fingerMouse.thumbDir=dir;fingerMouse.thumbT=now;}else if(now-fingerMouse.thumbSince>120){const dt=Math.min(.1,(now-fingerMouse.thumbT)/1000);const ramp=Math.min(1,(now-fingerMouse.thumbSince-120)/500);i3ScrollBy(-dir*innerHeight*(.3+.6*ramp)*dt*scrollGain());}fingerMouse.thumbT=now;}
  else{fingerMouse.thumbSince=0;fingerMouse.thumbDir=0;}}
 if(!fingerMouse.hold&&!mirrored)fmNav(hands,now);
 /* an open palm (all five fingers straight, one hand) held 0.7 s while NVTRA is talking or thinking stops it. The pointing cursor hand must never do this: the operator points at the screen while asking. */
 if((agent.speaking||agent.busy)&&sets.length===1&&fmFullyOpen(sets[0])&&!fingerMouse.hold){if(!fingerMouse.pointSince)fingerMouse.pointSince=now;else if(now-fingerMouse.pointSince>700&&now-(fingerMouse.pointAt||0)>2500){fingerMouse.pointAt=now;agentInterrupt('palm');}}else fingerMouse.pointSince=0;
 /* open left palm swiping up or down scrolls the page (smart scrolling: the slower return stroke is ignored) */
 if(hands.left&&!fingerMouse.thumbDir&&!mirrored){const L=hands.left,w=L[0];const open=[8,12,16,20].filter((tip,i)=>dist(L[tip],w)>dist(L[[6,10,14,18][i]],w)*Math.min(1.2,HP.curl)).length>=3;const pyRaw=(L[0].y+L[9].y)/2;if(!fingerMouse.lastPalmT||now-fingerMouse.lastPalmT>400){fingerMouse.palmF=new OneEuro(3.2,.12,1);fingerMouse.strokeY0=pyRaw;fingerMouse.strokeArmed=false;}const py=fingerMouse.palmF.filter(pyRaw,now/1000);if(open&&fingerMouse.lastPalmT&&now-fingerMouse.lastPalmT<400){const dt=(now-fingerMouse.lastPalmT)/1000;const vy=(py-fingerMouse.lastPalmY)/Math.max(.016,dt);const travel=Math.abs(py-fingerMouse.strokeY0);const rest=HP.swipeMin*.8;if(Math.abs(vy)<rest)fingerMouse.strokeY0=py;if(travel>.012)fingerMouse.strokeArmed=true;if(!fingerMouse.hold)smartScroll(fingerMouse.strokeArmed?vy:0,dt,now);if(Math.abs(vy)<rest)fingerMouse.strokeArmed=false;}fingerMouse.lastPalmY=py;fingerMouse.lastPalmT=now;}else{fingerMouse.lastPalmT=0;smartScroll(0,0,now);}
 if(now<fingerMouse.warmUntil){camHud('camera warming up');return true;}
 if(fingerMouse.hold){if(!hands.right){fingerMouse.palm=null;fingerMouse.peaceNow=false;return false;}const pinchNow=dist(h[8],h[4])/size<HP.pinchOn+.02;if(pinchNow&&now-fingerMouse.holdAt>600){if(!fingerMouse.pinchSince)fingerMouse.pinchSince=now;if(now-fingerMouse.pinchSince>90){fmHold(null);fingerMouse.clicked=true;}return false;}if(!pinchNow)fingerMouse.pinchSince=0;
  const peace=gate('peace',fmPeace(h),90,160,now);if(peace!==fingerMouse.peaceNow){fingerMouse.peaceNow=peace;fingerMouse.palm=null;fingerMouse.ch3=null;const hint=document.querySelector('#i3-rotate-banner span');if(hint)text(hint,peace?'rotating · move left or right · pinch to exit':'move, swipe, spread two hands to zoom · two fingers up to rotate · pinch to exit');if(peace&&window.__i3Physics)window.__i3Physics.sample({position:[0,0,0],timestamp:performance.now()/1000,confidence:0});}
  if(peace)fmRotate(h,now);return false;}
 if(!fingerMouse.on)return false;
 /* A lone hand always drives the cursor, whatever label MediaPipe guessed for it; with two
    hands the cursor waits a moment before hiding so a dropped frame does not blink it out. */
 const cursorHand=hands.right||(sets.length===1?sets[0]:null);
 if(!cursorHand){/* cursor holds its place */return true;}
 fingerMouse.rightSeen=now;
 const el=fmCursor();
 const tip=cursorHand[8];const nx=clamp((1-tip.x-HP.edge)/(1-2*HP.edge),0,1),ny=clamp((tip.y-HP.edge)/(1-2*HP.edge),0,1);let x=fingerMouse.fx.filter(nx*innerWidth,now/1000),y=fingerMouse.fy.filter(ny*innerHeight,now/1000);
 /* closing the fingers drags the index tip; keep the cursor where it was ~150 ms before the pinch */
 fingerMouse.trail=fingerMouse.trail||[];fingerMouse.trail.push([now,x,y]);while(fingerMouse.trail.length>24)fingerMouse.trail.shift();
 const pr0=dist(h[8],h[4])/size;const closing=fingerMouse.pinching?pr0<HP.pinchOff:pr0<HP.pinchOn;
 const liveX=x,liveY=y;
 if(closing){if(!fingerMouse.frozen){const past=fingerMouse.trail.find(t=>now-t[0]<=160)||fingerMouse.trail[0];fingerMouse.frozen=[past[1],past[2]];}x=fingerMouse.frozen[0];y=fingerMouse.frozen[1];}else fingerMouse.frozen=null;
 /* a pinch that started on a slider drags it: the hand's live x drives the handle until release */
 if(fingerMouse.slider){if(closing){fmSliderMove(fingerMouse.slider,liveX,liveY);fmPlace(liveX,liveY,'hand');return true;}else{fmSliderEnd(fingerMouse.slider,liveX,liveY);fingerMouse.slider=null;fingerMouse.clicked=true;}}
 /* taking over from the pointer: glide from where the cursor is to where the hand points */
 if(cursorPos.by!=='hand'){fingerMouse.blend={x:cursorPos.x,y:cursorPos.y,t:now};}
 if(fingerMouse.blend){const k=Math.min(1,(now-fingerMouse.blend.t)/280);const e=1-Math.pow(1-k,3);x=fingerMouse.blend.x+(x-fingerMouse.blend.x)*e;y=fingerMouse.blend.y+(y-fingerMouse.blend.y)*e;if(k>=1)fingerMouse.blend=null;}
 fmPlace(x,y,'hand');
 if(now-(fingerMouse.hoverAt||0)>90){fingerMouse.hoverAt=now;const under=document.elementFromPoint(clamp(x,1,innerWidth-1),clamp(y,1,innerHeight-1));fingerMouse.overClickable=!!under?.closest?.('a,button,[role=button],input,select,summary,label,.tab-btn,.nav-glass-btn,.module-card,.mtdi-card,.mtdi-orbit-card,.i3-tool,.i3-mode-card,.i3-sc-btn');}
 const pr=dist(h[8],h[4])/size;const pinch=fingerMouse.pinching?pr<HP.pinchOff:pr<HP.pinchOn;fingerMouse.pinching=pinch;el.classList.toggle('hover',pinch||!!fingerMouse.overClickable);
 if(pinch){if(!fingerMouse.pinchSince)fingerMouse.pinchSince=now;if(!fingerMouse.clicked&&now-fingerMouse.pinchSince>140){fingerMouse.clicked=true;el.classList.add('click');setTimeout(()=>el.classList.remove('click'),300);const target=document.elementFromPoint(x,y);if(target){const slider=fmSliderAt(target);if(slider){fingerMouse.slider=slider;fmSliderStart(slider,x,y);return true;}const canvas=target.closest('canvas');if(fingerMouse.hand3d&&canvas&&canvas.__i3LegacyHandControls){fmHold(canvas);return true;}if(target.closest('#i3-camera-toggle'))return true;/* a pinch near the header must never switch the camera off */const clickable=target.closest('a,button,[role=button],input,select,summary,label,.tab-btn,.nav-glass-btn,.module-card,.mtdi-card,.i3-tool,#i3-orb')||target;for(const type of ['pointerdown','mousedown','pointerup','mouseup','click'])clickable.dispatchEvent(new MouseEvent(type,{bubbles:true,cancelable:true,clientX:x,clientY:y}));}}}
 else{fingerMouse.pinchSince=0;fingerMouse.clicked=false;}
 return true;
};
/* NVTRA voice agent. Continuous recognition waits for the wake word; the request that
   follows goes to /api/agent, whose reply is spoken and whose actions are applied to the
   interface. Recognition uses the browser's speech engine (Chrome sends audio to Google;
   this host kiosk Chromium has no engine, so there the orb accepts typed requests). */
const agent={listening:false,rec:null,awake:false,awakeAt:0,busy:false,orb:null,raf:0,level:0,analyser:null,phase:0,speaking:false};
const WAKE=/\b(?:hey|hi|ok|okay|yo)?[ ,]*(?:n[aeiou]{1,2}\s?[vbfw][aeiou]{0,2}\s?[tdk]+[rh]*[aeiou]*\w*|n[aeiou]+[vb][aeiou]+r+[aeiou]*\w*|n[aeiou]+v[aeiou]*\s?[tdk]r\w*|nova\s?\w*|nvtra|novatra|navatra|navarra|nevada|nova\b|navara|nabatra|nevatra|no\s?vatra|nutra\w*|nectar|natra\w*|nova k\w*)\b/i;
const showWake=t=>t.replace(WAKE,'NVTRA');
let typeTimer=0;function typeIn(el,value){if(!el)return;clearInterval(typeTimer);const chars=Array.from(value||'');let i=0;el.textContent='';typeTimer=setInterval(()=>{i+=2;el.textContent=chars.slice(0,i).join('');if(i>=chars.length)clearInterval(typeTimer);},18);}
function orbShow(state,textValue){const orb=document.getElementById('i3-orb');if(!orb)return;orb.classList.remove('collapsed','hidden');const robot=null;const slot=document.getElementById('i3-orb-robot');if(robot&&slot&&!slot.contains(robot)){agent.robotHome=robot.parentElement;agent.robotNext=robot.nextSibling;slot.appendChild(robot);slot.hidden=false;document.getElementById('i3-orb-canvas').hidden=true;}text(document.getElementById('i3-orb-state'),state||'');if(textValue!==undefined)text(document.getElementById('i3-orb-text'),textValue);document.getElementById('i3-orb-text')?.classList.remove('guess');orbAnimate();}
/* Hide once the exchange is over: never while the operator is mid-sentence (a chunk recording or
   decoding), awake, or NVTRA is busy or speaking. Re-checks until it is safe. */
function orbHideWhenIdle(){if(vc.speaking||(vc.inflight||0)>0||agent.awake||agent.busy||agent.speaking){clearTimeout(agent.hideTimer);agent.hideTimer=setTimeout(orbHideWhenIdle,300);return;}orbHide();}
function orbHide(){const orb=document.getElementById('i3-orb');if(orb){orb.classList.add('collapsed');}text(document.getElementById('i3-orb-state'),agent.listening?'Listening for Hey Novatra':'Press ◍ or N to start listening');const robot=document.getElementById('nvtra-spline-host');if(robot&&agent.robotHome&&agent.robotHome.isConnected){agent.robotHome.insertBefore(robot,agent.robotNext&&agent.robotNext.isConnected?agent.robotNext:null);agent.robotHome=null;const slot=document.getElementById('i3-orb-robot');if(slot)slot.hidden=true;document.getElementById('i3-orb-canvas').hidden=false;}cancelAnimationFrame(agent.raf);agent.raf=0;agent.awake=false;}
function orbAnimate(){if(agent.raf)return;const canvas=document.getElementById('i3-orb-canvas');const ctx=canvas.getContext('2d');const draw=()=>{if(document.getElementById('i3-orb').classList.contains('hidden')){agent.raf=0;return;}agent.phase+=.035;let level=agent.level;if(agent.analyser){const data=new Uint8Array(agent.analyser.frequencyBinCount);agent.analyser.getByteTimeDomainData(data);let sum=0;for(const v of data){const d=(v-128)/128;sum+=d*d;}level=Math.min(1,Math.sqrt(sum/data.length)*4);}if(agent.speaking)level=.35+Math.sin(agent.phase*6)*.2;const bars=document.querySelectorAll('#i3-voice-bars i');bars.forEach((bar,i)=>{const v=Math.max(.15,Math.min(1,level*3*(0.5+Math.abs(Math.sin(agent.phase*4+i*.9)))));bar.style.height=(4+v*16)+'px';});const w=canvas.width,h=canvas.height,cx=w/2,cy=h/2,base=w*.24;ctx.clearRect(0,0,w,h);const layers=[['#1d4ed8',.9,1],['#3b82f6',.7,1.4],['#22d3ee',.55,1.9],['#a5f3fc',.4,2.6]];layers.forEach(([color,alpha,speed],li)=>{ctx.beginPath();for(let a=0;a<=Math.PI*2+.01;a+=Math.PI/64){const wob=Math.sin(a*3+agent.phase*speed)*.06+Math.sin(a*5-agent.phase*speed*1.3)*.04+Math.sin(a*7+agent.phase*.7)*.03;const r=base*(1+li*.09)*(1+wob*(1+level*4)+level*.15);const x=cx+Math.cos(a)*r,y=cy+Math.sin(a)*r;a===0?ctx.moveTo(x,y):ctx.lineTo(x,y);}ctx.closePath();ctx.globalAlpha=alpha*.55;ctx.fillStyle=color;ctx.globalCompositeOperation='lighter';ctx.fill();});ctx.globalCompositeOperation='source-over';ctx.globalAlpha=1;const core=ctx.createRadialGradient(cx,cy,0,cx,cy,base*.9);core.addColorStop(0,'rgba(255,255,255,.9)');core.addColorStop(.35,'rgba(147,197,253,.55)');core.addColorStop(1,'rgba(29,78,216,0)');ctx.fillStyle=core;ctx.beginPath();ctx.arc(cx,cy,base*.9,0,Math.PI*2);ctx.fill();agent.raf=requestAnimationFrame(draw);};agent.raf=requestAnimationFrame(draw);}
function voicePlayer(){if(!agent.player){agent.player=new Audio();agent.player.preload='auto';}return agent.player;}
/* Browsers only let audio start after a user gesture: the first click, key or touch
   unlocks one shared player, which then plays every ElevenLabs reply. */
function unlockVoice(){if(agent.unlocked)return;agent.unlocked=true;const p=voicePlayer();p.src='data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4Ljc2LjEwMAAAAAAAAAAAAAAA//tQxAADB8AhSmxhIIEVCSiJrDCQBTcu3UrAIwUdkRgQbFAZC1CQEwTJ9mjRvBA4UOLD8nKVOWfh+UlK3z/177OXrfOdKl7pyn3Xf//WreyTRUoAWgBgkOAGbZHBgG1OF6zM82DWbZaUmMBptgQhGjsyYqc9ae9XPAJFdr7NbQ8N8vqcxvw5/eJoWcnYSt0pVsdC+SQcrHT1ecCDvvs/wAAAAAaAAAAAdVr/eb9gADrudHKAAAAA';p.play().catch(()=>{});}
for(const type of ['pointerdown','keydown','touchstart'])document.addEventListener(type,unlockVoice,{once:true,capture:true});
async function speak(textValue){speechDrop();agentPauseListening();let why='';try{agent.speaking=true;const response=await fetch('/api/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:textValue}),signal:AbortSignal.timeout(15000)});if(response.ok){const blob=await response.blob();const audio=voicePlayer();if(audio.src&&audio.src.startsWith('blob:'))URL.revokeObjectURL(audio.src);audio.src=URL.createObjectURL(blob);agent.audio=audio;const done=()=>{agent.speaking=false;agent.audio=null;agent.followUntil=performance.now()+8000;setTimeout(agentResumeListening,250);};audio.onended=done;audio.onerror=done;await audio.play();bargeInWatch();return;}else{why=(await response.json().catch(()=>({}))).error||('http '+response.status);}}catch(error){why=error.message||String(error);}agent.speaking=false;text(document.getElementById('i3-orb-state'),'Browser voice · '+clean(why).slice(0,60));speakBrowser(textValue);}
function bargeInWatch(){if(!agent.analyser)return;let loud=0;const check=()=>{if(!agent.speaking)return;const data=new Uint8Array(agent.analyser.frequencyBinCount);agent.analyser.getByteTimeDomainData(data);let sum=0;for(const v of data){const d=(v-128)/128;sum+=d*d;}const level=Math.sqrt(sum/data.length);loud=level>.09?loud+1:0;if(loud>=5){speechPause();return;}setTimeout(check,50);};setTimeout(check,400);}
/* Interrupting NVTRA pauses the sentence instead of killing it. 'Carry on' resumes it; any other
   utterance becomes the new request and the paused sentence is dropped. */
function speechPause(){if(!agent.speaking)return;agent.speaking=false;try{if(agent.audio){agent.audio.pause();agent.pausedAudio=agent.audio;}else if(window.speechSynthesis?.speaking){speechSynthesis.pause();agent.pausedSynth=true;}}catch(error){}agent.audio=null;agent.pausedAt=performance.now();agentResumeListening();orbShow('Paused · say carry on, or ask something else','');agent.awake=true;agent.awakeAt=performance.now();}
function speechResume(){const a=agent.pausedAudio;agent.pausedAudio=null;if(a){agent.audio=a;agent.speaking=true;agentPauseListening();orbShow('NVTRA','');a.play().catch(()=>{agent.speaking=false;agentResumeListening();});bargeInWatch();return true;}if(agent.pausedSynth){agent.pausedSynth=false;agent.speaking=true;agentPauseListening();speechSynthesis.resume();bargeInWatch();return true;}return false;}
/* Hard stop: whatever NVTRA is saying or working on ends now. The reply in flight is
   discarded when it lands. Triggered by the island's Stop button or an open palm held to the camera. */
function agentInterrupt(why){agent.stopSeq=(agent.stopSeq||0)+1;speechDrop();try{agent.audio?.pause();}catch(error){}agent.audio=null;agent.pausedAudio=null;try{speechSynthesis.cancel();}catch(error){}agent.speaking=false;agent.busy=false;agent.awake=false;agentResumeListening?.();orbShow('Stopped','');setTimeout(orbHide,900);fmToast?.('NVTRA STOPPED');}
function speechDrop(){if(agent.pausedAudio){try{agent.pausedAudio.pause();}catch(error){}agent.pausedAudio=null;}if(agent.pausedSynth){agent.pausedSynth=false;try{speechSynthesis.cancel();}catch(error){}}}
const RESUME=/^\W*(ok(ay)?[, ]*)?(never ?mind|carry on|continue|go on|keep going|resume|as you were|go ahead|finish)(\W.*)?$/i;
window.__i3Speak=speak;
function speakBrowser(textValue){agentPauseListening();try{if(!('speechSynthesis' in window)){agentResumeListening();return;}speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(textValue);u.rate=1.02;u.pitch=1;const voices=speechSynthesis.getVoices();const pick=voices.find(v=>/en(-|_)(GB|ZA|AU)/i.test(v.lang)&&/female|Samantha|Karen|Moira|Google UK English Female/i.test(v.name))||voices.find(v=>/^en/i.test(v.lang));if(pick)u.voice=pick;agent.speaking=true;u.onend=()=>{agent.speaking=false;agent.followUntil=performance.now()+8000;setTimeout(agentResumeListening,250);};u.onerror=()=>{agent.speaking=false;agentResumeListening();};speechSynthesis.speak(u);bargeInWatch();}catch(error){agent.speaking=false;agentResumeListening();}}
function waitFor(selector,ms){return new Promise(resolve=>{const started=performance.now();const check=()=>{const el=document.querySelector(selector);if(el)return resolve(el);if(performance.now()-started>ms)return resolve(null);setTimeout(check,120);};check();});}
async function runActions(actions){const navIds={'/':'nav-home','/page-1':'nav-em','/page-2':'nav-sweep3','/mtdi':'nav-mtdi','/page-3':'nav-page3','/settings':'nav-settings'};
 for(const action of actions||[]){const t=String(action.target||'').toLowerCase();
  if(action.type==='navigate'){const id=navIds[t];if(id){document.getElementById(id)?.click();const until=performance.now()+1500;while(location.pathname!==t&&performance.now()<until)await new Promise(r=>setTimeout(r,60));if(location.pathname!==t){/* the nav button did not take (page still settling): push the route directly */history.pushState({},'',t);window.dispatchEvent(new Event('_dashprivate_pushstate'));window.dispatchEvent(new PopStateEvent('popstate'));}await waitFor('#page-content > *',4000);await new Promise(r=>setTimeout(r,500));}}
  else if(action.type==='tab'){const map={c1:'p1-tab-c1',c2x:'p1-tab-c2x',both:'p1-tab-both',ch3:'sp-tab-rf',wifi:'sp-tab-wifi',bt:'sp-tab-bt'};const id=map[t];if(id){const el=await waitFor('#'+id,4000);el?.click();}}
  else if(action.type==='mode'){await control({action:'mode',mode:t==='offline'?'offline':'online'}).catch(()=>{});}
  else if(action.type==='camera'){const on=t!=='off';const running=!!window.__i3HandVisionRunning||!!state.packet?.camera?.enabled;if(on!==running)document.getElementById('i3-camera-toggle')?.click();}
  else if(action.type==='finger_mouse'){fmToggle(t!=='off');}
  else if(action.type==='scroll'){if(t==='top')scrollTo({top:0,behavior:'smooth'});else if(t==='bottom')scrollTo({top:document.body.scrollHeight,behavior:'smooth'});else scrollBy({top:(t==='up'?-1:1)*innerHeight*.7,behavior:'smooth'});}
  else if(action.type==='character'){
   // "backflip and wave after" arrives as one comma-separated target in spoken
   // order. Await the queue so a following action does not talk over the moves.
   const moves=t.split(',').map(x=>x.trim()).filter(Boolean);
   if(buddyPerform(moves,{replace:true})){
    const until=performance.now()+moves.length*3400+1200;
    while((buddy.clip||buddy.queue.length)&&performance.now()<until)await new Promise(r=>setTimeout(r,80));
   }}
  else if(action.type==='relock'){await control({action:'baseline',channel:t==='all'?null:t,relock:true}).catch(()=>{});}
 }}
function cameraFrame(){try{const video=document.querySelector('.i3-hand-vision-video');if(!video||video.readyState<2)return null;const c=document.createElement('canvas');c.width=512;c.height=Math.round(512*video.videoHeight/Math.max(1,video.videoWidth));c.getContext('2d').drawImage(video,0,0,c.width,c.height);return c.toDataURL('image/jpeg',.7);}catch(error){return null;}}
async function agentRequest(textValue){if(agent.busy)return;agent.busy=true;const seq=agent.stopSeq||0;orbShow('Thinking',textValue);try{const image=cameraFrame();const response=await fetch('/api/agent',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:textValue,image}),signal:AbortSignal.timeout(60000)});const data=await response.json();if((agent.stopSeq||0)!==seq){agent.busy=false;return;}if(!response.ok)throw Error(data.error||'Agent unavailable');orbShow(data.source==='instant'?'Done':data.source==='rules'?'Command mode':'NVTRA','');agent.followUntil=performance.now()+30000;typeIn(document.getElementById('i3-orb-text'),data.say);if(data.source!=='instant')speak(data.say);await runActions(data.actions);setTimeout(orbHideWhenIdle,data.source==='instant'?1800:2200);}catch(error){orbShow('NVTRA could not answer',clean(error.message));setTimeout(orbHideWhenIdle,3500);}finally{agent.busy=false;const q=agent.queued;agent.queued=null;if(q){agent.followUntil=performance.now()+30000;setTimeout(()=>{if(!agent.busy)agentHandleTranscript(q,true);},50);}}}
/* Turn taking: while NVTRA speaks the recogniser is paused so it never hears itself; the
   microphone level can still interrupt it (barge in). A request is sent once the
   operator has stopped talking for 750 ms, not on the engine's own final flag. */
/* Anything that sounds like the name wakes it: fuzzy match on the first words, plus a plain
   question or command spoken to the instrument counts even without the name. */
function fuzzyWake(t){const words=t.toLowerCase().replace(/[^a-z\s]/g,' ').split(/\s+/).filter(Boolean).slice(0,4);const targets=['novatra','navatra','nvtra','nova','nuvatra','nevatra'];const lev=(a,b)=>{const m=[];for(let i=0;i<=a.length;i++){m[i]=[i];}for(let j=1;j<=b.length;j++)m[0][j]=j;for(let i=1;i<=a.length;i++)for(let j=1;j<=b.length;j++)m[i][j]=Math.min(m[i-1][j]+1,m[i][j-1]+1,m[i-1][j-1]+(a[i-1]===b[j-1]?0:1));return m[a.length][b.length];};for(let i=0;i<words.length;i++){const w=words[i],w2=w+(words[i+1]||'');for(const tg of targets){if(w.length>=4&&lev(w,tg)<=Math.max(2,Math.floor(tg.length/3)))return true;if(w2.length>=6&&lev(w2,tg)<=2)return true;}}return false;}
const COMMAND=/^\W*(open|show|go to|take me to|switch to|scroll|relock|turn (on|off)|enable|disable|start|stop)\b/i;
const ASK=/^(please|so|and|now|what|what's|whats|how|how's|why|when|where|who|which|is|are|was|were|will|should|can|could|would|do|does|did|tell|explain|describe|summarise|summarize|open|show|go|take|switch|turn|enable|disable|start|stop|scroll|relock|set|give|read|check|compare|run|make|change|list|report|help)\b/i;
function agentHandleTranscript(transcript,isFinal){const now=performance.now();if(agent.speaking)return;if(agent.busy){/* said while NVTRA is thinking: keep it for right after the answer instead of dropping it */if(isFinal&&transcript.trim().length>2)agent.queued=transcript;return;}
 if(!agent.awake&&!transcript.match(WAKE)&&fuzzyWake(transcript)){transcript='Hey Novatra '+transcript.replace(/^\W*\w+\W*/,'');}
 if(!agent.awake&&!transcript.match(WAKE)&&isFinal&&((transcript.trim().split(/\s+/).length>=3&&ASK.test(transcript.trim()))||(vc.enabled&&COMMAND.test(transcript.trim())))){transcript='Hey Novatra '+transcript;}
 if(!agent.awake&&!transcript.match(WAKE)&&isFinal){orbShow('Heard · say Hey Novatra first',transcript.slice(0,80));setTimeout(orbHideWhenIdle,2500);return;}
 if(agent.pausedAudio||agent.pausedSynth){const said=transcript.replace(WAKE,'').trim();if(RESUME.test(said)){text(document.getElementById('i3-orb-text'),showWake(transcript));speechResume();agent.awake=false;return;}speechDrop();agent.awake=true;agent.awakeAt=now;}
 if(!agent.awake&&agent.followUntil&&now<agent.followUntil&&transcript.trim().length>2){agent.awake=true;agent.awakeAt=now;}
 if(!agent.awake){const m=transcript.match(WAKE);if(!m)return;agent.awake=true;agent.awakeAt=now;agent.pending=transcript.slice(m.index+m[0].length).replace(/^[\s,.;:!?-]+/,'').trim();orbShow('Listening',showWake(agent.pending));}
 else{const part=transcript.replace(WAKE,'').replace(/^[\s,.;:!?-]+/,'').trim();const prev=(agent.pending||'').trim();agent.pending=(vc.enabled&&isFinal&&prev&&now-(agent.pendingAt||0)<4000&&!prev.toLowerCase().includes(part.toLowerCase()))?prev.replace(/[\s.?!,;:]+$/,'')+' '+part.replace(/^[A-Z]/,c=>c.toLowerCase()):part;/* a follow-up while the island is closed (within the follow-up window) must open it again */if(document.getElementById('i3-orb')?.classList.contains('collapsed'))orbShow('Listening',showWake(agent.pending));else text(document.getElementById('i3-orb-text'),showWake(agent.pending));}
 agent.pendingAt=now;
 clearTimeout(agent.silence);const complete=/[?.!]\s*$/.test(transcript.trim())||COMMAND.test((agent.pending||'').trim());const fire=()=>{if(vc.speaking||vc.inflight>0){agent.silence=setTimeout(fire,300);return;}const request=(agent.pending||'').trim();if(request.length>2){agent.awake=false;agentRequest(request);}else if(performance.now()-agent.awakeAt>8000){agent.awake=false;orbHide();}else{orbShow('Go ahead','');}};agent.silence=setTimeout(fire,vc.enabled&&isFinal?(complete?250:1400):isFinal?350:750);}
/* Server transcription. The microphone feeds a small energy based voice detector; each
   utterance (speech, then 650 ms of silence) is encoded as 16 kHz WAV and sent to
   /api/transcribe (Groq Whisper, Gemini audio or OpenAI Whisper). Far more accurate than
   the browser engine, which stays as the fallback when no key can transcribe. */
const vc={ctx:null,proc:null,buf:[],pre:[],speaking:false,silenceMs:0,speechMs:0,startedAt:0,noise:.006,enabled:false,paused:false,available:null};
function wavEncode(chunks,rate){let n=0;for(const c of chunks)n+=c.length;const out=new DataView(new ArrayBuffer(44+n*2));const str=(o,t)=>{for(let i=0;i<t.length;i++)out.setUint8(o+i,t.charCodeAt(i));};str(0,'RIFF');out.setUint32(4,36+n*2,true);str(8,'WAVE');str(12,'fmt ');out.setUint32(16,16,true);out.setUint16(20,1,true);out.setUint16(22,1,true);out.setUint32(24,rate,true);out.setUint32(28,rate*2,true);out.setUint16(32,2,true);out.setUint16(34,16,true);str(36,'data');out.setUint32(40,n*2,true);let o=44;for(const c of chunks){for(let i=0;i<c.length;i++){const v=Math.max(-1,Math.min(1,c[i]));out.setInt16(o,v<0?v*32768:v*32767,true);o+=2;}}return new Blob([out],{type:'audio/wav'});}
function downsample(input,from,to){if(from===to)return Float32Array.from(input);const ratio=from/to,len=Math.floor(input.length/ratio),out=new Float32Array(len);for(let i=0;i<len;i++){const a=Math.floor(i*ratio),b=Math.min(input.length,Math.floor((i+1)*ratio));let sum=0;for(let j=a;j<b;j++)sum+=input[j];out[i]=sum/Math.max(1,b-a);}return out;}
function vcStart(stream){if(vc.ctx)return;const ctx=new (window.AudioContext||window.webkitAudioContext)();vc.ctx=ctx;
 /* Started without a user gesture (NVTRA remembered on across a reload) the context sits suspended and the
    microphone is silent: resume it now and again on the first gesture. */
 const wake=()=>{if(ctx.state!=='running')ctx.resume().catch(()=>{});};wake();for(const type of ['pointerdown','keydown','touchstart'])document.addEventListener(type,wake,{capture:true,passive:true});ctx.onstatechange=()=>{if(ctx.state==='suspended'&&vc.enabled)text(document.getElementById('i3-control-result'),'Click or press a key once so the microphone can start');};const src=ctx.createMediaStreamSource(stream);agent.analyser=ctx.createAnalyser();agent.analyser.fftSize=512;src.connect(agent.analyser);const proc=ctx.createScriptProcessor(2048,1,1);vc.proc=proc;src.connect(proc);proc.connect(ctx.destination);vc.enabled=true;
 proc.onaudioprocess=e=>{if(!vc.enabled)return;const raw=e.inputBuffer.getChannelData(0);let sum=0;for(let i=0;i<raw.length;i++)sum+=raw[i]*raw[i];const level=Math.sqrt(sum/raw.length);const ms=raw.length/ctx.sampleRate*1000;
  if(vc.paused||agent.busy||(agent.speaking&&!vc.speaking)){vc.noise=Math.min(vc.noise,level*.9+vc.noise*.1);return;}
  const frame=downsample(raw,ctx.sampleRate,16000);const gate=Math.max(.008,vc.noise*2.6);
  if(!vc.speaking){vc.pre.push(frame);if(vc.pre.length>14)vc.pre.shift();if(level>gate){vc.speechMs+=ms;if(vc.speechMs>=120){vc.speaking=true;vc.buf=vc.pre.slice();vc.pre=[];vc.silenceMs=0;vc.startedAt=performance.now();if(!agent.awake)orbShow('Listening','');else text(document.getElementById('i3-orb-state'),'Listening');}}else{vc.speechMs=0;vc.noise=vc.noise*.97+level*.03;}}
  else{vc.buf.push(frame);if(level>gate)vc.silenceMs=0;else vc.silenceMs+=ms;const dur=performance.now()-vc.startedAt;const endGap=dur<1500?1000:850;if(vc.silenceMs>endGap||dur>20000){const chunks=vc.buf;vc.buf=[];vc.speaking=false;vc.speechMs=0;if(dur>350)vcSend(chunks);else if(!agent.awake)orbHide();}}};}
async function vcSend(chunks){const blob=wavEncode(chunks,16000);vc.inflight=(vc.inflight||0)+1;try{text(document.getElementById('i3-orb-state'),'Understanding');const r=await fetch('/api/transcribe',{method:'POST',headers:{'Content-Type':'audio/wav'},body:blob,signal:AbortSignal.timeout(30000)});const data=await r.json().catch(()=>({}));if(!r.ok){vc.available=false;vc.enabled=false;agent.recInterimOnly=false;text(document.getElementById('i3-orb-state'),'Browser hearing · '+clean(data.error||('http '+r.status)).slice(0,50));return;}vc.available=true;const t=(data.text||'').trim();if(!t){vcMissed("Didn't catch that");return;}agentHandleTranscript(t,true);}catch(error){vcMissed('Took too long to understand · say it again');}finally{vc.inflight=Math.max(0,(vc.inflight||0)-1);}}
/* A chunk that came back empty or late must never close the island under the operator: if the browser
   just heard the wake word, or more speech is on its way, stay open and wait for it. */
function vcMissed(msg){const heardWake=performance.now()-(agent.wakeHeardAt||0)<6000;if(agent.awake||heardWake){if(heardWake&&!agent.awake){agent.awake=true;agent.awakeAt=performance.now();}orbShow('Go ahead','');return;}if(vc.speaking||vc.inflight>1)return;text(document.getElementById('i3-orb-state'),msg);setTimeout(orbHideWhenIdle,2000);}
function agentPauseListening(){vc.paused=true;try{agent.rec?.stop();}catch(error){}}
function agentResumeListening(){vc.paused=false;if(agent.listening&&agent.rec){try{agent.rec.start();}catch(error){}}}
function agentStartBrowserEngine(){const Rec=window.SpeechRecognition||window.webkitSpeechRecognition;if(!Rec||agent.rec)return false;
 const rec=new Rec();rec.continuous=true;rec.interimResults=true;rec.lang='en-GB';agent.rec=rec;
 rec.onresult=event=>{let interim='',finals='';for(let i=event.resultIndex;i<event.results.length;i++){const r=event.results[i];if(r.isFinal)finals+=r[0].transcript+' ';else interim+=r[0].transcript+' ';}
  if(agent.recInterimOnly){/* the accurate transcript comes from the instrument; the browser only shows what it thinks it hears so the operator sees a response at once */const t=(interim||finals).trim();if(t&&!agent.busy){const wake=fuzzyWake(t)||WAKE.test(t);if(wake)agent.wakeHeardAt=performance.now();if(!document.getElementById('i3-orb').classList.contains('collapsed')||wake){orbShow(agent.awake?'Listening':'Hearing…',showWake(t).slice(0,90));document.getElementById('i3-orb-text')?.classList.add('guess');}}return;}
  if(finals.trim())agentHandleTranscript(finals.trim(),true);else if(interim.trim())agentHandleTranscript(interim.trim(),false);};
 rec.onerror=event=>{if(event.error==='not-allowed'||event.error==='service-not-allowed'){orbShow('Microphone permission denied','Allow the microphone for this site and try again');setTimeout(orbHide,3000);agentStop();}else if(event.error==='network'){text(document.getElementById('i3-orb-state'),'Speech service offline; type below');}};
 rec.onend=()=>{if(agent.listening&&!agent.speaking&&agent.rec===rec){setTimeout(()=>{if(agent.listening&&!agent.speaking&&agent.rec===rec){try{rec.start();}catch(error){}}},120);}};
 try{rec.start();return true;}catch(error){return false;}}
function agentStart(){const btn=document.getElementById('i3-agent-toggle');if(!navigator.mediaDevices?.getUserMedia){orbShow('Microphone not available','Use the secure https page, then allow the microphone');setTimeout(orbHide,3500);return;}
 navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}}).then(stream=>{agent.listening=true;btn?.setAttribute('aria-pressed','true');vcStart(stream);vc.enabled=true;vc.paused=false;text(document.getElementById('i3-control-result'),'NVTRA is listening. Say: Hey Novatra, open the sweep3 page.');
  /* The browser's own recogniser (Safari, Chrome, Edge) is streaming, free and answers in well under a
     second, so it is the primary engine. The server path (Groq/Gemini/OpenAI) is the fallback for
     browsers without one (Firefox) and can take 10 s or fail on free-tier quotas. */
  /* Engine choice. The instrument's own Whisper (faster-whisper on this host, taught the
     instrument's vocabulary) is far more accurate than the browser recogniser, so when it is
     loaded the microphone audio goes there (VAD → 16 kHz WAV → /api/transcribe) and the
     browser engine only paints interim words for feedback. Until it has loaded, or on an
     instrument without it, the browser engine does the whole job. */
  agent.recInterimOnly=false;const started=agentStartBrowserEngine();
  const pick=()=>fetch('/api/transcribe',{cache:'no-store'}).then(r=>r.json()).then(st=>{const local=!!st.local?.available;const cloud=(st.cloud||[]).length>0&&!st.offline;
   if(local||(cloud&&!started)){vc.enabled=true;vc.available=true;agent.recInterimOnly=true;text(document.getElementById('i3-control-result'),'NVTRA is listening ('+(local?'on-device Whisper '+st.local.model:'cloud transcription')+'). Say: Hey Novatra, open the sweep3 page.');camHud?.('');return true;}
   if(st.local?.loading){text(document.getElementById('i3-control-result'),'NVTRA is listening (browser engine while the on-device speech model loads)');return false;}
   if(!started){vc.enabled=cloud;vc.available=cloud;if(!cloud)orbShow('Voice recognition unavailable','This browser has no speech engine and the instrument has no local model or cloud key. Type below.');}
   else text(document.getElementById('i3-control-result'),'NVTRA is listening (browser engine). Say: Hey Novatra…');return !st.local?.loading;}).catch(()=>false);
  pick().then(done=>{if(!done){const timer=setInterval(()=>{if(!agent.listening){clearInterval(timer);return;}pick().then(ok=>{if(ok)clearInterval(timer);});},5000);}});
 }).catch(error=>{orbShow('Microphone permission denied','Allow the microphone and try again');setTimeout(orbHide,3000);btn?.setAttribute('aria-pressed','false');});}
function agentStop(){agent.listening=false;vc.enabled=false;try{agent.rec?.stop();}catch(error){}agent.rec=null;document.getElementById('i3-agent-toggle')?.setAttribute('aria-pressed','false');orbHide();text(document.getElementById('i3-control-result'),'NVTRA stopped listening');}
function agentToggle(){if(agent.listening){agentStop();try{localStorage.setItem('i3-agent','off');}catch(error){}}else{agentStart();try{localStorage.setItem('i3-agent','on');}catch(error){}}}
function restoreDevices(){try{if(localStorage.getItem('i3-camera')==='on'&&!window.__i3HandVisionRunning&&navigator.mediaDevices?.getUserMedia){setTimeout(()=>document.getElementById('i3-camera-toggle')?.click(),800);}if(localStorage.getItem('i3-agent')==='on'&&!agent.listening){setTimeout(agentStart,1400);}}catch(error){}}
function orbSubmit(){const input=document.getElementById('i3-orb-input');const value=(input?.value||'').trim();if(value){input.value='';agentRequest(value);}}
document.addEventListener('submit',event=>{if(event.target.id==='i3-orb-form'){event.preventDefault();orbSubmit();}});
document.addEventListener('keydown',event=>{if(event.target.id==='i3-orb-input'&&event.key==='Enter'){event.preventDefault();event.stopPropagation();orbSubmit();}},true);
document.addEventListener('click',event=>{if(event.target.closest('#i3-orb-form button')){event.preventDefault();orbSubmit();}});
/* Diagnostics handle: lets the console (and the test harness) feed NVTRA transcripts and inspect its state. */
window.__i3Voice={agent,vc,handle:agentHandleTranscript,missed:function(m){vcMissed(m);},show:orbShow,hide:orbHide,request:function(t){return agentRequest(t);},send:function(chunks){return vcSend(chunks);}};
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!agent.busy)orbHide();});
document.addEventListener('click',event=>{const orb=event.target.closest('#i3-orb');if(orb&&orb.classList.contains('collapsed')){orbShow(agent.listening?'Listening':'Type a request or say Hey Novatra','');document.getElementById('i3-orb-input')?.focus();}});
/* Only a real click by the operator dismisses the island, and never in the middle of an exchange
   (awake, a chunk decoding): synthetic clicks from the finger mouse or voice navigation must not close it. */
document.addEventListener('click',event=>{const orb=document.getElementById('i3-orb');if(orb&&event.isTrusted&&!orb.classList.contains('collapsed')&&!event.target.closest('#i3-orb')&&!agent.busy&&!agent.awake&&!(vc.inflight>0))orbHide();});
/* The site uses its own cursor everywhere: the ring follows the mouse, or the fingertip when the finger mouse is on. */
addEventListener('pointermove',e=>{if(!e.isTrusted||e.pointerType!=='mouse')return;const iv=cursorMode()==='iv';fingerMouse.blend=null;if(!iv){/* MAC mode: remember where the pointer is (the hand glides from here) but show only the system pointer */cursorPos.x=e.clientX;cursorPos.y=e.clientY;cursorPos.by='pointer';fmCursor().classList.remove('visible');return;}fmPlace(e.clientX,e.clientY,'pointer');const el=fmCursor();const over=e.target?.closest?.('a,button,[role=button],input,select,summary,label,.tab-btn,.nav-glass-btn,.module-card,.mtdi-card,.i3-tool,.i3-mode-card');el.classList.toggle('hover',!!over);},{passive:true});
document.addEventListener('mouseleave',()=>{if(cursorMode()!=='iv')fmCursor().classList.remove('visible');});
applyCursorMode();
addEventListener('mousedown',()=>{const el=fmCursor();el.classList.add('click');setTimeout(()=>el.classList.remove('click'),200);},{passive:true});
let liquidRafGlobal=0;
async function boot(){
 const progress=document.getElementById('i3-boot-progress'),status=document.getElementById('i3-boot-state'),percent=document.getElementById('i3-boot-percent'),steps=Array.from(document.querySelectorAll('#i3-boot-steps span'));let stage=0;const milestones=[.65,.70,.85,.95,1];
 const setProgress=(fraction,label)=>{const pct=Math.round(clamp(fraction,0,1)*100);if(progress)progress.style.width=(clamp(fraction,0,1)*100).toFixed(2)+'%';const bar=progress?.parentElement;if(bar)bar.setAttribute('aria-valuenow',String(pct));text(percent,pct+'%');if(label)text(status,label);steps.forEach((el,i)=>el.classList.toggle('done',i<stage));};
 window.__i3BootTaken=true;window.__i3BootLiquid=true;
 const complete=label=>{setProgress(milestones[stage]??1,label);stage++;steps.forEach((el,i)=>el.classList.toggle('done',i<stage));};
 /* Liquid loader: three summed sines per column, like the reference component, rendered with GPU transforms. */
 const columns=Array.from(document.querySelectorAll('.i3-liquid-col'));let liquidRaf=0;
 const liquid=()=>{if(!document.getElementById('i3-boot'))return;const time=performance.now()*.001;columns.forEach((col,index)=>{const delay=index*.72;const level=clamp(.16+.84*(.5+.5*Math.sin(time*1.15+delay)+Math.sin(time*2.3+delay)*.06),.12,1);const bar=col.querySelector('.i3-bar');bar.style.transform='scaleY('+level.toFixed(3)+')';col.querySelector('.i3-drop').classList.toggle('on',level>.9);});liquidRaf=requestAnimationFrame(liquid);liquidRafGlobal=liquidRaf;};
 if(!reduced()){liquidRaf=requestAnimationFrame(liquid);liquidRafGlobal=liquidRaf;}else columns.forEach(col=>{col.querySelector('.i3-bar').style.transform='scaleY(.6)';});
 setProgress(.55,'Interface modules received');text(document.getElementById('i3-boot-detail'),'Verifying fonts, graphics and instrument status');fmCursor();
 const sceneImages=Array.from(document.querySelectorAll('#i3-scene img[data-src]'));sceneImages.forEach(img=>{img.src=img.dataset.src;img.removeAttribute('data-src');});/* the scene layers load only after the bundles */
 /* A bundle that failed or arrived truncated over a weak link leaves Dash unable to mount and the
    loader stuck for good. Reload once (bypassing the broken cache entry) instead of waiting forever. */
 {const failed=(window.__i3FailedScripts||[]).length>0,noDcc=!window.dash_core_components||!window.dash_renderer;let tries=0;try{tries=+(sessionStorage.getItem('i3-boot-retry')||0);}catch(e){}
  if((failed||noDcc)&&tries<2){try{sessionStorage.setItem('i3-boot-retry',String(tries+1));}catch(e){}text(status,'A module did not arrive intact; reloading');await new Promise(resolve=>setTimeout(resolve,600));location.reload();return;}
  if(!failed&&!noDcc){try{sessionStorage.removeItem('i3-boot-retry');}catch(e){}}}
 /* a background tab gets no animation frames; do not let the boot wait on one */
 await Promise.race([new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))),new Promise(resolve=>setTimeout(resolve,400))]);
 const fontsReady=await Promise.race([document.fonts.ready.then(()=>true),new Promise(resolve=>setTimeout(()=>resolve(false),2500))]);complete(fontsReady?'Typography ready':'Typography fallback ready');
 if(getComputedStyle(root).getPropertyValue('--i3-css-ready').trim()!=='238'){text(status,'Styles unavailable. Reload to retry.');return;}complete('Layout and theme ready');
 const hasGL=createGL();
 /* Page effects first: the parallax layers and the hand model are fetched now, while the loader
    is on screen, so every hero and the camera start instantly afterwards. */
 text(status,'Loading effects and scene layers');const graphicsReady=await Promise.race([Promise.all([...sceneImages.map(img=>img.decode?img.decode().catch(()=>{}):Promise.resolve()),...['/assets/parallax/scroll-1.svg','/assets/parallax/scroll-2.svg','/assets/parallax/scroll-4.svg'].map(u=>fetch(u,{cache:'force-cache'}).then(r=>{if(!r.ok)throw Error(String(r.status));}).catch(()=>{}))]).then(()=>true),new Promise(resolve=>setTimeout(()=>resolve(false),4000))]);prefetchHandModel();
 complete(graphicsReady?(hasGL?'Graphics and effects ready':'Accessible graphics ready'):'Core graphics ready; optional layers continuing');
 let packet,attempt=0;for(;;){try{packet=await snapshot();break;}catch(error){attempt++;text(status,'Waiting for the instrument, attempt '+attempt+'. '+clean(error.message));await new Promise(resolve=>setTimeout(resolve,1500));}}
 complete('Sensor status received');
 const shell=await new Promise(resolve=>{const check=()=>{const node=document.getElementById('page-content');if(node?.firstElementChild){resolve(node);return true;}return false;};if(check())return;const observer=new MutationObserver(()=>{if(check())observer.disconnect();});observer.observe(document.body,{subtree:true,childList:true});});
 complete('Interface mounted');
 cacheNodes();drawPacket(packet);
 await chooseMode(packet);
 /* Single readiness event. The original document boot (intro, page shader, robot) runs first so
    body.intro-active and the Home handoff transform exist before anything becomes visible. */
 window.__i3ResolveReady?.();await new Promise(resolve=>setTimeout(resolve,0));
 setProgress(1,'Interface ready');await new Promise(resolve=>setTimeout(resolve,180));
 root.dataset.i3Ready='true';cancelAnimationFrame(liquidRaf);document.getElementById('i3-boot')?.remove();metrics.readyMs=performance.now();
 window.dispatchEvent(new CustomEvent('studio:ready',{detail:{webgl:hasGL,readyMs:metrics.readyMs}}));
 control({action:'start'}).catch(()=>{});restoreDevices();setTimeout(buddyMount,1500);
 orbAnimate();let rescan=0;new MutationObserver(records=>{if(!records.some(r=>r.addedNodes.length||r.removedNodes.length))return;if(rescan)return;rescan=requestAnimationFrame(()=>{rescan=0;cacheNodes();mountMotion();});}).observe(shell,{childList:true,subtree:true});setupControls();connect();
 requestAnimationFrame(()=>{compileGL();requestAnimationFrame(frame);mountMotion();});
 setInterval(()=>{const el=document.getElementById('i3-performance');if(el){const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:0;text(el,'Browser '+Math.round(1000/(mean(metrics.frames)||1000))+' fps · instrument drawing '+mean(metrics.work).toFixed(2)+' ms · layout shift '+metrics.layoutShift.toFixed(4));}if(Date.now()-state.lastMessage>15000)text(document.getElementById('i3-stream-state'),'Waiting for stream. Reconnect is automatic.');},5000);
 setInterval(()=>{const ordered=metrics.work.slice().sort((a,b)=>a-b),avg=metrics.frames.length?metrics.frames.reduce((a,b)=>a+b,0)/metrics.frames.length:0;fetch('/api/performance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({first_meaningful_paint_ms:metrics.readyMs,fps:avg?1000/avg:0,frame_work_p95_ms:ordered[Math.floor(ordered.length*.95)]||0,long_tasks:metrics.longTasks,samples_dropped:state.packet?.archive?.dropped||0,refresh_hz:refreshEstimate(),dpr:devicePixelRatio||1,viewport_w:innerWidth,viewport_h:innerHeight,agent:navigator.userAgent.slice(0,160)})}).catch(()=>{});},30000);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();

/* ══════════════════════════════════════════════════════════
   Easter eggs: Judge detected (J), Environmental Intelligence arm,
   Aether terminal (Pyodide sandbox), Judge Mode, classified QR, Fieldrun.
   None of this touches acquisition, packets or callbacks.
   ══════════════════════════════════════════════════════════ */
(function(){
const EGG={jTimer:null,jHeld:false,armedUntil:0,judgeBusy:false,judgeAt:0,py:null,pyLoading:null};
const typing=()=>{const a=document.activeElement;return !!a&&(a.tagName==='INPUT'||a.tagName==='TEXTAREA'||a.tagName==='SELECT'||a.isContentEditable);};
const onSixth=()=>location.pathname==='/mtdi';
const sysNote=(msg,ms,big)=>{let el=document.getElementById('i3-sys-note');if(!el){el=document.createElement('div');el.id='i3-sys-note';el.setAttribute('role','status');document.body.appendChild(el);}
 el.className='i3-sys-note'+(big?' i3-sys-note-big':'');el.textContent=msg;clearTimeout(sysNote.t);requestAnimationFrame(()=>requestAnimationFrame(()=>el.classList.add('on')));sysNote.t=setTimeout(()=>el.classList.remove('on'),ms);};
/* ── J anywhere: "Judge detected" · K arms the Environmental Intelligence line for 5 s · H on Sweep3: JUDGE FREQUENCY ── */
addEventListener('keydown',e=>{
 if(e.metaKey||e.ctrlKey||e.altKey||typing()||e.repeat)return;const k=e.key.toLowerCase();
 if(k==='j'){if(!EGG.judgeBusy)sysNote('Judge detected',1600,false);return;}
 if(k==='k'){EGG.armedUntil=performance.now()+5000;return;}
 if(k==='h'&&location.pathname==='/page-2')judgeFrequency();
});
const eiOpening=target=>{if(!target||!target.closest)return false;if(target.closest('#c1-recal-btn,#c2-recal-btn,[id$="-recal-btn"]'))return true;const card=target.closest('.mtdi-orbit-card[data-mtdi-id="environment"]');return card&&!card.classList.contains('is-expanded')&&!target.closest('.mtdi-detail-close');};
const eiTrigger=()=>{if(performance.now()>EGG.armedUntil)return;EGG.armedUntil=0;setTimeout(()=>sysNote('The composite universe has been politely asked to shut up.',2700,true),420);};
document.addEventListener('click',e=>{if(eiOpening(e.target))eiTrigger();},true);
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&eiOpening(e.target))eiTrigger();},true);
function judgeFrequency(){if(performance.now()-(EGG.freqAt||0)<3200)return;EGG.freqAt=performance.now();i3Log('judge','Judge frequency detected on the sweep3 view');document.querySelectorAll('.i3-freq-note').forEach(n=>n.remove());
 const el=document.createElement('div');el.className='i3-freq-note';el.setAttribute('role','status');el.innerHTML='JUDGE FREQUENCY DETECTED<small>SWEEP3 ANALYSIS · PRESENTATION PROTOCOL ACTIVE</small>';document.body.appendChild(el);boom();setTimeout(()=>el.remove(),2700);}
/* ── NVTRA pillar entrance: the boot liquid loader, once per open ── */
const LOGO_SVG='<svg viewBox="120 300 612 420" aria-hidden="true"><defs><linearGradient id="lgau" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e2c56b"/><stop offset="1" stop-color="#c9a44a"/></linearGradient><radialGradient id="lgglow"><stop offset="0" stop-color="#e2c56b" stop-opacity=".55"/><stop offset="1" stop-color="#e2c56b" stop-opacity="0"/></radialGradient></defs><ellipse class="lg-glow" cx="426" cy="540" rx="300" ry="190" fill="url(#lgglow)"/><g fill="none" stroke="url(#lgau)" stroke-width="22" stroke-linejoin="miter" stroke-miterlimit="6"><polyline class="lg-stroke s1" points="176,344 410,514 410,672"/><polyline class="lg-stroke s1" points="676,344 442,514 442,672"/><polyline class="lg-stroke s2" points="232,432 372,532 372,608"/><polyline class="lg-stroke s2" points="620,432 480,532 480,608"/><polyline class="lg-stroke s3" points="248,472 338,540 338,588"/><polyline class="lg-stroke s3" points="604,472 514,540 514,588"/></g><g fill="url(#lgau)"><polygon class="lg-tip s1" points="399,672 421,672 410,690"/><polygon class="lg-tip s1" points="431,672 453,672 442,690"/><polygon class="lg-tip s2" points="361,608 383,608 372,622"/><polygon class="lg-tip s2" points="469,608 491,608 480,622"/><polygon class="lg-tip s3" points="327,588 349,588 338,600"/><polygon class="lg-tip s3" points="503,588 525,588 514,600"/></g></svg>';
function nvtraEntrance(card){if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;card.querySelectorAll('#i3-nvtra-boot').forEach(n=>n.remove());const el=document.createElement('div');el.id='i3-nvtra-boot';el.setAttribute('aria-hidden','true');el.innerHTML=LOGO_SVG+'<div class="i3-boot-eyebrow">NVTRA · COMPOSITE INTELLIGENCE</div>';card.appendChild(el);
 setTimeout(()=>el.classList.add('out'),2300);setTimeout(()=>el.remove(),2950);}
new MutationObserver(muts=>{for(const m of muts){const card=m.target;if(card.matches&&card.matches('.mtdi-orbit-card[data-mtdi-id="nvtra"]')&&card.classList.contains('is-expanded')&&!card.__i3Entered){card.__i3Entered=true;nvtraEntrance(card);}else if(card.matches&&card.matches('.mtdi-orbit-card[data-mtdi-id="nvtra"]')&&!card.classList.contains('is-expanded'))card.__i3Entered=false;}}).observe(document.body,{attributes:true,subtree:true,attributeFilter:['class']});
/* ── Vine boom (synthesised, no asset) ── */
function boom(){try{const ctx=new (window.AudioContext||window.webkitAudioContext)();const t=ctx.currentTime;const master=ctx.createGain();master.gain.value=.9;master.connect(ctx.destination);
 const o=ctx.createOscillator();o.type='sine';o.frequency.setValueAtTime(160,t);o.frequency.exponentialRampToValueAtTime(28,t+.55);const g=ctx.createGain();g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(1,t+.012);g.gain.exponentialRampToValueAtTime(.001,t+1.4);o.connect(g);g.connect(master);o.start(t);o.stop(t+1.5);
 const o2=ctx.createOscillator();o2.type='triangle';o2.frequency.setValueAtTime(60,t);o2.frequency.exponentialRampToValueAtTime(34,t+.9);const g2=ctx.createGain();g2.gain.setValueAtTime(.6,t);g2.gain.exponentialRampToValueAtTime(.001,t+1.8);o2.connect(g2);g2.connect(master);o2.start(t);o2.stop(t+1.9);
 const n=ctx.createBuffer(1,ctx.sampleRate*.25,ctx.sampleRate);const d=n.getChannelData(0);for(let i=0;i<d.length;i++)d[i]=(Math.random()*2-1)*Math.pow(1-i/d.length,3);const ns=ctx.createBufferSource();ns.buffer=n;const lp=ctx.createBiquadFilter();lp.type='lowpass';lp.frequency.value=900;const ng=ctx.createGain();ng.gain.value=.5;ns.connect(lp);lp.connect(ng);ng.connect(master);ns.start(t);
 setTimeout(()=>ctx.close().catch(()=>{}),2600);}catch(error){}}
/* ── Judge Mode ── */
const judgeEls=()=>{if(judgeEls.done)return judgeEls.done;const dim=document.createElement('div');dim.id='i3-judge-dim';const hud=document.createElement('div');hud.id='i3-judge-hud';const flash=document.createElement('div');flash.id='i3-judge-flash';
 const panel=document.createElement('div');panel.id='i3-judge-panel';panel.innerHTML='<div class="i3-judge-top"><h1>JUDGE MODE<span>PRESENTATION PROTOCOL · LIVE INSTRUMENT READINGS</span></h1><button type="button" class="i3-judge-exit">EXIT JUDGE MODE</button></div><div class="i3-judge-grid" id="i3-judge-grid"></div>';
 panel.querySelector('.i3-judge-exit').addEventListener('click',judgeExit);document.body.append(dim,hud,flash,panel);return judgeEls.done={dim,hud,flash,panel};};
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function judgeMode(put){i3Log('judge','Judge mode triggered from the Aether terminal');
 if(EGG.judgeBusy)return put('Judge Mode is already running.','t-warn');
 if(performance.now()-EGG.judgeAt<12000)return put('Judge Mode cooling down · try again in a moment.','t-warn');
 EGG.judgeBusy=true;EGG.judgeAt=performance.now();const els=judgeEls();
 try{
  els.dim.classList.add('on');await wait(450);
  els.hud.innerHTML='<div class="i3-judge-alert">JUDGE DETECTED<small>SG PERIMETER BREACHED</small></div>';els.hud.classList.add('on');
  try{const say=window.__i3Speak;if(say)say('OHHHH NO! JUDGE ALERT!');}catch(error){}
  await wait(2300);boom();els.flash.style.transition='none';els.flash.style.opacity='.75';requestAnimationFrame(()=>{els.flash.style.transition='opacity .5s ease';els.flash.style.opacity='0';});
  await wait(350);els.hud.innerHTML='<div class="i3-judge-hud-proto"><b>JUDGE MODE</b>PRESENTATION PROTOCOL ACTIVE<em>LOOK PROFESSIONAL IMMEDIATELY</em></div>';
  await wait(2600);els.hud.classList.remove('on');els.dim.classList.remove('on');await wait(450);
  judgePanelOpen();put('Presentation interface enabled. Use EXIT JUDGE MODE to return to Aether.','t-sys');
 }finally{EGG.judgeBusy=false;}
}
function judgePanelOpen(){const els=judgeEls();els.panel.classList.add('on');judgeTick();EGG.judgeTimer=setInterval(judgeTick,600);}
function judgeExit(){const els=judgeEls();els.panel.classList.remove('on');clearInterval(EGG.judgeTimer);}
function judgeTick(){const grid=document.getElementById('i3-judge-grid');if(!grid)return;const p=window.__i3Instrument||{};const ch=p.channels||{};const fu=p.fusion||{};
 const num=(v,d=2)=>Number.isFinite(v)?Number(v).toFixed(d):'—';
 const tile=(k,v,unit,s,cls)=>'<div class="i3-judge-tile '+(cls||'')+'"><div class="k">'+k+'</div><div class="v">'+v+(unit?'<small>'+unit+'</small>':'')+'</div><div class="s">'+s+'</div></div>';
 const st=c=>!c?'bad':c.state==='connected'?(c.clipped?'warn':'ok'):'bad';const sv=c=>!c?'NOT PRESENT':c.state==='connected'?(c.clipped?'CLIPPING':'CONNECTED'):String(c.state||'OFFLINE').toUpperCase();
 const m=ch.ch1,e=ch.ch2,r=ch.ch3;const conf=Number(fu.confidence)||0;
 grid.innerHTML=
  tile('CHANNEL 3',r&&r.state==='connected'?num(r.deviation,1):'—',r?r.unit||'':'',sv(r),st(r))+
  tile('CHANNEL 1',m&&m.state==='connected'?num(m.display&&m.display.magnitude,2):'—','',sv(m),st(m))+
  tile('CHANNEL 2',e&&e.state==='connected'?num(e.display&&e.display.rms_mv,1):'—','',sv(e),st(e))+
  tile('MTDI · FUSED',String(fu.condition||'—').toUpperCase(),'',String(fu.interpretation||'').slice(0,110),'text '+(conf>80?'ok':conf>50?'warn':'bad'))+
  tile('CONFIDENCE',conf.toFixed(0),'%','Evidence quality',conf>80?'ok':conf>50?'warn':'bad')+
  tile('STATUS',[m,e,r].filter(c=>c&&c.state==='connected').length+' / 3','','channels reporting',[m,e,r].every(c=>c&&c.state==='connected')?'ok':'warn')+
  '<div class="i3-judge-tile wide"><div class="k">MAJOR ALERTS</div>'+((fu.warnings||[]).length?'<ul>'+fu.warnings.slice(0,4).map(w=>'<li>'+String(w).replace(/</g,'&lt;')+'</li>').join('')+'</ul>':'<div class="v">No active alerts.</div>')+'</div>';}
/* ── Aether terminal ── */
const esc=t=>String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;');
const HELP=['AETHER TERMINAL · commands','  any Python expression or statement   e.g. 2 + 2 · print("NVTRA") · for i in range(5): print(i)','  nano file.py      write a small Python file (^O save · ^X save & exit)','  python file.py    run a file you wrote · ls · cat file.py · rm file.py','  clear             wipe the screen','  help()            this list','  i3_game.py        launch Fieldrun (X returns to Aether)','  judge mode        you have been warned','  rickroll          classified','Shift+Enter inserts a newline · ↑/↓ browse history'].join('\n');
const SAFE_PRELUDE='import sys\nfor _m in ("subprocess","socket","ctypes","multiprocessing","_thread"):\n    sys.modules[_m]=None\nimport os as _os\nfor _n in ("system","popen","remove","unlink","rmdir","removedirs","rename","kill","execv","execvp","spawnl"):\n    try:\n        setattr(_os,_n,None)\n    except Exception:\n        pass\ndel _os\n';
async function pyodideReady(setState){if(EGG.py)return EGG.py;if(EGG.pyLoading)return EGG.pyLoading;
 EGG.pyLoading=(async()=>{setState('LOADING PYTHON',true);if(!window.loadPyodide){await new Promise((res,rej)=>{const sc=document.createElement('script');sc.src='https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js';sc.onload=res;sc.onerror=()=>rej(Error('Python runtime unreachable (offline?)'));document.head.appendChild(sc);});}
  const py=await window.loadPyodide({indexURL:'https://cdn.jsdelivr.net/pyodide/v0.26.4/full/'});await py.runPythonAsync(SAFE_PRELUDE);EGG.py=py;setState('SANDBOX READY',false);return py;})().catch(error=>{EGG.pyLoading=null;setState('CORE STANDBY',false);throw error;});
 return EGG.pyLoading;}
function mountAetherTerminal(){document.querySelectorAll('[data-i3-aether-terminal]:not([data-i3-mounted])').forEach(term=>{term.dataset.i3Mounted='1';
 const card=term.closest('.aether-term-card'),out=term.querySelector('.aether-term-out'),inp=term.querySelector('.aether-term-in'),stateEl=card.querySelector('#aether-term-state'),tick=card.querySelector('#aether-term-tick');
 const history=[];let hIdx=0,draft='';const put=(line,cls)=>{const span=document.createElement('span');if(cls)span.className=cls;span.textContent=line+'\n';out.appendChild(span);out.scrollTop=out.scrollHeight;};
 const setState=(label,busy)=>{stateEl.textContent=label;card.classList.toggle('is-busy',!!busy);card.classList.toggle('is-ready',!!EGG.py);};
 term.addEventListener('click',e=>{if(e.target!==out&&!out.contains(e.target))inp.focus();});
 const startup=['NVTRA AETHER TERMINAL','TITLE','AETHER CORE ONLINE','Python Sandbox Ready'];startup.forEach((l,i)=>setTimeout(()=>{put(l,i<3?'t-sys':'t-dim');if(i===3){put('type help() for commands','t-dim');setState('CORE STANDBY',false);}},260+i*330));
 const t0=Date.now();const tickFn=()=>{if(!tick.isConnected)return clearInterval(tickId);const s=Math.floor((Date.now()-t0)/1000);tick.textContent='SESSION '+String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')+' · '+new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'});};const tickId=setInterval(tickFn,1000);tickFn();
 const classified=card.querySelector('#aether-classified'),game=card.querySelector('#aether-game'),frame=card.querySelector('#aether-game-frame');document.querySelectorAll('body > .aether-game').forEach(old=>old.remove());document.body.appendChild(game);/* fixed overlay must escape the card's containing block */
 classified.querySelector('.aether-classified-close').addEventListener('click',()=>{classified.hidden=true;});
 const closeGame=()=>{if(game.hidden)return;game.hidden=true;frame.innerHTML='';document.documentElement.style.overflow='';inp.focus();put('Fieldrun closed · back in Aether','t-dim');};game.querySelector('.aether-game-close').addEventListener('click',closeGame);
 addEventListener('message',e=>{if(e.data==='i3-fieldrun-close')closeGame();});addEventListener('keydown',e=>{if(!game.hidden&&(e.key==='x'||e.key==='X'))closeGame();});
 const files=EGG.files||(EGG.files=new Map());const nano=term.querySelector('.aether-nano'),nanoBody=nano.querySelector('.aether-nano-body'),nanoFile=nano.querySelector('.aether-nano-file');let nanoName='';
 const nanoSave=()=>{files.set(nanoName,nanoBody.value);put('[ Wrote '+nanoBody.value.split('\n').length+' lines to '+nanoName+' ]','t-dim');};const nanoClose=()=>{nano.hidden=true;inp.focus();};
 const nanoOpen=name=>{nanoName=name;nanoFile.textContent=name+(files.has(name)?'':'  (new file)');nanoBody.value=files.get(name)||'';nano.hidden=false;put('nano '+name+' · ^O writes · ^X saves and exits','t-dim');setTimeout(()=>nanoBody.focus(),30);};
 nanoBody.addEventListener('keydown',e=>{e.stopPropagation();if(e.ctrlKey&&(e.key==='o'||e.key==='O')){e.preventDefault();nanoSave();}else if(e.ctrlKey&&(e.key==='x'||e.key==='X')){e.preventDefault();nanoSave();nanoClose();}else if(e.key==='Escape'){e.preventDefault();nanoSave();nanoClose();}else if(e.key==='Tab'){e.preventDefault();const st=nanoBody.selectionStart,en=nanoBody.selectionEnd;nanoBody.value=nanoBody.value.slice(0,st)+'    '+nanoBody.value.slice(en);nanoBody.selectionStart=nanoBody.selectionEnd=st+4;}});
 nanoBody.addEventListener('keyup',e=>e.stopPropagation());nanoBody.addEventListener('keypress',e=>e.stopPropagation());
 const launchGame=()=>{put('Locating i3_game.py … found in AETHER CORE','t-dim');put('Booting FIELDRUN · reactor recovery simulation','t-sys');setTimeout(()=>{frame.innerHTML='';const f=document.createElement('iframe');f.src='/assets/aether/fieldrun.html?t='+Date.now();f.title='MTDI Studio Fieldrun';f.allow='camera; autoplay';f.setAttribute('allowfullscreen','');frame.appendChild(f);game.hidden=false;document.documentElement.style.overflow='hidden';setTimeout(()=>{try{f.contentWindow.focus();}catch(error){}},400);},700);};
 async function run(raw){const code=raw.replace(/\s+$/,'');if(!code.trim())return;put('aether$ '+code,'t-in');history.push(code);if(history.length>200)history.shift();hIdx=history.length;draft='';
  const cmd=code.trim().toLowerCase();
  if(cmd==='judge mode'||cmd==='judgemode'){put('JUDGE MODE ACTIVATED','t-warn');put('Engaging presentation protocol …','t-dim');judgeMode(put);return;}
  if(cmd==='rickroll'||cmd==='rick roll'){put('Scanning AETHER CORE for classified resources …','t-dim');await wait(650);put('CLASSIFIED NVTRA RESOURCE LOCATED','t-warn');classified.hidden=false;classified.scrollIntoView({block:'nearest',behavior:'smooth'});return;}
  if(/^(python3?\s+|run\s+|\.\/)?i3_game\.py$/.test(cmd)){launchGame();return;}
  let m;if((m=/^nano(?:\s+(\S+))?$/.exec(cmd))){nanoOpen(m[1]||'untitled.py');return;}
  if(cmd==='ls'||cmd==='dir'){put(files.size?[...files.keys()].concat(['i3_game.py']).join('   '):'i3_game.py','t-dim');return;}
  if((m=/^cat\s+(\S+)$/.exec(cmd))){if(files.has(m[1]))put(files.get(m[1]));else put('cat: '+m[1]+': No such file','t-err');return;}
  if((m=/^rm\s+(\S+)$/.exec(cmd))){put(files.delete(m[1])?'removed '+m[1]:'rm: '+m[1]+': No such file','t-err');return;}
  let fileCode=null;if((m=/^(?:python3?\s+|run\s+|\.\/)?(\S+\.py)$/.exec(cmd))){if(!files.has(m[1])){put('python: can\'t open file \''+m[1]+'\': No such file · write it with nano '+m[1],'t-err');return;}fileCode=files.get(m[1]);}
  if(cmd==='clear'||cmd==='cls'||cmd==='clear()'){out.textContent='';return;}
  if(cmd==='help'||cmd==='help()'||cmd==='?'){put(HELP,'t-dim');return;}
  if(cmd==='exit'||cmd==='exit()'||cmd==='quit'||cmd==='quit()'){put('The core does not exit. It only rests.','t-dim');return;}
  let py;try{py=await pyodideReady(setState);}catch(error){put('Python sandbox unavailable: '+(error.message||error),'t-err');return;}
  setState('RUNNING',true);try{const buf=[];py.setStdout({batched:s=>buf.push(s)});py.setStderr({batched:s=>buf.push(s)});
   let value;try{value=await py.runPythonAsync(fileCode!==null?fileCode:code);}finally{if(buf.length)put(buf.join('\n'));}
   if(value!==undefined&&value!==null){const r=py.globals.get('repr');let shown;try{shown=r(value);}catch(error){shown=String(value);}if(shown!=='None')put(String(shown));}
   if(value&&typeof value.destroy==='function')try{value.destroy();}catch(error){}
  }catch(error){const lines=String(error.message||error).trim().split('\n');const tail=lines.filter(l=>l.trim()&&!/^\s/.test(l)&&!/^Traceback|pyodide|_pyodide/.test(l)).slice(-2);put(tail.join('\n')||'Error','t-err');}
  finally{setState('SANDBOX READY',false);}}
 inp.addEventListener('keydown',e=>{e.stopPropagation();
  if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();const v=inp.value;inp.value='';inp.style.height='';run(v);return;}
  if(e.key==='ArrowUp'&&!inp.value.includes('\n')){if(!history.length)return;e.preventDefault();if(hIdx===history.length)draft=inp.value;hIdx=Math.max(0,hIdx-1);inp.value=history[hIdx];return;}
  if(e.key==='ArrowDown'&&!inp.value.includes('\n')){if(!history.length)return;e.preventDefault();hIdx=Math.min(history.length,hIdx+1);inp.value=hIdx===history.length?draft:history[hIdx];return;}
  if(e.key==='l'&&e.ctrlKey){e.preventDefault();out.textContent='';}});
 inp.addEventListener('keyup',e=>e.stopPropagation());inp.addEventListener('keypress',e=>e.stopPropagation());
 inp.addEventListener('input',()=>{inp.style.height='auto';inp.style.height=Math.min(120,inp.scrollHeight)+'px';});
});}
new MutationObserver(()=>mountAetherTerminal()).observe(document.body,{childList:true,subtree:true});mountAetherTerminal();
window.__i3Egg={judgeMode:()=>judgeMode(()=>{}),judgeFrequency,judgeExit,boom,sysNote,arm:()=>{EGG.armedUntil=performance.now()+5000;}};
})();
})();
'''


def _live(html, path, default="Unavailable", fmt=None, class_name=None):
    args = {"data-i3-bind": path}
    if fmt:
        args["data-i3-format"] = fmt
    if class_name:
        args["className"] = class_name
    return html.Span(default, **args)


def _row(html, label, path, fmt=None):
    return html.Div([html.Span(label, className="i3-label"), _live(html, path, fmt=fmt)], className="i3-row")


def _card(html, title, body, size=""):
    return html.Section([html.Div(title, className="section-label i3-card-title"), *body], className="chart-card i3-card " + size)


def _channel(html, key, title):
    path = "channels." + key
    return _card(html, title, [
        _live(html, path + ".state", "Offline", class_name="i3-state"),
        html.Div([_live(html, path + ".deviation", fmt="number"), " ", _live(html, path + ".unit", "")], className="i3-value"),
        _live(html, path + ".uncertainty", 'Text', class_name="i3-mute"),
        html.Canvas(**{"data-i3-trace": key, "aria-label": title + ' Text', "className": "i3-mini-trace"}),
        _row(html, 'Label', path + ".baseline", "baseline"),
    ], "compact")


def axial_panel(html):
    path = "fusion.axial."
    return _card(html, 'Title', [
        *[_row(html, label, path + key, "number") for key, label in [
            ("x", 'Text'), ("y", 'Text'), ("z", 'Text'),
            ("magnitude", 'Text'), ("disagreement", 'Text'),
            ("agreement", 'Text'), ("contribution", 'Text'), ("confidence_contribution", 'Text')]],
        html.Div('Paragraph. Enter your text here.', className="i3-mute"),
    ])


def baseline_panel(html, dcc):
    return _card(html, 'Title', [
        html.P('Paragraph. Enter your text here.'),
        html.Form([
            html.Div([
                html.Label(['Label', html.Select([html.Option("All", value="all"), html.Option("Channel 1", value="ch1"), html.Option("Channel 2", value="ch2"), html.Option("Channel 3", value="ch3")], name="channel")]),
                html.Label(['Label', dcc.Input(name="window", type="number", value=10, min=2, max=600, step=1)]),
            ], className="i3-form"),
            html.Div([html.Button(label, type="button", className="i3-btn", **{"data-i3-action": "baseline", "data-i3-op": op}) for label, op in [('Text', "window"), ("Relock", "relock"), ("Freeze", "freeze"), ("Resume", "resume")]], className="i3-form"),
            html.Div('Text', className="i3-inline-result", **{"data-i3-result": "true"}),
        ], **{"data-i3-form": "baseline"}),
        *[_row(html, label + " baseline", "channels." + key + ".baseline", "baseline_window") for key, label in [("ch1", 'Channel 1'), ("ch2", 'Channel 2'), ("ch3", "Channel 3")]],
    ], "tall")


def transient_panel(html):
    return _card(html, 'Title', [
        html.Table([
            html.Thead(html.Tr([html.Th(x) for x in ["Channel", "State", "Variance", "Threshold"]])),
            html.Tbody([html.Tr([html.Td(label), *[html.Td(_live(html, "channels." + key + ".transient." + value, fmt="number" if value != "state" else None)) for value in ["state", "variance", "threshold"]]]) for key, label in [("ch1", 'Channel 1'), ("ch2", 'Channel 2'), ("ch3", "Channel 3")]])
        ], className="i3-health"),
        html.P('Paragraph. Enter your text here.'),
    ])


def vector_panel(html):
    return _card(html, 'Title', [
        html.Canvas(className="i3-vector", **{"data-i3-vector": "true", "aria-label": 'Text'}),
        _row(html, 'Label', "fusion.vector.bearing", "number"),
        _row(html, 'Label', "fusion.vector.raw"),
        html.Div('Paragraph. Enter your text here.', className="i3-mute"),
    ])


def signature_panel(html):
    return _card(html, 'Title', [
        html.Div(_live(html, "fusion.interpretation", 'Text'), className="i3-condition"),
        html.Div(_live(html, "fusion.evidence", 'Text'), className="i3-evidence"),
        html.Details([html.Summary('Title'), html.Pre(_live(html, "rules", 'Text', fmt="json"), className="i3-details")]),
    ])


def confidence_panel(html):
    factors = [("availability", "Availability"), ("baseline", "Baseline"),
               ("signal_to_noise", 'Text'), ("clipping", "Clipping"),
               ("timing", "Timing"), ("transient", "Transient"),
               ("axial_consensus", 'Text'), ("correlation", "Correlation")]
    return _card(html, 'Title', [
        html.Div('Paragraph. Enter your text here.', className="i3-mute"),
        html.Table([
            html.Thead(html.Tr([html.Th(label) for label in ["Factor", "Weight", "Ch 1", "Ch 2", "Ch 3"]])),
            html.Tbody([html.Tr([html.Td(label), html.Td(_live(html, "fusion.breakdown.weights." + key, fmt="fraction")), *[
                html.Td(_live(html, "fusion.breakdown.channels." + channel + ".terms." + key + ".value", fmt="number"))
                for channel in ["ch1", "ch2", "ch3"]]]) for key, label in factors]),
        ], className="i3-health"),
        html.Div('Paragraph. Enter your text here.', className="i3-notice"),
    ])


def calibration_panel(html, dcc):
    return _card(html, 'Title', [
        html.Div('Paragraph. Enter your text here.', className="i3-mute"),
        html.Form([
            html.Div([
                html.Label(['Label', html.Select([html.Option("Channel 1", value="ch1"), html.Option("Channel 2", value="ch2"), html.Option("Channel 3", value="ch3")], name="channel")]),
                html.Label(['Label', dcc.Input(name="unit", type="text", value="unit", required=True)]),
                html.Label(['Label', dcc.Input(name="raw_low", type="number", required=True)]),
                html.Label(['Label', dcc.Input(name="raw_high", type="number", required=True)]),
                html.Label(['Label', dcc.Input(name="known_low", type="number", required=True)]),
                html.Label(['Label', dcc.Input(name="known_high", type="number", required=True)]),
                html.Label(['Label', dcc.Input(name="uncertainty", type="number", min=0, required=True)]),
                html.Label(['Label', dcc.Input(name="method", type="text", required=True, minLength=3)]),
            ], className="i3-form"),
            html.Button('Button', type="button", className="i3-btn", **{"data-i3-action": "calibrate"}),
            html.Button('Button', type="button", className="i3-btn", **{"data-i3-action": "reset_calibration"}),
            html.Div('Paragraph. Enter your text here.', className="i3-inline-result", **{"data-i3-result": "true"}),
        ], **{"data-i3-form": "calibration"}),
        *[_row(html, label + " calibrated", "channels." + key + ".calibration.timestamp", "time") for key, label in [("ch1", 'Channel 1'), ("ch2", 'Channel 2'), ("ch3", "Channel 3")]],
    ], "tall")


def _audio_block(html, dcc, key, title, extra):
    path = "audition.sources." + key + "."
    return html.Div([
        html.H4([title, _live(html, path + "state", "Unavailable", class_name="i3-state")]),
        html.Canvas(className="i3-meter", **{"data-i3-meter": key, "aria-label": title + ' Text'}),
        html.Div([html.Span('Label', className="i3-label"), _live(html, path + "level_dbfs", fmt="number")], className="i3-row"),
        html.Div([html.Span("Device", className="i3-label"), _live(html, path + "device")], className="i3-row"),
        html.Div([html.Span("Status", className="i3-label"), _live(html, path + "error", 'Text')], className="i3-row"),
        html.Form([
            html.Div([
                html.Button("Start", type="button", className="i3-btn i3-primary", **{"data-i3-action": "audition", "data-i3-source": key, "data-i3-op": "start"}),
                html.Button("Stop", type="button", className="i3-btn", **{"data-i3-action": "audition", "data-i3-source": key, "data-i3-op": "stop"}),
                html.Button("Mute", type="button", className="i3-btn", **{"data-i3-action": "audition", "data-i3-source": key, "data-i3-op": "mute", "aria-pressed": "false"}),
            ], className="i3-form"),
            html.Label(["Gain", dcc.Input(name="gain", type="range", min=0, max=30, step=0.5, value=4 if key == "ch2f" else 1, className="i3-gain")]),
            *extra,
            html.Audio(preload="none", **{"data-i3-audio": key}),
            html.Div('Text', className="i3-inline-result", **{"data-i3-result": "true"}),
        ], **{"data-i3-form": "audition-" + key}),
    ], className="i3-audio")


def audition_panel(html, dcc):
    sdr_extra = [html.Div([
        html.Label(['Label', dcc.Input(name="frequency_mhz", type="number", min=24, max=1766, step=0.001, value=100)]),
        html.Label(['Label', html.Select([html.Option(m.upper(), value=m) for m in ("wbfm", "fm", "am", "usb", "lsb")], name="mode")]),
        html.Button('Button', type="button", className="i3-btn", **{"data-i3-action": "audition", "data-i3-source": "sdr", "data-i3-op": "tune"}),
    ], className="i3-form")]
    return _card(html, 'Title', [
        html.Div('Paragraph. Enter your text here.', className="i3-mute"),
        html.Div([_audio_block(html, dcc, "ch2f", 'Title', []), _audio_block(html, dcc, "c1", 'Title', []), _audio_block(html, dcc, "coil", 'Title', []), _audio_block(html, dcc, "sdr", 'Title', sdr_extra)], className="i3-audio-grid three"),
    ], "tall wide")



def timeline_panel(html):
    return _card(html, 'Title', [
        html.Div('Paragraph. Enter your text here.', className="i3-mute"),
        html.Div("No events yet", className="i3-timeline", **{"data-i3-timeline": "true"}),
    ])


def telemetry_panel(html):
    return _card(html, 'Title', [
        html.Pre(_live(html, "telemetry", 'Text', "json"), className="i3-details"),
    ], "tall")


def camera_panel(html):
    return _card(html, 'Title', [
        html.Div([html.Span('Text', className="i3-mute"), html.Img(className="i3-camera-preview", alt='Text', **{"data-i3-camera-preview": "true"})], className="i3-camera-frame"),
        _row(html, 'Label', "camera.state"),
        _row(html, 'Label', "camera.resolution"),
        _row(html, 'Label', "camera.fps", "number"),
        _row(html, 'Label', "camera.dropped_frames", "number"),
        _row(html, 'Label', "camera.tracking.confidence", "fraction"),
        _row(html, "Status", "camera.error"),
        html.Div('Paragraph. Enter your text here.', className="i3-notice"),
    ])


def parallax_header(html, title="Title"):
    """Scroll linked layered header: layers rise at 70, 55, 40 and 10 percent of the scroll."""
    return html.Section([
        html.Div([
            html.Div(className="parallax__black-line-overflow"),
            html.Div([
                html.Img(src="/assets/parallax/scroll-1.svg", alt="", className="parallax__layer-img", **{"data-parallax-layer": "1"}),
                html.Img(src="/assets/parallax/scroll-2.svg", alt="", className="parallax__layer-img", **{"data-parallax-layer": "2"}),
                html.Div(html.H2(title, className="parallax__title"), className="parallax__layer-title", **{"data-parallax-layer": "3"}),
                html.Img(src="/assets/parallax/scroll-4.svg", alt="", className="parallax__layer-img", **{"data-parallax-layer": "4"}),
            ], className="parallax__layers", **{"data-parallax-layers": "true"}),
            html.Div(className="parallax__fade"),
            html.Div(className="parallax__veil"),
        ], className="parallax__visuals"),
    ], className="parallax__header")


PILLAR_CARDS = [
    ("axial", 'Text', "/mtdi"), ("baseline", 'Text', "/mtdi"),
    ("transient", 'Text', "/mtdi"),
    ("compass", 'Text', "/mtdi"), ("audition", 'Text', "/mtdi"),
    ("signature", 'Text', "/mtdi"), ("page3", 'Text', "/page-3"),
]


def cards_track(html, dcc):
    """A scroll pinned horizontal track: cards rotate in, settle flat, rotate out."""
    cards = []
    for index, (key, label, href) in enumerate(PILLAR_CARDS):
        cards.append(html.Div(
            html.Div([
                html.Img(src=f"/assets/parallax/card-{key}.webp", alt=label, className="i3-rotate-img"),
                html.Div([html.Span(f"{index + 1:02d}", className="i3-rotate-index"), html.Span(label)], className="i3-rotate-caption"),
            ], className="i3-rotate-card", style={"zIndex": len(PILLAR_CARDS) - index}, **{"data-i3-card": str(index)}),
            className="i3-rotate-wrap"))
    return html.Section([
        html.Div([
            html.Div('Label', className="i3-eyebrow i3-rotate-eyebrow"),
            html.Div(cards, className="i3-rotate-track", **{"data-i3-track": "true"}),
            html.Div('Subtext', className="i3-rotate-hint"),
        ], className="i3-rotate-sticky"),
    ], className="i3-rotate", **{"data-i3-rotate": "true"})


def page(html, dcc):
    return html.Main([
        html.Div(className="i3-scrub-hero", **{"data-i3-scrub": "skyline", "data-i3-title": T("page3.hero_title"),
                                              "data-i3-tagline": T("page3.hero_tagline")}),
        html.Div([
        html.Header([
            html.Div(T("page3.eyebrow"), className="i3-eyebrow"),
            html.H1(T("page3.title")),
            html.P(T("page3.subtitle")),
        ]),
        html.Article([
        html.Section([
            html.H2('Heading 2'),
            html.P('Paragraph. Enter your text here.'),
            html.Div([html.Div([html.B("MTDI"), html.Span('Text')], className="i3-page3-definition"),
                      html.Div([html.B("TITLE"), html.Span('Text')], className="i3-page3-definition")], className="i3-page3-definitions"),
        ], className="i3-page3-section i3-page3-overview"),
        html.Section([
            html.Div([html.Div('Label', className="i3-eyebrow"), html.Div(_live(html, "fusion.condition", 'Text'), className="i3-condition"), html.Div([html.Div(_live(html, "fusion.interpretation", 'Text')), html.Div(_live(html, "fusion.evidence", ""))], className="i3-evidence")]),
            html.Div([html.Strong(_live(html, "fusion.confidence", "0 %", "percent")), html.Span('Text', className="i3-mute")], className="i3-confidence"),
        ], className="i3-summary i3-page3-summary"),
        html.Section([html.H2('Heading 2'), html.P('Paragraph. Enter your text here.'),
                      html.Div([_channel(html, "ch1", 'Title'), _channel(html, "ch2", 'Title'), _channel(html, "ch3", 'Title')], className="i3-channels three")], className="i3-page3-section"),
        html.Section([html.H2('Heading 2'), html.P('Paragraph. Enter your text here.'),
                      html.Div([signature_panel(html), vector_panel(html), axial_panel(html), confidence_panel(html)], className="i3-grid")], className="i3-page3-section"),
        html.Section([html.H2('Heading 2'), html.P('Paragraph. Enter your text here.'),
                      html.Div([baseline_panel(html, dcc), calibration_panel(html, dcc), transient_panel(html)], className="i3-grid")], className="i3-page3-section"),
        html.Section([html.H2('Heading 2'), html.P('Text'),
                      html.Div([audition_panel(html, dcc), timeline_panel(html), camera_panel(html), export_panel(html)], className="i3-grid")], className="i3-page3-section"),
        ], id="i3-page3-document", className="i3-page3-document"),
        html.Div(id="i3-performance", className="i3-performance"),
        ], className="i3-page-body i3-page-body-flat"),
    ], className="i3-page")


def export_panel(html):
    return _card(html, 'Title', [
        html.P('Paragraph. Enter your text here.'),
        html.A('Text', href="/download/studio-report.pdf", className="i3-btn"),
        html.A('Text', href="/api/export/session.json", className="i3-btn"),
        html.A('Text', href="/api/export/session.csv", className="i3-btn"),
        html.Button("Upload report to Notion", type="button", className="i3-btn", **{"data-i3-action": "cloud_report"}),
        html.Div('Text', className="i3-inline-result", **{"data-i3-cloud": "true"}),
    ])


def restructure_ch3(children, html):
    """Reorganise the CH3 sweep tab like the EM pages: readings and status first, then
    a two column band with the reading guide on the left and the sweep controls on the
    right, then the live charts."""
    items = list(children)
    def cls(c):
        return str(getattr(c, "className", "") or "")
    def cid(c):
        return str(getattr(c, "id", "") or "")
    def text(c):
        ch = getattr(c, "children", None)
        return ch if isinstance(ch, str) else ""
    action, guide, controls, head, stores, rest = [], [], [], [], [], []
    i = 0
    while i < len(items):
        c = items[i]
        c_cls, c_id = cls(c), cid(c)
        if "sweep3-sweep-action" in c_cls:
            action.append(c)
        elif "summary-panel" in c_cls:
            guide.append(c)
        elif "section-label" in c_cls and text(c).startswith("WHAT THE"):
            guide.append(c)
            if i + 1 < len(items) and "validation-subcopy" in cls(items[i + 1]):
                guide.append(items[i + 1]); i += 1
        elif "section-label" in c_cls and text(c) == "DEVICE":
            controls.append(c)
            if i + 1 < len(items) and cid(items[i + 1]) == "ch3-dev-strip":
                controls.append(items[i + 1]); i += 1
        elif "metric-row" in c_cls or "online-bar" in c_cls or c_id == "ch3-warn":
            head.append(c)
        elif "ch3-ctl-bar" in c_cls:
            controls.append(c)
        elif type(c).__name__ == "Store":
            stores.append(c)
        else:
            rest.append(c)
        i += 1
    for c in controls:
        if "ch3-ctl-bar" in cls(c):
            c.style = {**(getattr(c, "style", None) or {}), "marginTop": "0", "marginBottom": "12px"}
    band = html.Div([
        html.Div(guide, className="ch3-guide"),
        html.Div([html.Div('LABEL', className="section-label", style={"marginTop": "0"})] + controls, className="ch3-controls chart-card"),
    ], className="ch3-layout")
    return action + head + [band] + stores + rest


def _walk(component):
    yield component
    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk(child)
    elif children is not None and not isinstance(children, (str, int, float, bool)):
        yield from _walk(children)


def centralize_css(index):
    """Collect presentation colour primitives in one palette declaration."""
    palette = {}
    colour = re.compile(r'url\([^)]*\)|#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)')

    def token(match):
        value = match.group()
        if value.startswith('url('):
            return value
        key = palette.setdefault(value, f'--i3-palette-{len(palette)}')
        return f'var({key})'

    def stylesheet(match):
        css = re.sub(r'\{([^{}]*)\}', lambda block: '{' + colour.sub(token, block[1]) + '}', match[1])
        return '<style>' + css + '</style>'

    index = re.sub(r'<style>([\s\S]*?)</style>', stylesheet, index)
    variables = ''.join(f'{key}:{value};' for value, key in palette.items())
    return index.replace('</head>', '<style>:root{' + variables + '}</style></head>', 1)


def install(ns, runtime):
    html, dcc, app = ns["html"], ns["dcc"], ns["app"]
    # The D4 analysis engine used to be dressed as MTDI pillar 00. It is not a pillar:
    # MTDI judges the instrument, D4 interprets the field. It belongs here, beside the
    # transient lock and the rest of the page-3 interpretation work.
    def page3_page():
        node = page(html, dcc)
        body = next((n for n in _walk(node)
                     if "i3-page-body" in str(getattr(n, "className", "") or "")), None)
        if body is None:
            return node
        document = next((n for n in _walk(node) if getattr(n, "id", None) == "i3-page3-document"), None)
        children = list(document.children if document is not None else body.children)
        section = html.Div([
            html.H2('Heading 2'),
            ns["d4_engine_section"](),
        ], className="i3-d4-host i3-page3-section")
        if document is not None:
            document.children = children + [section]
        else:
            body.children = children + [section]
        return node

    ns["PAGES"]["/page-3"] = page3_page
    tools = html.Div([
        html.Button("◉", id="i3-camera-toggle", type="button", className="i3-tool", title="Enable camera (hand tracking). Shortcut C", **{"data-i3-action": "camera", "aria-pressed": "false", "aria-label": 'Text'}),
        html.Button("⇅", id="i3-mode-toggle", type="button", className="i3-tool", title='Title', **{"data-i3-action": "mode_toggle", "aria-label": 'Text'}),
        html.Button("◍", id="i3-agent-toggle", type="button", className="i3-tool", title='Title', **{"data-i3-action": "agent", "aria-pressed": "false", "aria-label": 'Text'}),
        html.A('Text', id="i3-https-link", href="#", className="i3-tool i3-tool-text", hidden=True),
        html.Span('Text', id="i3-stream-state", hidden=True),
    ], className="i3-header-tools")
    toast = html.Div("", id="i3-control-result", className="i3-toast", role="status")
    def pill(key, label):
        return html.Div([html.Span(className="pill-dot pill-off"), html.Span(label, className="pill-key"), html.Span("…", className="pill-val")], className="i3-island-pill pill-" + key)
    orb = html.Div([
        html.Div([
            html.Canvas(id="i3-orb-canvas", width=420, height=420),
            html.Div(id="i3-orb-robot", className="i3-orb-robot", hidden=True),
            html.Div([html.Div("NVTRA", className="i3-orb-name"), html.Div("Press ◍ or N to start listening", id="i3-orb-state", className="i3-orb-state")], className="i3-island-head"),
            html.Div([html.I() for _ in range(9)], id="i3-voice-bars", className="i3-voice-bars", **{"aria-hidden": "true"}),
            html.Div([pill("mtdi", "MTDI"), pill("c1", 'LABEL'), pill("ef", 'LABEL'), pill("ch3", "Channel 3")], className="i3-island-pills"),
        ], className="i3-island-top"),
        html.Div("", id="i3-orb-text", className="i3-orb-text"),
        html.Form([dcc.Input(id="i3-orb-input", type="text", placeholder='Enter your text here', autoComplete="off", debounce=False), html.Button("Send", type="submit", className="i3-btn i3-primary")], id="i3-orb-form", className="i3-orb-form"),
        html.Div([
            html.Select([html.Option('Text', value="")], className="i3-orb-engine", title='Title', **{"data-i3-engine": "true", "aria-label": 'Text'}),
            html.Button("■ Stop", type="button", className="i3-btn i3-orb-stop", title='Title', **{"data-i3-action": "agent_stop"}),
        ], className="i3-orb-tools"),
    ], id="i3-orb", className="i3-island collapsed")
    for node in _walk(app.layout):
        if getattr(node, "className", None) == "site-header":
            node.children = list(node.children) + [tools]
    for node in _walk(app.layout):
        if getattr(node, "id", None) == "nav-glass":
            children = list(node.children)
            entry = [dcc.Link(html.Button([html.Span(className="nav-dot"), T("nav.page3")], className="nav-glass-btn", id="nav-page3"), href="/page-3", style={"textDecoration": "none"}), html.Div(className="nav-glass-sep")]
            position = next((i for i, child in enumerate(children) if getattr(getattr(child, "children", None), "id", None) == "nav-settings"), len(children))
            node.children = children[:position] + entry + children[position:]
    children = list(app.layout.children)
    children.append(toast)
    children.append(orb)
    app.layout.children = children
    factories = {
        "validation_chamber_section": lambda: [axial_panel(html), confidence_panel(html)],
        "environmental_intelligence_section": lambda: [baseline_panel(html, dcc), transient_panel(html)],
        "i3_field_section": lambda: [vector_panel(html), audition_panel(html, dcc)],
        "nvtra_field_section": lambda: [signature_panel(html)],
        "settings_page": lambda: [calibration_panel(html, dcc), camera_panel(html), telemetry_panel(html), timeline_panel(html), export_panel(html)],
    }
    replacements = {}
    for name, addition in factories.items():
        original = ns[name]
        def extended(original=original, addition=addition):
            node = original()
            node.children = list(node.children) + [html.Div(addition(), className="i3-grid i3-pillars")]
            for item in _walk(node):
                if getattr(item, "id", None) == "export-btn":
                    item.children = "DOWNLOAD LOCAL PDF"
            return node
        replacements[original] = extended
        ns[name] = extended
    original_ch3_body = ns["ch3_sweep_body"]
    def ch3_body_restructured():
        return restructure_ch3(original_ch3_body(), html)
    ns["ch3_sweep_body"] = ch3_body_restructured
    ns["PAGES"]["/settings"] = ns["settings_page"]
    ns["MTDI_ORBIT_PILLARS"][:] = [(*item[:6], replacements.get(item[6], item[6])) for item in ns["MTDI_ORBIT_PILLARS"]]
    for node in _walk(app.layout):
        if getattr(node, "id", None) == "mobile-mode-probe":
            node.disabled = True
        if getattr(node, "id", None) in ("header-interval", "nvtra-interval"):
            node.disabled = True
    index = app.index_string
    index = re.sub(r'<script>\s*/\* Phones always receive[\s\S]*?</script>', '', index)
    index = index.replace('if(window.__i3HandVisionRunning){', 'if(window.__i3HandVisionRunning){', 1)
    index = index.replace("if(!canvas||!/Macintosh|Mac OS X/.test(navigator.userAgent||''))return;", "if(!canvas)return;canvas.__i3LegacyHandControls=controls;return;")
    index = index.replace("var FRAME_120=1000/(COARSE_DEVICE?60:120);", "var FRAME_120=1000/60;")
    # Sharper landmarks: a 720p feed gives the full hand model twice the pixels per finger.
    index = index.replace("getUserMedia({video:{facingMode:'user',width:{ideal:640},height:{ideal:480}},audio:false})", "getUserMedia({video:{facingMode:'user',width:{ideal:640},height:{ideal:480},frameRate:{ideal:30}},audio:false})")
    index = index.replace("      window.__i3HandVisionRunning=true;\n",
        "      window.__i3HandVisionRunning=true;\n      window.__i3StopHandVision=function(){window.__i3HandVisionRunning=false;window.__i3HandVisionStarting=false;try{hands.close();}catch(e){}try{stream.getTracks().forEach(function(t){t.stop();});}catch(e){}try{video.pause();video.srcObject=null;}catch(e){}try{preview.remove();}catch(e){}handVisionStatus('CAMERA OFF · INERTIA CONTINUES','');if(window.__i3Physics)window.__i3Physics.sample({position:[0,0,0],timestamp:performance.now()/1000,confidence:0});};\n")
    index = index.replace("        if(!sets.length){lastPalmX=null;twoHandReference=null;",
        "        if(!sets.length){lastPalmX=null;twoHandReference=null;if(window.__i3Physics)window.__i3Physics.sample({position:[0,0,0],timestamp:performance.now()/1000,confidence:0});if(window.__i3HandGesture)window.__i3HandGesture([],overlay);")
    index = index.replace("        var hand=sets[0],palmX=(hand[0].x+hand[5].x+hand[9].x+hand[13].x+hand[17].x)/5;",
        "        if(window.__i3HandGesture&&window.__i3HandGesture(sets,overlay,results.multiHandedness||[]))return;\n        var hand=sets[0],palmX=(hand[0].x+hand[5].x+hand[9].x+hand[13].x+hand[17].x)/5;")
    index = index.replace("if(Math.abs(visibleDx)>.002)window.__i3HandControls.rotate(visibleDx);",
                          "if(!window.__i3Physics&&Math.abs(visibleDx)>.002)window.__i3HandControls.rotate(visibleDx);")
    index = index.replace("        lastPalmX=palmX;\n",
        "        lastPalmX=palmX;\n        if(window.__i3Physics&&window.__i3PhysicsHold&&window.__i3PhysicsHold()){var centres=sets.map(function(h){return [(h[0].x+h[5].x+h[9].x+h[13].x+h[17].x)/5,(h[0].y+h[5].y+h[9].y+h[13].y+h[17].y)/5];});var yawHand=centres[0],pitchHand=centres[0];if(centres.length>=2){centres.sort(function(a,b){return a[0]-b[0];});yawHand=centres[0];pitchHand=centres[0].concat([]);pitchHand[1]=(centres[0][1]+centres[1][1])/2;}window.__i3Physics.sample({position:[yawHand[0],pitchHand[1],0],timestamp:performance.now()/1000,confidence:1,hands:centres.length});}\n")
    index = index.replace("await loadExternalScript('https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js');", "await loadExternalScript('/assets/mediapipe/hands.js');")
    index = index.replace("var hands=new Hands({locateFile:function(file){return 'https://cdn.jsdelivr.net/npm/@mediapipe/hands/'+file;}});", "var hands=new Hands({locateFile:function(file){return '/assets/mediapipe/'+file+'?v=" + str(ns['APP_VERSION']) + "';}});")
    index = index.replace("hands.setOptions({maxNumHands:2,modelComplexity:0,minDetectionConfidence:.55,minTrackingConfidence:.55});", "window.__i3HandOptions={maxNumHands:2,modelComplexity:0,minDetectionConfidence:.55,minTrackingConfidence:.6,selfieMode:false};window.__i3HandModelUrl=function(file){return '/assets/mediapipe/'+file+'?v=" + str(ns['APP_VERSION']) + "';};hands.setOptions(window.__i3HandOptions);")
    index = index.replace("if(busy||video.readyState<2||now-lastSent<66)return;", "if(busy||video.readyState<2||now-lastSent<((navigator.hardwareConcurrency||4)>=8?33:50))return;")
    # Hand zoom uses the same limits as the trackpad so the globe and constellation never leave their frame.
    index = index.replace("zoom:function(handScale){zoom=Math.max(.65,Math.min(1.40,handScale));render();},",
                          "zoom:function(handScale){var h=Math.max(.58,Math.min(1.65,handScale));zoom=.72+(h-.58)/(1.65-.58)*(1.38-.72);render();},")
    index = index.replace("if(e.ctrlKey)zoom=Math.max(.84,Math.min(1.12,zoom*Math.exp(-dy*.001)));", "if(e.ctrlKey)zoom=Math.max(.72,Math.min(1.38,zoom*Math.exp(-dy*.001)));")
    index = index.replace("zoom=Math.max(.84,Math.min(1.12,touchGesture.zoom*Math.pow(Math.hypot(dx,dy)/Math.max(8,touchGesture.d),.72)));", "zoom=Math.max(.72,Math.min(1.38,touchGesture.zoom*Math.pow(Math.hypot(dx,dy)/Math.max(8,touchGesture.d),.72)));")
    index = index.replace("zoom:function(handScale){zoom=Math.max(.65,Math.min(1.35,handScale));render();},",
                          "zoom:function(handScale){var h=Math.max(.58,Math.min(1.65,handScale));zoom=.72+(h-.58)/(1.65-.58)*(1.2-.72);render();},")
    index = index.replace("zoom=Math.max(.84,Math.min(1.08,zoom*Math.exp(-rawY*.003)));", "zoom=Math.max(.72,Math.min(1.2,zoom*Math.exp(-rawY*.003)));")
    # Controls must follow the page: refresh the target before every zoom so it never points at a canvas that was replaced.
    index = index.replace("if(window.__i3HandControls&&window.__i3HandControls.zoom)window.__i3HandControls.zoom(smoothed);", "if(window.__i3HoldActive&&window.__i3HoldActive()&&window.__i3HandControls&&window.__i3HandControls.zoom)window.__i3HandControls.zoom(smoothed);")
    index = index.replace("  function bootPageShader(){", "  window.__i3BootPageShader=function(){bootPageShader();};\n  function bootPageShader(){", 1)
    index = index.replace("  async function startMacHandVision(canvas,controls){", "  window.__i3StartHandVision=function(c,k){return startMacHandVision(c,k);};\n  async function startMacHandVision(canvas,controls){")
    index = index.replace("  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',boot);}" + chr(10) + "  else{boot();}", "  window.__i3ReadyPromise.then(boot);")
    index = index.replace("rotate:function(screenDx){yaw+=screenDx*3.8;", "physics:function(delta){yaw+=delta[1];pitch+=delta[0];roll+=delta[2];render();},rotate:function(screenDx){yaw+=screenDx*3.8;")
    index = index.replace("rotate:function(screenDx){yaw+=screenDx*240;", "physics:function(delta){yaw+=delta[1]*57.2958;pitch+=delta[0]*57.2958;roll+=delta[2]*57.2958;render();},rotate:function(screenDx){yaw+=screenDx*240;")
    index = index.replace("exportLink.textContent='EXPORT PDF + NOTION';", "exportLink.textContent='DOWNLOAD LOCAL PDF';")
    # Eager loading lists every optional chunk; keep only the ones these pages use so a
    # cold load does not fetch MathJax, date pickers or tables that never render.
    bundle_sizes = {}
    size_lock = __import__("threading").Lock()

    def measure_bundles(urls):
        client = app.server.test_client()
        for url in urls:
            if url in bundle_sizes:
                continue
            try:
                response = client.get(url, headers={"Accept-Encoding": "gzip"})
                size = len(response.get_data()) if response.status_code == 200 else 0
            except Exception:
                size = 0
            with size_lock:
                bundle_sizes[url] = size
    unused_chunks = re.compile(r'<script src="/_dash-component-suites/dash/(?:dcc/async-(?:datepicker|highlight|markdown|mathjax|upload)|dash_table/async-(?:export|table|highlight))[^"]*"></script>\s*')
    original_interpolate = app.interpolate_index

    def interpolate_without_unused(**kwargs):
        scripts = unused_chunks.sub("", kwargs.get("scripts", ""))
        urls = re.findall(r'<script src="([^"]+)"', scripts)
        missing = [url.split("?")[0] for url in urls if url.split("?")[0] not in bundle_sizes]
        if missing:
            # The loader cannot report byte progress accurately until it knows every
            # compressed module size. The warm-up below keeps this measurement off the
            # normal request path after startup.
            measure_bundles(missing)
        with size_lock:
            known = {url: size for url, size in bundle_sizes.items() if size}
        # Real compressed sizes drive the byte accurate download bar in the loader.
        kwargs["scripts"] = '<script>window.I3_BUNDLES=' + json.dumps(known) + '</script>' + scripts
        return original_interpolate(**kwargs)
    # Warm the size table and the gzip cache so the first browser never pays for it.
    def warm():
        import time as _time
        _time.sleep(2)
        try:
            app.server.test_client().get("/")
        except Exception:
            pass
    __import__("threading").Thread(target=warm, name="i3-warm", daemon=True).start()
    app.interpolate_index = interpolate_without_unused
    index = index.replace('<head>', '<head><script>' + HEAD_JS + '</script>', 1)
    index = index.replace('</head>', '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>' + CSS + '</style></head>', 1)
    index = re.sub(r'</head>\s*<body\b[^>]*>', lambda match: match[0] + boot_html(), index, count=1)
    index = index.replace('</body>', '<script>' + _gsap() + '</script><script>' + JS.replace('__I3_VERSION__', str(ns['APP_VERSION'])) + '</script></body>')
    app.index_string = centralize_css(index)
    app.server.config["I3_UI_RUNTIME"] = runtime


def _gsap():
    return zlib.decompress(base64.b64decode(GSAP_B64)).decode("utf8")

GSAP_B64 = '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'

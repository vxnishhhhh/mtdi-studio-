"""Flask server, security headers, gzip, Spline and NVTRA asset routes, Dash app, index and layout."""
from ._shared import inherit
inherit(globals(), 'common', 'sensors', 'intelligence', 'system', 'tokens', 'theme', 'browser')
from .content import T  # studio words (S1-06): studio/content/default.json


server = Flask(__name__)
server.secret_key = os.environ.get("STUDIO_SECRET_KEY") or secrets.token_hex(32)

_SPLINE_RUNTIME_BUNDLE_URL = (
    "https://unpkg.com/@splinetool/runtime@1.10.94/build/runtime.js"
)
_spline_runtime_bundle = None
_spline_runtime_lock = threading.Lock()
_SPLINE_ROBOT_SCENE_URL = (
    "https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode"
)
_spline_robot_scene = None
_spline_robot_lock = threading.Lock()
_spline_runtime_gz = None


# Circuit-board 3D: three.js and the scene are vendored in studio/vendor and served
# here rather than from assets/, because Dash loads every .js under assets/ on every
# page and three.js is 636 KB. This way three.js is fetched only when a board canvas
# is actually on screen, and it is same-origin so offline mode keeps working.
_VENDOR_DIR = Path(__file__).resolve().parent / "vendor"
_vendor_cache = {}
_vendor_lock = threading.Lock()


def _vendor_js(name):
    """Serve a vendored script, gzipped when the client accepts it."""
    if name not in _vendor_cache:
        with _vendor_lock:
            if name not in _vendor_cache:
                path = _VENDOR_DIR / name
                if not path.is_file():
                    return Response("console.error('%s missing');" % name,
                                    mimetype="text/javascript", status=404,
                                    headers={"Cache-Control": "no-store"})
                raw = path.read_bytes()
                _vendor_cache[name] = (raw, gzip.compress(raw, compresslevel=6))
    raw, packed = _vendor_cache[name]
    if "gzip" in request.headers.get("Accept-Encoding", "").lower():
        return Response(packed, mimetype="text/javascript",
                        headers={"Cache-Control": "public, max-age=604800",
                                 "Content-Encoding": "gzip", "Vary": "Accept-Encoding"})
    return Response(raw, mimetype="text/javascript",
                    headers={"Cache-Control": "public, max-age=604800"})


@server.get("/_i3/three.js")
def _three_js():
    return _vendor_js("three.min.js")


@server.get("/_i3/boards.js")
def _boards_js():
    return _vendor_js("boards.js")


@server.get("/_i3/spline-runtime.js")
def _spline_runtime():
    """Same-origin cached Spline canvas runtime for reliable module loading."""
    global _spline_runtime_bundle
    if _spline_runtime_bundle is None:
        with _spline_runtime_lock:
            if _spline_runtime_bundle is None:
                try:
                    with urllib.request.urlopen(_SPLINE_RUNTIME_BUNDLE_URL, timeout=20) as response:
                        raw = response.read()
                    # The runtime pulls its modelling wasm (process.js + process.wasm) from unpkg,
                    # which the CSP blocks; point it at the same-origin copies served below.
                    raw = raw.replace(b'"https://unpkg.com/@splinetool/modelling-wasm@1.10.94/build"', b'"/_i3"')
                    _spline_runtime_bundle = raw
                except Exception as exc:
                    LOG.warning("Spline canvas runtime unavailable: %s", exc)
                    return Response(
                        "console.error('NVTRA robot runtime unavailable');",
                        mimetype="text/javascript", status=503,
                        headers={"Cache-Control":"no-store"},
                    )
    global _spline_runtime_gz
    if "gzip" in request.headers.get("Accept-Encoding", "").lower():
        if _spline_runtime_gz is None:
            _spline_runtime_gz = gzip.compress(_spline_runtime_bundle, compresslevel=6)
        return Response(
            _spline_runtime_gz, mimetype="text/javascript",
            headers={"Cache-Control":"public, max-age=604800", "Content-Encoding":"gzip", "Vary":"Accept-Encoding"},
        )
    return Response(
        _spline_runtime_bundle, mimetype="text/javascript",
        headers={"Cache-Control":"public, max-age=604800"},
    )


# Every helper the Spline runtime may fetch at load time (modelling/boolean/navmesh wasm, the
# UI wasm and the Draco decoders). Served same-origin under /_i3/<file> so the CSP stays closed;
# each is fetched once from its CDN and kept in memory.
_SPLINE_HELPERS = {
    "process.js": "https://unpkg.com/@splinetool/modelling-wasm@1.10.94/build/process.js",
    "process.wasm": "https://unpkg.com/@splinetool/modelling-wasm@1.10.94/build/process.wasm",
    "boolean.js": "https://unpkg.com/@splinetool/boolean-wasm@1.10.94/build/boolean.js",
    "boolean.wasm": "https://unpkg.com/@splinetool/boolean-wasm@1.10.94/build/boolean.wasm",
    "navmesh.js": "https://unpkg.com/@splinetool/navmesh-wasm@1.10.94/build/navmesh.js",
    "navmesh.wasm": "https://unpkg.com/@splinetool/navmesh-wasm@1.10.94/build/navmesh.wasm",
    "ui.wasm": "https://unpkg.com/@splinetool/ui-wasm@1.10.94/build/ui.wasm",
    "draco_decoder.js": "https://www.gstatic.com/draco/versioned/decoders/1.5.2/draco_decoder.js",
    "draco_decoder.wasm": "https://www.gstatic.com/draco/versioned/decoders/1.5.2/draco_decoder.wasm",
    "draco_wasm_wrapper.js": "https://www.gstatic.com/draco/versioned/decoders/1.5.2/draco_wasm_wrapper.js",
}
_spline_helper_files = {}


_gzip_cache = {}


def _maybe_gzip(key, payload, mimetype, headers):
    """Serve cached bytes gzipped when the browser accepts it. A serverless function
    response is capped at 4.5 MB, and the Spline runtime, wasm helpers and scene all
    shrink well below that once compressed."""
    headers = dict(headers)
    if "gzip" in request.headers.get("Accept-Encoding", "").lower():
        packed = _gzip_cache.get(key)
        if packed is None:
            packed = _gzip_cache[key] = gzip.compress(payload, compresslevel=6)
        headers.update({"Content-Encoding": "gzip", "Vary": "Accept-Encoding"})
        return Response(packed, mimetype=mimetype, headers=headers)
    return Response(payload, mimetype=mimetype, headers=headers)


@server.get("/_i3/<name>")
def _spline_helper(name):
    source = _SPLINE_HELPERS.get(name)
    if not source:
        return Response("", status=404)
    if name not in _spline_helper_files:
        with _spline_runtime_lock:
            if name not in _spline_helper_files:
                try:
                    with urllib.request.urlopen(source, timeout=25) as response:
                        _spline_helper_files[name] = response.read()
                except Exception as exc:
                    LOG.warning("Spline helper %s unavailable: %s", name, exc)
                    return Response("", status=503, headers={"Cache-Control": "no-store"})
    mimetype = "application/wasm" if name.endswith(".wasm") else "text/javascript"
    return _maybe_gzip("helper:" + name, _spline_helper_files[name], mimetype,
                       {"Cache-Control": "public, max-age=604800"})


@server.get("/_i3/nvtra-loader.js")
def _nvtra_loader_module():
    """External module bootstrap avoids browsers blocking an inline module."""
    return Response(
        'import { Application } from "/_i3/spline-runtime.js";\n'
        'window.__NvtraSplineApplication = Application;\n'
        'window.dispatchEvent(new Event("nvtra-spline-runtime-ready"));\n',
        mimetype="text/javascript",
        headers={"Cache-Control":"no-cache"},
    )


@server.get("/_i3/nvtra-robot.splinecode")
def _spline_robot_asset():
    """Same-origin cached NVTRA robot scene, avoiding client-side CDN failures."""
    global _spline_robot_scene
    if _spline_robot_scene is None:
        with _spline_robot_lock:
            if _spline_robot_scene is None:
                try:
                    with urllib.request.urlopen(_SPLINE_ROBOT_SCENE_URL, timeout=25) as response:
                        _spline_robot_scene = response.read()
                except Exception as exc:
                    LOG.warning("Spline robot scene unavailable: %s", exc)
                    return Response(
                        json.dumps({"error":"NVTRA robot scene unavailable"}),
                        mimetype="application/json", status=503,
                        headers={"Cache-Control":"no-store"},
                    )
    return _maybe_gzip("robot-scene", _spline_robot_scene, "application/json",
                       {"Cache-Control": "public, max-age=86400"})


@server.get("/_i3/natural-earth-land.json")
def _natural_earth_land():
    """Serve the embedded globe geometry with stable same-origin caching."""
    payload = gzip.decompress(base64.b64decode(_NATURAL_EARTH_LAND_GZIP_B64))
    return Response(payload, mimetype="application/json", headers={
        "Cache-Control": "public, max-age=31536000, immutable",
    })


@server.get("/manifest.webmanifest")
def _web_app_manifest():
    """Installed to a home screen, the studio is a landscape app (Android locks it; iOS
    ignores the field, and the /phone stage turns the view instead)."""
    payload = {
        "name": "MTDI Studio", "short_name": "MTDI Studio",
        "start_url": "/", "scope": "/", "display": "standalone",
        "orientation": "landscape", "background_color": "#07090f",
        "theme_color": "#07090f",
    }
    return Response(
        json.dumps(payload, separators=(",", ":")),
        mimetype="application/manifest+json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


# The phone stage. The studio runs in the iframe as an ordinary 1180 px desktop window; this
# page only fits that window to the glass: scaled onto the long edge, and turned a quarter
# turn when the phone is upright so the view stays landscape. The iframe may use the camera,
# microphone and motion sensors the studio already asks for (same origin, Permissions-Policy).
PHONE_STAGE_WIDTH = 1180
PHONE_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#07090f">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="/manifest.webmanifest">
<title>MTDI Studio</title>
<style>
html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#07090f;overscroll-behavior:none}
#stage{position:fixed;top:0;left:0;border:0;display:block;transform-origin:0 0;background:#07090f}
</style>
</head>
<body>
<iframe id="stage" title="MTDI Studio" src="/?stage=phone"
  allow="camera; microphone; fullscreen; accelerometer; gyroscope; magnetometer; clipboard-write; autoplay"></iframe>
<script>
(function(){
  var STAGE=__STAGE__, frame=document.getElementById('stage'), rotated=false;
  function fit(){
    var vv=window.visualViewport, w=vv?vv.width:innerWidth, h=vv?vv.height:innerHeight;
    var portrait=h>w, lng=Math.max(w,h), shrt=Math.min(w,h), s=lng/STAGE;
    frame.style.width=STAGE+'px';
    frame.style.height=(shrt/s).toFixed(2)+'px';
    /* Upright: the stage's top edge goes to the right of the glass, which reads correctly
       once the phone is turned to landscape - the view never changes, only the glass. */
    frame.style.transform=portrait?'translate('+w+'px,0) rotate(90deg) scale('+s+')':'scale('+s+')';
    document.documentElement.classList.toggle('portrait',portrait);
    rotated=portrait;
    /* Rotated, the browser cannot turn a finger drag into a scroll (it pans along the glass,
       not the stage), so the stage scrolls itself (below) and the browser's own panning is
       switched off there. Unrotated, native scrolling works and is left alone. */
    try{var de=frame.contentDocument.documentElement;de.style.touchAction=portrait?'none':'';de.classList.toggle('stage-turned',portrait);}catch(e){}
    /* Device pixels per stage CSS pixel; the studio caps its canvases to this (max 2). */
    window.__i3StageDPR=(window.devicePixelRatio||1)*s;
  }

  /* Scrolling a rotated stage. Touch coordinates inside the frame are already in the stage's
     own axes, so a drag scrolls the nearest scrollable box under the finger along the stage's
     axis, and keeps gliding after the finger lifts. Sliders and text fields keep every drag;
     drag-to-rotate views (3D boards, the globe, 3D charts) keep a sideways drag and give an
     up/down drag to the page. Flat charts do not pan, so a drag over one scrolls the page and
     a tap still reads. */
  function attachTouch(){
    var w=frame.contentWindow, d=frame.contentDocument;
    if(!w||!d||w.__i3StageTouch||!d.documentElement)return;
    try{if(w.location.search.indexOf('stage=phone')<0)return;}catch(e){return;}   /* not the blank first page */
    w.__i3StageTouch=true;
    d.documentElement.style.touchAction=rotated?'none':'';
    d.documentElement.classList.toggle('stage-turned',rotated);   /* every box, see theme.py */
    var drag=null, vx=0, vy=0, glide=0;
    /* Controls own every drag. Drag-to-rotate views own a sideways drag only: an up/down drag
       scrolls the page, and the view does not see it (same rule as their pan-y on the
       unrotated stage). */
    var OWN='.rc-slider,input,textarea,select,[contenteditable]';
    var ROTATE='#nvtra-spline-canvas,#home-module-globe,.instrument-constellation-canvas,.i3-lunar-canvas,'+
               '.i3-vector,.i3-sc-canvas,.i3-sc-boards,.i3-tab-board canvas,.js-plotly-plot canvas,.gl-container';
    function own(el){
      for(var n=el;n&&n.nodeType===1&&n!==d.documentElement&&n!==d.body;n=n.parentElement){
        if(n.matches(OWN))return true;
      }
      return false;
    }
    function hush(e){if(drag&&drag.hush)e.stopPropagation();}
    w.addEventListener('pointermove',function(e){if(e.pointerType==='touch')hush(e);},{capture:true,passive:true});
    function scroller(el,vertical){
      for(var n=el;n&&n.nodeType===1&&n!==d.documentElement&&n!==d.body;n=n.parentElement){
        var s=w.getComputedStyle(n);
        if(vertical&&/auto|scroll/.test(s.overflowY)&&n.scrollHeight>n.clientHeight+1)return n;
        if(!vertical&&/auto|scroll/.test(s.overflowX)&&n.scrollWidth>n.clientWidth+1)return n;
      }
      return d.scrollingElement||d.documentElement;
    }
    w.addEventListener('touchstart',function(e){
      w.cancelAnimationFrame(glide);
      drag=null;
      if(!rotated||e.touches.length!==1)return;
      /* A control keeps its drags, except that a text box that has overflowed scrolls itself
         up and down (nothing in the turned stage pans natively, see theme.py). */
      var box=null;
      if(own(e.target)){
        box=e.target.closest&&e.target.closest('textarea,[contenteditable]');
        if(!box||box.scrollHeight<=box.clientHeight+1)return;
      }
      var t=e.touches[0];
      drag={x:t.clientX,y:t.clientY,t:e.timeStamp,target:e.target,el:null,vertical:true,box:box,
            rotates:!!(e.target.closest&&e.target.closest(ROTATE)),hush:false};
      vx=vy=0;
    },{capture:true,passive:true});
    w.addEventListener('touchmove',function(e){
      if(!drag||e.touches.length!==1)return;
      var t=e.touches[0], dx=drag.x-t.clientX, dy=drag.y-t.clientY, now=e.timeStamp;
      if(!drag.el){
        if(Math.abs(dx)+Math.abs(dy)<8)return;          /* still a tap */
        drag.vertical=Math.abs(dy)>=Math.abs(dx);
        if(drag.rotates&&!drag.vertical){drag=null;return;}   /* sideways on a 3D view: it rotates */
        if(drag.box&&!drag.vertical){drag=null;return;}       /* sideways in a text box: the box's own (select, caret) */
        drag.hush=drag.rotates;                          /* up/down on a 3D view: the page scrolls */
        drag.el=drag.box||scroller(drag.target,drag.vertical);
      }
      hush(e);
      if(drag.vertical)dx=0;else dy=0;
      drag.el.scrollBy(dx,dy);
      var dt=Math.max(1,now-drag.t);
      vx=0.8*dx/dt+0.2*vx; vy=0.8*dy/dt+0.2*vy;
      drag.x=t.clientX; drag.y=t.clientY; drag.t=now;
    },{capture:true,passive:true});
    /* Speed is measured from the touch events' own times, not from when a busy page got to
       them, so a glide is not lost while the studio is drawing. */
    function release(e){
      if(!drag||!drag.el){drag=null;return;}
      var el=drag.el, last=w.performance.now();
      if(e.timeStamp-drag.t>90)vx=vy=0;                  /* the finger stopped before lifting */
      drag=null;
      (function step(now){
        var dt=Math.max(1,now-last); last=now;
        var k=Math.pow(0.93,dt/16); vx*=k; vy*=k;   /* about as far as the browser glides unturned */
        if(Math.abs(vx)<0.02&&Math.abs(vy)<0.02)return;
        el.scrollBy(vx*dt,vy*dt);
        glide=w.requestAnimationFrame(step);
      })(last);
    }
    w.addEventListener('touchend',release,{capture:true,passive:true});
    w.addEventListener('touchcancel',release,{capture:true,passive:true});
  }
  frame.addEventListener('load',function(){attachTouch();fit();});
  /* The studio's intro is on screen before the frame's load event (which waits for every
     script), so attach as soon as the real document exists, and again after any reload. */
  setInterval(attachTouch,400);

  fit();
  addEventListener('resize',fit,{passive:true});
  if(window.visualViewport)visualViewport.addEventListener('resize',fit,{passive:true});
  addEventListener('orientationchange',function(){setTimeout(fit,250);},{passive:true});
  /* A real lock where the browser allows one (installed app, fullscreen on Android). */
  try{var o=screen.orientation;if(o&&o.lock){var p=o.lock('landscape');if(p&&p.catch)p.catch(function(){});}}catch(e){}
})();
</script>
</body>
</html>
""".replace("__STAGE__", str(PHONE_STAGE_WIDTH))


@server.get("/phone")
def _phone_stage():
    return Response(PHONE_SHELL, mimetype="text/html", headers={"Cache-Control": "no-store"})


@server.get("/api/system")
def _system_api():
    """Return only measured host telemetry, with explicit readiness and freshness."""
    with sys_lock:
        current = dict(sys_data)
    ready = current.get("last_rx") is not None
    temperature_ready = ready and bool(current.get("temperature_available"))
    payload = {
        "ready": ready,
        "sampled_at_unix": current.get("last_rx") if ready else None,
        "freshness_seconds": round(max(0.0, time.time() - current["last_rx"]), 3)
                             if ready else None,
        "source": current.get("telemetry_source") if ready else "starting",
        "host_model": current.get("host_model") if ready else None,
        "single_board": bool(current.get("single_board")) if ready else False,
        "error": current.get("telemetry_error"),
        "cpu": {
            "usage_percent": current.get("cpu_usage") if ready else None,
            "temperature_c": current.get("cpu_temp") if temperature_ready else None,
            "temperature_available": temperature_ready,
        },
        "memory": {
            "used_mb": current.get("ram_used_mb") if ready else None,
            "total_mb": current.get("ram_total_mb") if ready else None,
            "percent": current.get("ram_pct") if ready else None,
        },
        "disk": {
            "used_gb": current.get("disk_used_gb") if ready else None,
            "total_gb": current.get("disk_total_gb") if ready else None,
            "percent": current.get("disk_pct") if ready else None,
        },
        "uptime": current.get("uptime_str") if ready else None,
        "load_average": [
            current.get("load_1"), current.get("load_5"), current.get("load_15")
        ] if ready else None,
        "process_rss_mb": current.get("py_mem_mb") if ready else None,
        "app_version": APP_VERSION,
    }
    return Response(
        json.dumps(payload, separators=(",", ":")), mimetype="application/json",
        headers={"Cache-Control": "no-store", "X-Studio-Data": "measured-host-only"},
    )


server.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Strict",
)
# ── Security hardening ──
_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob: https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline'; "
    "font-src 'self' data:; "
    "img-src 'self' data: blob:; "
    "media-src 'self' data: blob:; "
    "connect-src 'self' https://cdn.jsdelivr.net; "
    "worker-src 'self' blob: https://cdn.jsdelivr.net; "
    "object-src 'none'; base-uri 'self'; frame-ancestors 'self'"
)


def hash_password(password, iterations=310_000):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def _password_matches(password, encoded):
    try:
        scheme, count, salt_hex, digest_hex = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"),
            bytes.fromhex(salt_hex), int(count),
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except Exception:
        LOG.warning("Invalid STUDIO_AUTH_PASSWORD_HASH format")
        return False


# ── authentication throttle ───────────────────────────────────────────────────
# The credential checks below are sound - PBKDF2 at 310k iterations and
# hmac.compare_digest throughout - but nothing limited how many attempts a client
# could make. On a LAN, and especially behind the public HTTPS tunnel, an attacker
# could try access tokens or Basic passwords as fast as this host would answer. The
# tokens are high entropy, so this is not the weakest link, but an unthrottled
# auth endpoint on an instrument that sits on a competition venue's Wi-Fi is a
# gap worth closing, and the flood alone would starve acquisition.
#
# Deliberately in-process and memory-only: no dependency, no disk, and the state
# is discarded on restart, which is the correct behaviour for an instrument whose
# access token is regenerated anyway.
_AUTH_FAIL_WINDOW = 300.0     # seconds an attempt is remembered
_AUTH_FAIL_LIMIT = 12         # failures per address before the lockout begins
_AUTH_LOCKOUT = 60.0          # seconds locked out once the limit is passed
_AUTH_MAX_TRACKED = 4096      # cap the table so it cannot be grown without bound
_auth_failures = {}
_auth_lock = threading.Lock()


_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _auth_client():
    """The address to throttle, or None for an address that must never be locked.

    request.remote_addr only, never a forwarded header: those are attacker
    controlled, and trusting one would let a single client evade the throttle by
    varying it.

    Loopback is exempt. Not as a convenience: anything speaking from 127.0.0.1 is
    already on this host and has a shell, so throttling it defends nothing, while the
    instrument's own local tooling shares that one address with the operator - so a
    single misconfigured local caller could lock the real operator out of the
    dashboard mid-demonstration. That is a worse failure than the one this guards
    against. Credentials are still required from loopback; only the counter is
    skipped."""
    address = request.remote_addr or "unknown"
    return None if address in _LOOPBACK else address


def _auth_locked(address):
    if address is None:
        return 0.0
    now = time.monotonic()
    with _auth_lock:
        entry = _auth_failures.get(address)
        if not entry:
            return 0.0
        attempts, first_at, locked_until = entry
        if locked_until > now:
            return locked_until - now
        # A served lockout buys a fresh allowance. Without this the attempt count
        # stayed above the limit, so the first failure after the lockout expired
        # re-locked immediately and the address could never recover inside the
        # 300 s window - measured: 401 once, then 429 forever.
        if locked_until or now - first_at > _AUTH_FAIL_WINDOW:
            _auth_failures.pop(address, None)
    return 0.0


def _auth_failed(address):
    if address is None:
        return
    now = time.monotonic()
    with _auth_lock:
        attempts, first_at, locked_until = _auth_failures.get(address, (0, now, 0.0))
        if now - first_at > _AUTH_FAIL_WINDOW:
            attempts, first_at = 0, now
        attempts += 1
        if attempts >= _AUTH_FAIL_LIMIT:
            locked_until = now + _AUTH_LOCKOUT
            LOG.warning("Authentication locked out for %s after %d failures", address, attempts)
        if len(_auth_failures) >= _AUTH_MAX_TRACKED and address not in _auth_failures:
            # Drop the oldest first attempt rather than refusing to track.
            oldest = min(_auth_failures, key=lambda key: _auth_failures[key][1])
            _auth_failures.pop(oldest, None)
        _auth_failures[address] = (attempts, first_at, locked_until)


def _auth_succeeded(address):
    if address is None:
        return
    with _auth_lock:
        _auth_failures.pop(address, None)


@server.before_request
def _lan_authentication():
    if (RUNTIME.get("host") in {"127.0.0.1", "::1", "localhost"}
            and not RUNTIME.get("public_tunnel")):
        return None
    address = _auth_client()
    remaining = _auth_locked(address)
    if remaining > 0:
        return Response(
            f"Too many authentication attempts. Try again in {remaining:.0f} s.",
            429, {"Retry-After": str(int(remaining) + 1)})
    expected_user = os.environ.get("STUDIO_AUTH_USER", "")
    expected_hash = os.environ.get("STUDIO_AUTH_PASSWORD_HASH", "")
    if expected_user and expected_hash:
        header = request.headers.get("Authorization", "")
        authenticated = False
        try:
            if header.startswith("Basic "):
                decoded = base64.b64decode(header[6:], validate=True).decode("utf-8")
                supplied_user, supplied_password = decoded.split(":", 1)
                authenticated = (
                    hmac.compare_digest(supplied_user, expected_user)
                    and _password_matches(supplied_password, expected_hash)
                )
        except Exception:
            authenticated = False
        if authenticated:
            _auth_succeeded(address)
            return None
        _auth_failed(address)
        return Response(
            "Authentication required for LAN access",
            401,
            {"WWW-Authenticate": 'Basic realm="MTDI Studio"'},
        )

    # When no persistent Basic credentials were configured, the single printed
    # high-entropy link establishes a browser session. The token never appears in
    # dashboard HTML or subsequent Dash requests.
    access_token = RUNTIME.get("access_token") or ""
    if not access_token:
        return None
    supplied_token = request.args.get("access", "")
    cookie_token = request.cookies.get("studio_access", "")
    if access_token and cookie_token and hmac.compare_digest(cookie_token, access_token):
        return None
    if access_token and supplied_token and hmac.compare_digest(supplied_token, access_token):
        _auth_succeeded(address)
        response = Response(status=302)
        response.headers["Location"] = request.path or "/"
        response.set_cookie(
            "studio_access",
            access_token,
            max_age=30 * 24 * 60 * 60,
            httponly=True,
            samesite="Strict",
            secure=bool(RUNTIME.get("public_tunnel")),
        )
        return response
    _auth_failed(address)
    return Response("Use the access link printed by MTDI Studio", 401)


@server.after_request
def _security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(self), camera=(self), usb=()"
    resp.headers["Content-Security-Policy"] = _CSP
    # Isolate the browsing context. The Aether terminal loads Pyodide, which runs
    # Python in WebAssembly in the page - entirely client side, with no server
    # execution path - but it is still a large third-party runtime sharing an
    # origin with the instrument's controls, so it should not be reachable from,
    # or able to reach into, another document.
    resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    resp.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    # Only over the public tunnel. Sending HSTS from the LAN HTTP listener would
    # pin every browser on the venue's network to HTTPS for this host:port, and
    # the plain :8050 dashboard would stop loading for them.
    if RUNTIME.get("public_tunnel") and request.is_secure:
        resp.headers["Strict-Transport-Security"] = "max-age=31536000"
    resp.headers.pop("Server", None)
    # Plotly callback JSON is highly compressible. Compressing it preserves every
    # point and the desktop refresh cadence while dramatically reducing phone/Wi-Fi
    # transfer time. Downloads and already encoded/streamed responses are untouched.
    accepts_gzip = "gzip" in request.headers.get("Accept-Encoding", "").lower()
    response_type = resp.mimetype or ""
    compressible = (
        response_type in {"application/json", "text/html", "text/css", "application/javascript", "text/javascript", "application/wasm"}
        or response_type.endswith("+json")
    )
    if (
        accepts_gzip and compressible and not resp.direct_passthrough
        and "Content-Encoding" not in resp.headers
    ):
        payload = resp.get_data()
        if len(payload) >= 1024:
            resp.set_data(gzip.compress(payload, compresslevel=4))
            resp.headers["Content-Encoding"] = "gzip"
            resp.headers["Vary"] = "Accept-Encoding"
    return resp

app = dash.Dash(
    __name__, server=server,
    # public/assets is served by Vercel's CDN directly (no 4.5 MB function response limit)
    # and by Dash itself when running locally.
    assets_folder=str(Path(__file__).resolve().parent.parent / "public" / "assets"),
    # Dash tests this regex against the file NAME only. Three.js, the lunar module and the
    # MediaPipe hand bundles are loaded on demand by the page, never at boot.
    assets_ignore=r"(three\.min\.js|lunar\.js|robot-hand\.js|hands.*\.js)",
    suppress_callback_exceptions=True, update_title=None,
    # Load the chart chunks with the page instead of lazily: each lazy chunk was a
    # serial round trip on Wi Fi and timed out on weak links.
    eager_loading=True,
)
app.title = "MTDI Studio"

app.index_string = f"""<!DOCTYPE html>
<html>
  <head>
    {{%metas%}}<title>{{%title%}}</title>{{%favicon%}}{{%css%}}
    <style>{GLOBAL_CSS}</style>
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#07090f">
    <link rel="manifest" href="/manifest.webmanifest">
    <script type="module" src="/_i3/nvtra-loader.js?v={APP_VERSION}"></script>
    <script defer src="/_i3/boards.js?v={APP_VERSION}"></script>
    <script>
      /* PHONES: a fixed landscape stage. A phone (coarse pointer, short screen edge up to
         600 CSS px) is sent to /phone, a thin shell that holds this same page in an iframe
         exactly 1180 px wide: the desktop composition, at the height the screen allows.
         The shell scales that stage onto the long edge and turns it a quarter turn when
         the phone is held upright, so the view is always landscape. Inside the iframe the
         page sees an ordinary 1180 px desktop window, so every layout rule and script works
         unchanged - unlike rotating <body>, which left innerWidth, window scroll and every
         canvas size pointing at the wrong box.

         TABLETS (coarse pointer, larger screen) keep the desktop composition through the
         viewport: 1180 CSS px on the long edge, no rotation.

         Settings can switch a phone to the native mobile reflow instead ('mobile'); then
         there is no stage and the narrow stylesheet applies. */
      (function(){{
        var STAGE=1180, root=document.documentElement;
        function inStage(){{
          try{{return window.top!==window&&window.top.location.pathname==='/phone';}}catch(e){{return false;}}
        }}
        function forced(){{
          try{{return new URLSearchParams(location.search).get('phone-preview')==='1';}}catch(e){{return false;}}
        }}
        function coarse(){{
          try{{return matchMedia('(pointer:coarse)').matches||navigator.maxTouchPoints>0;}}catch(e){{return false;}}
        }}
        function isPhone(){{
          var a=Number(screen.width)||innerWidth, b=Number(screen.height)||innerHeight;
          return forced()||(coarse()&&Math.min(a,b)<=600);
        }}
        function wantMobile(){{
          try{{return localStorage.getItem('i3-phone-layout')==='mobile';}}catch(e){{return false;}}
        }}
        function setViewport(content){{
          /* Dash and the interface each add a viewport tag; the last one wins, so set all. */
          var metas=document.querySelectorAll('meta[name="viewport"]');
          for(var i=0;i<metas.length;i++)metas[i].content=content;
        }}
        if(inStage()){{
          root.classList.add('phone-desktop','phone-stage');
          /* Canvases and WebGL size themselves by devicePixelRatio. Inside the stage one CSS
             pixel lands on (screen density x stage scale) device pixels, about 2.1 on a
             phone; rendering at the phone's full 3x would draw twice the pixels nobody sees.
             devicePixelRatio is a replaceable attribute, so this caps it for this page only. */
          try{{
            var d=Number(window.top.__i3StageDPR)||Math.min(2,window.devicePixelRatio||1);
            window.devicePixelRatio=Math.max(1,Math.min(2,d));
          }}catch(e){{}}
          /* Touch forgiveness. At phone scale the desktop controls are small, so a tap that
             lands just outside one - within 12 stage px, about 7 on the glass - goes to the
             nearest control instead of the background. Anything that already takes the tap
             (a control, a chart, an input, a clickable card) keeps it, and a control only
             receives it if nothing covers it at that spot. */
          var OWN='button,a,input,select,textarea,label,summary,[role="button"],[role="tab"],[role="slider"],'+
                  '[contenteditable],.js-plotly-plot,.dash-dropdown,.Select,.rc-slider';
          function takesTap(el){{
            for(var n=el,i=0;n&&n.nodeType===1&&i<8;n=n.parentElement,i++){{
              if(n.matches(OWN)||getComputedStyle(n).cursor==='pointer')return true;
            }}
            return false;
          }}
          document.addEventListener('click',function(ev){{
            if(!ev.isTrusted||!ev.target||ev.target.nodeType!==1||takesTap(ev.target))return;
            var x=ev.clientX,y=ev.clientY,R=12,best=null,bestD=R+1;
            var all=document.querySelectorAll('button,a[href],[role="button"],[role="tab"]');
            for(var i=0;i<all.length;i++){{
              var el=all[i],r=el.getBoundingClientRect();
              if(!r.width||!r.height||el.disabled)continue;
              var d=Math.hypot(Math.max(r.left-x,0,x-r.right),Math.max(r.top-y,0,y-r.bottom));
              if(d>=bestD)continue;
              var top=document.elementFromPoint(Math.min(Math.max(x,r.left+1),r.right-1),
                                                Math.min(Math.max(y,r.top+1),r.bottom-1));
              if(top&&(top===el||el.contains(top))){{best=el;bestD=d;}}
            }}
            if(best){{ev.preventDefault();ev.stopPropagation();best.click();}}
          }},true);
        }}
        function syncPhoneMode(){{
          if(inStage()){{
            /* Settings chose the mobile reflow: leave the stage for the plain page. */
            if(wantMobile()){{try{{window.top.location.replace('/');}}catch(e){{}}}}
            return;
          }}
          var phone=isPhone(), mobile=phone&&wantMobile();
          if(phone&&!mobile){{location.replace('/phone'+location.search);return;}}
          var tablet=!phone&&coarse();
          root.classList.toggle('phone-desktop',tablet);
          root.classList.toggle('i3-mobile-layout',mobile);
          if(tablet){{
            var a=Number(screen.width)||innerWidth, b=Number(screen.height)||innerHeight;
            var portrait=matchMedia('(orientation: portrait)').matches;
            var edge=portrait?Math.min(a,b):Math.max(a,b);
            setViewport('width='+STAGE+',initial-scale='+(edge/STAGE).toFixed(4)+
                        ',minimum-scale=0.25,maximum-scale=3,viewport-fit=cover');
          }} else if(mobile){{
            setViewport('width=device-width,initial-scale=1,maximum-scale=5,viewport-fit=cover');
          }}
          try{{
            if(window.dash_clientside&&window.dash_clientside.set_props){{
              window.dash_clientside.set_props('mobile-mode',{{data:phone||tablet}});
            }}
          }}catch(err){{}}
        }}
        /* Exposed so the Settings toggle can re-apply the layout choice without a reload. */
        try{{window.__i3SyncPhoneMode=syncPhoneMode;}}catch(err){{}}
        syncPhoneMode();
        document.addEventListener('DOMContentLoaded',syncPhoneMode);
        addEventListener('orientationchange',function(){{setTimeout(syncPhoneMode,200);}},{{passive:true}});
        addEventListener('resize',syncPhoneMode,{{passive:true}});
      }})();
    </script>
    <script>
      (function(){{try{{
        localStorage.removeItem('i3-theme');
        if(localStorage.getItem('i3-anim')==='off')document.documentElement.classList.add('no-anim');
      }}catch(e){{}}}})();
    </script>
    <script>
      /* A full document startup always begins with the intro and always hands off
         to Home. This executes before Dash reads location.pathname. In-app routing
         never re-runs it, so navigation and Back cannot replay the intro. */
      if ("scrollRestoration" in history) history.scrollRestoration = "manual";
      try{{
        if(location.pathname!=="/") history.replaceState(history.state,"","/"+location.search);
      }}catch(e){{}}
      scrollTo(0,0);
    </script>
  </head>
  <body>
    {{%app_entry%}}
    <footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer>
    <script>{SCRUB_JS}</script>
  </body>
</html>"""

app.layout = html.Div([
    html.Button("↻\nREFRESH", id="mobile-refresh-btn", n_clicks=0,
                title="Fetch the newest data",
                **{"aria-label":"Refresh live data"}),
    dcc.Store(id="mobile-mode", data=False, storage_type="memory"),
    dcc.Interval(id="mobile-mode-probe", interval=400, n_intervals=0),
    dcc.Interval(id="d4-tick", interval=2500, n_intervals=0),
    html.Div(
        "SIMULATED DATA · NOT A MEASUREMENT",
        id="simulation-watermark",
        style={
            "display":"block" if RUNTIME["demo"] else "none",
            "position":"fixed", "left":"0", "right":"0", "bottom":"0",
            "zIndex":"99999", "padding":"10px", "textAlign":"center",
            "fontFamily":"monospace", "fontWeight":"700", "letterSpacing":"0.16em",
            "color":"#07090f", "background":"#ffab40",
            "boxShadow":"0 -4px 30px rgba(255,171,64,0.45)",
        },
    ),
    html.Div(T("brand.credit"), id="fixed-credit"),
    html.Div([html.Span(id="typewriter-text"), html.Span("▋", id="typewriter-cursor")], id="typewriter-bar"),
    html.Div(id="nvtra-alert-stack"),
    html.Div(id="nvtra-alert-trigger", style={"display":"none"}),
    dcc.Store(id="nvtra-prev-state", storage_type="memory", data={"c1":0}),
    dcc.Interval(id="nvtra-interval", interval=1500, n_intervals=0),
    dcc.Location(id="url", refresh=False),
    # write-only sinks for the pattern-matching key actions (their real effect is on
    # the server-side key store; these just satisfy Dash's require-an-Output rule).
    dcc.Store(id="key-use-sink", storage_type="memory"),
    dcc.Store(id="chat-model-use-sink", storage_type="memory"),
    dcc.Store(id="chat-session-sink", storage_type="memory"),
    dcc.Store(id="key-del-sink", storage_type="memory"),
    dcc.Store(id="key-name-sink", storage_type="memory"),
    # NVTRA word-by-word chat: question in, full answer out, then a clientside typewriter.
    dcc.Store(id="nvtra-ask", storage_type="memory"),
    dcc.Store(id="nvtra-reply", storage_type="memory"),
    html.Div(id="nvtra-type-dummy", style={"display":"none"}),
    dcc.Download(id="archive-json-download"),
    dcc.Download(id="archive-csv-download"),
    html.Div(id="scroll-top-dummy", style={"display":"none"}),
    html.Div(id="scroll-sink", style={"display":"none"}),
    html.Div(id="settings-anim-dummy", style={"display":"none"}),
    # 2px navigation progress bar — the entire "loading" affordance. See RENDERING NOTES.
    html.Div(id="nav-progress"),
    html.Div([
        dcc.Link(html.Div(T("brand.title"), className="header-brand"), href="/", style={"textDecoration":"none"}),
        html.Div([html.Div(id="nav-glass", className="nav-glass", children=[
            dcc.Link(html.Button([html.Span(className="nav-dot"),T("nav.home")],     className="nav-glass-btn", id="nav-home"),     href="/",         style={"textDecoration":"none"}),
            html.Div(className="nav-glass-sep"),
            dcc.Link(html.Button([html.Span(className="nav-dot"),T("nav.page1")], className="nav-glass-btn", id="nav-em"),       href="/page-1",       style={"textDecoration":"none"}),
            html.Div(className="nav-glass-sep"),
            dcc.Link(html.Button([html.Span(className="nav-dot"),T("nav.page2")], className="nav-glass-btn", id="nav-sweep3"), href="/page-2", style={"textDecoration":"none"}),
            html.Div(className="nav-glass-sep"),
            dcc.Link(html.Button([html.Span(className="nav-dot"),T("nav.mtdi")],     className="nav-glass-btn", id="nav-mtdi"),     href="/mtdi",     style={"textDecoration":"none"}),
            html.Div(className="nav-glass-sep"),
            dcc.Link(html.Button([html.Span(className="nav-dot"),T("nav.settings")], className="nav-glass-btn", id="nav-settings"), href="/settings", style={"textDecoration":"none"}),
        ])], className="nav-glass-wrap"),
        html.Div(id="header-pills", className="header-pills"),
        dcc.Interval(id="header-interval", interval=1200, n_intervals=0),
    ], className="site-header"),
    startup_intro(),
    html.Div([
    # ── permanent shell ──────────────────────────────────────────────────────
    html.Div(id="page-content"),
    ], id="app-shell"),
])

# Detect touch-phone mode entirely in the browser. The tiny probe callback never
# reaches this host; it only toggles the data intervals below.
app.clientside_callback(
    "function(n,p){try{return document.documentElement.classList.contains('phone-desktop')||!!(matchMedia('(pointer:coarse)').matches||navigator.maxTouchPoints>0);}catch(e){return false;}}",
    Output("mobile-mode", "data"),
    Input("mobile-mode-probe", "n_intervals"), Input("url", "pathname"),
)

# A phone runs the same live cadence as the desktop. Every data and Plotly timer
# used to be disabled on touch devices, leaving the instrument frozen behind a
# floating refresh button - a phone-only behaviour the PC never has. The point of
# the phone view is to be the desktop view, so the timers run here too.

# Reset scroll to the top ONLY when the new page content has actually mounted (driven by
# display_page's scroll-top-dummy output), never on the raw URL change. Doing it on the
# URL change scrolls the OLD page first — that is the visible "goes up a bit then
# switches". Firing on the content swap means the reset happens together with the new
# page appearing, and it is always instant (never smooth).
app.clientside_callback(
    "function(n){"
    "try{history.scrollRestoration='manual';}catch(e){}"
    "document.documentElement.classList.remove('nav-busy');"
    # The new page is in: start its ready signal (data-page-ready, see browser.py).
    "if(window.__i3PageMounted){window.__i3PageMounted();}"
    # FIRST render is Home because the head normalises every fresh document URL to /.
    # Leave the document at 0 while the fixed intro handles its own internal scroll.
    "if(!window.__i3FirstRouteDone){window.__i3FirstRouteDone=true;return '';}"
    # Every later route change is ordinary module navigation. The removed intro is
    # no longer part of the document, so scroll 0 is always the module top.
    "if(window.__i3ResetScroll){window.__i3ResetScroll();}"
    "else{window.scrollTo(0,0);"
    "if(document.documentElement)document.documentElement.scrollTop=0;"
    "if(document.body)document.body.scrollTop=0;}"
    "return '';}",
    Output("scroll-sink","children"), Input("scroll-top-dummy","children")
)

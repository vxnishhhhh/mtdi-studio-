"""NVTRA assistant: AI providers, key management, chat sessions, SG analysis prompts."""
import base64
import os
import threading
import hashlib
import re
import urllib.request
import urllib.error
import socket
import time
from ._shared import inherit
inherit(globals(), 'common', 'sensors')

# ── NVTRA chatbot (Google Gemini) ─────────────────────────────────────────────
# The assistant is powered by Gemini's free tier. Get a key at
# https://aistudio.google.com/apikey and paste it into GEMINI_API_KEY below — that is
# the ONE place the key lives. (An optional GEMINI_API_KEY environment variable
# overrides it, which is handy for a systemd service, but you don't need it.)
# Before sharing this file publicly, blank the key out. The call is made server-side
# from this host, so the browser CSP (connect-src 'self') does not apply to it.
# Free-tier quota on Gemini is PER MODEL, so a key can be out of quota on one model
# yet perfectly fine on another. gemini-flash-latest reliably has free-tier quota;
# the app tries the list below in order and uses the first that answers. Set the env
# var GEMINI_MODEL to force a specific one.
GEMINI_MODEL    = os.environ.get("GEMINI_MODEL", "").strip()
GEMINI_MODELS   = ([GEMINI_MODEL] if GEMINI_MODEL else []) + \
                  ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.0-flash"]
# Other providers NVTRA can talk to (so a key that isn't a Gemini key still works).
# Use published Anthropic Messages API model IDs. The previous speculative names
# (`claude-sonnet-5`, `claude-haiku-4-5-*`) produced HTTP 400 before authentication
# could be meaningfully tested.
ANTHROPIC_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-3-5-haiku-20241022",
    "claude-3-haiku-20240307",
]
OPENAI_MODELS = ["gpt-5-mini", "gpt-4.1-mini", "gpt-4o-mini"]
XAI_MODELS = ["grok-4.5"]
KIMI_MODELS = ["kimi-k2.5"]
GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
try:
    AI_REQUEST_TIMEOUT = max(5.0, min(120.0, float(os.environ.get(
        "STUDIO_AI_TIMEOUT_SECONDS", "35"
    ))))
except ValueError:
    AI_REQUEST_TIMEOUT = 35.0

# ── API KEY CONFIGURATION ────────────────────────────────────────────────────
# UI-managed credentials live in the instrument's protected local state; environment
# variables are also supported. The distributable source must never contain a key.
# Never ship provider credentials inside the instrument source. Configure keys with
# GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, XAI_API_KEY, GROQ_API_KEY or
# KIMI_API_KEY, or add them through Settings → AI Keys on the local instrument.
MANUAL_API_KEYS = []
NVTRA_MAX_TURNS = 16          # how much conversation history is sent back each call


def _key_provider(key, selected="auto"):
    """Return a supported provider, or ``unknown`` when a prefix is ambiguous."""
    if selected in {"gemini", "openai", "anthropic", "xai", "groq", "kimi"}:
        return selected
    k = (key or "").strip()
    if k.startswith("sk-ant"): return "anthropic"
    if k.startswith("sk-proj-"): return "openai"
    if k.startswith(("xai-", "xai_")): return "xai"
    if k.startswith("gsk_"): return "groq"
    if k.startswith(("AIza", "AQ.")): return "gemini"
    # Generic sk-* keys are used by several OpenAI-compatible providers, including
    # Moonshot/Kimi, so guessing OpenAI here would silently route them incorrectly.
    return "unknown"


def _provider_label(key=None, provider="auto"):
    p = _key_provider(key, provider)
    return {"anthropic": "Claude", "openai": "OpenAI", "gemini": "Gemini",
            "xai": "Grok", "kimi": "Kimi",
            "groq": "Groq",
            "unknown": "Choose provider"}[p]


def _validate_key_provider(key, provider="auto"):
    key = (key or "").strip()
    if not key:
        return None, "Paste an API key first."
    detected = _key_provider(key)
    chosen = _key_provider(key, provider)
    if chosen == "unknown":
        return None, "This key prefix is ambiguous. Choose Gemini, OpenAI or Claude."
    if detected != "unknown" and provider not in ("auto", detected):
        return None, f"This key looks like {_provider_label(key)} but {provider.title()} was selected."
    if len(key) < 16:
        return None, "The key is too short to be a valid provider API key."
    return chosen, None


# Conversation lives server-side: this is a single-instrument LAN kiosk, so one shared
# thread is the right model (and it survives page navigation without a browser Store).
nvtra_lock = threading.RLock()
nvtra_history = deque(maxlen=40)     # {"role":"user"|"model", "text":str}
nvtra_chat_archive = deque(maxlen=500)  # complete cross-session conversations
nvtra_sessions = deque(maxlen=120)   # grouped, clickable conversations
nvtra_active_session = [None]


def _new_session_id():
    return f"chat-{int(time.time() * 1000)}-{secrets.token_hex(3)}"


def _new_chat_session(title="New session"):
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    session = {
        "id": _new_session_id(), "title": title, "title_source": "pending",
        "created_utc": stamp, "updated_utc": stamp, "messages": [],
    }
    nvtra_sessions.append(session)
    nvtra_active_session[0] = session["id"]
    return session


def _active_chat_session(create=True):
    sid = nvtra_active_session[0]
    session = next((s for s in nvtra_sessions if s.get("id") == sid), None)
    return session or (_new_chat_session() if create else None)


def _sync_history_from_session(session):
    nvtra_history.clear()
    nvtra_history.extend((session or {}).get("messages", [])[-nvtra_history.maxlen:])


def _normalize_chat_sessions():
    """De-duplicate sessions and fold pre-session records into one imported chat."""
    sessions = list(nvtra_sessions)
    modern = []
    legacy_messages = []
    legacy_created = ""
    legacy_updated = ""
    seen_fingerprints = set()
    for session in sessions:
        messages = session.get("messages") or []
        fingerprint = tuple(
            (message.get("role"), message.get("text")) for message in messages
        )
        if fingerprint and fingerprint in seen_fingerprints:
            continue
        if fingerprint:
            seen_fingerprints.add(fingerprint)
        is_legacy = (
            session.get("title_source") == "legacy"
            or not str(session.get("id", "")).startswith("chat-")
        )
        if is_legacy:
            legacy_created = legacy_created or session.get("created_utc", "")
            legacy_updated = session.get("updated_utc", "") or legacy_updated
            legacy_messages.extend(messages)
        else:
            modern.append(session)
    if legacy_messages:
        first_prompt = next(
            (m.get("text", "") for m in legacy_messages if m.get("role") == "user"),
            "Imported history",
        )
        modern.insert(0, {
            "id": "legacy-history",
            "title": first_prompt.strip()[:54] or "Imported history",
            "title_source": "input",
            "created_utc": legacy_created,
            "updated_utc": legacy_updated,
            "messages": legacy_messages,
        })
    nvtra_sessions.clear()
    nvtra_sessions.extend(modern[-nvtra_sessions.maxlen:])
    if not any(s.get("id") == nvtra_active_session[0] for s in nvtra_sessions):
        nvtra_active_session[0] = nvtra_sessions[-1]["id"] if nvtra_sessions else None

# ── live API-key store (add / switch keys from the UI, in memory only) ──
nvtra_keys_lock = threading.RLock()
_nvtra_kid = [0]
def _new_kid():
    _nvtra_kid[0] += 1
    return f"k{_nvtra_kid[0]}"
nvtra_keys = {
    "active": None,
    "items": [],
}
LOCAL_CLOUD_STATE_PATH = Path(os.environ.get(
    "STUDIO_CLOUD_STATE",
    str(Path.home() / ".local/share/mtdi-studio/cloud_state.enc"),
)).expanduser()
local_cloud_lock = threading.RLock()
notion_outbox_lock = threading.RLock()
notion_outbox = []
_notion_drain_running = [False]


def _save_local_cloud_state():
    """Atomically persist encrypted keys, chat history and pending Notion writes."""
    with local_cloud_lock, nvtra_keys_lock, nvtra_lock, notion_outbox_lock:
        state = {
            "version": 1,
            "keys": {
                "active": nvtra_keys["active"],
                "items": [dict(item) for item in nvtra_keys["items"]],
            },
            "chats": list(nvtra_history),
            "chat_archive": list(nvtra_chat_archive),
            "chat_sessions": list(nvtra_sessions),
            "active_chat_session": nvtra_active_session[0],
            "notion_outbox": list(notion_outbox),
            "saved_at": time.time(),
        }
        encrypted = _cloud_encrypt(json.dumps(
            state, ensure_ascii=False, separators=(",", ":")
        ))
        if not encrypted:
            LOG.error("Local cloud state was not saved: encryption secret unavailable")
            return False
        LOCAL_CLOUD_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            LOCAL_CLOUD_STATE_PATH.parent.chmod(0o700)
        except OSError:
            pass
        temporary = LOCAL_CLOUD_STATE_PATH.with_suffix(".tmp")
        temporary.write_text(encrypted, encoding="utf-8")
        temporary.chmod(0o600)
        os.replace(temporary, LOCAL_CLOUD_STATE_PATH)
        return True


def _load_local_cloud_state():
    """Restore the last committed local state before attempting any cloud request."""
    if not LOCAL_CLOUD_STATE_PATH.exists():
        return False
    try:
        decoded = _cloud_decrypt(
            LOCAL_CLOUD_STATE_PATH.read_text(encoding="utf-8").strip()
        )
        state = json.loads(decoded)
        keys = state.get("keys") or {}
        items = []
        for item in keys.get("items") or []:
            provider, error = _validate_key_provider(
                item.get("key", ""), item.get("provider", "auto")
            )
            if not error and item.get("id"):
                clean = dict(item)
                clean["provider"] = provider
                clean["builtin"] = False
                items.append(clean)
        with nvtra_keys_lock:
            nvtra_keys["items"] = items
            requested = keys.get("active")
            nvtra_keys["active"] = (
                requested if any(x["id"] == requested for x in items)
                else (items[0]["id"] if items else None)
            )
            numeric = [
                int(x["id"][1:]) for x in items
                if re.fullmatch(r"k\d+", x.get("id", ""))
            ]
            if numeric:
                _nvtra_kid[0] = max(_nvtra_kid[0], max(numeric))
        with nvtra_lock:
            nvtra_history.clear()
            nvtra_history.extend((state.get("chats") or [])[-nvtra_history.maxlen:])
            nvtra_chat_archive.clear()
            nvtra_chat_archive.extend(
                (state.get("chat_archive") or [])[-nvtra_chat_archive.maxlen:]
            )
            nvtra_sessions.clear()
            loaded_sessions = state.get("chat_sessions") or []
            if loaded_sessions:
                nvtra_sessions.extend(loaded_sessions[-nvtra_sessions.maxlen:])
            else:
                # Older builds stored one archive row per exchange. Preserve those
                # records as individually selectable legacy sessions.
                for old in list(nvtra_chat_archive)[-nvtra_sessions.maxlen:]:
                    messages = []
                    if old.get("user"):
                        messages.append({"role": "user", "text": old["user"]})
                    if old.get("answer"):
                        messages.append({
                            "role": "model", "text": old["answer"],
                            "error": old.get("status") == "error",
                        })
                    nvtra_sessions.append({
                        "id": old.get("session_id") or old.get("id") or _new_session_id(),
                        "title": (old.get("title") or old.get("user") or "Saved chat")[:54],
                        "title_source": old.get("title_source", "legacy"),
                        "created_utc": old.get("recorded_utc", ""),
                        "updated_utc": old.get("recorded_utc", ""),
                        "messages": messages,
                    })
            requested_session = state.get("active_chat_session")
            nvtra_active_session[0] = (
                requested_session
                if any(s.get("id") == requested_session for s in nvtra_sessions)
                else (nvtra_sessions[-1]["id"] if nvtra_sessions else None)
            )
            active_session = _active_chat_session(create=False)
            if active_session:
                _sync_history_from_session(active_session)
            _normalize_chat_sessions()
            _sync_history_from_session(_active_chat_session(create=False))
        with notion_outbox_lock:
            notion_outbox[:] = [
                record for record in (state.get("notion_outbox") or [])
                if record.get("section") == "Chat History"
            ]
        return True
    except Exception:
        LOG.exception("Encrypted local cloud state could not be restored")
        return False


def _mask_key(k):
    k = (k or "").strip()
    if len(k) <= 12:
        return (k[:2] + "…") if k else "(empty)"
    return f"{k[:6]}…{k[-4:]}"


def _active_ai_credential():
    """Return (key, provider); explicit provider environment keys remain supported."""
    env_candidates = (
        ("gemini", os.environ.get("GEMINI_API_KEY", "").strip()),
        ("openai", os.environ.get("OPENAI_API_KEY", "").strip()),
        ("anthropic", os.environ.get("ANTHROPIC_API_KEY", "").strip()),
        ("xai", os.environ.get("XAI_API_KEY", "").strip()),
        ("groq", os.environ.get("GROQ_API_KEY", "").strip()),
        ("kimi", (os.environ.get("KIMI_API_KEY", "").strip() or
                  os.environ.get("MOONSHOT_API_KEY", "").strip())),
    )
    forced = os.environ.get("STUDIO_AI_PROVIDER", "").strip().lower()
    if forced:
        for provider, key in env_candidates:
            if provider == forced and key:
                return key, provider
    for provider, key in env_candidates:
        if key:
            return key, provider
    with nvtra_keys_lock:
        if nvtra_keys["active"] == "local":
            # The operator picked the on-device model on purpose: no cloud key applies.
            return "", "local"
        for it in nvtra_keys["items"]:
            if it.get("id") == nvtra_keys["active"]:
                return it["key"].strip(), it.get("provider") or _key_provider(it["key"])
        if nvtra_keys["items"]:
            it = nvtra_keys["items"][0]
            return it["key"].strip(), it.get("provider") or _key_provider(it["key"])
    return "", "unknown"


def _active_ai_model():
    """Return the model saved with the active key, if model discovery selected one."""
    _key, provider = _active_ai_credential()
    env_name = {
        "gemini": "GEMINI_MODEL", "openai": "OPENAI_MODEL",
        "anthropic": "ANTHROPIC_MODEL", "xai": "XAI_MODEL",
        "groq": "GROQ_MODEL", "kimi": "KIMI_MODEL",
    }.get(provider)
    if env_name and os.environ.get(env_name, "").strip():
        return os.environ[env_name].strip()
    with nvtra_keys_lock:
        item = next(
            (x for x in nvtra_keys["items"] if x["id"] == nvtra_keys["active"]),
            None,
        )
        return (item or {}).get("model", "")


def _provider_from_label(label):
    text = (label or "").strip().lower()
    if any(word in text for word in ("grok", "xai", "x.ai")):
        return "xai"
    if "groq" in text:
        return "groq"
    if any(word in text for word in ("kimi", "moonshot")):
        return "kimi"
    if "claude" in text or "anthropic" in text:
        return "anthropic"
    if "gemini" in text or "google" in text:
        return "gemini"
    if "openai" in text or "chatgpt" in text:
        return "openai"
    return "unknown"


def _discover_provider_model(key, provider):
    """Safely query only the chosen provider and select an available chat model."""
    defaults = {
        "xai": XAI_MODELS[0], "groq": GROQ_MODELS[0], "kimi": KIMI_MODELS[0],
        "anthropic": ANTHROPIC_MODELS[0], "openai": OPENAI_MODELS[0],
        "gemini": GEMINI_MODELS[0],
    }
    if provider not in {"xai", "groq", "kimi"}:
        return defaults.get(provider, "")
    url = (
        "https://api.x.ai/v1/models" if provider == "xai"
        else ("https://api.groq.com/openai/v1/models" if provider == "groq"
              else "https://api.moonshot.ai/v1/models")
    )
    req = urllib.request.Request(
        url, method="GET", headers={"Authorization": f"Bearer {key}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=AI_REQUEST_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
        available = [
            str(item.get("id", "")) for item in (payload.get("data") or [])
            if item.get("id")
        ]
        preferred = (
            XAI_MODELS if provider == "xai"
            else (GROQ_MODELS if provider == "groq" else KIMI_MODELS)
        )
        for model in preferred:
            if model in available:
                return model
        marker = "grok" if provider == "xai" else (
            "llama" if provider == "groq" else "kimi"
        )
        return next((m for m in available if marker in m.lower()),
                    defaults[provider])
    except Exception:
        return defaults[provider]


def _gemini_key():
    """Compatibility helper retained for existing callers."""
    return _active_ai_credential()[0]


def nvtra_engines():
    """Every engine NVTRA can answer with, for the pickers: the local model first, then
    the stored cloud keys. Offline mode lists the local model only."""
    local = local_ai_status()
    active, items = nvtra_keys_snapshot()
    _key, provider = _active_ai_credential()
    local_active = provider in ("local", "unknown") or instrument_offline() or not _key
    out = [{"id": "local", "label": "Local model", "model": str(local["model"] or "none"),
            "available": bool(local["available"]), "active": local_active, "note": local.get("error")}]
    if instrument_offline():
        return out
    for it in items:
        out.append({"id": it["id"], "label": it["label"],
                    "model": it.get("model") or _provider_label(it["key"], it.get("provider", "auto")),
                    "available": True, "active": (not local_active) and it["id"] == active})
    return out


def nvtra_keys_snapshot():
    with nvtra_keys_lock:
        return nvtra_keys["active"], [dict(x) for x in nvtra_keys["items"]]


def nvtra_add_key(label, key, provider="auto"):
    key = (key or "").strip()
    chosen, error = _validate_key_provider(key, provider)
    if error:
        return None
    model = _discover_provider_model(key, chosen)
    with nvtra_keys_lock:
        kid = _new_kid()
        label = (label or "").strip()[:40] or f"Key {_nvtra_kid[0]}"
        item = {"id": kid, "label": label, "key": key,
                "provider": chosen, "model": model, "builtin": False}
        nvtra_keys["items"].append(item)
        nvtra_keys["active"] = kid          # newly added key becomes active
    _save_local_cloud_state()
    return kid


def nvtra_set_active(kid):
    changed = False
    with nvtra_keys_lock:
        if kid == "local" or any(it["id"] == kid for it in nvtra_keys["items"]):
            nvtra_keys["active"] = kid
            changed = True
    if changed:
        _save_local_cloud_state()


def nvtra_rename_key(kid, new_label):
    new_label = (new_label or "").strip()[:40]
    if not new_label:
        return False
    old_label = ""
    with nvtra_keys_lock:
        item = next((x for x in nvtra_keys["items"] if x["id"] == kid), None)
        if not item:
            return False
        old_label = item["label"]
        if old_label == new_label:
            return True
        item["label"] = new_label
    _save_local_cloud_state()
    return True


def nvtra_delete_key(kid):
    removed = None
    with nvtra_keys_lock:
        it = next((x for x in nvtra_keys["items"] if x["id"] == kid), None)
        if not it or it["builtin"]:
            return
        removed = dict(it)
        nvtra_keys["items"] = [x for x in nvtra_keys["items"] if x["id"] != kid]
        if nvtra_keys["active"] == kid:
            nvtra_keys["active"] = (
                nvtra_keys["items"][0]["id"] if nvtra_keys["items"] else None
            )
    _save_local_cloud_state()


def _merge_manual_api_keys():
    """Seed enabled source-configured keys without replacing saved UI edits."""
    added = []
    with nvtra_keys_lock:
        existing = {item["id"] for item in nvtra_keys["items"]}
        for configured in MANUAL_API_KEYS:
            key = str(configured.get("key", "")).strip()
            kid = str(configured.get("id", "")).strip()
            provider = str(configured.get("provider", "auto")).strip()
            if (not configured.get("enabled") or not kid or
                    not key or key.startswith("DEMO_")):
                continue
            chosen, error = _validate_key_provider(key, provider)
            if error:
                LOG.error("Manual API key %s was ignored: %s", kid, error)
                continue
            model = (str(configured.get("model", "")).strip() or
                     _discover_provider_model(key, chosen))
            current = next(
                (x for x in nvtra_keys["items"] if x.get("id") == kid), None
            )
            if current:
                changed = any((
                    current.get("key") != key,
                    current.get("provider") != chosen,
                    current.get("model", "") != model,
                ))
                current.update({
                    "key": key, "provider": chosen, "model": model,
                    "builtin": False, "source": "manual-config",
                })
                if changed:
                    added.append(dict(current))
                continue
            item = {
                "id": kid,
                "label": str(configured.get("label", "")).strip()[:40]
                         or _provider_label(key, chosen),
                "key": key,
                "provider": chosen,
                "model": model,
                "builtin": False,
                "source": "manual-config",
            }
            nvtra_keys["items"].append(item)
            existing.add(kid)
            added.append(dict(item))
        if added and not nvtra_keys["active"]:
            nvtra_keys["active"] = added[0]["id"]
    if added:
        _save_local_cloud_state()
    return added


# ── NVTRA agent: spoken or typed commands become interface actions ──────────────
AGENT_PAGES = {"home": "/", "page 1": "/page-1", "page one": "/page-1", "page 2": "/page-2", "page two": "/page-2",
               "mtdi": "/mtdi", "page 3": "/page-3", "page three": "/page-3", "settings": "/settings"}
AGENT_ACTIONS_DOC = (
    "Return ONLY a JSON object: {\"say\": string, \"actions\": [ {\"type\": string, \"target\": string} ] }.\n"
    "Allowed action types and targets:\n"
    "navigate: one of / (Home), /page-1 (Page 1), /page-2 (Page 2), /mtdi (MTDI), /page-3 (Page 3), /settings (Settings)\n"
    "tab: c1 | c2x | both (Page 1)  or ch3 | wifi | bt (Page 2)\n"
    "mode: online | offline\n"
    "camera: on | off\n"
    "finger_mouse: on | off\n"
    "scroll: up | down | top | bottom\n"
    "relock: ch1 | ch2 | ch3 | current | all  (relearn the baseline of channel 1, 2, 3, 4 or all)\n"
    "Keep \"say\" short for simple requests (one or two spoken sentences) but answer complex or multi-part questions fully, up to about five sentences, so nothing is left out. Speak naturally and warmly like a calm human colleague talking out loud: contractions are fine, no lists, no headings, no brackets, no symbols, no code, and only state numbers that appear in the live context. "
    "Example: for 'five plus five' answer {\"say\": \"That's ten.\", \"actions\": []}. "
    "If the request is a question, answer it in \"say\" and use an empty actions list. General knowledge, maths, science and world questions are welcome: answer them directly and confidently from your own knowledge. Never invent actions outside this list. Never write the word 'say' or any JSON inside the spoken text."
)


ELEVENLABS_VOICE = os.environ.get("STUDIO_ELEVENLABS_VOICE", "TWutjvRaJqAX89preB4e")  # Evan (library voice, paid tiers)
ELEVENLABS_FALLBACK_VOICE = os.environ.get("STUDIO_ELEVENLABS_FALLBACK", "nPczCjzI2devNBz1zQrb")  # Brian (premade, every tier)
_elevenlabs_blocked = {}  # voice id -> retry time, for library voices the plan refuses
_elevenlabs_voices_cache = {"at": 0.0, "voices": []}


def _state_dir():
    return Path(os.environ.get("STUDIO_STATE_DIR", str(Path.home() / ".local/share/mtdi-studio")))


def elevenlabs_voice_id():
    """The voice chosen in Settings, else the default preferred voice."""
    try:
        chosen = (_state_dir() / "elevenlabs.voice").read_text().strip()
    except OSError:
        chosen = ""
    return chosen or ELEVENLABS_VOICE


def elevenlabs_voices(force=False):
    """Voices the saved key can use through the API, cached for ten minutes.
    Library voices that the plan blocks (HTTP 402) are listed but flagged."""
    key = _elevenlabs_key()
    if not key:
        return []
    if not force and _elevenlabs_voices_cache["voices"] and time.time() - _elevenlabs_voices_cache["at"] < 600:
        return _elevenlabs_voices_cache["voices"]
    req = urllib.request.Request("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            payload = json.loads(r.read().decode())
    except Exception:
        return _elevenlabs_voices_cache["voices"]
    voices = []
    for v in payload.get("voices", []):
        labels = v.get("labels") or {}
        cat = v.get("category") or ""
        voices.append({"id": v.get("voice_id"), "name": (v.get("name") or "").split(" - ")[0],
                       "description": (v.get("name") or "").partition(" - ")[2] or labels.get("description") or "",
                       "gender": labels.get("gender", ""), "accent": labels.get("accent", ""),
                       "category": cat, "free": cat in ("premade", "generated", "cloned")})
    voices.sort(key=lambda v: (not v["free"], v["name"]))
    _elevenlabs_voices_cache.update(at=time.time(), voices=voices)
    return voices


def _elevenlabs_key():
    key = (os.environ.get("ELEVENLABS_API_KEY") or "").strip()
    if not key:
        try:
            key = (Path(os.environ.get("STUDIO_STATE_DIR", str(Path.home() / ".local/share/mtdi-studio"))) / "elevenlabs.key").read_text().strip()
        except OSError:
            key = ""
    return key


def elevenlabs_key_configured():
    return bool(_elevenlabs_key())


def elevenlabs_key_check(key):
    """None when ElevenLabs accepts the key for text-to-speech, else a short reason."""
    for voice in (elevenlabs_voice_id(), ELEVENLABS_FALLBACK_VOICE):
        try:
            _elevenlabs_tts(key, voice, "Hi.", timeout=12)
            return None
        except urllib.error.HTTPError as error:
            if error.code == 402 and voice != ELEVENLABS_FALLBACK_VOICE:
                continue
            detail = ""
            try:
                detail = json.loads(error.read().decode())["detail"]["message"][:120]
            except Exception:
                pass
            return "ElevenLabs rejected this key (HTTP %d): %s" % (error.code, detail or "check that it has text-to-speech permission")
        except Exception as error:
            return "Could not reach ElevenLabs: " + str(error)[:80]
    return "ElevenLabs rejected this key"


def _elevenlabs_tts(key, voice, text, timeout=20):
    body = json.dumps({"text": text[:600], "model_id": "eleven_turbo_v2_5",
                       "voice_settings": {"stability": 0.45, "similarity_boost": 0.8, "style": 0.2}}).encode()
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_22050_32",
                                 data=body, method="POST",
                                 headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def elevenlabs_speech(text, voice=None):
    """MP3 bytes for NVTRA's voice from ElevenLabs, or (None, reason).

    The preferred voice is a library voice that free accounts cannot use through the API
    (HTTP 402); when that happens the premade fallback voice is used and the preferred one
    is retried an hour later, so an upgraded plan switches voices on its own."""
    key = _elevenlabs_key()
    if not key:
        return None, "no ElevenLabs key configured"
    if instrument_offline():
        return None, "offline mode"
    preferred = re.sub(r"[^A-Za-z0-9_-]", "", voice or "") or elevenlabs_voice_id()
    blocked_until = _elevenlabs_blocked.get(preferred, 0.0)
    voices = [preferred, ELEVENLABS_FALLBACK_VOICE] if time.time() > blocked_until else [ELEVENLABS_FALLBACK_VOICE]
    if preferred == ELEVENLABS_FALLBACK_VOICE:
        voices = [preferred]
    last = "no voice"
    for voice in voices:
        try:
            return _elevenlabs_tts(key, voice, text), None
        except urllib.error.HTTPError as exc:
            last = f"http-{exc.code}"
            if exc.code == 402 and voice == preferred:
                _elevenlabs_blocked[preferred] = time.time() + 3600
                continue
            return None, last
        except Exception as exc:
            return None, str(exc)[:80]
    return None, last


def _credential_for(provider):
    """Any saved or environment key for one provider (not only the active one)."""
    env = {"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY", "groq": "GROQ_API_KEY"}.get(provider)
    if env and os.environ.get(env, "").strip():
        return os.environ[env].strip()
    with nvtra_keys_lock:
        for it in nvtra_keys["items"]:
            if (it.get("provider") or _key_provider(it["key"])) == provider:
                return it["key"].strip()
    return ""


def _multipart(fields, filch2f, filename, mimetype, data):
    boundary = "----studio" + hashlib.md5(os.urandom(8)).hexdigest()
    body = b""
    for k, v in fields.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{filch2f}\"; filename=\"{filename}\"\r\n"
             f"Content-Type: {mimetype}\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


_stt_cooldown = {}
_whisper = {"model": None, "name": None, "error": None, "loading": False, "lock": threading.Lock()}
WHISPER_PROMPT = ("Hey Novatra. Novatra, NVTRA, MTDI, MTDI Studio, Aether, baseline, relock, calibration, "
                  "open page one, open page two, open page three, go to settings, turn on the camera, scroll down.")


def local_whisper_status():
    return {"available": _whisper["model"] is not None, "model": _whisper["name"], "loading": _whisper["loading"], "error": _whisper["error"]}


def _local_whisper():
    """faster-whisper on this host itself (offline, no quota). Loaded once in the background; the
    model name comes from NVTRA_WHISPER_MODEL (base.en by default: 2.5 s per utterance on this host 5 and word perfect on the instrument vocabulary; small.en is 3x slower)."""
    if _whisper["model"] is not None or _whisper["error"] or _whisper["loading"]:
        return _whisper["model"]
    with _whisper["lock"]:
        if _whisper["model"] is not None or _whisper["loading"]:
            return _whisper["model"]
        _whisper["loading"] = True

    def load():
        try:
            from faster_whisper import WhisperModel
            name = os.environ.get("NVTRA_WHISPER_MODEL", "base.en").strip() or "base.en"
            # two threads: the acquisition loops, the HTTPS server and the D4 engine share the
            # same four cores; a four thread decode starved them and froze the instrument
            threads = int(os.environ.get("NVTRA_WHISPER_THREADS", "2") or 2)
            _whisper["model"] = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=threads)
            _whisper["name"] = name
        except Exception as exc:
            _whisper["error"] = f"local whisper unavailable: {str(exc)[:120]}"
        finally:
            _whisper["loading"] = False
    threading.Thread(target=load, name="nvtra-whisper-load", daemon=True).start()
    return None


def _transcribe_local(data, mimetype):
    model = _local_whisper()
    if model is None:
        return None, _whisper["error"] or "local whisper loading"
    import io, wave
    import numpy as np
    try:
        if mimetype.startswith("audio/wav") or data[:4] == b"RIFF":
            with wave.open(io.BytesIO(data)) as w:
                rate, n = w.getframerate(), w.getnframes()
                pcm = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
                if w.getnchannels() > 1:
                    pcm = pcm.reshape(-1, w.getnchannels()).mean(axis=1)
            if rate != 16000:
                idx = np.arange(0, pcm.size, rate / 16000.0)
                pcm = np.interp(idx, np.arange(pcm.size), pcm).astype(np.float32)
        else:
            return None, "local whisper needs 16 kHz WAV"
        # a little gain normalisation: quiet laptop microphones sit far below full scale
        peak = float(np.max(np.abs(pcm))) if pcm.size else 0.0
        if 0 < peak < 0.3:
            pcm = pcm * (0.5 / peak)
        if pcm.size > 16000 * 25:
            pcm = pcm[-16000 * 25:]          # never decode more than 25 s
        # one decode at a time, and never wait more than 8 s for the lock: a second utterance
        # arriving while one is decoding falls through to the cloud engines instead of queueing
        if not _whisper["lock"].acquire(timeout=8.0):
            return None, "local whisper busy"
        try:
            result = {}
            timed_out = {"v": False}
            def decode():
                try:
                    segments, _info = model.transcribe(pcm, language="en", beam_size=3, best_of=3, temperature=0.0,
                                                       initial_prompt=WHISPER_PROMPT, condition_on_previous_text=False,
                                                       vad_filter=True, vad_parameters={"min_silence_duration_ms": 300},
                                                       no_speech_threshold=0.5, log_prob_threshold=-1.2)
                    result["text"] = " ".join(seg.text.strip() for seg in segments).strip()
                except Exception as exc:
                    result["error"] = str(exc)[:100]
                finally:
                    if timed_out["v"]:
                        _whisper["lock"].release()   # the runaway decode keeps the lock until it ends
            worker = threading.Thread(target=decode, name="nvtra-whisper", daemon=True)
            worker.start()
            # long questions take longer to decode than short commands: allow ~2.5 s per second of
            # audio, never less than the configured floor and never more than 28 s
            budget = max(float(os.environ.get("NVTRA_WHISPER_TIMEOUT", "12")), min(28.0, 3.0 + 2.5 * pcm.size / 16000.0))
            worker.join(timeout=budget)
            if worker.is_alive():
                timed_out["v"] = True
                return None, "local whisper timed out"
            if "error" in result:
                return None, "local whisper: " + result["error"]
            text = result["text"]
        finally:
            if not timed_out["v"]:
                _whisper["lock"].release()
        # the wake word in its many spellings
        text = re.sub(r"\b(no|na|ne|nu)[vb]a?(tra|tro|dra|tara|ttra)\b", "Novatra", text, flags=re.I)
        return text, f"local-whisper-{_whisper['name']}"
    except Exception as exc:
        return None, f"local whisper: {str(exc)[:100]}"


def transcribe_audio(data, mimetype="audio/wav"):
    """Speech to text for NVTRA: Groq Whisper (fast, accurate), then Gemini audio, then
    OpenAI Whisper. Returns (text, engine) or (None, reason)."""
    if len(data) < 2000:
        return "", "empty"
    # Local Whisper first: offline, no quota, and the prompt teaches it the instrument's words.
    local_text, local_engine = _transcribe_local(data, mimetype)
    if local_text is not None:
        return local_text, local_engine
    if instrument_offline():
        return None, "offline mode; " + local_engine
    if not any(_credential_for(p) for p in ("groq", "gemini", "openai")):
        return None, local_engine + "; no Groq, Gemini or OpenAI key for transcription"
    # A provider that answered 429 stays out of the rotation for five minutes; without this, every
    # utterance waited on the same dead quota before falling through.
    now = time.time()
    skip = {p for p, until in _stt_cooldown.items() if until > now}
    prompt = "Hey Novatra. NVTRA, Novatra, MTDI, MTDI Studio, Aether, baseline, relock, page one, page two, page three, settings."
    key = "" if "groq" in skip else _credential_for("groq")
    if key:
        body, ctype = _multipart({"model": "whisper-large-v3", "language": "en", "response_format": "json",
                                  "temperature": "0", "prompt": prompt}, "file", "speech.wav", mimetype, data)
        req = urllib.request.Request("https://api.groq.com/openai/v1/audio/transcriptions", data=body, method="POST",
                                     headers={"Authorization": "Bearer " + key, "Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return (json.loads(r.read().decode()).get("text") or "").strip(), "groq-whisper"
        except Exception as exc:
            last = "groq: " + str(exc)[:80]
            if "429" in last:
                _stt_cooldown["groq"] = now + 300
    else:
        last = "no groq key"
    key = "" if "gemini" in skip else _credential_for("gemini")
    if key:
        body = {"contents": [{"role": "user", "parts": [
            {"text": "You are a speech-to-text engine. Transcribe this English speech exactly, word for word, even if the speaker talks fast, mumbles, slurs or has a South African accent; do not paraphrase, do not add anything, do not answer questions in it. Reply with the transcript only; reply with an empty string if there is no speech. Names that may occur: " + prompt + ". Any word that sounds like Novatra, Nevada, Navarra, Nova, NVTRA is the assistant's name and should be written Novatra."},
            {"inline_data": {"mime_type": mimetype, "data": base64.b64encode(data).decode()}}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 200, "thinkingConfig": {"thinkingBudget": 0}}}
        for model in GEMINI_MODELS:
            reply, err, retryable = _gemini_call(model, key, body)
            if reply is None and err and "thinking" in err.lower():
                plain = json.loads(json.dumps(body)); plain["generationConfig"].pop("thinkingConfig", None)
                reply, err, retryable = _gemini_call(model, key, plain)
            if reply is not None:
                return reply.strip().strip('"'), "gemini-audio"
            last = "gemini: " + str(err)[:80]
            if not retryable:
                break
        if "429" in last:
            _stt_cooldown["gemini"] = now + 300
    key = "" if "openai" in skip else _credential_for("openai")
    if key:
        body, ctype = _multipart({"model": "whisper-1", "language": "en", "prompt": prompt}, "file", "speech.wav", mimetype, data)
        req = urllib.request.Request("https://api.openai.com/v1/audio/transcriptions", data=body, method="POST",
                                     headers={"Authorization": "Bearer " + key, "Content-Type": ctype})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return (json.loads(r.read().decode()).get("text") or "").strip(), "openai-whisper"
        except Exception as exc:
            last = "openai: " + str(exc)[:80]
            if "429" in last:
                _stt_cooldown["openai"] = now + 300
    return None, last


# ── character moves ───────────────────────────────────────────────────────────
# The NVTRA character can be told to move: "backflip and wave after" runs both, in
# that order. Order is taken from where each word appears in the sentence, not from
# the order of this table, so "wave, then backflip" does the opposite.
#
# Split into strong and weak deliberately. This is an composite instrument:
# "wave", "point", "spin" and "peak" are ordinary vocabulary here, and a question
# like "what does a radio wave look like" must not make the character wave. Weak
# words only count when a strong move word is also present, or when the sentence is
# plainly an instruction to him. Strong words have no other meaning in this app.
CHARACTER_STRONG = {
    "backflip": ("backflip", "back flip", "back-flip", "somersault", "flip"),
    "salute": ("salute",),
    "bow": ("bow", "take a bow"),
    "dance": ("dance", "dancing", "boogie"),
    "thumbsup": ("thumbs up", "thumbs-up"),
    "thumbsdown": ("thumbs down", "thumbs-down"),
}
CHARACTER_WEAK = {
    "wave": ("wave", "say hi", "say hello", "greet"),
    "jump": ("jump", "hop", "leap"),
    "spin": ("spin", "twirl", "turn around"),
    "nod": ("nod",),
    "shake": ("shake your head",),
    "peace": ("peace sign", "peace"),
    "fist": ("fist bump", "fist"),
    "point": ("point at", "point to"),
}
CHARACTER_CUES = ("do a", "do the", "can you", "could you", "show me", "give me",
                  "perform", "let's see", "lets see", "again", "and then", "after")


def _character_actions(t):
    """Move names in the order they are spoken. Empty when nothing is asked for."""
    found = []
    for name, words in CHARACTER_STRONG.items():
        for word in words:
            at = re.search(r"\b" + re.escape(word) + r"\b", t)
            if at:
                found.append((at.start(), name))
                break
    strong = bool(found)
    cue = strong or any(c in t for c in CHARACTER_CUES)
    if cue:
        for name, words in CHARACTER_WEAK.items():
            for word in words:
                at = re.search(r"\b" + re.escape(word) + r"\b", t)
                if at:
                    found.append((at.start(), name))
                    break
    if not found:
        return []
    # De-duplicate by name, keeping the first mention, then restore spoken order.
    seen, ordered = set(), []
    for position, name in sorted(found):
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return [{"type": "character", "target": ",".join(ordered[:6])}]


def _agent_fallback(text):
    """Deterministic command parsing when no model is reachable."""
    t = text.lower()
    actions = []
    for name, path in AGENT_PAGES.items():
        if name in t and any(v in t for v in ("open", "go to", "show", "take me", "navigate", "switch to")):
            actions.append({"type": "navigate", "target": path})
            break
    if "ch2" in t and "field" in t and "/page-1" in [a["target"] for a in actions]:
        actions.append({"type": "tab", "target": "c2x"})
    if "wifi" in t or "wi fi" in t:
        actions.append({"type": "tab", "target": "wifi"})
    if "bluetooth" in t:
        actions.append({"type": "tab", "target": "bt"})
    # Mentioning the camera used to switch it on, so "what does the camera do" started the
    # camera, and "where is my mouse" grabbed the cursor. Both need an explicit instruction.
    # "turn <up to three words> on/off" covers "turn it on", "turn the camera off" and
    # "turn the finger cursor off" without matching the "on" in "is the camera on".
    turn_on = re.search(r"\b(?:enable|activate|start)\b|\b(?:turn|switch)\s+(?:\w+\s+){0,3}on\b", t)
    turn_off = re.search(r"\b(?:disable|deactivate|stop)\b|\b(?:turn|switch)\s+(?:\w+\s+){0,3}off\b", t)
    if "camera" in t and (turn_on or turn_off):
        actions.append({"type": "camera", "target": "off" if turn_off else "on"})
    if ("finger" in t or "mouse" in t) and (turn_on or turn_off):
        actions.append({"type": "finger_mouse", "target": "off" if turn_off else "on"})
    if "scroll" in t:
        # "scroll to the top" contains neither "up" nor "down", so it used to fall through
        # to "down" and scroll the opposite way. runActions already handles top and bottom.
        target = ("top" if "top" in t else "bottom" if "bottom" in t
                  else "up" if "up" in t else "down")
        actions.append({"type": "scroll", "target": target})
    actions.extend(_character_actions(t))
    if "offline" in t and "mode" in t:
        actions.append({"type": "mode", "target": "offline"})
    if "online" in t and "mode" in t:
        actions.append({"type": "mode", "target": "online"})
    # Relocking is destructive: the baselines are deliberately frozen, and relearning them
    # mid-measurement discards the reference every deviation is quoted against. The word
    # "baseline" alone used to be enough, so the question "how was the baseline learned"
    # silently relocked all four channels. Require an explicit instruction.
    if "relock" in t or "relearn" in t or ("baseline" in t and any(
            v in t for v in ("relock", "relearn", "reset", "recalibrate", "redo", "take a new", "learn a new"))):
        actions.append({"type": "relock", "target": "all"})
    say = ("Done." if actions else
           'I did not catch a command I can run. Try: open the channel 3 page, relock the baseline, or enable the camera.')
    return {"say": say, "actions": actions, "source": "rules"}


COMMAND_WORDS = ("open", "go to", "show", "switch", "enable", "disable", "turn on", "turn off", "start", "stop",
                 "scroll", "relock", "baseline", "finger", "offline mode", "online mode", "camera",
                 "backflip", "somersault", "salute", "dance", "thumbs up", "thumbs down", "take a bow")


def _parse_agent_reply(reply):
    """Models sometimes wrap the JSON in code fences or write say(...) instead of JSON."""
    body = re.sub(r"^```[a-z]*|```$", "", reply.strip(), flags=re.M).strip()
    match = re.search(r"\{[\s\S]*\}", body)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except ValueError:
            pass
    spoken = re.search(r"\bsay\s*[:(=]\s*(.+?)\s*(?:\)\s*$|,\s*\"?actions|$)", body, flags=re.I | re.S)
    if spoken:
        said = spoken.group(1).strip().strip("\"'").strip()
        if said:
            return {"say": said, "actions": []}
    # A cut-off JSON reply: salvage whatever text followed "say".
    partial = re.search(r"\"say\"\s*:\s*\"([^\"]*)", body)
    if partial and partial.group(1).strip():
        return {"say": partial.group(1).strip(), "actions": []}
    return {}


def _clean_say(text):
    """Plain spoken text: no JSON scaffolding, brackets, quotes or markdown."""
    text = re.sub(r"^\s*(json|javascript)\b\s*", "", text, flags=re.I)
    text = re.sub(r"[{}\[\]\"`*#_]", "", text)
    text = re.sub(r"^\s*(json|javascript)\b\s*", "", text, flags=re.I)
    text = re.sub(r"^\s*(say|response|answer)\s*[:(=]?\s*", "", text, flags=re.I)
    text = re.sub(r",?\s*actions\s*[:=]?\s*.*$", "", text, flags=re.I | re.S)
    text = re.sub(r"\s*\)\s*$", "", text)
    text = re.sub(r"\s+", " ", text).strip().strip(",").strip()
    return text or "Sorry, I did not catch that."


_agent_history = []  # last few turns so follow-up questions make sense


def nvtra_agent(text, image_b64=None):
    """Turn a spoken or typed request into a reply and interface actions.

    Plain commands are executed immediately by the rule parser (no model round trip);
    questions go to the selected model, with the camera frame when one is supplied so
    NVTRA can describe what the operator sees.
    """
    text = str(text or "").strip()
    if not text:
        raise ValueError("Say or type a request first")
    text = re.sub(r"^\s*(hey|hi|ok|okay|yo)?[ ,]*(n[aeo]+\s?v[aeo]+\s?[td]+[rh]*[aeo]*\w*|n[aeo]+v[aeo]+r+[aeo]*\w*|nvtra|nova)\b[ ,]*", "", text, flags=re.I).strip() or text
    lowered = text.lower()
    if any(word in lowered for word in COMMAND_WORDS) and "?" not in text and not lowered.startswith(("what", "how", "why", "is ", "are ", "can ", "tell", "describe", "explain")):
        quick = _agent_fallback(text)
        if quick["actions"]:
            quick["source"] = "instant"
            return quick
    context = _nvtra_context()
    context = context[:3200]
    system_text = (NVTRA_PERSONA + "\n\nYou are now acting as NVTRA, the instrument's voice agent (say it as Novatra). "
                   + AGENT_ACTIONS_DOC + ("\nA camera frame from the operator's webcam is attached: you may describe what is visible when asked." if image_b64 else "")
                   + "\n\nCurrent time: " + _agent_clock_text()
                   + "\n\n=== LIVE INSTRUMENT CONTEXT ===\n" + context)
    key, prov = _active_ai_credential()
    turns = [t for t in _agent_history[-6:]] + [{"role": "user", "text": text}]
    if image_b64 and prov == "gemini" and key and not instrument_offline():
        reply, err = _gen_gemini(key, system_text, turns, 700, image_b64=image_b64)
    else:
        reply, err = _selected_ai_generate(system_text, turns, max_output_tokens=700)
    if err or not reply:
        result = _agent_fallback(text)
        result["note"] = _nvtra_error_text(err) if err else "Model returned nothing"
        if not result["actions"] and local_ai_status()["available"]:
            # A question with no runnable command: let the local model answer from the live context.
            local_reply, local_err = _gen_ollama(
                "Answer in one or two short spoken sentences using only these live readings.\n" + _nvtra_context(),
                [{"role": "user", "text": text}], 120)
            if local_reply and not local_err:
                result["say"] = local_reply.strip()[:400]
                result["source"] = "local model"
        return result
    data = _parse_agent_reply(reply)
    actions = []
    allowed = {"navigate", "tab", "mode", "camera", "finger_mouse", "scroll", "relock", "character"}
    for item in data.get("actions") or []:
        if isinstance(item, dict) and item.get("type") in allowed:
            actions.append({"type": item["type"], "target": str(item.get("target", ""))[:40]})
    say = _clean_say(str(data.get("say") or reply))[:900]
    if not data:
        fallback = _agent_fallback(text)
        actions = fallback["actions"]
    _agent_history.append({"role": "user", "text": text[:300]})
    _agent_history.append({"role": "assistant", "text": json.dumps({"say": say, "actions": actions})})
    del _agent_history[:-8]
    return {"say": say, "actions": actions, "source": "model"}


def _agent_clock_text():
    """Local and UTC clock so NVTRA can answer 'what is the time in X' by offset."""
    import datetime as _dt
    now = _dt.datetime.now().astimezone()
    utc = _dt.datetime.now(_dt.timezone.utc)
    return (f"{now.strftime('%A %d %B %Y, %H:%M')} local ({now.strftime('%Z')}, UTC{now.strftime('%z')}); "
            f"UTC {utc.strftime('%H:%M')}. Convert to other zones by their UTC offset (South Africa is UTC+2).")


def _nvtra_signal_notes():
    """SG screen findings, baseline/probe events and the recent trend, for the NVTRA prompt.

    Everything here is derived from measured data already held by the instrument; failures
    (module not loaded yet, no archive) just omit the line rather than inventing one."""
    import importlib
    lines = []
    try:
        charts = importlib.import_module("studio.charts")
        with sweep3_lock:
            findings = charts.sg_findings(sweep3_data)[:4]
        if findings:
            items = "; ".join(f"{f['title']} ({f['severity']}: {f['detail']})" for f in findings)
            lines.append("interference screen (heuristic, sources are only 'possible'): " + items[:600])
        elif sweep3_data.get("last_rx") is not None and not sweep3_data.get("error"):
            lines.append('interference screen: no harmonic, comb, broadband or intermittent pattern in the current sweep.')
    except Exception:
        pass
    try:
        runtime = getattr(importlib.import_module("studio.common"), "INSTRUMENT_RUNTIME", None)
        events = list(runtime.events)[-5:] if runtime is not None else []
        if events:
            now = time.time()
            items = "; ".join(f"{max(0, now - e['timestamp']):.0f}s ago [{e['source']}] {e['message'][:90]}" for e in reversed(events))
            lines.append("Recent instrument events (newest first): " + items)
        snap = runtime.engine.snapshot() if runtime is not None else None
        if snap:
            for key, item in snap.get("channels", {}).items():
                hist = item.get("history") or []
                if len(hist) >= 20:
                    early = statistics.median(p["deviation"] for p in hist[: len(hist) // 4])
                    late = statistics.median(p["deviation"] for p in hist[-len(hist) // 4:])
                    span = hist[-1]["t"] - hist[0]["t"]
                    word = "steady" if abs(late - early) < 1e-9 or abs(late - early) < 0.05 * max(abs(early), abs(late), 1e-9) + 1e-6 else ("rising" if late > early else "falling")
                    lines.append(f"Trend {key} (last {span:.0f} s): {word}, deviation {early:+.3g} -> {late:+.3g} {item.get('unit', '')}.")
                stale = (item.get("baseline") or {}).get("stale_for")
                if stale:
                    lines.append(f"{key} baseline lock has been stale for {stale:.0f} s (quiet level drifted).")
    except Exception:
        pass
    return lines


def _nvtra_context():
    """A compact, factual snapshot of the live instrument, injected into every prompt.
    The assistant must answer from THIS — it is not allowed to invent sensor numbers."""
    lines = []
    with c1_lock:
        if ch1_data["error"]:
            lines.append(f"Channel 1: OFFLINE ({ch1_data['error'][:60]})")
        else:
            m = ch1_data
            raw_c1 = m.get("raw_magnitude")
            if raw_c1 is not None:
                # hardware path: 'magnitude' is the deviation from the quiet baseline, the raw
                # field magnitude is separate. Both are stated so the model never calls a
                # 0.02 uT deviation "the total field".
                lines.append(f"Ch1probe: change from the quiet baseline {m['magnitude']:+.3f} uT "
                             f"(component changes X {m['x']:+.3f}, Y {m['y']:+.3f}, Z {m['z']:+.3f}); "
                             f"session change range {m['min_c1']:.3f}-{m['max_c1']:.3f} uT. "
                             f"Raw field magnitude {raw_c1:.2f} uT with factory scaling (absolute accuracy unknown; "
                             f"Earth's field is normally 25-65 uT, so quote the raw value only as 'sensor reading').")
            else:
                lines.append(f"Ch1probe: {m['magnitude']:.2f} uT total "
                             f"(X {m['x']:.2f}, Y {m['y']:.2f}, Z {m['z']:.2f}); "
                             f"session min {m['min_c1']:.2f}, max {m['max_c1']:.2f} uT. "
                             f"Earth's field is normally 25-65 uT.")
    with ch2f_lock:
        e = ch2f_data
        if e["error"]:
            lines.append(f"Channel 2: OFFLINE ({e['error'][:60]})")
        elif not e["calibrated"]:
            lines.append('Channel 2: still settling its quiet baseline (first minute after start).')
        elif not e.get("probe_calibrated", True):
            # no V/m scaling: the honest numbers are the raw RMS and the change from baseline
            dev = e["rms_mv"] - e["baseline_mv"]
            lines.append(f"Ch2 probe: {e['rms_mv']:.2f} mV RMS raw, {dev:+.2f} mV RMS relative to the quiet baseline "
                         f"({'above' if dev > 0 else 'at or below'} baseline), relative activity {e['rel_index']:.0f}%. "
                         f"The probe has no V/m calibration, so there is no absolute field value; say so if asked for V/m.")
        else:
            lines.append(f"Ch2 probe: {e['field_vu']:.3f} V/m "
                         f"({e['field_vu']:.3f} N/C), level {e['level']}, "
                         f"relative activity {e['rel_index']:.0f}%.")
    with sweep3_lock:
        s = sweep3_data
        if s["error"] or s["last_rx"] is None:
            lines.append(f"Channel 3 analyser (Source 3): OFFLINE ({(s['error'] or 'no sweep yet')[:50]})")
        else:
            peak_txt = ", ".join(f"{_freq_label(p['freq'])} at {p['level']:.0f} unit ({p['band']})"
                                 for p in s["peaks"][:4]) or "none above the floor"
            lines.append(f"Sweep3 (src3, {_span_label(s['span_start'], s['span_stop'])}): "
                         f"noise floor {s['floor']:.0f} dBm; strongest peak "
                         f"{_freq_label(s['peak_freq'])} at {s['peak_level']:.0f} dBm. "
                         f"Tracked peaks: {peak_txt}.")
            if not s["level_sane"]:
                lines.append(
                    "NOTE: sweep3 levels are untrusted; verify parser, units and analyser state."
                )
    with wifi_lock:
        if not wifi_data["error"] and wifi_data["last_rx"]:
            names = ", ".join(n["ssid"] for n in wifi_data["networks"][:6]) or "none"
            lines.append(f"Channel 5: {len(wifi_data['networks'])} networks in range ({names}).")
    with bt_lock:
        if not bt_data["error"] and bt_data["last_rx"]:
            lines.append(f"Channel 6: {len(bt_data['devices'])} devices advertising nearby.")
    lines.extend(_nvtra_signal_notes())
    with mtdi_lock:
        lines.append(
            f"MTDI active sensor health: {mtdi_data['active_health']:.0f}%; "
            f"system completeness: {mtdi_data['completeness']:.0f}% "
            f"(ch1probe {mtdi_data['c1_health']:.0f}%, "
            f"Ch2 {mtdi_data['ch2f_health']:.0f}%, "
            f"sweep3 {mtdi_data['ch3_health']:.0f}%)."
        )
    return "\n".join(lines)


NVTRA_PERSONA = (
    "You are NVTRA, the built-in assistant for this MTDI Studio, a template interface "
    "built on MTDI (Microprocessing Technological Diagnostic Intelligence) and the I³ "
    "interface (Induction, Interference, Intelligence). The studio has these pages: Home, "
    "Page 1, Page 2, MTDI, Page 3 and Settings. MTDI is its self-diagnostic health and "
    "completeness framework, with five pillars: Validation Chamber, Environmental "
    "Intelligence, NVTRA, I³ and Aether. No data source is connected unless the CONTEXT "
    "below shows live channels.\n\n"
    "Your job is to help the operator understand what they are seeing. Assume they may be a "
    "beginner. Explain plainly, briefly (2-4 short sentences unless asked for more), and "
    "concretely. When useful, quote the live readings from the CONTEXT below.\n\n"
    "Honesty rules you must follow:\n"
    "- Only state values that appear in the CONTEXT. Never invent a reading or a "
    "device that is not there. If the answer is not in the CONTEXT, say so.\n"
    "- You run on a commercial large language model via an API key the operator supplied. "
    "If asked what you are, say so honestly; do not claim to be a custom-built AI.\n"
    "- Do not give instructions for intercepting private communications or "
    "defeating security.\n\n"
    "Keep the tone calm and technical. "
    "Reply in plain text only — no markdown, no LaTeX, no asterisks, no emoji."
)


def _gemini_call(model, key, body):
    """One generateContent call to one model. Returns (reply, error, retryable)."""
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={key}")
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=AI_REQUEST_TIMEOUT) as r:
            payload = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            emsg = json.loads(e.read().decode())["error"]["message"]
        except Exception:
            emsg = e.reason
        # 429 (no quota on THIS model) and 404 (model gone) are worth retrying on the
        # next model in the list; 400/403 (bad key/request) will fail everywhere.
        return None, f"http-{e.code}: {emsg[:140]}", e.code in (429, 404)
    except urllib.error.URLError as e:
        if isinstance(e.reason, (TimeoutError, socket.timeout)):
            return None, "timeout: provider did not respond in time", False
        return None, f"network: {e.reason}", False
    except (TimeoutError, socket.timeout):
        return None, "timeout: provider did not respond in time", False
    except Exception as e:
        return None, f"{e}"[:140], False
    cands = payload.get("candidates") or []
    if not cands:
        fb = (payload.get("promptFeedback") or {}).get("blockReason", "no candidates")
        return None, f"blocked: {fb}", False
    parts = (cands[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        return None, f"empty ({cands[0].get('finishReason', 'unknown')})", False
    return text, None, False


# ── Instrument mode: online (cloud providers allowed) or offline (local only) ──
# The browser asks the operator at every startup. The choice is enforced here so no
# cloud request leaves this host while offline, whatever keys are configured.
INSTRUMENT_MODE = {"mode": os.environ.get("STUDIO_MODE", "online"), "internet": None, "checked_at": 0.0}
OLLAMA_URL = os.environ.get("STUDIO_OLLAMA_URL", "http://127.0.0.1:11434")
# A llama.cpp server (llama_cpp.server) is the lighter engine used on this Pi; it
# speaks the same OpenAI style API. Both are probed, Ollama first.
LLAMACPP_URL = os.environ.get("STUDIO_LLAMACPP_URL", "http://127.0.0.1:11435")
# Preference order, lightest first. smollm2:135m is the smallest chat model in the
# Ollama library (135 million parameters, about 270 MB); qwen2.5:0.5b (494 million,
# about 400 MB) is the next step up and noticeably more coherent.
OLLAMA_MODELS = [m for m in [os.environ.get("STUDIO_OLLAMA_MODEL", "").strip(),
                             "smollm2:135m", "qwen2.5:0.5b", "qwen2.5:1.5b", "qwen2.5:3b", "llama3.2:1b"] if m]
LOCAL_AI_TIMEOUT = float(os.environ.get("STUDIO_LOCAL_AI_TIMEOUT", "240"))
_local_ai_cache = {"at": 0.0, "status": None}


def instrument_offline():
    return INSTRUMENT_MODE.get("mode") == "offline"


def internet_reachable(max_age=30.0):
    """Cheap TCP reachability probe, cached; never blocks a request for long."""
    now = time.time()
    if INSTRUMENT_MODE["internet"] is not None and now - INSTRUMENT_MODE["checked_at"] < max_age:
        return INSTRUMENT_MODE["internet"]
    ok = False
    for host, port in (("1.1.1.1", 443), ("8.8.8.8", 53)):
        try:
            with socket.create_connection((host, port), timeout=1.5):
                ok = True
                break
        except OSError:
            continue
    INSTRUMENT_MODE.update(internet=ok, checked_at=now)
    return ok


def local_ai_status(max_age=20.0):
    """Report the local Ollama service and which preferred model is installed."""
    now = time.time()
    if _local_ai_cache["status"] is not None and now - _local_ai_cache["at"] < max_age:
        return _local_ai_cache["status"]
    status = {"available": False, "model": None, "models": [], "error": None, "url": OLLAMA_URL, "engine": None}
    try:
        names = []
        try:
            with urllib.request.urlopen(OLLAMA_URL + "/api/tags", timeout=2) as r:
                tags = json.loads(r.read().decode())
            names = [item.get("name", "") for item in tags.get("models", [])]
            status["engine"] = "ollama"
        except Exception as ollama_exc:
            with urllib.request.urlopen(LLAMACPP_URL + "/v1/models", timeout=2) as r:
                listing = json.loads(r.read().decode())
            names = [os.path.basename(str(item.get("id", ""))) for item in listing.get("data", [])]
            status.update(engine="llama.cpp", url=LLAMACPP_URL)
            if not names:
                raise ollama_exc
        status["models"] = names
        for preferred in OLLAMA_MODELS:
            stem = preferred.split(":")[0].lower()
            match = next((n for n in names if n == preferred or stem in n.lower().replace("-", "")), None)
            if match:
                status.update(available=True, model=match)
                break
        if not status["available"]:
            status["error"] = "Ollama is running but no chat model is installed yet" if not names else f"No preferred model among {', '.join(names[:4])}"
            if names and not status["available"]:
                status.update(available=True, model=names[0], error=None)
    except Exception as exc:
        status["error"] = f"Local model service unavailable: {str(exc)[:80]}"
    _local_ai_cache.update(at=now, status=status)
    return status


def _gen_ollama(system_text, history, max_output_tokens=350):
    """Fully local generation through Ollama's OpenAI compatible endpoint."""
    status = local_ai_status()
    if not status["available"]:
        return None, "no-local-model: " + (status["error"] or "")
    return _gen_openai_compatible("local", system_text, history,
                                  status["url"] + "/v1/chat/completions", [status["model"]],
                                  max_output_tokens, timeout=LOCAL_AI_TIMEOUT)


def _http_json(url, body, headers, timeout=None):
    """POST json, return (payload, error). error is 'http-CODE: msg' / 'network:' / etc."""
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={**headers, "Content-Type": "application/json"},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout or AI_REQUEST_TIMEOUT) as r:
            return json.loads(r.read().decode()), None
    except urllib.error.HTTPError as e:
        try:
            emsg = json.loads(e.read().decode())["error"]["message"]
        except Exception:
            emsg = e.reason
        return None, f"http-{e.code}: {emsg[:140]}"
    except urllib.error.URLError as e:
        if isinstance(e.reason, (TimeoutError, socket.timeout)):
            return None, "timeout: provider did not respond in time"
        return None, f"network: {e.reason}"
    except (TimeoutError, socket.timeout):
        return None, "timeout: provider did not respond in time"
    except Exception as e:
        return None, f"{e}"[:140]


def _gen_gemini(key, system_text, history, max_output_tokens=700, image_b64=None):
    contents = [{"role": ("user" if h["role"] == "user" else "model"),
                 "parts": [{"text": h["text"]}]} for h in history[-NVTRA_MAX_TURNS:]]
    if image_b64 and contents:
        # The operator's camera frame rides along with the last user turn.
        contents[-1]["parts"].append({"inline_data": {"mime_type": "image/jpeg", "data": image_b64}})
    body = {"system_instruction": {"parts": [{"text": system_text}]}, "contents": contents,
            "generationConfig": {"temperature": 0.6, "topP": 0.9,
                                 "maxOutputTokens": int(max_output_tokens),
                                 # Thinking tokens count against the output budget on the
                                 # Gemini 2.5+ models; a voice reply must not be eaten by them.
                                 "thinkingConfig": {"thinkingBudget": 0}}}
    last_err = "no-model"
    for model in GEMINI_MODELS:
        reply, err, retryable = _gemini_call(model, key, body)
        if reply is None and err and "thinking" in err.lower():
            # Older models reject thinkingConfig; retry the same model without it.
            plain = json.loads(json.dumps(body))
            plain["generationConfig"].pop("thinkingConfig", None)
            reply, err, retryable = _gemini_call(model, key, plain)
        if reply is not None:
            return reply, None
        last_err = err
        if not retryable:
            return None, err
    return None, last_err


def _gen_anthropic(key, system_text, history, max_output_tokens=700):
    msgs = [{"role": ("user" if h["role"] == "user" else "assistant"), "content": h["text"]}
            for h in history[-NVTRA_MAX_TURNS:]]
    last_err = "http-404: no Claude model"
    for model in ANTHROPIC_MODELS:
        payload, err = _http_json("https://api.anthropic.com/v1/messages",
            {"model": model, "max_tokens": int(max_output_tokens),
             "system": system_text, "messages": msgs},
            {"x-api-key": key, "anthropic-version": "2023-06-01"})
        if err:
            last_err = err
            lower_err = err.lower()
            # Anthropic may report an unavailable/retired model as either 404 or
            # 400. Only retry model-specific failures; bad keys and billing errors
            # must remain visible instead of being hidden behind more requests.
            if (err.startswith("http-404") or
                    (err.startswith("http-400") and
                     any(word in lower_err for word in
                         ("model", "not found", "does not exist", "unavailable")))):
                continue
            return None, err
        text = "".join(b.get("text", "") for b in (payload.get("content") or [])
                       if b.get("type") == "text").strip()
        return (text, None) if text else (None, "empty")
    return None, last_err


def _gen_openai(key, system_text, history, max_output_tokens=700):
    items = [{"role": ("user" if h["role"] == "user" else "assistant"),
              "content": h["text"]} for h in history[-NVTRA_MAX_TURNS:]]
    last_err = "http-404: no OpenAI model"
    for model in OPENAI_MODELS:
        payload, err = _http_json("https://api.openai.com/v1/responses",
            {"model": model, "instructions": system_text, "input": items,
             "max_output_tokens": int(max_output_tokens), "store": False},
            {"Authorization": f"Bearer {key}"})
        if err:
            last_err = err
            if err.startswith("http-404"):
                continue
            return None, err
        text = ""
        for item in payload.get("output") or []:
            for part in item.get("content") or []:
                if part.get("type") == "output_text":
                    text += part.get("text", "")
        text = text.strip()
        return (text, None) if text else (None, "empty")
    return None, last_err


def _gen_openai_compatible(key, system_text, history, url, models,
                           max_output_tokens=700, timeout=None):
    """Chat Completions transport shared by xAI Grok and Moonshot Kimi."""
    messages = [{"role": "system", "content": system_text}]
    messages.extend({
        "role": ("user" if h["role"] == "user" else "assistant"),
        "content": h["text"],
    } for h in history[-NVTRA_MAX_TURNS:])
    last_err = "http-404: no compatible model"
    for model in models:
        payload, err = _http_json(
            url,
            {"model": model, "messages": messages,
             "max_tokens": int(max_output_tokens),
             "temperature": 0.6, "stream": False},
            {"Authorization": f"Bearer {key}"}, timeout=timeout,
        )
        if err:
            last_err = err
            low = err.lower()
            if (err.startswith("http-404") or
                    (err.startswith("http-400") and "model" in low)):
                continue
            return None, err
        choices = payload.get("choices") or []
        text = (
            ((choices[0].get("message") or {}).get("content") or "").strip()
            if choices else ""
        )
        return (text, None) if text else (None, "empty")
    return None, last_err


def _gen_xai(key, system_text, history, model="", max_output_tokens=700):
    return _gen_openai_compatible(
        key, system_text, history,
        "https://api.x.ai/v1/chat/completions", [model] if model else XAI_MODELS,
        max_output_tokens,
    )


def _gen_kimi(key, system_text, history, model="", max_output_tokens=700):
    return _gen_openai_compatible(
        key, system_text, history,
        "https://api.moonshot.ai/v1/chat/completions", [model] if model else KIMI_MODELS,
        max_output_tokens,
    )


def _gen_groq(key, system_text, history, model="", max_output_tokens=700):
    return _gen_openai_compatible(
        key, system_text, history,
        "https://api.groq.com/openai/v1/chat/completions",
        [model] if model else GROQ_MODELS, max_output_tokens,
    )


def _selected_ai_generate(system_text, user_history, max_output_tokens=700):
    """Dispatch a task to the operator-selected provider and model.

    Offline mode never leaves this host: the local Ollama model answers or nothing does.
    Online mode uses the selected cloud provider and falls back to the local model
    when there is no key or the provider cannot be reached.
    """
    if instrument_offline():
        return _gen_ollama(system_text, user_history, min(max_output_tokens, 400))
    key, prov = _active_ai_credential()
    if not key:
        if local_ai_status()["available"]:
            return _gen_ollama(system_text, user_history, min(max_output_tokens, 400))
        return None, "no-key"
    selected_model = _active_ai_model()
    if prov == "anthropic":
        return _gen_anthropic(key, system_text, user_history, max_output_tokens)
    if prov == "openai":
        return _gen_openai(key, system_text, user_history, max_output_tokens)
    if prov == "xai":
        return _gen_xai(key, system_text, user_history, selected_model,
                        max_output_tokens)
    if prov == "kimi":
        return _gen_kimi(key, system_text, user_history, selected_model,
                         max_output_tokens)
    if prov == "groq":
        return _gen_groq(key, system_text, user_history, selected_model,
                         max_output_tokens)
    if prov == "gemini":
        reply, err = _gen_gemini(key, system_text, user_history, max_output_tokens)
        if err and (err.startswith("network") or err.startswith("timeout")) and local_ai_status()["available"]:
            return _gen_ollama(system_text, user_history, min(max_output_tokens, 400))
        return reply, err
    # Fail closed: an ambiguous provider must never receive an implicit network
    # destination, especially when the request contains live sensor arrays.
    return None, "unknown-provider"


def _gemini_generate(user_history):
    """Generate NVTRA chat through the active provider (legacy name retained)."""
    system_text = NVTRA_PERSONA + "\n\n=== LIVE INSTRUMENT CONTEXT ===\n" + _nvtra_context()
    return _selected_ai_generate(system_text, user_history)


def _nvtra_error_text(err):
    """Turn an internal error code into a short, actionable message for the operator.
    Messages point at Settings → AI KEYS (keys now live in the app, not in the source)."""
    if err == "no-key":
        return "No API key set. Add one in Settings → AI KEYS, or install a local model for offline mode."
    if err.startswith("no-local-model"):
        return ("Offline mode needs the local model. On this host run: ollama pull qwen2.5:3b "
                "(and make sure the ollama service is running). " + err.split(":", 1)[1].strip())
    if err == "unknown-provider":
        return "Choose the provider for the active key in Settings → AI KEYS."
    if err.startswith("http-429"):
        return ("This key is out of quota right now. Wait a few minutes, or switch to "
                "another key in Settings → AI KEYS.")
    if err.startswith("http-400"):
        low = err.lower()
        if "credit balance" in low or "billing" in low:
            return ("Claude accepted the key but this Anthropic account needs API "
                    "credits or billing enabled.")
        if "model" in low:
            return ("Claude accepted the request format, but this account cannot use "
                    "any configured Claude model. Check model access in Anthropic Console.")
        return ("The provider rejected the request. Check that the selected provider "
                "matches this key. Anthropic API keys normally begin with sk-ant-.")
    if err.startswith("http-401"):
        return ("The active key was rejected — it looks invalid or is for a different "
                "service. Check it in Settings → AI KEYS.")
    if err.startswith("http-403"):
        return ("The provider refused this key (403). Make sure it's enabled for the API. "
                "You can switch keys in Settings → AI KEYS.")
    if err.startswith("http-404"):
        return "No usable model for this key/provider right now. Try a different key."
    if err.startswith("network"):
        return "Can't reach the AI provider — check this host's internet connection."
    if err.startswith("timeout"):
        return "The AI provider timed out. Check this host connection and try again."
    if err.startswith("http-402"):
        return "The provider requires billing or available credits for this key."
    if err.startswith("empty"):
        return "That answer got cut off. Try a shorter or more specific question."
    if err.startswith("blocked"):
        return "The safety filter blocked that one. Try rewording it."
    return f"Couldn't reach the AI provider: {err}"


SG_REQUIRED_HEADINGS = (
    "CLASSIFICATION", "DIAGNOSTIC GUESS", "EVIDENCE", "CONFIDENCE",
    "LIMITATIONS", "NEXT SAFE CHECK",
)

# Basic supervised learning set for NVTRA Intelligence. These are labelled,
# operator-supplied observations measured at 1 cm; they do not alter calibration.
NVTRA_ML_REFERENCES = (
    {"label": "REFERENCE 1", "ch2_vu": 50.0, "ch1_val": 2000.0},
    {"label": "REFERENCE 2", "ch2_vu": 40.0, "ch1_val": 702.0},
)
NVTRA_PUBLIC_ML_SOURCES = (
    {"label": "SOURCE A", "scope": "Text", "doi": "Text",
     "role": "Text",
     "field_note": "Text",
     "items": ("Item 1", "Item 2", "Item 3", "Item 4", "Item 5")},
    {"label": "SOURCE B", "scope": "Text", "doi": "Text",
     "role": "Text",
     "field_note": "Text",
     "items": ("Item 1", "Item 2", "Item 3", "Item 4", "Item 5", "Item 6")},
)


def _nvtra_basic_ml(ch2_vu, ch1_val):
    """Nearest-reference classifier with rejection for an unfamiliar field pair."""
    ch2_vu = max(0.0, float(ch2_vu))
    ch1_val = max(0.0, float(ch1_val))
    ranked = []
    for row in NVTRA_ML_REFERENCES:
        # Relative feature scales keep V/m and unit comparable without pretending
        # two training examples constitute a statistically trained model.
        e_scale = max(10.0, row["ch2_vu"] * 0.50)
        b_scale = max(100.0, row["ch1_val"] * 0.35)
        distance = math.hypot(
            (ch2_vu - row["ch2_vu"]) / e_scale,
            (ch1_val - row["ch1_val"]) / b_scale,
        )
        ranked.append((distance, row))
    ranked.sort(key=lambda item: item[0])
    best_distance, best = ranked[0]
    second_distance = ranked[1][0]
    if best_distance > 2.5:
        return {
            "label": "UNKNOWN", "confidence": 0,
            "reason": "The live field pair is outside both labelled 1 cm examples.",
            "distance": best_distance,
        }
    margin = max(0.0, second_distance - best_distance)
    confidence = round(100 * min(0.95, (1 / (1 + best_distance)) * (0.55 + min(0.40, margin / 3))))
    return {
        "label": best["label"], "confidence": confidence,
        "reason": (
            f"Nearest labelled example: {best['ch2_vu']:.0f} V/m and "
            f"{best['ch1_val']:.0f} unit at 1 cm."
        ),
        "distance": best_distance,
    }


SG_ANALYST_SYSTEM = (
    "You are the analysis engine inside MTDI Studio. Analyse only the supplied "
    "numeric channel window and trust metadata. Do not identify a specific source unless "
    "the evidence supports it. Treat any uncalibrated channel as a limitation. "
    "Distinguish single-channel disturbance, coupled multi-channel disturbance, and insufficient "
    "evidence. Never invent values. Return plain text with exactly these headings: "
    "CLASSIFICATION, DIAGNOSTIC GUESS, EVIDENCE, CONFIDENCE, LIMITATIONS, NEXT SAFE CHECK. "
    "Confidence must be LOW, MEDIUM, or HIGH and must fall when a channel is stale, clipped, "
    "uncalibrated, or untrusted. This is an educated diagnostic aid, not proof of a source."
)


def _sg_missing_headings(answer):
    """Return required sections absent as standalone headings in an LLM answer."""
    lines = {
        re.sub(r"[^A-Z ]", "", line.upper()).strip()
        for line in str(answer or "").splitlines()
    }
    return [heading for heading in SG_REQUIRED_HEADINGS if heading not in lines]


def _series_features(values):
    clean = [float(value) for value in values if math.isfinite(float(value))]
    if not clean:
        return {"samples": 0}
    deltas = [b - a for a, b in zip(clean, clean[1:])]
    return {
        "samples": len(clean), "min": round(min(clean), 6),
        "max": round(max(clean), 6), "mean": round(statistics.fmean(clean), 6),
        "stddev": round(statistics.pstdev(clean), 6) if len(clean) > 1 else 0.0,
        "peak_to_peak": round(max(clean) - min(clean), 6),
        "delta_rms": round(math.sqrt(statistics.fmean([x*x for x in deltas])), 6)
                     if deltas else 0.0,
    }


def _sg_live_snapshot():
    """Capture one internally consistent, real sensor window for selected-LLM analysis."""
    now = time.time()
    with c1_lock:
        c1 = dict(ch1_data)
        c1_values = list(ch1_data["history"])[-120:]
        xyz_values = list(ch1_data["xyz_history"])[-120:]
    with ch2f_lock:
        ef = dict(ch2f_data)
        c2_values = list(ch2f_data["history"])[-120:]
        c2_relative = list(ch2f_data["rel_history"])[-120:]
    with sweep3_lock:
        ch3 = dict(sweep3_data)
        ch3_frequencies = list(sweep3_data["freqs"])
        ch3_levels = list(sweep3_data["levels"])
        ch3_peaks = [dict(item) for item in sweep3_data["peaks"][:10]]
    freshness = {
        "ch1probe_age_s": round(now - c1["last_rx"], 2) if c1["last_rx"] else None,
        "ch2f_age_s": round(now - ef["last_rx"], 2) if ef["last_rx"] else None,
        "sweep3_age_s": round(now - ch3["last_rx"], 2) if ch3["last_rx"] else None,
    }
    online_count = sum((
        c1["error"] is None and c1["last_rx"] is not None,
        ef["error"] is None and ef["last_rx"] is not None,
        ch3["error"] is None and ch3["last_rx"] is not None,
    ))
    if online_count == 0:
        return None, 'No live source stream is available for interference analysis.'
    xyz = [[round(float(v), 5) for v in row[:3]] for row in xyz_values]
    ch3_pairs = [
        [round(float(freq), 3), round(float(level), 3)]
        for freq, level in zip(ch3_frequencies, ch3_levels)
    ]
    payload = {
        "captured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "freshness": freshness,
        "trust": {
            "ch1probe_error": c1["error"], "ch1probe_calibrated": c1["calibrated"],
            "ch1probe_chip_warning": c1["chip_warning"],
            "ch2f_error": ef["error"], "ch2f_calibrated": ef["calibrated"],
            "ch2f_clipped": ef["clipped"], "ch2f_warning": ef["warning"],
            "ch2f_probe_scale_scale_per_volt": ef["probe_scale_scale_per_volt"],
            "ch2f_probe_scale_source": ef["probe_scale_source"],
            "sweep3_error": ch3["error"], "sweep3_trusted": ch3["trusted"],
            "sweep3_level_sane": ch3["level_sane"], "sweep3_warnings": ch3["warnings"],
        },
        "features": {
            "ch1_magnitude_val": _series_features(c1_values),
            "ch2_field_vu": _series_features(c2_values),
            "ch2_relative_percent": _series_features(c2_relative),
            "ch3_level_dbm": _series_features(ch3_levels),
            "ch3_noise_floor_dbm": round(float(ch3["floor"]), 3),
        },
        "arrays": {
            "ch1_magnitude_val": [round(float(v), 5) for v in c1_values],
            "ch1_xyz_val": xyz,
            "ch2_field_vu": [round(float(v), 6) for v in c2_values],
            "ch2_relative_percent": [round(float(v), 4) for v in c2_relative],
            "ch3_frequency_hz_and_level_dbm": ch3_pairs,
        },
        "tracked_ch3_peaks": ch3_peaks,
    }
    return payload, None


def nvtra_online():
    """True when the chat can answer: a cloud key online, or the local model in any mode."""
    if instrument_offline():
        return bool(local_ai_status()["available"])
    key, provider = _active_ai_credential()
    if key and provider in {"gemini", "openai", "anthropic", "xai", "groq", "kimi"}:
        return True
    return bool(local_ai_status()["available"])


def _c1_health():
    """Link/data health for the ch1probe.

    Calibration state is deliberately NOT a health penalty: running without a
    hard/soft-iron profile is the normal default and only means the vector is
    uncorrected.  Only a real fault (chip-ID mismatch) degrades health.
    """
    with c1_lock:
        err = ch1_data["error"]; last = ch1_data["last_rx"]
        chip_warning = ch1_data["chip_warning"]
        calibrated = ch1_data["calibrated"]
        c1 = ch1_data["magnitude"]; hist = list(ch1_data["history"])[-10:]
    if err: return 0.0, f"offline: {err[:48]}"
    if last is None: return 0.0, "no data yet"
    age = time.time() - last
    if age > 5: return 0.0, f"stale ({age:.0f}s)"
    if chip_warning: return 40.0, chip_warning
    if c1 > 180: return 20.0, "near saturation"
    suffix = "" if calibrated else " · uncorrected (no calibration profile)"
    if len(hist) >= 5:
        mean = sum(hist)/len(hist)
        std = math.sqrt(sum((v-mean)**2 for v in hist)/len(hist))
        if std < 0.5: return 100.0, f"stable (σ={std:.2f} unit){suffix}"
        elif std < 2.0: return 80.0, f"mild noise (σ={std:.2f} unit){suffix}"
        elif std < 5.0: return 50.0, f"noisy (σ={std:.2f} unit){suffix}"
        else: return 25.0, f"very noisy (σ={std:.1f} unit){suffix}"
    return 70.0, "warming up" + suffix


def _ch2f_health():
    with ch2f_lock:
        err = ch2f_data["error"]
        last = ch2f_data["last_rx"]
        clipped = ch2f_data["clipped"]
        calibrated = ch2f_data["calibrated"]
        warning = ch2f_data["warning"]
    if err:
        return 0.0, f"offline: {err[:48]}"
    if last is None:
        return 0.0, "no data yet"
    age = time.time() - last
    if age > 5:
        return 0.0, f"stale ({age:.0f}s)"
    if clipped:
        return 20.0, "ADC clipped; block untrusted"
    if warning:
        return 40.0, warning
    if not calibrated:
        return 60.0, "baseline calibration in progress"
    return 100.0, "fresh, in range, baseline ready"


def _ch3_health():
    """Transport/data health, not scientific accuracy."""
    with sweep3_lock:
        err = sweep3_data["error"]; last = sweep3_data["last_rx"]
        got = len(sweep3_data["levels"]); want = sweep3_data["points"]
        trusted = sweep3_data["trusted"]; floor = sweep3_data["floor"]
        sweep_s = sweep3_data["sweep_s"]; present = sweep3_data["present"]
    if err:  return 0.0, f"offline: {err[:48]}", present
    if last is None: return 0.0, "no sweep yet", present
    age = time.time() - last
    if age > max(20.0, sweep_s * 4): return 0.0, f"stale ({age:.0f}s)", present
    if want and got != want:         return 0.0, f"invalid sweep ({got}/{want} pts)", present
    if not trusted:                  return 25.0, f"untrusted level state ({floor:+.0f} unit)", present
    if floor > -40.0:                return 60.0, f"high floor ({floor:+.0f} unit)", present
    return 100.0, f"clean sweep ({got} pts, {sweep_s:.1f}s)", present

def mtdi_loop():
    while not STOP_EVENT.is_set():
        try:
            mc, mn = _c1_health()
            ec, en = _ch2f_health()
            rc, rn, _ch3_present = _ch3_health()
            with wifi_lock:
                wifi_ready = wifi_data["last_rx"] is not None and wifi_data["error"] is None
            with bt_lock:
                bt_ready = bt_data["last_rx"] is not None and bt_data["error"] is None
            with sys_lock:
                sys_ready = sys_data["uptime_str"] != "—"
            modules = [
                mc > 0, ec > 0, rc > 0, wifi_ready, bt_ready,
                ARCHIVE.session_id is not None and ARCHIVE.last_error is None,
                sys_ready,
            ]
            completeness = 100.0 * sum(modules) / len(modules)
            active_values = []
            if RUNTIME["demo"] or _env_enabled("STUDIO_ENABLE_CH1PROBE"):
                active_values.append(mc)
            if RUNTIME["demo"] or _env_enabled("STUDIO_ENABLE_CH2F"):
                active_values.append(ec)
            if RUNTIME["demo"] or _env_enabled("STUDIO_ENABLE_SRC3"):
                active_values.append(rc)
            active_health = round(
                sum(active_values) / len(active_values), 1
            ) if active_values else 0.0
            with mtdi_lock:
                mtdi_data.update({
                    "c1_health":mc, "c1_note":mn,
                    "ch2f_health":ec, "ch2f_note":en,
                    "ch3_health":rc, "ch3_note":rn,
                    "active_health":active_health,
                    "completeness":round(completeness, 1),
                })
        except Exception:
            LOG.exception("MTDI health calculation failed")
        STOP_EVENT.wait(0.8)

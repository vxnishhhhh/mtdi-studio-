"""Speech in and out, standard library only.

    from mtdi import voice
    text = voice.transcribe(open("question.wav", "rb").read(), "audio/wav")["text"]
    audio = voice.speak("All channels steady.")["audio"]          # MP3 bytes

Speech to text: Groq (whisper-large-v3) or OpenAI (whisper-1), from GROQ_API_KEY /
OPENAI_API_KEY. Text to speech: ElevenLabs (ELEVENLABS_API_KEY, voice from
MTDI_ELEVENLABS_VOICE) or OpenAI (tts-1). ``MTDI_<PROVIDER>_BASE_URL`` overrides hosts.
"""
import json
import os
import secrets
import urllib.error
import urllib.request

STT = {"groq": ("GROQ_API_KEY", "https://api.groq.com/openai", "/v1/audio/transcriptions", "whisper-large-v3"),
       "openai": ("OPENAI_API_KEY", "https://api.openai.com", "/v1/audio/transcriptions", "whisper-1")}
DEFAULT_VOICE = "nPczCjzI2devNBz1zQrb"   # an ElevenLabs premade voice available on every plan


class VoiceError(Exception):
    pass


def _base(provider, default):
    return os.environ.get(f"MTDI_{provider.upper()}_BASE_URL", default).rstrip("/")


def _multipart(fields, filename, mimetype, data):
    boundary = "----mtdi" + secrets.token_hex(12)
    out = b""
    for k, v in fields.items():
        out += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    out += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {mimetype}\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    return out, "multipart/form-data; boundary=" + boundary


def _send(url, body, headers, timeout=60):
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read(), response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as error:
        raise VoiceError(f"HTTP {error.code}: {error.read()[:200].decode('utf-8', 'replace')}") from None
    except urllib.error.URLError as error:
        raise VoiceError(f"unreachable: {error.reason}") from None


def transcribe(data, mimetype="audio/wav", prompt="", language="en"):
    """Audio bytes to text: {"text", "provider"}. Tries Groq, then OpenAI."""
    errors = []
    for provider in ("groq", "openai"):
        env, base, path, model = STT[provider]
        key = os.environ.get(env, "").strip()
        if not key:
            continue
        ext = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mpeg": "mp3", "audio/mp4": "m4a"}.get(mimetype, "wav")
        fields = {"model": model, "response_format": "json", "language": language}
        if prompt:
            fields["prompt"] = prompt
        body, ctype = _multipart(fields, "speech." + ext, mimetype, bytes(data))
        try:
            raw, _ = _send(_base(provider, base) + path, body,
                           {"Authorization": "Bearer " + key, "Content-Type": ctype})
            return {"text": json.loads(raw).get("text", "").strip(), "provider": provider}
        except VoiceError as error:
            errors.append(f"{provider}: {error}")
    raise VoiceError("no speech-to-text available: " + ("; ".join(errors) or "set GROQ_API_KEY or OPENAI_API_KEY"))


def speak(text, voice=None):
    """Text to MP3 bytes: {"audio", "provider"}. Tries ElevenLabs, then OpenAI."""
    text = str(text)[:2500]
    errors = []
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if key:
        voice_id = voice or os.environ.get("MTDI_ELEVENLABS_VOICE", DEFAULT_VOICE)
        url = _base("elevenlabs", "https://api.elevenlabs.io") + f"/v1/text-to-speech/{voice_id}"
        try:
            audio, _ = _send(url, json.dumps({"text": text, "model_id": "eleven_multilingual_v2"}).encode(),
                             {"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
            return {"audio": audio, "provider": "elevenlabs"}
        except VoiceError as error:
            errors.append(f"elevenlabs: {error}")
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        url = _base("openai", "https://api.openai.com") + "/v1/audio/speech"
        try:
            audio, _ = _send(url, json.dumps({"model": "tts-1", "voice": voice or "alloy", "input": text}).encode(),
                             {"Authorization": "Bearer " + key, "Content-Type": "application/json"})
            return {"audio": audio, "provider": "openai"}
        except VoiceError as error:
            errors.append(f"openai: {error}")
    raise VoiceError("no text-to-speech available: " + ("; ".join(errors) or "set ELEVENLABS_API_KEY or OPENAI_API_KEY"))

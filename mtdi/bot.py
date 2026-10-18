"""NVTRA as a bot: grounded answers about a running project, by text or by voice.

    from mtdi.runtime import Runner
    from mtdi.bot import Bot
    bot = Bot(Runner("projects/host-health"))
    bot.reply("is anything unusual right now?")        # {"text", "engine"}
    bot.reply_voice(wav_bytes)                         # {"heard", "text", "audio", ...}

With a language-model key NVTRA answers in its own words, but only from the live
packet it is given; without one it answers from the rule engine (``pillars.nvtra``),
which needs no network. Either way it never invents a reading.
"""
import json

from . import llm, voice
from .pillars import nvtra

PERSONA = (
    "You are NVTRA, the intelligence of an MTDI project (Microprocessing Technological Diagnostic "
    "Intelligence). You explain what the project's channels show. Use only the numbers in the "
    "PACKET below; if something is not in it, say you do not have it. Each channel has a state "
    "(connected, stale, waiting), a deviation from its learned baseline, a signal-to-noise ratio and "
    "an evidence-quality score (0-100, not a probability). Be brief: two to four plain sentences, "
    "no markdown, no lists."
)


def packet_summary(packet, limit=12):
    """A compact, model-friendly view of an MTDI packet."""
    fusion = packet.get("fusion", {})
    channels = []
    for cid, ch in list(packet.get("channels", {}).items())[:limit]:
        env, ev = ch.get("environment", {}), ch.get("evidence", {})
        channels.append({"id": cid, "label": ch.get("label"), "unit": ch.get("unit"), "state": ev.get("state"),
                         "value": ch.get("magnitude"), "deviation": env.get("deviation"), "snr": env.get("snr"),
                         "baseline_locked": env.get("frozen"), "score": round(ch.get("score") or 0, 1),
                         "source": ev.get("data_source")})
    return {"project": (packet.get("project") or {}).get("name"), "condition": fusion.get("condition"),
            "interpretation": fusion.get("interpretation"), "score": fusion.get("score"),
            "completeness": fusion.get("completeness"), "warnings": (fusion.get("warnings") or [])[:5],
            "channels": channels}


class Bot:
    def __init__(self, runner=None, packet_provider=None, history=8):
        if runner is None and packet_provider is None:
            raise ValueError("give a Runner or a packet_provider")
        self.packet = packet_provider or runner.engine.snapshot
        self.history = []
        self.keep = history

    def reply(self, question):
        packet = self.packet()
        question = str(question).strip()[:2000]
        if llm.available():
            context = json.dumps(packet_summary(packet), default=str)
            messages = self.history[-self.keep:] + [{"role": "user", "content": question}]
            try:
                out = llm.chat(messages, system=PERSONA + "\n\nPACKET: " + context)
                self.history += [{"role": "user", "content": question}, {"role": "assistant", "content": out["text"]}]
                return {"text": out["text"], "engine": f"{out['provider']}:{out['model']}"}
            except llm.LLMError as error:
                fallback = nvtra.answer(question, packet)
                return {"text": fallback, "engine": "rules", "note": f"model unavailable ({error})"}
        return {"text": nvtra.answer(question, packet), "engine": "rules"}

    def reply_voice(self, audio, mimetype="audio/wav", speak=True):
        heard = voice.transcribe(audio, mimetype, prompt="NVTRA, MTDI, baseline, channel")
        out = self.reply(heard["text"])
        out["heard"] = heard["text"]
        if speak:
            try:
                out.update(voice.speak(out["text"]))
            except voice.VoiceError as error:
                out["speech_error"] = str(error)
        return out

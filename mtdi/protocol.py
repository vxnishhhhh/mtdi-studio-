"""The MTDI line protocol: how any firmware talks to MTDI.

One sample per line, newline terminated, in either form:

    KEY=value,KEY=value,...          e.g.  CH1=512,CH2=498,CH3=530
    {"KEY": value, ...}              e.g.  {"DIST_CM": 41.7}

This is the format Inductra Vaion's Uno firmware already speaks, so existing
firmware works unchanged. Keys starting with an underscore are reserved:

    _T     device time in milliseconds (optional; improves timing measurements)
    _SEQ   device sequence number (optional; reveals dropped lines)

Parsing is strict on purpose: a line that is not entirely well formed is
rejected whole, never partly used. The parser is the trust boundary between
hardware and every pillar above it.
"""
import json
import math
import re

KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_.\-]{0,47}$")
NUMBER = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
MAX_LINE = 2048


class ProtocolError(ValueError):
    pass


def parse_line(line):
    """Return {KEY: float} for a valid line, or raise ProtocolError."""
    if isinstance(line, bytes):
        try:
            line = line.decode("ascii")
        except UnicodeDecodeError as error:
            raise ProtocolError("line is not ASCII") from error
    text = line.strip()
    if not text:
        raise ProtocolError("empty line")
    if len(text) > MAX_LINE:
        raise ProtocolError("line too long")
    if text[0] == "{":
        return _parse_json(text)
    values = {}
    for field in text.split(","):
        key, sep, raw = field.partition("=")
        key, raw = key.strip(), raw.strip()
        if not sep or not KEY.match(key) or not NUMBER.match(raw):
            raise ProtocolError(f"malformed field {field!r}")
        if key in values:
            raise ProtocolError(f"duplicate key {key}")
        values[key] = _finite(raw, key)
    return values


def _parse_json(text):
    try:
        data = json.loads(text)
    except ValueError as error:
        raise ProtocolError("invalid JSON") from error
    if not isinstance(data, dict) or not data:
        raise ProtocolError("JSON line must be a non-empty object")
    values = {}
    for key, raw in data.items():
        if not KEY.match(str(key)) or isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ProtocolError(f"malformed field {key!r}")
        values[str(key)] = _finite(raw, key)
    return values


def _finite(raw, key):
    value = float(raw)
    if not math.isfinite(value):
        raise ProtocolError(f"{key} is not finite")
    return value


def format_line(values):
    """The inverse of parse_line for KEY=value lines (used by the simulator and tests)."""
    return ",".join(f"{k}={_fmt(v)}" for k, v in values.items())


def _fmt(value):
    return str(int(value)) if float(value).is_integer() else f"{value:.6g}"

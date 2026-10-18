# MTDI line protocol (5.0)

How any firmware talks to MTDI: one sample per line, ASCII, newline terminated.

```
KEY=value,KEY=value,...\n
```

or one JSON object per line:

```
{"KEY": value, ...}\n
```

* **Keys:** a letter or `_` first, then letters, digits, `_ . -`; up to 48 characters.
* **Values:** decimal numbers (`512`, `-3.25`, `1.2e-3`). No units, no quotes, no NaN or infinity.
* **One line = one moment.** Keys that belong to one channel (all axes of a vector) must be
  on the same line.
* **Reserved keys:** `_T` device time in milliseconds, `_SEQ` sequence number (MTDI counts the
  gaps as dropped lines). Both optional.
* **Strict:** a line with any malformed field is rejected whole and counted in the Validation
  Chamber. It is never partly used.
* **Failures:** if the sensor cannot be read, print nothing for that sample. Never print a stand-in
  value.

Examples:

```
CH1=512,CH2=498,CH3=530
AX=-1234,AY=410,AZ=6021,_SEQ=17
{"TEMP_C": 21.4, "HUM_PCT": 40}
```

Templates: `mtdi_template_arduino/` (C++, any Arduino core), `mtdi_template_micropython/`, and the
SDKs that print and parse the same lines: `sdk/cpp/mtdi.hpp`, `sdk/java`, `sdk/js/mtdi.mjs`, `matlab/+mtdi`.
Check a line from the command line: `python -m mtdi parse "CH1=512,CH2=498,CH3=530"`.

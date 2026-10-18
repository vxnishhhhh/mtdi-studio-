# Beyond sensors: software, networks and security

*MTDI Studio · October 2026*

MTDI was born measuring magnetic and electric fields, but nothing in its pillars depends
on physics. A channel is a stream of numbers with a unit, an expected rate and a noise
floor. That describes a lot of technology.

## Computers and single-board computers

Host Health watches the machine MTDI runs on. Its CPU, memory, load and network each
learn a normal level. An NVTRA rule flags outbound traffic that rises while compute
stays normal: a backup explains it, and so would data leaving that should not. Running
it on a Raspberry Pi turns the Pi into its own diagnostic instrument.

## Networks

Network Watch's probe measures TCP connect latency and failure rate to one target.
Environmental Intelligence learns what this particular link normally does, so "slow"
means slow for this link, not slower than a number someone guessed.

## Cybersecurity

Auth Watch counts failed and accepted authentications per window from a Linux auth log.
A fixed threshold ("alert after 10 failures") is wrong in both directions: too noisy on
a busy bastion host, too lax on a quiet one. Environmental Intelligence learns each
host's own rhythm, and an NVTRA rule describes the brute-force pattern: failures far
above normal, without matching successes. The rule also names the innocent explanation,
a misconfigured client retrying stale credentials, because MTDI never claims more than
its evidence.

## The same five pillars

| Pillar | Sensors | Software and IT |
|---|---|---|
| Validation Chamber | is the sensor talking, in range, on time | is the probe alive, is the metric fresh |
| Environmental Intelligence | the room's normal field | the host's normal load and login rhythm |
| NVTRA | "a nearby current loop" | "outbound traffic without compute load" |
| I³ | the instrument interface | the same interface |
| Aether | why the instrument exists | why the service exists |

## Honest limits

MTDI watches numbers. It does not parse packets, scan for vulnerabilities or replace an
intrusion detection system. It is a diagnostic layer that tells you when something
departs from its own normal, and how much to trust the measurement that says so.

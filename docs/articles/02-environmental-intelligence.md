# Environmental Intelligence: learn, lock, compare

*MTDI Studio · October 2026*

A reading on its own means very little. 47 µT is unremarkable on a desk and alarming
next to a sleeping baby's cot. Twelve failed logins is a quiet hour for one server and
an attack on another. **Environmental Intelligence**, MTDI's pillar 01, answers the
question every reading implies: compared to what?

## Learn

Each channel learns a baseline from the real environment it sits in. The learner is a
time-windowed median. It keeps quiet samples (within six times the measured noise of
the current baseline) and refuses excursions, so a door slamming or a phone passing does
not become part of "normal". The noise is measured the same way: 1.4826 times the median
absolute deviation, a spread estimate that one outlier cannot inflate.

For a vector sensor, every axis learns its own baseline. The deviation is the length of
the change across axes, and **axial consensus** tracks whether the axes keep sharing a
change in the same proportions. That is how a real source tends to behave, while noise
does not.

## Lock

A baseline that keeps adapting will slowly absorb the very change you are trying to see.
So a baseline can be **locked**. Once locked it never moves on its own, and every later
reading is measured against it.

Sometimes the world really does move: the instrument is carried to another room, a
supply warms up. A **stale-lock watch** notices when nearly everything in the last minute
has been refused, yet the refused values are themselves steady. It reports the lock as
stale and by how much, and can re-learn automatically if the project allows it.

## Compare

A learned environment can be **saved under a name** ("lab bench", "bedroom", "production
server at night") and recalled later. When recalled, its reference is pinned and every
channel reports its deviation from that saved environment instead of from the present one.

A saved environment is evidence, so MTDI refuses to save one that came from the simulator.
It also refuses channels that have not finished learning.

## Why it is universal

Nothing in this pillar knows what it measures. The magnetometer's baseline, the
ultrasonic sensor's empty room, the CPU's idle level and an auth log's normal rhythm are
the same algorithm with different numbers from each project's manifest. The code is
Inductra Vaion's Baseline Lock and Transient Watch with every electromagnetic constant
moved out into configuration.

## Try it

```bash
python -m mtdi run projects/host-health        # real data from the computer you are on
```

Open **Environment**, let it learn, press **Lock all**, then start something heavy.
Watch the deviation and the transient classification respond.

# A score you can take apart

*MTDI Studio · October 2026*

Confidence numbers usually arrive as a single percentage with nothing behind it. MTDI's
score is built the other way round: eight named factors, each computed from something
measurable, each with a visible weight. If the score is 71 %, you can see which factor
cost what.

## The eight factors

| Factor | Weight | Measured from |
|---|---|---|
| Availability | 0.20 | Is the channel connected and fresh? |
| Baseline | 0.15 | Has Environmental Intelligence finished learning? |
| Signal to noise | 0.20 | How clearly a change stands above the measured ambient noise |
| Clipping | 0.15 | Is the raw value inside its declared range? |
| Timing | 0.10 | How regular the arrival intervals are |
| Transient behaviour | 0.10 | Is the channel bursty, or stable/continuous? |
| Axial consensus | 0.05 | Do a vector's axes agree on the shape of a change? |
| Correlation | 0.05 | Do channels that changed together correlate? |

Each factor lies between 0 and 1. A channel's score is the weighted sum, and the project's
score is the mean over every declared channel. **An offline channel scores zero**, so a
missing sensor lowers the score instead of quietly disappearing from it. Channels marked
`optional` are left out while offline.

## Two regimes for signal to noise

When a signal is present, the factor is the logarithm of the signal-to-noise ratio. At
rest there is nothing to stand above the noise, so the channel is judged on resolution
instead: how far its measured noise sits below the budget a healthy sensor should meet.
Resolution earns at most half the credit, because a quiet channel proves a clean signal
path, not a working one.

## What it is not

It is a heuristic evidence-quality score, **not a calibrated probability**. It cannot tell
you the reading is correct, only how much evidence there is that the measurement process
is healthy. MTDI labels it that way everywhere it appears.

## Changing the weights

A project can re-weight the factors in its manifest. For example, a project whose
channels arrive irregularly by design can lower `timing`. Weights are renormalised to sum
to one, and the interface always shows the weights in use.

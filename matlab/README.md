# MTDI MATLAB toolbox (`+mtdi`)

An independent MATLAB implementation, so MTDI's numbers can be checked by a second code
path (Inductra Vaion's rule: two implementations agreeing on one capture is the reason to
believe either). Base MATLAB only, R2016b or newer; no toolboxes.

| Function | What it does |
|---|---|
| `mtdi.packet(url)` | read the live packet from a running studio |
| `mtdi.watch(url, seconds)` | live plot of the score and every channel's deviation |
| `mtdi.recording(file)` | read a `--record` JSONL session |
| `mtdi.analyze(recording, manifest)` | per-channel samples, mean, median, noise, LOD, LOQ, rate, clipping |
| `mtdi.verify(recording, manifest, pyJson)` | compare with `python -m mtdi analyze` |

```matlab
addpath('matlab');                                   % from the repository root
p = mtdi.packet('http://raspberrypi.local:8050');
s = mtdi.analyze('session.jsonl', 'projects/host-health/project.json');
mtdi.verify('session.jsonl', 'projects/host-health/project.json', 'py.json')
```

`python -m mtdi matlab <project>` opens MATLAB Online in your browser (signed in with your
MathWorks account) and writes a starter script for the project.

The MATLAB files have been checked with GNU Octave in this repository's tests when Octave is
installed; they have not yet been run in MATLAB itself.

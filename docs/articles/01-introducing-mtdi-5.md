# Introducing MTDI 5.0

*MTDI Studio · October 2026*

Most systems that measure something will hand you a number. Very few tell you whether
to believe it.

MTDI (**Microprocessing Technological Diagnostic Intelligence**) started inside
Inductra Vaion, a Raspberry Pi instrument that measures the electromagnetic environment
on several independent channels. Inductra needed more than readings. It needed to know
whether each sensor was connected, whether its data was fresh, what "normal" looked
like in the room it was in, and how to explain a change to a person. That layer became
MTDI. Version 5.0 lifts it out of the instrument so that any project can stand on it.

## The name, word by word

* **Microprocessing.** It runs where the data is: pure Python, a few megabytes of memory,
  comfortable on a Raspberry Pi or any small single-board computer.
* **Technological.** It is not tied to one field. A channel can be a magnetometer, a CPU,
  a network link or a login log.
* **Diagnostic.** It captures readings and the evidence about them: presence, freshness,
  timing, range, noise and detection limits.
* **Intelligence.** NVTRA, the intelligence pillar, explains what the evidence shows, and
  the system as a whole learns its own environment.

## Five pillars, one core

| | Pillar | Question it answers |
|---|---|---|
| 00 | Validation Chamber | Can this channel be believed right now? |
| 01 | Environmental Intelligence | What is normal here, and how far are we from it? |
| 02 | NVTRA | What is happening, in words, and what else could explain it? |
| 03 | I³ | How does a person see all of this? |
| 04 | Aether | Why does this project exist, and who made it? |

The core fuses the first two into one score made of eight named, weighted factors. It is
an evidence-quality score that can be taken apart factor by factor. It is not a
probability, and the interface says so.

## One file per project

A project joins MTDI by writing a `project.json`. It names where data comes from (a
microcontroller on USB, a program's output, an HTTP post, the host computer itself) and
which keys form which measurement. Everything else (the pillars, the score, the
interface) comes from the framework. The first project, Inductra Vaion, joined without
changing a single byte of its firmware: the lines its Arduino already printed were valid
MTDI protocol lines.

## What 5.0 ships

* Every pillar, implemented and tested.
* Eight adapters: serial, TCP, HTTP, Python, process, system, replay and a clearly
  labelled simulator.
* A generated interface: every project gets a home page, channel views, the MTDI pillar
  orbit, Environmental Intelligence and the Validation Chamber, with no UI code.
* An independent MATLAB toolbox whose results must match the Python ones.
* `python -m mtdi adopt`, which copies MTDI into another repository so a new project
  is built on it from the first commit.
* A playbook for AI assistants, so a link to the repository is enough to start.

## What it refuses to do

It does not invent values. A sensor that stops talking becomes a visible fault, not a
plausible number. Simulated data is labelled at every layer and can never be saved as a
real environment. Detection limits come from measured noise, never from a datasheet
typed into a config file.

That last list matters more than the features. MTDI exists because invisible things,
whether a field, a fault or an intrusion, are only useful once you can trust how they
were measured.

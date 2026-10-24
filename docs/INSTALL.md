# Installing MTDI

MTDI installs the way MATLAB does: one installer, and everything is there afterwards. That means the
engine, the studio interface, NVTRA, the machine-learning detectors, the MATLAB toolbox files, the SDKs
and the example projects.

## Raspberry Pi 5 or a Mac

```bash
curl -fsSL https://raw.githubusercontent.com/vxnishhhhh/mtdi-studio-/main/install.sh | bash
```

| Step | What happens |
|---|---|
| Python | Finds Python 3.11 or newer (Raspberry Pi OS Bookworm ships 3.11). On a Mac without it, the installer points you to the free python.org installer. |
| System packages | Pi only: installs `git` and `python3-venv` with `apt` if they are missing, so it asks for your password once. |
| Code | Clones into `~/mtdi`, or updates it if it is already there. Run `./install.sh` from a clone to install that clone instead. |
| Environment | A private Python environment in `~/mtdi/.venv`. Nothing is installed into the system Python. |
| Command | `mtdi` in `~/.local/bin`, added to your PATH. |
| Check | Runs `mtdi doctor` and stops with the reason if anything is broken. |

On a Pi 5 it takes a few minutes. Most of that time is downloading the Python packages, which have ready-built
64-bit ARM versions, so nothing is compiled.

## Options

| Option | Effect |
|---|---|
| `--autostart` | Starts the studio at boot: a systemd user service on the Pi, a launchd agent on a Mac. It listens on your network (`--lan`). |
| `--with-speech` | Adds on-device speech recognition (faster-whisper, about 300 MB). |
| `--uninstall` | Removes the environment, the command and the autostart entry. It keeps the code and your projects. |

When piping the installer from `curl`, pass options like this: `curl -fsSL .../install.sh | bash -s -- --autostart`.

## After installing

```bash
mtdi doctor                       # is this machine ready? (Python, packages, engine, speed, studio, serial, local AI, disk)
mtdi studio --lan                 # the interface; open the printed address on your phone or laptop
mtdi run projects/host-health     # a live project on the machine's own data; bundled projects work from any folder
```

`mtdi doctor` times the worst case on this machine: a 128-channel project, with a new packet arriving
before every snapshot. Above the 100 ms target it shows a warning instead of failing, and estimates how
many channels the machine handles inside the target.

The optional extras cost nothing:

* Offline AI: install [Ollama](https://ollama.com), then run `ollama pull llama3.2:3b`. NVTRA uses it automatically.
* Sensors: plug in a USB or UART device. `mtdi doctor` lists the serial ports it can see.

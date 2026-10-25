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

## Installing one exact version

The command above installs whatever `main` holds right now. To install a revision you have checked,
take the script from that same commit and pin the code to it:

```bash
curl -fsSL https://raw.githubusercontent.com/vxnishhhhh/mtdi-studio-/<commit>/install.sh | MTDI_REF=<commit> bash
```

`<commit>` is a full 40-character commit id. The code the installer checks out is verified by git
against that id, and the script comes from the same commit's path on GitHub, which later pushes cannot
change. You still trust GitHub to serve that commit faithfully; nothing on your machine checks the
script before it runs. If you want to read it first, download it, read it, then run it with
`MTDI_REF=<commit> bash install.sh`. The installer prints the commit it installed.
`MTDI_REF` also takes a tag, but a tag can be moved. A pinned install stays where it is:
`mtdi update` says so instead of updating. Run the plain command again to follow `main`.

## Updating

```bash
mtdi update --check    # is there an update?
mtdi update            # pull it, reinstall packages if they changed, restart the autostart service, run a quick doctor
```

Your projects and recordings are your own files, and an update never touches them. If you have edited
one of MTDI's own files, the update stops and lists that file instead of overwriting it.

## After installing

```bash
mtdi doctor                       # is this machine ready? (Python, packages, engine, speed, studio, serial, local AI, disk)
mtdi studio --lan                 # the interface; open the printed address on your phone or laptop
mtdi run projects/host-health     # a live project on the machine's own data; bundled projects work from any folder
```

`mtdi doctor` times the worst case on this machine: a 128-channel project, with a new packet arriving
before every snapshot. Above the 100 ms target it shows a warning instead of failing, and estimates how
many channels the machine handles inside the target.

### On a phone

A phone gets the same desktop layout as a laptop, always in landscape. Hold the phone sideways
and the studio fills the screen. Held upright it stays landscape, turned with the phone, so it
reads correctly as soon as you turn it (or with rotation lock on). Swipe to scroll; a drag across a
3D view rotates it, and a drag up or down scrolls past it. Small controls also accept a tap just
beside them.

* For the full screen with no browser bars, add the studio to your home screen (Share, then "Add to
  Home Screen" on an iPhone; the menu, then "Install app" on Android). Android then also holds the
  app in landscape.
* In Settings, the Desktop / Mobile switch moves this phone to a narrow layout of its own instead
  ("Mobile"), or back to the landscape desktop layout ("Desktop").

The optional extras cost nothing:

* Offline AI: install [Ollama](https://ollama.com), then run `ollama pull llama3.2:3b`. NVTRA uses it automatically.
* Sensors: plug in a USB or UART device. `mtdi doctor` lists the serial ports it can see.

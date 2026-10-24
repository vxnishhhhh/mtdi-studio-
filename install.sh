#!/usr/bin/env bash
# MTDI installer for Raspberry Pi OS (64-bit) and macOS. One command, everything included:
#
#   curl -fsSL https://raw.githubusercontent.com/vxnishhhhh/mtdi-studio-/main/install.sh | bash
#   ./install.sh                      # from a clone: installs that clone
#   ./install.sh --autostart          # also start the studio at boot (systemd on Linux, launchd on macOS)
#   ./install.sh --with-speech        # also on-device speech recognition (faster-whisper, ~300 MB)
#   ./install.sh --uninstall          # remove the environment, launcher and autostart; keeps your projects
#
# Installs into $MTDI_HOME (default ~/mtdi): the code, a private Python environment (.venv) and the
# `mtdi` command in ~/.local/bin. Nothing paid, no accounts, no keys; it ends by running `mtdi doctor`.
# GUIDE: each step is one function below; main() at the bottom lists them in order.
set -euo pipefail

REPO="${MTDI_REPO:-https://github.com/vxnishhhhh/mtdi-studio-}"
MTDI_HOME="${MTDI_HOME:-$HOME/mtdi}"
BIN="$HOME/.local/bin"
AUTOSTART=0 SPEECH=0 UNINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --autostart) AUTOSTART=1 ;;
    --with-speech) SPEECH=1 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help) if [ -f "${BASH_SOURCE[0]:-}" ]; then sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
               else echo "options: --autostart --with-speech --uninstall (details: $REPO/blob/main/install.sh)"; fi; exit 0 ;;
    *) echo "unknown option: $arg (try --help)"; exit 2 ;;
  esac
done

# The script's own folder when run as a file (./install.sh); empty when piped from curl, so the
# current directory is never mistaken for a copy of MTDI to install or uninstall.
script_dir() {
  local src="${BASH_SOURCE[0]:-}"
  [ -n "$src" ] && [ -f "$src" ] && cd "$(dirname "$src")" && pwd
}

say() { printf '\033[1m==>\033[0m %s\n' "$*"; }
die() { printf '\033[31mmtdi install: %s\033[0m\n' "$*" >&2; exit 1; }
OS="$(uname -s)"

find_python() {
  for py in python3.13 python3.12 python3.11 python3; do
    if command -v "$py" >/dev/null 2>&1 && "$py" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
      PY="$(command -v "$py")"; return
    fi
  done
  if [ "$OS" = Darwin ]; then
    die "needs Python 3.11 or newer. Free installer: https://www.python.org/downloads/ (or: brew install python@3.12), then run this again."
  fi
  die "needs Python 3.11 or newer (Raspberry Pi OS Bookworm has 3.11). Run: sudo apt install python3 python3-venv"
}

system_packages() {
  [ "$OS" = Linux ] && command -v apt-get >/dev/null 2>&1 || return 0
  local need=()
  command -v git >/dev/null 2>&1 || need+=(git)
  "$PY" -c 'import venv, ensurepip' 2>/dev/null || need+=(python3-venv)
  [ ${#need[@]} -eq 0 ] && return 0
  say "installing system packages: ${need[*]} (asks for your password)"
  sudo apt-get update -q && sudo apt-get install -y -q "${need[@]}"
}

get_code() {
  local here
  here="$(script_dir || true)"
  if [ -n "$here" ] && [ -f "$here/run.py" ] && [ -d "$here/mtdi" ]; then
    MTDI_HOME="$here"; say "using this copy: $MTDI_HOME"; return
  fi
  command -v git >/dev/null 2>&1 || die "needs git (macOS: xcode-select --install)"
  if [ -d "$MTDI_HOME/.git" ]; then
    say "updating $MTDI_HOME"; git -C "$MTDI_HOME" pull --ff-only -q
  else
    say "downloading MTDI into $MTDI_HOME"; git clone -q --depth 1 "$REPO" "$MTDI_HOME"
  fi
}

python_env() {
  say "creating the Python environment (a few minutes on a Pi)"
  [ -x "$MTDI_HOME/.venv/bin/python" ] || "$PY" -m venv "$MTDI_HOME/.venv"
  local pip=("$MTDI_HOME/.venv/bin/python" -m pip -q --disable-pip-version-check)
  "${pip[@]}" install --upgrade pip
  local extras="serial"
  [ "$SPEECH" = 1 ] && extras="serial,local-speech"
  "${pip[@]}" install -e "$MTDI_HOME[$extras]"
}

launcher() {
  mkdir -p "$BIN"
  cat > "$BIN/mtdi" <<EOF
#!/bin/sh
# MTDI launcher, written by install.sh. Remove with: $MTDI_HOME/install.sh --uninstall
export MTDI_LOCAL_LLM="\${MTDI_LOCAL_LLM:-1}"   # use Ollama when it runs; falls back instantly when it does not
exec "$MTDI_HOME/.venv/bin/python" -m mtdi "\$@"
EOF
  chmod +x "$BIN/mtdi"
  case ":$PATH:" in
    *":$BIN:"*) ;;
    *) local rc="$HOME/.bashrc"
       [ "$OS" = Darwin ] && rc="$HOME/.zshrc"
       grep -q 'MTDI launcher path' "$rc" 2>/dev/null || printf '\nexport PATH="$HOME/.local/bin:$PATH"  # MTDI launcher path\n' >> "$rc"
       say "added ~/.local/bin to PATH; open a new terminal for the mtdi command" ;;
  esac
}

autostart() {
  [ "$AUTOSTART" = 1 ] || return 0
  if [ "$OS" = Linux ]; then
    mkdir -p "$HOME/.config/systemd/user"
    cat > "$HOME/.config/systemd/user/mtdi-studio.service" <<EOF
[Unit]
Description=MTDI studio
After=network-online.target

[Service]
WorkingDirectory=$MTDI_HOME
ExecStart=$MTDI_HOME/.venv/bin/python -m mtdi studio --lan
Restart=on-failure

[Install]
WantedBy=default.target
EOF
    systemctl --user daemon-reload
    systemctl --user enable --now mtdi-studio.service
    loginctl enable-linger "$USER" 2>/dev/null || sudo loginctl enable-linger "$USER" || true
    say "studio starts at boot (logs: journalctl --user -u mtdi-studio)"
  else
    local plist="$HOME/Library/LaunchAgents/dev.mtdi.studio.plist"
    mkdir -p "$(dirname "$plist")"
    cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>dev.mtdi.studio</string>
  <key>WorkingDirectory</key><string>$MTDI_HOME</string>
  <key>ProgramArguments</key><array><string>$MTDI_HOME/.venv/bin/python</string><string>-m</string><string>mtdi</string><string>studio</string><string>--lan</string></array>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardErrorPath</key><string>$HOME/.mtdi-studio/launchd.log</string>
</dict></plist>
EOF
    mkdir -p "$HOME/.mtdi-studio"
    launchctl unload "$plist" 2>/dev/null || true
    launchctl load "$plist"
    say "studio starts at login (logs: ~/.mtdi-studio/launchd.log)"
  fi
}

uninstall() {
  local home
  home="$(script_dir || true)"
  [ -n "$home" ] && [ -f "$home/run.py" ] && [ -d "$home/mtdi" ] || home="$MTDI_HOME"
  if [ "$OS" = Linux ] && [ -f "$HOME/.config/systemd/user/mtdi-studio.service" ]; then
    systemctl --user disable --now mtdi-studio.service 2>/dev/null || true
    rm -f "$HOME/.config/systemd/user/mtdi-studio.service"
  fi
  if [ -f "$HOME/Library/LaunchAgents/dev.mtdi.studio.plist" ]; then
    launchctl unload "$HOME/Library/LaunchAgents/dev.mtdi.studio.plist" 2>/dev/null || true
    rm -f "$HOME/Library/LaunchAgents/dev.mtdi.studio.plist"
  fi
  rm -f "$BIN/mtdi"
  rm -rf "$home/.venv"
  say "removed the launcher, autostart and Python environment. The code and your projects stay in $home."
}

main() {
  [ "$UNINSTALL" = 1 ] && { uninstall; exit 0; }
  case "$OS" in Linux|Darwin) ;; *) die "supports Raspberry Pi OS / Linux and macOS; on Windows use WSL" ;; esac
  find_python
  system_packages
  find_python
  get_code
  python_env
  launcher
  autostart
  say "checking the install"
  "$BIN/mtdi" doctor || die "doctor found problems (above). Fix them and run: mtdi doctor"
  echo
  say "MTDI is installed. Try:"
  case ":$PATH:" in *":$BIN:"*) ;; *) echo "    (in this terminal, until you open a new one: export PATH=\"$BIN:\$PATH\")" ;; esac
  echo "    mtdi studio --lan                       the interface (open the address it prints, from any device on your network)"
  echo "    mtdi run projects/host-health           a live project on this computer's own data"
  echo "    mtdi doctor                             check the machine again any time"
}

main

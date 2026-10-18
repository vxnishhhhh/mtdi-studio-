# Running MTDI on a Raspberry Pi

*MTDI Studio · October 2026*

The **M** in MTDI stands for microprocessing: it should run where the data is, on small,
slow, low-power computers.

## What it needs

* Python 3.9 or newer. The engine and every pillar except the interface use only the
  standard library.
* For the browser interface: Dash and Flask (`pip install -r requirements.txt`). Inductra
  Vaion already ran a much heavier Dash interface on a Raspberry Pi 5.
* For serial sources: pyserial.

## How heavy it is

On the 2.1 GHz Xeon server used to develop it, the engine ingests a protocol line in
about 25 µs and builds a full packet in about 2 ms, with about 15 MB resident.
A Raspberry Pi Zero 2 W is roughly 10–20× slower per core. That is an estimate, **not a
measurement on a Pi**, but it still puts Inductra's ~100 lines per second at a few
percent of one core.

## Lighter modes

```bash
python -m mtdi run projects/host-health --headless   # JSON API only, no Dash
python -m mtdi watch projects/host-health            # live view in the terminal, over SSH
```

Headless mode serves `/mtdi/packet`, `/mtdi/state`, `/mtdi/ingest`, `/mtdi/action` and
`/mtdi/ask`, so a heavier machine (or MATLAB, through `mtdi.packet`) can draw the
interface while the Pi only measures.

## Start on boot

```ini
# /etc/systemd/system/mtdi.service
[Unit]
Description=MTDI Studio
After=network-online.target

[Service]
WorkingDirectory=/home/pi/mtdi-studio
ExecStart=/usr/bin/python3 -m mtdi run projects/host-health --host 0.0.0.0
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now mtdi
```

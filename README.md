# ISW / Ice-Sealed Wyvern

<img src="https://github.com/YoyPa/isw/blob/master/image/isw.svg" alt="" width="25%" align="right">

ISW is a fan control utility for MSI laptops running Linux. It provides both a **command-line interface** and a **native GTK3 graphical interface** to manage fan curves, temperatures, and hardware settings via the Embedded Controller (EC).

> ISW is MSI at 180° — Ice-Sealed Wyvern in opposition to MSI's "unleash the dragon".

Supported laptops are listed in [`/etc/isw.conf`](etc/isw.conf). The GUI will **auto-detect your laptop** on startup.

## Warning

- Use at your own risk!
- Secure boot can prevent access to the EC.
- Check that your EC works the same way — see the [wiki](https://github.com/YoyPa/isw/wiki/MSI-G-laptop-EC---Rosetta) for documentation.

## Features

### GUI (`isw-gui`)

- **Fan Curve Editor** — Interactive chart with draggable points for CPU and GPU fan curves
- **Real-time Monitor** — Live temperature, fan speed, and RPM graphs with 2-minute rolling history
- **Settings Panel** — Fan mode (Advanced/Basic/Auto), CoolerBoost toggle, battery charging threshold, USB backlight
- **Auto-detection** — Automatically selects the correct profile for your laptop via DMI board identification

### CLI (`isw`)

| Option | Description |
|--------|-------------|
| `-b off\|on` | Enable or disable CoolerBoost |
| `-c` | Show an EC dump |
| `-f FILE` | Show profiles in a firmware update file |
| `-p SECTION` | Show current profile in EC |
| `-r [N]` | Real-time CPU/GPU temp and fan speed (N iterations, or infinite) |
| `-s ADDR VAL` | Set a single EC byte (hex address, decimal value) |
| `-t PERCENT` | Set battery charging threshold (20–100%) |
| `-u off\|half\|full` | Set USB backlight level |
| `-w SECTION` | Write a profile to EC |

All options except `-h` and `-f` require root privileges.

## Installation

### Requirements

- Python 3.8+
- `PyGObject` (GTK3 bindings) — for the GUI
- `ec_sys` kernel module with `write_support=1`

### Setup

Clone the repository:

```
git clone https://github.com/mario0x/isw
cd isw
```

Or install as a Python package:

```
pip install .
```

### EC module setup

ISW needs the `ec_sys` kernel module loaded with write support:

**If ec_sys is a builtin kernel module:**

Add `ec_sys.write_support=1` to your kernel parameters in `/etc/default/grub`, then run `update-grub` and reboot.

**If ec_sys is a loadable module:**

Copy the provided config files:

```
sudo cp etc/modprobe.d/isw-ec_sys.conf /etc/modprobe.d/
sudo cp etc/modules-load.d/isw-ec_sys.conf /etc/modules-load.d/
```

Then reboot, or load immediately with:

```
sudo modprobe ec_sys write_support=1
```

## Usage

### GUI

```
sudo ./isw-gui
```

The GUI auto-detects your laptop model. You can also select a profile manually from the dropdown.

### CLI

Find your `SECTION_NAME` in [`isw.conf`](etc/isw.conf) — it's your motherboard ID (e.g. `14A1EMS1` for a GS40 6QE).

```bash
# Apply a fan profile
sudo ./isw -w 14A1EMS1

# Monitor temperatures in real-time
sudo ./isw -r

# Set battery charging threshold to 80%
sudo ./isw -t 80

# Toggle CoolerBoost
sudo ./isw -b on
```

### Launch at startup/resume

Use the systemd service to apply a profile at boot and after resume:

```
sudo systemctl enable isw@SECTION_NAME.service
```

## Project structure

```
isw
├── src/isw/
│   ├── cli.py           # Command-line interface
│   ├── config.py         # Config parsing (dataclasses)
│   ├── constants.py      # EC addresses, fan modes, magic numbers
│   ├── ec.py             # Low-level EC read/write
│   └── gui/
│       ├── app.py        # Main GTK3 application window
│       ├── controls.py   # Settings panel
│       ├── fan_curve.py  # Interactive fan curve editor
│       ├── monitor.py    # Real-time monitoring graphs
│       └── profiles.py   # Profile selector
├── etc/isw.conf          # Laptop profile database
├── isw                   # CLI entry point
├── isw-gui               # GUI entry point
└── pyproject.toml        # Python package config
```

## Contributing

Help support your laptop by opening an issue and providing `isw -cp MSI_ADDRESS_DEFAULT` output. Make sure your dump is taken before altering the EC — you can reset it with a reboot or by changing the power source.

# Installation

Install from PyPI for the usual case, or download the single script if you would rather not install a package. Once it is installed, continue with [Setup & First Run](setup-and-first-run.md).

## Requirements

* Python 3.6 or higher
* Libraries: [steam](https://github.com/ValvePython/steam), `requests`, `python-dateutil`, `python-dotenv`
* Optional: [Pillow](https://pypi.org/project/Pillow/), needed only to attach Steam avatar or game artwork to ntfy alerts
* Optional: [wcwidth](https://pypi.org/project/wcwidth/), needed only to measure display width for `TRUNCATE_CHARS`

Tested on:

* **macOS**: Ventura, Sonoma, Sequoia, Tahoe
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm, Trixie), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
* **Windows**: 10, 11

It should work on other versions of macOS, Linux, Unix and Windows as well.

## Install from PyPI

```sh
pip install steam_monitor
```

To also attach Steam avatar or game artwork to ntfy alerts, install the optional extra instead. It selects the newest Pillow release your Python version still supports:

```sh
pip install "steam_monitor[ntfy-images]"
```

## Manual Installation

Download the *[steam_monitor.py](https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/steam_monitor.py)* file to the desired location.

Install dependencies via pip:

```sh
pip install steam requests python-dateutil python-dotenv
```

Alternatively, from the downloaded *[requirements.txt](https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/requirements.txt)*:

```sh
pip install -r requirements.txt
```

For optional ntfy artwork attachments also install Pillow. On Python 3.10 and newer:

```sh
pip install "Pillow>=12.0.0"
```

Older Python versions need the newest Pillow they still support. The commented lines in *requirements.txt* list the pin for each one.

## Upgrading

To upgrade to the latest version when installed from PyPI:

```sh
pip install steam_monitor -U
```

If you installed manually, download the newest *[steam_monitor.py](https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/steam_monitor.py)* file to replace your existing installation.

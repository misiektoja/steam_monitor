# Installation

Steam Monitor runs as a local Python program. Choose the PyPI package for the shortest command or the manual script to run a downloaded file.

New to Python? Start with [New to Python: check and install](#new-to-python-check-and-install).

<a id="requirements"></a>
## Requirements

* Python 3.6 or higher
* Libraries: [steam](https://github.com/ValvePython/steam), `requests`, `python-dateutil`, `python-dotenv`
* Optional for ntfy artwork attachments: [Pillow](https://github.com/python-pillow/Pillow)
* Optional for display-width-aware terminal truncation with `TRUNCATE_CHARS` and `--truncate`: [wcwidth](https://pypi.org/project/wcwidth/)
* Optional for better coloured output in the classic Windows Command Prompt: [colorama](https://github.com/tartley/colorama). It is installed automatically on Windows and `--doctor` reports it as missing only there, where it makes a difference

Tested on:

* **macOS**: Tahoe, Sequoia, Sonoma, Ventura
* **Linux**: Raspberry Pi OS (Trixie, Bookworm, Bullseye), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2026/2025/2024
* **Windows**: 11, 10

It should work on other versions of macOS, Linux, Unix and Windows as well.

<a id="new-to-python-check-and-install"></a>
## New to Python: check and install

Use this section if you are new to Python or do not know what is already installed. The platform sections only prepare Python and `pip`. Everyone then uses the same Steam Monitor installation and setup commands. Steam Monitor requires Python 3.6 or newer.

<a id="check-whether-steam-monitor-is-already-installed"></a>
### Check whether Steam Monitor is already installed

Open Windows PowerShell on Windows or Terminal on macOS and Linux then run:

    steam_monitor --version

If this prints a Steam Monitor version, skip to [Run the setup wizard](#run-the-setup-wizard). If the command is not recognized or not found, continue with the section for your operating system.

<a id="windows-10-or-11"></a>
### Windows 10 or 11

Open Windows PowerShell. Select **Start**, type `PowerShell` then open **Windows PowerShell**.

Check Python and `pip`:

    python --version
    pip --version

If both commands work and Python reports version 3.6 or newer, skip to [Install Steam Monitor](#install-steam-monitor).

If either command fails or Python is older than the required version:

1. Open the official [Python Install Manager in Microsoft Store](https://apps.microsoft.com/detail/9NQ7512CXL7T), select **View in Store** then select **Install**. If Microsoft Store is unavailable, download the manager from [python.org](https://www.python.org/downloads/).

2. Close PowerShell then open it again.

3. Run `py install default` to install the default Python release then run `python --version`. If an older installation still takes precedence, use the troubleshooting guide below to correct the command aliases.

4. Check both commands again:

        python --version
        pip --version

If `pip` is still not recognized, run `py install --refresh`, close PowerShell then open it again. This Python Install Manager command repairs its command aliases.

See the official [Python Install Manager troubleshooting table](https://docs.python.org/3/using/windows.html#troubleshooting) if either check is still unavailable.

<a id="macos"></a>
### macOS

Open Terminal. Press **Command+Space**, type `Terminal` then press **Return**.

Check Python and `pip`:

    python3 --version
    pip --version

If both commands work and Python reports version 3.6 or newer, skip to [Install Steam Monitor](#install-steam-monitor).

If either command fails or Python is older than the required version:

1. Open the official [Python downloads for macOS](https://www.python.org/downloads/macos/). Select a stable Python release that meets the requirement above then download its **macOS 64-bit universal2 installer**. This single installer supports Apple Silicon and Intel Macs.

2. Open the downloaded `.pkg` file. Keep the standard options, select **Continue** through the installer then enter your macOS password when requested.

3. Open the new **Python 3.x** folder for the version you installed in Applications then double-click **Install Certificates.command**. Wait until its Terminal window reports `update complete` then close that window.

4. Close Terminal then open it again.

5. Check both commands again:

        python3 --version
        pip --version

The official [Using Python on macOS](https://docs.python.org/3/using/mac.html) guide shows every installer screen and explains the installed applications.

<a id="ubuntu-debian-raspberry-pi-os-or-kali"></a>
### Ubuntu, Debian, Raspberry Pi OS or Kali

Open Terminal then check Python and `pip`:

    python3 --version
    pip --version

If both commands work and Python reports version 3.6 or newer, skip to [Install Steam Monitor](#install-steam-monitor).

If either command fails or Python is too old, install or update the packages:

    sudo apt update
    sudo apt install python3 python3-pip

The package manager keeps an existing current package instead of reinstalling it. Terminal may ask for your password. Type the password you use to sign in then press **Enter**. Terminal does not show password characters while you type.

Check both commands again:

    python3 --version
    pip --version

If Python reports a version older than 3.6, follow your distribution's instructions to install a supported Python version before continuing. For another Linux distribution, install Python 3.6 or newer plus `pip` through its package manager.

<a id="install-steam-monitor"></a>
### Install Steam Monitor

Every operating system uses the same command:

    pip install steam_monitor

Verify the installation:

    steam_monitor --version

On Linux, `pip` may report that the system Python is externally managed. If that happens, install Steam Monitor with the isolated `pipx` tool instead:

    sudo apt install pipx
    pipx ensurepath
    pipx install steam_monitor

Close Terminal, open it again then run `steam_monitor --version`.

<a id="run-the-setup-wizard"></a>
### Run the setup wizard

Every operating system uses the same command:

    steam_monitor --setup

The setup wizard collects the target, service credentials and optional notifications. Continue to [Setup & First Run](setup-and-first-run.md) for a walkthrough of its questions.

<a id="choose-an-installation-method"></a>
## Choose an Installation Method

| Method | Best for | Command used in later examples |
| --- | --- | --- |
| PyPI | Users who already have Python or followed the beginner steps above | `steam_monitor [OPTIONS]` |
| Manual script | Users who want to download and run one Python file | `python3 steam_monitor.py [OPTIONS]` on macOS/Linux or `python steam_monitor.py [OPTIONS]` on Windows |

Later pages use the short PyPI command. If you chose the manual script, keep the options after `steam_monitor` and replace the command itself with the one in the table. The setup wizard and `--help` also print commands for the detected installation.

<a id="install-from-pypi"></a>
### Install from PyPI

```sh
pip install steam_monitor
steam_monitor --version
```

<a id="install-the-manual-script"></a>
### Install the Manual Script

Download the script and dependency list into the same directory:

```sh
curl -fsSLO https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/steam_monitor.py
curl -fsSLO https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/requirements.txt
```

You can also download [steam_monitor.py](https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/steam_monitor.py) and [requirements.txt](https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/requirements.txt) in a browser or use the files from a cloned repository.

Install the core dependencies:

```sh
pip install -r requirements.txt
```

You can install the core dependencies directly if you downloaded only the script:

```sh
pip install steam requests python-dateutil python-dotenv
```

Verify the script:

```sh
python3 steam_monitor.py --version
```

Use `python steam_monitor.py --version` on Windows.

<a id="next-step"></a>
## Next Step

Continue to [Setup & First Run](setup-and-first-run.md) to prepare credentials, choose a target and run the wizard.

<a id="upgrading"></a>
## Upgrading

Use the same installation method and Python environment you used originally. Upgrading does not remove your configuration, `.env` secrets, logs, CSV files or saved history. Keep those files in the same working directory or another persistent location.

### Upgrade a PyPI Installation

```sh
pip install --upgrade steam_monitor
steam_monitor --version
```

If you used `pipx`, upgrade with:

```sh
pipx upgrade steam_monitor
```

### Upgrade a Manual Installation

Replace [steam_monitor.py](https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/steam_monitor.py) and [requirements.txt](https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/requirements.txt) with the newest copies. You can download them in a browser, use the files from an updated clone or run:

```sh
curl -fsSLO https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/steam_monitor.py
curl -fsSLO https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/requirements.txt
pip install --upgrade -r requirements.txt
python3 steam_monitor.py --version
```

Refresh the dependencies even when `requirements.txt` appears unchanged because a new release may add or change a required library.

Use `python steam_monitor.py --version` on Windows. If you modified the script itself, save your changes before replacing it and reapply them to the new version.

### Check Upgrade

After any upgrade run the doctor command:

```sh
steam_monitor --doctor <steam_target>
```

Use the [manual equivalent](usage.md#command-format-by-installation-method) if you installed the script directly.

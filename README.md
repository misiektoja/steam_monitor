# steam_monitor

steam_monitor is a tool for real-time monitoring of Steam players' activities.

<a id="features"></a>
## Features

- Real-time tracking of Steam users' gaming activity (including detection when a user gets online/offline or plays games)
- Basic statistics for user activity (such as how long in different states, how long a game is played, overall time and the number of played games in the session etc.)
- Email notifications for different events (when a player gets online/away/snooze/offline, starts/finishes/changes a game or errors occur)
- Saving all user activities with timestamps to a CSV file
- Possibility to control the running copy of the script via signals

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/assets/steam_monitor.png" alt="steam_monitor_screenshot" width="85%"/>
</p>

<a id="table-of-contents"></a>
## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
   * [Install from PyPI](#install-from-pypi)
   * [Manual Installation](#manual-installation)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
   * [Configuration File](#configuration-file)
   * [Steam Web API key](#steam-web-api-key)
   * [User Privacy Settings](#user-privacy-settings)
   * [SMTP Settings](#smtp-settings)
   * [Storing Secrets](#storing-secrets)
5. [Usage](#usage)
   * [Monitoring Mode](#monitoring-mode)
   * [Email Notifications](#email-notifications)
   * [CSV Export](#csv-export)
   * [Check Intervals](#check-intervals)
   * [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix)
   * [Coloring Log Output with GRC](#coloring-log-output-with-grc)
6. [Change Log](#change-log)
7. [License](#license)

<a id="requirements"></a>
## Requirements

* Python 3.6 or higher
* Libraries: [steam](https://github.com/ValvePython/steam), `requests`, `python-dateutil`, `python-dotenv`

Tested on:

* **macOS**: Ventura, Sonoma, Sequoia
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm), Ubuntu 24, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
* **Windows**: 10, 11

It should work on other versions of macOS, Linux, Unix and Windows as well.

<a id="installation"></a>
## Installation

<a id="install-from-pypi"></a>
### Install from PyPI

```sh
pip install steam_monitor
```

<a id="manual-installation"></a>
### Manual Installation

Download the *[steam_monitor.py](https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/steam_monitor.py)* file to the desired location.

Install dependencies via pip:

```sh
pip install "steam[client]" requests python-dateutil python-dotenv
```

Alternatively, from the downloaded *[requirements.txt](https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/requirements.txt)*:

```sh
pip install -r requirements.txt
```

<a id="quick-start"></a>
## Quick Start

- Grab your [Steam Web API key](#steam-web-api-key) and track the `steam_user_id` gaming activities:

```sh
steam_monitor <steam_user_id> -u "your_steam_web_api_key"
```

Or if you installed [manually](#manual-installation):

```sh
python3 steam_monitor.py <steam_user_id> -u "your_steam_web_api_key"
```

To get the list of all supported command-line arguments / flags:

```sh
steam_monitor --help
```

<a id="configuration"></a>
## Configuration

<a id="configuration-file"></a>
### Configuration File

Most settings can be configured via command-line arguments.

If you want to have it stored persistently, generate a default config template and save it to a file named `steam_monitor.conf`:

```sh
steam_monitor --generate-config > steam_monitor.conf

```

Edit the `steam_monitor.conf` file and change any desired configuration options (detailed comments are provided for each).

<a id="steam-web-api-key"></a>
### Steam Web API key

You can get the Steam Web API key here: [http://steamcommunity.com/dev/apikey](http://steamcommunity.com/dev/apikey)

Provide the `STEAM_API_KEY` secret using one of the following methods:
 - Pass it at runtime with `-u` / `--steam-api-key`
 - Set it as an [environment variable](#storing-secrets) (e.g. `export STEAM_API_KEY=...`)
 - Add it to [.env file](#storing-secrets) (`STEAM_API_KEY=...`) for persistent use

Fallback:
 - Hard-code it in the code or config file

If you store the `STEAM_API_KEY` in a dotenv file you can update its value and send a `SIGHUP` signal to the process to reload the file with the new API key without restarting the tool. More info in [Storing Secrets](#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](#signal-controls-macoslinuxunix).

<a id="user-privacy-settings"></a>
### User Privacy Settings

In order to monitor Steam user activity, proper privacy settings need to be enabled on the monitored user account.

The user should go to [Steam Privacy Settings](https://steamcommunity.com/my/edit/settings).

The value in **My Profile → Game details** should be set to **Friends Only** or **Public**. 

<a id="smtp-settings"></a>
### SMTP Settings

If you want to use email notifications functionality, configure SMTP settings in the `steam_monitor.conf` file. 

Verify your SMTP settings by using `--send-test-email` flag (the tool will try to send a test email notification):

```sh
steam_monitor --send-test-email
```

<a id="storing-secrets"></a>
### Storing Secrets

It is recommended to store secrets like `STEAM_API_KEY` or `SMTP_PASSWORD` as either an environment variable or in a dotenv file.

Set environment variables using `export` on **Linux/Unix/macOS/WSL** systems:

```sh
export STEAM_API_KEY="your_steam_web_api_key"
export SMTP_PASSWORD="your_smtp_password"
```

On **Windows Command Prompt** use `set` instead of `export` and on **Windows PowerShell** use `$env`.

Alternatively store them persistently in a dotenv file (recommended):

```ini
STEAM_API_KEY="your_steam_web_api_key"
SMTP_PASSWORD="your_smtp_password"
```

By default the tool will auto-search for dotenv file named `.env` in current directory and then upward from it. 

You can specify a custom file with `DOTENV_FILE` or `--env-file` flag:

```sh
steam_monitor <steam_user_id> --env-file /path/.env-steam_monitor
```

 You can also disable `.env` auto-search with `DOTENV_FILE = "none"` or `--env-file none`:

```sh
steam_monitor <steam_user_id> --env-file none
```

As a fallback, you can also store secrets in the configuration file or source code.

<a id="usage"></a>
## Usage

<a id="monitoring-mode"></a>
### Monitoring Mode

To monitor specific user activity, just type the player's Steam64 ID (`steam_user_id` in the example below):

```sh
steam_monitor <steam_user_id>
```

If you have not set `STEAM_API_KEY` secret, you can use `-u` flag:

```sh
steam_monitor <steam_user_id> -u "your_steam_web_api_key"
```

If you do not know the user's Steam64 ID, but you know the Steam profile/community URL (which can be customized by the user), you can also run the tool with `-r` flag which will automatically resolve it to Steam64 ID: 

```sh
steam_monitor -r "https://steamcommunity.com/id/steam_username/"
```

By default, the tool looks for a configuration file named `steam_monitor.conf` in:
 - current directory 
 - home directory (`~`)
 - script directory 

 If you generated a configuration file as described in [Configuration](#configuration), but saved it under a different name or in a different directory, you can specify its location using the `--config-file` flag:


```sh
steam_monitor <steam_user_id> --config-file /path/steam_monitor_new.conf
```

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence.

You can monitor multiple Steam players by running multiple instances of the script.

The tool automatically saves its output to `steam_monitor_<user_steam_id/file_suffix>.log` file. The log file name can be changed via `ST_LOGFILE` configuration option and its suffix via `FILE_SUFFIX` / `-y` flag. Logging can be disabled completely via `DISABLE_LOGGING` / `-d` flag.

The tool also saves the timestamp and last status (after every change) to the `steam_<user_display_name>_last_status.json` file, so the last status is available after the restart of the tool.

<a id="email-notifications"></a>
### Email Notifications

To enable email notifications when a user gets online or offline:
- set `ACTIVE_INACTIVE_NOTIFICATION` to `True`
- or use the `-a` flag

```sh
steam_monitor <steam_user_id> -a
```

To be informed when a user starts, stops or changes the played game:
- set `GAME_CHANGE_NOTIFICATION` to `True`
- or use the `-g` flag

```sh
steam_monitor <steam_user_id> -g
```

To get email notifications about any changes in user status (online/away/snooze/offline):
- set `STATUS_NOTIFICATION` to `True`
- or use the `-s` flag

```sh
steam_monitor <steam_user_id> -s
```

To disable sending an email on errors (enabled by default):
- set `ERROR_NOTIFICATION` to `False`
- or use the `-e` flag

```sh
steam_monitor <steam_user_id> -e
```

Make sure you defined your SMTP settings earlier (see [SMTP settings](#smtp-settings)).

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/assets/steam_monitor_email_notifications.png" alt="steam_monitor_email_notifications" width="85%"/>
</p>

<a id="csv-export"></a>
### CSV Export

If you want to save all reported activities of the Steam user to a CSV file, set `CSV_FILE` or use `-b` flag:

```sh
steam_monitor <steam_user_id> -b steam_user_id.csv
```

The file will be automatically created if it does not exist.

<a id="check-intervals"></a>
### Check Intervals

If you want to customize polling intervals, use `-k` and `-c` flags (or corresponding configuration options):

```sh
steam_monitor <steam_user_id> -k 30 -c 120
```

* `STEAM_ACTIVE_CHECK_INTERVAL`, `-k`: check interval when the user is online, away or snooze (seconds)
* `STEAM_CHECK_INTERVAL`, `-c`: check interval when the user is offline (seconds)

<a id="signal-controls-macoslinuxunix"></a>
### Signal Controls (macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new configuration options / flags.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user gets online or offline (-a) |
| USR2 | Toggle email notifications when user starts/stops/changes the game (-g) |
| CONT | Toggle email notifications for all user status changes (online/away/snooze/offline) (-s) |
| TRAP | Increase the check timer for player activity when user is online/away/snooze (by 30 seconds) |
| ABRT | Decrease check timer for player activity when user is online/away/snooze (by 30 seconds) |
| HUP | Reload secrets from .env file |

Send signals with `kill` or `pkill`, e.g.:

```sh
pkill -USR1 -f "steam_monitor <steam_user_id>"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

<a id="coloring-log-output-with-grc"></a>
### Coloring Log Output with GRC

You can use [GRC](https://github.com/garabik/grc) to color logs.

Add to your GRC config (`~/.grc/grc.conf`):

```
# monitoring log file
.*_monitor_.*\.log
conf.monitor_logs
```

Now copy the [conf.monitor_logs](https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/grc/conf.monitor_logs) to your `~/.grc/` and log files should be nicely colored when using `grc` tool.

Example:

```sh
grc tail -F -n 100 steam_monitor_<user_steam_id/file_suffix>.log
```

<a id="change-log"></a>
## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/steam_monitor/blob/main/RELEASE_NOTES.md) for details.

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/steam_monitor/blob/main/LICENSE).

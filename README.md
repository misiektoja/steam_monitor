# steam_monitor

<p align="left">
  <img src="https://img.shields.io/github/v/release/misiektoja/steam_monitor?style=flat-square&color=blue" alt="GitHub Release" />
  <img src="https://img.shields.io/pypi/v/steam_monitor?style=flat-square&color=teal" alt="PyPI Version" />
  <img src="https://img.shields.io/github/stars/misiektoja/steam_monitor?style=flat-square&color=magenta" alt="GitHub Stars" />
  <img src="https://img.shields.io/badge/python-3.6+-blueviolet?style=flat-square" alt="Python Versions" />
  <img src="https://img.shields.io/github/license/misiektoja/steam_monitor?style=flat-square&color=blue" alt="License" />
  <img src="https://img.shields.io/github/last-commit/misiektoja/steam_monitor?style=flat-square&color=green" alt="Last Commit" />
  <img src="https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square" alt="Maintenance" />
</p>

Powerful tool for real-time tracking of **Steam players' activities**.

### 🚀 Quick Install
```sh
pip install steam_monitor
```

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/assets/steam_monitor.png" alt="steam_monitor_screenshot" width="85%"/>
</p>

<a id="features"></a>
## Features

- **Real-time tracking** of Steam users' gaming activity (including detection when a user gets online/offline or plays games)
- **Basic statistics for user activity** (such as how long in different states, how long a game is played, overall time and the number of played games in the session etc.)
- **Detailed user information** display mode providing comprehensive Steam profile insights including **profile details**, **Steam level and XP statistics**, **earned badges**, **ban status**, **friends count** (with optional full friends list), **top games by lifetime hours**, **recently played games** with playtime statistics, **hours played in the last 2 weeks** and optionally list of **recent achievements**
- **Steam community URL resolution** - automatically resolve Steam community URLs to Steam64 IDs (no need to know the numeric ID)
- **Steam level and total XP change tracking**
- **Friends list change tracking** (friends count and when available - added/removed friends)
- **Games library change tracking** (game count, added/removed games)
- **Email notifications** for different events (when a player gets online/away/snooze/offline, starts/finishes/changes a game, Steam level and total XP changes, friends list changes or errors occur)
- **Saving all user activities and profile changes** with timestamps to a **CSV file**
- **Status persistence** - automatically saves last status to JSON file to resume monitoring after restart
- **Smart session continuity** - handles short offline interruptions and preserves session statistics
- **Flexible configuration** - support for config files, dotenv files, environment variables and command-line arguments
- **Configurable color themes** - customizable terminal output colors and styles
- Possibility to **control the running copy** of the script via signals
- **Functional, procedural Python** (minimal OOP)

<a id="table-of-contents"></a>
## Table of Contents

1. [Requirements](#requirements)
2. [Installation](#installation)
   * [Install from PyPI](#install-from-pypi)
   * [Manual Installation](#manual-installation)
   * [Upgrading](#upgrading)
3. [Quick Start](#quick-start)
4. [Configuration](#configuration)
   * [Configuration File](#configuration-file)
   * [Steam Web API key](#steam-web-api-key)
   * [User Privacy Settings](#user-privacy-settings)
   * [SMTP Settings](#smtp-settings)
   * [Storing Secrets](#storing-secrets)
5. [Usage](#usage)
   * [Detailed User Information Display Mode](#detailed-user-information-display-mode)
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

* **macOS**: Ventura, Sonoma, Sequoia, Tahoe
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm, Trixie), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
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

<a id="upgrading"></a>
### Upgrading

To upgrade to the latest version when installed from PyPI:

```sh
pip install steam_monitor -U
```

If you installed manually, download the newest *[steam_monitor.py](https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/steam_monitor.py)* file to replace your existing installation.

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
# On macOS, Linux or Windows Command Prompt (cmd.exe)
steam_monitor --generate-config > steam_monitor.conf

# On Windows PowerShell (recommended to avoid encoding issues)
steam_monitor --generate-config steam_monitor.conf
```

> **IMPORTANT**: On **Windows PowerShell**, using redirection (`>`) can cause the file to be encoded in UTF-16, which will lead to "null bytes" errors when running the tool. It is highly recommended to provide the filename directly as an argument to `--generate-config` to ensure UTF-8 encoding.

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

<a id="detailed-user-information-display-mode"></a>
### Detailed User Information Display Mode

To display comprehensive Steam profile information for a user without starting monitoring, type the player's Steam64 ID (`steam_user_id` in the example below) and use the `-i` / `--info` flag:

```sh
steam_monitor <steam_user_id> -i
```

Or with a Steam community URL:

```sh
steam_monitor -r "https://steamcommunity.com/id/steam_username/" -i
```

If you have not set `STEAM_API_KEY` secret, you can use `-u` flag:

```sh
steam_monitor <steam_user_id> -i -u "your_steam_web_api_key"
# or
steam_monitor -r "https://steamcommunity.com/id/steam_username/" -i -u "your_steam_web_api_key"
```

This mode displays detailed information including:
- Steam64 ID, display name, real name
- Country/region
- Current status and profile visibility
- Account creation date
- Profile URL
- Steam level, badges earned and XP statistics
- Ban status (VAC, Community, Economy)
- Friends count
- Top games by lifetime hours
- Recently played games with playtime statistics
- Hours played in the last 2 weeks

Optionally, you can also display **recently earned achievements** using the `--achievements` flag:

```sh
steam_monitor <steam_user_id> -i --achievements                    # show recent achievements (default: 10)
steam_monitor <steam_user_id> -i --achievements -n 20              # show up to 20 recent achievements
steam_monitor <steam_user_id> -i --achievements --achievements-all-games  # check all owned games instead of only recently played
```

Recent achievements show game name, achievement name, description (if available) and earn time.

**How it works:**
- By default, the tool checks achievements from the user's recently played games (up to 15 games).
- If the recently played games list is empty or hidden, it automatically falls back to checking all owned games.
- Use `--achievements-all-games` to force checking all owned games instead of only recently played games. This is useful for users who haven't played recently, as their recently played list may be limited and older games with achievements might be missed.
- Achievements are sorted by unlock time (most recent first) and limited to the number specified with `-n` (default: 10).

The visibility of achievements depends on the user's Steam privacy settings for game details. If game details are set to "Private", achievements may not be accessible.

The tool displays this information and then exits (does not start monitoring).

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

When monitoring starts, the tool displays user information including Steam64 ID, display name, real name (if available), country/region, current status, profile visibility, account creation date and profile URL.

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

The tool also saves the timestamp and last status (after every change) to the `steam_<user_display_name>_last_status.json` file, so the last status is available after the restart of the tool. When games library tracking is enabled, a snapshot of the library (game count and app IDs) is stored in `steam_<user_display_name>_games.json` and only changes are reported.

To track when the user's **Steam level and total XP** changes:
- set `STEAM_LEVEL_XP_CHECK` to `True`
- or use the `--check-level-xp` flag

To track changes in the user's **friends list** (count and when available - added/removed friends):
- set `FRIENDS_CHECK` to `True`
- or use the `--check-friends` flag

To track changes in the user's **games library** (game count and added/removed games):
- set `GAMES_LIBRARY_CHECK` to `True`
- or use the `--check-games` flag

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

To get email notifications when the user's **Steam level and total XP** changes:
- set `STEAM_LEVEL_XP_NOTIFICATION` to `True`
- or use the `--notify-level-xp` flag

It requires Steam level and total XP tracking (`STEAM_LEVEL_XP_CHECK` / `--check-level-xp`) to be enabled.

```sh
steam_monitor <steam_user_id> --check-level-xp --notify-level-xp
```

To get email notifications when the user's **friends list** changes:
- set `FRIENDS_NOTIFICATION` to `True`
- or use the `--notify-friends` flag

It requires friends tracking (`FRIENDS_CHECK` / `--check-friends`) to be enabled.

```sh
steam_monitor <steam_user_id> --check-friends --notify-friends
```

To get email notifications when the user's **games library** changes:
- set `GAMES_LIBRARY_NOTIFICATION` to `True`
- or use the `--notify-games` flag

It requires games library tracking (`GAMES_LIBRARY_CHECK` / `--check-games`) to be enabled.

```sh
steam_monitor <steam_user_id> --check-games --notify-games
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

If you want to save **profile-related changes** (Steam level changes, total XP changes, friends count changes, games library changes and individual added/removed friends) to a **separate CSV file**, set `PROFILE_CSV_FILE` or use the `--profile-csv-file` flag:

```sh
steam_monitor <steam_user_id> --profile-csv-file steam_user_id_profile.csv
```

Each row contains a timestamp, event type and associated values (for example: old/new Steam level or XP, friends count delta or one friend per row for added/removed friends, when available).

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
| URG | Toggle email notifications for Steam level/XP changes (--notify-level-xp) |
| PIPE | Toggle email notifications for friends list changes (--notify-friends) |
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

The tool has native **color output** support for terminal since v1.5 (see `COLORED_OUTPUT` and `COLOR_THEME` config options), but you can also use [GRC](https://github.com/garabik/grc) to color logs.

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

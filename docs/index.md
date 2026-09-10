# steam_monitor

Real-time tracker for Steam players' activity, with detailed profile insights and instant alerts.

<a id="-quick-install"></a>
<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](installation.md#new-to-python-install-everything) first.

Install from PyPI:

```sh
pip install steam_monitor
```

Run the setup wizard:

```sh
steam_monitor --setup
```

The wizard asks for the target, authentication, polling intervals and optional notifications. Review the settings before saving them. See [Setup & First Run](setup-and-first-run.md) for the service-specific steps.

For the manual single-file method, dependencies and upgrade commands, see [Installation](installation.md).

## Features

- **Real-time tracking** of Steam users' gaming activity (including detection when a user gets online/offline or plays games)
- **Basic statistics for user activity** (such as how long in different states, how long a game is played, overall time and the number of played games in the session etc.)
- **Detailed user information** display mode providing comprehensive Steam profile insights including **profile details**, **Steam level and XP statistics**, **earned badges**, **ban status**, **friends count** (with optional full friends list showing when each friendship started), **top games by lifetime hours**, **recently played games** with playtime statistics, **hours played in the last 2 weeks**, optional **persona name history** and optionally list of **recent achievements**
- **Steam community URL resolution** - automatically resolve Steam community URLs to Steam64 IDs (no need to know the numeric ID)
- **Steam level and total XP change tracking**
- **Display (persona) name change tracking** (detects and logs in real time when the monitored user renames their account)
- **Friends list change tracking** (friends count and when available - added/removed friends)
- **Games library change tracking** (game count, added/removed games)
- **Email notifications** for different events (when a player gets online/away/snooze/offline, starts/finishes/changes a game, Steam level and total XP changes, display name changes, friends list changes or errors occur)
- **Webhook notifications** through **Discord**, **ntfy** and compatible services, independently configurable from email alerts
- **Saving all user activities and profile changes** with timestamps to a **CSV file**
- **Status persistence** - automatically saves last status to JSON file to resume monitoring after restart
- **Smart session continuity** - handles short offline interruptions and preserves session statistics
- **Guided setup** - `--setup` asks a few questions and writes a ready-to-run configuration, with a review summary and per-section editing before anything is saved
- **Preflight diagnostics** - `--doctor` checks the environment, configuration, connectivity, credentials, monitored profile and notification channels, and tells you how to fix whatever is not ready
- **Flexible configuration** - support for config files, dotenv files, environment variables and command-line arguments
- **Configurable color themes** - customizable terminal output colors and styles
- Possibility to **control the running copy** of the script via signals
- **Functional, procedural Python** (minimal OOP)

## Screenshots

![steam_monitor](https://raw.githubusercontent.com/misiektoja/steam_monitor/main/assets/steam_monitor.png)

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install-run) for first-time setup. These examples use the PyPI command. See [Command Format by Installation Method](usage.md#command-format) for manual-script equivalents.

Replace the target placeholders with a Steam64 ID or complete Steam community profile URL. Monitoring requires the [Steam Web API key](setup-and-first-run.md#steam-web-api-key) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `steam_monitor --setup` |
| Start monitoring with saved credentials | `steam_monitor <steam_target>` |
| Check setup before monitoring | `steam_monitor --doctor <steam_target>` |
| Enter or replace credentials through hidden prompts | `steam_monitor --set-steam-api-key` |
| Use a specific configuration and secrets file | `steam_monitor --config-file steam_monitor.conf --env-file .env <steam_target>` |
| Show profile details once | `steam_monitor <steam_target> -i` |
| List every supported command-line option | `steam_monitor --help` |

The monitored account must expose the activity described in [User Privacy Settings](setup-and-first-run.md#user-privacy-settings).

Monitoring runs until you press `Ctrl+C`. For email, Discord and ntfy alerts, CSV output and service-specific commands, see [Usage](usage.md). If a run fails, start with [Doctor Preflight](troubleshooting.md#doctor-preflight).

## Documentation

* [Installation](installation.md) - Python setup, package or manual install and upgrades
* [Setup & First Run](setup-and-first-run.md) - credentials, target selection and the setup wizard
* [Configuration](configuration.md) - settings, notifications and secret storage
* [Usage](usage.md) - monitoring, output and command options
* [Troubleshooting](troubleshooting.md) - Doctor checks and recovery steps

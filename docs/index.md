# steam_monitor

Real-time tracker for Steam players' activity, with detailed profile insights and instant alerts.

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

## Get started

1. [Install it](installation.md)
2. [Set it up and run it for the first time](setup-and-first-run.md)
3. [Tune the configuration](configuration.md)

If something does not work, [`--doctor`](troubleshooting.md#doctor-preflight) will usually tell you why, and [`--verbose` or `--debug`](troubleshooting.md#verbose-and-debug-output) will show you what the tool is doing.

## Screenshots

![steam_monitor](https://raw.githubusercontent.com/misiektoja/steam_monitor/main/assets/steam_monitor.png)

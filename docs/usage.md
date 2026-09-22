# Usage

<a id="command-format-by-installation-method"></a>
## Command Format by Installation Method

Examples use the PyPI command. For a downloaded script, run commands from the directory containing `steam_monitor.py` and keep the same arguments:

| Installation | Command |
| --- | --- |
| PyPI or pipx | `steam_monitor [OPTIONS]` |
| Manual script on macOS or Linux | `python3 steam_monitor.py [OPTIONS]` |
| Manual script on Windows | `python steam_monitor.py [OPTIONS]` |

For example, `steam_monitor --setup` becomes `python3 steam_monitor.py --setup` on macOS or Linux. Use `python` on Windows. Replace placeholders such as `<steam_target>` with a Steam64 ID or complete Steam community profile URL.

Activate the tool's virtual environment before running these commands. For a downloaded script, run them from the directory containing `steam_monitor.py`.

For first-time configuration, follow [Setup & First Run](setup-and-first-run.md). Use [Doctor Preflight](troubleshooting.md#doctor-preflight) to check a setup before monitoring.

The tool has two modes. **Monitoring mode** watches a profile continuously and sends alerts as things change. **User information mode** prints a detailed profile snapshot once and exits.

<a id="user-information-display-mode"></a>
## User Information Display Mode

To display comprehensive Steam profile information for a user without starting monitoring, pass a Steam64 ID, Steam3 identifier, vanity name or full profile URL as `steam_target` and use the `-i` / `--info` flag:

```sh
steam_monitor <steam_target> -i
```

For compatibility with existing scripts, `-r` / `--resolve-community-url` still resolves a Steam community URL:

```sh
steam_monitor -r "https://steamcommunity.com/id/steam_username/" -i
```

If you have not set `STEAM_API_KEY` secret, you can use `-u` flag:

```sh
steam_monitor <steam_target> -i -u "your_steam_web_api_key"
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
- Friends count (with `--list-friends` it also shows the full list including when each friendship started)
- Top games by lifetime hours
- Recently played games with playtime statistics
- Hours played in the last 2 weeks

Optionally, you can also display the **persona (display) name history** using the `--name-history` flag:

```sh
steam_monitor <steam_target> -i --name-history
```

This lists the user's previous display names with the date each one was changed, as reported by Steam.

Optionally, you can also display **recently earned achievements** using the `--achievements` flag:

```sh
steam_monitor <steam_target> -i --achievements                    # show recent achievements (default: 10)
steam_monitor <steam_target> -i --achievements -n 20              # show up to 20 recent achievements
steam_monitor <steam_target> -i --achievements --achievements-all-games  # check all owned games instead of only recently played
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
## Monitoring Mode

To monitor specific user activity, pass a Steam64 ID, Steam3 identifier, vanity name or full profile URL:

```sh
steam_monitor <steam_target>
```

You can also save any of these forms as `TARGET_STEAM_ID` in `steam_monitor.conf`. A positional target takes precedence. With a saved target no positional value is needed:

```sh
steam_monitor
```

If you have not set `STEAM_API_KEY` secret, you can use `-u` flag:

```sh
steam_monitor <steam_target> -u "your_steam_web_api_key"
```

The legacy `-r` flag remains supported for commands that explicitly resolve a community URL:

```sh
steam_monitor -r "https://steamcommunity.com/id/steam_username/"
```

When monitoring starts, the tool displays user information including Steam64 ID, display name, real name (if available), country/region, current status, profile visibility, account creation date and profile URL.


 If you generated a configuration file as described in [Configuration](configuration.md), but saved it under a different name or in a different directory, you can specify its location using the `--config-file` flag:

```sh
steam_monitor <steam_target> --config-file /path/steam_monitor_new.conf
```

`--config-file none` switches automatic config discovery off for one run. The startup summary reports `Discovery disabled` when it is in effect.

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence.

You can monitor multiple Steam players by running multiple instances of the script.

The tool automatically saves its output to `steam_monitor_<user_steam_id/file_suffix>.log` file. The log file name can be changed via `ST_LOGFILE` configuration option and its suffix via `FILE_SUFFIX` / `-y` flag. Logging can be disabled completely via `DISABLE_LOGGING` / `-d` flag.

Set `ASCII_LOG_SEPARATORS` to `"Auto"` (default) to use ASCII separator-only lines on Windows, `"On"` to use them on every operating system or `"Off"` to preserve Unicode separators in logs everywhere. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.

The tool also saves the timestamp and last status (after every change) to the `steam_<steam64_id>_last_status.json` file, so the last status is available after the restart of the tool. See [Status File](#status-file) to keep it somewhere else. When games library tracking is enabled, a snapshot of the library (game count, app IDs and the titles seen so far) is stored in `steam_<steam64_id>_games.json` and only changes are reported.

To track when the user's **Steam level and total XP** changes:
- set `STEAM_LEVEL_XP_CHECK` to `True`
- or use the `--check-level-xp` flag

To track changes in the user's **friends list** (count and when available - added/removed friends):
- set `FRIENDS_CHECK` to `True`
- or use the `--check-friends` flag

To track changes in the user's **games library** (game count and added/removed games):
- set `GAMES_LIBRARY_CHECK` to `True`
- or use the `--check-games` flag

Added and removed games are reported by title with the app ID after it, for example `Dota 2 (570)`. Titles come from one snapshot taken at startup plus a lookup limited to the games that actually changed, so the regular checks stay small. A title the lookup cannot resolve is reported as the bare app ID.

The user's **display (persona) name** is tracked automatically with no extra configuration. Whenever it changes, the tool logs the old and new name and (when a profile CSV is configured) records a `name_change` row. To also receive an email on such changes use `--notify-name-change` (see [Email Notifications](#email-notifications)).

<a id="terminal-output"></a>
## Terminal Output

Use `--help` for examples grouped by task and matched to your installation.

Monitoring mode prints the settings that are actually in effect before the first check.

Optional features appear once you switch them on.

Use `--verbose` or `--debug` for the full startup summary, including output paths, notification settings, secret sources and runtime information.

Use `--truncate N` or `TRUNCATE_CHARS` to limit screen line width. Set it to `999` to detect the terminal width automatically. Truncation does not change log files and is ignored when logging is disabled with `-d`.

The tool clears the terminal when monitoring starts. Set `CLEAR_SCREEN` to `False` to keep whatever is already on the screen.

The screen is never cleared when output is redirected to a file or a pipe, in debug mode or for a command that prints a result and exits, such as `--doctor`, `--help` and the test senders.

Two settings add detail to what a run prints. `VERBOSE_MODE` adds the decisions the run made and `DEBUG_MODE` adds timestamped technical traces. Both are off by default, both are independent of each other and both have a flag that wins over the file, `--verbose` and `--debug`. `DELIVERY_CONFIRMATIONS` is on by default and controls whether verbose mode confirms each delivered email and webhook alert. See [Verbose and Debug Output](troubleshooting.md#verbose-and-debug-output).

<a id="coloured-terminal-output"></a>
### Coloured Terminal Output

Steam Monitor colours live terminal output and help by default. Saved log files stay plain text.

Turn colour off for one run with `--no-color` or permanently with `COLORED_OUTPUT = False`. Colour is also disabled for redirected output, `NO_COLOR` or an unsupported terminal. See [Terminal Colours](configuration.md#terminal-colours) for details and Windows support.

Override individual colours with `COLOR_THEME`. It is merged over the built-in theme, so you only name the parts you want to change:

```ini
COLOR_THEME = { "game": "bright_magenta bold", "username": "green" }
```

See [Terminal Colours](configuration.md#terminal-colours) for every theme key and the accepted colour and style names.

<a id="email-notifications"></a>
## Email Notifications

To enable email notifications when a user gets online or offline:
- set `ACTIVE_INACTIVE_NOTIFICATION` to `True`
- or use the `-a` flag

```sh
steam_monitor <steam_target> -a
```

To be informed when a user starts, stops or changes the played game:
- set `GAME_CHANGE_NOTIFICATION` to `True`
- or use the `-g` flag

```sh
steam_monitor <steam_target> -g
```

To get email notifications about any changes in user status (online/away/snooze/offline):
- set `STATUS_NOTIFICATION` to `True`
- or use the `-s` flag

```sh
steam_monitor <steam_target> -s
```

To get email notifications when the user's **display (persona) name** changes:
- set `NAME_CHANGE_NOTIFICATION` to `True`
- or use the `--notify-name-change` flag

Display name changes are always detected and logged to the console, log file and profile CSV. This flag only controls whether an email is also sent.

```sh
steam_monitor <steam_target> --notify-name-change
```

To get email notifications when the user's **Steam level and total XP** changes:
- set `STEAM_LEVEL_XP_NOTIFICATION` to `True`
- or use the `--notify-level-xp` flag

It requires Steam level and total XP tracking (`STEAM_LEVEL_XP_CHECK` / `--check-level-xp`) to be enabled.

```sh
steam_monitor <steam_target> --check-level-xp --notify-level-xp
```

To get email notifications when the user's **friends list** changes:
- set `FRIENDS_NOTIFICATION` to `True`
- or use the `--notify-friends` flag

It requires friends tracking (`FRIENDS_CHECK` / `--check-friends`) to be enabled.

```sh
steam_monitor <steam_target> --check-friends --notify-friends
```

To get email notifications when the user's **games library** changes:
- set `GAMES_LIBRARY_NOTIFICATION` to `True`
- or use the `--notify-games` flag

It requires games library tracking (`GAMES_LIBRARY_CHECK` / `--check-games`) to be enabled.

```sh
steam_monitor <steam_target> --check-games --notify-games
```

To disable sending an email on errors and the recovery alert that follows (both enabled by default):
- set `ERROR_NOTIFICATION` to `False`
- or use the `-e` flag

```sh
steam_monitor <steam_target> -e
```

Email and webhook error alerts are sent after **5 minutes** of a continuing failure. Problems that need your action, such as a rejected API key, alert immediately. Each kind of failure alerts once per channel. Failed deliveries are retried after 5 minutes, with increasing waits up to an hour. Alerts can fire again after monitoring recovers.

A failure alert carries the subject `Steam Monitor error: <what went wrong> (user: <username>)` and lists the fix, the guide link, how many checks failed in a row, since when and when the next retry is. When the failure clears, a `Steam Monitor recovered: monitoring <username> resumed after <time>` alert follows on every channel that received the failure alert.

Make sure you have configured your [SMTP settings](configuration.md#smtp-settings) first.

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/assets/steam_monitor_email_notifications.png" alt="steam_monitor_email_notifications" width="85%"/>
</p>

<a id="webhook-notifications"></a>
## Webhook Notifications

Webhook event switches mirror the email choices while remaining independent:

| Event | Configuration | One-run flag |
| --- | --- | --- |
| User goes online or offline | `WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION` | `--webhook-active-inactive` |
| Any status change | `WEBHOOK_STATUS_NOTIFICATION` | `--webhook-status` |
| Game starts, changes or stops | `WEBHOOK_GAME_CHANGE_NOTIFICATION` | `--webhook-game-changes` |
| Steam level or XP changes | `WEBHOOK_LEVEL_XP_NOTIFICATION` | `--webhook-level-xp` |
| Friends list changes | `WEBHOOK_FRIENDS_NOTIFICATION` | `--webhook-friends` |
| Games library changes | `WEBHOOK_GAMES_NOTIFICATION` | `--webhook-games` |
| Display name changes | `WEBHOOK_NAME_CHANGE_NOTIFICATION` | `--webhook-name-change` |
| Monitoring errors and recoveries | `WEBHOOK_ERROR_NOTIFICATION` | `--webhook-errors` or `--no-webhook-error-notify` |

A monitoring error webhook carries the same title and text as the error email, without the timestamp the webhook service shows itself, and the matching recovery alert follows on the same channel.

Use `--webhook` or `--no-webhook` to override the master switch for one run. Event flags enable the master switch automatically. Level and XP, friends and games alerts require their corresponding tracking options.

For example:

```sh
steam_monitor <steam_target> --webhook-active-inactive --webhook-game-changes
steam_monitor <steam_target> --check-friends --webhook-friends
```

Known Discord and `ntfy.sh` URLs automatically select the matching request format even if the configured provider is stale. Set `WEBHOOK_PROVIDER` in `steam_monitor.conf` or use `--webhook-provider {discord,ntfy}` for self-hosted ntfy or compatible endpoints. For automation or one-time tests, `--webhook-url URL` overrides the destination without changing `.env`:

```sh
steam_monitor --webhook-provider ntfy --webhook-url "https://ntfy.sh/your-private-topic" --send-test-webhook
```

A URL passed on the command line may remain visible in shell history or process listings. Prefer `--set-webhook-url` for persistent private destinations.

<a id="csv-export"></a>
## CSV Export

If you want to save all reported activities of the Steam user to a CSV file, set `CSV_FILE` or use `-b` flag:

```sh
steam_monitor <steam_target> -b steam_user_id.csv
```

The file will be automatically created if it does not exist.

If you want to save **profile-related changes** (Steam level changes, total XP changes, display name changes, friends count changes, games library changes and individual added/removed friends) to a **separate CSV file**, set `PROFILE_CSV_FILE` or use the `--profile-csv-file` flag:

```sh
steam_monitor <steam_target> --profile-csv-file steam_user_id_profile.csv
```

Each row contains a timestamp, event type and associated values (for example: old/new Steam level or XP, friends count delta or one friend per row for added/removed friends, when available).

<a id="status-file"></a>
## Status File

The tool saves the timestamp and last status after every change, so the last status is available after a restart. By default it uses `steam_<steam64_id>_last_status.json` in the current directory. Set `STEAM_STATUS_FILE` or use the `--status-file` flag to keep it somewhere else:

```sh
steam_monitor <steam_target> --status-file ~/steam/last_status.json
```

Interrupted writes leave the previous status file intact. If a saved timestamp is more than five minutes ahead of the machine clock, monitoring warns and starts timing that status again. Files named after the Steam display name by versions before 2.0 are renamed to use the Steam64 ID on first start.

<a id="check-intervals"></a>
## Check Intervals

If you want to customize the polling intervals, use the `-k` and `-c` flags (or the corresponding configuration options):

```sh
steam_monitor <steam_target> -k 30 -c 120
```

* `STEAM_ACTIVE_CHECK_INTERVAL`, `-k`: check interval when the user is online, away or snooze (seconds)
* `STEAM_CHECK_INTERVAL`, `-c`: check interval when the user is offline (seconds)

An active interval below 30 seconds invites the Steam rate limiter, which stops the tool seeing anything. `--doctor` warns when the configured interval is that short.
<a id="liveness-reminder"></a>
### Liveness Reminder

While nothing changes, the tool prints one reminder that it is still running:

```
* Monitoring healthy for <steam_target>. The user is online with no status or game change since the last check
Liveness check, timestamp:	Mon 08 Sep 2026, 09:15:05
```

The reminder is timed in seconds, so it arrives at the same rate whichever check interval is in use. Set `LIVENESS_CHECK_INTERVAL` to change it (default: 86400, i.e. 24 hours) or to 0 to switch it off.

Anything the tool prints about the target restarts the countdown, so a busy run stays quiet.

<a id="signal-controls-macoslinuxunix"></a>
## Signal Controls (macOS/Linux/Unix)

The tool has several signal handlers implemented which allow to change behavior of the tool without a need to restart it with new configuration options / flags.

List of supported signals:

| Signal | Description |
| ----------- | ----------- |
| USR1 | Toggle email notifications when user gets online or offline (-a) |
| USR2 | Toggle email notifications when user starts/stops/changes the game (-g) |
| CONT | Toggle email notifications for all user status changes (online/away/snooze/offline) (-s) |
| URG | Toggle email notifications for Steam level/XP changes (--notify-level-xp) |
| PIPE | Toggle email notifications for friends list changes (--notify-friends) |
| VTALRM | Toggle email notifications for display name changes (--notify-name-change) |
| TRAP | Increase the check timer for player activity when user is online/away/snooze (by 30 seconds) |
| ABRT | Decrease check timer for player activity when user is online/away/snooze (by 30 seconds) |
| HUP | Reload secrets from .env file |

`SIGHUP` keeps command-line credentials and nonempty environment values exported before startup. Change those values and restart to replace them.

Send signals with `kill` or `pkill`, e.g.:

```sh
pkill -USR1 -f "steam_monitor <steam_target>"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

<a id="coloring-log-output-with-grc"></a>
## Coloring Log Output with GRC

The tool colours the terminal itself, but you can also use [GRC](https://github.com/garabik/grc) to colour logs.

The bundled recipe follows the same colours as the live output. It also covers the other monitors in the family, so one copy in `~/.grc/` colours every tool's logs.

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

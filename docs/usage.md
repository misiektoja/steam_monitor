# Usage

<a id="command-format"></a>
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

## Detailed User Information Display Mode

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

By default, the tool looks for a configuration file named `steam_monitor.conf` in:
 - current directory
 - home directory (`~`)
 - script directory

 If you generated a configuration file as described in [Configuration](configuration.md), but saved it under a different name or in a different directory, you can specify its location using the `--config-file` flag:

```sh
steam_monitor <steam_target> --config-file /path/steam_monitor_new.conf
```

`--config-file none` switches automatic config discovery off for one run. The startup summary reports `Discovery disabled` when it is in effect.

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence.

You can monitor multiple Steam players by running multiple instances of the script.

The tool automatically saves its output to `steam_monitor_<user_steam_id/file_suffix>.log` file. The log file name can be changed via `ST_LOGFILE` configuration option and its suffix via `FILE_SUFFIX` / `-y` flag. Logging can be disabled completely via `DISABLE_LOGGING` / `-d` flag.

Set `ASCII_LOG_SEPARATORS` to `"Auto"` (default) to use ASCII separator-only lines on Windows, `"On"` to use them on every operating system or `"Off"` to preserve Unicode separators in logs everywhere. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.

The tool also saves the timestamp and last status (after every change) to the `steam_<steam64_id>_last_status.json` file, so the last status is available after the restart of the tool. See [Status File](#status-file) to keep it somewhere else. When games library tracking is enabled, a snapshot of the library (game count and app IDs) is stored in `steam_<steam64_id>_games.json` and only changes are reported.

To track when the user's **Steam level and total XP** changes:
- set `STEAM_LEVEL_XP_CHECK` to `True`
- or use the `--check-level-xp` flag

To track changes in the user's **friends list** (count and when available - added/removed friends):
- set `FRIENDS_CHECK` to `True`
- or use the `--check-friends` flag

To track changes in the user's **games library** (game count and added/removed games):
- set `GAMES_LIBRARY_CHECK` to `True`
- or use the `--check-games` flag

The user's **display (persona) name** is tracked automatically with no extra configuration. Whenever it changes, the tool logs the old and new name and (when a profile CSV is configured) records a `name_change` row. To also receive an email on such changes use `--notify-name-change` (see [Email Notifications](#email-notifications)).

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

To disable sending an email on errors (enabled by default):
- set `ERROR_NOTIFICATION` to `False`
- or use the `-e` flag

```sh
steam_monitor <steam_target> -e
```

Email and webhook error alerts are sent after **5 minutes** of a continuing failure. Problems that need your action, such as a rejected API key, alert immediately. Each kind of failure alerts once per channel. Failed deliveries are retried after 5 minutes, with increasing waits up to an hour. Alerts can fire again after monitoring recovers.

Make sure you have configured your [SMTP settings](configuration.md#smtp-settings) first.

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/assets/steam_monitor_email_notifications.png" alt="steam_monitor_email_notifications" width="85%"/>
</p>

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
| Monitoring errors | `WEBHOOK_ERROR_NOTIFICATION` | `--webhook-errors` or `--no-webhook-error-notify` |

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

## Status File

The tool saves the timestamp and last status after every change, so the last status is available after a restart. By default it uses `steam_<steam64_id>_last_status.json` in the current directory. Set `STEAM_STATUS_FILE` or use the `--status-file` flag to keep it somewhere else:

```sh
steam_monitor <steam_target> --status-file ~/steam/last_status.json
```

Interrupted writes leave the previous status file intact. If a saved timestamp is more than five minutes ahead of the machine clock, monitoring warns and starts timing that status again. Files named after the Steam display name by versions before 2.0 are renamed to use the Steam64 ID on first start.

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

## Terminal Colours

Terminal output is coloured by default. `COLORED_OUTPUT` and `COLOR_THEME` apply to monitoring output and to the `--setup`, `--doctor` and `--help` screens. `--no-color` turns colour off for all of them.

The `--help` screen is coloured too. Group headings, option names, the values those options take, the example commands and the comments above them each get their own colour, so the screen can be scanned instead of read.

Turn it off for one run:

```sh
steam_monitor <steam_target> --no-color
```

Turn it off permanently in the config file:

```python
COLORED_OUTPUT = False
```

On Windows, install [colorama](https://pypi.org/project/colorama/) for colours in the older Command Prompt. Windows Terminal needs nothing extra.

Each part of the output has a logical name. `COLOR_THEME` in the config file overrides only the names it lists. Combine attributes with spaces or `+`, for example `"bright_cyan bold"` or `"red underline"`. Valid colours are `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white` and their `bright_` variants, plus the `bold`, `dim`, `underline` and `blink` attributes. An empty string leaves that part uncoloured.

The built-in colours apply unless you set `COLOR_THEME`. Older configurations may set every colour explicitly. Remove that block to use current defaults or edit individual values to keep a custom theme. The old `steam_id` key is still accepted as `id`.

```python
COLOR_THEME = {
    "game": "bright_magenta bold",
    "duration": "cyan",
}
```

The four presence colours apply where the tool reports a state, such as a `Status:` row, a status change line or a capitalised state like `*** User got OFFLINE !`. A sentence that only mentions a state, such as the liveness line `The user is offline with no status or game change since the last check`, stays in the default colour. The two boolean colours apply to a `Yes` or `No` that is the whole value of a labelled row, not to the word inside a sentence.

| Theme key | Default | What it colours |
| --- | --- | --- |
| `header` | `bright_cyan` | Report and wizard headings, plus the ASCII banner |
| `section` | `bright_white` | Section names and every command the tool tells you to run |
| `username` | `bright_cyan underline` | The monitored account name and the detected install method |
| `id` | `bright_magenta` | The Steam64 ID |
| `status_online` | `green` | An online presence |
| `status_offline` | `red` | An offline presence |
| `status_away` | `yellow` | An away presence |
| `status_snooze` | `magenta` | A snooze presence |
| `status_other` | `white` | A presence value the tool does not recognise |
| `game` | `bright_yellow` | Game titles |
| `duration` | `green` | Time spans such as `3 hours, 21 minutes` |
| `timestamp_label` | *(empty)* | The `Timestamp:` label, left uncoloured by default |
| `timestamp_value` | `cyan` | The timestamp itself |
| `info` | `cyan` | `To fix:` lines, notes, prompts and `[SKIP]` rows |
| `warning` | `yellow` | `* Warning:` lines and `[WARN]` rows |
| `error` | `red` | `* Error:` lines and `[FAIL]` rows |
| `signal` | `yellow` | `* Signal ... received` lines |
| `email` | `bright_cyan` | Lines reporting an email being sent |
| `webhook` | `bright_blue` | Lines reporting a webhook being sent |
| `date` | `magenta` | Single dates and times |
| `date_range` | `magenta` | Date and time ranges |
| `boolean_true` | `green` | `True`, `Enabled`, `On`, a `Yes` answer and `[PASS]` rows |
| `boolean_false` | `red` | `False`, `Disabled`, `Off` and a `No` answer |
| `link` | `blue underline` | URLs |
| `help_heading` | `bright_cyan bold` | The `--help` group headings and example task names |
| `help_usage` | `bright_white bold` | The `usage:` label |
| `help_option` | `bright_green` | Option names such as `--doctor` |
| `help_metavar` | `yellow` | The value each option takes, such as a path or a number of seconds |
| `help_placeholder` | `bright_magenta` | Values to replace in the help examples |
| `help_command` | `bright_white` | The commands in the help examples |
| `help_comment` | `bright_black` | The `#` comment above each help example |
| `help_default` | `bright_black` | The `(default: ...)` notes |

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

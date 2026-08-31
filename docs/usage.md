# Usage

## Detailed User Information Display Mode

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
- Friends count (with `--list-friends` it also shows the full list including when each friendship started)
- Top games by lifetime hours
- Recently played games with playtime statistics
- Hours played in the last 2 weeks

Optionally, you can also display the **persona (display) name history** using the `--name-history` flag:

```sh
steam_monitor <steam_user_id> -i --name-history
```

This lists the user's previous display names with the date each one was changed, as reported by Steam.

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

## Monitoring Mode

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

 If you generated a configuration file as described in [Configuration](configuration.md), but saved it under a different name or in a different directory, you can specify its location using the `--config-file` flag:

```sh
steam_monitor <steam_user_id> --config-file /path/steam_monitor_new.conf
```

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence.

You can monitor multiple Steam players by running multiple instances of the script.

The tool automatically saves its output to `steam_monitor_<user_steam_id/file_suffix>.log` file. The log file name can be changed via `ST_LOGFILE` configuration option and its suffix via `FILE_SUFFIX` / `-y` flag. Logging can be disabled completely via `DISABLE_LOGGING` / `-d` flag.

Set `ASCII_LOG_SEPARATORS` to `"Auto"` (default) to use ASCII separator-only lines on Windows, `"On"` to use them on every operating system or `"Off"` to preserve Unicode separators in logs everywhere. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.

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

The user's **display (persona) name** is tracked automatically with no extra configuration. Whenever it changes, the tool logs the old and new name and (when a profile CSV is configured) records a `name_change` row. To also receive an email on such changes use `--notify-name-change` (see [Email Notifications](#email-notifications)).

## Email Notifications

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

To get email notifications when the user's **display (persona) name** changes:
- set `NAME_CHANGE_NOTIFICATION` to `True`
- or use the `--notify-name-change` flag

Display name changes are always detected and logged to the console, log file and profile CSV. This flag only controls whether an email is also sent.

```sh
steam_monitor <steam_user_id> --notify-name-change
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

Make sure you defined your SMTP settings earlier (see [SMTP settings](configuration.md#smtp-settings)).

Example email:

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/assets/steam_monitor_email_notifications.png" alt="steam_monitor_email_notifications" width="85%"/>
</p>

## Webhook Notifications

Webhook event switches mirror the email choices while remaining independent:

| Event | Configuration | One-run flag |
| --- | --- | --- |
| User becomes active | `WEBHOOK_ACTIVE_NOTIFICATION` | `--webhook-active` |
| User goes offline | `WEBHOOK_INACTIVE_NOTIFICATION` | `--webhook-inactive` |
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
steam_monitor <steam_user_id> --webhook-active --webhook-inactive --webhook-game-changes
steam_monitor <steam_user_id> --check-friends --webhook-friends
```

Known Discord and `ntfy.sh` URLs automatically select the matching request format even if the configured provider is stale. Set `WEBHOOK_PROVIDER` in `steam_monitor.conf` or use `--webhook-provider {discord,ntfy}` for self-hosted ntfy or compatible endpoints. For automation or one-time tests, `--webhook-url URL` overrides the destination without changing `.env`:

```sh
steam_monitor --webhook-provider ntfy --webhook-url "https://ntfy.sh/your-private-topic" --send-test-webhook
```

A URL passed on the command line may remain visible in shell history or process listings. Prefer `--set-webhook-url` for persistent private destinations.

## CSV Export

If you want to save all reported activities of the Steam user to a CSV file, set `CSV_FILE` or use `-b` flag:

```sh
steam_monitor <steam_user_id> -b steam_user_id.csv
```

The file will be automatically created if it does not exist.

If you want to save **profile-related changes** (Steam level changes, total XP changes, display name changes, friends count changes, games library changes and individual added/removed friends) to a **separate CSV file**, set `PROFILE_CSV_FILE` or use the `--profile-csv-file` flag:

```sh
steam_monitor <steam_user_id> --profile-csv-file steam_user_id_profile.csv
```

Each row contains a timestamp, event type and associated values (for example: old/new Steam level or XP, friends count delta or one friend per row for added/removed friends, when available).

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

Send signals with `kill` or `pkill`, e.g.:

```sh
pkill -USR1 -f "steam_monitor <steam_user_id>"
```

As Windows supports limited number of signals, this functionality is available only on Linux/Unix/macOS.

## Coloring Log Output with GRC

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

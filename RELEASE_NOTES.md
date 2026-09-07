# steam_monitor release notes

This is a high-level summary of the most important changes.

# Changes in 2.0 (TBD)

Version **2.0** focuses on making Steam Monitor easier to set up, safer to configure and easier to recover when something goes wrong. It adds **guided setup**, a **`--set-smtp-password`** command, a read-only **Doctor preflight check**, verbose and debug diagnostics modes. New diagnostics explain failures and recovery steps. It also parses configuration files as data, guards config replacement, blocks webhook redirects. The standard install has fewer dependencies and release downloads can be verified. It also adds clearer security and support guidance.

**Features and improvements**:

- **NEW:** **Guided setup and a useful first screen** - `--setup` collects the Steam target, check intervals, API key and notification settings. It accepts Steam64 IDs, Steam3 identifiers, vanity names, full profile URLs and intervals such as `30s`, `1.5h` or `1h 30m`. Webhook setup asks which service receives alerts, then takes a Discord URL or an ntfy topic, expanding a bare ntfy.sh topic name, and for ntfy also offers a separate access token and artwork attachments. It asks whether to save the target in the configuration file, so later runs need no positional value. An **Output files** section chooses whether the per-target log file is written and takes an optional CSV path, where a blank answer disables CSV output and a path with no extension is saved with `.csv` added, plus an optional status file path where a blank answer keeps the default name in the working directory and a path with no extension is saved with `.json` added. **Both destinations are checked before the first question**, so an unwritable path or a directory given by mistake is reported straight away instead of after you have answered everything, **a configuration file already in place is replaced only after you agree**, with the option to write somewhere else instead, and **a secret already in the dotenv file is never replaced without asking**. Nothing is written until you choose Save. A final review lets you edit one section or discard all changes. The summary's **File destinations** section changes where the configuration and dotenv files are written. Moving the dotenv file asks the sections holding secrets again, since a secret you chose to keep was never going to reach the new file. **Ctrl+C is answered by the question, not by the shared signal handler**: before the save it reports `Setup cancelled. Destination files were not changed.` and at the `Run doctor now?` and `Start monitoring now?` questions that follow it says the setup is saved and prints the next-step commands. Setup offers `--doctor` whenever a target was given and offers to **start monitoring** only after that doctor run passed. A rerun proposes the saved webhook switch as the default of the webhook question and proposes email when the saved settings already send it. **Every answer setup cannot use offers a way out**, so a value you cannot produce right now no longer costs you the answers already given: a blank answer asks whether to continue without it and names what stops working, a rejected one offers another attempt and declining switches the channel that needed it off so half a mail server or a webhook with no destination is never written. The rebuilt file starts from the settings already in place with your answers applied over them, so **a declined section is cleared rather than carried over** and a rerun that declines email leaves no mail server behind. Secrets go to the dotenv file through hidden prompts that look like every other question and keep debug output off while a secret is typed, existing files are backed up and the final screen offers a `--doctor` configuration check and, on a local install, to start monitoring right away. **The mail server is signed in to before setup saves it**, so a wrong password or an unreachable host is reported during setup instead of at the first alert, and no email is sent. A refused sign-in offers the mail server questions again and giving up switches email alerts off, while an unreachable server keeps the answers for `--doctor` to check later. The questions show the values already saved as defaults and end with the hidden password prompt, where a blank answer keeps the stored password. The SMTP port question now refuses a number outside 1 through 65535, so setup can no longer save a port `--doctor` would then reject. Declining the retry offer at a number question keeps the value already saved instead of asking the same question again. `--set-steam-api-key` and `--set-webhook-url` end with the same labelled next-step commands the wizard prints. Re-running setup uses the current settings as defaults. Running the tool with no arguments and no saved target now shows the main commands, including the profile details command, and can open the wizard instead of printing an argument error. It exits 0 once that offer is answered and 1 where there is no terminal to answer on, so a script still sees a bare invocation as the usage error it was. Existing uses of `-r` and `--resolve-community-url` still work. Prompts, summaries, Doctor rows and printed commands use the **same wording as the other monitors in this family**, so the tools read the same way
- **NEW:** **Saved monitoring target** - `TARGET_STEAM_ID` stores the monitored profile in the configuration file. It accepts a Steam64 ID, Steam3 identifier, vanity name or full profile URL. A target written after the command takes precedence. With a saved target, `steam_monitor` starts monitoring with no arguments
- **NEW:** **Choose where the status file goes** - The new **`STEAM_STATUS_FILE`** setting and **`--status-file`** flag choose where the last seen status is kept. By default it is `steam_<steam64_id>_last_status.json` in the current directory. `--setup` asks for it in the **Output files** section. The setup summary, the startup summary and `--doctor` name the file the run will use
- **NEW:** **Read-only Doctor setup checks** - `--doctor` checks the environment, configuration, connectivity, Steam credentials, target and notification channels. It opens with the detected install method, reports the Python version with the minimum the tool supports, names the active configuration and dotenv files plus each secret's source without revealing values, and names the log, CSV and status files monitoring would write with whether each one can be created. **Settings that control timing and counts are checked for usable values**. Every one that is wrong is named in a single row, so a negative interval or an out-of-range port is caught before the run rather than during it. **A check interval short enough to invite rate limiting is warned about separately**, since a rate-limited account looks like a broken tool rather than a setting. Each row is colour-coded by status and a link in a row's detail is shown in the link colour. Every warning or failure includes a `To fix:` action and a matching `Guide:` link. The email check signs in to the configured SMTP server without sending anything, and each ready notification row lists the alert categories that channel would deliver. The command writes no files and sends test notifications only after confirmation. It reports the optional `colorama` package only on Windows, since the classic Command Prompt is the only place it changes anything. When setup runs it, it checks the settings and secrets that were just saved. The report ends with the command that starts monitoring, carrying the same configuration and dotenv files it just checked, so a clean report leads straight into a run.
- **NEW:** **Verbose and debug diagnostics modes** - `--verbose` reports what the tool is doing in plain `* ` lines: an alert channel switched off because `SMTP_HOST` or `WEBHOOK_URL` is still a placeholder, notification delivery results, and any Steam lookup that is unavailable so you know which alerts cannot run, reported once when it stops working and again when it recovers rather than on every check. Each notice closes with the same `Timestamp:` line and separator as every other block, and **verbose stays quiet between events** instead of printing a line per check, which `--debug` records instead. It also expands the startup summary, which names the configuration file, dotenv file, install method and the source of each secret. `--debug` adds timestamped traces for configuration loading, Steam requests, connectivity, email, webhooks, state files and failures. Each trace line **names the operation then lists its details as comma-separated `key=value` fields**, and every outbound call reports `outcome=OK` or `outcome=failed` with the error. The modes are independent and can also be enabled with `VERBOSE_MODE` and `DEBUG_MODE`. Command-line flags take precedence. A `--debug` run also leaves the terminal as it was instead of clearing it, so the output you are comparing against stays on screen, while `--verbose` clears it like an ordinary run. Secret values remain redacted and secret-entry prompts suppress debug output
- **NEW:** **Actionable failure recovery** - Errors now include a plain-language summary, a `To fix:` action and a `Guide:` link. `--debug` adds the technical cause. Suggested commands match the install method and retain non-default `--config-file` or `--env-file` paths. `--config-file none` and `--env-file none` are carried too, each except into a command that writes the file it switches off, since `--setup` and the commands that save a secret need somewhere to write. **A monitoring failure now reads the same in every monitor in this family**: `* Error: <what failed> (retrying in <time>)`, with the `To fix:` paragraph under it the first time that category appears. **A failure that lasts is reported once, not on every check**: the liveness banner takes over with `* Monitoring degraded for <steam_id>` and what is still failing, once per **`LIVENESS_CHECK_INTERVAL`** however often the failing run retries. Once it clears, `* Monitoring recovered for <steam_id>` reports how long the outage lasted. With **`LIVENESS_CHECK_INTERVAL`** set to 0 there is no banner to carry the reminder, so the one-line summary keeps printing on every check. **Starting without a profile to watch uses the same block**, naming the accepted target forms and a ready-to-paste command instead of printing the whole help screen.
- **NEW:** **Searchable documentation site** - The guide now lives at [misiektoja.github.io/steam_monitor](https://misiektoja.github.io/steam_monitor/) with Installation, Setup & First Run, Configuration, Usage, Troubleshooting, Testing and About pages.
- **NEW:** **`--set-smtp-password` saves the mail server password privately** - Enter `SMTP_PASSWORD` through a hidden prompt instead of editing the dotenv file by hand. The mail server has to accept the password before it is written and no email is sent, so a wrong password, or an app password the provider requires, is reported straight away. A refused sign-in leaves the dotenv file unchanged, and a password already saved there is replaced only after you confirm. The command ends with the same labelled next-step commands the other one-shot commands print.
- **IMPROVE:** **Clearer startup and help output** - Startup, setup, welcome and Doctor screens now use a boxed Steam ASCII banner. The Steam wordmark, Monitor line and version share one body column. The Setup Wizard heading uses the same header colour as the sibling monitors, and hidden secret prompts are coloured like the visible ones. The default startup summary leads with the monitored account and the polling intervals, shows enabled features and points to `--verbose` and `--debug` for more detail. Its rows appear in the same order as in the sibling monitors, so a setting sits in the same place whichever of them you are reading. **The log file always keeps the full summary** whatever the terminal showed, so a bug report made from a log carries every effective setting. **`TRUNCATE_CHARS`** and the new **`--truncate N`** flag cut each screen line to a maximum width. Use `999` to auto-detect the terminal width. Log files always keep the full line and truncation is off by default. `--help` shows its argument groups in the order shared with the sibling monitors, with **`Email notifications`** and **`Webhook notifications`** named apart and `--setup`, `--doctor`, `--generate-config` and `--set-steam-api-key` together under **`Configuration & dotenv files`**. Its examples are grouped by task with a comment above each command and print commands for the detected install method. The one-shot commands - `--setup`, `--doctor`, the `--set-*` commands and the `--send-test-*` commands - describe themselves with the same sentence in every monitor, so the same command no longer reads as a different one in each tool
- **IMPROVE:** **Names, IDs and links have their own colours** - Display names are `bright_cyan underline`, identifiers such as the Steam64 ID are `bright_magenta` and URLs are `blue underline`, so a name is never mistaken for a link. The `Target:`, `Steam64 ID:` and `Profile URL:` rows are coloured, and links printed inside a message, such as the `Guide:` lines, are no longer left plain. The `Monitoring user with Steam64 ID` line now colours the ID instead of losing its colour mid-line, and its separator matches the text width. The same three colours mean the same three things in every monitor in this family. The `steam_id` theme key is now **`id`** and a configuration file that still sets `steam_id` keeps working. The **`email`** and **`webhook`** keys colour the line that reports a delivery, `bright_cyan` and `bright_blue`, the same two colours the sibling monitors use
- **IMPROVE:** **A generated configuration no longer freezes the colours** - `COLOR_THEME` now ships commented out, so the tool's own defaults apply and a later change to them reaches you. Uncomment it to override colours and keep only the lines you want to change. **A configuration file written by an earlier version sets every colour explicitly and therefore keeps the old ones**: delete its `COLOR_THEME` block to follow the current defaults, or edit the values you want to keep. Such a file still loads unchanged
- **IMPROVE:** **Optional ntfy artwork and fewer dependencies** - Pillow is no longer installed by default and the unused `steam[client]` extra has been removed. Install artwork support with `pip install "steam_monitor[ntfy-images]"` then set `NTFY_IMAGES = True`. The extra selects a compatible Pillow release for Python 3.6 through 3.14. Upgrading users who want to keep artwork must enable `NTFY_IMAGES`
- **IMPROVE:** **Clearer ntfy customization** - `WEBHOOK_TEMPLATE`, `WEBHOOK_USERNAME` and `WEBHOOK_AVATAR_URL` are documented as Discord-only settings. ntfy uses `WEBHOOK_HEADERS` for options such as `X-Priority` and `X-Tags`
- **IMPROVE:** **`--set-steam-api-key` says it is contacting Steam** - The command validated the pasted key against the Steam Web API but printed nothing while it waited, so a slow or unreachable network looked like a hang. It now reports `* Checking the entered Steam Web API key before changing the private settings file ...` before the call, the same way the sibling monitors announce theirs
- **IMPROVE:** **The webhook provider warning names the provider the way the rest of the output does** - When a configured `WEBHOOK_PROVIDER` disagrees with the destination URL, startup corrects it and says so. That message printed the internal key, such as `discord`, where every other line prints `Discord`. It now uses the display name, matching the sibling monitors
- **IMPROVE:** **Safer file updates and TLS control** - Replacing a generated configuration or a configuration file rewritten by `--setup` creates a timestamped `.bak` file first. **Saving a secret keeps no backup**: `--set-steam-api-key`, `--set-smtp-password` and `--set-webhook-url` rewrite the dotenv file atomically, so the credential you replaced is not left behind in a `.bak` file. Status and games-library state files are written atomically. **`VERIFY_SSL` controls certificate verification for every outbound connection**, including Steam Web API calls, the connectivity check, the mail server that sends email alerts and webhook delivery. Switching it off is reported rather than silent: the startup summary gains a `TLS verification` row and `--doctor` warns while it is off
- **IMPROVE:** **Verifiable releases and gated publishing** - Release archives now include `steam_monitor_<tag>_SHA256SUMS.txt`, signed build provenance and an attached `.intoto.jsonl` attestation bundle. Verify an archive with `gh attestation verify steam_monitor_<tag>.zip --repo misiektoja/steam_monitor`.
- **IMPROVE:** **Security, support and contribution guidance** - New security and support policies explain private vulnerability reporting and where to ask questions or report bugs. Guided issue forms, a pull request template, contribution guidance, a code of conduct and a third-party license notice document the project workflow
- **IMPROVE:** **`--config-file none` switches config discovery off** - The value `none` already switched the dotenv search off through `--env-file none`. It now does the same for the configuration file, so a run can use built-in defaults and command-line values only, without picking up a `steam_monitor.conf` sitting in the working directory. `--doctor` reports it as `[PASS] No configuration file selected` instead of stopping with a missing-file error. `--setup` refuses both values, since it needs somewhere to write the files it saves. Both flags name the value in `--help`
- **IMPROVE:** **One-shot commands keep the screen** - **`--doctor`**, **`--help`**, the `--set-*` commands and the `--send-test-*` commands no longer clear the terminal, so their output stays in the scrollback and can be pasted into a bug report. Monitoring runs and `--setup` still start on a clean screen when `CLEAR_SCREEN` is on.
- **IMPROVE:** **Test commands send the same message in every monitor** - **`--send-test-email`** and **`--send-test-webhook`** now use one subject and one body shared by the sibling monitors. The body names the command that sent it, so a test message arriving beside real alerts is easy to place

**Bug fixes**:

- **BUGFIX:** **Saved state survives a display name change** - The last status file and the games library snapshot were named after the Steam display name, so a name change made the next start begin from scratch. Both are now named after the Steam64 ID, as `steam_<steam64_id>_last_status.json` and `steam_<steam64_id>_games.json`. A file from an earlier version is renamed to the new name once, on the first start, so the saved state is kept
- **BUGFIX:** **The liveness banner now follows the clock** - Its cadence was counted in checks derived from **`STEAM_CHECK_INTERVAL`**, so it drifted from the interval you configured: with a check interval longer than **`LIVENESS_CHECK_INTERVAL`** the banner printed after every check. A target polled on the shorter **`STEAM_ACTIVE_CHECK_INTERVAL`** was reminded up to twice as often as asked. The banner and the outage reminder now print once per **`LIVENESS_CHECK_INTERVAL`** of elapsed time
- **BUGFIX:** **The liveness banner no longer skips an online target** - The banner was printed only while the target was offline, so a target who stayed online gave no periodic sign that monitoring was still running. It now prints whenever nothing changed for **`LIVENESS_CHECK_INTERVAL`**. It names the current state whether or not **`--verbose`** is on
- **BUGFIX:** **Failed alerts are retried** - Email and webhook delivery is tracked separately. A channel that fails is retried on the next cycle while a channel that already succeeded is not sent again
- **BUGFIX:** **Steam names cannot control terminal output** - Display names, real names, game names and achievement text are stripped of control characters and bounded in length before they reach the terminal, log files or notifications
- **BUGFIX:** **Exported secrets work without a dotenv file** - Exported `STEAM_API_KEY`, `SMTP_PASSWORD`, `WEBHOOK_URL` and `NTFY_ACCESS_TOKEN` values now apply on their own and override values from the dotenv file. `SIGHUP` keeps that precedence when secrets are reloaded
- **BUGFIX:** **A game title is coloured whole** - A title containing an apostrophe, such as `Assassin's Creed Valhalla`, was coloured only up to that apostrophe, and a title containing a dot, an underscore or a slash, such as `S.T.A.L.K.E.R. 2`, was left plain entirely. Both are now coloured in full, while quoted file names and paths still stay plain. A quoted **`<placeholder>`**, a quoted command-line option such as `'--env-file none'` and a quoted piece of a URL such as `'?code='` are no longer coloured as titles
- **BUGFIX:** **The `status_change` theme key is gone** - `COLOR_THEME` listed a `status_change` colour that nothing ever read, so setting it did nothing. It has been removed. A configuration file that still sets it keeps working and the setting is ignored, as it always was
- **BUGFIX:** **Screen clearing and colour follow the configuration file** - `CLEAR_SCREEN` and `COLORED_OUTPUT` from the configuration file now apply to the startup banner. Previously both screens had already printed before the file was read, so only the built-in defaults applied
- **BUGFIX:** **A configured `FILE_SUFFIX` names the log file** - `FILE_SUFFIX` from the configuration file is now used in the log file name. Previously only the `-y` flag had any effect and a configured value was always replaced by the Steam ID
- **BUGFIX:** **Connectivity settings take effect** - The startup connectivity check now honors `CHECK_INTERNET_URL` and `CHECK_INTERNET_TIMEOUT` from the configuration file
- **BUGFIX:** **An unset webhook destination switches the channel off** - With `WEBHOOK_ENABLED = True` and a `WEBHOOK_URL` left unset or still holding its `your_webhook_url` placeholder, every alert failed with `WEBHOOK_URL must contain a complete HTTPS link`. Webhook alerts are now switched off at startup instead, and `--verbose` reports why
- **BUGFIX:** **Webhook redirects are refused** - Discord and ntfy deliveries no longer follow redirects. The destination is revalidated at delivery time after a dotenv reload, so alerts and headers cannot be forwarded to an unchecked host
- **BUGFIX:** **Configuration files are parsed as data** - Configuration files no longer execute as Python. Only documented assignments with literal values or references to another setting are accepted. Invalid content names the rejected line and setting without applying part of the file
- **BUGFIX:** **Declining a secret replacement is no longer reported as a cancelled command** - Answering `n` at the `Replace the saved ...?` question of `--set-steam-api-key`, `--set-webhook-url` or `--set-smtp-password` said the command was cancelled and told you to run it again when you have the value ready, which only asks the same question. It now says the saved value was left as it is and names the answer that replaces it. Ctrl+C still reports the cancel, but its message starts on its own line instead of continuing the hidden prompt

# Changes in 1.9.2 (04 Aug 2026)

**Bug fixes**:

- **BUGFIX:** Fixed indentation of ASCII log separators in summary screen

# Changes in 1.9.1 (04 Aug 2026)

Version **1.9.1** keeps terminal separators visually consistent and makes saved log separators portable without changing UTF-8 log content.

**Features and improvements**:

- **IMPROVE:** **Consistent terminal separators** - The monitoring startup divider now uses the same Unicode separator style as the rest of the terminal output
- **IMPROVE:** **Portable log separators** - The new `ASCII_LOG_SEPARATORS` setting controls whether separator-only lines saved to log files use ASCII hyphens. `"Auto"` enables them on Windows by default, `"On"` enables them on every operating system and `"Off"` preserves Unicode separators. Terminal separators stay Unicode. Log files and all other logged text remain UTF-8.

# Changes in 1.9 (31 Jul 2026)

Version **1.9** adds independent **Discord and ntfy webhook notifications**, safer **Steam API key setup** and customizable delivery for activity and profile alerts.

**Features and improvements**:

- **NEW:** Added independent **Discord and ntfy webhook notifications** with per-event controls for activity, game, profile, friends-list, games-library and monitoring-error alerts
- **NEW:** Added private **webhook URL setup** with `--set-webhook-url`, automatic provider detection, one-run provider and URL overrides plus `--send-test-webhook` for delivery checks
- **NEW:** Added safe **Steam API key setup** through `--set-steam-api-key` with live validation and atomic dotenv persistence that keeps the key out of shell history and process listings
- **NEW:** Added **customizable Discord-format payloads** plus native ntfy topic delivery with protected-topic authentication and bounded Steam artwork attachments with text fallback, using Pillow for image preparation
- **IMPROVE:** Added compact **email and webhook category rollups** to the startup summary with short labels and unstarred continuation lines when needed

**Bug fixes**:

- **BUGFIX:** Kept long ntfy text notifications below the server's 4 KB attachment boundary and added a visible truncation marker
- **BUGFIX:** Prevented notification summaries containing **errors** from turning entirely red, keeping only the `On` or `Off` state colored
- **BUGFIX:** Made `SIGHUP` redetect Discord or ntfy when the private webhook destination changes

# Changes in 1.8.1 (22 Jul 2026)

**Bug fixes**:

- **BUGFIX:** Replaced intermittent Steam community profile HTML scraping with the authenticated `ISteamUser.ResolveVanityURL` Web API for reliable vanity URL resolution
- **BUGFIX:** Added local handling for numeric Steam64, Steam3 and `/user/<invite-code>` profile URLs
- **BUGFIX:** Improved error reporting for invalid URLs, API failures and rate limits so resolver failures are no longer reported as a missing `STEAM64_ID`

# Changes in 1.8 (26 Jun 2026)

**Features and Improvements**:

- **NEW:** **Display (persona) name change tracking** - detects and logs in real time when the monitored user renames their account. Changes are written to the console, log file and profile CSV with no extra configuration and no additional API calls
- **NEW:** Optional **email notifications** when the display name changes (`NAME_CHANGE_NOTIFICATION` / `--notify-name-change`)
- **NEW:** Added **signal handler** (SIGVTALRM) for toggling display name change email notifications
- **NEW:** Enhanced **user info** display mode (`-i`) to optionally show the **persona name history** (`--name-history`), retrieved from Steam's public profile endpoint
- **IMPROVE:** Enhanced the `--list-friends` output in **user info** display mode (`-i`) to show when each friendship started
- **IMPROVE:** Added GitHub Actions workflow for publishing packages to PyPI and auto-building/attaching zip and tar.gz assets to published releases
- **IMPROVE:** Added **Dependabot** version updates

# Changes in 1.7 (06 Feb 2026)

**Features and Improvements**:

- **NEW:** **Games library change tracking** - track when the user's game count (or library set) changes. Enable with `GAMES_LIBRARY_CHECK` or `--check-games` (closes [#1](https://github.com/misiektoja/steam_monitor/issues/1))
- **NEW:** Optional **email notifications** when the games library changes (`GAMES_LIBRARY_NOTIFICATION` / `--notify-games`; requires games library tracking to be enabled)
- **NEW:** Games library changes can be logged to the **profile CSV**

# Changes in 1.6 (23 Jan 2026)

**Features and Improvements**:

- **NEW:** Added `--no-color` flag to disable colored output
- **IMPROVE:** Enhanced `--generate-config` to support writing directly to a file (e.g. `steam_monitor --generate-config steam_monitor.conf`). This avoids UTF-16 encoding issues on **Windows PowerShell**
- **IMPROVE:** Improved color output initialization for **Windows compatibility**
- **IMPROVE:** Expanded tabs to spaces in output log files to ensure **consistent alignment across different viewers**

# Changes in 1.5 (29 Dec 2025)

**Features and Improvements**:

- **NEW:** Implemented native **color output** support for terminal, enhancing user experience with customizable **color themes** (see `COLORED_OUTPUT` and `COLOR_THEME` config options). You can still use the old **grc** method if you prefer
- **NEW:** Added **inactivity thresholds** and **estimated last activity** tracking for user status changes (see `STEAM_AWAY_INACTIVITY_THRESHOLD` and `STEAM_SNOOZE_INACTIVITY_THRESHOLD` config options)
- **NEW:** Introduced tracking for **Steam level**, **total XP** and **friends list** changes with optional **email notifications** and **CSV logging**
- **NEW:** Added **signal handlers** for toggling **Steam level/XP** and **friends list** email notifications
- **NEW:** Added **optional separate CSV file** for **profile-related changes** (Steam level, total XP, friends changes). See `PROFILE_CSV_FILE` config option and `--profile-csv-file` flag
- **IMPROVE:** Enhanced **user info** display mode (`-i`) to optionally list **recent achievements** (`--achievements`) and added **CLI flag** to force fetching achievements from all **owned games** (`--achievements-all-games`)
- **IMPROVE:** Implemented fallback for **achievement fetching** by referring to **owned games** when **recently played list** is empty
- **IMPROVE:** Enhanced **user info** display mode (`-i`) to optionally list **friends** with detailed information (`--list-friends`)
- **IMPROVE:** Enhanced **game playtime** display in monitoring and user info display mode
- **IMPROVE:** Refactored handling of users with **privacy settings** set to block **friends list**

**Dependencies**:

- **NEW:** Added **colorama** dependency for **Windows platform** support

# Changes in 1.4 (11 Nov 2025)

**Features and Improvements**:

- **NEW:** Added detailed user information display mode (`-i` / `--info` flag), providing comprehensive Steam profile insights including Steam level, badges and XP statistics, country/region, ban status (VAC, Community, Economy), profile URL, friends list/count, top games and recently played games with playtime statistics
- **IMPROVE:** Enhanced user information display in monitoring mode to include country/region details and profile URL

# Changes in 1.3.1 (13 Jun 2025)

**Bug fixes**:

- **BUGFIX:** Fixed config file generation to work reliably on Windows systems

# Changes in 1.3 (22 May 2025)

**Features and Improvements**:

- **NEW:** The tool can now be installed via pip: `pip install steam_monitor`
- **NEW:** Added support for external config files, environment-based secrets and dotenv integration with auto-discovery
- **IMPROVE:** Enhanced startup summary to show loaded config and dotenv file paths
- **IMPROVE:** Simplified and renamed command-line arguments for improved usability
- **NEW:** Implemented SIGHUP handler for dynamic reload of secrets from dotenv files
- **IMPROVE:** Added configuration option to control clearing the terminal screen at startup
- **IMPROVE:** Changed connectivity check to use Steam API endpoint for reliability
- **IMPROVE:** Added check for missing pip dependencies with install guidance
- **IMPROVE:** Allow disabling liveness check by setting interval to 0 (default changed to 12h)
- **IMPROVE:** Improved handling of log file creation
- **IMPROVE:** Refactored CSV file initialization and processing
- **IMPROVE:** Added support for `~` path expansion across all file paths
- **IMPROVE:** Refactored code structure to support packaging for PyPI
- **IMPROVE:** Enforced configuration option precedence: code defaults < config file < env vars < CLI flags
- **IMPROVE:** Updated horizontal line for improved output aesthetics
- **IMPROVE:** Email notifications now auto-disable if SMTP config is invalid
- **IMPROVE:** Removed short option for `--send-test-email` to avoid ambiguity

**Bug fixes**:

- **BUGFIX:** Eliminated duplicate Steam API calls
- **BUGFIX:** Correctly handle 429 errors by respecting Retry-After headers and suppressing log noise

# Changes in 1.2 (14 Jun 2024)

**Features and Improvements**:

- **NEW:** Added new parameter (**-z** / **--send_test_email_notification**) which allows to send test email notification to verify SMTP settings defined in the script
- **IMPROVE:** Support for float type of timestamps added in date/time related functions
- **IMPROVE:** Function get_short_date_from_ts() rewritten to display year if show_year == True and current year is different, also can omit displaying hour and minutes if show_hours == False
- **IMPROVE:** Checking if correct version of Python (>=3.5) is installed
- **IMPROVE:** Possibility to define email sending timeout (default set to 15 secs)

**Bug fixes**:

- **BUGFIX:** Fixed "SyntaxError: f-string: unmatched (" issue in older Python versions
- **BUGFIX:** Fixed "SyntaxError: f-string expression part cannot include a backslash" issue in older Python versions

# Changes in 1.1 (23 May 2024)

**Features and Improvements**:

- **NEW:** Feature counting overall time and number of played games in the session
- **NEW:** Possibility to define STEAM_API_KEY via command line argument (**-u** / **--steam_api_key**)
- **IMPROVE:** Improvements for running the code in Python under Windows
- **NEW:** Possibility to define output log file name suffix (**-y** / **--log_file_suffix**)
- **IMPROVE:** Information about log file name visible in the start screen
- **IMPROVE:** Email sending function send_email() has been rewritten to detect invalid SMTP settings
- **IMPROVE:** Strings have been converted to f-strings for better code visibility
- **IMPROVE:** Better detection of wrong command line arguments
- **IMPROVE:** Rewritten get_date_from_ts(), get_short_date_from_ts(), get_hour_min_from_ts() and get_range_of_dates_from_tss() functions to automatically detect if time object is timestamp or datetime
- **IMPROVE:** Help screen reorganization
- **IMPROVE:** pep8 style convention corrections

**Bug fixes**:

- **BUGFIX:** Improved exception handling while processing JSON files

# Changes in 1.0 (25 Apr 2024)

**Features and Improvements**:

- **NEW:** Support for short offline interruption, so if user gets offline and online again (for example due to rebooting the PC) during the next OFFLINE_INTERRUPT seconds (configurable in .py file) then we set online start timestamp back to the previous one
- **IMPROVE:** Additional information in the subject of email notifications

**Bug fixes**:

- **BUGFIX:** Fixes for handling situations where some profile information is not available

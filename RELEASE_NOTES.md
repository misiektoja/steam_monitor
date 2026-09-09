# steam_monitor release notes

This is a high-level summary of the most important changes.

# Changes in 2.0 (TBD)

Version **2.0** focuses on making Steam Monitor easier to set up, safer to configure and easier to recover when something goes wrong. It adds **guided setup**, a read-only **Doctor preflight check**, a **`--set-smtp-password`** command for hidden password entry plus verbose and debug diagnostics modes. New diagnostics explain failures and recovery steps. It also parses configuration files as data, guards config replacement and blocks webhook redirects. The standard install has fewer dependencies and release downloads can be verified. It also adds clearer security and support guidance.

**Features and improvements**:

- **NEW:** **Guided setup** - `--setup` wizard walks through the profile, check intervals, credentials, notifications and output files. Review or edit answers before saving, with hidden secret entry and confirmation before replacing existing settings. Running with no arguments offers setup when no target is saved
- **NEW:** **Saved target and configurable status file** - Save a profile with `TARGET_STEAM_ID` to start monitoring without arguments. Use `--status-file` or `STEAM_STATUS_FILE` to choose where the last seen status is stored
- **NEW:** **Doctor preflight check** - `--doctor` checks configuration, Steam access, notification channels and output destinations before monitoring. Problems include suggested fixes. It writes no files and sends test notifications only after confirmation
- **NEW:** **Verbose and debug modes** - `--verbose` reports operational changes and notification results. `--debug` adds technical traces for troubleshooting. Both keep secrets redacted
- **NEW:** **Private SMTP password setup** - `--set-smtp-password` takes a hidden password and checks it with the mail server before saving. Guided setup also checks email credentials without sending a message
- **IMPROVE:** **Clearer errors and recovery** - Failures explain what to fix and link to the guide. Persistent outages produce periodic reminders instead of repeating full errors, followed by a recovery notice
- **IMPROVE:** **More readable terminal output** - Shorter startup summaries, clearer colours and task-based help examples make commands and settings easier to find. Optional `--truncate N` limits screen width while logs retain full lines. Existing colour overrides remain in effect
- **IMPROVE:** **Optional ntfy artwork and fewer dependencies** - Pillow is no longer installed by default and artwork is disabled by default. To keep artwork after upgrading, install `steam_monitor[ntfy-images]` and set `NTFY_IMAGES = True`
- **IMPROVE:** **Safer file updates** - Replacing configuration files creates backups. Secret and monitoring state files are updated atomically, with no backup of replaced secrets
- **IMPROVE:** **Documentation and verifiable downloads** - A [searchable guide](https://misiektoja.github.io/steam_monitor/) covers installation, setup and troubleshooting. Releases include checksums and signed build attestations. New security and support guidance explains where to report problems

**Bug fixes**:

- **BUGFIX:** **State survives display name changes** - Status and games-library files now use the Steam64 ID. Existing files are migrated automatically
- **BUGFIX:** **More reliable alerts and monitoring status** - Failed email and webhook deliveries are retried without repeating successful deliveries. Liveness messages follow the configured interval for both online and offline targets
- **BUGFIX:** **Configuration settings take effect consistently** - Exported secrets work without a dotenv file. Startup respects configured screen, colour, log suffix and connectivity settings. Unconfigured webhooks are disabled instead of failing on every alert
- **BUGFIX:** **Safer configuration loading** - Configuration files are read as settings instead of executed as Python. Plain values and references to other settings still work. Files using imports, function calls or calculations must be rewritten as plain settings
- **BUGFIX:** **Safer notifications and terminal output** - Webhooks refuse redirects and Steam-supplied text cannot inject terminal control commands. `VERIFY_SSL` now applies to all outbound connections, including email, with a warning when verification is disabled

Smaller fixes and development changes are listed in the [full change history](https://github.com/misiektoja/steam_monitor/compare/v1.9.2...v2.0).

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

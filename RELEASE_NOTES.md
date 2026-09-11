# steam_monitor release notes

This is a high-level summary of the most important changes.

# Changes in 2.0 (TBD)

Version **2.0** adds **guided setup**, a read-only **Doctor preflight check** and **private SMTP password entry**. **Coloured output**, startup summaries and verbose/debug modes make monitoring easier to follow. It protects saved history and credentials, improves error alerts and adds verifiable downloads. **ntfy artwork is now optional** and needs an extra dependency.

**Features and improvements**:

- **NEW:** **Guided setup** - `--setup` wizard collects the profile, intervals, credentials, notifications and output files. Review or edit answers before saving and confirm replacements. Reruns preserve saved settings and move retained credentials to the private dotenv file. A first run without a saved target offers setup
- **NEW:** **Saved target and status file** - Set `TARGET_STEAM_ID` to start monitoring without arguments. Use `--status-file` or `STEAM_STATUS_FILE` to choose where the last seen status is stored
- **NEW:** **Doctor preflight check** - `--doctor` checks configuration, Steam access, notifications and output destinations with suggested fixes. It writes no files and sends test notifications only after confirmation
- **NEW:** **Private SMTP password setup** - `--set-smtp-password` takes a hidden password and checks it with the mail server before saving. Guided setup also checks email credentials without sending a message
- **NEW:** **Clearer output and diagnostics** - Coloured output and a short startup summary show the active settings. `--verbose` adds operational updates and `--debug` adds technical traces. Secrets are redacted and logs retain the full summary
- **NEW:** **Configurable TLS verification** - `VERIFY_SSL` covers outbound certificate checks, including email. Verification is on by default and disabling it produces a warning
- **IMPROVE:** **Clearer errors and recovery** - Failures include repair guidance, periodic outage reminders and recovery notices. Persistent rate limits trigger enabled error alerts after five minutes. Failed monitoring-error alerts retry per channel without repeating successful deliveries. Other alerts are not queued for later retry
- **IMPROVE:** **One webhook setting for presence** - `WEBHOOK_ACTIVE_INACTIVE_NOTIFICATION` and `--webhook-active-inactive` replace the separate active and inactive switches, matching the email side. Configurations that set `WEBHOOK_ACTIVE_NOTIFICATION` or `WEBHOOK_INACTIVE_NOTIFICATION` still apply and a startup note names the replacement. The startup summary and Doctor now use the same alert names for email and webhooks
- **IMPROVE:** **Optional ntfy artwork** - Pillow is no longer installed by default and artwork is disabled. To keep artwork after upgrading, install `steam_monitor[ntfy-images]` and set `NTFY_IMAGES = True`
- **IMPROVE:** **Terminal and saved-log colours** - `--truncate N` limits screen width while logs retain full lines. It works without `wcwidth`, which improves Unicode width measurements. Copy the updated `grc/conf.monitor_logs` to `~/.grc/` to use the live terminal colours in saved logs
- **IMPROVE:** **Notification output** - Subjects omit program-name prefixes. Set `DELIVERY_CONFIRMATIONS = False` to hide delivery confirmations while keeping verbose diagnostics
- **IMPROVE:** **Documentation and verifiable downloads** - A [searchable guide](https://misiektoja.github.io/steam_monitor/) covers setup, usage and troubleshooting. Releases include checksums and signed build attestations

**Bug fixes**:

- **BUGFIX:** **Protected monitoring history** - Status and games-library files use Steam64 IDs, with automatic migration. Failed or incomplete library reads retain saved history and damaged status files stop monitoring before replacement. Status timestamps ahead of the clock are retained with corrected timing
- **BUGFIX:** **Safer configuration loading** - Configuration files are read as settings instead of executed as Python. Plain values and references to other settings still work. Replace imports, function calls and calculations with plain settings
- **BUGFIX:** **Safer configuration and secret updates** - `--generate-config FILE` confirms replacement and creates a backup. Non-interactive replacement requires `--force`. Shell redirection with `>` bypasses these protections. Exported secrets work without a dotenv file. Command-line credentials and nonempty startup exports retain priority after `SIGHUP`. Change those values and restart to replace them. Reloads apply changed or removed file-owned secrets
- **BUGFIX:** **Safer alerts and output** - Webhook retries keep their original destination and credentials. Discord templates cannot enable mentions and invalid templates are rejected before delivery. Error messages redact credentials, including SMTP rejection replies. Webhooks refuse redirects and upstream text cannot clear or retitle the terminal. Emails accepted by the mail server no longer become false failures if closing the connection fails, avoiding duplicate retries
- **BUGFIX:** **Reliable startup and status reminders** - Configured timing, connectivity and screen settings now take effect consistently. Redirected output avoids terminal-clearing errors. Liveness reminders cover online and offline targets and now default to 24 hours

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

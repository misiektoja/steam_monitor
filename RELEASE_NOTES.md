# steam_monitor release notes

This is a high-level summary of the most important changes.

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

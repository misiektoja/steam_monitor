# steam_monitor release notes

This is a high-level summary of the most important changes. 

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

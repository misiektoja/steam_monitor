# steam_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 1.1 (23 May 2024)

**Features and Improvements**:

- New feature counting overall time and number of played games in the session
- Possibility to define STEAM_API_KEY via command line argument (**-u** / **--steam_api_key**)
- Improvements for running the code in Python under Windows
- Possibility to define output log file name suffix (**-y** / **--log_file_suffix**)
- Information about log file name visible in the start screen
- Email sending function send_email() has been rewritten to detect invalid SMTP settings
- Strings have been converted to f-strings for better code visibility
- Better detection of wrong command line arguments
- Rewritten get_date_from_ts(), get_short_date_from_ts(), get_hour_min_from_ts() and get_range_of_dates_from_tss() functions to automatically detect if time object is timestamp or datetime
- Help screen reorganization
- pep8 style convention corrections

**Bug fixes**:

- Improved exception handling while processing JSON files

# Changes in 1.0 (25 Apr 2024)

**Features and Improvements**:

- Support for detection of short offline interruptions (and adjustment of online start timestamp)
- Additional information in the subject of email notifications

**Bug fixes**:

- Fixes for handling situations where some profile information is not available

#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.6

Tool implementing real-time tracking of Steam players activities:
https://github.com/misiektoja/steam_monitor/

Python pip3 requirements:

steam[client]
requests
python-dateutil
python-dotenv (optional)
colorama (optional, for better colours on Windows terminals)
"""

VERSION = "1.6"

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

CONFIG_BLOCK = """
# Get your Steam Web API key from:
# http://steamcommunity.com/dev/apikey
#
# Provide the STEAM_API_KEY secret using one of the following methods:
#   - Pass it at runtime with -u / --steam-api-key
#   - Set it as an environment variable (e.g. export STEAM_API_KEY=...)
#   - Add it to ".env" file (STEAM_API_KEY=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
STEAM_API_KEY = "your_steam_web_api_key"

# SMTP settings for sending email notifications
# If left as-is, no notifications will be sent
#
# Provide the SMTP_PASSWORD secret using one of the following methods:
#   - Set it as an environment variable (e.g. export SMTP_PASSWORD=...)
#   - Add it to ".env" file (SMTP_PASSWORD=...) for persistent use
# Fallback:
#   - Hard-code it in the code or config file
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
RECEIVER_EMAIL = "your_receiver_email"

# Whether to send an email when user goes online/offline
# Can also be enabled via the -a flag
ACTIVE_INACTIVE_NOTIFICATION = False

# Whether to send an email on game start/change/stop
# Can also be enabled via the -g flag
GAME_CHANGE_NOTIFICATION = False

# Whether to send an email on all status changes (online/away/snooze/offline)
# Can also be enabled via the -s flag
STATUS_NOTIFICATION = False

# Whether to send an email on errors
# Can also be disabled via the -e flag
ERROR_NOTIFICATION = True

# Whether to periodically check the user's Steam level and total XP for changes
# (disabled by default to avoid extra API usage)
# Can also be enabled via the --check-level-xp flag
STEAM_LEVEL_XP_CHECK = False

# Whether to send an email when user's Steam level or total XP changes
# Requires STEAM_LEVEL_XP_CHECK to be enabled; can also be enabled via the --notify-level-xp flag
STEAM_LEVEL_XP_NOTIFICATION = False

# Whether to periodically check the user's friends list for changes
# (disabled by default to avoid extra API usage)
# Can also be enabled via the --check-friends flag
FRIENDS_CHECK = False

# Whether to send an email when the user's friends list changes
# Requires FRIENDS_CHECK to be enabled; can also be enabled via the --notify-friends flag
FRIENDS_NOTIFICATION = False

# How often to check for player activity when the user is offline; in seconds
# Can also be set using the -c flag
STEAM_CHECK_INTERVAL = 120  # 2 min

# How often to check for player activity when the user is online, away or snoozing; in seconds
# Can also be set using the -k flag
STEAM_ACTIVE_CHECK_INTERVAL = 60  # 1 min

# If the user disconnects (offline) and reconnects (online) within OFFLINE_INTERRUPT seconds,
# the online session start time will be restored to the previous session's start time (short offline interruption),
# and previous session statistics (like total playtime and number of played games) will be preserved
OFFLINE_INTERRUPT = 420  # 7 mins

# Steam's inactivity thresholds (approximate, in seconds)
# User status changes to "away" after ~5 minutes of inactivity while showing "online"
STEAM_AWAY_INACTIVITY_THRESHOLD = 300  # 5 minutes
# User status changes to "snooze" after ~2 hours of being in "away" status
STEAM_SNOOZE_INACTIVITY_THRESHOLD = 7200  # 2 hours

# How often to print a "liveness check" message to the output; in seconds
# Set to 0 to disable
LIVENESS_CHECK_INTERVAL = 43200  # 12 hours

# URL used to verify internet connectivity at startup
CHECK_INTERNET_URL = 'https://api.steampowered.com/'

# Timeout used when checking initial internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# CSV file to write all status & game changes
# Can also be set using the -b flag
CSV_FILE = ""

# Optional separate CSV file for profile-related changes (Steam level, total XP, friends changes)
# Can also be set using the --profile-csv-file flag
PROFILE_CSV_FILE = ""

# Location of the optional dotenv file which can keep secrets
# If not specified it will try to auto-search for .env files
# To disable auto-search, set this to the literal string "none"
# Can also be set using the --env-file flag
DOTENV_FILE = ""

# Suffix to append to the output filenames instead of default user Steam ID
# Can also be set using the -y flag
FILE_SUFFIX = ""

# Base name for the log file. Output will be saved to steam_monitor_<user_steam_id/file_suffix>.log
# Can include a directory path to specify the location, e.g. ~/some_dir/steam_monitor
ST_LOGFILE = "steam_monitor"

# Whether to disable logging to steam_monitor_<user_steam_id/file_suffix>.log
# Can also be disabled via the -d flag
DISABLE_LOGGING = False

# Width of horizontal line
HORIZONTAL_LINE = 113

# Whether to clear the terminal screen after starting the tool
CLEAR_SCREEN = True

# Whether to use coloured output in the terminal (auto-disabled if the terminal
# does not appear to support colours or when output is redirected to a file)
# Can also be disabled via the --no-color flag
COLORED_OUTPUT = True

# Colour theme used for different parts of the output
# Keys are logical names used by the tool, values are colour/style strings
# You can combine multiple attributes with spaces or '+', for example:
#   "bright_cyan bold", "yellow", "red underline", "bright_magenta bold underline", "red bold blink"
# Valid colour names: black, red, green, yellow, blue, magenta, cyan, white,
# and their bright_ variants (bright_red, bright_green, ...).
COLOR_THEME = {
    # General sections
    "header": "bright_cyan",
    "section": "bright_white",
    # Identity
    "username": "blue underline",
    "steam_id": "bright_magenta",
    # Status values
    "status_online": "green",
    "status_offline": "red",
    "status_away": "yellow",
    "status_snooze": "magenta",
    "status_other": "white",
    # Activity / game info
    "status_change": "yellow",
    "game": "bright_yellow",
    "duration": "green",
    # Misc
    "timestamp_label": "",
    "timestamp_value": "cyan",
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "signal": "yellow",
    # Dates
    "date": "magenta",
    "date_range": "magenta",
    # Boolean values
    "boolean_true": "green",
    "boolean_false": "red",
}

# Value used by signal handlers increasing/decreasing the check for player activity
# when user is online/away/snooze (STEAM_ACTIVE_CHECK_INTERVAL); in seconds
STEAM_ACTIVE_CHECK_SIGNAL_VALUE = 30  # 30 seconds
"""

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

# Default dummy values so linters shut up
# Do not change values below - modify them in the configuration section or config file instead
STEAM_API_KEY = ""
SMTP_HOST = ""
SMTP_PORT = 0
SMTP_USER = ""
SMTP_PASSWORD = ""
SMTP_SSL = False
SENDER_EMAIL = ""
RECEIVER_EMAIL = ""
ACTIVE_INACTIVE_NOTIFICATION = False
GAME_CHANGE_NOTIFICATION = False
STATUS_NOTIFICATION = False
ERROR_NOTIFICATION = False
STEAM_LEVEL_XP_CHECK = False
STEAM_LEVEL_XP_NOTIFICATION = False
FRIENDS_CHECK = False
FRIENDS_NOTIFICATION = False
PROFILE_CSV_FILE = ""
STEAM_CHECK_INTERVAL = 0
STEAM_ACTIVE_CHECK_INTERVAL = 0
OFFLINE_INTERRUPT = 0
STEAM_AWAY_INACTIVITY_THRESHOLD = 0
STEAM_SNOOZE_INACTIVITY_THRESHOLD = 0
LIVENESS_CHECK_INTERVAL = 0
CHECK_INTERNET_URL = ""
CHECK_INTERNET_TIMEOUT = 0
CSV_FILE = ""
DOTENV_FILE = ""
FILE_SUFFIX = ""
ST_LOGFILE = ""
DISABLE_LOGGING = False
HORIZONTAL_LINE = 0
CLEAR_SCREEN = False
STEAM_ACTIVE_CHECK_SIGNAL_VALUE = 0
COLORED_OUTPUT = False
COLOR_THEME = {}

exec(CONFIG_BLOCK, globals())

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "steam_monitor.conf"

# List of secret keys to load from env/config
SECRET_KEYS = ("STEAM_API_KEY", "SMTP_PASSWORD")

LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / STEAM_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Status', 'Game name', 'Game ID']

profile_csvfieldnames = ['Date', 'Event', 'OldValue', 'NewValue', 'Delta', 'FriendSteamID', 'FriendPersona', 'FriendRealName']

steam_personastates = ["offline", "online", "busy", "away", "snooze", "looking to trade", "looking to play"]
steam_visibilitystates = ["private", "private", "private", "public"]

CLI_CONFIG_PATH = None

# to solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"


import sys

if sys.version_info < (3, 6):
    print("* Error: Python version 3.6 or higher required !")
    sys.exit(1)

import time
import string
import json
import os
from datetime import datetime
from dateutil import relativedelta
import calendar
import requests as req
import signal
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import csv
import platform
from platform import system
import re
import ipaddress

try:
    from colorama import init as colorama_init  # type: ignore[import]
except ImportError:
    colorama_init = None

try:
    import steam.steamid
    import steam.webapi
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the Steam library !\n\nTo install it, run:\n    pip3 install \"steam[client]\"\n\nOnce installed, re-run this tool. For more help, visit:\nhttps://github.com/ValvePython/steam/")
import shutil
from pathlib import Path


# ANSI escape sequence helper used for colouring and stripping colour codes
ANSI_ESCAPE_RE = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")

# Internal flag & style map for colour handling
COLOR_ENABLED = False
_COLOR_STYLES = {}

# Default built-in colour theme. Values can be overridden via COLOR_THEME in config
DEFAULT_COLOR_THEME = {
    # General sections
    "header": "bright_cyan",
    "section": "bright_white",
    # Identity
    "username": "blue underline",
    "steam_id": "bright_magenta",
    # Status values
    "status_online": "green",
    "status_offline": "red",
    "status_away": "yellow",
    "status_snooze": "magenta",
    "status_other": "white",
    # Activity / game info
    "status_change": "yellow",
    "game": "bright_yellow",
    "duration": "green",
    # Misc
    "timestamp_label": "",
    "timestamp_value": "cyan",
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "signal": "yellow",
    # Dates
    "date": "magenta",
    "date_range": "magenta",
    # Boolean values
    "boolean_true": "green",
    "boolean_false": "red",
}

ANSI_RESET = "\033[0m"

# Mapping of style names to ANSI SGR codes
_STYLE_CODES = {
    "bold": "1",
    "dim": "2",
    "underline": "4",
    "blink": "5",
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_black": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}

# Pre-compiled regexes used for line-level colourisation
_TIMESTAMP_LINE_RE = re.compile(r"^(Timestamp:\s+)(.*)$")
_STATUS_LINE_RE = re.compile(r"^(Status:\s+)([A-Za-z ]+)$")
_DISPLAY_NAME_RE = re.compile(r"^(Display name:\s+)(.*)$")
# 'Steam user <display name> ...' where name can contain spaces
_STEAM_USER_LINE_RE = re.compile(
    r"^(Steam user )(.+?)( (?:changed status|started playing|stopped playing|changed game from|now plays).*)$"
)
_USER_IN_GAME_RE = re.compile(r"^(User is currently in-game:\s+)(.*)$")
# Long date in format returned by get_date_from_ts, e.g. 'Sun 21 Apr 2024, 15:08:45'
_LONG_DATE_RE = re.compile(r"\b\w{3}\s+\d{1,2}\s+\w{3}\s+\d{4},\s+\d{2}:\d{2}:\d{2}\b")
# Short range date in parentheses, e.g. '(Sat 22 Nov 16:54 - 17:58)'
_SHORT_RANGE_DATE_RE = re.compile(
    r"\(\w{3}\s+\d{1,2}\s+\w{3}\s+\d{2}:\d{2}\s*-\s*\d{2}:\d{2}\)"
)
# Date range without year, e.g. 'Sat 22 Nov 03:24 - 08:28'
_DATE_RANGE_RE = re.compile(
    r"\b\w{3}\s+\d{1,2}\s+\w{3}\s+\d{2}:\d{2}\s*-\s*\d{2}:\d{2}\b"
)
_STATUS_CHANGE_RE = re.compile(
    r"^(Steam user .+? changed status from\s+)([a-zA-Z ]+)(\s+to\s+)([a-zA-Z ]+)(.*)$"
)
_GAME_CHANGE_RE = re.compile(
    r"^(Steam user .+? )(started playing|stopped playing|changed game from)(.*)$"
)
_DURATION_RE = re.compile(
    r"(\d+\s+(seconds?|minutes?|hours?|days?|weeks?|months?|years?))", re.IGNORECASE
)
_ONLINE_WORD_RE = re.compile(r"(?i)( online| appeared |\bYes\b)")
_OFFLINE_WORD_RE = re.compile(r"(?i)( offline| away| snooze|\bNo\b)")
_BOOLEAN_TRUE_RE = re.compile(r"\bTrue\b")
_BOOLEAN_FALSE_RE = re.compile(r"\bFalse\b")
# Game names in quotes, but exclude file paths (containing underscores followed by more text, dots, or slashes)
_GAME_NAME_QUOTED_RE = re.compile(r"(['\"])((?![^'\"]*[._/])[^'\"]+)\1")


# Builds ANSI escape sequence from a style description string
def _build_ansi_sequence(style_str):
    if not style_str:
        return ""
    parts = re.split(r"[+ ]+", style_str.strip().lower())
    codes = []
    for p in parts:
        code = _STYLE_CODES.get(p)
        if code:
            codes.append(code)
    if not codes:
        return ""
    return f"\033[{';'.join(codes)}m"


# Detects whether the given output stream likely supports ANSI colours
def _stream_supports_color(stream):
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    if os.getenv("NO_COLOR"):
        return False
    # On Windows with colorama, skip TERM check since colorama handles ANSI translation
    # Windows Terminal and Command Prompt often don't set TERM, but colorama works fine
    if not (colorama_init and system() == 'Windows'):
        term = os.getenv("TERM", "")
        if term.lower() in ("", "dumb", "unknown"):
            return False
    # If stdin is a pipe, we're likely being piped (e.g., via tee), so disable colors
    # to avoid writing ANSI codes to files
    if hasattr(sys.stdin, "isatty") and not sys.stdin.isatty():
        return False
    return True


# Initializes colour handling based on config and terminal capabilities
def init_color_output(stream):
    global COLOR_ENABLED, _COLOR_STYLES

    # On Windows, initialize colorama before checking color support
    # This allows colorama to enable ANSI support, which may affect the isatty() check
    if colorama_init and system() == 'Windows':
        try:
            colorama_init(autoreset=False)
        except Exception:
            pass

    COLOR_ENABLED = bool(globals().get("COLORED_OUTPUT", False)) and _stream_supports_color(stream)

    if not COLOR_ENABLED:
        _COLOR_STYLES = {}
        return

    user_theme = globals().get("COLOR_THEME") if isinstance(globals().get("COLOR_THEME"), dict) else {}
    theme = {**DEFAULT_COLOR_THEME, **(user_theme or {})}

    styles = {}
    for name, style_str in theme.items():
        seq = _build_ansi_sequence(style_str)
        if seq:
            styles[name] = seq
    _COLOR_STYLES = styles


# Applies a configured colour style (by logical part name) to the given text
def colorize(part, text):
    if not COLOR_ENABLED:
        return text
    start = _COLOR_STYLES.get(part)
    if not start:
        return text
    return f"{start}{text}{ANSI_RESET}"


# Returns coloured representation of a textual Steam status string
def colorize_status(status_text):
    status = (status_text or "").strip().lower()
    if status in ("online", "available", "active"):
        key = "status_online"
    elif status in ("offline", "invisible", "inactive"):
        key = "status_offline"
    elif status == "away":
        key = "status_away"
    elif status == "snooze":
        key = "status_snooze"
    else:
        key = "status_other"
    return colorize(key, status_text)


# Applies colour rules to a single output line
def _colorize_line(line):
    original = line

    # Timestamp lines
    m = _TIMESTAMP_LINE_RE.match(line.strip("\n"))
    if m:
        label, rest = m.groups()
        colored = f"{colorize('timestamp_label', label)}{colorize('timestamp_value', rest)}"
        return colored + ("\n" if line.endswith("\n") else "")

    # Status: ONLINE / OFFLINE ...
    m = _STATUS_LINE_RE.match(line.strip("\n"))
    if m:
        label, status = m.groups()
        colored = f"{label}{colorize_status(status)}"
        return colored + ("\n" if line.endswith("\n") else "")

    # Display name: <username>
    m = _DISPLAY_NAME_RE.match(line.strip("\n"))
    if m:
        label, name = m.groups()
        colored = f"{label}{colorize('username', name)}"
        return colored + ("\n" if line.endswith("\n") else "")

    # Steam user <name> ... lines (apply username colour but continue for further rules)
    m = _STEAM_USER_LINE_RE.match(line)
    if m:
        prefix, user, rest = m.groups()
        line = f"{prefix}{colorize('username', user)}{rest}"

    # "User is currently in-game: <name>"
    m = _USER_IN_GAME_RE.match(line)
    if m:
        prefix, game = m.groups()
        return f"{prefix}{colorize('game', game)}"

    # Status change long line
    m = _STATUS_CHANGE_RE.match(line)
    if m:
        pfx, old_s, mid, new_s, tail = m.groups()
        # Colour only the status words; keep the surrounding text in default colour
        return f"{pfx}{colorize_status(old_s)}{mid}{colorize_status(new_s)}{tail}"

    # Game change lines - don't color the verb, just process the line normally
    # (game names in quotes will be colored separately below)

    # Highlight durations
    def _dur_repl(mo):
        return colorize("duration", mo.group(0))

    line = _DURATION_RE.sub(_dur_repl, line)

    # Highlight long date strings (info mode, account creation date, etc.)
    line = _LONG_DATE_RE.sub(lambda mo: colorize("date", mo.group(0)), line)
    # Highlight short date ranges in parentheses, e.g. '(Sat 22 Nov 16:54 - 17:58)'
    line = _SHORT_RANGE_DATE_RE.sub(lambda mo: colorize("date_range", mo.group(0)), line)
    # Highlight date ranges without year, e.g. 'Sat 22 Nov 03:24 - 08:28'
    line = _DATE_RANGE_RE.sub(lambda mo: colorize("date_range", mo.group(0)), line)

    # Highlight game names in quotes
    def _game_name_repl(mo):
        quote_char, game_name = mo.groups()
        return f"{quote_char}{colorize('game', game_name)}{quote_char}"
    line = _GAME_NAME_QUOTED_RE.sub(_game_name_repl, line)

    # Highlight boolean values first
    line = _BOOLEAN_TRUE_RE.sub(lambda mo: colorize("boolean_true", mo.group(0)), line)
    line = _BOOLEAN_FALSE_RE.sub(lambda mo: colorize("boolean_false", mo.group(0)), line)

    # Highlight online/offline keywords
    line = _ONLINE_WORD_RE.sub(lambda mo: colorize("status_online", mo.group(0)), line)

    def _offline_repl(mo):
        text = mo.group(0)
        lower = text.lower()
        if "away" in lower:
            return colorize("status_away", text)
        if "snooze" in lower:
            return colorize("status_snooze", text)
        return colorize("status_offline", text)

    line = _OFFLINE_WORD_RE.sub(_offline_repl, line)

    # Errors / warnings (avoid colouring summary lines like 'errors = False')
    lowered = original.lower()
    if any(w in lowered for w in ("failure", "forbidden", "timeout")) or (
        "error" in lowered and "[errors =" not in lowered
    ):
        return colorize("error", line)
    if "warning" in lowered and "[warnings =" not in lowered:
        return colorize("warning", line)
    if "signal" in lowered and "received" in lowered:
        return colorize("signal", line)

    return line


# Applies colourisation to multi-line text, preserving line breaks
def apply_color_to_text(text):
    if not COLOR_ENABLED:
        return text

    parts = []
    for chunk in text.splitlines(keepends=True):
        if chunk.endswith(("\n", "\r")):
            stripped = chunk.rstrip("\r\n")
            newline = chunk[len(stripped):]
            parts.append(_colorize_line(stripped) + newline)
        else:
            parts.append(_colorize_line(chunk))
    return "".join(parts)


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename, strip_ansi=True):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")
        self.strip_ansi = strip_ansi

    def write(self, message):
        coloured = apply_color_to_text(message)
        self.terminal.write(coloured)

        # Expand tabs for file output (stdout remains untouched)
        expanded_message = message.expandtabs(8)

        if self.strip_ansi:
            clean = ANSI_ESCAPE_RE.sub("", expanded_message)
            self.logfile.write(clean)
        else:
            self.logfile.write(expanded_message)
        self.terminal.flush()
        self.logfile.flush()

    def flush(self):
        self.terminal.flush()
        self.logfile.flush()


# Simple colour-aware stdout wrapper used when logging is disabled
# Applies the same line-based colouring rules as Logger, but does not write anything to a log file
class ColorStream(object):
    def __init__(self, stream):
        self.terminal = stream

    def write(self, message):
        coloured = apply_color_to_text(message)
        self.terminal.write(coloured)
        self.terminal.flush()

    def flush(self):
        self.terminal.flush()


# Signal handler when user presses Ctrl+C
def signal_handler(sig, frame):
    sys.stdout = stdout_bck
    print('\n* You pressed Ctrl+C, tool is terminated.')
    sys.exit(0)


# Checks internet connectivity
def check_internet(url=CHECK_INTERNET_URL, timeout=CHECK_INTERNET_TIMEOUT):
    try:
        _ = req.get(url, timeout=timeout)
        return True
    except req.RequestException as e:
        print(f"* No connectivity, please check your network:\n\n{e}")
        return False


# Clears the terminal screen
def clear_screen(enabled=True):
    if not enabled:
        return
    # Don't clear screen if stdout is redirected (not a TTY)
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return
    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except Exception:
        print("* Cannot clear the screen contents")


# Converts absolute value of seconds to human readable format
def display_time(seconds, granularity=2):
    intervals = (
        ('years', 31556952),  # approximation
        ('months', 2629746),  # approximation
        ('weeks', 604800),    # 60 * 60 * 24 * 7
        ('days', 86400),      # 60 * 60 * 24
        ('hours', 3600),      # 60 * 60
        ('minutes', 60),
        ('seconds', 1),
    )
    result = []

    if seconds > 0:
        for name, count in intervals:
            value = seconds // count
            if value:
                seconds -= value * count
                if value == 1:
                    name = name.rstrip('s')
                result.append(f"{value} {name}")
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Calculates time span between two timestamps, accepts timestamp integers, floats and datetime objects
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1 = timestamp1
    ts2 = timestamp2

    if type(timestamp1) is int:
        dt1 = datetime.fromtimestamp(int(ts1))
    elif type(timestamp1) is float:
        ts1 = int(round(ts1))
        dt1 = datetime.fromtimestamp(ts1)
    elif type(timestamp1) is datetime:
        dt1 = timestamp1
        ts1 = int(round(dt1.timestamp()))
    else:
        return ""

    if type(timestamp2) is int:
        dt2 = datetime.fromtimestamp(int(ts2))
    elif type(timestamp2) is float:
        ts2 = int(round(ts2))
        dt2 = datetime.fromtimestamp(ts2)
    elif type(timestamp2) is datetime:
        dt2 = timestamp2
        ts2 = int(round(dt2.timestamp()))
    else:
        return ""

    if ts1 >= ts2:
        ts_diff = ts1 - ts2
    else:
        ts_diff = ts2 - ts1
        dt1, dt2 = dt2, dt1

    if ts_diff > 0:
        date_diff = relativedelta.relativedelta(dt1, dt2)
        years = date_diff.years
        months = date_diff.months
        weeks = date_diff.weeks
        if not show_weeks:
            weeks = 0
        days = date_diff.days
        if weeks > 0:
            days = days - (weeks * 7)
        hours = date_diff.hours
        if (not show_hours and ts_diff > 86400):
            hours = 0
        minutes = date_diff.minutes
        if (not show_minutes and ts_diff > 3600):
            minutes = 0
        seconds = date_diff.seconds
        if (not show_seconds and ts_diff > 60):
            seconds = 0
        date_list = [years, months, weeks, days, hours, minutes, seconds]

        for index, interval in enumerate(date_list):
            if interval > 0:
                name = intervals[index]
                if interval == 1:
                    name = name.rstrip('s')
                result.append(f"{interval} {name}")
        return ', '.join(result[:granularity])
    else:
        return '0 seconds'


# Sends email notification
def send_email(subject, body, body_html, use_ssl, smtp_timeout=15):
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')

    try:
        ipaddress.ip_address(str(SMTP_HOST))
    except ValueError:
        if not fqdn_re.search(str(SMTP_HOST)):
            print("Error sending email - SMTP settings are incorrect (invalid IP address/FQDN in SMTP_HOST)")
            return 1

    try:
        port = int(SMTP_PORT)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        print("Error sending email - SMTP settings are incorrect (invalid port number in SMTP_PORT)")
        return 1

    if not email_re.search(str(SENDER_EMAIL)) or not email_re.search(str(RECEIVER_EMAIL)):
        print("Error sending email - SMTP settings are incorrect (invalid email in SENDER_EMAIL or RECEIVER_EMAIL)")
        return 1

    if not SMTP_USER or not isinstance(SMTP_USER, str) or SMTP_USER == "your_smtp_user" or not SMTP_PASSWORD or not isinstance(SMTP_PASSWORD, str) or SMTP_PASSWORD == "your_smtp_password":
        print("Error sending email - SMTP settings are incorrect (check SMTP_USER & SMTP_PASSWORD variables)")
        return 1

    if not subject or not isinstance(subject, str):
        print("Error sending email - SMTP settings are incorrect (subject is not a string or is empty)")
        return 1

    if not body and not body_html:
        print("Error sending email - SMTP settings are incorrect (body and body_html cannot be empty at the same time)")
        return 1

    try:
        if use_ssl:
            ssl_context = ssl.create_default_context()
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
            smtpObj.starttls(context=ssl_context)
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=smtp_timeout)
        smtpObj.login(SMTP_USER, SMTP_PASSWORD)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] = str(Header(subject, 'utf-8'))

        if body:
            part1 = MIMEText(body, 'plain')
            part1 = MIMEText(body.encode('utf-8'), 'plain', _charset='utf-8')
            email_msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html, 'html')
            part2 = MIMEText(body_html.encode('utf-8'), 'html', _charset='utf-8')
            email_msg.attach(part2)

        smtpObj.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_msg.as_string())
        smtpObj.quit()
    except Exception as e:
        print(f"Error sending email: {e}")
        return 1
    return 0


# Initializes the CSV file
def init_csv_file(csv_file_name):
    try:
        if not os.path.isfile(csv_file_name) or os.path.getsize(csv_file_name) == 0:
            with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
    except Exception as e:
        raise RuntimeError(f"Could not initialize CSV file '{csv_file_name}': {e}")


# Writes CSV entry
def write_csv_entry(csv_file_name, timestamp, status, gamename, gameid):
    try:

        with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow({'Date': timestamp, 'Status': status, 'Game name': gamename, 'Game ID': gameid})

    except Exception as e:
        raise RuntimeError(f"Failed to write to CSV file '{csv_file_name}': {e}")


# Initializes the profile CSV file
def init_profile_csv_file(csv_file_name):
    try:
        if not os.path.isfile(csv_file_name) or os.path.getsize(csv_file_name) == 0:
            with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=profile_csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
    except Exception as e:
        raise RuntimeError(f"Could not initialize profile CSV file '{csv_file_name}': {e}")


# Writes profile CSV entry
def write_profile_csv_entry(csv_file_name, date, event, old_value=None, new_value=None, delta=None, friend_steamid=None, friend_persona=None, friend_realname=None):
    try:
        with open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(csv_file, fieldnames=profile_csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            csvwriter.writerow({'Date': str(date), 'Event': event, 'OldValue': old_value if old_value is not None else "", 'NewValue': new_value if new_value is not None else "", 'Delta': delta if delta is not None else "", 'FriendSteamID': friend_steamid if friend_steamid is not None else "", 'FriendPersona': friend_persona if friend_persona is not None else "", 'FriendRealName': friend_realname if friend_realname is not None else ""})
    except Exception as e:
        raise RuntimeError(f"Failed to write to profile CSV file '{csv_file_name}': {e}")


# Returns the current date/time in human readable format; eg. Sun 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]} {datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")}')


# Prints the current date/time in human readable format with separator; eg. Sun 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("─" * HORIZONTAL_LINE)


# Returns the timestamp/datetime object in human readable format (long version); eg. Sun 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime("%d %b %Y, %H:%M:%S")}')


# Returns the timestamp/datetime object in human readable format (short version); eg.
# Sun 21 Apr 15:08
# Sun 21 Apr 24, 15:08 (if show_year == True and current year is different)
# Sun 21 Apr (if show_hour == False)
def get_short_date_from_ts(ts, show_year=False, show_hour=True):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    if show_hour:
        hour_strftime = " %H:%M"
    else:
        hour_strftime = ""

    if show_year and int(datetime.fromtimestamp(ts_new).strftime("%Y")) != int(datetime.now().strftime("%Y")):
        if show_hour:
            hour_prefix = ","
        else:
            hour_prefix = ""
        return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime(f"%d %b %y{hour_prefix}{hour_strftime}")}')
    else:
        return (f'{calendar.day_abbr[(datetime.fromtimestamp(ts_new)).weekday()]} {datetime.fromtimestamp(ts_new).strftime(f"%d %b{hour_strftime}")}')


# Returns the timestamp/datetime object in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts, show_seconds=False):
    if type(ts) is datetime:
        ts_new = int(round(ts.timestamp()))
    elif type(ts) is int:
        ts_new = ts
    elif type(ts) is float:
        ts_new = int(round(ts))
    else:
        return ""

    if show_seconds:
        out_strf = "%H:%M:%S"
    else:
        out_strf = "%H:%M"
    return (str(datetime.fromtimestamp(ts_new).strftime(out_strf)))


# Returns the range between two timestamps/datetime objects; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1, ts2, between_sep=" - ", short=False):
    if type(ts1) is datetime:
        ts1_new = int(round(ts1.timestamp()))
    elif type(ts1) is int:
        ts1_new = ts1
    elif type(ts1) is float:
        ts1_new = int(round(ts1))
    else:
        return ""

    if type(ts2) is datetime:
        ts2_new = int(round(ts2.timestamp()))
    elif type(ts2) is int:
        ts2_new = ts2
    elif type(ts2) is float:
        ts2_new = int(round(ts2))
    else:
        return ""

    ts1_strf = datetime.fromtimestamp(ts1_new).strftime("%Y%m%d")
    ts2_strf = datetime.fromtimestamp(ts2_new).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_hour_min_from_ts(ts2_new, show_seconds=True)}"
    else:
        if short:
            out_str = f"{get_short_date_from_ts(ts1_new)}{between_sep}{get_short_date_from_ts(ts2_new)}"
        else:
            out_str = f"{get_date_from_ts(ts1_new)}{between_sep}{get_date_from_ts(ts2_new)}"
    return (str(out_str))


# Signal handler for SIGUSR1 allowing to switch active/inactive email notifications
def toggle_active_inactive_notifications_signal_handler(sig, frame):
    global ACTIVE_INACTIVE_NOTIFICATION
    ACTIVE_INACTIVE_NOTIFICATION = not ACTIVE_INACTIVE_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [active/inactive status changes = {ACTIVE_INACTIVE_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGUSR2 allowing to switch played game changes notifications
def toggle_game_change_notifications_signal_handler(sig, frame):
    global GAME_CHANGE_NOTIFICATION
    GAME_CHANGE_NOTIFICATION = not GAME_CHANGE_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [game changes = {GAME_CHANGE_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGCONT allowing to switch all status changes notifications
def toggle_all_status_changes_notifications_signal_handler(sig, frame):
    global STATUS_NOTIFICATION
    STATUS_NOTIFICATION = not STATUS_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [all status changes = {STATUS_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGURG allowing to switch Steam level/XP changes notifications
def toggle_level_xp_notifications_signal_handler(sig, frame):
    global STEAM_LEVEL_XP_NOTIFICATION
    STEAM_LEVEL_XP_NOTIFICATION = not STEAM_LEVEL_XP_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [Steam level/XP changes = {STEAM_LEVEL_XP_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGPIPE allowing to switch friends list changes notifications
def toggle_friends_notifications_signal_handler(sig, frame):
    global FRIENDS_NOTIFICATION
    FRIENDS_NOTIFICATION = not FRIENDS_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [friends changes = {FRIENDS_NOTIFICATION}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGTRAP allowing to increase check timer for player activity when user is online by STEAM_ACTIVE_CHECK_SIGNAL_VALUE seconds
def increase_active_check_signal_handler(sig, frame):
    global STEAM_ACTIVE_CHECK_INTERVAL
    STEAM_ACTIVE_CHECK_INTERVAL = STEAM_ACTIVE_CHECK_INTERVAL + STEAM_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Steam timers: [active check interval: {display_time(STEAM_ACTIVE_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGABRT allowing to decrease check timer for player activity when user is online by STEAM_ACTIVE_CHECK_SIGNAL_VALUE seconds
def decrease_active_check_signal_handler(sig, frame):
    global STEAM_ACTIVE_CHECK_INTERVAL
    if STEAM_ACTIVE_CHECK_INTERVAL - STEAM_ACTIVE_CHECK_SIGNAL_VALUE > 0:
        STEAM_ACTIVE_CHECK_INTERVAL = STEAM_ACTIVE_CHECK_INTERVAL - STEAM_ACTIVE_CHECK_SIGNAL_VALUE
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Steam timers: [active check interval: {display_time(STEAM_ACTIVE_CHECK_INTERVAL)}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGHUP allowing to reload secrets from .env
def reload_secrets_signal_handler(sig, frame):
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")

    # disable autoscan if DOTENV_FILE set to none
    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        # reload .env if python-dotenv is installed
        try:
            from dotenv import load_dotenv, find_dotenv
            if DOTENV_FILE:
                env_path = DOTENV_FILE
            else:
                env_path = find_dotenv()
            if env_path:
                load_dotenv(env_path, override=True)
            else:
                print("* No .env file found, skipping env-var reload")
        except ImportError:
            env_path = None
            print("* python-dotenv not installed, skipping env-var reload")

    if env_path:
        for secret in SECRET_KEYS:
            old_val = globals().get(secret)
            val = os.getenv(secret)
            if val is not None and val != old_val:
                globals()[secret] = val
                print(f"* Reloaded {secret} from {env_path}")

    print_cur_ts("Timestamp:\t\t\t")


# Finds an optional config file
def find_config_file(cli_path=None):
    """
    Search for an optional config file in:
      1) CLI-provided path (must exist if given)
      2) ./{DEFAULT_CONFIG_FILENAME}
      3) ~/.{DEFAULT_CONFIG_FILENAME}
      4) script-directory/{DEFAULT_CONFIG_FILENAME}
    """

    if cli_path:
        p = Path(os.path.expanduser(cli_path))
        return str(p) if p.is_file() else None

    candidates = [
        Path.cwd() / DEFAULT_CONFIG_FILENAME,
        Path.home() / f".{DEFAULT_CONFIG_FILENAME}",
        Path(__file__).parent / DEFAULT_CONFIG_FILENAME,
    ]

    for p in candidates:
        if p.is_file():
            return str(p)
    return None


# Resolves an executable path by checking if it's a valid file or searching in $PATH
def resolve_executable(path):
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path

    found = shutil.which(path)
    if found:
        return found

    raise FileNotFoundError(f"Could not find executable '{path}'")


# Prints country/region using raw Steam fields
def print_country_region(player):
    country_code = player.get('loccountrycode')
    state_code = player.get('locstatecode')
    city_id = player.get('loccityid')

    if country_code:
        print(f"Country code:\t\t\t{country_code}")
    if state_code:
        print(f"State/Region code:\t\t{state_code}")
    if city_id:
        print(f"City ID (Steam):\t\t{city_id}")


# Fetches recent achievements for the user
def fetch_recent_achievements(steamid, s_api, s_played, max_games=15, max_achievements=10, force_use_owned_games=False):
    achievements = []

    games_from_owned = False
    games = []

    # If force_use_owned_games is True, skip GetRecentlyPlayedGames and go straight to owned games
    if not force_use_owned_games:
        games = s_played.get("response", {}).get("games", []) if isinstance(s_played, dict) else []

    # Fallback: if recently played games are hidden or empty, or if force_use_owned_games is True, try owned games
    if not games or force_use_owned_games:
        try:
            # Call GetOwnedGames with all parameters that the steam.webapi wrapper
            # considers required, to avoid local validation errors before the HTTP call.
            owned = s_api.call(
                "IPlayerService.GetOwnedGames",
                steamid=steamid,
                include_appinfo=1,
                include_played_free_games=1,
                appids_filter=[],          # empty list → no filtering, all games
                include_free_sub=0,        # 0 = do not include free subscriptions
                include_extended_appinfo=0,  # keep response small, we only need playtime/name
                language="en",
            )
            owned_games = owned.get("response", {}).get("games", []) if isinstance(owned, dict) else []
            if owned_games:
                # Sort by total playtime (most played first) as a heuristic for relevance
                games = sorted(
                    owned_games,
                    key=lambda g: g.get("playtime_forever", 0),
                    reverse=True,
                )
                games_from_owned = True
        except Exception:
            games = []

    if not games:
        return achievements

    # Limit number of API calls only when we truly have a "recently played" list.
    # For owned-games fallback, consider all games so that low-playtime fresh games
    # (with new achievements) are not missed.
    for idx, game in enumerate(games):
        if not games_from_owned and idx >= max_games:
            break
        appid = game.get("appid")
        game_name = game.get("name") or f"AppID {appid}"
        if not appid:
            continue

        try:
            stats = s_api.call(
                "ISteamUserStats.GetPlayerAchievements",
                steamid=steamid,
                appid=appid,
            )
        except Exception:
            # Game may not have achievements or the API might not support it
            continue

        playerstats = stats.get("playerstats", {}) if isinstance(stats, dict) else {}
        ach_list = playerstats.get("achievements", []) if isinstance(playerstats, dict) else []

        for ach in ach_list:
            try:
                if not isinstance(ach, dict):
                    continue
                if ach.get("achieved") not in (1, True):
                    continue
                unlock_ts = ach.get("unlocktime") or ach.get("unlock_time") or 0
                if not unlock_ts:
                    continue

                achievements.append(
                    {
                        "game": game_name,
                        "name": ach.get("name") or ach.get("apiname") or "",
                        "description": ach.get("description") or "",
                        "unlocktime": int(unlock_ts),
                    }
                )
            except Exception:
                continue

    # Sort by unlock time (most recent first) and limit to requested number
    achievements.sort(key=lambda a: a.get("unlocktime", 0), reverse=True)
    return achievements[:max_achievements]


# Fetches and displays recent achievements for a Steam user
def display_recent_achievements(steamid, s_api, s_played, max_games=15, max_achievements=10, force_use_owned_games=False):
    print(f"\n* Fetching recent achievements...")
    achievements = fetch_recent_achievements(steamid, s_api, s_played, max_games=max_games, max_achievements=max_achievements, force_use_owned_games=force_use_owned_games)

    if not achievements:
        print("* No recent achievements found or access is restricted by the user's privacy settings.")
        print("* Note: 'Game details' privacy must allow the API to see play data and achievements.")
        return

    print(f"\nRecent achievements ({len(achievements)}):")
    print("─" * HORIZONTAL_LINE)

    for i, ach in enumerate(achievements, 1):
        game_name = ach.get("game", "Unknown Game")
        ach_name = ach.get("name", "Unknown Achievement")
        description = ach.get("description", "")
        unlock_ts = ach.get("unlocktime", 0)

        print(f"\n{i}. {colorize('game', game_name)}")
        print(f"   Achievement: {colorize('section', ach_name)}")
        if description:
            print(f"   Description: {description}")
        if unlock_ts:
            date_str = get_date_from_ts(int(unlock_ts))
            print(f"   Earned: {colorize('date', date_str)}")
        else:
            print(f"   Earned: {colorize('warning', 'Date not available')}")


# Gets detailed user information and displays it (for -i/--info mode)
def display_user_info(steamid, list_friends=False, show_achievements=False, achievements_count=None, achievements_use_owned_games=False):
    steamid_coloured = colorize("steam_id", str(steamid))
    print(f"* Fetching details for Steam user with ID '{steamid_coloured}'...\n")

    try:
        s_api = steam.webapi.WebAPI(key=STEAM_API_KEY)
        s_user = s_api.call('ISteamUser.GetPlayerSummaries', steamids=str(steamid))
        s_played = s_api.call('IPlayerService.GetRecentlyPlayedGames', steamid=steamid, count=5)
    except Exception as e:
        print(f"* Error: {e}")
        sys.exit(1)

    try:
        username = s_user["response"]["players"][0].get("personaname")
    except Exception:
        print(f"* Error: User with Steam64 ID {steamid} does not exist!")
        sys.exit(1)

    status = int(s_user["response"]["players"][0].get("personastate"))
    visibilitystate = int(s_user["response"]["players"][0].get("communityvisibilitystate"))
    realname = s_user["response"]["players"][0].get("realname", "")
    profile_url = s_user["response"]["players"][0].get("profileurl")
    timecreated = s_user["response"]["players"][0].get("timecreated")
    lastlogoff = s_user["response"]["players"][0].get("lastlogoff")
    gameid = s_user["response"]["players"][0].get("gameid")
    gamename = s_user["response"]["players"][0].get("gameextrainfo", "")

    status_ts_old = int(time.time())
    status_ts_old_bck = status_ts_old
    last_status_ts = 0
    last_status = -1

    if status == 0:
        steam_last_status_file = f"steam_{username}_last_status.json"

        if os.path.isfile(steam_last_status_file):
            try:
                with open(steam_last_status_file, 'r', encoding="utf-8") as f:
                    last_status_read = json.load(f)
                if last_status_read:
                    last_status_ts = last_status_read[0]
                    last_status = last_status_read[1]
                    if lastlogoff and lastlogoff > last_status_ts:
                        status_ts_old = lastlogoff
                    else:
                        status_ts_old = last_status_ts
            except Exception:
                pass

        if status_ts_old == status_ts_old_bck and lastlogoff:
            status_ts_old = lastlogoff

    print(f"Steam64 ID:\t\t\t{steamid}")
    print(f"Display name:\t\t\t{username}")
    if realname:
        print(f"Real name:\t\t\t{realname}")
    try:
        player_obj = s_user["response"]["players"][0]
        print_country_region(player_obj)
    except Exception:
        pass

    print(f"\nStatus:\t\t\t\t{str(steam_personastates[status]).upper()}")
    print(f"Profile visibility:\t\t{steam_visibilitystates[visibilitystate]}")

    if timecreated:
        print(f"\nAccount creation date:\t\t{get_date_from_ts(timecreated)}")

    if profile_url:
        print(f"\nProfile URL:\t\t\t{profile_url}")

    s_level_displayed = False
    try:
        s_level = s_api.call('IPlayerService.GetSteamLevel', steamid=steamid)
        print(f"\nSteam level:\t\t\t{s_level['response'].get('player_level', 'n/a')}")
        s_level_displayed = True
    except Exception:
        pass

    try:
        badges = s_api.call('IPlayerService.GetBadges', steamid=steamid)
        player_xp = badges['response'].get('player_xp', 0)
        xp_to_level = badges['response'].get('player_xp_needed_to_level_up', 0)
        xp_current_level = badges['response'].get('player_xp_needed_current_level', 0)
        badge_count = len(badges['response'].get('badges', []))

        if not s_level_displayed:
            print()
        print(f"Badges earned:\t\t\t{badge_count}")
        print(f"Total XP:\t\t\t{player_xp}")
        print(f"XP to next level:\t\t{xp_to_level}")
        print(f"XP in current level:\t\t{xp_current_level}")
    except Exception:
        pass

    try:
        bans = s_api.call('ISteamUser.GetPlayerBans', steamids=str(steamid))
        if bans['players']:
            b = bans['players'][0]
            print(f"\nVAC banned:\t\t\t{b.get('VACBanned')} ({b.get('NumberOfVACBans', 0)})")
            print(f"Community banned:\t\t{b.get('CommunityBanned')}")
            econ_ban_map = {"none": "False", "banned": "True", "probation": "Probation"}
            econ_ban = b.get('EconomyBan', 'none')
            print(f"Economy ban:\t\t\t{econ_ban_map.get(econ_ban, econ_ban)}")
            print(f"Days since last ban:\t\t{b.get('DaysSinceLastBan')}")
    except Exception:
        pass

    try:
        friends = s_api.call('ISteamUser.GetFriendList', steamid=steamid, relationship='friend')
        friend_entries = friends.get('friendslist', {}).get('friends', [])
        n_friends = len(friend_entries)
        print(f"\nFriends:\t\t\t{n_friends}")

        if list_friends and friend_entries:
            friend_ids = [f.get('steamid') for f in friend_entries if f.get('steamid')]
            print("\nFriends list:")

            # Steam Web API allows up to 100 steamids per GetPlayerSummaries call, so chunk the requests
            chunk_size = 100
            for i in range(0, len(friend_ids), chunk_size):
                chunk = friend_ids[i:i + chunk_size]
                try:
                    summaries = s_api.call(
                        'ISteamUser.GetPlayerSummaries',
                        steamids=",".join(chunk),
                    )
                except Exception as e:
                    print(f"* Warning: Cannot fetch friend details: {e}")
                    break

                players = summaries.get("response", {}).get("players", [])
                for p in players:
                    persona = p.get("personaname", "")
                    real_name = p.get("realname") or ""
                    sid = p.get("steamid", "")
                    if real_name:
                        print(f"- {persona} ({real_name}) [{sid}]")
                    else:
                        print(f"- {persona} [{sid}]")
    except Exception:
        pass

    if status == 0 and status_ts_old != status_ts_old_bck:
        last_status_dt_str = datetime.fromtimestamp(status_ts_old).strftime("%d %b %Y, %H:%M:%S")
        last_status_ts_weekday = str(calendar.day_abbr[(datetime.fromtimestamp(status_ts_old)).weekday()])
        print(f"\n* Last time user was available:\t{last_status_ts_weekday} {last_status_dt_str}")
        print(f"* User is OFFLINE for:\t\t{calculate_timespan(int(time.time()), int(status_ts_old), show_seconds=False)}")

    try:
        owned = s_api.call('IPlayerService.GetOwnedGames', steamid=steamid, include_appinfo=1, include_played_free_games=1)
        games = owned.get('response', {}).get('games', [])
        if games:
            top = sorted(games, key=lambda g: g.get('playtime_forever', 0), reverse=True)[:5]
            print("\nTop games by lifetime hours:")
            for i, g in enumerate(top, 1):
                hours = int(g.get('playtime_forever', 0) / 60)
                print(f"{i} {g.get('name')} - {hours}h")
    except Exception:
        pass

    if gameid:
        print(f"\nUser is currently in-game:\t{gamename}")

    if "games" in s_played["response"].keys() and s_played["response"]["games"]:
        print(f"\nList of recently played games:")
        for i, game in enumerate(s_played["response"]["games"]):
            name = game.get('name')
            mins_2w = game.get('playtime_2weeks', 0) or 0
            mins_total = game.get('playtime_forever', 0) or 0
            hrs_2w = mins_2w // 60
            hrs_total = mins_total // 60
            print(f"{i + 1} {name} (last 2w: {hrs_2w}h, total: {hrs_total}h)")

        total_2w = sum(g.get('playtime_2weeks', 0) or 0 for g in s_played["response"]["games"]) // 60
        print(f"\nHours played last 2 weeks:\t{total_2w}h")

    if show_achievements:
        max_ach = achievements_count if isinstance(achievements_count, int) and achievements_count > 0 else 10
        display_recent_achievements(steamid, s_api, s_played, max_games=15, max_achievements=max_ach, force_use_owned_games=achievements_use_owned_games)


# Main function that monitors gaming activity of the specified Steam user
def steam_monitor_user(steamid, csv_file_name, profile_csv_file_name=None):

    alive_counter = 0
    status_ts = 0
    status_ts_old = 0
    status_online_start_ts = 0
    status_online_start_ts_old = 0
    game_ts = 0
    game_ts_old = 0
    status = 0
    game_total_ts = 0
    games_number = 0
    game_total_after_offline_counted = False
    estimated_last_activity_ts = 0  # Estimated timestamp when user was last active (used for away/snooze calculations)
    last_steam_level = None
    last_player_xp = None
    last_friend_ids = None

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print(f"* Error: {e}")

    try:
        if profile_csv_file_name:
            init_profile_csv_file(profile_csv_file_name)
    except Exception as e:
        print(f"* Error: {e}")

    try:
        s_api = steam.webapi.WebAPI(key=STEAM_API_KEY)
        s_user = s_api.call('ISteamUser.GetPlayerSummaries', steamids=str(steamid))
        s_played = s_api.call('IPlayerService.GetRecentlyPlayedGames', steamid=steamid, count=5)
    except Exception as e:
        print(f"* Error: {e}")
        sys.exit(1)

    try:
        username = s_user["response"]["players"][0].get("personaname")
    except Exception:
        print(f"* Error: User with Steam64 ID {steamid} does not exist!")
        sys.exit(1)

    status = int(s_user["response"]["players"][0].get("personastate"))
    visibilitystate = int(s_user["response"]["players"][0].get("communityvisibilitystate"))

    realname = s_user["response"]["players"][0].get("realname", "")
    profile_url = s_user["response"]["players"][0].get("profileurl")
    timecreated = s_user["response"]["players"][0].get("timecreated")
    lastlogoff = s_user["response"]["players"][0].get("lastlogoff")
    gameid = s_user["response"]["players"][0].get("gameid")
    gamename = s_user["response"]["players"][0].get("gameextrainfo", "")

    status_ts_old = int(time.time())
    status_ts_old_bck = status_ts_old

    if status > 0:
        status_online_start_ts = status_ts_old
        status_online_start_ts_old = status_online_start_ts

    steam_last_status_file = f"steam_{username}_last_status.json"
    last_status_read = []
    last_status_ts = 0
    last_status = -1

    if os.path.isfile(steam_last_status_file):
        try:
            with open(steam_last_status_file, 'r', encoding="utf-8") as f:
                last_status_read = json.load(f)
        except Exception as e:
            print(f"* Cannot load last status from '{steam_last_status_file}' file: {e}")
        if last_status_read:
            last_status_ts = last_status_read[0]
            last_status = last_status_read[1]
            # Backward compatibility: check if estimated_last_activity_ts exists (new format has 3 elements)
            if len(last_status_read) >= 3 and last_status_read[2] is not None:
                estimated_last_activity_ts = last_status_read[2]
            steam_last_status_file_mdate_dt = datetime.fromtimestamp(int(os.path.getmtime(steam_last_status_file)))
            steam_last_status_file_mdate = steam_last_status_file_mdate_dt.strftime("%d %b %Y, %H:%M:%S")
            steam_last_status_file_mdate_weekday = str(calendar.day_abbr[(steam_last_status_file_mdate_dt).weekday()])

            print(f"* Last status loaded from file '{steam_last_status_file}' ({steam_last_status_file_mdate_weekday} {steam_last_status_file_mdate})")

            if last_status_ts > 0:
                last_status_dt_str = datetime.fromtimestamp(last_status_ts).strftime("%d %b %Y, %H:%M:%S")
                last_status_str = str(steam_personastates[last_status]).upper()
                last_status_ts_weekday = str(calendar.day_abbr[(datetime.fromtimestamp(last_status_ts)).weekday()])
                print(f"* Last status read from file: {last_status_str} ({last_status_ts_weekday} {last_status_dt_str})")

                if lastlogoff and status == 0 and lastlogoff > last_status_ts:
                    status_ts_old = lastlogoff
                elif status == 0:
                    status_ts_old = last_status_ts
                if status > 0 and status == last_status:
                    status_online_start_ts = last_status_ts
                    status_online_start_ts_old = status_online_start_ts
                    status_ts_old = last_status_ts

    if last_status_ts > 0 and status != last_status:
        last_status_to_save = []
        last_status_to_save.append(status_ts_old)
        last_status_to_save.append(status)
        # Save estimated_last_activity_ts if status is away or snooze, otherwise save None
        if status == 3 or status == 4:  # away (3) or snooze (4)
            if estimated_last_activity_ts > 0:
                last_status_to_save.append(estimated_last_activity_ts)
            else:
                last_status_to_save.append(None)
        else:
            last_status_to_save.append(None)
        try:
            with open(steam_last_status_file, 'w', encoding="utf-8") as f:
                json.dump(last_status_to_save, f, indent=2)
        except Exception as e:
            print(f"* Cannot save last status to '{steam_last_status_file}' file: {e}")

    try:
        if csv_file_name and (status != last_status):
            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), steam_personastates[status], gamename, gameid)
    except Exception as e:
        print(f"* Error: {e}")

    print(f"\nSteam64 ID:\t\t\t{steamid}")
    print(f"Display name:\t\t\t{username}")
    if realname:
        print(f"Real name:\t\t\t{realname}")
    try:
        player_obj = s_user["response"]["players"][0]
        print_country_region(player_obj)
    except Exception:
        pass

    print(f"\nStatus:\t\t\t\t{str(steam_personastates[status]).upper()}")
    print(f"Profile visibility:\t\t{steam_visibilitystates[visibilitystate]}")

    if timecreated:
        print(f"\nAccount creation date:\t\t{get_date_from_ts(timecreated)}")

    if profile_url:
        print(f"\nProfile URL:\t\t\t{profile_url}")

    # Optional level/XP snapshot at monitoring start
    if STEAM_LEVEL_XP_CHECK:
        s_level_displayed = False
        try:
            s_level = s_api.call('IPlayerService.GetSteamLevel', steamid=steamid)
            print(f"\nSteam level:\t\t\t{s_level.get('response', {}).get('player_level', 'n/a')}")
            s_level_displayed = True
        except Exception:
            s_level_displayed = False

        try:
            badges = s_api.call('IPlayerService.GetBadges', steamid=steamid)
            resp = badges.get('response', {}) if isinstance(badges, dict) else {}
            player_xp = resp.get('player_xp', 0)
            xp_to_level = resp.get('player_xp_needed_to_level_up', 0)
            xp_current_level = resp.get('player_xp_needed_current_level', 0)
            badge_count = len(resp.get('badges', []))

            if not s_level_displayed:
                print()
            print(f"Badges earned:\t\t\t{badge_count}")
            print(f"Total XP:\t\t\t{player_xp}")
            print(f"XP to next level:\t\t{xp_to_level}")
            print(f"XP in current level:\t\t{xp_current_level}")
        except Exception:
            pass

    # Optional friends snapshot at monitoring start
    if FRIENDS_CHECK:
        try:
            friends = s_api.call('ISteamUser.GetFriendList', steamid=steamid, relationship='friend')
            friend_entries = friends.get('friendslist', {}).get('friends', []) if isinstance(friends, dict) else []
            n_friends = len(friend_entries)
            print(f"\nFriends:\t\t\t{n_friends}")
        except Exception:
            # Gracefully indicate that friends data is not accessible (privacy or API limitations)
            print(f"\nFriends:\t\t\tN/A")

    if last_status_ts == 0:
        if lastlogoff and status == 0:
            status_ts_old = lastlogoff
        last_status_to_save = []
        last_status_to_save.append(status_ts_old)
        last_status_to_save.append(status)
        # Save estimated_last_activity_ts if status is away or snooze, otherwise save None
        if status == 3 or status == 4:  # away (3) or snooze (4)
            if estimated_last_activity_ts > 0:
                last_status_to_save.append(estimated_last_activity_ts)
            else:
                last_status_to_save.append(None)
        else:
            last_status_to_save.append(None)
        try:
            with open(steam_last_status_file, 'w', encoding="utf-8") as f:
                json.dump(last_status_to_save, f, indent=2)
        except Exception as e:
            print(f"* Cannot save last status to '{steam_last_status_file}' file: {e}")

    if status_ts_old != status_ts_old_bck:
        if status == 0:
            last_status_dt_str = datetime.fromtimestamp(status_ts_old).strftime("%d %b %Y, %H:%M:%S")
            last_status_str = str(steam_personastates[last_status]).upper()
            last_status_ts_weekday = str(calendar.day_abbr[(datetime.fromtimestamp(status_ts_old)).weekday()])
            print(f"\n* Last time user was available:\t{last_status_ts_weekday} {last_status_dt_str}")
        print(f"\n* User is {str(steam_personastates[status]).upper()} for:\t\t{calculate_timespan(int(time.time()), int(status_ts_old), show_seconds=False)}")

    if gameid:
        print(f"\nUser is currently in-game:\t{gamename}")
        game_ts_old = int(time.time())
        games_number += 1

    if "games" in s_played["response"].keys() and s_played["response"]["games"]:
        print(f"\nList of recently played games:")
        for i, game in enumerate(s_played["response"]["games"]):
            name = game.get('name')
            mins_2w = game.get('playtime_2weeks', 0) or 0
            mins_total = game.get('playtime_forever', 0) or 0
            hrs_2w = mins_2w // 60
            hrs_total = mins_total // 60
            print(f"{i + 1} {name} (last 2w: {hrs_2w}h, total: {hrs_total}h)")

    status_old = status
    gameid_old = gameid
    gamename_old = gamename

    print_cur_ts("\nTimestamp:\t\t\t")

    alive_counter = 0
    email_sent = False

    m_subject = m_body = ""

    if status > 0:
        sleep_interval = STEAM_ACTIVE_CHECK_INTERVAL
    else:
        sleep_interval = STEAM_CHECK_INTERVAL

    time.sleep(sleep_interval)

    # Main loop
    while True:
        current_steam_level = None
        current_player_xp = None
        current_friend_ids = None
        try:
            s_api = steam.webapi.WebAPI(key=STEAM_API_KEY)
            s_user = s_api.call('ISteamUser.GetPlayerSummaries', steamids=str(steamid))
            s_played = s_api.call('IPlayerService.GetRecentlyPlayedGames', steamid=steamid, count=5)
            status = int(s_user["response"]["players"][0]["personastate"])
            gameid = s_user["response"]["players"][0].get("gameid")
            gamename = s_user["response"]["players"][0].get("gameextrainfo", "")
            email_sent = False

            # Fetch Steam level and total XP if tracking is enabled
            if STEAM_LEVEL_XP_CHECK:
                try:
                    s_level = s_api.call('IPlayerService.GetSteamLevel', steamid=steamid)
                    current_steam_level = s_level.get('response', {}).get('player_level')
                except Exception:
                    current_steam_level = None

                try:
                    badges = s_api.call('IPlayerService.GetBadges', steamid=steamid)
                    current_player_xp = badges.get('response', {}).get('player_xp')
                except Exception:
                    current_player_xp = None

            # Fetch friends list when tracking is enabled
            if FRIENDS_CHECK:
                try:
                    friends = s_api.call('ISteamUser.GetFriendList', steamid=steamid, relationship='friend')
                    friend_entries = friends.get('friendslist', {}).get('friends', [])
                    current_friend_ids = {f.get('steamid') for f in friend_entries if f.get('steamid')}
                except Exception:
                    current_friend_ids = None
        except Exception as e:

            if status > 0:
                sleep_interval = STEAM_ACTIVE_CHECK_INTERVAL
            else:
                sleep_interval = STEAM_CHECK_INTERVAL

            if isinstance(e, req.exceptions.HTTPError) and e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After') or sleep_interval)
                time.sleep(retry_after)
                continue
            else:
                print(f"* Error, retrying in {display_time(sleep_interval)}{': ' + str(e) if e else ''}")
                if 'Forbidden' in str(e):
                    print("* API key might not be valid anymore!")
                    if ERROR_NOTIFICATION and not email_sent:
                        m_subject = f"steam_monitor: API key error! (user: {username})"
                        m_body = f"API key might not be valid anymore: {e}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                        send_email(m_subject, m_body, "", SMTP_SSL)
                        email_sent = True

            print_cur_ts("Timestamp:\t\t\t")

            time.sleep(sleep_interval)

            continue

        change = False
        act_inact_flag = False

        status_ts = int(time.time())
        game_ts = int(time.time())

        # Player status changed
        if status != status_old:

            last_status_to_save = []
            last_status_to_save.append(status_ts)
            last_status_to_save.append(status)
            # Save estimated_last_activity_ts if status is away or snooze, otherwise save None
            if status == 3 or status == 4:  # away (3) or snooze (4)
                last_status_to_save.append(estimated_last_activity_ts)
            else:
                last_status_to_save.append(None)
            try:
                with open(steam_last_status_file, 'w', encoding="utf-8") as f:
                    json.dump(last_status_to_save, f, indent=2)
            except Exception as e:
                print(f"* Cannot save last status to '{steam_last_status_file}' file: {e}")

            print(f"Steam user {username} changed status from {steam_personastates[status_old]} to {steam_personastates[status]}")
            print(f"User was {steam_personastates[status_old]} for {calculate_timespan(int(status_ts), int(status_ts_old))} ({get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)})")

            m_subject_was_since = f", was {steam_personastates[status_old]}: {get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)}"
            m_subject_after = calculate_timespan(int(status_ts), int(status_ts_old), show_seconds=False)
            m_body_was_since = f" ({get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)})"

            m_body_short_offline_msg = ""
            m_body_inactivity_info = ""

            # Track inactivity for away/snooze status changes
            # User changed from "online" to "away" - estimate last activity as ~5 minutes before status change
            if status_old == 1 and status == 3:  # online (1) to away (3)
                estimated_last_activity_ts = status_ts - STEAM_AWAY_INACTIVITY_THRESHOLD
                online_duration = status_ts - status_ts_old
                estimated_active_duration = max(0, online_duration - STEAM_AWAY_INACTIVITY_THRESHOLD)
                estimated_inactive_duration = min(STEAM_AWAY_INACTIVITY_THRESHOLD, online_duration)

                inactivity_msg = f"User was likely active for ~{display_time(estimated_active_duration)}, then inactive for ~{display_time(estimated_inactive_duration)} before status changed to away"
                inactivity_msg_email = f"\n\n{inactivity_msg}\n\nEstimated last activity: {get_date_from_ts(estimated_last_activity_ts)}"
                print(inactivity_msg)
                print(f"Estimated last activity:\t{get_date_from_ts(estimated_last_activity_ts)}")
                m_body_inactivity_info = inactivity_msg_email

            # User changed from "away" to "snooze" - total inactivity is ~5 minutes (before away) + away duration
            elif status_old == 3 and status == 4:  # away (3) to snooze (4)
                away_duration = status_ts - status_ts_old
                # If we have estimated_last_activity_ts from when user went to away, use it
                # Otherwise estimate it as away_timestamp - 5 minutes
                if estimated_last_activity_ts > 0:
                    total_inactivity = status_ts - estimated_last_activity_ts
                    estimated_last_activity_display = get_date_from_ts(estimated_last_activity_ts)
                else:
                    # Fallback: estimate last activity as away_timestamp - 5 minutes
                    estimated_last_activity_ts = status_ts_old - STEAM_AWAY_INACTIVITY_THRESHOLD
                    total_inactivity = away_duration + STEAM_AWAY_INACTIVITY_THRESHOLD
                    estimated_last_activity_display = get_date_from_ts(estimated_last_activity_ts)

                inactivity_msg = f"User was likely inactive for ~{display_time(total_inactivity)} total before status changed to snooze (including ~{display_time(STEAM_AWAY_INACTIVITY_THRESHOLD)} before away status + {display_time(away_duration)} away)"
                inactivity_msg_email = f"\n\n{inactivity_msg}\n\nEstimated last activity: {estimated_last_activity_display}"
                print(inactivity_msg)
                print(f"Estimated last activity:\t{estimated_last_activity_display}")
                m_body_inactivity_info = inactivity_msg_email

            # Player got online (from offline, away, or snooze)
            if status_old == 0 and status > 0:
                print(f"*** User got ACTIVE ! (was offline since {get_date_from_ts(status_ts_old)})")
                game_total_after_offline_counted = False
                estimated_last_activity_ts = 0  # Reset when user goes back online
                if (status_ts - status_ts_old) > OFFLINE_INTERRUPT or not status_online_start_ts_old:
                    status_online_start_ts = status_ts
                    game_total_ts = 0
                    games_number = 0
                elif (status_ts - status_ts_old) <= OFFLINE_INTERRUPT and status_online_start_ts_old > 0:
                    status_online_start_ts = status_online_start_ts_old
                    m_body_short_offline_msg = f"\n\nShort offline interruption ({display_time(status_ts - status_ts_old)}), online start timestamp set back to {get_short_date_from_ts(status_online_start_ts_old)}"
                    print(f"Short offline interruption ({display_time(status_ts - status_ts_old)}), online start timestamp set back to {get_short_date_from_ts(status_online_start_ts_old)}")
                act_inact_flag = True
            elif (status_old == 3 or status_old == 4) and status == 1:  # away (3) or snooze (4) to online (1)
                estimated_last_activity_ts = 0  # Reset when user becomes active again

            m_body_played_games = ""

            # Player got offline
            if status_old > 0 and status == 0:
                if status_online_start_ts > 0:
                    m_subject_after = calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)
                    online_since_msg = f"(after {calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)}: {get_range_of_dates_from_tss(int(status_online_start_ts), int(status_ts), short=True)})"
                    m_subject_was_since = f", was available: {get_range_of_dates_from_tss(int(status_online_start_ts), int(status_ts), short=True)}"
                    m_body_was_since = f" ({get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)})\n\nUser was available for {calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)} ({get_range_of_dates_from_tss(int(status_online_start_ts), int(status_ts), short=True)})"
                else:
                    online_since_msg = ""
                if games_number > 0:
                    if gameid_old and not gameid:
                        game_total_ts += (int(game_ts) - int(game_ts_old))
                        game_total_after_offline_counted = True
                    m_body_played_games = f"\n\nUser played {games_number} games for total time of {display_time(game_total_ts)}"
                    print(f"User played {games_number} games for total time of {display_time(game_total_ts)}")
                print(f"*** User got OFFLINE ! {online_since_msg}")
                status_online_start_ts_old = status_online_start_ts
                status_online_start_ts = 0
                act_inact_flag = True

            m_body_user_in_game = ""
            if gameid:
                print(f"User is currently in-game: {gamename}")
                m_body_user_in_game = f"\n\nUser is currently in-game: {gamename}"

            change = True

            m_subject = f"Steam user {username} is now {steam_personastates[status]} (after {m_subject_after}{m_subject_was_since})"
            m_body = f"Steam user {username} changed status from {steam_personastates[status_old]} to {steam_personastates[status]}\n\nUser was {steam_personastates[status_old]} for {calculate_timespan(int(status_ts), int(status_ts_old))}{m_body_was_since}{m_body_inactivity_info}{m_body_short_offline_msg}{m_body_user_in_game}{m_body_played_games}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
            if STATUS_NOTIFICATION or (ACTIVE_INACTIVE_NOTIFICATION and act_inact_flag):
                print(f"Sending email notification to {RECEIVER_EMAIL}")
                send_email(m_subject, m_body, "", SMTP_SSL)
            status_ts_old = status_ts
            print_cur_ts("Timestamp:\t\t\t")

        # Player started/stopped/changed the game
        if gameid != gameid_old:

            # User changed the game
            if gameid_old and gameid:
                print(f"Steam user {username} changed game from '{gamename_old}' to '{gamename}' after {calculate_timespan(int(game_ts), int(game_ts_old))}")
                print(f"User played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=' to ')}")
                game_total_ts += (int(game_ts) - int(game_ts_old))
                games_number += 1
                m_subject = f"Steam user {username} changed game to '{gamename}' (after {calculate_timespan(int(game_ts), int(game_ts_old), show_seconds=False)}: {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True)})"
                m_body = f"Steam user {username} changed game from '{gamename_old}' to '{gamename}' after {calculate_timespan(int(game_ts), int(game_ts_old))}\n\nUser played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=' to ')}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"

            # User started playing new game
            elif not gameid_old and gameid:
                print(f"Steam user {username} started playing '{gamename}'")
                games_number += 1
                m_subject = f"Steam user {username} now plays '{gamename}'"
                m_body = f"Steam user {username} now plays '{gamename}'{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"

            # User stopped playing the game
            elif gameid_old and not gameid:
                print(f"Steam user {username} stopped playing '{gamename_old}' after {calculate_timespan(int(game_ts), int(game_ts_old))}")
                print(f"User played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=' to ')}")
                if not game_total_after_offline_counted:
                    game_total_ts += (int(game_ts) - int(game_ts_old))
                m_subject = f"Steam user {username} stopped playing '{gamename_old}' (after {calculate_timespan(int(game_ts), int(game_ts_old), show_seconds=False)}: {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True)})"
                m_body = f"Steam user {username} stopped playing '{gamename_old}' after {calculate_timespan(int(game_ts), int(game_ts_old))}\n\nUser played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=' to ')}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"

            change = True

            if GAME_CHANGE_NOTIFICATION and m_subject and m_body:
                print(f"Sending email notification to {RECEIVER_EMAIL}")
                send_email(m_subject, m_body, "", SMTP_SSL)

            game_ts_old = game_ts
            print_cur_ts("Timestamp:\t\t\t")

        # Steam level changed
        if STEAM_LEVEL_XP_CHECK and current_steam_level is not None:
            try:
                level_int = int(current_steam_level)
            except (TypeError, ValueError):
                level_int = None
            try:
                last_level_int = int(last_steam_level) if last_steam_level is not None else None
            except (TypeError, ValueError):
                last_level_int = None

            if last_level_int is not None and level_int is not None and level_int != last_level_int:
                delta = level_int - last_level_int
                direction = "increased" if delta > 0 else "decreased"
                print(f"Steam user {username} level {direction} from {last_level_int} to {level_int} (delta {delta})")
                xp_info_str = ""
                if current_player_xp is not None:
                    try:
                        xp_int_for_level = int(current_player_xp)
                        xp_info_str = f"Total XP after level change:\t{xp_int_for_level}"
                    except (TypeError, ValueError):
                        xp_info_str = ""
                if profile_csv_file_name:
                    try:
                        write_profile_csv_entry(profile_csv_file_name, date=datetime.fromtimestamp(int(time.time())), event="steam_level_change", old_value=last_level_int, new_value=level_int, delta=delta,)
                    except Exception as e:
                        print(f"* Error writing profile CSV: {e}")

                if STEAM_LEVEL_XP_NOTIFICATION:
                    m_subject = f"Steam user {username} level changed to {level_int}"
                    m_body = (
                        f"Steam user {username} level {direction} from {last_level_int} to {level_int} (delta {delta})"
                        f"\n{xp_info_str}"
                        f"{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    )
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)

                print_cur_ts("Timestamp:\t\t\t")

            if level_int is not None:
                last_steam_level = level_int

        # Total XP changed
        if STEAM_LEVEL_XP_CHECK and current_player_xp is not None:
            try:
                xp_int = int(current_player_xp)
            except (TypeError, ValueError):
                xp_int = None
            try:
                last_xp_int = int(last_player_xp) if last_player_xp is not None else None
            except (TypeError, ValueError):
                last_xp_int = None

            if last_xp_int is not None and xp_int is not None and xp_int != last_xp_int:
                delta = xp_int - last_xp_int
                direction = "increased" if delta > 0 else "decreased"
                print(f"Steam user {username} total XP {direction} from {last_xp_int} to {xp_int} (delta {delta})")

                if profile_csv_file_name:
                    try:
                        write_profile_csv_entry(profile_csv_file_name, date=datetime.fromtimestamp(int(time.time())), event="total_xp_change", old_value=last_xp_int, new_value=xp_int, delta=delta,)
                    except Exception as e:
                        print(f"* Error writing profile CSV: {e}")

                if STEAM_LEVEL_XP_NOTIFICATION:
                    m_subject = f"Steam user {username} total XP changed to {xp_int}"
                    m_body = (
                        f"Steam user {username} total XP {direction} from {last_xp_int} to {xp_int} (delta {delta})"
                        f"{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    )
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)

                print_cur_ts("Timestamp:\t\t\t")

            if xp_int is not None:
                last_player_xp = xp_int

        # Friends list changed
        if FRIENDS_CHECK and current_friend_ids is not None:
            if last_friend_ids is None:
                # Initialize baseline without treating it as a change
                last_friend_ids = current_friend_ids
            else:
                added_ids = current_friend_ids - last_friend_ids
                removed_ids = last_friend_ids - current_friend_ids

                if added_ids or removed_ids:
                    old_count = len(last_friend_ids)
                    new_count = len(current_friend_ids)
                    delta = new_count - old_count
                    print(f"Steam user {username} friends count changed from {old_count} to {new_count} (delta {delta})")

                    if profile_csv_file_name:
                        try:
                            write_profile_csv_entry(profile_csv_file_name, date=datetime.fromtimestamp(int(time.time())), event="friends_count_change", old_value=old_count, new_value=new_count, delta=delta,)
                        except Exception as e:
                            print(f"* Error writing profile CSV: {e}")

                    added_details = []
                    removed_details = []

                    def _fetch_friend_summaries(id_set):
                        if not id_set:
                            return []
                        summaries = []
                        ids_list = list(id_set)
                        chunk_size = 100
                        for i in range(0, len(ids_list), chunk_size):
                            chunk = ids_list[i:i + chunk_size]
                            try:
                                resp = s_api.call('ISteamUser.GetPlayerSummaries', steamids=",".join(chunk))
                                players = resp.get('response', {}).get('players', [])
                                summaries.extend(players)
                            except Exception:
                                continue
                        return summaries

                    added_players = []
                    removed_players = []

                    try:
                        added_players = _fetch_friend_summaries(added_ids)
                        added_map = {p.get('steamid'): p for p in added_players}
                        for sid in added_ids:
                            p = added_map.get(sid, {})
                            persona = p.get('personaname') or ""
                            real = p.get('realname') or ""
                            if profile_csv_file_name:
                                try:
                                    write_profile_csv_entry(profile_csv_file_name, date=datetime.fromtimestamp(int(time.time())), event="friend_added", friend_steamid=sid, friend_persona=persona, friend_realname=real,)
                                except Exception as e:
                                    print(f"* Error writing profile CSV: {e}")
                            if real:
                                added_details.append(f"- {persona} ({real}) [{sid}]")
                            else:
                                added_details.append(f"- {persona or sid} [{sid}]")
                    except Exception:
                        pass

                    try:
                        removed_players = _fetch_friend_summaries(removed_ids)
                        removed_map = {p.get('steamid'): p for p in removed_players}
                        for sid in removed_ids:
                            p = removed_map.get(sid, {})
                            persona = p.get('personaname') or ""
                            real = p.get('realname') or ""
                            if profile_csv_file_name:
                                try:
                                    write_profile_csv_entry(profile_csv_file_name, date=datetime.fromtimestamp(int(time.time())), event="friend_removed", friend_steamid=sid, friend_persona=persona, friend_realname=real,)
                                except Exception as e:
                                    print(f"* Error writing profile CSV: {e}")
                            if real:
                                removed_details.append(f"- {persona} ({real}) [{sid}]")
                            else:
                                removed_details.append(f"- {persona or sid} [{sid}]")
                    except Exception:
                        pass

                    if added_details:
                        print("New friends added:")
                        for line in added_details:
                            print(line)
                    if removed_details:
                        print("Friends removed:")
                        for line in removed_details:
                            print(line)

                    if FRIENDS_NOTIFICATION:
                        m_subject_friends = f"Steam user {username} friends list changed (now {new_count})"
                        body_lines = [
                            f"Steam user {username} friends count changed from {old_count} to {new_count} (delta {delta})",
                        ]
                        if added_details:
                            body_lines.append("\nNew friends added:")
                            body_lines.extend(added_details)
                        if removed_details:
                            body_lines.append("\nFriends removed:")
                            body_lines.extend(removed_details)
                        m_body_friends = "\n".join(body_lines) + get_cur_ts(nl_ch + nl_ch + "Timestamp: ")
                        print(f"Sending email notification to {RECEIVER_EMAIL}")
                        send_email(m_subject_friends, m_body_friends, "", SMTP_SSL)

                    print_cur_ts("Timestamp:\t\t\t")

                    alive_counter = 0
                    last_friend_ids = current_friend_ids

        if change:
            alive_counter = 0

            try:
                if csv_file_name:
                    write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), steam_personastates[status], gamename, gameid)
            except Exception as e:
                print(f"* Error: {e}")

        status_old = status
        gameid_old = gameid
        gamename_old = gamename
        alive_counter += 1

        if LIVENESS_CHECK_COUNTER and alive_counter >= LIVENESS_CHECK_COUNTER and status == 0:
            print_cur_ts("Liveness check, timestamp:\t")
            alive_counter = 0

        if status > 0:
            time.sleep(STEAM_ACTIVE_CHECK_INTERVAL)
        else:
            time.sleep(STEAM_CHECK_INTERVAL)


def main():
    global CLI_CONFIG_PATH, DOTENV_FILE, LIVENESS_CHECK_COUNTER, STEAM_API_KEY, CSV_FILE, PROFILE_CSV_FILE, DISABLE_LOGGING, ST_LOGFILE, ACTIVE_INACTIVE_NOTIFICATION, GAME_CHANGE_NOTIFICATION, STATUS_NOTIFICATION, ERROR_NOTIFICATION, STEAM_LEVEL_XP_CHECK, STEAM_LEVEL_XP_NOTIFICATION, FRIENDS_CHECK, FRIENDS_NOTIFICATION, STEAM_CHECK_INTERVAL, STEAM_ACTIVE_CHECK_INTERVAL, FILE_SUFFIX, SMTP_PASSWORD, stdout_bck, COLORED_OUTPUT, COLOR_THEME

    if "--generate-config" in sys.argv:
        config_content = CONFIG_BLOCK.strip("\n") + "\n"
        # Check if a filename was provided after --generate-config
        try:
            idx = sys.argv.index("--generate-config")
            if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-"):
                # Write directly to file (bypasses PowerShell UTF-16 encoding issue on Windows)
                output_file = sys.argv[idx + 1]
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(config_content)
                print(f"Config written to: {output_file}")
                sys.exit(0)
        except (ValueError, IndexError):
            pass
        # No filename provided - write to stdout using buffer to ensure UTF-8
        sys.stdout.buffer.write(config_content.encode("utf-8"))
        sys.stdout.buffer.flush()
        sys.exit(0)

    if "--version" in sys.argv:
        print(f"{os.path.basename(sys.argv[0])} v{VERSION}")
        sys.exit(0)

    stdout_bck = sys.stdout

    # Initialise colour handling based on CLI args (early check) and terminal capabilities
    if "--no-color" in sys.argv:
        globals()["COLORED_OUTPUT"] = False

    init_color_output(stdout_bck)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    clear_screen(CLEAR_SCREEN)

    print(colorize("header", f"Steam Monitoring Tool v{VERSION}\n"))

    parser = argparse.ArgumentParser(
        prog="steam_monitor",
        description=("Monitor a Steam user's playing status and send customizable email alerts [ https://github.com/misiektoja/steam_monitor/ ]"), formatter_class=argparse.RawTextHelpFormatter
    )

    # Positional
    parser.add_argument(
        "steam64_id",
        nargs="?",
        metavar="STEAM64_ID",
        help="User's Steam64 ID",
        type=int
    )

    # Version, just to list in help, it is handled earlier
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s v{VERSION}"
    )

    # Configuration & dotenv files
    conf = parser.add_argument_group("Configuration & dotenv files")
    conf.add_argument(
        "--config-file",
        dest="config_file",
        metavar="PATH",
        help="Location of the optional config file",
    )
    conf.add_argument(
        "--generate-config",
        dest="generate_config",
        nargs="?",
        const=True,
        metavar="FILENAME",
        help="Print default config template and exit (on Windows PowerShell, specify a filename to avoid redirect encoding issues)",
    )
    conf.add_argument(
        "--env-file",
        dest="env_file",
        metavar="PATH",
        help="Path to optional dotenv file (auto-search if not set, disable with 'none')",
    )

    # API settings
    creds = parser.add_argument_group("API settings")
    creds.add_argument(
        "-u", "--steam-api-key",
        dest="steam_api_key",
        metavar="STEAM_API_KEY",
        type=str,
        help="Steam Web API key"
    )
    creds.add_argument(
        "-r", "--resolve-community-url",
        dest="resolve_community_url",
        metavar="COMMUNITY_URL",
        type=str,
        help="Use Steam community URL & resolve it to Steam64 ID"
    )

    # Notifications
    notify = parser.add_argument_group("Notifications")
    notify.add_argument(
        "-a", "--notify-active-inactive",
        dest="notify_active_inactive",
        action="store_true",
        default=None,
        help="Email when user goes online/offline"
    )
    notify.add_argument(
        "-g", "--notify-game-change",
        dest="notify_game_change",
        action="store_true",
        default=None,
        help="Email on game start/change/stop"
    )
    notify.add_argument(
        "-s", "--notify-status",
        dest="notify_status",
        action="store_true",
        default=None,
        help="Email on all status changes"
    )
    notify.add_argument(
        "--notify-level-xp",
        dest="notify_level_xp",
        action="store_true",
        default=None,
        help="Email when user's Steam level or total XP changes (requires --check-level-xp or STEAM_LEVEL_XP_CHECK=True)"
    )
    notify.add_argument(
        "--notify-friends",
        dest="notify_friends",
        action="store_true",
        default=None,
        help="Email when friends list changes (requires --check-friends or FRIENDS_CHECK=True)"
    )
    notify.add_argument(
        "-e", "--no-error-notify",
        dest="notify_errors",
        action="store_false",
        default=None,
        help="Disable email on errors"
    )
    notify.add_argument(
        "--send-test-email",
        dest="send_test_email",
        action="store_true",
        help="Send test email to verify SMTP settings"
    )

    # User information
    info = parser.add_argument_group("User information")
    info.add_argument(
        "-i", "--info",
        dest="info",
        action="store_true",
        help="Get detailed user information and display it, then exit"
    )
    info.add_argument(
        "--list-friends",
        dest="list_friends",
        action="store_true",
        help="When used with -i/--info, also list all friends instead of only the count"
    )
    info.add_argument(
        "--achievements",
        dest="show_achievements",
        action="store_true",
        help="When used with -i/--info, also display recent achievements (via Steam Web API)"
    )
    info.add_argument(
        "-n", "--achievements-count",
        dest="achievements_count",
        metavar="NUMBER",
        type=int,
        help="When used with --achievements, limit number of recent achievements to display (default: 10)"
    )
    info.add_argument(
        "--achievements-all-games",
        dest="achievements_use_owned_games",
        action="store_true",
        help="When used with --achievements, check all owned games instead of only recently played games. "
             "Useful for users who haven't played recently, as their recently played list may be limited."
    )
    # Intervals & timers
    times = parser.add_argument_group("Intervals & timers")
    times.add_argument(
        "-c", "--check-interval",
        dest="check_interval",
        metavar="SECONDS",
        type=int,
        help="Polling interval when user is offline"
    )
    times.add_argument(
        "-k", "--active-interval",
        dest="active_interval",
        metavar="SECONDS",
        type=int,
        help="Polling interval when user is online"
    )

    # Features & Output
    opts = parser.add_argument_group("Features & output")
    opts.add_argument(
        "--check-level-xp",
        dest="check_level_xp",
        action="store_true",
        default=None,
        help="Track Steam level and total XP changes (console/log output)"
    )
    opts.add_argument(
        "--check-friends",
        dest="check_friends",
        action="store_true",
        default=None,
        help="Track changes in friends count and list (may be limited by privacy settings)"
    )
    opts.add_argument(
        "-b", "--csv-file",
        dest="csv_file",
        metavar="CSV_FILENAME",
        type=str,
        help="Write status & game changes to CSV"
    )
    opts.add_argument(
        "--profile-csv-file",
        dest="profile_csv_file",
        metavar="CSV_FILENAME",
        type=str,
        help="Write profile changes (Steam level/XP and friends) to a separate CSV"
    )
    opts.add_argument(
        "-y", "--file-suffix",
        dest="file_suffix",
        metavar="SUFFIX",
        type=str,
        help="Log file suffix instead of Steam64 ID"
    )
    opts.add_argument(
        "-d", "--disable-logging",
        dest="disable_logging",
        action="store_true",
        default=None,
        help="Disable logging to steam_monitor_<user_steam_id/file_suffix>.log"
    )
    opts.add_argument(
        "--no-color",
        dest="no_color",
        action="store_true",
        default=None,
        help="Disable coloured output in the terminal"
    )

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Allow empty targets if utility flags are used
    if not args.steam64_id and not args.resolve_community_url:
        utility_flags = {
            "--no-color", "-h", "--help",
            "--version", "--generate-config",
            "--send-test-email"
        }
        complex_args = [a for a in sys.argv[1:] if a not in utility_flags]

        if complex_args:
            print("\n* Error: STEAM64_ID needs to be defined !\n", flush=True)

        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.config_file:
        CLI_CONFIG_PATH = os.path.expanduser(args.config_file)

    cfg_path = find_config_file(CLI_CONFIG_PATH)

    if not cfg_path and CLI_CONFIG_PATH:
        print(f"* Error: Config file '{CLI_CONFIG_PATH}' does not exist")
        sys.exit(1)

    if cfg_path:
        try:
            with open(cfg_path, "r") as cf:
                exec(cf.read(), globals())
        except Exception as e:
            print(f"* Error loading config file '{cfg_path}': {e}")
            sys.exit(1)

    if args.env_file:
        DOTENV_FILE = os.path.expanduser(args.env_file)
    else:
        if DOTENV_FILE:
            DOTENV_FILE = os.path.expanduser(DOTENV_FILE)

    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        try:
            from dotenv import load_dotenv, find_dotenv

            if DOTENV_FILE:
                env_path = DOTENV_FILE
                if not os.path.isfile(env_path):
                    print(f"* Warning: dotenv file '{env_path}' does not exist\n")
                else:
                    load_dotenv(env_path, override=True)
            else:
                env_path = find_dotenv() or None
                if env_path:
                    load_dotenv(env_path, override=True)
        except ImportError:
            env_path = DOTENV_FILE if DOTENV_FILE else None
            if env_path:
                print(f"* Warning: Cannot load dotenv file '{env_path}' because 'python-dotenv' is not installed\n\nTo install it, run:\n    pip3 install python-dotenv\n\nOnce installed, re-run this tool\n")

    if env_path:
        for secret in SECRET_KEYS:
            val = os.getenv(secret)
            if val is not None:
                globals()[secret] = val

    if not check_internet():
        sys.exit(1)

    if args.send_test_email:
        print("* Sending test email notification ...\n")
        if send_email("steam_monitor: test email", "This is test email - your SMTP settings seems to be correct !", "", SMTP_SSL, smtp_timeout=5) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if args.steam_api_key:
        STEAM_API_KEY = args.steam_api_key

    if not STEAM_API_KEY or STEAM_API_KEY == "your_steam_web_api_key":
        print("* Error: STEAM_API_KEY (-u / --steam_api_key) value is empty or incorrect")
        sys.exit(1)

    if args.check_interval:
        STEAM_CHECK_INTERVAL = args.check_interval
        LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / STEAM_CHECK_INTERVAL

    if args.active_interval:
        STEAM_ACTIVE_CHECK_INTERVAL = args.active_interval

    s_id = 0
    if args.steam64_id:
        s_id = int(args.steam64_id)

    if args.resolve_community_url:
        print(f"* Resolving Steam community URL to Steam64 ID: {args.resolve_community_url}\n")
        try:
            s_id = steam.steamid.steam64_from_url(args.resolve_community_url)
            if s_id:
                s_id = int(s_id)
        except Exception as e:
            print("* Error: Cannot get Steam64 ID for specified community URL")
            print("*", e)
            sys.exit(1)

    if not s_id:
        # Check should have been handled earlier by the utility_flags logic
        print("* Error: STEAM64_ID needs to be defined !")
        sys.exit(1)

    if args.csv_file:
        CSV_FILE = os.path.expanduser(args.csv_file)
    else:
        if CSV_FILE:
            CSV_FILE = os.path.expanduser(CSV_FILE)

    if CSV_FILE:
        try:
            with open(CSV_FILE, 'a', newline='', buffering=1, encoding="utf-8") as _:
                pass
        except Exception as e:
            print(f"* Error: CSV file cannot be opened for writing: {e}")
            sys.exit(1)

    if args.profile_csv_file:
        PROFILE_CSV_FILE = os.path.expanduser(args.profile_csv_file)
    else:
        if PROFILE_CSV_FILE:
            PROFILE_CSV_FILE = os.path.expanduser(PROFILE_CSV_FILE)

    if PROFILE_CSV_FILE:
        try:
            with open(PROFILE_CSV_FILE, 'a', newline='', buffering=1, encoding="utf-8") as _:
                pass
        except Exception as e:
            print(f"* Error: Profile CSV file cannot be opened for writing: {e}")
            sys.exit(1)

    if args.file_suffix:
        FILE_SUFFIX = args.file_suffix
    else:
        FILE_SUFFIX = str(s_id)

    if args.no_color is True:
        COLORED_OUTPUT = False

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    # Re-initialize colour output to pick up any theme changes from config/dotenv
    init_color_output(stdout_bck)

    if not DISABLE_LOGGING:
        log_path = Path(os.path.expanduser(ST_LOGFILE))
        if log_path.parent != Path('.'):
            if log_path.suffix == "":
                log_path = log_path.parent / f"{log_path.name}_{FILE_SUFFIX}.log"
        else:
            if log_path.suffix == "":
                log_path = Path(f"{log_path.name}_{FILE_SUFFIX}.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        FINAL_LOG_PATH = str(log_path)
        sys.stdout = Logger(FINAL_LOG_PATH, strip_ansi=True)
    else:
        FINAL_LOG_PATH = None
        # Even when logging is disabled, keep coloured output on the terminal.
        sys.stdout = ColorStream(stdout_bck)

    # Handle info mode - display user information once and exit
    if args.info:
        display_user_info(s_id, list_friends=getattr(args, "list_friends", False), show_achievements=getattr(args, "show_achievements", False), achievements_count=getattr(args, "achievements_count", None), achievements_use_owned_games=getattr(args, "achievements_use_owned_games", False))
        sys.stdout = stdout_bck
        sys.exit(0)

    if args.notify_active_inactive is True:
        ACTIVE_INACTIVE_NOTIFICATION = True

    if args.notify_game_change is True:
        GAME_CHANGE_NOTIFICATION = True

    if args.notify_status is True:
        STATUS_NOTIFICATION = True

    if args.notify_errors is False:
        ERROR_NOTIFICATION = False
    if args.check_level_xp is True:
        STEAM_LEVEL_XP_CHECK = True
    if args.notify_level_xp is True:
        STEAM_LEVEL_XP_NOTIFICATION = True
    if args.check_friends is True:
        FRIENDS_CHECK = True
    if args.notify_friends is True:
        FRIENDS_NOTIFICATION = True

    if SMTP_HOST.startswith("your_smtp_server_"):
        ACTIVE_INACTIVE_NOTIFICATION = False
        GAME_CHANGE_NOTIFICATION = False
        STATUS_NOTIFICATION = False
        ERROR_NOTIFICATION = False
        STEAM_LEVEL_XP_NOTIFICATION = False
        FRIENDS_NOTIFICATION = False

    print(f"* Steam polling intervals:\t[offline: {display_time(STEAM_CHECK_INTERVAL)}] [online: {display_time(STEAM_ACTIVE_CHECK_INTERVAL)}]")
    print(f"* Email notifications:\t\t[online/offline status changes = {ACTIVE_INACTIVE_NOTIFICATION}] [game changes = {GAME_CHANGE_NOTIFICATION}]\n*\t\t\t\t[all status changes = {STATUS_NOTIFICATION}] [level/XP changes = {STEAM_LEVEL_XP_NOTIFICATION}]\n*\t\t\t\t[friends changes = {FRIENDS_NOTIFICATION}] [errors = {ERROR_NOTIFICATION}]")
    print(f"* Liveness check:\t\t{bool(LIVENESS_CHECK_INTERVAL)}" + (f" ({display_time(LIVENESS_CHECK_INTERVAL)})" if LIVENESS_CHECK_INTERVAL else ""))
    print(f"* Level/XP tracking enabled:\t{STEAM_LEVEL_XP_CHECK}")
    print(f"* Friends tracking enabled:\t{FRIENDS_CHECK}")
    print(f"* CSV logging enabled:\t\t{bool(CSV_FILE)}" + (f" ({CSV_FILE})" if CSV_FILE else ""))
    print(f"* Profile CSV logging enabled:\t{bool(PROFILE_CSV_FILE)}" + (f" ({PROFILE_CSV_FILE})" if PROFILE_CSV_FILE else ""))
    print(f"* Output logging enabled:\t{not DISABLE_LOGGING}" + (f" ({FINAL_LOG_PATH})" if not DISABLE_LOGGING else ""))
    print(f"* Configuration file:\t\t{cfg_path}")
    print(f"* Dotenv file:\t\t\t{env_path or 'None'}")

    out = f"\nMonitoring user with Steam64 ID {colorize('steam_id', str(s_id))}"
    print(colorize("header", out))
    print("-" * len(out))

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
        signal.signal(signal.SIGUSR2, toggle_game_change_notifications_signal_handler)
        signal.signal(signal.SIGCONT, toggle_all_status_changes_notifications_signal_handler)
        signal.signal(signal.SIGURG, toggle_level_xp_notifications_signal_handler)
        signal.signal(signal.SIGPIPE, toggle_friends_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)
        signal.signal(signal.SIGHUP, reload_secrets_signal_handler)

    steam_monitor_user(s_id, CSV_FILE, PROFILE_CSV_FILE)

    sys.stdout = stdout_bck
    sys.exit(0)


if __name__ == "__main__":
    main()

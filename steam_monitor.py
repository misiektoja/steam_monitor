#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v2.0

Tool implementing real-time tracking of Steam players activities:
https://github.com/misiektoja/steam_monitor/

Python pip3 requirements:

steam
requests
python-dateutil
python-dotenv (optional)
Pillow (optional, needed only when NTFY_IMAGES attaches artwork to ntfy alerts)
colorama (optional, for better colours on Windows terminals)
"""

VERSION = "2.0"

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

CONFIG_BLOCK = """
# Get your Steam Web API key from:
# http://steamcommunity.com/dev/apikey
#
# Provide the STEAM_API_KEY secret using one of the following methods:
#   - Validate and save it through a hidden prompt with --set-steam-api-key
#   - Set it as an environment variable (e.g. export STEAM_API_KEY=...)
#   - Add it to ".env" file (STEAM_API_KEY=...) for persistent use
#   - Pass it at runtime with -u / --steam-api-key (may remain in shell history)
# Fallback:
#   - Hard-code it in the code or config file
STEAM_API_KEY = "your_steam_web_api_key"

# Steam profile to monitor by Steam64 ID, Steam3 identifier, vanity name or profile URL
# A positional command-line target overrides this value
TARGET_STEAM_ID = ""

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

# Whether to send an email when the user's display (persona) name changes
# Display name changes are always detected and logged. This flag only controls email
# Can also be enabled via the --notify-name-change flag
NAME_CHANGE_NOTIFICATION = False

# Whether to send an email on errors
# Can also be disabled via the -e flag
ERROR_NOTIFICATION = True

# ----------------------------
# Webhook Notifications
# ----------------------------

# Master switch for webhook notifications through Discord or ntfy
# Event settings below select which notifications are sent
# Can also be enabled via the --webhook flag
WEBHOOK_ENABLED = False

# Service used to deliver webhook notifications: "discord" or "ntfy"
# Known Discord and ntfy.sh URLs correct a mismatched configured value at runtime
# Can also be set via the --webhook-provider flag
WEBHOOK_PROVIDER = "discord"

# Private destination used to send webhook notifications
# Discord: Edit Channel -> Integrations -> Webhooks -> New Webhook -> Copy Webhook URL
# ntfy: complete topic URL such as https://ntfy.sh/your-private-topic
# Prefer --set-webhook-url, an environment variable or a dotenv file instead of storing this private URL here
# The --webhook-url flag is available for one-run overrides but may leave the private URL in shell history
WEBHOOK_URL = "your_webhook_url"

# Discord display name (leave empty to use the webhook default)
# Applies only when WEBHOOK_PROVIDER is "discord" (ignored by the ntfy provider)
WEBHOOK_USERNAME = "Steam Monitor"

# Discord avatar URL (leave empty to use the webhook default)
# Applies only when WEBHOOK_PROVIDER is "discord" (ignored by the ntfy provider)
WEBHOOK_AVATAR_URL = ""

# Whether to send a webhook notification when the user becomes active
# Can also be enabled via the --webhook-active flag
WEBHOOK_ACTIVE_NOTIFICATION = False

# Whether to send a webhook notification when the user goes offline
# Can also be enabled via the --webhook-inactive flag
WEBHOOK_INACTIVE_NOTIFICATION = False

# Whether to send a webhook notification on any status change
# Can also be enabled via the --webhook-status flag
WEBHOOK_STATUS_NOTIFICATION = False

# Whether to send a webhook notification on game start, change or stop
# Can also be enabled via the --webhook-game-changes flag
WEBHOOK_GAME_CHANGE_NOTIFICATION = False

# Whether to send a webhook notification when the user's Steam level or total XP changes
# Requires STEAM_LEVEL_XP_CHECK; can also be enabled via the --webhook-level-xp flag
WEBHOOK_LEVEL_XP_NOTIFICATION = False

# Whether to send a webhook notification when the user's friends list changes
# Requires FRIENDS_CHECK; can also be enabled via the --webhook-friends flag
WEBHOOK_FRIENDS_NOTIFICATION = False

# Whether to send a webhook notification when the user's games library changes
# Requires GAMES_LIBRARY_CHECK; can also be enabled via the --webhook-games flag
WEBHOOK_GAMES_NOTIFICATION = False

# Whether to send a webhook notification when the user's display name changes
# Can also be enabled via the --webhook-name-change flag
WEBHOOK_NAME_CHANGE_NOTIFICATION = False

# Whether to send a webhook notification on monitoring errors
# Can also be enabled via --webhook-errors or disabled via --no-webhook-error-notify
WEBHOOK_ERROR_NOTIFICATION = True

# Optional request headers for advanced webhook integrations
# Values support the same placeholders as WEBHOOK_TEMPLATE
WEBHOOK_HEADERS = {}

# ----------------------------
# Advanced Webhook Settings
# ----------------------------

# Discord-format webhook request payload template
# Applies only when WEBHOOK_PROVIDER is "discord". The "ntfy" provider needs no template and ignores this
# value: it sends the alert body as a native ntfy message with the subject as its title. Use WEBHOOK_HEADERS
# to add ntfy options such as priority or tags
# Supported placeholders include title, description, version, image_url, fields, fields_str, color, timestamp,
# username and avatar_url
WEBHOOK_TEMPLATE = {
    "username": "{username}",
    "avatar_url": "{avatar_url}",
    "allowed_mentions": {
        "parse": [],
    },
    "embeds": [{
        "title": "{title}",
        "description": "{description}",
        "color": "{color}",
        "footer": {
            "text": "Steam Monitor v{version}",
        },
        "timestamp": "{timestamp}",
        "thumbnail": {
            "url": "{image_url}",
        },
    }],
}

# Optional transformations applied to WEBHOOK_TEMPLATE and WEBHOOK_HEADERS values
# Tuple format: (field_to_target, method_name, *optional_arguments)
#
# Examples:
#   [
#       ("title", "upper"),
#       ("description", "replace", "**", ""),
#       ("description", "strip"),
#   ]
WEBHOOK_TRANSFORMS = []

# Optional ntfy access token for Bearer authentication
# Prefer an environment variable or dotenv file instead of storing this token here
NTFY_ACCESS_TOKEN = ""

# Whether to attach a Steam avatar or game image to supported ntfy alerts
# Requires the optional Pillow package: pip3 install "steam_monitor[ntfy-images]"
# Image preparation or delivery failures fall back to text
NTFY_IMAGES = False

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

# Whether to periodically check the user's games library (game count and list) for changes
# Uses a minimal API call (no names/icons)
# Can also be enabled via the --check-games flag
GAMES_LIBRARY_CHECK = False

# Whether to send an email when the user's games library changes
# Requires GAMES_LIBRARY_CHECK to be enabled; can also be enabled via the --notify-games flag
GAMES_LIBRARY_NOTIFICATION = False

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

# Whether to verify TLS certificates on every outbound connection, email delivery included
# Only set this to False on a network that intercepts TLS with its own certificate authority
# Switching it off removes the protection against an intercepted connection
VERIFY_SSL = True

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

# Whether to print extra startup and runtime detail
# Independent of DEBUG_MODE, so enable both to see everything
# Can also be enabled via the --verbose flag, which turns it on regardless of this setting
VERBOSE_MODE = False

# Whether to print timestamped diagnostic detail, including every outbound call,
# each notification delivery attempt and the technical cause of failures
# Independent of VERBOSE_MODE, so enable both to see everything
# Can also be enabled via the --debug flag, which turns it on regardless of this setting
DEBUG_MODE = False

# Controls conversion of separator-only log lines to ASCII:
#   "Auto" - enable on Windows only (default)
#   "On"   - enable on every operating system
#   "Off"  - preserve Unicode separators in logs
ASCII_LOG_SEPARATORS = "Auto"

# Max characters per line when printing to screen to avoid line wrapping
# Does not affect log file output
# Set to 999 to auto-detect terminal width
# Applies only when DISABLE_LOGGING is False
# Can also be set via the --truncate flag
TRUNCATE_CHARS = 0

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
# The defaults below are what the tool uses while this block stays commented out. Uncomment it to override
# them and keep only the lines you want to change, so the rest keep following the tool's own defaults.
# COLOR_THEME = {
#     # General sections
#     "header": "bright_cyan",
#     "section": "bright_white",
#     # Identity
#     "username": "bright_cyan underline",
#     "id": "bright_magenta",
#     # Status values
#     "status_online": "green",
#     "status_offline": "red",
#     "status_away": "yellow",
#     "status_snooze": "magenta",
#     "status_other": "white",
#     # Activity / game info
#     "game": "bright_yellow",
#     "duration": "green",
#     # Misc
#     "timestamp_label": "",
#     "timestamp_value": "cyan",
#     "info": "cyan",
#     "warning": "yellow",
#     "error": "red",
#     "signal": "yellow",
#     "email": "bright_cyan",
#     "webhook": "bright_blue",
#     # Dates
#     "date": "magenta",
#     "date_range": "magenta",
#     # Boolean values
#     "boolean_true": "green",
#     "boolean_false": "red",
#     # Links
#     "link": "blue underline",
# }

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
TARGET_STEAM_ID = ""
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
NAME_CHANGE_NOTIFICATION = False
ERROR_NOTIFICATION = False
WEBHOOK_ENABLED = False
WEBHOOK_PROVIDER = ""
WEBHOOK_URL = ""
WEBHOOK_USERNAME = ""
WEBHOOK_AVATAR_URL = ""
WEBHOOK_ACTIVE_NOTIFICATION = False
WEBHOOK_INACTIVE_NOTIFICATION = False
WEBHOOK_STATUS_NOTIFICATION = False
WEBHOOK_GAME_CHANGE_NOTIFICATION = False
WEBHOOK_LEVEL_XP_NOTIFICATION = False
WEBHOOK_FRIENDS_NOTIFICATION = False
WEBHOOK_GAMES_NOTIFICATION = False
WEBHOOK_NAME_CHANGE_NOTIFICATION = False
WEBHOOK_ERROR_NOTIFICATION = False
WEBHOOK_HEADERS = {}
WEBHOOK_TEMPLATE = {}
WEBHOOK_TRANSFORMS = []
NTFY_ACCESS_TOKEN = ""
NTFY_IMAGES = False
STEAM_LEVEL_XP_CHECK = False
STEAM_LEVEL_XP_NOTIFICATION = False
FRIENDS_CHECK = False
FRIENDS_NOTIFICATION = False
GAMES_LIBRARY_CHECK = False
GAMES_LIBRARY_NOTIFICATION = False
PROFILE_CSV_FILE = ""
STEAM_CHECK_INTERVAL = 0
STEAM_ACTIVE_CHECK_INTERVAL = 0
OFFLINE_INTERRUPT = 0
STEAM_AWAY_INACTIVITY_THRESHOLD = 0
STEAM_SNOOZE_INACTIVITY_THRESHOLD = 0
LIVENESS_CHECK_INTERVAL = 0
CHECK_INTERNET_URL = ""
CHECK_INTERNET_TIMEOUT = 0
VERIFY_SSL = True
CSV_FILE = ""
DOTENV_FILE = ""
FILE_SUFFIX = ""
ST_LOGFILE = ""
DISABLE_LOGGING = False
ASCII_LOG_SEPARATORS = "Auto"
TRUNCATE_CHARS = 0
VERBOSE_MODE = False
DEBUG_MODE = False

# True once monitoring has printed its header, so a verbose notice after that closes its own block
MONITORING_ACTIVE = False

HORIZONTAL_LINE = 0
CLEAR_SCREEN = False
STEAM_ACTIVE_CHECK_SIGNAL_VALUE = 0
COLORED_OUTPUT = False
COLOR_THEME = {}

exec(CONFIG_BLOCK, globals())

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "steam_monitor.conf"

# Documentation links, kept as constants so error messages, help text and the guides they point at cannot drift apart
PROJECT_URL = "https://github.com/misiektoja/steam_monitor"
DOCS_BASE_URL = "https://misiektoja.github.io/steam_monitor"
GUIDE_URL = f"{DOCS_BASE_URL}/"
INSTALL_GUIDE_URL = f"{DOCS_BASE_URL}/installation/"
QUICK_START_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/"
CONFIG_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/"
CONFIG_FILE_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#configuration-file"
STEAM_API_KEY_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/#steam-web-api-key"
PRIVACY_GUIDE_URL = f"{DOCS_BASE_URL}/setup-and-first-run/#user-privacy-settings"
SMTP_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#smtp-settings"
WEBHOOK_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#webhook-settings"
SECRETS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#storing-secrets"
TLS_GUIDE_URL = f"{DOCS_BASE_URL}/configuration/#tls-verification"
USAGE_GUIDE_URL = f"{DOCS_BASE_URL}/usage/"
STEAM_API_KEY_REGISTRATION_URL = "https://steamcommunity.com/dev/apikey"
STEAM_TARGET_FORMS = "Steam64 ID, Steam3 identifier, vanity name or full profile URL"
STEAM_TARGET_INPUT_ERROR = f"Enter a {STEAM_TARGET_FORMS}, for example https://steamcommunity.com/id/<name>/"
DOCTOR_GUIDE_URL = f"{DOCS_BASE_URL}/troubleshooting/#doctor-preflight"

# Shared prefixes for the checks a delivery test depends on, kept as constants because the labels are dynamic
SMTP_READY_CHECK_LABEL = "SMTP connection and login succeeded"
WEBHOOK_READY_CHECK_LABEL = "Webhook URL, headers and alert choices look valid"

# The label every sibling monitor uses when email alerts are on but the settings they would use cannot deliver
EMAIL_UNUSABLE_CHECK_LABEL = "Email alerts are enabled but unusable"

# List of secret keys to load from env/config
SECRET_KEYS = ("STEAM_API_KEY", "SMTP_PASSWORD", "WEBHOOK_URL", "NTFY_ACCESS_TOKEN")

# Secrets supplied as arguments. The dotenv and environment lookup cannot see them, so they are recorded here
COMMAND_LINE_SECRET_KEYS = frozenset()

# The one-shot commands that only write a secret, so the other early-exit flags do not swallow them
SECRET_ACTION_FLAGS = ("--set-steam-api-key", "--set-smtp-password", "--set-webhook-url")

LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / STEAM_CHECK_INTERVAL

# The last connectivity failure, so a quiet caller can classify it instead of the check printing it
LAST_CONNECTIVITY_ERROR = None

stdout_bck = None
csvfieldnames = ['Date', 'Status', 'Game name', 'Game ID']

profile_csvfieldnames = ['Date', 'Event', 'OldValue', 'NewValue', 'Delta', 'FriendSteamID', 'FriendPersona', 'FriendRealName']

steam_personastates = ["offline", "online", "busy", "away", "snooze", "looking to trade", "looking to play"]
steam_visibilitystates = ["private", "private", "private", "public"]

CLI_CONFIG_PATH = None

# Secret names already present in the process environment before dotenv loading
EXPORTED_SECRET_KEYS = frozenset()

# to solve the issue: 'SyntaxError: f-string expression part cannot include a backslash'
nl_ch = "\n"

STARTUP_BANNER = r"""
 .---------------.    ____  _
|         .--.   |   / ___|| |_ ___  __ _ _ __ ___
|    O===|  O |  |   \___ \| __/ _ \/ _` | '_ ` _ \
|   /     '--'   |    ___) | ||  __/ (_| | | | | | |
|  O             |   |____/ \__\___|\__,_|_| |_| |_|
 '---------------'
                      __  __             _ _
                     |  \/  | ___  _ __ (_) |_ ___  _ __
                     | |\/| |/ _ \| '_ \| | __/ _ \| '__|
                     | |  | | (_) | | | | | || (_) | |
                     |_|  |_|\___/|_| |_|_|\__\___/|_|"""


import sys

# Declared once so the startup gate, the packaging metadata and any later environment check cannot disagree
MINIMUM_PYTHON_VERSION = (3, 6)
MINIMUM_PYTHON_VERSION_TEXT = ".".join(str(part) for part in MINIMUM_PYTHON_VERSION)

if sys.version_info < MINIMUM_PYTHON_VERSION:
    print(f"* Error: Python version {MINIMUM_PYTHON_VERSION_TEXT} or higher required !")
    sys.exit(1)

import time
import textwrap
import json
import os
from datetime import datetime
from dateutil import relativedelta
import calendar
import requests as req
import urllib3
import signal
import smtplib
import ssl
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
import functools
from contextlib import contextmanager
import ast
import csv
import getpass
# Referenced from the type comments below, which the linter does not parse
from typing import Any, Dict  # noqa: F401
import platform
from platform import system
import importlib.util
import math
import re
import shlex
import subprocess
from collections import namedtuple
import unicodedata
import ipaddress
import tempfile
from io import BytesIO
from email.utils import parsedate_to_datetime
from urllib.parse import unquote, urlparse, urlsplit

try:
    from colorama import init as colorama_init  # type: ignore[import]
except ImportError:
    colorama_init = None

try:
    import steam.steamid
    import steam.webapi
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the Steam library !\n\nTo install it, run:\n    pip3 install steam\n\nOnce installed, re-run this tool. For more help, visit:\nhttps://github.com/ValvePython/steam/")
import shutil
from pathlib import Path

WEBHOOK_SESSION = req.Session()

# Keep webhook delivery independent from Steam API retries and long server timers
WEBHOOK_MAX_ATTEMPTS = 2
WEBHOOK_MAX_RETRY_AFTER_SECONDS = 5.0
WEBHOOK_FALLBACK_RETRY_SECONDS = 1.0
STEAM_MAX_RETRY_AFTER_SECONDS = 3600.0
WEBHOOK_TIMEOUT_SECONDS = 10
WEBHOOK_EMBED_TITLE_LIMIT = 256
WEBHOOK_EMBED_DESCRIPTION_LIMIT = 4096
NTFY_MESSAGE_LIMIT_BYTES = 4095
NTFY_TRUNCATION_SUFFIX = "\n\n[Notification truncated to fit ntfy's 4 KB message limit]"
NTFY_IMAGE_DOWNLOAD_LIMIT_BYTES = 5 * 1024 * 1024
NTFY_IMAGE_DOWNLOAD_CHUNK_BYTES = 64 * 1024
NTFY_IMAGE_PIXEL_LIMIT = 25_000_000
NTFY_IMAGE_FILENAME = "steam-image.jpg"
# One short retry absorbs a transient failure without waiting a whole polling interval
TRANSIENT_RETRY_SECONDS = 5

NTFY_IMAGE_ALLOWED_HOST_SUFFIXES = ("steamstatic.com", "steamusercontent.com", "steamcdn-a.akamaihd.net", "steamuserimages-a.akamaihd.net")

PILImage = None  # type: Any
try:
    from PIL import Image as PILImageModule
    PILImage = PILImageModule
except ImportError:
    pass
NTFY_IMAGES_AVAILABLE = PILImage is not None


# Install methods the tool can detect, used to tailor every command it prints
INSTALL_METHOD_PYPI = "pip"
INSTALL_METHOD_SCRIPT = "manual"
INSTALL_METHOD_ENV_VAR = "STEAM_MONITOR_INSTALL_METHOD"


# Returns True when the tool runs inside a container, so printed commands and paths can be adjusted for it
def running_in_container():
    if os.environ.get("STEAM_MONITOR_IN_CONTAINER", "").strip().casefold() in ("1", "true", "yes"):
        return True
    if os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv"):
        return True
    try:
        with open("/proc/1/cgroup", encoding="utf-8", errors="replace") as cgroup_file:
            return any(marker in cgroup_file.read() for marker in ("docker", "containerd", "kubepods", "podman"))
    except OSError:
        return False


# Returns how the tool was started, either as the installed console script or as a downloaded standalone script
def install_method():
    override = os.environ.get(INSTALL_METHOD_ENV_VAR, "").strip().casefold()
    if override in (INSTALL_METHOD_PYPI, INSTALL_METHOD_SCRIPT):
        return override
    if os.path.basename(sys.argv[0] or "").casefold().endswith(".py"):
        return INSTALL_METHOD_SCRIPT
    return INSTALL_METHOD_PYPI


# Returns a readable name for the detected install method
def install_method_display_name(method=None):
    selected = install_method() if method is None else method
    base = {"pip": "PyPI install", "manual": "downloaded script"}.get(selected, selected)
    return f"{base} in a container" if running_in_container() else base


# Returns the argv prefix that invokes this tool for the detected install method
def install_command_prefix():
    if install_method() == INSTALL_METHOD_SCRIPT:
        return ["python3", os.path.basename(sys.argv[0]) or "steam_monitor.py"]
    return ["steam_monitor"]


# Returns one command-line argument quoted for the shell the user is most likely pasting into
def quote_command_argument(argument):
    text = str(argument)
    # A <placeholder> is documentation for the reader to replace, so quoting it would only be noise
    if text.startswith("<") and text.endswith(">"):
        return text
    if system() == "Windows":
        return f'"{text}"' if (not text or any(char.isspace() for char in text)) else text
    return shlex.quote(text)


# Returns a copy-pasteable command line for the detected install method, carrying non-default config and dotenv paths
def render_command(arguments=None, include_paths=True, config_path=None, env_path=None):
    parts = list(install_command_prefix())
    parts.extend(str(argument) for argument in (arguments or []))
    # An explicitly passed path is always rendered, while include_paths only governs falling back to the active ones
    selected_config = config_path if config_path is not None else (CLI_CONFIG_PATH if include_paths else None)
    selected_env = env_path if env_path is not None else (DOTENV_FILE if include_paths else None)
    if selected_config:
        parts.extend(["--config-file", str(selected_config)])
    if selected_env and str(selected_env).casefold() != "none":
        parts.extend(["--env-file", str(selected_env)])
    return " ".join(quote_command_argument(part) for part in parts)


# Renders one diagnostic line as an operation followed by comma-separated key=value fields, dropping unset ones
def format_diagnostic_line(operation, fields):
    rendered = ", ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    return f"{operation}: {rendered}" if rendered else str(operation)


# Prints one timestamped and sanitized diagnostic line only when debug mode is enabled
def debug_print(_operation, **fields):
    if DEBUG_MODE:
        # Sanitized here rather than at each call site, since one caller interpolating a secret is enough to leak it
        message = format_diagnostic_line(_operation, fields)
        print(f"[DEBUG {datetime.now().strftime('%H:%M:%S')}] {sanitize_error_text(message)}")


# Returns whether the full startup summary should be shown, which debug mode also implies
def full_startup_summary_enabled():
    return bool(VERBOSE_MODE or DEBUG_MODE)


# Prints one sanitized operational detail only when verbose mode is enabled
def verbose_print(message):
    if VERBOSE_MODE:
        print(f"* {sanitize_error_text(message)}")


# Prints verbose-only notices as one block, so a standalone line is not left without the timestamp trailer
def verbose_notice(*messages):
    if not VERBOSE_MODE or not messages:
        return
    for message in messages:
        verbose_print(message)
    # Before monitoring starts the notice belongs to the startup screen, which the monitoring header closes
    if MONITORING_ACTIVE:
        print_cur_ts("Timestamp:\t\t\t")


# Marks the point where output stops being the startup screen, so later notices close their own block
def mark_monitoring_started():
    global MONITORING_ACTIVE
    MONITORING_ACTIVE = True


# Records a swallowed exception in debug output so a silently degraded feature can still be diagnosed
def debug_swallowed_exception(context, exc):
    debug_print(context, outcome="failed", error=f"{type(exc).__name__}: {exc}")


# Strips terminal control sequences and other C0/C1 characters from third-party text before it reaches a console or a log
def sanitize_untrusted_text(value, max_length=256):
    if value is None:
        return ""
    text = str(value)
    text = ANSI_ESCAPE_RE.sub("", text)
    # Everything a remote service sends is hostile until proven otherwise, so drop the control range outright
    text = "".join(character for character in text if character == " " or not unicodedata.category(character).startswith("C"))
    text = text.strip()
    if max_length and len(text) > max_length:
        text = text[:max_length] + "..."
    return text


# Writes JSON to a file atomically, so a crash cannot leave a half-written state file behind
def write_json_atomic(destination, payload, mode=None):
    destination_path = Path(destination).expanduser()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{destination_path.name}.", suffix=".tmp", dir=str(destination_path.parent), delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(payload, temporary_file, indent=2)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        if mode is not None and os.name == "posix":
            os.chmod(str(temporary_path), mode)
        os.replace(str(temporary_path), str(destination_path))
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return str(destination_path)


# Copies an existing file to a timestamped private backup before it is replaced, returning the backup path or None
def create_timestamped_backup(destination, attempts=100):
    destination_path = Path(destination).expanduser()
    if not destination_path.is_file():
        return None
    existing_bytes = destination_path.read_bytes()
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    for attempt in range(attempts):
        suffix = f".{stamp}.bak" if attempt == 0 else f".{stamp}-{attempt}.bak"
        backup_path = destination_path.with_name(destination_path.name + suffix)
        try:
            # O_EXCL so a backup can never overwrite an earlier one, even under a concurrent run
            descriptor = os.open(str(backup_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(descriptor, "wb") as backup_file:
                backup_file.write(existing_bytes)
                backup_file.flush()
                os.fsync(backup_file.fileno())
        except Exception:
            try:
                os.unlink(str(backup_path))
            except OSError:
                pass
            raise
        return str(backup_path)
    raise OSError(f"Could not create a unique backup for '{destination_path}' after {attempts} attempts")


# Silences the repeated certificate warning once verification is off, so the choice is reported by the summary and the doctor instead of on every request
def apply_tls_verification_setting():
    if not VERIFY_SSL:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Returns the TLS context SMTP uses, unverified while VERIFY_SSL is off so email follows the same switch as every other connection
def smtp_ssl_context():
    context = ssl.create_default_context()
    if not VERIFY_SSL:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


# Returns a Steam Web API client whose session honors the configured TLS verification setting
def steam_web_api_client(api_key=None):
    selected_key = STEAM_API_KEY if api_key is None else api_key
    # Interfaces are loaded manually because the automatic load fires before the session can be configured
    client = steam.webapi.WebAPI(key=selected_key, auto_load_interfaces=False)
    # A release that moves the session should still start, verifying, rather than fail on the missing attribute
    try:
        client.session.verify = VERIFY_SSL
    except AttributeError as exc:
        debug_print("TLS verification", target="Steam Web API session", outcome="failed", error=f"{type(exc).__name__}: {exc}")
    client.load_interfaces(client.fetch_interfaces())
    return client


# Silences debug output while a raw secret is entered or validated, then restores the previous mode
@contextmanager
def debug_output_suppressed():
    global DEBUG_MODE
    previous_debug_mode = DEBUG_MODE
    DEBUG_MODE = False
    try:
        yield
    finally:
        DEBUG_MODE = previous_debug_mode


# Silences debug output for the whole of a function that handles a raw secret
def suppresses_debug_output(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with debug_output_suppressed():
            return func(*args, **kwargs)
    return wrapper


# Returns the webhook destination host on its own, so delivery can be traced without printing the private URL
def webhook_destination_host():
    try:
        return urlsplit(str(WEBHOOK_URL).strip()).hostname or "unknown host"
    except ValueError:
        return "unknown host"


# Applies only the explicitly supplied --verbose and --debug flags so the command line always wins over the config file
def apply_diagnostic_cli_flags(args):
    global VERBOSE_MODE, DEBUG_MODE
    if getattr(args, "verbose", None):
        VERBOSE_MODE = True
    if getattr(args, "debug", None):
        DEBUG_MODE = True


# Returns a placeholder reporting only whether a secret is set, never any part of its value
def mask_secret(value):
    # Diagnostic output is meant to be pasted into public bug reports, so not even a prefix of a live key may appear.
    # Which secret is loaded is answered by its name and source instead, which secret_sources reports.
    if value is None or not str(value):
        return "(not set)"
    return "<redacted>"


# Returns the newest Pillow release that still supports the running Python version
def ntfy_images_requirement():
    if sys.version_info < (3, 7):
        return "Pillow>=8.0,<9.0"
    if sys.version_info < (3, 8):
        return "Pillow>=9.0,<10.0"
    if sys.version_info < (3, 9):
        return "Pillow>=10.0,<11.0"
    if sys.version_info < (3, 10):
        return "Pillow>=11.3.0,<12"
    return "Pillow>=12.0.0"


# Returns the command that installs optional ntfy artwork support for the active installation
def ntfy_images_install_command():
    if install_method() == INSTALL_METHOD_SCRIPT:
        return 'pip3 install "{}"'.format(ntfy_images_requirement())
    return 'pip3 install "steam_monitor[ntfy-images]"'


# ANSI escape sequence helper used for colouring and stripping colour codes
ANSI_ESCAPE_RE = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")

# Matches only the colour sequences the tool emits, which truncation copies through without spending display width
SGR_SEQUENCE_RE = re.compile(r"\x1b\[[0-9;]*m")

# Internal flag & style map for colour handling
COLOR_ENABLED = False
_COLOR_STYLES = {}

# Default built-in colour theme. Values can be overridden via COLOR_THEME in config
DEFAULT_COLOR_THEME = {
    # General sections
    "header": "bright_cyan",
    "section": "bright_white",
    # Identity
    "username": "bright_cyan underline",
    "id": "bright_magenta",
    # Status values
    "status_online": "green",
    "status_offline": "red",
    "status_away": "yellow",
    "status_snooze": "magenta",
    "status_other": "white",
    # Activity / game info
    "game": "bright_yellow",
    "duration": "green",
    # Misc
    "timestamp_label": "",
    "timestamp_value": "cyan",
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "signal": "yellow",
    "email": "bright_cyan",
    "webhook": "bright_blue",
    # Dates
    "date": "magenta",
    "date_range": "magenta",
    # Boolean values
    "boolean_true": "green",
    "boolean_false": "red",
    # Links
    "link": "blue underline",
}

# COLOR_THEME key names used by older releases, still honoured so an existing config keeps working
_THEME_KEY_ALIASES = {"steam_id": "id"}

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
# The monitored account named inside a sentence, so the ID is coloured without wrapping the whole line
_MONITORED_ID_RE = re.compile(r"^(Monitoring user with Steam64 ID\s+)(\S+)$")
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
_DURATION_RE = re.compile(
    r"(\d+\s+(seconds?|minutes?|hours?|days?|weeks?|months?|years?))", re.IGNORECASE
)
_ONLINE_WORD_RE = re.compile(r"(?i)( online| appeared |\bYes\b)")
_OFFLINE_WORD_RE = re.compile(r"(?i)( offline| away| snooze|\bNo\b)")
_BOOLEAN_TRUE_RE = re.compile(r"\bTrue\b")
_BOOLEAN_FALSE_RE = re.compile(r"\bFalse\b")
_NOTIFICATION_SUMMARY_STATE_RE = re.compile(r"^(\* Notifications \((?:email|webhook)\):\s+)(On|Off)(.*)$")
# Quoted names such as game titles. At least one word character is required so a run of punctuation between two
# quotes is not read as a name. The closing quote has to be followed by whitespace, punctuation or the end of the
# line, so a title's own apostrophe does not end the name early: "Assassin's Creed Valhalla"
_QUOTED_CONTENT_RE = re.compile(r"(['\"])([^\n]*?\w[^\n]*?)\1(?=[\s.,;:!?)\]]|$)")

# Quoted values shaped like a file name or a filesystem path stay plain, since a log or state destination is
# not content. Game titles routinely contain slashes and dots, so only these two shapes are excluded
_QUOTED_FILE_LIKE_RE = re.compile(r"^[~.]?[\\/]|^[A-Za-z]:[\\/]|\.[A-Za-z0-9]{1,8}$")

# A quoted '<name>' inside a printed command is the placeholder the reader has to replace, not a game title
_QUOTED_PLACEHOLDER_RE = re.compile(r"^<[^<>]*>$")

# A quoted command-line option is an instruction to retype, not a name
_QUOTED_OPTION_RE = re.compile(r"^-")

# A quoted piece of a URL, such as the '?code=' or '&state=' a prompt points at. Only a leading '?' or '&' counts,
# so a title may end in a question mark and a title such as 'Ratchet & Clank' is still a name
_QUOTED_URL_PART_RE = re.compile(r"^[?&]|://")
_URL_RE = re.compile(r"(https?://[^\s\]]+)")

# Output labels whose value is coloured with one theme style, longest label first so a prefix cannot win
_LABEL_STYLES = (
    (("Steam64 ID:", "Target:"), "id"),
)


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

    # A config written against an older key name still wins over the default, unless it also sets the current name
    for legacy_name, current_name in _THEME_KEY_ALIASES.items():
        if user_theme and legacy_name in user_theme and current_name not in user_theme:
            theme[current_name] = user_theme[legacy_name]

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


# Splits a labelled output row into its label and value, tolerating a leading '* ' summary marker
def _split_output_label(value, labels):
    body = value.rstrip("\n")
    cursor = len(body) - len(body.lstrip())
    if body[cursor:cursor + 1] == "*":
        cursor += 1
        cursor += len(body[cursor:]) - len(body[cursor:].lstrip())
    for label in labels:
        if not body.startswith(label, cursor):
            continue
        value_start = cursor + len(label)
        value_start += len(body[value_start:]) - len(body[value_start:].lstrip())
        if value_start == cursor + len(label):
            return None
        return body[:value_start], body[value_start:]
    return None


# Colours one quoted name unless the quoted value is a path, a placeholder, an option or a piece of a URL
def _colorize_quoted_name(match):
    name = match.group(2)
    if _QUOTED_FILE_LIKE_RE.search(name) or _QUOTED_PLACEHOLDER_RE.match(name) or _QUOTED_OPTION_RE.match(name) or _QUOTED_URL_PART_RE.search(name):
        return match.group(0)
    return f"{match.group(1)}{colorize('game', name)}{match.group(1)}"


# Applies colour rules to a single output line
def _colorize_line(line, notification_summary=False):
    original = line

    if notification_summary:
        match = _NOTIFICATION_SUMMARY_STATE_RE.match(line)
        if not match:
            return line
        prefix, state, suffix = match.groups()
        state_style = "boolean_true" if state == "On" else "boolean_false"
        return f"{prefix}{colorize(state_style, state)}{suffix}"

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

    # "Monitoring user with Steam64 ID <id>"
    m = _MONITORED_ID_RE.match(line.strip("\n"))
    if m:
        prefix, steam_id = m.groups()
        colored = f"{prefix}{colorize('id', steam_id)}"
        return colored + ("\n" if line.endswith("\n") else "")

    # Any '<something> URL:' row is a link, checked before the label table so 'Profile URL:' is not read as a name
    if " URL:" in line or _split_output_label(line, ("URL:",)):
        return _URL_RE.sub(lambda mo: colorize("link", mo.group(0)), line)

    # Labelled identifier rows keep their label plain and colour only the value
    for labels, style_name in _LABEL_STYLES:
        labeled_value = _split_output_label(line, labels)
        if labeled_value:
            label, rest = labeled_value
            return f"{label}{colorize(style_name, rest)}" + ("\n" if line.endswith("\n") else "")

    # Links printed inside a sentence, such as the guide link on the welcome and doctor screens
    line = _URL_RE.sub(lambda mo: colorize("link", mo.group(0)), line)

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
    line = _QUOTED_CONTENT_RE.sub(_colorize_quoted_name, line)

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
    if "sending email" in lowered:
        return colorize("email", line)
    if "sending webhook" in lowered:
        return colorize("webhook", line)

    return line


# Applies colourisation to multi-line text, preserving line breaks
def apply_color_to_text(text):
    if not COLOR_ENABLED:
        return text

    parts = []
    in_notification_summary = False
    for chunk in text.splitlines(keepends=True):
        if chunk.endswith(("\n", "\r")):
            stripped = chunk.rstrip("\r\n")
            newline = chunk[len(stripped):]
        else:
            stripped = chunk
            newline = ""
        starts_notification_summary = _NOTIFICATION_SUMMARY_STATE_RE.match(stripped) is not None
        continues_notification_summary = in_notification_summary and stripped.startswith(" " * 32)
        in_notification_summary = starts_notification_summary or continues_notification_summary
        parts.append(_colorize_line(stripped, notification_summary=in_notification_summary) + newline)
    return "".join(parts)


# Reports whether separator-only log lines should use ASCII on this system
def ascii_log_separators_enabled():
    mode = str(ASCII_LOG_SEPARATORS).strip().lower()
    if mode not in {"auto", "on", "off"}:
        raise ValueError("ASCII_LOG_SEPARATORS must be 'Auto', 'On' or 'Off'")
    return mode == "on" or (mode == "auto" and platform.system() == "Windows")


# Converts Unicode-only horizontal separator lines to ASCII when configured
def normalize_log_separators(message):
    if not ascii_log_separators_enabled():
        return message
    return re.sub(r"(?m)^─+$", lambda match: match.group(0).replace("─", "-"), message)


# Truncates each line to a display width, expanding tabs and counting double-width characters correctly
def truncate_string_per_line(message, truncate_width, tabsize=8):
    try:
        from wcwidth import wcwidth
    except ImportError:
        return message
    truncated_lines = []
    for line in message.split("\n"):
        expanded_line = line.expandtabs(tabsize)
        current_width = 0
        truncated = []
        position = 0
        while position < len(expanded_line):
            # A colour sequence is copied through free of charge, so styling never eats into the visible width
            escape = SGR_SEQUENCE_RE.match(expanded_line, position)
            if escape:
                truncated.append(escape.group(0))
                position = escape.end()
                continue
            char = expanded_line[position]
            char_width = wcwidth(char)
            if char_width is None or char_width < 0:
                char_width = 0
            if current_width + char_width > truncate_width:
                break
            truncated.append(char)
            current_width += char_width
            position += 1
        truncated_lines.append("".join(truncated))
    return "\n".join(truncated_lines)


# Resolves CLI and configured truncation settings while expanding the terminal-width sentinel
def resolve_truncate_chars(cli_value, configured_value, logging_disabled):
    truncate_chars = configured_value if cli_value is None else cli_value
    if logging_disabled:
        return 0
    if truncate_chars == 999:
        terminal_size = shutil.get_terminal_size()
        print(f"The detected terminal screen width is: {terminal_size.columns} characters\n")
        return terminal_size.columns
    return truncate_chars


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename, strip_ansi=True):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")
        self.strip_ansi = strip_ansi

    def write(self, message):
        terminal_message = truncate_string_per_line(message, TRUNCATE_CHARS) if TRUNCATE_CHARS else message
        self.terminal.write(apply_color_to_text(terminal_message))

        # Expand tabs for file output (stdout remains untouched)
        expanded_message = message.expandtabs(8)

        if self.strip_ansi:
            expanded_message = ANSI_ESCAPE_RE.sub("", expanded_message)
        self.logfile.write(normalize_log_separators(expanded_message))
        self.terminal.flush()
        self.logfile.flush()

    # Writes text the log file should keep but the terminal has already shown, or does not need
    def log_only(self, message):
        expanded_message = message.expandtabs(8)
        if self.strip_ansi:
            expanded_message = ANSI_ESCAPE_RE.sub("", expanded_message)
        self.logfile.write(normalize_log_separators(expanded_message))
        self.logfile.flush()

    # Writes text meant for the reader at the terminal, which the log file has its own version of
    def terminal_only(self, message):
        terminal_message = truncate_string_per_line(message, TRUNCATE_CHARS) if TRUNCATE_CHARS else message
        self.terminal.write(apply_color_to_text(terminal_message))
        self.terminal.flush()

    def flush(self):
        self.terminal.flush()
        self.logfile.flush()


# Simple colour-aware stdout wrapper used when logging is disabled
# Applies the same line-based colouring rules as Logger, but does not write anything to a log file
class ColorStream(object):
    def __init__(self, stream):
        self.terminal = stream

    def write(self, message):
        terminal_message = truncate_string_per_line(message, TRUNCATE_CHARS) if TRUNCATE_CHARS else message
        self.terminal.write(apply_color_to_text(terminal_message))
        self.terminal.flush()

    # Writes one message to the terminal while matching the Logger interface
    def terminal_only(self, message):
        self.write(message)

    # Discards log-only output, since this stream is used exactly when there is no log file
    def log_only(self, message):
        return

    def flush(self):
        self.terminal.flush()


# Signal handler when user presses Ctrl+C
def signal_handler(sig, frame):
    sys.stdout = stdout_bck
    print('\n* You pressed Ctrl+C, tool is terminated.')
    sys.exit(0)


# Reads one answer with Python's default Ctrl+C behavior, so the prompt reports the outcome instead of the signal handler
def read_interactively(reader, *args, **kwargs):
    try:
        previous_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.default_int_handler)
    except (ValueError, OSError):
        # Handlers can only be replaced from the main thread, which is where every prompt runs
        return reader(*args, **kwargs)
    try:
        return reader(*args, **kwargs)
    finally:
        try:
            signal.signal(signal.SIGINT, previous_handler)
        except (ValueError, OSError):
            pass


# Checks internet connectivity against the configured URL and timeout
def check_internet(url=None, timeout=None, quiet=False):
    # Resolved at call time so a config file can change these, which binding them as default arguments prevented
    selected_url = CHECK_INTERNET_URL if url is None else url
    selected_timeout = CHECK_INTERNET_TIMEOUT if timeout is None else timeout
    debug_print("Connectivity check", url=selected_url, timeout=f"{selected_timeout}s", verify_ssl=VERIFY_SSL)
    try:
        _ = req.get(selected_url, timeout=selected_timeout, verify=VERIFY_SSL)
        debug_print("Connectivity check", url=selected_url, outcome="OK")
        return True
    except req.RequestException as e:
        # Quiet callers render the failure themselves, which doctor needs so nothing lands on its progress line
        global LAST_CONNECTIVITY_ERROR
        debug_print("Connectivity check", url=selected_url, outcome="failed", error=f"{type(e).__name__}: {e}")
        if not quiet:
            print_recovery_error(e, context="connectivity")
        LAST_CONNECTIVITY_ERROR = e
        return False


# Resolves a Steam community user URL to a Steam64 ID through the Steam Web API
def resolve_steam_community_url(community_url, api_key, timeout=30):
    try:
        parsed_url = urlparse(community_url)
        hostname = (parsed_url.hostname or "").lower()
    except (AttributeError, ValueError):
        raise ValueError("Invalid Steam community URL") from None

    if parsed_url.scheme not in ("http", "https") or hostname not in ("steamcommunity.com", "www.steamcommunity.com"):
        raise ValueError("Invalid Steam community URL")

    path_parts = [unquote(part) for part in parsed_url.path.split("/") if part]
    if len(path_parts) < 2:
        raise ValueError("Invalid Steam community user URL")

    profile_type = path_parts[0].lower()
    profile_name = path_parts[1]

    if profile_type == "profiles":
        profile_id = steam.steamid.SteamID(profile_name)
        if not profile_id.is_valid() or profile_id.type != steam.steamid.EType.Individual:
            raise ValueError("Invalid Steam user profile ID")
        return int(profile_id.as_64)

    if profile_type == "user":
        profile_id = steam.steamid.from_invite_code(profile_name)
        if not profile_id or not profile_id.is_valid():
            raise ValueError("Invalid Steam user invite URL")
        return int(profile_id.as_64)

    if profile_type != "id":
        raise ValueError("Only Steam user profile URLs are supported")

    resolver_url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"
    try:
        response = req.get(resolver_url, params={"key": api_key, "vanityurl": profile_name, "url_type": 1}, timeout=timeout, verify=VERIFY_SSL)
    except req.Timeout:
        raise ValueError("Steam Web API request timed out") from None
    except req.RequestException:
        raise ValueError("Cannot connect to the Steam Web API") from None

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        retry_message = f" Retry after {retry_after}." if retry_after else ""
        raise ValueError(f"Steam Web API rate limit exceeded.{retry_message}")
    if response.status_code == 403:
        raise ValueError("Steam Web API rejected the API key")
    if response.status_code != 200:
        raise ValueError(f"Steam Web API returned HTTP {response.status_code}")

    try:
        result = response.json().get("response", {})
    except (AttributeError, ValueError):
        raise ValueError("Steam Web API returned an invalid response") from None
    if not isinstance(result, dict):
        raise ValueError("Steam Web API returned an invalid response")

    if str(result.get("success")) != "1":
        message = result.get("message")
        if message:
            raise ValueError(f"Steam community URL could not be resolved: {message}")
        raise ValueError("Steam community URL could not be resolved")

    resolved_id = steam.steamid.SteamID(result.get("steamid", ""))
    if not resolved_id.is_valid() or resolved_id.type != steam.steamid.EType.Individual:
        raise ValueError("Steam Web API returned an invalid Steam64 ID")
    return int(resolved_id.as_64)


# Parses a human duration such as 30s, 2m, 1.5h, 1h 30m, 1d or a bare number of seconds, returning whole seconds
def parse_duration_input(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None
    if not isinstance(value, str):
        return None
    text = value.strip().casefold().replace(",", ".")
    if not text:
        return None
    units = {"s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
             "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
             "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
             "d": 86400, "day": 86400, "days": 86400}
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*([a-z]*)", text)
    # Reject anything the pattern did not fully consume, so "5x" or "abc" cannot read as a bare number
    if not matches or re.sub(r"(\d+(?:\.\d+)?)\s*([a-z]*)", "", text).strip():
        return None
    total = 0.0
    for amount, unit in matches:
        if unit and unit not in units:
            return None
        total += float(amount) * units.get(unit, 1)
    seconds = int(round(total))
    return seconds if seconds > 0 else None


# Splits a Steam target into a resolved Steam64 ID or the vanity name that still needs one API lookup
def normalize_steam_target(value):
    if isinstance(value, bool) or value is None:
        raise ValueError(STEAM_TARGET_INPUT_ERROR)
    text = str(value).strip()
    if not text or any(character.isspace() for character in text):
        raise ValueError(STEAM_TARGET_INPUT_ERROR)

    # A bare Steam64 ID, the form the tool stores and the one everything else normalizes to
    if text.isdigit():
        candidate = steam.steamid.SteamID(text)
        if candidate.is_valid() and candidate.type == steam.steamid.EType.Individual:
            return int(candidate.as_64), None
        raise ValueError(STEAM_TARGET_INPUT_ERROR)

    # A Steam3 identifier such as [U:1:22202] pasted straight out of a console or a profile page
    if text.startswith("[") and text.endswith("]"):
        candidate = steam.steamid.SteamID(text)
        if candidate.is_valid() and candidate.type == steam.steamid.EType.Individual:
            return int(candidate.as_64), None
        raise ValueError(STEAM_TARGET_INPUT_ERROR)

    lowered = text.casefold()
    if lowered.startswith("steamcommunity.com/") or lowered.startswith("www.steamcommunity.com/"):
        text = "https://" + text
        lowered = text.casefold()

    if lowered.startswith("http://") or lowered.startswith("https://"):
        try:
            parsed = urlparse(text)
        except ValueError:
            raise ValueError(STEAM_TARGET_INPUT_ERROR) from None
        if (parsed.hostname or "").casefold() not in ("steamcommunity.com", "www.steamcommunity.com"):
            raise ValueError(STEAM_TARGET_INPUT_ERROR)
        parts = [unquote(part) for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise ValueError(STEAM_TARGET_INPUT_ERROR)
        kind, name = parts[0].casefold(), parts[1]
        if kind == "profiles":
            candidate = steam.steamid.SteamID(name)
            if candidate.is_valid() and candidate.type == steam.steamid.EType.Individual:
                return int(candidate.as_64), None
            raise ValueError(STEAM_TARGET_INPUT_ERROR)
        if kind == "user":
            candidate = steam.steamid.from_invite_code(name)
            if candidate and candidate.is_valid():
                return int(candidate.as_64), None
            raise ValueError(STEAM_TARGET_INPUT_ERROR)
        if kind == "id":
            # A vanity name cannot be resolved locally, so it is handed back for the one API lookup it needs
            return None, name
        raise ValueError(STEAM_TARGET_INPUT_ERROR)

    # A bare vanity name, which is what people copy out of the address bar
    if re.fullmatch(r"[A-Za-z0-9_-]{2,64}", text):
        return None, text
    raise ValueError(STEAM_TARGET_INPUT_ERROR)


# Resolves any accepted Steam target form to one canonical Steam64 ID
def resolve_steam_target(value, api_key):
    steam64, vanity = normalize_steam_target(value)
    if steam64 is not None:
        return steam64
    original = str(value).strip()
    if original.casefold().startswith(("steamcommunity.com/", "www.steamcommunity.com/")):
        original = "https://" + original
    community_url = original if original.casefold().startswith(("http://", "https://")) else f"https://steamcommunity.com/id/{vanity}/"
    return resolve_steam_community_url(community_url, api_key)


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


# Commands that print a one-shot result and exit, so the screen keeps whatever is already on it
KEEP_HISTORY_FLAGS = (*SECRET_ACTION_FLAGS, "--doctor", "--send-test-email", "--send-test-webhook", "--help", "-h")


# Returns True when the running command is a one-shot whose output has to stay scrollable
def keep_terminal_history():
    return any(flag in sys.argv for flag in KEEP_HISTORY_FLAGS)


# Prints the ASCII startup banner with a separately aligned version
def print_startup_banner():
    print("\n".join(colorize("header", line) if line else line for line in STARTUP_BANNER.splitlines()))
    print(colorize("info", f"{'':21}v{VERSION}") + "\n")


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


# Opens one authenticated SMTP session and leaves closing it to the caller
def smtp_connect_and_login(use_ssl, smtp_timeout=15):
    smtp_object = smtplib.SMTP(SMTP_HOST, int(SMTP_PORT), timeout=smtp_timeout)
    try:
        if use_ssl:
            smtp_object.starttls(context=smtp_ssl_context())
        smtp_object.login(SMTP_USER, SMTP_PASSWORD)
        return smtp_object
    except Exception:
        try:
            smtp_object.quit()
        except Exception:
            pass
        raise


# Sends one email notification, validating the settings before it connects
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

    debug_print("SMTP delivery", host=SMTP_HOST, port=SMTP_PORT, user=SMTP_USER, starttls=bool(use_ssl), timeout=f"{smtp_timeout}s")
    try:
        smtpObj = smtp_connect_and_login(use_ssl, smtp_timeout=smtp_timeout)
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
        print(f"Error sending email: {sanitize_error_text(e)}")
        debug_swallowed_exception("Sending email", e)
        return 1
    debug_print("SMTP delivery", host=SMTP_HOST, port=SMTP_PORT, recipient=RECEIVER_EMAIL, outcome="OK")
    verbose_print(f"Email delivered to {RECEIVER_EMAIL}")
    return 0


# Raised when a private setting cannot be checked or saved safely
class SecretConfigurationError(Exception):
    pass


# Quotes one secret value for lossless parsing by python-dotenv
def _format_dotenv_value(value):
    if not isinstance(value, str):
        raise TypeError("Dotenv secret values must be strings")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
    return f'"{escaped}"'


# Resolves a private dotenv destination without searching parent directories
def resolve_secret_env_path(env_file=None, cwd=None):
    if env_file is not None and str(env_file).casefold() == "none":
        raise SecretConfigurationError("Private secret entry requires a dotenv destination. Replace '--env-file none' with a writable path.")
    base_directory = Path.cwd() if cwd is None else Path(cwd)
    destination = base_directory / ".env" if env_file is None else Path(env_file).expanduser()
    return destination.resolve()


# Returns the keys a dotenv file itself defines, used to tell a file-supplied secret from an exported one
def dotenv_file_keys(env_path=None):
    if not env_path or not os.path.isfile(str(env_path)):
        return frozenset()
    try:
        from dotenv import dotenv_values
    except ImportError:
        return frozenset()
    try:
        return frozenset(name for name, value in dotenv_values(str(env_path)).items() if value is not None)
    except Exception:
        return frozenset()


# Returns where each effective environment secret came from while preserving exported-value precedence
def secret_sources(env_path=None, exported_keys=None):
    file_keys = dotenv_file_keys(env_path)
    protected_keys = EXPORTED_SECRET_KEYS if exported_keys is None else frozenset(exported_keys)
    sources = {}
    for secret in SECRET_KEYS:
        if os.getenv(secret) is None:
            continue
        sources[secret] = "environment" if secret in protected_keys or secret not in file_keys else str(env_path)
    return sources


# Reloads dotenv secrets without replacing values exported when the process started
def reload_dotenv_secrets(env_path, exported_keys=None):
    from dotenv import dotenv_values
    protected_keys = EXPORTED_SECRET_KEYS if exported_keys is None else frozenset(exported_keys)
    values = dotenv_values(str(env_path))
    for secret in SECRET_KEYS:
        value = values.get(secret)
        if secret not in protected_keys and value is not None:
            os.environ[secret] = value


# Copies exported secrets into module globals and returns the applied names paired with whether the value changed
def load_secrets_from_environment(namespace=None):
    selected_namespace = globals() if namespace is None else namespace
    applied = []
    for secret in SECRET_KEYS:
        value = os.getenv(secret)
        if value is None:
            continue
        applied.append((secret, selected_namespace.get(secret) != value))
        selected_namespace[secret] = value
    return applied


# Checks whether a dotenv file already contains one named assignment
def _dotenv_contains_key(destination, key):
    destination_path = Path(destination)
    if not destination_path.exists():
        return False
    try:
        lines = destination_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        raise SecretConfigurationError(f"Could not read dotenv destination '{destination_path}'. Check that it is a readable UTF-8 file.")
    assignment_pattern = re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}\s*=")
    return any(assignment_pattern.match(line) for line in lines)


# Updates supported secrets in a dotenv file through an atomic replacement
def update_dotenv_file(destination, updates):
    if not hasattr(updates, "items"):
        raise TypeError("Dotenv updates must be a mapping")
    update_items = list(updates.items())
    for key, value in update_items:
        if not isinstance(key, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or key not in SECRET_KEYS:
            raise ValueError(f"Unsupported dotenv key: {key!r}")
        if not isinstance(value, str):
            raise TypeError(f"Dotenv value for {key} must be a string")

    destination_path = Path(destination).expanduser()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    existing_lines = destination_path.read_text(encoding="utf-8").splitlines() if destination_path.exists() else []
    update_keys = {key for key, _ in update_items}
    values_by_key = dict(update_items)
    seen_keys = set()
    output_lines = []
    assignment_pattern = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
    for line in existing_lines:
        match = assignment_pattern.match(line)
        key = match.group(1) if match else None
        if key not in update_keys:
            output_lines.append(line)
            continue
        if key in seen_keys:
            continue
        output_lines.append(f"{key}={_format_dotenv_value(values_by_key[key])}")
        seen_keys.add(key)
    for key, value in update_items:
        if key not in seen_keys:
            output_lines.append(f"{key}={_format_dotenv_value(value)}")
            seen_keys.add(key)

    content = "\n".join(output_lines)
    if output_lines:
        content += "\n"
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{destination_path.name}.", suffix=".tmp", dir=str(destination_path.parent), delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        if os.name == "posix":
            os.chmod(str(temporary_path), 0o600)
        backup_path = create_timestamped_backup(destination_path)
        os.replace(str(temporary_path), str(destination_path))
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return {"path": str(destination_path), "updated_keys": tuple(key for key, _ in update_items), "backup_path": backup_path}


# Validates a Steam Web API key without exposing it in output
def validate_steam_api_key(api_key, timeout=10):
    if not isinstance(api_key, str) or not re.fullmatch(r"[A-Fa-f0-9]{32}", api_key.strip()):
        return False
    try:
        response = req.get("https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/", params={"key": api_key.strip(), "steamids": "76561197960287930"}, timeout=timeout, verify=VERIFY_SSL)
        if response.status_code != 200:
            return False
        payload = response.json()
        return isinstance(payload, dict) and isinstance(payload.get("response"), dict) and isinstance(payload["response"].get("players"), list)
    except (ValueError, req.RequestException):
        return False


# Privately validates and atomically stores one Steam Web API key
@suppresses_debug_output
def run_set_steam_api_key(env_file=None, interactive=None, input_func=None, getpass_func=None, validator=None):
    destination = resolve_secret_env_path(env_file)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise SecretConfigurationError("--set-steam-api-key requires an interactive terminal. Run it in a terminal window so the API key stays hidden while you paste it.")
    prompt = input if input_func is None else input_func
    if _dotenv_contains_key(destination, "STEAM_API_KEY"):
        try:
            confirmed = read_interactively(prompt, f"Replace the saved Steam Web API key in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print()
            raise RecoveryError(secret_entry_cancelled_advice("Steam Web API key", "--set-steam-api-key", STEAM_API_KEY_GUIDE_URL)) from None
        if not confirmed:
            raise RecoveryError(secret_replacement_declined_advice("Steam Web API key", "--set-steam-api-key", STEAM_API_KEY_GUIDE_URL))
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        api_key = read_interactively(hidden_prompt, "Paste the Steam Web API key (input hidden): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise RecoveryError(secret_entry_cancelled_advice("Steam Web API key", "--set-steam-api-key", STEAM_API_KEY_GUIDE_URL)) from None
    validate = validate_steam_api_key if validator is None else validator
    if not validate(api_key):
        raise SecretConfigurationError("The entered Steam Web API key is invalid or could not be verified. The private settings file was not changed.")
    try:
        result = update_dotenv_file(destination, {"STEAM_API_KEY": api_key})
    except Exception:
        raise SecretConfigurationError(f"Could not save the Steam Web API key in '{destination}'. Check file permissions or choose another path with --env-file.")
    print("* Steam Web API key is valid")
    print(f"* Updated private settings file: {destination}")
    if result.get("backup_path"):
        print(f"* Previous private settings file backed up to: {result['backup_path']}")
    print()
    _wizard_print_command("Check setup again:", render_command(["--doctor", "<steam_target>"], include_paths=False, env_path=destination))
    _wizard_print_command("After Doctor passes, start monitoring:", render_command(["<steam_target>"], include_paths=False, env_path=destination))
    return str(destination)


# Returns whether a webhook URL is a complete private HTTPS link
def validate_webhook_url(url=None):
    selected_url = WEBHOOK_URL if url is None else url
    if not isinstance(selected_url, str) or not selected_url.strip():
        return False
    try:
        parsed = urlsplit(selected_url.strip())
    except ValueError:
        return False
    return parsed.scheme.casefold() == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password and bool(parsed.path.strip("/"))


# Accepts a complete HTTPS ntfy URL or a bare ntfy.sh topic name and returns the full URL
def normalize_ntfy_topic_url(value):
    if not isinstance(value, str):
        return ""
    normalized = value.strip()
    if validate_webhook_url(normalized):
        return normalized
    if re.fullmatch(r"[-_A-Za-z0-9]{1,64}", normalized):
        return f"https://ntfy.sh/{normalized}"
    return ""


# Detects Discord and public ntfy webhook providers from distinctive URL shapes
def detect_webhook_provider(url):
    if not validate_webhook_url(url):
        return ""
    try:
        parsed = urlsplit(str(url).strip())
    except ValueError:
        return ""
    hostname = parsed.hostname.casefold() if parsed.hostname else ""
    if hostname == "ntfy.sh":
        return "ntfy"
    discord_host = hostname in ("discord.com", "discordapp.com") or hostname.endswith(".discord.com") or hostname.endswith(".discordapp.com")
    discord_path = re.match(r"^/api(?:/v[0-9]+)?/webhooks/[0-9]+/[^/]+/?$", parsed.path) is not None
    return "discord" if discord_host and discord_path else ""


# Privately validates and atomically stores one webhook URL
@suppresses_debug_output
def run_set_webhook_url(env_file=None, interactive=None, input_func=None, getpass_func=None):
    destination = resolve_secret_env_path(env_file)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise SecretConfigurationError("--set-webhook-url requires an interactive terminal. Run it in a terminal window so the webhook URL stays hidden while you paste it.")
    prompt = input if input_func is None else input_func
    if _dotenv_contains_key(destination, "WEBHOOK_URL"):
        try:
            confirmed = read_interactively(prompt, f"Replace the saved webhook URL in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print()
            raise RecoveryError(secret_entry_cancelled_advice("webhook URL", "--set-webhook-url", WEBHOOK_GUIDE_URL)) from None
        if not confirmed:
            raise RecoveryError(secret_replacement_declined_advice("webhook URL", "--set-webhook-url", WEBHOOK_GUIDE_URL))
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        webhook_url = read_interactively(hidden_prompt, "Paste the Discord or ntfy webhook URL (input hidden): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise RecoveryError(secret_entry_cancelled_advice("webhook URL", "--set-webhook-url", WEBHOOK_GUIDE_URL)) from None
    if not validate_webhook_url(webhook_url):
        raise SecretConfigurationError("That does not look like a complete HTTPS webhook URL. The private settings file was not changed.")
    try:
        result = update_dotenv_file(destination, {"WEBHOOK_URL": webhook_url})
    except Exception:
        raise SecretConfigurationError(f"Could not save the webhook URL in '{destination}'. Check file permissions or choose another path with --env-file.")
    print("* Webhook URL looks valid")
    print(f"* Updated private settings file: {destination}")
    if result.get("backup_path"):
        print(f"* Previous private settings file backed up to: {result['backup_path']}")
    print()
    _wizard_print_command("Send a test webhook:", render_command(["--send-test-webhook"], include_paths=False, env_path=destination))
    _wizard_print_command("Check setup again:", render_command(["--doctor", "<steam_target>"], include_paths=False, env_path=destination))
    return str(destination)


# Signs in to the configured mail server with one entered password, so nothing is saved that cannot deliver
def smtp_sign_in(password, timeout=15):
    global SMTP_PASSWORD

    candidate = str(password or "")
    if not candidate or candidate == "your_smtp_password":
        raise SecretConfigurationError("No SMTP password was entered. The private settings file was not changed.")
    if not all(doctor_value_is_set(value) for value in (SMTP_HOST, SMTP_USER, SENDER_EMAIL, RECEIVER_EMAIL)):
        raise SecretConfigurationError("The mail server settings are incomplete. Set SMTP_HOST, SMTP_USER, SENDER_EMAIL and RECEIVER_EMAIL first, or run --setup.")
    previous_password = SMTP_PASSWORD
    SMTP_PASSWORD = candidate
    smtp_object = None
    try:
        smtp_object = smtp_connect_and_login(SMTP_SSL, smtp_timeout=timeout)
    finally:
        if smtp_object is not None:
            try:
                smtp_object.quit()
            except Exception:
                pass
        SMTP_PASSWORD = previous_password
    return str(SMTP_USER)


# Privately checks one SMTP password against the mail server and atomically stores it
@suppresses_debug_output
def run_set_smtp_password(env_file=None, interactive=None, input_func=None, getpass_func=None, sign_in=None):
    destination = resolve_secret_env_path(env_file)
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        raise SecretConfigurationError("--set-smtp-password requires an interactive terminal. Run it in a terminal window so the password stays hidden while you type it.")
    prompt = input if input_func is None else input_func
    if _dotenv_contains_key(destination, "SMTP_PASSWORD"):
        try:
            confirmed = read_interactively(prompt, f"Replace the saved SMTP password in '{destination}'? [y/N]: ").strip().casefold() in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print()
            raise RecoveryError(secret_entry_cancelled_advice("SMTP password", "--set-smtp-password", SMTP_GUIDE_URL)) from None
        if not confirmed:
            raise RecoveryError(secret_replacement_declined_advice("SMTP password", "--set-smtp-password", SMTP_GUIDE_URL))
    print(f"* The password is checked by signing in to {SMTP_HOST} as {SMTP_USER}. Nothing is sent")
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        smtp_password = str(read_interactively(hidden_prompt, "Enter the SMTP password (input hidden): ")).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise RecoveryError(secret_entry_cancelled_advice("SMTP password", "--set-smtp-password", SMTP_GUIDE_URL)) from None
    check = smtp_sign_in if sign_in is None else sign_in
    try:
        signed_in_user = check(smtp_password, timeout=5)
    except SecretConfigurationError:
        raise
    except Exception as exc:
        raise SecretConfigurationError(f"The mail server did not accept the password: {type(exc).__name__}: {sanitize_error_text(exc)}. The private settings file was not changed.") from None
    try:
        result = update_dotenv_file(destination, {"SMTP_PASSWORD": smtp_password})
    except Exception:
        raise SecretConfigurationError(f"Could not save the SMTP password in '{destination}'. Check file permissions or choose another path with --env-file.")
    print(f"* The mail server accepted the password for {signed_in_user}")
    print(f"* Updated private settings file: {destination}")
    if result.get("backup_path"):
        print(f"* Previous private settings file backed up to: {result['backup_path']}")
    print()
    _wizard_print_command("Send a test email:", render_command(["--send-test-email"], include_paths=False, env_path=destination))
    _wizard_print_command("Check setup again:", render_command(["--doctor", "<steam_target>"], include_paths=False, env_path=destination))
    return str(destination)


# Returns the normalized configured webhook provider or an empty string when unsupported
def normalized_webhook_provider(provider=None):
    selected_provider = WEBHOOK_PROVIDER if provider is None else provider
    if not isinstance(selected_provider, str):
        return ""
    normalized = selected_provider.strip().casefold()
    return normalized if normalized in ("discord", "ntfy") else ""


# Returns enabled email notification category names in display order
def _startup_email_notification_categories():
    settings = (
        (ACTIVE_INACTIVE_NOTIFICATION, "online/offline"),
        (STATUS_NOTIFICATION, "status"),
        (GAME_CHANGE_NOTIFICATION, "game"),
        (STEAM_LEVEL_XP_NOTIFICATION, "level/XP"),
        (FRIENDS_NOTIFICATION, "friends"),
        (GAMES_LIBRARY_NOTIFICATION, "games"),
        (NAME_CHANGE_NOTIFICATION, "name"),
        (ERROR_NOTIFICATION, "errors"),
    )
    return [label for enabled, label in settings if enabled]


# Returns enabled webhook notification category names in display order
def _startup_webhook_notification_categories():
    settings = (
        (WEBHOOK_ACTIVE_NOTIFICATION, "active"),
        (WEBHOOK_INACTIVE_NOTIFICATION, "inactive"),
        (WEBHOOK_STATUS_NOTIFICATION, "status"),
        (WEBHOOK_GAME_CHANGE_NOTIFICATION, "game"),
        (WEBHOOK_LEVEL_XP_NOTIFICATION, "level/XP"),
        (WEBHOOK_FRIENDS_NOTIFICATION, "friends"),
        (WEBHOOK_GAMES_NOTIFICATION, "games"),
        (WEBHOOK_NAME_CHANGE_NOTIFICATION, "name"),
        (WEBHOOK_ERROR_NOTIFICATION, "errors"),
    )
    return [label for label in _selected_webhook_notification_categories(settings) if WEBHOOK_ENABLED]


# Returns the webhook alert types selected in the configuration, ignoring the master switch
def _selected_webhook_notification_categories(settings=None):
    if settings is None:
        settings = (
            (WEBHOOK_ACTIVE_NOTIFICATION, "active"),
            (WEBHOOK_INACTIVE_NOTIFICATION, "inactive"),
            (WEBHOOK_STATUS_NOTIFICATION, "status"),
            (WEBHOOK_GAME_CHANGE_NOTIFICATION, "game"),
            (WEBHOOK_LEVEL_XP_NOTIFICATION, "level/XP"),
            (WEBHOOK_FRIENDS_NOTIFICATION, "friends"),
            (WEBHOOK_GAMES_NOTIFICATION, "games"),
            (WEBHOOK_NAME_CHANGE_NOTIFICATION, "name"),
            (WEBHOOK_ERROR_NOTIFICATION, "errors"),
        )
    return [label for enabled, label in settings if enabled]


# Formats one notification row with unstarred continuation lines when needed
def _format_startup_notification_line(label, categories):
    prefix = f"* {label:<30}"
    state = "On (" + ", ".join(categories) + ")" if categories else "Off"
    return textwrap.fill(state, width=100, initial_indent=prefix, subsequent_indent=" " * len(prefix), break_long_words=False, break_on_hyphens=False)


# Returns one channel's rollup value, naming the enabled categories rather than only whether the channel is on
def _startup_notification_state(categories):
    return "On (" + ", ".join(categories) + ")" if categories else "Off"


# Builds compact startup notification lines for both delivery channels
def _startup_notification_summary_lines():
    enabled_email = _startup_email_notification_categories()
    enabled_webhook = _startup_webhook_notification_categories()
    return [_format_startup_notification_line("Notifications (email):", enabled_email), _format_startup_notification_line("Notifications (webhook):", enabled_webhook)]


# Redacts configured secrets and API key query values from one error-shaped value
def sanitize_error_text(value):
    text = str(value)
    for secret_name in SECRET_KEYS:
        secret_value = globals().get(secret_name)
        if isinstance(secret_value, str) and secret_value and not secret_value.startswith("your_"):
            text = text.replace(secret_value, "<redacted>")
    text = re.sub(r"(?i)([?&]key=)[^&\s]+", r"\1<redacted>", text)
    text = re.sub(r"(?im)(\b(?:STEAM_API_KEY|SMTP_PASSWORD|WEBHOOK_URL|NTFY_ACCESS_TOKEN)\b\s*=\s*)[^\r\n]*", r"\1<redacted>", text)
    return text


# Every recovery category the tool can report, kept closed so a message is testable, deduplicable and translatable later
RECOVERY_CODES = frozenset({
    "config.missing", "config.invalid", "config.insecure",
    "dependency.missing",
    "secret.missing", "secret.entry",
    "auth.api_key_invalid", "auth.rejected",
    "network.unavailable", "network.timeout",
    "steam.rate_limited", "steam.unavailable",
    "target.missing", "target.invalid", "target.not_found", "target.not_visible",
    "smtp.invalid", "smtp.authentication", "smtp.connection",
    "webhook.invalid", "webhook.rejected", "webhook.rate_limited", "webhook.connection",
    "file.unreadable", "file.unwritable",
    "unknown",
})

# A namedtuple rather than a dataclass, because the declared minimum Python for this tool predates dataclasses
RecoveryAdvice = namedtuple("RecoveryAdvice", ["code", "summary", "fix", "retryable", "detail"])
RecoveryAdvice.__new__.__defaults__ = ("",)


# Carries structured recovery advice across an exception boundary without exposing technical detail
class RecoveryError(Exception):
    # Initializes a structured recovery exception, keeping the original cause attached for debug output
    def __init__(self, advice, cause=None):
        self.advice = advice
        self.cause = cause
        if cause is not None:
            self.__cause__ = cause
        super().__init__(advice.summary)


# Builds one piece of recovery advice, refusing any code outside the closed set and sanitizing every field
def make_recovery_advice(code, summary, fix, retryable, detail=""):
    if code not in RECOVERY_CODES:
        raise ValueError(f"Unsupported recovery code: {code}")
    return RecoveryAdvice(code, sanitize_error_text(summary), sanitize_error_text(fix), bool(retryable), sanitize_error_text(detail) if detail else "")


# Adds a directly relevant documentation link on its own line
def recovery_fix_with_guide(fix, guide_url):
    return f"{fix}\nGuide: {guide_url}"


# Returns the advice a cancelled secret entry reports, worded the same way by every one-shot secret command
def secret_entry_cancelled_advice(subject, flag, guide_url):
    return make_recovery_advice("secret.entry", f"{subject[:1].upper()}{subject[1:]} setup was cancelled and the dotenv file was not changed", recovery_fix_with_guide(f"Run {flag} again when you have the value ready", guide_url), False)


# Returns the advice a declined secret replacement reports, worded the same way by every one-shot secret command
def secret_replacement_declined_advice(subject, flag, guide_url, plural=False):
    kept = "were left as they are" if plural else "was left as it is"
    return make_recovery_advice("secret.entry", f"The saved {subject} {kept} and the dotenv file was not changed", recovery_fix_with_guide(f"Run {flag} again and answer y to replace the saved value", guide_url), False)


# Returns the HTTP status carried by an error, when it has one
def recovery_http_status(error):
    response = getattr(error, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


# Maps one exception plus its HTTP status and calling context to stable recovery advice
def classify_recovery_error(error=None, context="runtime", detail=""):
    if isinstance(error, RecoveryError):
        return error.advice
    message = str(detail or error or "").lower()
    safe_detail = sanitize_error_text(detail or error) if (detail or error) else ""
    status = recovery_http_status(error)

    def advice(code, summary, fix, retryable, guide_url=None):
        return make_recovery_advice(code, summary, recovery_fix_with_guide(fix, guide_url) if guide_url else fix, retryable, safe_detail)

    if context == "config":
        if "does not exist" in message:
            return advice("config.missing", safe_detail or "The configuration file was not found", f"Create one with '{render_command(['--generate-config', 'steam_monitor.conf'], include_paths=False)}' or correct the --config-file path", False, CONFIG_FILE_GUIDE_URL)
        return advice("config.invalid", safe_detail or "The configuration file could not be read", f"Correct the reported line, or start from a fresh template with '{render_command(['--generate-config', 'steam_monitor.conf'], include_paths=False)}'", False, CONFIG_FILE_GUIDE_URL)

    if context in ("set_steam_api_key", "set_smtp_password", "set_webhook_url"):
        flag = {"set_steam_api_key": "--set-steam-api-key", "set_smtp_password": "--set-smtp-password"}.get(context, "--set-webhook-url")
        guide = {"set_steam_api_key": STEAM_API_KEY_GUIDE_URL, "set_smtp_password": SMTP_GUIDE_URL}.get(context, WEBHOOK_GUIDE_URL)
        if "interactive terminal" in message:
            return advice("unknown", f"{flag} requires an interactive terminal", f"Run {flag} in a terminal window so the value stays hidden while you paste it", False, guide)
        if "cancelled" in message:
            return advice("unknown", safe_detail or "Setup was cancelled", f"Run {flag} again when you have the value ready", False, guide)
        if any(term in message for term in ("could not save", "file permissions", "writable path", "dotenv destination")):
            return advice("file.unwritable", safe_detail or "The private settings file could not be updated", "Check file permissions or choose another path with --env-file PATH", False, SECRETS_GUIDE_URL)
        if context == "set_steam_api_key":
            return advice("auth.api_key_invalid", safe_detail or "Steam rejected the entered Web API key", f"Copy a fresh key from {STEAM_API_KEY_REGISTRATION_URL} then run {flag} again", False, guide)
        if context == "set_smtp_password":
            if "settings are incomplete" in message:
                return advice("smtp.invalid", safe_detail or "The mail server settings are incomplete", f"Set SMTP_HOST, SMTP_USER, SENDER_EMAIL and RECEIVER_EMAIL, or run {render_command(['--setup'])}", False, guide)
            return advice("smtp.authentication", safe_detail or "The mail server did not accept the password", f"Use an app password when the provider requires one then run {flag} again", False, guide)
        return advice("webhook.invalid", safe_detail or "The webhook URL was not changed", f"Copy a complete Discord or ntfy webhook URL then run {flag} again", False, guide)

    if context == "target.missing":
        return advice("target.missing", safe_detail or "No Steam profile is configured", f"Pass the profile to watch as a {STEAM_TARGET_FORMS}: {render_command(['<steam_target>'])}", False, QUICK_START_GUIDE_URL)

    if context == "target":
        if any(term in message for term in ("rate limit", "429")) or status == 429:
            return advice("steam.rate_limited", "Steam rate limited the profile lookup", "Wait for the reported period then try again", True)
        if any(term in message for term in ("timed out", "timeout")):
            return advice("network.timeout", "The Steam Web API request timed out", "Check connectivity then try again", True)
        if "cannot connect" in message:
            return advice("network.unavailable", "The Steam Web API could not be reached", "Check connectivity, DNS and any proxy then try again", True)
        if any(term in message for term in ("invalid steam", "only steam user", "not supported")):
            return advice("target.invalid", safe_detail or "That is not a recognized Steam profile", f"Pass a {STEAM_TARGET_FORMS}", False, USAGE_GUIDE_URL)
        return advice("target.not_found", safe_detail or "No Steam user matches that profile", "Check the Steam64 ID or profile URL and try again", False, USAGE_GUIDE_URL)

    if context == "connectivity":
        # Classified from the error, because the detail names the endpoint rather than the failure
        cause = str(error or "").lower()
        if "timed out" in cause or "timeout" in cause:
            return advice("network.timeout", "The connectivity endpoint did not answer in time", "Check network, DNS, proxy and CHECK_INTERNET_URL settings", True)
        return advice("network.unavailable", "The connectivity endpoint could not be reached", "Check network, DNS, proxy and CHECK_INTERNET_URL settings", True)

    if context == "email":
        if any(term in message for term in ("authentication", "auth", "username and password", "535")):
            return advice("smtp.authentication", "The SMTP server rejected the sign-in", "Check SMTP_USER and SMTP_PASSWORD, and use an app password if the provider requires one", False, SMTP_GUIDE_URL)
        if any(term in message for term in ("settings are incorrect", "invalid")):
            return advice("smtp.invalid", safe_detail or "The SMTP settings are incomplete or invalid", "Check SMTP_HOST, SMTP_PORT, SENDER_EMAIL and RECEIVER_EMAIL in the configuration file", False, SMTP_GUIDE_URL)
        return advice("smtp.connection", "The SMTP server could not be reached", "Check SMTP_HOST, SMTP_PORT and SMTP_SSL, then confirm the host is reachable from this machine", True, SMTP_GUIDE_URL)

    if context == "webhook":
        if status == 429 or "rate limit" in message:
            return advice("webhook.rate_limited", "The webhook service is rate limiting deliveries", "Reduce how many alert types are enabled, or wait for the service to accept deliveries again", True, WEBHOOK_GUIDE_URL)
        if any(term in message for term in ("must contain", "must be discord", "could not be formatted", "header", "priority", "tags")):
            return advice("webhook.invalid", safe_detail or "The webhook configuration is not usable", f"Check WEBHOOK_URL, WEBHOOK_PROVIDER and the alert settings, then verify with '{render_command(['--send-test-webhook'])}'", False, WEBHOOK_GUIDE_URL)
        if any(term in message for term in ("could not be reached", "connection", "timed out")):
            return advice("webhook.connection", "The webhook service could not be reached", "Check connectivity and the webhook host, then try again", True, WEBHOOK_GUIDE_URL)
        return advice("webhook.rejected", safe_detail or "The webhook service refused the delivery", f"Confirm the webhook still exists and the URL is current, then verify with '{render_command(['--send-test-webhook'])}'", status is not None and status >= 500, WEBHOOK_GUIDE_URL)

    if context == "file":
        if any(term in message for term in ("cannot load", "unreadable", "not valid utf-8", "no such file")):
            return advice("file.unreadable", safe_detail or "A file the tool keeps could not be read", "Check the path and its permissions, or delete the file so it is recreated", False)
        return advice("file.unwritable", safe_detail or "A file the tool keeps could not be written", "Check that the directory exists and is writable, or choose another path", False)

    # Runtime, which is the monitoring loop and every Steam Web API call it makes
    if status == 429 or "rate limit" in message or "too many requests" in message:
        return advice("steam.rate_limited", "Steam is rate limiting requests", "The tool will wait and retry. Increase the polling intervals if this repeats", True)
    if status in (401, 403) or "forbidden" in message or "unauthorized" in message:
        return advice("auth.api_key_invalid", "Steam rejected the configured Web API key", f"Validate and replace it with '{render_command(['--set-steam-api-key'])}'", False, STEAM_API_KEY_GUIDE_URL)
    if status == 404 or "not found" in message:
        return advice("target.not_found", "Steam has no profile for the monitored Steam64 ID", "Check the Steam64 ID, since a deleted or renamed account cannot be monitored", False, USAGE_GUIDE_URL)
    if status is not None and status >= 500 or "service unavailable" in message or "bad gateway" in message:
        return advice("steam.unavailable", "The Steam Web API is temporarily unavailable", "This is usually a Steam outage. The tool will keep retrying", True)
    if "timed out" in message or "timeout" in message:
        return advice("network.timeout", "The Steam Web API request timed out", "Check connectivity. The tool will keep retrying", True)
    if any(term in message for term in ("connection", "name resolution", "network is unreachable", "no connectivity")):
        return advice("network.unavailable", "Steam could not be reached", "Check connectivity, DNS and any proxy. The tool will keep retrying", True)
    if "private" in message or "visibility" in message:
        return advice("target.not_visible", "The monitored profile is not publicly visible", "Ask the user to set game details and profile visibility to Public", False, PRIVACY_GUIDE_URL)
    return advice("unknown", safe_detail or "The request could not be completed", "Re-run with --debug to see the technical cause", True)


# Renders one structured failure as the shared Error, To fix and optional Technical detail block
def render_recovery_error(error=None, context="runtime", debug=None, detail=""):
    advice = classify_recovery_error(error, context, detail)
    lines = [f"* Error: {advice.summary}", f"To fix: {advice.fix}"]
    show_debug = DEBUG_MODE if debug is None else debug
    if show_debug and advice.detail:
        lines.append(f"Technical detail: {sanitize_error_text(advice.detail)}")
    return "\n".join(lines)


# Prints one structured recovery error and returns its stable advice
def print_recovery_error(error=None, context="runtime", debug=None, detail=""):
    advice = classify_recovery_error(error, context, detail)
    print(render_recovery_error(RecoveryError(advice), debug=debug))
    return advice


# Tracks the last uninterrupted recovery category so a long outage cannot repeat the same hint every cycle
class RecoveryHintTracker:
    # Starts with no category, so the first failure of any kind always renders its hint
    def __init__(self):
        self.last_code = None

    # Returns True for the first category and again only when the failure category changes
    def should_render(self, advice):
        if advice.code == self.last_code:
            return False
        self.last_code = advice.code
        return True

    # Clears suppression after a successful cycle, so a recurrence is reported again
    def reset(self):
        self.last_code = None


# Tracks which features are currently unavailable, so a lasting outage is reported once instead of every cycle
class FeatureOutageTracker:
    # Starts with every feature available, so the first outage of any of them is reported
    def __init__(self):
        self.unavailable = {}

    # Takes the features unavailable right now, each with its outage and recovery wording, and returns what changed
    def transitions(self, current):
        recovered = [messages[1] for key, messages in self.unavailable.items() if key not in current]
        started = [messages[0] for key, messages in current.items() if key not in self.unavailable]
        self.unavailable = dict(current)
        return recovered + started


# Prints one monitoring failure, repeating the fix only when the failure category changes
def print_monitor_recovery(error, context, tracker, prefix):
    advice = classify_recovery_error(error, context)
    print(prefix + advice.summary)
    if tracker.should_render(advice):
        print(f"To fix: {advice.fix}")
        if DEBUG_MODE and advice.detail:
            print(f"Technical detail: {sanitize_error_text(advice.detail)}")
    return advice


# Returns the spelling each webhook service uses for itself, since the stored value is casefolded for comparisons
def webhook_provider_display_name(provider=None):
    normalized = normalized_webhook_provider(provider)
    return {"discord": "Discord", "ntfy": "ntfy"}.get(normalized, normalized or "an unset provider")


# The four shared status markers. A fifth neutral marker is the single biggest source of drift between these
# tools, because every state it would cover is a state the others already call PASS
DOCTOR_STATUSES = ("PASS", "WARN", "FAIL", "SKIP")


# One doctor result, held until the whole report is rendered
DoctorCheck = namedtuple("DoctorCheck", ["section", "status", "label", "detail", "advice"])
DoctorCheck.__new__.__defaults__ = ("", None)


# Collects doctor checks plus the work later checks reuse, so nothing is fetched or authenticated twice
class DoctorReport:
    # Starts an empty report with no shared Steam state and no channel marked ready for a delivery test
    def __init__(self):
        self.checks = []
        self.steam_client: Any = None
        self.player_summary = None
        self.steam_id = None
        # Structural flags, so offering a delivery test never depends on matching a rendered label
        self.email_ready = False
        self.webhook_ready = False


# Builds one doctor check, keeping construction in one place so the shape cannot drift between sections
def make_doctor_check(section, status, label, detail="", advice=None):
    if status not in DOCTOR_STATUSES:
        raise ValueError(f"Unsupported doctor status: {status}")
    # Several advice objects carry the same text as their summary and printing it twice reads as two problems
    return DoctorCheck(section, status, label, "" if str(detail).strip() == str(label).strip() else detail, advice)


# Returns whether a configured value is a real value rather than an unedited placeholder
def doctor_value_is_set(value):
    return isinstance(value, str) and bool(value.strip()) and not value.strip().startswith("your_")


# Returns whether one configured webhook alert is enabled independently of email settings
def webhook_event_enabled(notification_type):
    settings = {
        "active": WEBHOOK_ACTIVE_NOTIFICATION,
        "inactive": WEBHOOK_INACTIVE_NOTIFICATION,
        "status": WEBHOOK_STATUS_NOTIFICATION,
        "game": WEBHOOK_GAME_CHANGE_NOTIFICATION,
        "level_xp": WEBHOOK_LEVEL_XP_NOTIFICATION,
        "friends": WEBHOOK_FRIENDS_NOTIFICATION,
        "games": WEBHOOK_GAMES_NOTIFICATION,
        "name": WEBHOOK_NAME_CHANGE_NOTIFICATION,
        "error": WEBHOOK_ERROR_NOTIFICATION,
    }
    return bool(WEBHOOK_ENABLED and settings.get(notification_type, False))


# Parses one numeric or HTTP-date retry value into seconds
def parse_retry_after_seconds(candidate):
    if candidate is None or candidate == "":
        return None
    try:
        seconds = float(candidate)
        return seconds if math.isfinite(seconds) else None
    except (TypeError, ValueError):
        try:
            retry_at = parsedate_to_datetime(str(candidate))
            seconds = (retry_at - datetime.now(retry_at.tzinfo)).total_seconds()
            return seconds if math.isfinite(seconds) else None
        except Exception:
            return None


# Returns the first valid retry delay bounded between zero and a caller-selected maximum
def bounded_retry_after_seconds(candidates, fallback, maximum):
    for candidate in candidates:
        seconds = parse_retry_after_seconds(candidate)
        if seconds is not None:
            return max(0.0, min(seconds, maximum))
    return max(0.0, min(float(fallback), maximum))


# Parses a webhook rate-limit delay and caps untrusted server values to a short wait
def webhook_retry_after_seconds(response):
    headers = getattr(response, "headers", {}) or {}
    candidates = [headers.get("Retry-After")] if hasattr(headers, "get") else []
    try:
        payload = response.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        candidates.append(payload.get("retry_after"))
    return bounded_retry_after_seconds(candidates, WEBHOOK_FALLBACK_RETRY_SECONDS, WEBHOOK_MAX_RETRY_AFTER_SECONDS)


# Parses a Steam rate-limit delay and caps untrusted server values to one hour
def steam_retry_after_seconds(response, fallback):
    headers = getattr(response, "headers", {}) or {}
    candidate = headers.get("Retry-After") if hasattr(headers, "get") else None
    return max(1, int(round(bounded_retry_after_seconds([candidate], fallback, STEAM_MAX_RETRY_AFTER_SECONDS))))


# Applies configured placeholders recursively to a webhook template
def format_payload(template, payload):
    if isinstance(template, dict):
        return {key: format_payload(value, payload) for key, value in template.items()}
    if isinstance(template, list):
        return [format_payload(value, payload) for value in template]
    if isinstance(template, tuple):
        return tuple(format_payload(value, payload) for value in template)
    if isinstance(template, str):
        if template == "{fields}":
            return payload.get("fields", [])
        if template == "{color}":
            return payload.get("color", 0x1B2838)
        try:
            return template.format(**payload)
        except KeyError:
            return template
    return template


# Returns a configuration error for unsafe or unsupported webhook customization
def validate_webhook_customization(provider=None):
    selected_provider = normalized_webhook_provider(provider)
    if selected_provider == "discord":
        if not isinstance(WEBHOOK_USERNAME, str):
            return "WEBHOOK_USERNAME must be a string"
        if not isinstance(WEBHOOK_AVATAR_URL, str):
            return "WEBHOOK_AVATAR_URL must be a string"
        if WEBHOOK_AVATAR_URL.strip() and not validate_webhook_url(WEBHOOK_AVATAR_URL):
            return "WEBHOOK_AVATAR_URL must contain a complete HTTPS link without embedded credentials"
        if not isinstance(WEBHOOK_TEMPLATE, (dict, list, str)):
            return "WEBHOOK_TEMPLATE must be a dictionary, list or string"
    if not isinstance(WEBHOOK_TRANSFORMS, (list, tuple)):
        return "WEBHOOK_TRANSFORMS must be a list or tuple"
    for index, transform in enumerate(WEBHOOK_TRANSFORMS):
        if not isinstance(transform, (list, tuple)) or len(transform) < 2 or not isinstance(transform[0], str) or not isinstance(transform[1], str):
            return f"WEBHOOK_TRANSFORMS entry {index + 1} must contain a field name and string method name"
        if transform[1].startswith("_") or not callable(getattr("", transform[1], None)):
            return f"WEBHOOK_TRANSFORMS entry {index + 1} uses an unsupported string method"
    return None


# Applies configured string transformations to one webhook value mapping
def apply_webhook_transforms(payload):
    transformed = dict(payload)
    for index, transform in enumerate(WEBHOOK_TRANSFORMS):
        field = transform[0]
        method_name = transform[1]
        if field not in transformed or not isinstance(transformed[field], str):
            continue
        try:
            transformed[field] = getattr(transformed[field], method_name)(*transform[2:])
        except Exception:
            raise ValueError(f"WEBHOOK_TRANSFORMS entry {index + 1} could not apply {field}.{method_name}")
    return transformed


# Builds bounded placeholder values shared by webhook templates and providers
def build_webhook_values(title, description, notification_type, image_url=""):
    colors = {"active": 0x57CBDE, "inactive": 0x747F8D, "status": 0x66C0F4, "game": 0x1A9FFF, "level_xp": 0xF5C518, "friends": 0x5C7E10, "games": 0xA4D007, "name": 0x9B59B6, "error": 0xE74C3C}
    safe_title = re.sub(r"[\r\n]+", " ", sanitize_error_text(title)).strip()[:WEBHOOK_EMBED_TITLE_LIMIT] or "Steam Monitor"
    safe_description = re.sub(r"\r\n?", "\n", sanitize_error_text(description)).strip()[:WEBHOOK_EMBED_DESCRIPTION_LIMIT]
    username = WEBHOOK_USERNAME.strip()[:80] if isinstance(WEBHOOK_USERNAME, str) else ""
    avatar_url = WEBHOOK_AVATAR_URL.strip() if isinstance(WEBHOOK_AVATAR_URL, str) else ""
    payload = {"title": safe_title, "description": safe_description, "version": VERSION, "image_url": str(image_url or ""), "fields": [], "fields_str": "", "color": colors.get(notification_type, 0x1B2838), "timestamp": datetime.now().astimezone().isoformat(), "username": username, "avatar_url": avatar_url}
    return apply_webhook_transforms(payload)


# Builds one customized Discord-format payload while keeping mentions disabled
def build_webhook_payload(title, description, notification_type, image_url="", payload_values=None):
    values = build_webhook_values(title, description, notification_type, image_url) if payload_values is None else payload_values
    try:
        payload = format_payload(WEBHOOK_TEMPLATE, values)
    except Exception:
        raise ValueError("WEBHOOK_TEMPLATE could not be formatted with the supported placeholders")
    if isinstance(payload, dict):
        if payload.get("username") == "":
            payload.pop("username")
        if payload.get("avatar_url") == "":
            payload.pop("avatar_url")
        payload["allowed_mentions"] = {"parse": []}
        embeds = payload.get("embeds")
        if isinstance(embeds, list):
            for embed in embeds:
                if isinstance(embed, dict) and isinstance(embed.get("thumbnail"), dict) and not embed["thumbnail"].get("url"):
                    embed.pop("thumbnail")
    return payload


# Truncates text to a UTF-8 byte limit without returning a partial character
def truncate_utf8_bytes(text, max_bytes, suffix=""):
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    encoded_suffix = suffix.encode("utf-8")
    if len(encoded_suffix) >= max_bytes:
        return encoded_suffix[:max_bytes].decode("utf-8", errors="ignore")
    return encoded[:max_bytes - len(encoded_suffix)].decode("utf-8", errors="ignore") + suffix


# Builds one bounded ntfy title and message pair
def build_ntfy_webhook_message(title, description):
    safe_title = re.sub(r"[\r\n]+", " ", sanitize_error_text(title)).strip()[:WEBHOOK_EMBED_TITLE_LIMIT] or "Steam Monitor"
    safe_message = truncate_utf8_bytes(re.sub(r"\r\n?", "\n", sanitize_error_text(description)).strip(), NTFY_MESSAGE_LIMIT_BYTES, NTFY_TRUNCATION_SUFFIX)
    return safe_title, safe_message


# Returns a validation error for unsupported ntfy priority or tag values
def validate_ntfy_metadata(priority, tags):
    if not isinstance(priority, int) or isinstance(priority, bool) or not 0 <= priority <= 5:
        return "ntfy priority must be 0 to omit it or an integer from 1 through 5"
    if not isinstance(tags, str):
        return "ntfy tags must be a comma-separated string"
    if "\r" in tags or "\n" in tags:
        return "ntfy tags must not contain line breaks"
    return None


# Returns a safe validation error for one custom webhook header mapping
def _validate_webhook_header_mapping(headers):
    if not isinstance(headers, dict):
        return "WEBHOOK_HEADERS must be a dictionary of string header names and values"
    normalized_names = set()
    for name, value in headers.items():
        if not isinstance(name, str) or not re.fullmatch(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+", name):
            return "WEBHOOK_HEADERS contains an invalid HTTP header name"
        normalized_name = name.casefold()
        if normalized_name in normalized_names:
            return "WEBHOOK_HEADERS contains duplicate case-insensitive header names"
        normalized_names.add(normalized_name)
        if not isinstance(value, str):
            return f"WEBHOOK_HEADERS value for {name} must be a string"
        if "\r" in value or "\n" in value:
            return f"WEBHOOK_HEADERS value for {name} must not contain line breaks"
    return None


# Returns a safe configuration error for custom webhook headers or ntfy access tokens
def validate_webhook_headers(provider=None):
    selected_provider = normalized_webhook_provider(provider)
    header_error = _validate_webhook_header_mapping(WEBHOOK_HEADERS)
    if header_error is not None:
        return header_error
    if selected_provider == "ntfy":
        if not isinstance(NTFY_ACCESS_TOKEN, str):
            return "NTFY_ACCESS_TOKEN must be a string"
        token = NTFY_ACCESS_TOKEN.strip()
        if "\r" in token or "\n" in token:
            return "NTFY_ACCESS_TOKEN must not contain line breaks"
        if token.casefold().startswith(("bearer ", "basic ")):
            return "NTFY_ACCESS_TOKEN must contain only the access token without an Authorization scheme"
    return None


# Builds provider-specific headers with custom placeholders and private ntfy authentication
def build_webhook_headers(provider, payload):
    validation_error = validate_webhook_headers(provider)
    if validation_error is not None:
        raise ValueError(validation_error)
    try:
        formatted_headers = format_payload(WEBHOOK_HEADERS, payload)
    except Exception:
        raise ValueError("WEBHOOK_HEADERS could not be formatted with the supported placeholders")
    formatted_error = _validate_webhook_header_mapping(formatted_headers)
    if formatted_error is not None:
        raise ValueError(formatted_error)
    if not isinstance(formatted_headers, dict):
        raise ValueError("WEBHOOK_HEADERS must be a dictionary of string header names and values")
    headers = {str(name): str(value) for name, value in formatted_headers.items()}
    if not any(name.casefold() == "user-agent" for name in headers):
        headers["User-Agent"] = f"SteamMonitor/{VERSION}"
    if provider == "ntfy":
        headers = {name: value for name, value in headers.items() if name.casefold() != "content-type"}
        headers["Content-Type"] = "text/plain; charset=utf-8"
        token = NTFY_ACCESS_TOKEN.strip()
        if token:
            headers = {name: value for name, value in headers.items() if name.casefold() != "authorization"}
            headers["Authorization"] = f"Bearer {token}"
    return headers


# Returns whether one image URL is a complete HTTPS URL on a Steam image host
def steam_image_url_is_allowed(image_url):
    try:
        parsed_url = urlsplit(image_url)
    except ValueError:
        return False
    hostname = parsed_url.hostname.casefold() if parsed_url.hostname else ""
    return parsed_url.scheme.casefold() == "https" and any(hostname == suffix or hostname.endswith(f".{suffix}") for suffix in NTFY_IMAGE_ALLOWED_HOST_SUFFIXES)


# Normalizes a Steam image hostname or protocol-relative URL to an allowed HTTPS URL
def normalize_steam_image_url(image_url):
    if not isinstance(image_url, str) or not image_url.strip():
        return ""
    normalized = image_url.strip()
    if normalized.startswith("//"):
        normalized = "https:" + normalized
    elif "://" not in normalized:
        normalized = "https://" + normalized.lstrip("/")
    return normalized if steam_image_url_is_allowed(normalized) else ""


# Returns the standard Steam game header image URL for one app ID
def steam_game_image_url(appid):
    return f"https://cdn.akamai.steamstatic.com/steam/apps/{int(appid)}/header.jpg" if appid else ""


# Builds one bounded in-memory JPEG for an ntfy attachment
def build_ntfy_image(image_url=""):
    if not NTFY_IMAGES or not image_url or not NTFY_IMAGES_AVAILABLE:
        return None
    try:
        if not steam_image_url_is_allowed(image_url):
            raise ValueError("ntfy image URL must use a Steam HTTPS image host")
        response = WEBHOOK_SESSION.get(image_url, headers={"User-Agent": f"SteamMonitor/{VERSION}"}, timeout=WEBHOOK_TIMEOUT_SECONDS, verify=VERIFY_SSL, stream=True, allow_redirects=False)
        with response:
            response.raise_for_status()
            content_type = str((response.headers or {}).get("Content-Type", "")).split(";", 1)[0].strip().casefold()
            if content_type and not content_type.startswith("image/"):
                raise ValueError("ntfy image response has an unsupported content type")
            content_length = (response.headers or {}).get("Content-Length")
            if content_length is not None and int(content_length) > NTFY_IMAGE_DOWNLOAD_LIMIT_BYTES:
                raise ValueError("ntfy image response is too large")
            image_bytes = bytearray()
            for chunk in response.iter_content(chunk_size=NTFY_IMAGE_DOWNLOAD_CHUNK_BYTES):
                if not chunk:
                    continue
                image_bytes.extend(chunk)
                if len(image_bytes) > NTFY_IMAGE_DOWNLOAD_LIMIT_BYTES:
                    raise ValueError("ntfy image response is too large")
        if not image_bytes:
            raise ValueError("ntfy image response was empty")
        with PILImage.open(BytesIO(bytes(image_bytes))) as original_img:
            if original_img.width * original_img.height > NTFY_IMAGE_PIXEL_LIMIT:
                raise ValueError("ntfy image has too many pixels")
            original_img.load()
            resized_img = original_img.convert("RGB")
        try:
            # Pillow moved LANCZOS into Resampling, so both the holder and the lookup stay dynamic
            resampling = getattr(getattr(PILImage, "Resampling", PILImage), "LANCZOS")  # noqa: B009
            resized_img.thumbnail((160, 160), resampling)
            canvas = PILImage.new("RGB", (400, 160), (27, 32, 35))
            try:
                paste_x = (canvas.size[0] - resized_img.size[0]) // 2
                paste_y = (canvas.size[1] - resized_img.size[1]) // 2
                canvas.paste(resized_img, (paste_x, paste_y))
                output = BytesIO()
                canvas.save(output, format="JPEG", quality=85, optimize=True)
                return output.getvalue()
            finally:
                canvas.close()
        finally:
            resized_img.close()
    except Exception as exc:
        debug_swallowed_exception("Preparing ntfy image", exc)
        return None


# Prints one webhook error without revealing private URLs, tokens or response bodies
def print_webhook_error(message):
    print(f"Error sending webhook: {sanitize_error_text(message)}")


# Sends one webhook request with the destination, deadline and redirect policy every delivery shares
def post_webhook_request(**request_kwargs):
    destination = str(WEBHOOK_URL or "").strip()
    # Revalidated here because a dotenv reload can replace the destination after the delivery started
    if not validate_webhook_url(destination):
        raise req.exceptions.InvalidURL("WEBHOOK_URL must contain a complete HTTPS link")
    return WEBHOOK_SESSION.post(destination, timeout=WEBHOOK_TIMEOUT_SECONDS, verify=VERIFY_SSL, allow_redirects=False, **request_kwargs)


# Sends one webhook through an isolated bounded retry path
def send_webhook(title, description, notification_type="status", force=False, sleeper=None, image_url="", ntfy_priority=0, ntfy_tags=""):
    if not force and not webhook_event_enabled(notification_type):
        return 1
    if not validate_webhook_url():
        print_webhook_error("WEBHOOK_URL must contain a complete HTTPS link")
        return 1
    provider = normalized_webhook_provider()
    if not provider:
        print_webhook_error("WEBHOOK_PROVIDER must be discord or ntfy")
        return 1
    metadata_error = validate_ntfy_metadata(ntfy_priority, ntfy_tags) if provider == "ntfy" else None
    if metadata_error is not None:
        print_webhook_error(metadata_error)
        return 1
    customization_error = validate_webhook_customization(provider)
    if customization_error is not None:
        print_webhook_error(customization_error)
        return 1
    header_error = validate_webhook_headers(provider)
    if header_error is not None:
        print_webhook_error(header_error)
        return 1
    normalized_image_url = normalize_steam_image_url(image_url)
    try:
        webhook_values = build_webhook_values(title, description, notification_type, normalized_image_url)
        request_headers = build_webhook_headers(provider, webhook_values)
        discord_payload = build_webhook_payload(title, description, notification_type, normalized_image_url, webhook_values) if provider == "discord" else None
    except ValueError as exc:
        print_webhook_error(str(exc))
        return 1
    debug_print("Webhook delivery", event=notification_type, channel=provider, host=webhook_destination_host())
    sleep_func = time.sleep if sleeper is None else sleeper
    ntfy_title, ntfy_message = build_ntfy_webhook_message(str(webhook_values["title"]), str(webhook_values["description"])) if provider == "ntfy" else ("", "")
    ntfy_image = build_ntfy_image(normalized_image_url) if provider == "ntfy" and NTFY_IMAGES and normalized_image_url else None
    use_ntfy_image = ntfy_image is not None
    ntfy_params = {"title": ntfy_title}  # type: Dict[str, Any]
    if provider == "ntfy" and ntfy_priority:
        ntfy_params["priority"] = ntfy_priority
    if provider == "ntfy" and ntfy_tags.strip():
        ntfy_params["tags"] = ntfy_tags.strip()
    for attempt in range(WEBHOOK_MAX_ATTEMPTS):
        debug_print("Webhook delivery", channel=provider, attempt=f"{attempt + 1}/{WEBHOOK_MAX_ATTEMPTS}", image="attached" if use_ntfy_image else None)
        try:
            if provider == "ntfy":
                if use_ntfy_image:
                    image_params = dict(ntfy_params)
                    image_params["message"] = ntfy_message
                    response = post_webhook_request(data=ntfy_image, params=image_params, headers=dict(request_headers, **{"Content-Type": "image/jpeg", "X-Filename": NTFY_IMAGE_FILENAME}))
                else:
                    response = post_webhook_request(data=ntfy_message.encode("utf-8"), params=ntfy_params, headers=request_headers)
            elif isinstance(discord_payload, str):
                response = post_webhook_request(data=discord_payload, headers=request_headers)
            else:
                response = post_webhook_request(json=discord_payload, headers=request_headers)
            if 200 <= response.status_code <= 299:
                verbose_print(f"Webhook delivered through {provider} (HTTP {response.status_code})")
                return 0
            retryable = response.status_code == 429 or 500 <= response.status_code <= 599
            debug_print("Webhook delivery", channel=provider, status=response.status_code, retryable=retryable)
            if use_ntfy_image and attempt < WEBHOOK_MAX_ATTEMPTS - 1:
                use_ntfy_image = False
                delay = webhook_retry_after_seconds(response) if response.status_code == 429 else WEBHOOK_FALLBACK_RETRY_SECONDS if response.status_code >= 500 else 0.0
                debug_print("Webhook delivery", channel=provider, image="dropped", retry_in=f"{delay}s")
                if delay:
                    sleep_func(delay)
                continue
            if not retryable or attempt == WEBHOOK_MAX_ATTEMPTS - 1:
                print_webhook_error(f"the service returned HTTP {response.status_code}")
                return 1
            delay = webhook_retry_after_seconds(response) if response.status_code == 429 else WEBHOOK_FALLBACK_RETRY_SECONDS
            debug_print("Webhook delivery", channel=provider, retry_in=f"{delay}s")
            sleep_func(delay)
        except req.RequestException as exc:
            debug_swallowed_exception("Webhook request", exc)
            if use_ntfy_image and attempt < WEBHOOK_MAX_ATTEMPTS - 1:
                use_ntfy_image = False
                debug_print("Webhook delivery", channel=provider, image="dropped", retry_in=f"{WEBHOOK_FALLBACK_RETRY_SECONDS}s")
                sleep_func(WEBHOOK_FALLBACK_RETRY_SECONDS)
                continue
            if attempt == WEBHOOK_MAX_ATTEMPTS - 1:
                print_webhook_error("the service could not be reached")
                return 1
            sleep_func(WEBHOOK_FALLBACK_RETRY_SECONDS)
    print_webhook_error("delivery failed")
    return 1


# Sends one alert through the enabled email and webhook channels
def send_notification_channels(notification_type, subject, body, body_html="", email_enabled=False, webhook_enabled=None, image_url="", ntfy_priority=0, ntfy_tags=""):
    email_attempted = bool(email_enabled)
    webhook_attempted = webhook_event_enabled(notification_type) if webhook_enabled is None else bool(webhook_enabled)
    email_delivered = False
    webhook_delivered = False
    if email_attempted:
        print(f"Sending email notification to {RECEIVER_EMAIL}")
        email_delivered = send_email(subject, body, body_html, SMTP_SSL) == 0
        debug_print("Email channel", event=notification_type, outcome="OK" if email_delivered else "failed")
    if webhook_attempted:
        print("Sending webhook notification")
        webhook_delivered = send_webhook(subject, body, notification_type, force=True, image_url=image_url, ntfy_priority=ntfy_priority, ntfy_tags=ntfy_tags) == 0
        debug_print("Webhook channel", event=notification_type, outcome="OK" if webhook_delivered else "failed")
    # Delivery, not the attempt, so a channel that failed is retried while one that succeeded is not resent
    return email_delivered, webhook_delivered


# Reports the running Python version plus every required and optional dependency
def doctor_check_environment(version_info=None, spec_finder=None):
    checks = []
    selected_version = sys.version_info if version_info is None else version_info
    version_text = ".".join(str(part) for part in tuple(selected_version)[:3])
    minimum_detail = f"Minimum supported version: {MINIMUM_PYTHON_VERSION_TEXT}"
    if tuple(selected_version)[:2] >= MINIMUM_PYTHON_VERSION:
        checks.append(make_doctor_check("Environment", "PASS", f"Python {version_text} is supported", minimum_detail))
    else:
        advice = make_recovery_advice("dependency.missing", f"Python {version_text} is unsupported", f"Install Python {MINIMUM_PYTHON_VERSION_TEXT} or newer then retry", False)
        checks.append(make_doctor_check("Environment", "FAIL", advice.summary, minimum_detail, advice))

    find_spec = importlib.util.find_spec if spec_finder is None else spec_finder

    # Returns whether one module can be located, treating an unimportable parent as absent
    def module_present(module_name):
        try:
            return find_spec(module_name) is not None
        except (ImportError, ValueError):
            return False

    for module_name, package_name in (("requests", "requests"), ("dateutil", "python-dateutil"), ("steam", "steam")):
        if module_present(module_name):
            checks.append(make_doctor_check("Environment", "PASS", f"Required dependency {package_name} is installed"))
        else:
            advice = make_recovery_advice("dependency.missing", f"Required dependency {package_name} is missing", f'Install it with: pip3 install "{package_name}"', False)
            checks.append(make_doctor_check("Environment", "FAIL", advice.summary, advice=advice))

    if module_present("dotenv"):
        checks.append(make_doctor_check("Environment", "PASS", "Optional dependency python-dotenv is installed", "Used only for reading secrets from a dotenv file"))
    else:
        checks.append(make_doctor_check("Environment", "WARN", "Optional dependency python-dotenv is not installed", "Secrets can only come from environment variables or the configuration file. Everything else works. Install it with: pip3 install python-dotenv"))

    # The guarded import flag is checked rather than the module, because it reflects whether artwork actually works
    if NTFY_IMAGES_AVAILABLE:
        checks.append(make_doctor_check("Environment", "PASS", "Optional dependency Pillow is installed", "Used only for artwork attachments in ntfy alerts"))
    else:
        checks.append(make_doctor_check("Environment", "WARN", "Optional dependency Pillow is not installed", f"ntfy alerts are delivered as text without artwork. Every other feature is unaffected. Install it with: {ntfy_images_install_command()}"))

    # A warning about a library that cannot affect this machine is noise, so the row is skipped off Windows
    if platform.system() == "Windows":
        if module_present("colorama"):
            checks.append(make_doctor_check("Environment", "PASS", "Optional dependency colorama is installed", "Used only for coloured output in the older Windows Command Prompt"))
        else:
            checks.append(make_doctor_check("Environment", "WARN", "Optional dependency colorama is not installed", "Coloured output may not render in the older Windows Command Prompt. Windows Terminal needs nothing extra. Install it with: pip3 install colorama"))
    return checks


# Groups the configured secret names by the source each value actually came from
def doctor_secret_sources(env_path=None):
    environment_sources = secret_sources(env_path)
    from_file = []
    from_environment = []
    from_settings = []
    from_command_line = []
    for key in SECRET_KEYS:
        if not doctor_value_is_set(globals().get(key)):
            continue
        source = environment_sources.get(key)
        # An argument overrides whatever the dotenv file or the environment held, so it is checked first
        if key in COMMAND_LINE_SECRET_KEYS:
            from_command_line.append(key)
        elif source == "environment":
            from_environment.append(key)
        elif source:
            from_file.append(key)
        else:
            from_settings.append(key)
    return from_file, from_environment, from_settings, from_command_line


# Reports which secrets are in effect and where each one was read from, by name and never by value
def doctor_secret_checks(env_path=None):
    from_file, from_environment, from_settings, from_command_line = doctor_secret_sources(env_path)
    checks = []
    if from_file:
        checks.append(make_doctor_check("Configuration", "PASS", "Secrets loaded from the dotenv file", ", ".join(from_file)))
    if from_environment:
        checks.append(make_doctor_check("Configuration", "PASS", "Secrets loaded from the environment", ", ".join(from_environment)))
    if from_settings:
        checks.append(make_doctor_check("Configuration", "PASS", "Secrets loaded from the configuration file or command line", ", ".join(from_settings)))
    if from_command_line:
        checks.append(make_doctor_check("Configuration", "PASS", "Secrets loaded from the command line", ", ".join(from_command_line)))
    if not checks:
        checks.append(make_doctor_check("Configuration", "PASS", "No secrets loaded", "Nothing was read from a dotenv file, the environment or the command line"))
    return checks


# Returns the log file monitoring will actually write, which needs the target-derived suffix
def build_log_path(base_path, suffix):
    log_path = Path(os.path.expanduser(str(base_path)))
    if log_path.suffix == "" and suffix:
        log_path = log_path.parent / f"{log_path.name}_{suffix}.log"
    return log_path


# Returns the closest parent that exists, so writability is judged without creating anything
def nearest_existing_parent(path):
    candidate = Path(path).expanduser()
    if candidate.exists():
        return candidate if candidate.is_dir() else candidate.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


# Reports whether one file monitoring will write can be created, without creating anything
def doctor_destination_check(label, destination):
    selected = Path(destination).expanduser()
    parent = nearest_existing_parent(selected)
    if parent.is_dir() and os.access(parent, os.W_OK):
        return make_doctor_check("Configuration", "PASS", f"{label} appears writable", f"Path: {selected}")
    advice = classify_recovery_error(context="file", detail=f"{label} is not writable: {selected}")
    return make_doctor_check("Configuration", "FAIL", advice.summary, advice.detail, advice)


# Reports each file monitoring will write, resolving the log name once a target is known
def doctor_output_destination_checks(target_value=None):
    checks = []
    if DISABLE_LOGGING:
        checks.append(make_doctor_check("Configuration", "PASS", "Output logging is disabled"))
    elif ST_LOGFILE:
        suffix = str(FILE_SUFFIX or "") or (str(target_value) if target_value else "")
        if suffix:
            checks.append(doctor_destination_check("Log destination", build_log_path(ST_LOGFILE, suffix)))
        else:
            checks.append(make_doctor_check("Configuration", "PASS", "Log destination will be finalized after a target is selected", f"Base path: {Path(os.path.expanduser(ST_LOGFILE))}"))
    if CSV_FILE:
        checks.append(doctor_destination_check("CSV destination", CSV_FILE))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "CSV logging is disabled"))
    if PROFILE_CSV_FILE:
        checks.append(doctor_destination_check("Profile CSV destination", PROFILE_CSV_FILE))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "Profile CSV logging is disabled"))
    return checks


# Reports the configuration and dotenv files in effect plus every file the tool will generate
def doctor_check_configuration(config_path=None, env_path=None, target_value=None):
    checks = []
    if config_path:
        checks.append(make_doctor_check("Configuration", "PASS", "Configuration file loaded", f"Path: {config_path}"))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No configuration file selected", "Using built-in defaults and command-line overrides"))
    if env_path and os.path.isfile(str(env_path)):
        checks.append(make_doctor_check("Configuration", "PASS", "Dotenv file loaded", f"Path: {env_path}"))
    elif env_path:
        advice = make_recovery_advice("config.missing", "The requested dotenv file was not found", recovery_fix_with_guide("Create the file or select an existing path with --env-file", SECRETS_GUIDE_URL), False, f"Path: {env_path}")
        checks.append(make_doctor_check("Configuration", "WARN", advice.summary, advice.detail, advice))
    else:
        checks.append(make_doctor_check("Configuration", "PASS", "No dotenv file selected", "Using environment variables and other configured sources"))
    checks.extend(doctor_secret_checks(env_path))

    if VERIFY_SSL:
        checks.append(make_doctor_check("Configuration", "PASS", "TLS certificate verification is on", "Every outbound request checks the server certificate"))
    else:
        advice = make_recovery_advice("config.insecure", "TLS certificate verification is off", recovery_fix_with_guide("Set VERIFY_SSL back to True unless this network intercepts TLS with its own certificate authority", TLS_GUIDE_URL), False)
        checks.append(make_doctor_check("Configuration", "WARN", "TLS certificate verification is off", "VERIFY_SSL is False, so an intercepted connection cannot be told apart from the real service", advice))

    checks.extend(doctor_output_destination_checks(target_value))
    return checks


# Confirms the configured connectivity endpoint is reachable, reusing the settings monitoring will use
def doctor_check_connectivity():
    global LAST_CONNECTIVITY_ERROR
    LAST_CONNECTIVITY_ERROR = None
    if check_internet(quiet=True):
        return [make_doctor_check("Connectivity", "PASS", "The connectivity endpoint is reachable", f"Endpoint: {CHECK_INTERNET_URL}")]
    advice = classify_recovery_error(LAST_CONNECTIVITY_ERROR, context="connectivity", detail=f"Could not reach {CHECK_INTERNET_URL}")
    return [make_doctor_check("Connectivity", "FAIL", "The connectivity endpoint could not be reached", f"Endpoint: {CHECK_INTERNET_URL}", advice)]


# Validates the Steam Web API key once and stores the client so later checks reuse it
def doctor_check_authentication(report):
    if not doctor_value_is_set(STEAM_API_KEY):
        advice = classify_recovery_error(context="set_steam_api_key", detail="No Steam Web API key is configured")
        return [make_doctor_check("Authentication", "FAIL", "No Steam Web API key is configured", "Nothing can be monitored without one", advice)]
    try:
        report.steam_client = steam_web_api_client()
    except Exception as exc:
        advice = classify_recovery_error(exc, context="runtime")
        return [make_doctor_check("Authentication", "FAIL", advice.summary, advice.detail, advice)]
    return [make_doctor_check("Authentication", "PASS", "Steam accepted the configured Web API key", "The key itself was not displayed")]


# Confirms the monitored profile exists and is visible, reusing the client the authentication check opened
def doctor_check_target(report, target_value=None):
    if not target_value:
        advice = classify_recovery_error(context="target.missing")
        return [make_doctor_check("Target", "WARN", advice.summary, "Nothing will be monitored until one is given", advice)]
    if report.steam_client is None:
        return [make_doctor_check("Target", "SKIP", "The monitored profile was not checked", "The Steam Web API key did not validate, so no lookup was attempted")]
    try:
        steam_id = resolve_steam_target(target_value, STEAM_API_KEY)
        summary = report.steam_client.call("ISteamUser.GetPlayerSummaries", steamids=str(steam_id))
        players = summary["response"]["players"]
    except Exception as exc:
        advice = classify_recovery_error(exc, context="target")
        return [make_doctor_check("Target", "FAIL", advice.summary, advice.detail, advice)]
    if not players:
        advice = classify_recovery_error(context="target", detail=f"Steam returned no profile for Steam64 ID {steam_id}")
        return [make_doctor_check("Target", "FAIL", advice.summary, advice.detail, advice)]
    report.player_summary = players[0]
    report.steam_id = steam_id
    checks = [make_doctor_check("Target", "PASS", "The monitored profile exists", f"Display name: {sanitize_untrusted_text(players[0].get('personaname'))} (Steam64 ID {steam_id})")]
    visibility = int(players[0].get("communityvisibilitystate", 1))
    if visibility >= 3:
        checks.append(make_doctor_check("Target", "PASS", "The monitored profile is publicly visible", "Status and game details can be read"))
    else:
        advice = make_recovery_advice("target.not_visible", "The monitored profile is not publicly visible", recovery_fix_with_guide("Ask the user to set profile and game details visibility to Public", PRIVACY_GUIDE_URL), False)
        checks.append(make_doctor_check("Target", "WARN", advice.summary, "Status and game changes cannot be detected while it is private", advice))
    return checks


# Joins setting names the way every doctor detail and action in this family lists them
def join_setting_names(names, conjunction):
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} {conjunction} {names[-1]}"


# Returns the doctor row for email alerts whose settings cannot deliver, worded the same way by every sibling monitor
def doctor_email_unusable_check(detail, fix):
    advice = make_recovery_advice("smtp.invalid", EMAIL_UNUSABLE_CHECK_LABEL, recovery_fix_with_guide(fix, SMTP_GUIDE_URL), False, detail)
    return make_doctor_check("Notifications", "WARN", EMAIL_UNUSABLE_CHECK_LABEL, detail, advice)


# Checks email alert settings then confirms the SMTP sign-in without sending anything
def doctor_check_email_notifications(report):
    enabled_categories = _startup_email_notification_categories()
    configured = doctor_value_is_set(SMTP_HOST) and doctor_value_is_set(SENDER_EMAIL) and doctor_value_is_set(RECEIVER_EMAIL)
    # The error alert ships on by default, so it alone cannot mean the channel is switched on
    deliberate_categories = [category for category in enabled_categories if category != "errors"]
    if not deliberate_categories and not configured:
        return [make_doctor_check("Notifications", "PASS", "Email notifications are disabled", "No SMTP connection was attempted and no email was sent")]
    if not configured:
        unset = [name for name, value in (("SMTP_HOST", SMTP_HOST), ("SENDER_EMAIL", SENDER_EMAIL), ("RECEIVER_EMAIL", RECEIVER_EMAIL)) if not doctor_value_is_set(value)]
        return [doctor_email_unusable_check(f"{join_setting_names(unset, 'or')} is empty or still set to its placeholder", f"Set {join_setting_names(unset, 'and')} or turn the email alerts off")]
    if not enabled_categories:
        advice = make_recovery_advice("smtp.invalid", "Email is configured but no alert types are selected", recovery_fix_with_guide("Turn on at least one email alert in the configuration file", SMTP_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be emailed", advice)]
    if not doctor_value_is_set(SMTP_USER) or not doctor_value_is_set(SMTP_PASSWORD):
        return [doctor_email_unusable_check("SMTP_USER or SMTP_PASSWORD is empty or still set to its placeholder", "Set SMTP_USER and SMTP_PASSWORD or turn the email alerts off")]
    smtp_object = None
    try:
        smtp_object = smtp_connect_and_login(SMTP_SSL, smtp_timeout=5)
    except Exception as exc:
        advice = classify_recovery_error(exc, "email")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    finally:
        if smtp_object is not None:
            try:
                smtp_object.quit()
            except Exception:
                pass
    report.email_ready = True
    return [make_doctor_check("Notifications", "PASS", SMTP_READY_CHECK_LABEL, f"Alerts: {', '.join(enabled_categories)}. No email was sent during this passive check")]


# Checks webhook alert settings without sending anything, asking whether the channel can fire before validating it
def doctor_check_webhook_notifications(report):
    selected_categories = _selected_webhook_notification_categories()
    deliberate_categories = [category for category in selected_categories if category != "errors"]
    if not WEBHOOK_ENABLED and not deliberate_categories:
        return [make_doctor_check("Notifications", "PASS", "Webhook alerts are disabled")]
    if not WEBHOOK_ENABLED:
        advice = make_recovery_advice("webhook.invalid", "Webhook alert types are selected but webhooks are switched off", recovery_fix_with_guide("Set WEBHOOK_ENABLED to True, or turn the alert types off", WEBHOOK_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be delivered", advice)]
    if not normalized_webhook_provider():
        advice = classify_recovery_error(context="webhook", detail="WEBHOOK_PROVIDER must be discord or ntfy")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    if not validate_webhook_url():
        advice = classify_recovery_error(context="webhook", detail="WEBHOOK_URL must contain a complete HTTPS link")
        return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    for validation_error in (validate_webhook_customization(normalized_webhook_provider()), validate_webhook_headers(normalized_webhook_provider())):
        if validation_error is not None:
            advice = classify_recovery_error(context="webhook", detail=validation_error)
            return [make_doctor_check("Notifications", "FAIL", advice.summary, advice.detail, advice)]
    if not selected_categories:
        advice = make_recovery_advice("webhook.invalid", "Webhook alerts are on but no alert types are selected", recovery_fix_with_guide("Turn on at least one webhook alert in the configuration file, or set WEBHOOK_ENABLED to False", WEBHOOK_GUIDE_URL), False)
        return [make_doctor_check("Notifications", "WARN", advice.summary, "Nothing would ever be delivered", advice)]
    report.webhook_ready = True
    return [make_doctor_check("Notifications", "PASS", f"{WEBHOOK_READY_CHECK_LABEL} for {webhook_provider_display_name()}", f"Alerts: {', '.join(selected_categories)}. The private link was not displayed. No webhook was sent during this passive check")]


# The fixed section order the report renders in, chosen so each section depends only on the ones above it
DOCTOR_SECTIONS = ("Environment", "Configuration", "Authentication", "Connectivity", "Target", "Notifications")

# Delivery results are printed as they happen rather than inside a section, but they still count in the summary
DOCTOR_DELIVERY_SECTION = "Optional delivery tests"

# The theme entry each doctor result marker is drawn in, so a failure reads as one at a glance
DOCTOR_MARK_STYLES = {"PASS": "boolean_true", "WARN": "warning", "FAIL": "error", "SKIP": "info"}

# Width of the transient progress line currently on screen, so the next write can erase exactly what it drew
DOCTOR_PROGRESS_WIDTH = 0


# Renders one doctor result marker in the colour its status calls for
def render_doctor_marker(status):
    return colorize(DOCTOR_MARK_STYLES.get(status, "info"), f"[{status}]")


# Renders the heading and every non-empty section, with a fix line on the rows that are not a pass
def render_doctor_sections(report):
    # The install method is context rather than a check: it cannot fail, so it is stated once here
    # instead of occupying a result row that no marker describes
    lines = [colorize("header", "Doctor"), f"Detected install method: {colorize('username', install_method())}"]
    for section in DOCTOR_SECTIONS:
        section_checks = [check for check in report.checks if check.section == section]
        if not section_checks:
            continue
        lines.extend(("", colorize("section", section)))
        for check in section_checks:
            lines.append(f"{render_doctor_marker(check.status)} {check.label}")
            if check.detail:
                lines.append(f"  {check.detail}")
            if check.status != "PASS" and check.advice is not None:
                # The fix carries its own guide line, so each line is indented and styled on its own rather
                # than leaving one colour sequence open across the newline
                lines.extend(f"  {colorize('info', advice_line)}" for advice_line in f"To fix: {check.advice.fix}".splitlines())
    return sanitize_error_text("\n".join(lines))


# Renders the one sentence that says whether the setup is usable and where to read more
def render_doctor_summary(checks):
    failures = sum(check.status == "FAIL" for check in checks)
    warnings = sum(check.status == "WARN" for check in checks)
    if failures:
        summary_line = colorize("error", f"  {failures} check(s) failed, {warnings} warning(s). Fix the failures above before relying on the tool.")
    elif warnings:
        summary_line = colorize("warning", f"  All critical checks passed with {warnings} warning(s). Review the warnings above.")
    else:
        summary_line = colorize("boolean_true", "  All checks passed. You are good to go!")
    return "\n".join(("", colorize("header", "Summary"), summary_line, "", colorize("info", f"Guide: {DOCTOR_GUIDE_URL}")))


# Returns the real terminal underneath the logger wrapper, so progress can move the cursor safely
def _doctor_terminal_stream():
    stream = sys.stdout
    while isinstance(stream, (Logger, ColorStream)):
        stream = stream.terminal
    return stream


# Shows one transient doctor step, only on an interactive terminal
# The line stays uncoloured on purpose: it is erased by writing exactly len(line) spaces, and escape
# sequences would make that width wrong and leave a styled remnant behind
def _doctor_progress(label):
    global DOCTOR_PROGRESS_WIDTH
    terminal = _doctor_terminal_stream()
    if terminal.isatty():
        if DOCTOR_PROGRESS_WIDTH:
            terminal.write("\r" + (" " * DOCTOR_PROGRESS_WIDTH) + "\r")
        line = f"* Checking {ANSI_ESCAPE_RE.sub('', sanitize_untrusted_text(label))} ..."
        DOCTOR_PROGRESS_WIDTH = len(line)
        terminal.write("\r" + line)
        terminal.flush()


# Clears the transient doctor progress line on an interactive terminal
def _doctor_progress_clear():
    global DOCTOR_PROGRESS_WIDTH
    terminal = _doctor_terminal_stream()
    if terminal.isatty() and DOCTOR_PROGRESS_WIDTH:
        terminal.write("\r" + (" " * DOCTOR_PROGRESS_WIDTH) + "\r")
        terminal.flush()
    DOCTOR_PROGRESS_WIDTH = 0


# States what doctor will and will not do, before the first slow check starts rather than after
def render_doctor_notice():
    print("Running preflight checks. No files will be written. Interactive email and webhook tests run only after separate approval.\n")


# Prompts for explicit delivery consent and defaults safely to no
def _doctor_ask_yes_no(question):
    while True:
        try:
            value = read_interactively(input, colorize("info", f"{question} [y/N]: ")).strip().casefold()
        except (EOFError, KeyboardInterrupt):
            print("\nDelivery test skipped.")
            return False
        if not value or value in ("n", "no"):
            return False
        if value in ("y", "yes"):
            return True
        print("  Please answer 'y' or 'n'.")


# Offers one real delivery per ready channel, only after separate interactive approval
def _doctor_offer_notification_tests(report):
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return []
    if not report.email_ready and not report.webhook_ready:
        return []
    print(colorize("header", "\nOptional delivery tests\n"))
    print("Doctor will not write files. Each approved test sends one real message.\n")
    checks = []
    if report.email_ready:
        if _doctor_ask_yes_no("Send one test email now? This will deliver a real message"):
            delivered = send_email("steam_monitor: doctor test email", "This test email was sent after approval in --doctor. Your SMTP delivery settings work.", "", SMTP_SSL, smtp_timeout=5) == 0
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "PASS" if delivered else "FAIL", "Doctor test email delivered" if delivered else "Doctor test email delivery failed", "One real test email was sent after confirmation" if delivered else "The approved test email could not be delivered")
        else:
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "SKIP", "Test email was not sent")
        checks.append(check)
        # Recorded on the report so the summary sentence and the exit code cannot disagree about the same run
        report.checks.append(check)
        print(f"{render_doctor_marker(check.status)} {check.label}")
    if report.webhook_ready:
        provider = webhook_provider_display_name()
        if _doctor_ask_yes_no(f"Send one test webhook through {provider} now? This will publish a real notification"):
            delivered = send_webhook("steam_monitor: doctor test webhook", "This test notification was sent after approval in --doctor. Your webhook delivery settings work.", "status", force=True) == 0
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "PASS" if delivered else "FAIL", "Doctor test webhook delivered" if delivered else "Doctor test webhook delivery failed", "One real test webhook was sent after confirmation" if delivered else "The approved test webhook could not be delivered")
        else:
            check = make_doctor_check(DOCTOR_DELIVERY_SECTION, "SKIP", "Test webhook was not sent")
        checks.append(check)
        report.checks.append(check)
        print(f"{render_doctor_marker(check.status)} {check.label}")
    return checks


# Runs every preflight check, then the approved delivery tests, returning zero only when nothing failed
def run_doctor(target_value=None, config_path=None, env_path=None):
    report = DoctorReport()
    progress = _doctor_progress if _doctor_terminal_stream().isatty() else None
    render_doctor_notice()
    try:
        for label, collect in (
            ("environment", lambda: doctor_check_environment()),
            ("configuration", lambda: doctor_check_configuration(config_path, env_path, target_value)),
            ("connectivity", lambda: doctor_check_connectivity()),
            ("authentication", lambda: doctor_check_authentication(report)),
            ("the monitored profile", lambda: doctor_check_target(report, target_value)),
            ("notifications", lambda: doctor_check_email_notifications(report) + doctor_check_webhook_notifications(report)),
        ):
            if progress is not None:
                progress(label)
            report.checks.extend(collect())
    finally:
        _doctor_progress_clear()
    print(render_doctor_sections(report))
    _doctor_offer_notification_tests(report)
    print(render_doctor_summary(report.checks))
    failed = any(check.status == "FAIL" for check in report.checks)
    if not failed:
        print("")
        print(f"Start monitoring with: {render_command([str(target_value)] if target_value else [])}")
    return 1 if failed else 0


# Returns a stored value only when it is a real answer, so template placeholders are never offered as defaults
def _wizard_default(value):
    return str(value) if doctor_value_is_set(value if isinstance(value, str) else str(value or "")) else ""


# Prints the shared line telling the user how defaults and cancelling work
def _wizard_print_default_guidance():
    print("Press Enter to accept the shown default. Ctrl+C cancels.\n")


# Reads one setup line, colorized like the sibling monitors. Cancelling propagates to the one
# handler in run_setup_wizard, which reports that nothing was written
def _wizard_input(prompt_text, input_func=None):
    prompt = input if input_func is None else input_func
    try:
        return read_interactively(prompt, colorize("info", prompt_text))
    except (EOFError, KeyboardInterrupt):
        # The interrupted prompt owns the line break, so every handler prints its message alone
        print()
        raise


# Asks one free-text question, returning the shown default when the answer is empty
def _wizard_ask_text(question, default="", required=False, input_func=None):
    suffix = f" [{default}]" if default else ""
    while True:
        answer = _wizard_input(f"{question}{suffix}: ", input_func=input_func).strip()
        if not answer:
            answer = default
        if answer or not required:
            return answer
        print("  This value is required.")
        if not _wizard_offer_retry(question, input_func=input_func):
            return ""


# Asks one yes or no question with a visible default
def _wizard_ask_yes_no(question, default=True, input_func=None):
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        answer = _wizard_input(f"{question} {hint}: ", input_func=input_func).strip().casefold()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


# Offers the one way out after an entry the wizard cannot use, so declining keeps every answer already given
def _wizard_offer_retry(label, consequence="", input_func=None):
    if consequence:
        return not _wizard_ask_yes_no(f"Continue without the {label}? {consequence}", default=False, input_func=input_func)
    return _wizard_ask_yes_no(f"Try entering the {label} again?", default=True, input_func=input_func)


# Asks one numbered multiple-choice question and returns the chosen index
def _wizard_ask_choice(question, options, default_index=0, input_func=None):
    print()
    print(question)
    for index, (label, description) in enumerate(options, 1):
        marker = " (default)" if index - 1 == default_index else ""
        print(f"  {colorize('username', str(index))}. {label}{colorize('info', marker)}")
        if description:
            for line in description.splitlines():
                print(f"     {line}")
    while True:
        answer = _wizard_input(f"Choose [1-{len(options)}]: ", input_func=input_func).strip()
        if not answer:
            return default_index
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        print(f"  Enter a number between 1 and {len(options)}.")


# Asks until the user provides a positive whole number or accepts the default
def _wizard_ask_positive_int(question, default, input_func=None):
    while True:
        answer = _wizard_ask_text(question, default=str(default), required=True, input_func=input_func)
        try:
            parsed = int(answer)
        except ValueError:
            parsed = 0
        if parsed > 0:
            return parsed
        print("  Enter a positive whole number.")


# Renders a wizard duration as raw seconds plus a readable form, so the stored config value stays visible
def _wizard_format_duration(seconds):
    remaining = seconds
    parts = []
    for suffix, count in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        value, remaining = divmod(remaining, count)
        if value:
            parts.append(f"{value}{suffix}")
    raw = f"{seconds}s"
    readable = " ".join(parts) or raw
    return raw if readable == raw else f"{raw} - {readable}"


# Asks one duration, accepting the formats people actually type
def _wizard_ask_duration(question, default, input_func=None):
    prompt_text = f"{question} [{_wizard_format_duration(default)}]: "
    while True:
        answer = _wizard_input(prompt_text, input_func=input_func).strip()
        if not answer:
            return default
        seconds = parse_duration_input(answer)
        if seconds is not None:
            return seconds
        print("  Enter a positive duration such as 120, 2m, 1.5h, 1h 30m or 1d.")


# Asks one secret through a hidden prompt with debug output off, so it never reaches the screen, the shell history or the debug stream
def _wizard_ask_secret(question, getpass_func=None):
    hidden_prompt = getpass.getpass if getpass_func is None else getpass_func
    try:
        # Colorized like the visible prompts, so a hidden answer does not look like a different question
        with debug_output_suppressed():
            return str(read_interactively(hidden_prompt, colorize("info", f"{question}: "))).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise


# Renders one configuration file from the built-in template with the chosen values substituted in
def generate_config_with_current_values(config_values):
    tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    replacements = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            continue
        name = statement.targets[0].id
        if name not in config_values:
            continue
        replacements[name] = (statement.lineno, getattr(statement, "end_lineno", statement.lineno), repr(config_values[name]))
    lines = CONFIG_BLOCK.strip("\n").split("\n")
    # The template keeps its own leading blank line, so template line numbers are one ahead of this list
    offset = 1 if CONFIG_BLOCK.startswith("\n") else 0
    skip_until = 0
    output = []
    for number, line in enumerate(lines, 1):
        template_line = number + offset
        if template_line < skip_until:
            continue
        replaced = next((name for name, (start, _end, _value) in replacements.items() if start == template_line), None)
        if replaced is None:
            output.append(line)
            continue
        start, end, rendered = replacements[replaced]
        output.append(f"{replaced} = {rendered}")
        skip_until = end + 1
    return "\n".join(output) + "\n"


# Checks one setup destination without creating or modifying it, so an unwritable path is caught before any question
def _wizard_validate_destination(path, label):
    destination = Path(path).expanduser().resolve()
    if destination.exists() and destination.is_dir():
        raise ValueError(f"{label} must be a file path, not a directory")
    parent = nearest_existing_parent(destination)
    if not parent.is_dir():
        raise ValueError(f"{label} does not have a usable parent directory")
    if not os.access(str(parent), os.W_OK):
        raise ValueError(f"{label} is not writable through parent '{parent}'")
    return destination


# Resolves both setup destinations, refusing the disabled settings that leave nowhere to write
def _wizard_destinations(config_file=None, env_file=None):
    if config_file is not None and str(config_file).casefold() == "none":
        raise ValueError("--setup requires a config destination. Replace '--config-file none' with a writable path")
    if env_file is not None and str(env_file).casefold() == "none":
        raise ValueError("--setup requires a dotenv destination. Replace '--env-file none' with a writable path")
    config_path = Path(config_file).expanduser() if config_file is not None else Path.cwd() / DEFAULT_CONFIG_FILENAME
    env_path = Path(env_file).expanduser() if env_file is not None else Path.cwd() / ".env"
    return _wizard_validate_destination(config_path, "Configuration destination"), _wizard_validate_destination(env_path, "Dotenv destination")


# Confirms replacing an existing config before any question is asked, so a long run cannot end in a surprise
def _wizard_choose_config_destination(config_path, input_func=None):
    selected = Path(config_path)
    while selected.exists() and not _wizard_ask_yes_no(f"Configuration file '{selected}' exists. Replace it with a fresh configuration built from defaults and create a timestamped backup?", default=False, input_func=input_func):
        alternative = _wizard_ask_text("Another config destination or leave empty to cancel", input_func=input_func)
        if not alternative:
            return None
        try:
            selected = _wizard_validate_destination(alternative, "Configuration destination")
        except ValueError as exc:
            print(f"  {exc}.")
    return selected


# Queues one secret for the save step, asking first when the dotenv file already assigns it
def _wizard_queue_secret(state, key, value, input_func=None):
    if not value:
        return False
    if _dotenv_contains_key(state.env_path, key) and not _wizard_ask_yes_no(f"The dotenv file already contains {key}. Replace that value?", default=False, input_func=input_func):
        print(f"  Existing {key} will be retained without being displayed or rewritten.")
        return False
    state.secret_updates[key] = value
    return True


# Holds every wizard answer until the user explicitly saves, so nothing is written during questioning
class WizardSetupState:
    # Starts from the values already in effect, which become both the defaults and the revert target
    def __init__(self, config_path, env_path, baseline_values):
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        self.baseline_values = dict(baseline_values)
        self.config_values = dict(baseline_values)
        self.secret_updates = {}
        self.target = ""
        self.pending_vanity = ""
        self.persist_target = True


# The mail server settings the wizard collects, and how long its sign-in check waits for the server
WIZARD_SMTP_CONFIG_KEYS = ("SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_USER", "SENDER_EMAIL", "RECEIVER_EMAIL")
WIZARD_SMTP_TIMEOUT = 5

# The email and webhook alert settings the wizard offers, in the order the questions are asked
WIZARD_EMAIL_NOTIFICATION_KEYS = ("ACTIVE_INACTIVE_NOTIFICATION", "GAME_CHANGE_NOTIFICATION", "STATUS_NOTIFICATION", "NAME_CHANGE_NOTIFICATION", "ERROR_NOTIFICATION")
WIZARD_WEBHOOK_NOTIFICATION_KEYS = ("WEBHOOK_ACTIVE_NOTIFICATION", "WEBHOOK_INACTIVE_NOTIFICATION", "WEBHOOK_GAME_CHANGE_NOTIFICATION", "WEBHOOK_STATUS_NOTIFICATION", "WEBHOOK_NAME_CHANGE_NOTIFICATION", "WEBHOOK_ERROR_NOTIFICATION")


# Each editable section: internal name, menu label and description, then the keys reverted when it is re-entered
WIZARD_SECTIONS = (
    ("Target", "Target", "Change the Steam profile that is monitored.", ("TARGET_STEAM_ID",), ()),
    ("Polling", "Polling interval", "Change how often Steam is checked.", ("STEAM_CHECK_INTERVAL", "STEAM_ACTIVE_CHECK_INTERVAL"), ()),
    ("Authentication", "Authentication", "Enter the Steam Web API key again.", (), ("STEAM_API_KEY",)),
    ("Email", "Email notifications", "Change SMTP details and email events.", WIZARD_SMTP_CONFIG_KEYS + WIZARD_EMAIL_NOTIFICATION_KEYS, ("SMTP_PASSWORD",)),
    ("Webhook", "Webhook alerts", "Change Discord or ntfy details and events.", ("WEBHOOK_ENABLED", "WEBHOOK_PROVIDER", "NTFY_IMAGES") + WIZARD_WEBHOOK_NOTIFICATION_KEYS, ("WEBHOOK_URL", "NTFY_ACCESS_TOKEN")),
    ("Output", "Output files", "Change log and CSV output settings.", ("DISABLE_LOGGING", "CSV_FILE"), ()),
)


# Restores one section to the values setup started with and drops any secret it had queued
def _wizard_reset_section(state, config_keys, secret_keys):
    for key in config_keys:
        if key in state.baseline_values:
            state.config_values[key] = state.baseline_values[key]
        else:
            state.config_values.pop(key, None)
    for key in secret_keys:
        state.secret_updates.pop(key, None)


# Asks for the monitored profile, accepting every form people paste and storing one canonical Steam64 ID
def _wizard_collect_target_section(state, initial_target=None, input_func=None):
    state.pending_vanity = ""
    while True:
        answer = _wizard_ask_text("Steam profile URL or ID to monitor", default=str(initial_target or state.target or ""), required=True, input_func=input_func)
        try:
            steam64, vanity = normalize_steam_target(answer)
        except ValueError as exc:
            print(f"  {exc}")
            continue
        if steam64 is not None:
            state.target = str(steam64)
            break
        resolved = None
        if doctor_value_is_set(state.secret_updates.get("STEAM_API_KEY") or state.config_values.get("STEAM_API_KEY")):
            api_key = state.secret_updates.get("STEAM_API_KEY") or state.config_values.get("STEAM_API_KEY")
            try:
                resolved = resolve_steam_community_url(f"https://steamcommunity.com/id/{vanity}/", api_key)
            except ValueError as exc:
                print(f"  Could not resolve '{vanity}': {exc}")
        if resolved is not None:
            state.target = str(resolved)
            print(f"  Resolved '{vanity}' to Steam64 ID {resolved}.")
            break
        state.pending_vanity = vanity
        print(f"  '{vanity}' will be resolved after the Steam Web API key is set up.")
        break
    state.persist_target = _wizard_ask_yes_no("Persist this target in the generated config?", default=state.persist_target, input_func=input_func)
    _wizard_apply_target(state)


# Mirrors the settled target into the config values, so an unpersisted target is left out of the file
def _wizard_apply_target(state):
    state.config_values["TARGET_STEAM_ID"] = state.target if state.persist_target and state.target else ""


# Resolves a vanity target after authentication or asks for another target when resolution is unavailable
def _wizard_resolve_pending_target(state, input_func=None):
    while state.pending_vanity:
        vanity = state.pending_vanity
        api_key = state.secret_updates.get("STEAM_API_KEY") or state.config_values.get("STEAM_API_KEY")
        if doctor_value_is_set(api_key):
            try:
                resolved = resolve_steam_community_url(f"https://steamcommunity.com/id/{vanity}/", api_key)
                state.target = str(resolved)
                state.pending_vanity = ""
                print(f"  Resolved '{vanity}' to Steam64 ID {resolved}.")
                _wizard_apply_target(state)
                return
            except ValueError as exc:
                print(f"  Could not resolve '{vanity}': {exc}")
        else:
            print(f"  '{vanity}' cannot be resolved without a Steam Web API key.")
        print("  Enter another supported profile value.")
        _wizard_collect_target_section(state, input_func=input_func)


# Asks how often the tool checks, in whichever duration format the user prefers
def _wizard_collect_polling_section(state, input_func=None):
    state.config_values["STEAM_CHECK_INTERVAL"] = _wizard_ask_duration("Steam polling interval while offline (seconds or use s/m/h/d)", int(state.config_values.get("STEAM_CHECK_INTERVAL") or STEAM_CHECK_INTERVAL), input_func=input_func)
    state.config_values["STEAM_ACTIVE_CHECK_INTERVAL"] = _wizard_ask_duration("Steam polling interval while online (seconds or use s/m/h/d)", int(state.config_values.get("STEAM_ACTIVE_CHECK_INTERVAL") or STEAM_ACTIVE_CHECK_INTERVAL), input_func=input_func)


# Asks for the Steam Web API key through a hidden prompt and validates it against Steam before accepting it
def _wizard_collect_auth_section(state, input_func=None, getpass_func=None, validator=None):
    print(f"Create or view your Steam Web API key: {STEAM_API_KEY_REGISTRATION_URL}")
    existing = doctor_value_is_set(state.config_values.get("STEAM_API_KEY"))
    if existing and not _wizard_ask_yes_no("Replace the Steam Web API key already configured?", default=False, input_func=input_func):
        return
    validate = validate_steam_api_key if validator is None else validator
    while True:
        api_key = _wizard_ask_secret("Steam Web API key", getpass_func=getpass_func)
        if not api_key:
            # Monitoring cannot run without it, so leaving it unset has to be a decision rather than a fallthrough
            if not _wizard_offer_retry("Steam Web API key", "Nothing can be monitored until one is set", input_func=input_func):
                return
            continue
        if validate(api_key):
            state.secret_updates["STEAM_API_KEY"] = api_key
            print("  Steam accepted the key.")
            return
        print("  Steam rejected that key. Check it was copied in full.")
        # A key Steam keeps rejecting cannot be corrected from inside the loop, so the wizard must be leavable here too
        if not _wizard_offer_retry("Steam Web API key", input_func=input_func):
            return


# Switches every email alert off together, so an abandoned answer cannot leave half a mail server configured
def _wizard_disable_email(state):
    for key in WIZARD_EMAIL_NOTIFICATION_KEYS + ("STEAM_LEVEL_XP_NOTIFICATION", "FRIENDS_NOTIFICATION", "GAMES_LIBRARY_NOTIFICATION"):
        state.config_values[key] = False


# Signs in to the collected mail server without sending anything, so a refused login is caught during setup
def _wizard_verify_smtp(values, password):
    names = ("SMTP_HOST", "SMTP_PORT", "SMTP_SSL", "SMTP_USER", "SMTP_PASSWORD", "SENDER_EMAIL", "RECEIVER_EMAIL")
    previous = {name: globals()[name] for name in names}
    smtp_object = None
    try:
        globals().update(values)
        # A blank answer keeps the password already stored, which is the one the sign-in must then prove
        globals()["SMTP_PASSWORD"] = password or previous["SMTP_PASSWORD"]
        smtp_object = smtp_connect_and_login(SMTP_SSL, smtp_timeout=WIZARD_SMTP_TIMEOUT)
        return None
    except Exception as exc:
        return classify_recovery_error(exc, "email")
    finally:
        if smtp_object is not None:
            try:
                smtp_object.quit()
            except Exception:
                pass
        globals().update(previous)


# Reports the outcome of the sign-in check: True to continue, False to ask again, None to switch email off
def _wizard_smtp_sign_in_accepted(values, password, input_func=None):
    print("  Checking the sign-in with the mail server ...")
    advice = _wizard_verify_smtp(values, password)
    if advice is None:
        print("  The mail server accepted the sign-in. No email was sent.")
        return True
    print(f"  {advice.summary}: {advice.detail}" if advice.detail else f"  {advice.summary}")
    print(f"  To fix: {advice.fix}")
    if _wizard_offer_retry("mail server settings", input_func=input_func):
        return False
    if advice.retryable:
        # Being offline is the usual reason a correct setup fails here, so the answers are kept rather than discarded
        print("  The settings were kept without being checked. Run --doctor to check the sign-in again.")
        return True
    print("  Email notifications stay off until the mail server accepts the settings.")
    return None


# Reports whether one required mail server answer was abandoned, switching the channel off when it was
def _wizard_email_answer_missing(state, key):
    if state.config_values.get(key):
        return False
    print("  Email notifications stay off until every mail server setting is answered.")
    _wizard_disable_email(state)
    return True


# Asks whether to send email alerts and collects only the settings that choice needs
def _wizard_collect_email_section(state, input_func=None, getpass_func=None):
    if not _wizard_ask_yes_no("Configure email notifications?", default=False, input_func=input_func):
        _wizard_disable_email(state)
        return
    while True:
        state.config_values["SMTP_HOST"] = _wizard_ask_text("SMTP host", default=_wizard_default(state.config_values.get("SMTP_HOST")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SMTP_HOST"):
            return
        state.config_values["SMTP_PORT"] = _wizard_ask_positive_int("SMTP port", int(state.config_values.get("SMTP_PORT") or 587), input_func=input_func)
        state.config_values["SMTP_SSL"] = _wizard_ask_yes_no("Enable TLS/SSL for SMTP?", default=bool(state.config_values.get("SMTP_SSL", True)), input_func=input_func)
        state.config_values["SMTP_USER"] = _wizard_ask_text("SMTP username", default=_wizard_default(state.config_values.get("SMTP_USER")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SMTP_USER"):
            return
        state.config_values["SENDER_EMAIL"] = _wizard_ask_text("Sender email", default=_wizard_default(state.config_values.get("SENDER_EMAIL")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "SENDER_EMAIL"):
            return
        state.config_values["RECEIVER_EMAIL"] = _wizard_ask_text("Receiver email", default=_wizard_default(state.config_values.get("RECEIVER_EMAIL")), required=True, input_func=input_func)
        if _wizard_email_answer_missing(state, "RECEIVER_EMAIL"):
            return
        password = _wizard_ask_secret("SMTP password", getpass_func=getpass_func)
        if password:
            _wizard_queue_secret(state, "SMTP_PASSWORD", password, input_func=input_func)
        outcome = _wizard_smtp_sign_in_accepted({name: state.config_values[name] for name in WIZARD_SMTP_CONFIG_KEYS}, password, input_func=input_func)
        if outcome is None:
            _wizard_disable_email(state)
            return
        if outcome:
            break
    preset = _wizard_ask_choice("Which email notifications should be enabled?", [
        ("Status and errors, recommended", "Online, offline, game change and error notifications."),
        ("Every supported event", "Enables all email notification types."),
        ("Custom", "Choose each notification type separately."),
    ], input_func=input_func)
    if preset == 0:
        selected = {"ACTIVE_INACTIVE_NOTIFICATION": True, "GAME_CHANGE_NOTIFICATION": True, "STATUS_NOTIFICATION": False, "NAME_CHANGE_NOTIFICATION": False, "ERROR_NOTIFICATION": True}
    elif preset == 1:
        selected = {name: True for name in WIZARD_EMAIL_NOTIFICATION_KEYS}
    else:
        print()
        questions = (
            ("ACTIVE_INACTIVE_NOTIFICATION", "Email when the user goes online or offline?"),
            ("GAME_CHANGE_NOTIFICATION", "Email when the user starts, changes or stops a game?"),
            ("STATUS_NOTIFICATION", "Email on every status change?"),
            ("NAME_CHANGE_NOTIFICATION", "Email when the display name changes?"),
            ("ERROR_NOTIFICATION", "Email on monitoring errors?"),
        )
        selected = {name: _wizard_ask_yes_no(question, default=False, input_func=input_func) for name, question in questions}
    state.config_values.update(selected)


# Switches the channel and every alert it owns off together, so a half-configured webhook cannot be written
def _wizard_disable_webhook(state):
    state.config_values["WEBHOOK_ENABLED"] = False
    state.config_values["NTFY_IMAGES"] = False
    state.config_values.update({name: False for name in WIZARD_WEBHOOK_NOTIFICATION_KEYS})


# Asks whether to send webhook alerts and collects the provider, the hidden URL and the alert choices
def _wizard_collect_webhook_section(state, input_func=None, getpass_func=None):
    if not _wizard_ask_yes_no("Set up webhook alerts (Discord, ntfy etc.)?", default=False, input_func=input_func):
        _wizard_disable_webhook(state)
        return
    provider_choice = _wizard_ask_choice("Which webhook service should receive alerts?", [
        ("Discord", "Sends a Discord embed to one channel webhook."),
        ("ntfy", "Sends a native notification to one ntfy topic URL."),
    ], input_func=input_func)
    provider = "discord" if provider_choice == 0 else "ntfy"
    state.config_values["WEBHOOK_PROVIDER"] = provider
    if provider == "discord":
        print("  In Discord: Edit Channel > Integrations > Webhooks > New Webhook > Copy Webhook URL.")
    else:
        print("  In ntfy: choose a hard-to-guess topic. Paste its name for ntfy.sh or use the complete HTTPS URL for a self-hosted server.")
    replace_webhook = True
    if _wizard_existing_secret("WEBHOOK_URL", state.env_path):
        choice = _wizard_ask_choice("Which webhook URL should be used?", [
            ("Keep the saved URL", "Keeps the private value without displaying or changing it."),
            ("Paste a new URL", "Uses a hidden prompt then saves the new private value in .env."),
        ], input_func=input_func)
        replace_webhook = choice == 1
    if replace_webhook:
        while True:
            answer = _wizard_ask_secret("Paste the Discord webhook URL" if provider == "discord" else "Paste the ntfy topic URL or ntfy.sh topic name", getpass_func=getpass_func)
            webhook_url = normalize_ntfy_topic_url(answer) if provider == "ntfy" else answer.strip()
            if validate_webhook_url(webhook_url):
                state.secret_updates["WEBHOOK_URL"] = webhook_url
                break
            # Nothing can be delivered without a destination, so giving up has to stay reachable from the prompt
            if not webhook_url:
                if not _wizard_offer_retry("webhook URL", "Webhook alerts stay off until one is set", input_func=input_func):
                    _wizard_disable_webhook(state)
                    return
                continue
            if provider == "ntfy":
                print("  Enter a complete HTTPS ntfy topic URL or a topic name containing up to 64 letters, numbers, dashes or underscores.")
            else:
                print("  That does not look like a complete HTTPS webhook URL. Copy it from the webhook service and try again.")
            if not _wizard_offer_retry("webhook URL", input_func=input_func):
                _wizard_disable_webhook(state)
                return
    if provider == "ntfy":
        _wizard_collect_ntfy_access_token(state, input_func=input_func, getpass_func=getpass_func)
    state.config_values["NTFY_IMAGES"] = _wizard_collect_ntfy_images(input_func=input_func) if provider == "ntfy" else False
    state.config_values["WEBHOOK_ENABLED"] = True
    preset = _wizard_ask_choice("Which webhook alerts should be sent?", [
        ("Status and errors, recommended", "Alerts when the user goes online, goes offline, changes game or monitoring has a problem."),
        ("Every supported alert", "Also sends every-status-change and display-name alerts."),
        ("Custom", "Choose each webhook alert separately."),
    ], input_func=input_func)
    if preset == 0:
        selected = {"WEBHOOK_ACTIVE_NOTIFICATION": True, "WEBHOOK_INACTIVE_NOTIFICATION": True, "WEBHOOK_GAME_CHANGE_NOTIFICATION": True, "WEBHOOK_STATUS_NOTIFICATION": False, "WEBHOOK_NAME_CHANGE_NOTIFICATION": False, "WEBHOOK_ERROR_NOTIFICATION": True}
    elif preset == 1:
        selected = {name: True for name in WIZARD_WEBHOOK_NOTIFICATION_KEYS}
    else:
        print()
        questions = (
            ("WEBHOOK_ACTIVE_NOTIFICATION", "Send a webhook alert when the user goes online?"),
            ("WEBHOOK_INACTIVE_NOTIFICATION", "Send a webhook alert when the user goes offline?"),
            ("WEBHOOK_GAME_CHANGE_NOTIFICATION", "Send a webhook alert when the user starts, changes or stops a game?"),
            ("WEBHOOK_STATUS_NOTIFICATION", "Send a webhook alert on every status change?"),
            ("WEBHOOK_NAME_CHANGE_NOTIFICATION", "Send a webhook alert when the display name changes?"),
            ("WEBHOOK_ERROR_NOTIFICATION", "Send a webhook alert when monitoring has a problem?"),
        )
        selected = {name: _wizard_ask_yes_no(question, default=False, input_func=input_func) for name, question in questions}
    state.config_values.update(selected)


# Collects an optional ntfy access token without displaying it or contacting the service
def _wizard_collect_ntfy_access_token(state, input_func=None, getpass_func=None):
    existing_token = _wizard_existing_secret("NTFY_ACCESS_TOKEN", state.env_path)
    if existing_token:
        choice = _wizard_ask_choice("Which ntfy authentication should be used?", [
            ("Keep the saved access token", "Keeps the private value without displaying or changing it."),
            ("Paste a new access token", "Uses a hidden prompt then saves the replacement in .env."),
            ("Do not use an access token", "Disables the saved token. Authentication in the topic URL still works."),
        ], input_func=input_func)
        if choice == 0:
            return
        if choice == 2:
            state.secret_updates["NTFY_ACCESS_TOKEN"] = ""
            print("  The saved ntfy access token will be disabled without being displayed.")
            return
    elif not _wizard_ask_yes_no("Authenticate this ntfy topic with a separate access token?", default=False, input_func=input_func):
        print("  No separate access token selected. Authentication already present in the topic URL still works.")
        return
    while True:
        token = _wizard_ask_secret("Paste the ntfy access token only", getpass_func=getpass_func)
        if not token or ("\r" not in token and "\n" not in token and not token.casefold().startswith(("bearer ", "basic "))):
            if token:
                state.secret_updates["NTFY_ACCESS_TOKEN"] = token
            return
        print("  Paste only the access token without a Bearer or Basic prefix.")
        if not _wizard_offer_retry("ntfy access token", input_func=input_func):
            return


# Offers artwork attachments for ntfy alerts, which need the optional Pillow package
def _wizard_collect_ntfy_images(input_func=None):
    if not NTFY_IMAGES_AVAILABLE:
        print("  Artwork attachments need the optional Pillow package, which is not installed.")
    if not _wizard_ask_yes_no("Attach game and avatar artwork to ntfy alerts?", default=NTFY_IMAGES_AVAILABLE, input_func=input_func):
        return False
    if NTFY_IMAGES_AVAILABLE:
        return True
    print(f"  Keeping ntfy alerts text-only. Install Pillow with '{ntfy_images_install_command()}' then set NTFY_IMAGES to True.")
    return False


# Reports whether a usable secret is already saved, without reading its value into the transcript
def _wizard_existing_secret(key, env_path):
    value = None
    path = Path(env_path)
    if path.is_file():
        try:
            from dotenv import dotenv_values
            value = dotenv_values(path, interpolate=False).get(key)
        except Exception:
            value = None
    if value is None:
        value = os.environ.get(key)
    return doctor_value_is_set(value)


# Runs one editable section again after resetting only the keys it owns
def _wizard_edit_setup_section(state, input_func=None, getpass_func=None):
    options = [(label, description) for _name, label, description, _config_keys, _secret_keys in WIZARD_SECTIONS]
    options.append(("Return to summary", "Keep every current answer."))
    choice = _wizard_ask_choice("Which setup section should be changed?", options, input_func=input_func)
    if choice == len(WIZARD_SECTIONS):
        return
    name, _label, _description, config_keys, secret_keys = WIZARD_SECTIONS[choice]
    _wizard_reset_section(state, config_keys, secret_keys)
    if name == "Target":
        state.target = ""
    print()
    collectors = {
        "Target": lambda: _wizard_collect_target_section(state, input_func=input_func),
        "Polling": lambda: _wizard_collect_polling_section(state, input_func=input_func),
        "Authentication": lambda: _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func),
        "Email": lambda: _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func),
        "Webhook": lambda: _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func),
        "Output": lambda: _wizard_collect_output_section(state, input_func=input_func),
    }
    collectors[name]()
    if name in ("Target", "Authentication"):
        _wizard_resolve_pending_target(state, input_func=input_func)


# The theme part each setup summary row draws its value in, for rows whose value has a known kind
WIZARD_SUMMARY_VALUE_STYLES = {"Target": "username", "Polling interval while offline": "duration", "Polling interval while online": "duration"}


# Colours one setup summary value from its row label
def _wizard_summary_value(label, value):
    text = str(value)
    part = WIZARD_SUMMARY_VALUE_STYLES.get(label)
    if part:
        return colorize(part, text)
    if text.startswith("enabled") or text == "complete":
        return colorize("boolean_true", text)
    if text in ("disabled", "incomplete"):
        return colorize("boolean_false", text)
    return text


# Prints one aligned label and value block, so every summary row lines up
def _wizard_print_summary_rows(rows):
    width = max(len(label) for label, _ in rows) + 1
    for label, value in rows:
        print(f"  {(label + ':'):<{width}} {_wizard_summary_value(label, value)}")


# Collects the log and CSV output destinations monitoring would write
def _wizard_collect_output_section(state, input_func=None):
    state.config_values["DISABLE_LOGGING"] = not _wizard_ask_yes_no("Write the normal per-target log file?", default=not bool(state.config_values.get("DISABLE_LOGGING")), input_func=input_func)
    state.config_values["CSV_FILE"] = _wizard_ask_text("Optional CSV output path (blank disables it)", default=str(state.config_values.get("CSV_FILE") or ""), input_func=input_func)


# Shows everything that is about to be written, by name and never by secret value
def _wizard_print_setup_summary(state):
    email_labels = {"ACTIVE_INACTIVE_NOTIFICATION": "online/offline", "GAME_CHANGE_NOTIFICATION": "game", "STATUS_NOTIFICATION": "every status change", "NAME_CHANGE_NOTIFICATION": "name change", "ERROR_NOTIFICATION": "errors"}
    webhook_labels = {"WEBHOOK_ACTIVE_NOTIFICATION": "online", "WEBHOOK_INACTIVE_NOTIFICATION": "offline", "WEBHOOK_GAME_CHANGE_NOTIFICATION": "game", "WEBHOOK_STATUS_NOTIFICATION": "every status change", "WEBHOOK_NAME_CHANGE_NOTIFICATION": "name change", "WEBHOOK_ERROR_NOTIFICATION": "errors"}
    enabled_email = [email_labels[name] for name in WIZARD_EMAIL_NOTIFICATION_KEYS if state.config_values.get(name)]
    enabled_webhooks = [webhook_labels[name] for name in WIZARD_WEBHOOK_NOTIFICATION_KEYS if state.config_values.get(name)] if state.config_values.get("WEBHOOK_ENABLED") else []
    api_key_set = "STEAM_API_KEY" in state.secret_updates or doctor_value_is_set(state.config_values.get("STEAM_API_KEY"))
    webhook_state = f"enabled ({webhook_provider_display_name(state.config_values.get('WEBHOOK_PROVIDER'))})" if state.config_values.get("WEBHOOK_ENABLED") else "disabled"
    rows = [
        ("Target", state.target or "not set"),
        ("Persist target", "yes" if state.persist_target else "no"),
        ("Polling interval while offline", _wizard_format_duration(int(state.config_values.get("STEAM_CHECK_INTERVAL") or 0))),
        ("Polling interval while online", _wizard_format_duration(int(state.config_values.get("STEAM_ACTIVE_CHECK_INTERVAL") or 0))),
        ("Authentication status", "complete" if api_key_set else "incomplete"),
        ("Email", "enabled" if enabled_email else "disabled"),
        ("Email notifications", ", ".join(enabled_email) if enabled_email else "none"),
        ("Webhook", webhook_state),
        ("Webhook alerts", ", ".join(enabled_webhooks) if enabled_webhooks else "none"),
        ("Output log", "disabled" if state.config_values.get("DISABLE_LOGGING") else "enabled"),
        ("CSV output", state.config_values.get("CSV_FILE") or "disabled"),
        ("Config destination", state.config_path),
        ("Dotenv destination", state.env_path),
        ("Install method", install_method_display_name()),
    ]
    print(colorize("header", "\nSetup summary\n"))
    _wizard_print_summary_rows(rows)


# Loops on the summary until the user saves or explicitly discards, so nothing is written by accident
def _wizard_review_setup(state, input_func=None, getpass_func=None):
    while True:
        _wizard_print_setup_summary(state)
        action = _wizard_ask_choice("What would you like to do?", [
            ("Save settings", "Write the displayed settings to the selected files."),
            ("Review or change settings", "Edit one section without losing the other answers."),
            ("Discard answers and exit", "Leave the destination files unchanged."),
        ], input_func=input_func)
        if action == 0:
            return True
        if action == 1:
            _wizard_edit_setup_section(state, input_func=input_func, getpass_func=getpass_func)
            continue
        print()
        if _wizard_ask_yes_no("Discard all entered answers and exit?", default=False, input_func=input_func):
            return False
        print("  Setup answers retained.")


# Writes the configuration atomically, backing up whatever was there first
def write_config_file(destination, content):
    destination_path = Path(destination).expanduser()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = create_timestamped_backup(destination_path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", prefix=f".{destination_path.name}.", suffix=".tmp", dir=str(destination_path.parent), delete=False) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(str(temporary_path), str(destination_path))
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return {"path": str(destination_path), "backup_path": backup_path}


# Prints where setup will write and which install method the printed commands are written for
def _wizard_print_setup_destinations(method, config_path, env_path):
    print(f"Detected install method: {colorize('username', method)}")
    print(f"Configuration:          {config_path}")
    print(f"Dotenv:                 {env_path}\n")


# Runs the guided setup, holding every answer until the user saves
def run_setup_wizard(initial_target=None, config_file=None, env_file=None, input_func=None, getpass_func=None, interactive=None):
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    if not terminal_is_interactive:
        print("The setup wizard needs an interactive terminal (TTY).")
        print("Run --setup from an interactive shell or use --generate-config and edit the files manually.")
        print(f"Guide: {QUICK_START_GUIDE_URL}")
        return 1

    try:
        config_path, env_path = _wizard_destinations(config_file, env_file)
    except ValueError as exc:
        print_recovery_error(exc, context="file.unwritable", detail=str(exc))
        return 1

    print(colorize("header", "Setup Wizard\n"))
    print("This asks a few questions and writes a ready-to-run configuration.")
    _wizard_print_default_guidance()
    print("Secrets go to the dotenv file. Non-secret settings go to the config file.")
    print()
    _wizard_print_setup_destinations(install_method(), config_path, env_path)

    baseline_values = {name: value for name, value in globals().items() if name in _config_allowed_names()}
    state = WizardSetupState(config_path, env_path, baseline_values)
    state.config_values["DOTENV_FILE"] = str(env_path)

    try:
        # Asked before anything else, so a config that has to be replaced is agreed to rather than discovered at Save
        config_existed = Path(config_path).exists()
        chosen_config = _wizard_choose_config_destination(config_path, input_func=input_func)
        if chosen_config is None:
            print("\n" + colorize("warning", "Setup cancelled. Destination files were not changed."))
            return 1
        state.config_path = chosen_config
        # A destination nothing was asked about printed nothing, so the separator would leave a blank gap
        if config_existed:
            print()
        _wizard_collect_target_section(state, initial_target, input_func=input_func)
        print()
        _wizard_collect_polling_section(state, input_func=input_func)
        print()
        _wizard_collect_auth_section(state, input_func=input_func, getpass_func=getpass_func)
        _wizard_resolve_pending_target(state, input_func=input_func)
        print()
        _wizard_collect_email_section(state, input_func=input_func, getpass_func=getpass_func)
        print()
        _wizard_collect_webhook_section(state, input_func=input_func, getpass_func=getpass_func)
        print()
        _wizard_collect_output_section(state, input_func=input_func)
        if not _wizard_review_setup(state, input_func=input_func, getpass_func=getpass_func):
            print("\n" + colorize("warning", "Setup cancelled. Destination files were not changed."))
            return 1
    except (EOFError, KeyboardInterrupt):
        print(colorize("warning", "Setup cancelled. Destination files were not changed."))
        return 1

    # Everything above only filled the state, so this is the first and only point anything reaches disk
    try:
        config_result = write_config_file(state.config_path, generate_config_with_current_values(state.config_values))
    except Exception as exc:
        print_recovery_error(exc, context="file", detail=f"Could not write the configuration to '{state.config_path}'")
        return 1
    secret_result = None
    if state.secret_updates:
        try:
            secret_result = update_dotenv_file(state.env_path, state.secret_updates)
        except Exception as exc:
            print_recovery_error(exc, context="file", detail=f"Could not write secrets to '{state.env_path}'")
            return 1

    print(colorize("header", "\nSaved files\n"))
    print(f"  Configuration: {config_result['path']}")
    if config_result["backup_path"]:
        print(f"  Backup:        {config_result['backup_path']}")
    if secret_result:
        print(f"  {'Secrets:' if state.secret_updates else 'Dotenv:':<15}{secret_result['path']}")
        if secret_result.get("backup_path"):
            print(f"  Backup:        {secret_result['backup_path']}")

    doctor_offered = bool(state.target)
    doctor_exit = None
    if doctor_offered:
        print()
    try:
        if doctor_offered and _wizard_ask_yes_no("Run doctor now? It writes no files and offers real delivery tests only with separate approval.", default=True, input_func=input_func):
            print()
            _wizard_apply_saved_values(state, env_path=state.env_path if secret_result else None)
            doctor_exit = run_doctor(target_value=int(state.target), config_path=str(state.config_path), env_path=str(state.env_path) if secret_result else None)
    except (EOFError, KeyboardInterrupt):
        # The files are already written, so an interrupt here only skips the optional check
        print(colorize("warning", "Setup is saved. Use the commands below when ready."))

    env_argument = str(state.env_path) if secret_result else ""
    # A persisted target is already in the config file, so the printed commands stay short
    target_arguments = [] if state.persist_target or not state.target else [state.target]
    print(colorize("header", "\nNext steps\n"))
    _wizard_print_command("Check setup again:", render_command(["--doctor"] + target_arguments, config_path=str(state.config_path), env_path=env_argument))
    start_label = "After Doctor passes, start monitoring:" if doctor_exit not in (None, 0) else "Start monitoring:"
    _wizard_print_command(start_label, render_command(target_arguments, config_path=str(state.config_path), env_path=env_argument))
    print(f"Guide: {colorize('link', QUICK_START_GUIDE_URL)}\n")

    api_key_ready = "STEAM_API_KEY" in state.secret_updates or doctor_value_is_set(state.config_values.get("STEAM_API_KEY"))
    try:
        start_monitoring = bool(state.target and api_key_ready and _wizard_ask_yes_no("Start monitoring now? Monitoring will continue until Ctrl+C.", default=True, input_func=input_func))
    except (EOFError, KeyboardInterrupt):
        # The files are already written, so an interrupt here only skips the optional launch
        print(colorize("warning", "Setup is saved. Start monitoring with the command above when ready."))
        return 0
    if start_monitoring:
        launch_arguments = _wizard_local_command_args(target=None if state.persist_target else state.target, config_path=state.config_path, env_path=state.env_path if secret_result else None)
        sys.stdout.flush()
        return _wizard_launch_monitor(launch_arguments)
    return 0


# Puts the values setup just saved into effect, so doctor checks the written files instead of the pre-setup state
def _wizard_apply_saved_values(state, env_path=None):
    # Config values first: they carry the unset placeholders for every secret, which would otherwise
    # overwrite the secrets applied below and make doctor report a working setup as unconfigured
    globals().update(state.config_values)
    if env_path:
        try:
            reload_dotenv_secrets(str(env_path))
        except Exception:
            # Reading the file back needs python-dotenv, so the entered values are applied directly below
            pass
    load_secrets_from_environment()
    # Secrets exported before startup keep winning here, exactly as they will when monitoring runs
    for key, value in state.secret_updates.items():
        if key not in EXPORTED_SECRET_KEYS and not doctor_value_is_set(globals().get(key)):
            globals()[key] = value


# Builds the exact local command that starts this monitor, used when setup offers to launch it
def _wizard_local_command_args(target=None, config_path=None, env_path=None):
    executable = sys.executable or ("python" if system() == "Windows" else "python3")
    arguments = [executable, "-m", "steam_monitor"] if install_method() == INSTALL_METHOD_PYPI else [executable, str(Path(__file__).resolve())]
    if target:
        arguments.append(str(target))
    if config_path:
        arguments.extend(["--config-file", str(config_path)])
    if env_path:
        arguments.extend(["--env-file", str(env_path)])
    return arguments


# Hands the terminal to the monitor, replacing this process where the platform allows it
def _wizard_launch_monitor(arguments):
    command = [str(argument) for argument in arguments]
    if system() == "Windows":
        try:
            return subprocess.run(command, check=False).returncode
        except KeyboardInterrupt:
            return 0
    os.execv(command[0], command)
    return 0


# Prints one labelled command on its own indented line, the shared shape across these tools
def _wizard_print_command(label, command, suffix=""):
    print(label)
    print(f"    {colorize('section', command)}{colorize('info', suffix) if suffix else ''}\n")


# Prints the commands a newcomer needs next, instead of an argparse usage error
def print_welcome_screen(input_func=None, interactive=None):
    terminal_is_interactive = sys.stdin.isatty() if interactive is None else interactive
    print(f"For <steam_target>, use a {STEAM_TARGET_FORMS}.\n")
    _wizard_print_command("Quickest start (already configured):", render_command(["<steam_target>"], include_paths=False))
    setup_suffix = "   (or just answer Y below)" if terminal_is_interactive else ""
    _wizard_print_command("Easiest start (guided setup wizard):", render_command(["--setup"], include_paths=False), setup_suffix)
    _wizard_print_command("Check setup before monitoring:", render_command(["--doctor", "<steam_target>"], include_paths=False))
    _wizard_print_command("Show profile details and exit:", render_command(["-i", "<steam_target>"], include_paths=False))
    print(f"Full options: {colorize('section', render_command(['--help'], include_paths=False))}")
    print(f"\nGuide:        {colorize('link', QUICK_START_GUIDE_URL)}\n")
    if terminal_is_interactive:
        try:
            start_setup = _wizard_ask_yes_no("Run the guided setup wizard now?", default=True, input_func=input_func)
        except (EOFError, KeyboardInterrupt):
            # This prompt sits outside the wizard, which handles its own interrupts
            print(colorize("warning", "Setup cancelled."))
            return 1
        if start_setup:
            print()
            return run_setup_wizard()
    # Without a terminal there was nothing to answer, so a bare invocation stays the usage error it was
    return 0 if terminal_is_interactive else 1


# One startup summary setting, routed independently to the concise view, the verbose view and the log file
StartupSummaryRow = namedtuple("StartupSummaryRow", ["label", "value", "concise", "full", "log"])
StartupSummaryRow.__new__.__defaults__ = (False, True, True)


# Formats one summary row with an aligned value column, wrapping only the rollup that grows long
def format_startup_summary_row(row):
    prefix = f"* {(row.label + ':'):<30}"
    if row.label in ("Notifications (email)", "Notifications (webhook)"):
        return textwrap.fill(str(row.value), width=100, initial_indent=prefix, subsequent_indent=" " * len(prefix), break_long_words=False, break_on_hyphens=False) + "\n"
    return f"{prefix}{row.value}\n"


# Prints the summary, showing the concise rows unless the full view was asked for. The log file always keeps
# the complete set, so a bug report made from a log carries every effective setting whatever the terminal showed
def emit_startup_summary(rows, show_full=False, stream=None):
    destination = sys.stdout if stream is None else stream
    # A stream that does not split its output has no log file to hold the full view, so those writes go nowhere
    write_log = getattr(destination, "log_only", lambda line: None)
    write_terminal = getattr(destination, "terminal_only", None)
    if write_terminal is None:
        write_terminal = destination.write
    for row in rows:
        line = format_startup_summary_row(row)
        if row.full and row.log:
            write_log(line)
        if row.full if show_full else row.concise:
            write_terminal(line)
    write_log("\n")
    write_terminal("\n")
    destination.flush()


# Builds every startup summary row, deciding per row whether it belongs in the concise view, the full view and the log
def build_startup_summary(target=None, config_path=None, env_path=None, log_path=None):
    dotenv_secrets, environment_secrets, config_secrets, command_line_secrets = doctor_secret_sources(env_path)
    from_dotenv, from_environment, from_config, from_command_line = sorted(dotenv_secrets), sorted(environment_secrets), sorted(config_secrets), sorted(command_line_secrets)
    logging_enabled = bool(log_path) and not DISABLE_LOGGING
    output_state = str(log_path) if logging_enabled else "Terminal only (logging disabled)"
    rows = [
        StartupSummaryRow("Target", str(target) if target else "None", concise=True),
        StartupSummaryRow("Polling intervals", f"[offline: {display_time(STEAM_CHECK_INTERVAL)}] [online: {display_time(STEAM_ACTIVE_CHECK_INTERVAL)}]", concise=True),
        StartupSummaryRow("Notifications (email)", _startup_notification_state(_startup_email_notification_categories()), concise=True),
        StartupSummaryRow("Notifications (webhook)", _startup_notification_state(_startup_webhook_notification_categories()), concise=True),
        StartupSummaryRow("Output", output_state, concise=True, full=False, log=False),
        StartupSummaryRow("Output logging", str(log_path) if logging_enabled else "Disabled"),
        StartupSummaryRow("Config", str(config_path) if config_path else "None", concise=True),
        StartupSummaryRow("Dotenv", str(env_path) if env_path else "None", concise=True),
        # Each tracked feature earns a concise row only when it is actually switched on
        StartupSummaryRow("Level/XP tracking", str(STEAM_LEVEL_XP_CHECK), concise=bool(STEAM_LEVEL_XP_CHECK)),
        StartupSummaryRow("Friends tracking", str(FRIENDS_CHECK), concise=bool(FRIENDS_CHECK)),
        StartupSummaryRow("Games tracking", str(GAMES_LIBRARY_CHECK), concise=bool(GAMES_LIBRARY_CHECK)),
        StartupSummaryRow("Liveness output", display_time(LIVENESS_CHECK_INTERVAL) if LIVENESS_CHECK_INTERVAL else "Disabled", concise=bool(LIVENESS_CHECK_INTERVAL)),
        StartupSummaryRow("CSV output", CSV_FILE or "Disabled", concise=bool(CSV_FILE)),
        StartupSummaryRow("Profile CSV output", PROFILE_CSV_FILE or "Disabled", concise=bool(PROFILE_CSV_FILE)),
        StartupSummaryRow("Terminal truncation", f"{TRUNCATE_CHARS} chars" if TRUNCATE_CHARS else "Disabled", concise=bool(TRUNCATE_CHARS)),
        StartupSummaryRow("Install method", install_method_display_name()),
        StartupSummaryRow("Secrets from dotenv", ", ".join(from_dotenv) if from_dotenv else "None"),
        StartupSummaryRow("Secrets from environment", ", ".join(from_environment) if from_environment else "None"),
        StartupSummaryRow("Secrets from config file", ", ".join(from_config) if from_config else "None"),
        StartupSummaryRow("Secrets from command line", ", ".join(from_command_line) if from_command_line else "None"),
        StartupSummaryRow("TLS verification", "On" if VERIFY_SSL else "Off, server certificates are not checked", concise=not VERIFY_SSL),
        StartupSummaryRow("ASCII log separators", f"{ascii_log_separators_enabled()} (mode: {ASCII_LOG_SEPARATORS})"),
        # The resolved state, not the setting: colour also switches itself off when the output is not a terminal
        StartupSummaryRow("Coloured output", f"{COLOR_ENABLED} (setting: {COLORED_OUTPUT})"),
        StartupSummaryRow("Verbose mode", str(VERBOSE_MODE), concise=bool(VERBOSE_MODE)),
        StartupSummaryRow("Debug mode", str(DEBUG_MODE), concise=bool(DEBUG_MODE)),
        # Points at the two modes for a reader who does not know they exist, so the full view drops it
        StartupSummaryRow("More details", "use --verbose or --debug", concise=True, full=False, log=False),
    ]
    return rows


# Renders the --help examples: one heading per task, then a comment and the command it describes
def render_help_examples(groups, guide_url):
    blocks = []
    for title, entries in groups:
        block = [f"{title}:"]
        for comment, command in entries:
            if len(block) > 1:
                block.append("")
            block.extend(f"  # {line}" for line in comment.split("\n"))
            if command:
                block.append(f"  {command}")
        blocks.append("\n".join(block))
    return "Examples:\n\n" + "\n\n".join(blocks) + f"\n\nGuide: {guide_url}\n"


# Returns the --help epilog, listing the commands worth knowing rather than every command there is
def help_examples():
    prefix = render_command(include_paths=False)
    groups = (
        ("Getting started", (
            ("Guided setup, recommended for the first run", f"{prefix} --setup"),
            ("Or save the Steam Web API key through a hidden prompt", f"{prefix} --set-steam-api-key"),
            ("Check the setup before relying on it", f"{prefix} --doctor <steam_target>"),
            ("Start monitoring", f"{prefix} <steam_target>"),
        )),
        ("Notifications", (
            ("Email when the user goes online or offline, and on game changes", f"{prefix} <steam_target> -a -g"),
            ("Send one test email", f"{prefix} --send-test-email"),
            ("Send one test webhook", f"{prefix} --send-test-webhook"),
        )),
        ("Information and diagnostics", (
            ("Show detailed profile information and exit", f"{prefix} -i <steam_target>"),
            ("Trace what the tool is doing", f"{prefix} <steam_target> --debug"),
        )),
    )
    return render_help_examples(groups, QUICK_START_GUIDE_URL)


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


# Signal handler for SIGVTALRM allowing to switch display name changes notifications
def toggle_name_change_notifications_signal_handler(sig, frame):
    global NAME_CHANGE_NOTIFICATION
    NAME_CHANGE_NOTIFICATION = not NAME_CHANGE_NOTIFICATION
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [display name changes = {NAME_CHANGE_NOTIFICATION}]")
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
    global WEBHOOK_PROVIDER
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")

    # disable autoscan if DOTENV_FILE set to none
    if DOTENV_FILE and DOTENV_FILE.lower() == 'none':
        env_path = None
    else:
        # reload .env if python-dotenv is installed
        try:
            from dotenv import find_dotenv
            if DOTENV_FILE:
                env_path = DOTENV_FILE
            else:
                env_path = find_dotenv()
            if env_path:
                reload_dotenv_secrets(env_path)
            else:
                print("* No .env file found, reloading exported environment variables only")
        except ImportError:
            env_path = None
            print("* python-dotenv not installed, reloading exported environment variables only")

    webhook_url_changed = False
    sources = secret_sources(env_path)
    for secret, changed in load_secrets_from_environment():
        if not changed:
            continue
        if secret == "WEBHOOK_URL":
            webhook_url_changed = True
        print(f"* Reloaded {secret} from {sources.get(secret, 'environment')}")
    if webhook_url_changed:
        detected_provider = detect_webhook_provider(WEBHOOK_URL)
        if detected_provider and detected_provider != normalized_webhook_provider():
            WEBHOOK_PROVIDER = detected_provider
            print(f"* Updated webhook provider to {detected_provider}")

    print_cur_ts("Timestamp:\t\t\t")


# Returns the --config-file value straight from argv, needed before argparse has run
def early_config_file_argument(arguments=None):
    values = list(sys.argv[1:] if arguments is None else arguments)
    for index, argument in enumerate(values):
        if argument == "--config-file" and index + 1 < len(values):
            return values[index + 1]
        if argument.startswith("--config-file="):
            return argument.split("=", 1)[1]
    return None


# Applies the terminal settings needed before argument parsing, leaving any failure to normal config loading
def apply_early_output_config():
    global CLEAR_SCREEN, COLORED_OUTPUT
    try:
        cli_path = early_config_file_argument()
        if cli_path is not None and cli_path.casefold() == "none":
            return
        expanded_path = os.path.expanduser(cli_path) if cli_path else None
        config_path = find_config_file(expanded_path)
        if not config_path:
            return
        values = parse_config_content(Path(config_path).read_text(encoding="utf-8"), str(config_path))
    except (MemoryError, OSError, RecursionError, SyntaxError, UnicodeError, ValueError):
        return
    if isinstance(values.get("CLEAR_SCREEN"), bool):
        CLEAR_SCREEN = values["CLEAR_SCREEN"]
    if isinstance(values.get("COLORED_OUTPUT"), bool):
        COLORED_OUTPUT = values["COLORED_OUTPUT"]


# Keeps argparse from colouring its own help, so the help screen is coloured by this tool alone and --no-color is
# not left with a second palette to silence. From Python 3.14 argparse colours the help by default on a terminal
def argparse_color_kwargs() -> dict[str, Any]:
    return {"color": False} if sys.version_info >= (3, 14) else {}


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


# Settings an older version wrote that this version no longer defines, ignored instead of rejected
RETIRED_CONFIG_SETTINGS = frozenset(())

# Settings the template ships commented out so the built-in default applies, still accepted from a config file
COMMENTED_CONFIG_SETTINGS = frozenset({"COLOR_THEME"})


# Collects the setting names the built-in configuration template defines
def _config_allowed_names():
    template_tree = ast.parse(CONFIG_BLOCK, "<built-in-config>", "exec")
    return frozenset(statement.targets[0].id for statement in template_tree.body if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name)) | COMMENTED_CONFIG_SETTINGS


# Parses allowlisted literal config assignments without executing any file content
def parse_config_content(content, filename="<config>", retired_out=None, reference_values=None):
    tree = ast.parse(content, filename, "exec")
    allowed_names = _config_allowed_names()
    parsed_values = {}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            raise ValueError(f"Line {getattr(statement, 'lineno', '?')}: only NAME = value assignments are allowed")
        name = statement.targets[0].id
        if name in RETIRED_CONFIG_SETTINGS and name not in allowed_names:
            if retired_out is not None and name not in retired_out:
                retired_out.append(name)
            continue
        if name not in allowed_names:
            raise ValueError(f"Line {statement.lineno}: unsupported configuration setting {name!r}")
        # One setting may reuse another, which the built-in template does and existing configs copy
        if isinstance(statement.value, ast.Name):
            referenced = statement.value.id
            if referenced not in allowed_names:
                raise ValueError(f"Line {statement.lineno}: {name} may only reference another configuration setting")
            source = parsed_values if referenced in parsed_values else (reference_values if reference_values is not None else globals())
            if referenced not in source:
                raise ValueError(f"Line {statement.lineno}: {name} references {referenced!r} before it has a value")
            parsed_values[name] = source[referenced]
            continue
        try:
            parsed_values[name] = ast.literal_eval(statement.value)
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as exc:
            raise ValueError(f"Line {statement.lineno}: {name} must be a plain value such as a number, string, True, False, None, list, tuple or dict") from exc
    return parsed_values


# Validates config content through the same restricted parser used at startup
def validate_config_content(content, filename="<generated-config>"):
    parse_config_content(content, filename)


# Reports settings an older version wrote that this version no longer defines
def describe_retired_settings(names, quoted_path):
    listed = ", ".join(sorted(names))
    return f"Config file {quoted_path} contains settings this version no longer uses, which were ignored: {listed}"


# Loads a config file as data and applies only recognized literal settings
def load_config_file(config_path, namespace=None, report_errors=True):
    selected_namespace = globals() if namespace is None else namespace
    retired_settings = []
    try:
        content = Path(config_path).read_text(encoding="utf-8")
        # Parsed as data rather than executed, so a config file picked up from the working directory cannot run code
        parsed_values = parse_config_content(content, str(config_path), retired_settings)
        selected_namespace.update(parsed_values)
        if report_errors:
            debug_print("Configuration applied", path=config_path, settings=len(parsed_values))
        if retired_settings and report_errors:
            print(f"* Note: {describe_retired_settings(retired_settings, chr(39) + str(config_path) + chr(39))}")
        return True
    except SyntaxError as exc:
        detail = f"Config file '{config_path}' has invalid Python syntax"
        if exc.lineno is not None:
            detail += f" at line {exc.lineno}"
        if exc.text:
            detail += f" | Source: {exc.text.rstrip()}"
        detail += f" | Parser: {exc.msg}"
    # Checked before ValueError because UnicodeDecodeError derives from it
    except UnicodeDecodeError:
        detail = f"Config file '{config_path}' is not valid UTF-8"
    except ValueError as exc:
        detail = f"Config file '{config_path}' contains unsupported content: {exc}"
    except Exception as exc:
        detail = f"Config file '{config_path}' failed with {type(exc).__name__}: {exc}"
    if report_errors:
        print("* Config files are read as data. Only documented SETTING = value lines with plain literal values are accepted.")
        print_recovery_error(context="config", detail=detail)
    return False


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
        game_name = sanitize_untrusted_text(ach.get("game", "Unknown Game"))
        ach_name = sanitize_untrusted_text(ach.get("name", "Unknown Achievement"))
        description = sanitize_untrusted_text(ach.get("description", ""))
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


# Fetches the persona (display) name history from Steam's public ajaxaliases endpoint
def fetch_persona_name_history(steamid, timeout=15):
    url = f"https://steamcommunity.com/profiles/{steamid}/ajaxaliases"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; steam_monitor)"}
    try:
        resp = req.get(url, headers=headers, timeout=timeout, verify=VERIFY_SSL)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        debug_swallowed_exception("Fetching the persona name history", exc)
        return []

    if not isinstance(data, list):
        return []

    history = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        name = entry.get("newname")
        if not name:
            continue
        history.append({"name": name, "timechanged": entry.get("timechanged", "")})
    return history


# Fetches and displays the persona name history for a Steam user
def display_persona_name_history(steamid):
    print(f"\n* Fetching persona name history...")
    history = fetch_persona_name_history(steamid)

    if not history:
        print("* No persona name history found or access is restricted by the user's privacy settings.")
        return

    print(f"\nPersona name history ({len(history)}):")
    for i, entry in enumerate(history, 1):
        name = sanitize_untrusted_text(entry.get("name", ""))
        when = sanitize_untrusted_text(entry.get("timechanged", ""))
        if when:
            print(f"{i} {colorize('username', name)} (changed: {when})")
        else:
            print(f"{i} {colorize('username', name)}")


# Gets detailed user information and displays it (for -i/--info mode)
def display_user_info(steamid, list_friends=False, show_name_history=False, show_achievements=False, achievements_count=None, achievements_use_owned_games=False):
    steamid_coloured = colorize("id", str(steamid))
    print(f"* Fetching details for Steam user with ID '{steamid_coloured}'...\n")

    try:
        debug_print("Opening the Steam Web API", steamid=steamid, key=mask_secret(STEAM_API_KEY))
        s_api = steam_web_api_client()
        s_user = s_api.call('ISteamUser.GetPlayerSummaries', steamids=str(steamid))
        s_played = s_api.call('IPlayerService.GetRecentlyPlayedGames', steamid=steamid, count=5)
        debug_print("Opening the Steam Web API", steamid=steamid, received="profile and recent games", outcome="OK")
    except Exception as e:
        print_recovery_error(e, context="runtime")
        sys.exit(1)

    try:
        username = sanitize_untrusted_text(s_user["response"]["players"][0].get("personaname"))
    except Exception as exc:
        print_recovery_error(exc, context="target", detail=f"Steam returned no profile for Steam64 ID {steamid}")
        sys.exit(1)

    status = int(s_user["response"]["players"][0].get("personastate"))
    visibilitystate = int(s_user["response"]["players"][0].get("communityvisibilitystate"))
    realname = sanitize_untrusted_text(s_user["response"]["players"][0].get("realname", ""))
    profile_url = s_user["response"]["players"][0].get("profileurl")
    timecreated = s_user["response"]["players"][0].get("timecreated")
    lastlogoff = s_user["response"]["players"][0].get("lastlogoff")
    gameid = s_user["response"]["players"][0].get("gameid")
    gamename = sanitize_untrusted_text(s_user["response"]["players"][0].get("gameextrainfo", ""))

    status_ts_old = int(time.time())
    status_ts_old_bck = status_ts_old
    last_status_ts = 0

    if status == 0:
        steam_last_status_file = f"steam_{username}_last_status.json"

        if os.path.isfile(steam_last_status_file):
            try:
                with open(steam_last_status_file, 'r', encoding="utf-8") as f:
                    last_status_read = json.load(f)
                if last_status_read:
                    last_status_ts = last_status_read[0]
                    # Read for its length check only: a truncated file must fall through to the defaults below
                    _last_status = last_status_read[1]
                    if lastlogoff and lastlogoff > last_status_ts:
                        status_ts_old = lastlogoff
                    else:
                        status_ts_old = last_status_ts
            except Exception as exc:
                debug_swallowed_exception(f"Reading the last status file '{steam_last_status_file}'", exc)

        if status_ts_old == status_ts_old_bck and lastlogoff:
            status_ts_old = lastlogoff

    print(f"Steam64 ID:\t\t\t{steamid}")
    print(f"Display name:\t\t\t{username}")
    if realname:
        print(f"Real name:\t\t\t{realname}")
    try:
        player_obj = s_user["response"]["players"][0]
        print_country_region(player_obj)
    except Exception as exc:
        debug_swallowed_exception("Displaying the country and region", exc)

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
    except Exception as exc:
        debug_swallowed_exception("Fetching the Steam level (IPlayerService.GetSteamLevel)", exc)

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
    except Exception as exc:
        debug_swallowed_exception("Fetching badges and XP (IPlayerService.GetBadges)", exc)

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
    except Exception as exc:
        debug_swallowed_exception("Fetching ban status (ISteamUser.GetPlayerBans)", exc)

    if show_name_history:
        display_persona_name_history(steamid)

    try:
        friends = s_api.call('ISteamUser.GetFriendList', steamid=steamid, relationship='friend')
        friend_entries = friends.get('friendslist', {}).get('friends', [])
        n_friends = len(friend_entries)
        print(f"\nFriends:\t\t\t{n_friends}")

        if list_friends and friend_entries:
            friend_ids = [f.get('steamid') for f in friend_entries if f.get('steamid')]
            # Map each friend's Steam64 ID to the Unix timestamp when the friendship started
            friend_since_map = {f.get('steamid'): f.get('friend_since') for f in friend_entries if f.get('steamid')}
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
                    persona = sanitize_untrusted_text(p.get("personaname", ""))
                    real_name = sanitize_untrusted_text(p.get("realname") or "")
                    sid = p.get("steamid", "")
                    since_ts = friend_since_map.get(sid)
                    since_str = f" - friend since {get_date_from_ts(int(since_ts))}" if since_ts else ""
                    if real_name:
                        print(f"- {persona} ({real_name}) [{sid}]{since_str}")
                    else:
                        print(f"- {persona} [{sid}]{since_str}")
    except Exception as exc:
        debug_swallowed_exception("Fetching the friends list (ISteamUser.GetFriendList)", exc)

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
                print(f"{i} {sanitize_untrusted_text(g.get('name'))} - {hours}h")
    except Exception as exc:
        debug_swallowed_exception("Fetching owned games (IPlayerService.GetOwnedGames)", exc)

    if gameid:
        print(f"\nUser is currently in-game:\t{gamename}")

    if "games" in s_played["response"].keys() and s_played["response"]["games"]:
        print(f"\nList of recently played games:")
        for i, game in enumerate(s_played["response"]["games"]):
            name = sanitize_untrusted_text(game.get('name'))
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

    mark_monitoring_started()

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
    last_games_count = None
    last_games_appids = None

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
    except Exception as e:
        print_recovery_error(e, context="file")

    try:
        if profile_csv_file_name:
            init_profile_csv_file(profile_csv_file_name)
    except Exception as e:
        print_recovery_error(e, context="file")

    try:
        debug_print("Opening the Steam Web API", steamid=steamid, key=mask_secret(STEAM_API_KEY))
        s_api = steam_web_api_client()
        s_user = s_api.call('ISteamUser.GetPlayerSummaries', steamids=str(steamid))
        s_played = s_api.call('IPlayerService.GetRecentlyPlayedGames', steamid=steamid, count=5)
        debug_print("Opening the Steam Web API", steamid=steamid, received="profile and recent games", outcome="OK")
    except Exception as e:
        print_recovery_error(e, context="runtime")
        sys.exit(1)

    try:
        username = sanitize_untrusted_text(s_user["response"]["players"][0].get("personaname"))
    except Exception as exc:
        print_recovery_error(exc, context="target", detail=f"Steam returned no profile for Steam64 ID {steamid}")
        sys.exit(1)

    status = int(s_user["response"]["players"][0].get("personastate"))
    visibilitystate = int(s_user["response"]["players"][0].get("communityvisibilitystate"))

    realname = sanitize_untrusted_text(s_user["response"]["players"][0].get("realname", ""))
    profile_url = s_user["response"]["players"][0].get("profileurl")
    timecreated = s_user["response"]["players"][0].get("timecreated")
    lastlogoff = s_user["response"]["players"][0].get("lastlogoff")
    gameid = s_user["response"]["players"][0].get("gameid")
    gamename = sanitize_untrusted_text(s_user["response"]["players"][0].get("gameextrainfo", ""))
    avatar_url = s_user["response"]["players"][0].get("avatarfull", "")

    status_ts_old = int(time.time())
    status_ts_old_bck = status_ts_old

    if status > 0:
        status_online_start_ts = status_ts_old
        status_online_start_ts_old = status_online_start_ts

    steam_last_status_file = f"steam_{username}_last_status.json"
    steam_games_file = f"steam_{username}_games.json"
    last_status_read = []
    last_status_ts = 0
    last_status = -1

    if os.path.isfile(steam_last_status_file):
        try:
            debug_print("Reading the last status file", path=steam_last_status_file)
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

    if GAMES_LIBRARY_CHECK and os.path.isfile(steam_games_file):
        try:
            debug_print("Reading the games library file", path=steam_games_file)
            with open(steam_games_file, 'r', encoding="utf-8") as f:
                games_data = json.load(f)
            if isinstance(games_data, dict):
                last_games_count = games_data.get("game_count")
                appids_list = games_data.get("appids")
                if appids_list is not None:
                    last_games_appids = set(appids_list)
            debug_print("Reading the games library file", path=steam_games_file, games=last_games_count, outcome="OK")
        except Exception as e:
            print(f"* Cannot load games library from '{steam_games_file}': {e}")

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
            write_json_atomic(steam_last_status_file, last_status_to_save)
            debug_print("Saved the last status", path=steam_last_status_file, outcome="OK")
        except Exception as e:
            print(f"* Cannot save last status to '{steam_last_status_file}' file: {e}")
            debug_swallowed_exception(f"Saving the last status to '{steam_last_status_file}'", e)

    try:
        if csv_file_name and (status != last_status):
            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), steam_personastates[status], gamename, gameid)
    except Exception as e:
        print_recovery_error(e, context="file")

    print(f"\nSteam64 ID:\t\t\t{steamid}")
    print(f"Display name:\t\t\t{username}")
    if realname:
        print(f"Real name:\t\t\t{realname}")
    try:
        player_obj = s_user["response"]["players"][0]
        print_country_region(player_obj)
    except Exception as exc:
        debug_swallowed_exception("Displaying the country and region", exc)

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
        except Exception as exc:
            s_level_displayed = False
            debug_swallowed_exception("Fetching the Steam level (IPlayerService.GetSteamLevel)", exc)

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
        except Exception as exc:
            debug_swallowed_exception("Fetching badges and XP (IPlayerService.GetBadges)", exc)

    # Optional friends snapshot at monitoring start
    if FRIENDS_CHECK:
        try:
            friends = s_api.call('ISteamUser.GetFriendList', steamid=steamid, relationship='friend')
            friend_entries = friends.get('friendslist', {}).get('friends', []) if isinstance(friends, dict) else []
            n_friends = len(friend_entries)
            print(f"\nFriends:\t\t\t{n_friends}")
        except Exception as exc:
            # Gracefully indicate that friends data is not accessible (privacy or API limitations)
            print(f"\nFriends:\t\t\tN/A")
            debug_swallowed_exception("Fetching the friends list (ISteamUser.GetFriendList)", exc)

    # Optional games library snapshot at monitoring start
    if GAMES_LIBRARY_CHECK:
        try:
            owned = s_api.call(
                "IPlayerService.GetOwnedGames",
                steamid=steamid,
                include_appinfo=0,
                include_played_free_games=1,
                appids_filter=[],
                include_free_sub=0,
                include_extended_appinfo=0,
                language="en",
            )
            games_list = owned.get("response", {}).get("games", []) if isinstance(owned, dict) else []
            current_count = len(games_list)
            current_appids = sorted(set(g.get("appid") for g in games_list if g.get("appid")))
            print(f"\nGames in library:\t\t{current_count}")
            last_games_count = current_count
            last_games_appids = set(current_appids)
            try:
                write_json_atomic(steam_games_file, {"game_count": current_count, "appids": current_appids})
                debug_print("Saved the games library", path=steam_games_file, outcome="OK")
            except Exception as e:
                print_recovery_error(e, context="file", detail=f"Cannot save games library to '{steam_games_file}'")
        except Exception as e:
            print(f"\nGames in library:\tN/A ({e})")

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
            write_json_atomic(steam_last_status_file, last_status_to_save)
            debug_print("Saved the last status", path=steam_last_status_file, outcome="OK")
        except Exception as e:
            print(f"* Cannot save last status to '{steam_last_status_file}' file: {e}")
            debug_swallowed_exception(f"Saving the last status to '{steam_last_status_file}'", e)

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
            name = sanitize_untrusted_text(game.get('name'))
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
    check_count = 0
    error_email_sent = False
    error_webhook_sent = False
    error_delivery_code = None

    m_subject = m_body = ""

    if status > 0:
        sleep_interval = STEAM_ACTIVE_CHECK_INTERVAL
    else:
        sleep_interval = STEAM_CHECK_INTERVAL

    recovery_hint_tracker = RecoveryHintTracker()
    feature_outages = FeatureOutageTracker()
    transient_retry_used = False

    debug_print("First check", due_in=display_time(sleep_interval))
    time.sleep(sleep_interval)

    # Main loop
    while True:
        check_count += 1
        current_steam_level = None
        current_player_xp = None
        current_friend_ids = None
        current_games_count = None
        current_games_appids = None
        current_username = None
        current_avatar_url = avatar_url
        try:
            debug_print("Polling Steam", steamid=steamid, endpoints="ISteamUser.GetPlayerSummaries+IPlayerService.GetRecentlyPlayedGames")
            s_api = steam_web_api_client()
            s_user = s_api.call('ISteamUser.GetPlayerSummaries', steamids=str(steamid))
            s_played = s_api.call('IPlayerService.GetRecentlyPlayedGames', steamid=steamid, count=5)
            status = int(s_user["response"]["players"][0]["personastate"])
            gameid = s_user["response"]["players"][0].get("gameid")
            gamename = sanitize_untrusted_text(s_user["response"]["players"][0].get("gameextrainfo", ""))
            current_username = sanitize_untrusted_text(s_user["response"]["players"][0].get("personaname"))
            current_avatar_url = s_user["response"]["players"][0].get("avatarfull", "") or avatar_url
            debug_print("Polling Steam", steamid=steamid, personastate=status, game=gamename or None, outcome="OK")

            # Fetch Steam level and total XP if tracking is enabled
            if STEAM_LEVEL_XP_CHECK:
                try:
                    s_level = s_api.call('IPlayerService.GetSteamLevel', steamid=steamid)
                    current_steam_level = s_level.get('response', {}).get('player_level')
                except Exception as exc:
                    current_steam_level = None
                    debug_swallowed_exception("Fetching Steam level (IPlayerService.GetSteamLevel)", exc)

                try:
                    badges = s_api.call('IPlayerService.GetBadges', steamid=steamid)
                    current_player_xp = badges.get('response', {}).get('player_xp')
                except Exception as exc:
                    current_player_xp = None
                    debug_swallowed_exception("Fetching total XP (IPlayerService.GetBadges)", exc)

            # Fetch friends list when tracking is enabled
            if FRIENDS_CHECK:
                try:
                    friends = s_api.call('ISteamUser.GetFriendList', steamid=steamid, relationship='friend')
                    friend_entries = friends.get('friendslist', {}).get('friends', [])
                    current_friend_ids = {f.get('steamid') for f in friend_entries if f.get('steamid')}
                except Exception as exc:
                    current_friend_ids = None
                    debug_swallowed_exception("Fetching the friends list (ISteamUser.GetFriendList)", exc)

            # Fetch games library (minimal: count + appids only) when tracking is enabled
            if GAMES_LIBRARY_CHECK:
                try:
                    owned = s_api.call(
                        "IPlayerService.GetOwnedGames",
                        steamid=steamid,
                        include_appinfo=0,
                        include_played_free_games=1,
                        appids_filter=[],
                        include_free_sub=0,
                        include_extended_appinfo=0,
                        language="en",
                    )
                    games_list = owned.get("response", {}).get("games", []) if isinstance(owned, dict) else []
                    current_games_count = len(games_list)
                    current_games_appids = set(g.get("appid") for g in games_list if g.get("appid"))
                except Exception as exc:
                    current_games_count = None
                    current_games_appids = None
                    debug_swallowed_exception("Fetching the games library (IPlayerService.GetOwnedGames)", exc)
        except Exception as e:

            if status > 0:
                sleep_interval = STEAM_ACTIVE_CHECK_INTERVAL
            else:
                sleep_interval = STEAM_CHECK_INTERVAL

            advice = classify_recovery_error(e, context="runtime")
            response = e.response if isinstance(e, req.exceptions.HTTPError) else None
            if advice.code != error_delivery_code:
                error_email_sent = False
                error_webhook_sent = False
                error_delivery_code = advice.code
            if advice.code == "steam.rate_limited":
                # Rate limits carry their own wait, so they skip the retry path rather than burning an attempt
                retry_after = steam_retry_after_seconds(response, sleep_interval) if response is not None else sleep_interval
                print_monitor_recovery(e, "runtime", recovery_hint_tracker, "* ")
                verbose_print(f"Waiting {display_time(retry_after)} before retrying")
                print_cur_ts("Timestamp:\t\t\t")
                time.sleep(retry_after)
                continue
            else:
                print_monitor_recovery(e, "runtime", recovery_hint_tracker, "* ")
                if advice.retryable and not transient_retry_used:
                    # One short retry absorbs a blip without waiting a whole polling interval
                    transient_retry_used = True
                    verbose_print(f"Retrying once in {display_time(TRANSIENT_RETRY_SECONDS)}")
                    print_cur_ts("Timestamp:\t\t\t")
                    time.sleep(TRANSIENT_RETRY_SECONDS)
                    continue
                print(f"* Retrying in {display_time(sleep_interval)}")
                if advice.code == "auth.api_key_invalid":
                    m_subject = f"steam_monitor: API key error! (user: {username})"
                    m_body = f"{advice.summary}{nl_ch}{nl_ch}To fix: {advice.fix}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                else:
                    m_subject = f"steam_monitor: monitoring error (user: {username})"
                    m_body = f"{advice.summary}{nl_ch}{nl_ch}To fix: {advice.fix}{nl_ch}{nl_ch}Steam Monitor will retry in {display_time(sleep_interval)}.{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                if (ERROR_NOTIFICATION and not error_email_sent) or (webhook_event_enabled("error") and not error_webhook_sent):
                    email_delivered, webhook_delivered = send_notification_channels("error", m_subject, m_body, email_enabled=ERROR_NOTIFICATION and not error_email_sent, webhook_enabled=webhook_event_enabled("error") and not error_webhook_sent, image_url=current_avatar_url, ntfy_priority=5, ntfy_tags="warning")
                    error_email_sent = error_email_sent or email_delivered
                    error_webhook_sent = error_webhook_sent or webhook_delivered

            print_cur_ts("Timestamp:\t\t\t")

            time.sleep(sleep_interval)

            continue

        recovery_hint_tracker.reset()
        transient_retry_used = False
        error_email_sent = False
        error_webhook_sent = False
        error_delivery_code = None

        # A tracked feature that returned nothing cannot raise its alert, which is invisible without these lines
        unavailable_features = {}
        if STEAM_LEVEL_XP_CHECK and (current_steam_level is None or current_player_xp is None):
            unavailable_features["level_xp"] = ("Steam level or total XP is unavailable, so level and XP alerts cannot fire", "Steam level and total XP are available again, so level and XP alerts can fire")
        if FRIENDS_CHECK and current_friend_ids is None:
            unavailable_features["friends"] = ("The friends list is unavailable, so friends alerts cannot fire", "The friends list is available again, so friends alerts can fire")
        if GAMES_LIBRARY_CHECK and current_games_count is None:
            unavailable_features["games_library"] = ("The games library is unavailable, so games library alerts cannot fire", "The games library is available again, so games library alerts can fire")
        debug_print("Tracked features", unavailable=",".join(unavailable_features) or "none")
        # An outage that lasts is news once, so only the features that changed since the last cycle are reported
        verbose_notice(*feature_outages.transitions(unavailable_features))

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
                write_json_atomic(steam_last_status_file, last_status_to_save)
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
            webhook_notification_type = "active" if status_old == 0 and status > 0 else "inactive" if status_old > 0 and status == 0 else "status"
            webhook_status_enabled = webhook_event_enabled("status") or webhook_event_enabled(webhook_notification_type)
            if STATUS_NOTIFICATION or (ACTIVE_INACTIVE_NOTIFICATION and act_inact_flag) or webhook_status_enabled:
                send_notification_channels(webhook_notification_type, m_subject, m_body, email_enabled=STATUS_NOTIFICATION or (ACTIVE_INACTIVE_NOTIFICATION and act_inact_flag), webhook_enabled=webhook_status_enabled, image_url=current_avatar_url)
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

            if (GAME_CHANGE_NOTIFICATION or webhook_event_enabled("game")) and m_subject and m_body:
                game_image_url = steam_game_image_url(gameid or gameid_old)
                send_notification_channels("game", m_subject, m_body, email_enabled=GAME_CHANGE_NOTIFICATION, image_url=game_image_url)

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

                if STEAM_LEVEL_XP_NOTIFICATION or webhook_event_enabled("level_xp"):
                    m_subject = f"Steam user {username} level changed to {level_int}"
                    m_body = (
                        f"Steam user {username} level {direction} from {last_level_int} to {level_int} (delta {delta})"
                        f"\n{xp_info_str}"
                        f"{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    )
                    send_notification_channels("level_xp", m_subject, m_body, email_enabled=STEAM_LEVEL_XP_NOTIFICATION, image_url=current_avatar_url)

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

                if STEAM_LEVEL_XP_NOTIFICATION or webhook_event_enabled("level_xp"):
                    m_subject = f"Steam user {username} total XP changed to {xp_int}"
                    m_body = (
                        f"Steam user {username} total XP {direction} from {last_xp_int} to {xp_int} (delta {delta})"
                        f"{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                    )
                    send_notification_channels("level_xp", m_subject, m_body, email_enabled=STEAM_LEVEL_XP_NOTIFICATION, image_url=current_avatar_url)

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

                    # Defined and called inside this iteration, so the enclosing s_api cannot change under it
                    def _fetch_friend_summaries(id_set):
                        if not id_set:
                            return []
                        summaries = []
                        ids_list = list(id_set)
                        chunk_size = 100
                        for i in range(0, len(ids_list), chunk_size):
                            chunk = ids_list[i:i + chunk_size]
                            try:
                                resp = s_api.call('ISteamUser.GetPlayerSummaries', steamids=",".join(chunk))  # noqa: B023
                                players = resp.get('response', {}).get('players', [])
                                summaries.extend(players)
                            except Exception as exc:
                                debug_swallowed_exception("Fetching friend details (ISteamUser.GetPlayerSummaries)", exc)
                                continue
                        return summaries

                    added_players = []
                    removed_players = []

                    try:
                        added_players = _fetch_friend_summaries(added_ids)
                        added_map = {p.get('steamid'): p for p in added_players}
                        for sid in added_ids:
                            p = added_map.get(sid, {})
                            persona = sanitize_untrusted_text(p.get('personaname') or "")
                            real = sanitize_untrusted_text(p.get('realname') or "")
                            if profile_csv_file_name:
                                try:
                                    write_profile_csv_entry(profile_csv_file_name, date=datetime.fromtimestamp(int(time.time())), event="friend_added", friend_steamid=sid, friend_persona=persona, friend_realname=real,)
                                except Exception as e:
                                    print(f"* Error writing profile CSV: {e}")
                            if real:
                                added_details.append(f"- {persona} ({real}) [{sid}]")
                            else:
                                added_details.append(f"- {persona or sid} [{sid}]")
                    except Exception as exc:
                        debug_swallowed_exception("Building the added friends detail list", exc)

                    try:
                        removed_players = _fetch_friend_summaries(removed_ids)
                        removed_map = {p.get('steamid'): p for p in removed_players}
                        for sid in removed_ids:
                            p = removed_map.get(sid, {})
                            persona = sanitize_untrusted_text(p.get('personaname') or "")
                            real = sanitize_untrusted_text(p.get('realname') or "")
                            if profile_csv_file_name:
                                try:
                                    write_profile_csv_entry(profile_csv_file_name, date=datetime.fromtimestamp(int(time.time())), event="friend_removed", friend_steamid=sid, friend_persona=persona, friend_realname=real,)
                                except Exception as e:
                                    print(f"* Error writing profile CSV: {e}")
                            if real:
                                removed_details.append(f"- {persona} ({real}) [{sid}]")
                            else:
                                removed_details.append(f"- {persona or sid} [{sid}]")
                    except Exception as exc:
                        debug_swallowed_exception("Building the removed friends detail list", exc)

                    if added_details:
                        print("New friends added:")
                        for line in added_details:
                            print(line)
                    if removed_details:
                        print("Friends removed:")
                        for line in removed_details:
                            print(line)

                    if FRIENDS_NOTIFICATION or webhook_event_enabled("friends"):
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
                        send_notification_channels("friends", m_subject_friends, m_body_friends, email_enabled=FRIENDS_NOTIFICATION, image_url=current_avatar_url)

                    print_cur_ts("Timestamp:\t\t\t")

                    alive_counter = 0
                    last_friend_ids = current_friend_ids

        # Games library changed
        if GAMES_LIBRARY_CHECK and current_games_count is not None and current_games_appids is not None:
            if last_games_count is None or last_games_appids is None:
                last_games_count = current_games_count
                last_games_appids = set(current_games_appids)
            else:
                count_changed = current_games_count != last_games_count
                appids_changed = current_games_appids != last_games_appids
                if count_changed or appids_changed:
                    old_count = last_games_count
                    new_count = current_games_count
                    delta = new_count - old_count
                    added_appids = sorted(current_games_appids - last_games_appids)
                    removed_appids = sorted(last_games_appids - current_games_appids)

                    if delta != 0:
                        delta_str = f"+{delta}" if delta > 0 else str(delta)
                        print(f"Steam user {username} games library changed from {old_count} to {new_count} ({delta_str})")
                    else:
                        print(f"Steam user {username} games library changed (same count: {new_count}, titles changed)")

                    if added_appids:
                        print(f"Added: {', '.join(str(a) for a in added_appids)}")
                    if removed_appids:
                        print(f"Removed: {', '.join(str(a) for a in removed_appids)}")

                    try:
                        write_json_atomic(steam_games_file, {"game_count": new_count, "appids": sorted(current_games_appids)})
                    except Exception as e:
                        print(f"* Cannot save games library to '{steam_games_file}': {e}")

                    if profile_csv_file_name:
                        try:
                            write_profile_csv_entry(profile_csv_file_name, date=datetime.fromtimestamp(int(time.time())), event="games_library_change", old_value=old_count, new_value=new_count, delta=delta,)
                        except Exception as e:
                            print(f"* Error writing profile CSV: {e}")

                    if GAMES_LIBRARY_NOTIFICATION or webhook_event_enabled("games"):
                        m_subject_games = f"Steam user {username} games library changed (now {new_count})"
                        body_parts = []
                        if delta != 0:
                            delta_str = f"+{delta}" if delta > 0 else str(delta)
                            body_parts.append(f"Steam user {username} games library changed from {old_count} to {new_count} ({delta_str})")
                        else:
                            body_parts.append(f"Steam user {username} games library changed (same count: {new_count}, titles changed)")
                        if added_appids:
                            body_parts.append(f"Added: {', '.join(str(a) for a in added_appids)}")
                        if removed_appids:
                            body_parts.append(f"Removed: {', '.join(str(a) for a in removed_appids)}")
                        m_body_games = "\n".join(body_parts) + get_cur_ts(nl_ch + nl_ch + "Timestamp: ")
                        send_notification_channels("games", m_subject_games, m_body_games, email_enabled=GAMES_LIBRARY_NOTIFICATION, image_url=current_avatar_url)

                    print_cur_ts("Timestamp:\t\t\t")
                    alive_counter = 0
                    last_games_count = current_games_count
                    last_games_appids = set(current_games_appids)

        # Display (persona) name changed
        if current_username and current_username != username:
            old_name = username
            new_name = current_username
            print(f"Steam user {old_name} changed display name to {new_name}")

            if profile_csv_file_name:
                try:
                    write_profile_csv_entry(profile_csv_file_name, date=datetime.fromtimestamp(int(time.time())), event="name_change", old_value=old_name, new_value=new_name)
                except Exception as e:
                    print(f"* Error writing profile CSV: {e}")

            if NAME_CHANGE_NOTIFICATION or webhook_event_enabled("name"):
                m_subject_name = f"Steam user {old_name} changed display name to {new_name}"
                m_body_name = f"Steam user {old_name} changed display name to {new_name}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
                send_notification_channels("name", m_subject_name, m_body_name, email_enabled=NAME_CHANGE_NOTIFICATION, image_url=current_avatar_url)

            print_cur_ts("Timestamp:\t\t\t")
            alive_counter = 0

            # Adopt the new display name for subsequent notifications and output
            username = current_username
            avatar_url = current_avatar_url

        if change:
            alive_counter = 0

            try:
                if csv_file_name:
                    write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), steam_personastates[status], gamename, gameid)
            except Exception as e:
                print_recovery_error(e, context="file")

        status_old = status
        gameid_old = gameid
        gamename_old = gamename
        alive_counter += 1

        debug_print("Completed check", check=f"#{check_count}", user=steamid, status=steam_personastates[status], game=gamename or None)

        if LIVENESS_CHECK_COUNTER and alive_counter >= LIVENESS_CHECK_COUNTER and status == 0:
            verbose_print(f"Monitoring healthy for {steamid}. The user is still offline with no status or game change")
            print_cur_ts("Liveness check, timestamp:\t")
            alive_counter = 0

        if status > 0:
            debug_print("Next check", due_in=display_time(STEAM_ACTIVE_CHECK_INTERVAL), reason="user is active")
            time.sleep(STEAM_ACTIVE_CHECK_INTERVAL)
        else:
            debug_print("Next check", due_in=display_time(STEAM_CHECK_INTERVAL), reason="user is offline")
            time.sleep(STEAM_CHECK_INTERVAL)


# Applies validated one-run webhook command-line overrides to runtime settings
def apply_webhook_cli_overrides(args, parser):
    global WEBHOOK_ENABLED, WEBHOOK_URL, WEBHOOK_PROVIDER, WEBHOOK_ACTIVE_NOTIFICATION, WEBHOOK_INACTIVE_NOTIFICATION, WEBHOOK_STATUS_NOTIFICATION, WEBHOOK_GAME_CHANGE_NOTIFICATION, WEBHOOK_LEVEL_XP_NOTIFICATION, WEBHOOK_FRIENDS_NOTIFICATION, WEBHOOK_GAMES_NOTIFICATION, WEBHOOK_NAME_CHANGE_NOTIFICATION, WEBHOOK_ERROR_NOTIFICATION
    if args.webhook_provider is not None:
        WEBHOOK_PROVIDER = str(args.webhook_provider)
    if args.webhook_url is not None:
        if not validate_webhook_url(args.webhook_url):
            parser.error("--webhook-url must contain a complete HTTPS link without embedded credentials")
        WEBHOOK_URL = str(args.webhook_url).strip()
        WEBHOOK_ENABLED = True
    if args.webhook_enabled is not None:
        WEBHOOK_ENABLED = args.webhook_enabled
    event_overrides = (
        ("webhook_active", "WEBHOOK_ACTIVE_NOTIFICATION"),
        ("webhook_inactive", "WEBHOOK_INACTIVE_NOTIFICATION"),
        ("webhook_status", "WEBHOOK_STATUS_NOTIFICATION"),
        ("webhook_game_changes", "WEBHOOK_GAME_CHANGE_NOTIFICATION"),
        ("webhook_level_xp", "WEBHOOK_LEVEL_XP_NOTIFICATION"),
        ("webhook_friends", "WEBHOOK_FRIENDS_NOTIFICATION"),
        ("webhook_games", "WEBHOOK_GAMES_NOTIFICATION"),
        ("webhook_name_change", "WEBHOOK_NAME_CHANGE_NOTIFICATION"),
    )
    for argument_name, setting_name in event_overrides:
        if getattr(args, argument_name) is True:
            WEBHOOK_ENABLED = True
            globals()[setting_name] = True
    if args.webhook_errors is not None:
        WEBHOOK_ERROR_NOTIFICATION = args.webhook_errors
        if args.webhook_errors:
            WEBHOOK_ENABLED = True
    if args.webhook_provider is None:
        detected_provider = detect_webhook_provider(WEBHOOK_URL)
        configured_provider = normalized_webhook_provider()
        if detected_provider and detected_provider != configured_provider:
            WEBHOOK_PROVIDER = detected_provider
            print(f"* Warning: Configured webhook provider did not match the URL. Using {detected_provider}.")


# Rejects unrelated options when a hidden secret-entry action is selected
def validate_secret_action_args(args, parser, action_dest, action_flag, permitted_extra=()):
    permitted = {action_dest, "env_file", "no_color", *permitted_extra}
    conflicts = []
    for name, value in vars(args).items():
        if name in permitted or value is None or value is False:
            continue
        conflicts.append("--" + name.replace("_", "-"))
    if conflicts:
        parser.error(f"{action_flag} cannot be combined with " + ", ".join(conflicts))


# Parses configuration and starts the selected Steam Monitor action
def main():
    global CLI_CONFIG_PATH, DOTENV_FILE, LIVENESS_CHECK_COUNTER, STEAM_API_KEY, CSV_FILE, PROFILE_CSV_FILE, DISABLE_LOGGING, ST_LOGFILE, ACTIVE_INACTIVE_NOTIFICATION, GAME_CHANGE_NOTIFICATION, STATUS_NOTIFICATION, NAME_CHANGE_NOTIFICATION, ERROR_NOTIFICATION, STEAM_LEVEL_XP_CHECK, STEAM_LEVEL_XP_NOTIFICATION, FRIENDS_CHECK, FRIENDS_NOTIFICATION, GAMES_LIBRARY_CHECK, GAMES_LIBRARY_NOTIFICATION, STEAM_CHECK_INTERVAL, STEAM_ACTIVE_CHECK_INTERVAL, FILE_SUFFIX, SMTP_PASSWORD, stdout_bck, COLORED_OUTPUT, COLOR_THEME, NTFY_IMAGES, EXPORTED_SECRET_KEYS, TRUNCATE_CHARS, WEBHOOK_ENABLED, DEBUG_MODE, COMMAND_LINE_SECRET_KEYS

    if "--generate-config" in sys.argv and not any(flag in sys.argv for flag in SECRET_ACTION_FLAGS):
        config_content = CONFIG_BLOCK.strip("\n") + "\n"
        # Check if a filename was provided after --generate-config
        try:
            idx = sys.argv.index("--generate-config")
            if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-"):
                # Write directly to file (bypasses PowerShell UTF-16 encoding issue on Windows)
                output_file = sys.argv[idx + 1]
                try:
                    backup_path = create_timestamped_backup(output_file)
                except OSError as exc:
                    print(f"* Error: Could not back up the existing config file '{output_file}': {exc}")
                    sys.exit(1)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(config_content)
                print(f"Config written to: {output_file}")
                if backup_path:
                    print(f"Previous config backed up to: {backup_path}")
                sys.exit(0)
        except (ValueError, IndexError):
            pass
        # No filename provided - write to stdout using buffer to ensure UTF-8
        sys.stdout.buffer.write(config_content.encode("utf-8"))
        sys.stdout.buffer.flush()
        sys.exit(0)

    if "--version" in sys.argv and not any(flag in sys.argv for flag in SECRET_ACTION_FLAGS):
        print(f"{os.path.basename(sys.argv[0])} v{VERSION}")
        sys.exit(0)

    stdout_bck = sys.stdout

    # The screen clearing and the banner run before argparse, so their settings are resolved from the
    # config file first rather than from the built-in defaults alone
    apply_early_output_config()

    # Initialise colour handling based on CLI args (early check) and terminal capabilities
    if "--no-color" in sys.argv:
        globals()["COLORED_OUTPUT"] = False

    init_color_output(stdout_bck)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Read straight from sys.argv because argparse has not run yet, and the screen is cleared before it does
    if "--debug" in sys.argv:
        DEBUG_MODE = True
    if CLEAR_SCREEN and DEBUG_MODE:
        debug_print("Terminal screen clear skipped because debug mode is active")
    clear_screen(CLEAR_SCREEN and not keep_terminal_history() and not DEBUG_MODE)

    print_startup_banner()

    parser = argparse.ArgumentParser(
        prog="steam_monitor",
        description=(f"Monitor a Steam user's playing status and send customizable email or webhook alerts [ {PROJECT_URL} ]"),
        epilog=help_examples(),
        formatter_class=argparse.RawTextHelpFormatter, **argparse_color_kwargs()
    )

    # Positional
    parser.add_argument(
        "steam64_id",
        nargs="?",
        metavar="STEAM_TARGET",
        help="Steam64 ID, Steam3 identifier, vanity name or profile URL",
        type=str
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
        "--set-steam-api-key",
        dest="set_steam_api_key",
        action="store_true",
        help="Privately validate and save STEAM_API_KEY through a hidden prompt",
    )
    conf.add_argument(
        "--set-smtp-password",
        dest="set_smtp_password",
        action="store_true",
        help="Enter the SMTP password privately, check it against the mail server and save it to the dotenv file",
    )
    conf.add_argument(
        "--set-webhook-url",
        dest="set_webhook_url",
        action="store_true",
        help="Save a Discord or ntfy webhook URL through a hidden prompt",
    )
    conf.add_argument(
        "--setup",
        dest="setup",
        action="store_true",
        default=None,
        help="Run the guided setup and write a ready-to-run configuration",
    )
    conf.add_argument(
        "--config-file",
        dest="config_file",
        metavar="PATH",
        help="Location of the optional config file (auto-search if not set, disable with 'none')",
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
    conf.add_argument(
        "--doctor",
        dest="doctor",
        action="store_true",
        default=None,
        help="Run read-only preflight checks and report what is ready and what is not",
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
    notify = parser.add_argument_group("Email notifications")
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
        "--notify-name-change",
        dest="notify_name_change",
        action="store_true",
        default=None,
        help="Email when user's display (persona) name changes"
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
        "--notify-games",
        dest="notify_games",
        action="store_true",
        default=None,
        help="Email when games library changes (requires --check-games or GAMES_LIBRARY_CHECK=True)"
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

    webhook_notify = parser.add_argument_group("Webhook notifications")
    webhook_toggle = webhook_notify.add_mutually_exclusive_group()
    webhook_toggle.add_argument(
        "--webhook",
        dest="webhook_enabled",
        action="store_true",
        default=None,
        help="Enable the configured webhook alerts"
    )
    webhook_toggle.add_argument(
        "--no-webhook",
        dest="webhook_enabled",
        action="store_false",
        default=None,
        help="Disable the configured webhook alerts"
    )
    webhook_notify.add_argument(
        "--webhook-url",
        dest="webhook_url",
        metavar="URL",
        type=str,
        help="Use one Discord webhook or ntfy topic URL for this run (may remain in shell history)"
    )
    webhook_notify.add_argument(
        "--webhook-provider",
        dest="webhook_provider",
        choices=("discord", "ntfy"),
        help="Webhook request format for this run (default: configured provider)"
    )
    webhook_notify.add_argument(
        "--webhook-active",
        dest="webhook_active",
        action="store_true",
        default=None,
        help="Send a webhook alert when the user becomes active"
    )
    webhook_notify.add_argument(
        "--webhook-inactive",
        dest="webhook_inactive",
        action="store_true",
        default=None,
        help="Send a webhook alert when the user goes offline"
    )
    webhook_notify.add_argument(
        "--webhook-status",
        dest="webhook_status",
        action="store_true",
        default=None,
        help="Send a webhook alert on every status change"
    )
    webhook_notify.add_argument(
        "--webhook-game-changes",
        dest="webhook_game_changes",
        action="store_true",
        default=None,
        help="Send a webhook alert on game start, change or stop"
    )
    webhook_notify.add_argument(
        "--webhook-level-xp",
        dest="webhook_level_xp",
        action="store_true",
        default=None,
        help="Send webhook alerts for Steam level or XP changes"
    )
    webhook_notify.add_argument(
        "--webhook-friends",
        dest="webhook_friends",
        action="store_true",
        default=None,
        help="Send webhook alerts for friends list changes"
    )
    webhook_notify.add_argument(
        "--webhook-games",
        dest="webhook_games",
        action="store_true",
        default=None,
        help="Send webhook alerts for games library changes"
    )
    webhook_notify.add_argument(
        "--webhook-name-change",
        dest="webhook_name_change",
        action="store_true",
        default=None,
        help="Send a webhook alert when the display name changes"
    )
    webhook_error_toggle = webhook_notify.add_mutually_exclusive_group()
    webhook_error_toggle.add_argument(
        "--webhook-errors",
        dest="webhook_errors",
        action="store_true",
        default=None,
        help="Send webhook alerts when monitoring has a problem"
    )
    webhook_error_toggle.add_argument(
        "--no-webhook-error-notify",
        dest="webhook_errors",
        action="store_false",
        default=None,
        help="Disable webhook alerts when monitoring has a problem"
    )
    webhook_notify.add_argument(
        "--send-test-webhook",
        dest="send_test_webhook",
        action="store_true",
        help="Send one test webhook without starting monitoring"
    )

    # User information
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
    # User information & listing
    info = parser.add_argument_group("User information & listing")
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
        "--name-history",
        dest="show_name_history",
        action="store_true",
        help="When used with -i/--info, also display the persona (display) name history"
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
        "--check-games",
        dest="check_games",
        action="store_true",
        default=None,
        help="Track changes in games library (game count); uses minimal API data (no names/icons)"
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
    opts.add_argument(
        "--truncate",
        dest="truncate",
        metavar="N",
        type=int,
        help="Max characters per screen line (not log), use 999 to auto-detect terminal width, ignored if -d is set"
    )
    opts.add_argument(
        "--verbose",
        dest="verbose",
        action="store_true",
        default=None,
        help="Print extra startup and runtime detail (overrides VERBOSE_MODE)"
    )
    opts.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        default=None,
        help="Print timestamped diagnostic detail including outbound calls and failure causes (overrides DEBUG_MODE)"
    )

    args = parser.parse_args()

    # Applied here so config-load failures and startup checks can already print diagnostics
    apply_diagnostic_cli_flags(args)

    selected_secret_actions = [flag for flag, selected in zip(SECRET_ACTION_FLAGS, (args.set_steam_api_key, args.set_smtp_password, args.set_webhook_url), strict=True) if selected]
    if len(selected_secret_actions) > 1:
        parser.error(f"{selected_secret_actions[0]} cannot be combined with {selected_secret_actions[1]}")

    if args.set_steam_api_key:
        validate_secret_action_args(args, parser, "set_steam_api_key", "--set-steam-api-key")
        try:
            run_set_steam_api_key(env_file=args.env_file)
        except (SecretConfigurationError, RecoveryError) as exc:
            print_recovery_error(exc, context="set_steam_api_key")
            sys.exit(1)
        sys.exit(0)

    if args.set_webhook_url:
        validate_secret_action_args(args, parser, "set_webhook_url", "--set-webhook-url")
        try:
            run_set_webhook_url(env_file=args.env_file)
        except (SecretConfigurationError, RecoveryError) as exc:
            print_recovery_error(exc, context="set_webhook_url")
            sys.exit(1)
        sys.exit(0)

    if args.send_test_email and args.send_test_webhook:
        parser.error("--send-test-email cannot be combined with --send-test-webhook")

    # "none" is the documented sentinel that switches discovery off, so it is a selection rather than a missing file
    config_discovery_disabled = args.config_file is not None and str(args.config_file).casefold() == "none"
    if args.config_file and not config_discovery_disabled:
        CLI_CONFIG_PATH = os.path.expanduser(args.config_file)

    cfg_path = None if config_discovery_disabled else find_config_file(CLI_CONFIG_PATH)

    if not cfg_path and CLI_CONFIG_PATH and not args.setup:
        # Setup is allowed to name a file that does not exist yet, since creating it is the point
        print_recovery_error(context="config", detail=f"Config file '{CLI_CONFIG_PATH}' does not exist")
        sys.exit(1)

    if cfg_path:
        debug_print("Loading configuration file", path=cfg_path)
        if not load_config_file(cfg_path):
            sys.exit(1)
    else:
        debug_print("No configuration file found, using built-in defaults")

    # Reapplied because the config file may carry VERBOSE_MODE or DEBUG_MODE values that must not beat an explicit flag
    apply_diagnostic_cli_flags(args)

    apply_tls_verification_setting()

    # Runs after the config file is read so a persisted TARGET_STEAM_ID counts as a target
    if len(sys.argv) == 1 and not TARGET_STEAM_ID:
        sys.exit(print_welcome_screen())

    if args.env_file:
        DOTENV_FILE = os.path.expanduser(args.env_file)
    else:
        if DOTENV_FILE:
            DOTENV_FILE = os.path.expanduser(DOTENV_FILE)

    EXPORTED_SECRET_KEYS = frozenset(secret for secret in SECRET_KEYS if os.getenv(secret) is not None)
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
                    load_dotenv(env_path, override=False)
            else:
                env_path = find_dotenv() or None
                if env_path:
                    load_dotenv(env_path, override=False)
        except ImportError:
            env_path = DOTENV_FILE if DOTENV_FILE else None
            if env_path:
                print(f"* Warning: Cannot load dotenv file '{env_path}' because 'python-dotenv' is not installed\n\nTo install it, run:\n    pip3 install python-dotenv\n\nOnce installed, re-run this tool\n")

    # Exported secrets apply on their own, so a dotenv file is an alternative to the environment rather than a precondition
    applied_secrets = load_secrets_from_environment()
    if applied_secrets:
        secret_source_map = secret_sources(env_path)
        for secret, _ in applied_secrets:
            debug_print("Secret resolution", name=secret, source=secret_source_map.get(secret, "environment"), value=mask_secret(globals().get(secret)))

    if args.steam_api_key:
        STEAM_API_KEY = args.steam_api_key

    apply_webhook_cli_overrides(args, parser)

    # Assigned once from the arguments rather than accumulated, so a second run in one process starts clean
    COMMAND_LINE_SECRET_KEYS = frozenset(name for name, supplied in (("STEAM_API_KEY", args.steam_api_key), ("WEBHOOK_URL", args.webhook_url)) if supplied)

    # Setup and doctor exit before the monitoring path re-initializes colour, so the configured
    # COLORED_OUTPUT, COLOR_THEME and --no-color are applied here rather than leaving both screens plain
    if args.no_color is True:
        COLORED_OUTPUT = False
    init_color_output(stdout_bck)

    # A target is optional only for the utility actions below or when the config file names one. Checked after the
    # dotenv file is resolved, so the command this prints carries the same paths the run was given
    if not args.steam64_id and not args.resolve_community_url and not TARGET_STEAM_ID:
        if not (args.send_test_email or args.send_test_webhook or args.doctor or args.setup or args.set_smtp_password):
            print_recovery_error(context="target.missing", detail="A Steam profile target needs to be defined")
            sys.exit(1)

    if args.set_smtp_password:
        # Runs after the config file so the mail server it signs in to is the one monitoring would use
        validate_secret_action_args(args, parser, "set_smtp_password", "--set-smtp-password", permitted_extra=("config_file",))
        try:
            run_set_smtp_password(env_file=args.env_file or env_path)
        except (SecretConfigurationError, RecoveryError) as exc:
            print_recovery_error(exc, context="set_smtp_password")
            sys.exit(1)
        sys.exit(0)

    if args.setup:
        # Runs here rather than earlier so the values already in effect become the defaults it offers
        setup_target = args.resolve_community_url or args.steam64_id or TARGET_STEAM_ID
        sys.exit(run_setup_wizard(initial_target=setup_target, config_file=args.config_file or cfg_path, env_file=args.env_file or env_path))

    if args.doctor:
        # Applied before the report so the log destination it names is the one monitoring would open
        if args.file_suffix:
            FILE_SUFFIX = args.file_suffix
        doctor_target = args.resolve_community_url or args.steam64_id or TARGET_STEAM_ID
        sys.exit(run_doctor(target_value=doctor_target, config_path=cfg_path, env_path=env_path))

    if not check_internet():
        sys.exit(1)

    if args.send_test_email:
        print("* Sending test email notification ...\n")
        debug_print("Test email", sender=SENDER_EMAIL, recipient=RECEIVER_EMAIL)
        if send_email("steam_monitor: test email", "This test email was sent by --send-test-email. Your SMTP settings work.", "", SMTP_SSL, smtp_timeout=5) == 0:
            print("* Email sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if args.send_test_webhook:
        print("* Sending test webhook notification ...\n")
        debug_print("Test webhook", channel=normalized_webhook_provider() or "an unset provider", host=webhook_destination_host())
        if send_webhook("steam_monitor: test webhook", "This test notification was sent by --send-test-webhook. Your webhook settings work.", "status", force=True) == 0:
            print("* Webhook sent successfully !")
        else:
            sys.exit(1)
        sys.exit(0)

    if not STEAM_API_KEY or STEAM_API_KEY == "your_steam_web_api_key":
        print_recovery_error(context="set_steam_api_key", detail="No Steam Web API key is configured")
        sys.exit(1)

    if args.check_interval:
        STEAM_CHECK_INTERVAL = args.check_interval
        LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / STEAM_CHECK_INTERVAL

    if args.active_interval:
        STEAM_ACTIVE_CHECK_INTERVAL = args.active_interval

    s_id = 0
    try:
        if args.resolve_community_url:
            print(f"* Resolving Steam community URL to Steam64 ID: {args.resolve_community_url}\n")
            s_id = resolve_steam_community_url(args.resolve_community_url, STEAM_API_KEY)
        elif args.steam64_id or TARGET_STEAM_ID:
            s_id = resolve_steam_target(args.steam64_id or TARGET_STEAM_ID, STEAM_API_KEY)
    except ValueError as e:
        print_recovery_error(e, context="target")
        sys.exit(1)

    if not s_id:
        # Check should have been handled earlier by the utility_flags logic
        print_recovery_error(context="target", detail="No Steam profile target was given")
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
            print_recovery_error(e, context="file", detail=f"CSV file '{CSV_FILE}' cannot be opened for writing")
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
            print_recovery_error(e, context="file", detail=f"Profile CSV file '{PROFILE_CSV_FILE}' cannot be opened for writing")
            sys.exit(1)

    # A configured FILE_SUFFIX is documented as replacing the Steam ID, so only an unset value falls back to it
    if args.file_suffix:
        FILE_SUFFIX = args.file_suffix
    elif not FILE_SUFFIX:
        FILE_SUFFIX = str(s_id)

    if args.no_color is True:
        COLORED_OUTPUT = False

    try:
        ascii_log_separators_enabled()
    except ValueError as e:
        print_recovery_error(e, context="config")
        sys.exit(1)

    if args.disable_logging is True:
        DISABLE_LOGGING = True

    TRUNCATE_CHARS = resolve_truncate_chars(args.truncate, TRUNCATE_CHARS, DISABLE_LOGGING)

    # Re-initialize colour output to pick up any theme changes from config/dotenv
    init_color_output(stdout_bck)

    if not DISABLE_LOGGING:
        # Shared with doctor, so the path it reports is the one monitoring opens
        log_path = build_log_path(ST_LOGFILE, FILE_SUFFIX)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        FINAL_LOG_PATH = str(log_path)
        sys.stdout = Logger(FINAL_LOG_PATH, strip_ansi=True)
    else:
        FINAL_LOG_PATH = None
        # Even when logging is disabled, keep coloured output on the terminal.
        sys.stdout = ColorStream(stdout_bck)

    # Handle info mode - display user information once and exit
    if args.info:
        display_user_info(s_id, list_friends=getattr(args, "list_friends", False), show_name_history=getattr(args, "show_name_history", False), show_achievements=getattr(args, "show_achievements", False), achievements_count=getattr(args, "achievements_count", None), achievements_use_owned_games=getattr(args, "achievements_use_owned_games", False))
        sys.stdout = stdout_bck
        sys.exit(0)

    if args.notify_active_inactive is True:
        ACTIVE_INACTIVE_NOTIFICATION = True

    if args.notify_game_change is True:
        GAME_CHANGE_NOTIFICATION = True

    if args.notify_status is True:
        STATUS_NOTIFICATION = True

    if args.notify_name_change is True:
        NAME_CHANGE_NOTIFICATION = True

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
    if getattr(args, "check_games", None) is True:
        GAMES_LIBRARY_CHECK = True
    if getattr(args, "notify_games", None) is True:
        GAMES_LIBRARY_NOTIFICATION = True

    if SMTP_HOST.startswith("your_smtp_server_"):
        verbose_print("Email notifications are off because SMTP_HOST is still the shipped placeholder")
        ACTIVE_INACTIVE_NOTIFICATION = False
        GAME_CHANGE_NOTIFICATION = False
        STATUS_NOTIFICATION = False
        NAME_CHANGE_NOTIFICATION = False
        ERROR_NOTIFICATION = False
        STEAM_LEVEL_XP_NOTIFICATION = False
        FRIENDS_NOTIFICATION = False
        GAMES_LIBRARY_NOTIFICATION = False
    if WEBHOOK_ENABLED and not validate_webhook_url():
        verbose_print("Webhook notifications are off because WEBHOOK_URL is not a complete HTTPS link")
        WEBHOOK_ENABLED = False

    emit_startup_summary(build_startup_summary(s_id, cfg_path, env_path, FINAL_LOG_PATH), show_full=full_startup_summary_enabled())

    if NTFY_IMAGES and not NTFY_IMAGES_AVAILABLE:
        NTFY_IMAGES = False
        if WEBHOOK_ENABLED and normalized_webhook_provider() == "ntfy":
            print(f"* Warning: ntfy artwork is enabled, but the optional 'Pillow' package is not installed\n\nTo attach artwork, run:\n    {ntfy_images_install_command()}\n\nOnce installed, re-run this tool. To stop this warning, set NTFY_IMAGES to False\n\nSending ntfy alerts as text only...\n")

    # The line coloriser colours the ID, so the printed text stays plain and the separator matches its width
    out = f"Monitoring user with Steam64 ID {s_id}"
    # The summary block already ended with one blank line, so this heading starts at the cursor
    print(out)
    print("─" * len(out))

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
        signal.signal(signal.SIGUSR2, toggle_game_change_notifications_signal_handler)
        signal.signal(signal.SIGCONT, toggle_all_status_changes_notifications_signal_handler)
        signal.signal(signal.SIGURG, toggle_level_xp_notifications_signal_handler)
        signal.signal(signal.SIGPIPE, toggle_friends_notifications_signal_handler)
        signal.signal(signal.SIGVTALRM, toggle_name_change_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)
        signal.signal(signal.SIGHUP, reload_secrets_signal_handler)

    steam_monitor_user(s_id, CSV_FILE, PROFILE_CSV_FILE)

    sys.stdout = stdout_bck
    sys.exit(0)


if __name__ == "__main__":
    main()

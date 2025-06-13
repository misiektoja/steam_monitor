#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.3.1

Tool implementing real-time tracking of Steam players activities:
https://github.com/misiektoja/steam_monitor/

Python pip3 requirements:

steam[client]
requests
python-dateutil
python-dotenv (optional)
"""

VERSION = "1.3.1"

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
STEAM_CHECK_INTERVAL = 0
STEAM_ACTIVE_CHECK_INTERVAL = 0
OFFLINE_INTERRUPT = 0
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

exec(CONFIG_BLOCK, globals())

# Default name for the optional config file
DEFAULT_CONFIG_FILENAME = "steam_monitor.conf"

# List of secret keys to load from env/config
SECRET_KEYS = ("STEAM_API_KEY", "SMTP_PASSWORD")

LIVENESS_CHECK_COUNTER = LIVENESS_CHECK_INTERVAL / STEAM_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Status', 'Game name', 'Game ID']

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
import re
import ipaddress
try:
    import steam.steamid
    import steam.webapi
except ModuleNotFoundError:
    raise SystemExit("Error: Couldn't find the Steam library !\n\nTo install it, run:\n    pip3 install \"steam[client]\"\n\nOnce installed, re-run this tool. For more help, visit:\nhttps://github.com/ValvePython/steam/")
import shutil
from pathlib import Path


# Logger class to output messages to stdout and log file
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")

    def write(self, message):
        self.terminal.write(message)
        self.logfile.write(message)
        self.terminal.flush()
        self.logfile.flush()

    def flush(self):
        pass


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


# Returns the current date/time in human readable format; eg. Sun 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f'{ts_str}{calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]}, {datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")}')


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


# Main function that monitors gaming activity of the specified Steam user
def steam_monitor_user(steamid, csv_file_name):

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

    try:
        if csv_file_name:
            init_csv_file(csv_file_name)
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

    print(f"\nDisplay name:\t\t\t{username}")

    if realname:
        print(f"Real name:\t\t\t{realname}")

    print(f"\nStatus:\t\t\t\t{str(steam_personastates[status]).upper()}")
    print(f"Profile visibility:\t\t{steam_visibilitystates[visibilitystate]}")

    if timecreated:
        print(f"Account creation date:\t\t{get_date_from_ts(timecreated)}")

    if last_status_ts == 0:
        if lastlogoff and status == 0:
            status_ts_old = lastlogoff
        last_status_to_save = []
        last_status_to_save.append(status_ts_old)
        last_status_to_save.append(status)
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

    if "games" in s_played["response"].keys():
        print(f"\nList of recently played games:")
        for i, game in enumerate(s_played["response"]["games"]):
            print(f"{i + 1} {game.get('name')}")

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
        try:
            s_api = steam.webapi.WebAPI(key=STEAM_API_KEY)
            s_user = s_api.call('ISteamUser.GetPlayerSummaries', steamids=str(steamid))
            s_played = s_api.call('IPlayerService.GetRecentlyPlayedGames', steamid=steamid, count=5)
            status = int(s_user["response"]["players"][0]["personastate"])
            gameid = s_user["response"]["players"][0].get("gameid")
            gamename = s_user["response"]["players"][0].get("gameextrainfo", "")
            email_sent = False
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

            # Player got online
            if status_old == 0 and status > 0:
                print(f"*** User got ACTIVE ! (was offline since {get_date_from_ts(status_ts_old)})")
                game_total_after_offline_counted = False
                if (status_ts - status_ts_old) > OFFLINE_INTERRUPT or not status_online_start_ts_old:
                    status_online_start_ts = status_ts
                    game_total_ts = 0
                    games_number = 0
                elif (status_ts - status_ts_old) <= OFFLINE_INTERRUPT and status_online_start_ts_old > 0:
                    status_online_start_ts = status_online_start_ts_old
                    m_body_short_offline_msg = f"\n\nShort offline interruption ({display_time(status_ts - status_ts_old)}), online start timestamp set back to {get_short_date_from_ts(status_online_start_ts_old)}"
                    print(f"Short offline interruption ({display_time(status_ts - status_ts_old)}), online start timestamp set back to {get_short_date_from_ts(status_online_start_ts_old)}")
                act_inact_flag = True

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
            m_body = f"Steam user {username} changed status from {steam_personastates[status_old]} to {steam_personastates[status]}\n\nUser was {steam_personastates[status_old]} for {calculate_timespan(int(status_ts), int(status_ts_old))}{m_body_was_since}{m_body_short_offline_msg}{m_body_user_in_game}{m_body_played_games}{get_cur_ts(nl_ch + nl_ch + 'Timestamp: ')}"
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
    global CLI_CONFIG_PATH, DOTENV_FILE, LIVENESS_CHECK_COUNTER, STEAM_API_KEY, CSV_FILE, DISABLE_LOGGING, ST_LOGFILE, ACTIVE_INACTIVE_NOTIFICATION, GAME_CHANGE_NOTIFICATION, STATUS_NOTIFICATION, ERROR_NOTIFICATION, STEAM_CHECK_INTERVAL, STEAM_ACTIVE_CHECK_INTERVAL, FILE_SUFFIX, SMTP_PASSWORD, stdout_bck

    if "--generate-config" in sys.argv:
        print(CONFIG_BLOCK.strip("\n"))
        sys.exit(0)

    if "--version" in sys.argv:
        print(f"{os.path.basename(sys.argv[0])} v{VERSION}")
        sys.exit(0)

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    clear_screen(CLEAR_SCREEN)

    print(f"Steam Monitoring Tool v{VERSION}\n")

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
        action="store_true",
        help="Print default config template and exit",
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
        "-b", "--csv-file",
        dest="csv_file",
        metavar="CSV_FILENAME",
        type=str,
        help="Write status & game changes to CSV"
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

    args = parser.parse_args()

    if len(sys.argv) == 1:
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

    if args.file_suffix:
        FILE_SUFFIX = args.file_suffix
    else:
        FILE_SUFFIX = str(s_id)

    if args.disable_logging is True:
        DISABLE_LOGGING = True

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
        sys.stdout = Logger(FINAL_LOG_PATH)
    else:
        FINAL_LOG_PATH = None

    if args.notify_active_inactive is True:
        ACTIVE_INACTIVE_NOTIFICATION = True

    if args.notify_game_change is True:
        GAME_CHANGE_NOTIFICATION = True

    if args.notify_status is True:
        STATUS_NOTIFICATION = True

    if args.notify_errors is False:
        ERROR_NOTIFICATION = False

    if SMTP_HOST.startswith("your_smtp_server_"):
        ACTIVE_INACTIVE_NOTIFICATION = False
        GAME_CHANGE_NOTIFICATION = False
        STATUS_NOTIFICATION = False
        ERROR_NOTIFICATION = False

    print(f"* Steam polling intervals:\t[offline: {display_time(STEAM_CHECK_INTERVAL)}] [online: {display_time(STEAM_ACTIVE_CHECK_INTERVAL)}]")
    print(f"* Email notifications:\t\t[online/offline status changes = {ACTIVE_INACTIVE_NOTIFICATION}] [game changes = {GAME_CHANGE_NOTIFICATION}]\n*\t\t\t\t[all status changes = {STATUS_NOTIFICATION}] [errors = {ERROR_NOTIFICATION}]")
    print(f"* Liveness check:\t\t{bool(LIVENESS_CHECK_INTERVAL)}" + (f" ({display_time(LIVENESS_CHECK_INTERVAL)})" if LIVENESS_CHECK_INTERVAL else ""))
    print(f"* CSV logging enabled:\t\t{bool(CSV_FILE)}" + (f" ({CSV_FILE})" if CSV_FILE else ""))
    print(f"* Output logging enabled:\t{not DISABLE_LOGGING}" + (f" ({FINAL_LOG_PATH})" if not DISABLE_LOGGING else ""))
    print(f"* Configuration file:\t\t{cfg_path}")
    print(f"* Dotenv file:\t\t\t{env_path or 'None'}")

    out = f"\nMonitoring user with Steam64 ID {s_id}"
    print(out)
    print("-" * len(out))

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
        signal.signal(signal.SIGUSR2, toggle_game_change_notifications_signal_handler)
        signal.signal(signal.SIGCONT, toggle_all_status_changes_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)
        signal.signal(signal.SIGHUP, reload_secrets_signal_handler)

    steam_monitor_user(s_id, CSV_FILE)

    sys.stdout = stdout_bck
    sys.exit(0)


if __name__ == "__main__":
    main()

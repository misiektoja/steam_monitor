#!/usr/bin/env python3
"""
Author: Michal Szymanski <misiektoja-github@rm-rf.ninja>
v1.1

Script implementing real-time monitoring of Steam players activity:
https://github.com/misiektoja/steam_monitor/

Python pip3 requirements:

steam[client]
python-dateutil
requests
"""

VERSION = 1.1

# ---------------------------
# CONFIGURATION SECTION START
# ---------------------------

# Get the Steam Web API key from: http://steamcommunity.com/dev/apikey
# Put the respective value below (or use -u parameter)
STEAM_API_KEY = "your_steam_web_api_key"

# SMTP settings for sending email notifications, you can leave it as it is below and no notifications will be sent
SMTP_HOST = "your_smtp_server_ssl"
SMTP_PORT = 587
SMTP_USER = "your_smtp_user"
SMTP_PASSWORD = "your_smtp_password"
SMTP_SSL = True
SENDER_EMAIL = "your_sender_email"
#SMTP_HOST = "mail.upcpoczta.pl"
#SMTP_PORT = 25
#SMTP_USER = "asz180312@upcpoczta.pl"
#SMTP_PASSWORD = "vWyuW7wrZGy7W45"
#SMTP_SSL = False
#SENDER_EMAIL = "asz180312@upcpoczta.pl"
RECEIVER_EMAIL = "your_receiver_email"

# How often do we perform checks for player activity when user is offline, you can also use -c parameter; in seconds
STEAM_CHECK_INTERVAL = 90  # 1.5 min

# How often do we perform checks for player activity when user is online/away/snooze, you can also use -k parameter; in seconds
STEAM_ACTIVE_CHECK_INTERVAL = 30  # 30 sec

# How often do we perform alive check by printing "alive check" message in the output; in seconds
TOOL_ALIVE_INTERVAL = 21600  # 6 hours

# If user gets offline and online again (for example due to rebooting the PC) during the next OFFLINE_INTERRUPT seconds then we set online start timestamp back to the previous one (so called short offline interruption)
OFFLINE_INTERRUPT = 420  # 7 mins

# URL we check in the beginning to make sure we have internet connectivity
CHECK_INTERNET_URL = 'http://www.google.com/'

# Default value for initial checking of internet connectivity; in seconds
CHECK_INTERNET_TIMEOUT = 5

# The name of the .log file; the tool by default will output its messages to steam_monitor_usersteamid.log file
ST_LOGFILE = "steam_monitor"

# Value used by signal handlers increasing/decreasing the check for player activity when user is online/away/snooze; in seconds
STEAM_ACTIVE_CHECK_SIGNAL_VALUE = 30  # 30 seconds

# -------------------------
# CONFIGURATION SECTION END
# -------------------------

TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / STEAM_CHECK_INTERVAL

stdout_bck = None
csvfieldnames = ['Date', 'Status', 'Game name', 'Game ID']

steam_personastates = ["offline", "online", "busy", "away", "snooze", "looking to trade", "looking to play"]
steam_visibilitystates = ["private", "private", "private", "public"]

active_inactive_notification = False
game_change_notification = False
status_notification = False


import sys
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
import steam.steamid
import steam.client
import steam.webapi


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


# Function to check internet connectivity
def check_internet():
    url = CHECK_INTERNET_URL
    try:
        _ = req.get(url, timeout=CHECK_INTERNET_TIMEOUT)
        print("OK")
        return True
    except Exception as e:
        print(f"No connectivity, please check your network - {e}")
        sys.exit(1)
    return False


# Function to convert absolute value of seconds to human readable format
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


# Function to calculate time span between two timestamps in seconds
def calculate_timespan(timestamp1, timestamp2, show_weeks=True, show_hours=True, show_minutes=True, show_seconds=True, granularity=3):
    result = []
    intervals = ['years', 'months', 'weeks', 'days', 'hours', 'minutes', 'seconds']
    ts1 = timestamp1
    ts2 = timestamp2

    if type(timestamp1) is int:
        dt1 = datetime.fromtimestamp(int(ts1))
    elif type(timestamp1) is datetime:
        dt1 = timestamp1
        ts1 = int(round(dt1.timestamp()))
    else:
        return ""

    if type(timestamp2) is int:
        dt2 = datetime.fromtimestamp(int(ts2))
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


# Function to send email notification
def send_email(subject, body, body_html, use_ssl):
    fqdn_re = re.compile(r'(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)')
    email_re = re.compile(r'[^@]+@[^@]+\.[^@]+')

    try:
        is_ip = ipaddress.ip_address(str(SMTP_HOST))
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
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            smtpObj.starttls(context=ssl_context)
        else:
            smtpObj = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        smtpObj.login(SMTP_USER, SMTP_PASSWORD)
        email_msg = MIMEMultipart('alternative')
        email_msg["From"] = SENDER_EMAIL
        email_msg["To"] = RECEIVER_EMAIL
        email_msg["Subject"] = Header(subject, 'utf-8')

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
        print(f"Error sending email - {e}")
        return 1
    return 0


# Function to write CSV entry
def write_csv_entry(csv_file_name, timestamp, status, gamename, gameid):
    try:
        csv_file = open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8")
        csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
        csvwriter.writerow({'Date': timestamp, 'Status': status, 'Game name': gamename, 'Game ID': gameid})
        csv_file.close()
    except Exception as e:
        raise


# Function to return the timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def get_cur_ts(ts_str=""):
    return (f"{ts_str}{calendar.day_abbr[(datetime.fromtimestamp(int(time.time()))).weekday()]}, {datetime.fromtimestamp(int(time.time())).strftime("%d %b %Y, %H:%M:%S")}")


# Function to print the current timestamp in human readable format; eg. Sun, 21 Apr 2024, 15:08:45
def print_cur_ts(ts_str=""):
    print(get_cur_ts(str(ts_str)))
    print("---------------------------------------------------------------------------------------------------------")


# Function to return the timestamp in human readable format (long version); eg. Sun, 21 Apr 2024, 15:08:45
def get_date_from_ts(ts):
    return (f"{calendar.day_abbr[(datetime.fromtimestamp(ts)).weekday()]} {datetime.fromtimestamp(ts).strftime("%d %b %Y, %H:%M:%S")}")


# Function to return the timestamp in human readable format (short version); eg. Sun 21 Apr 15:08
def get_short_date_from_ts(ts):
    return (f"{calendar.day_abbr[(datetime.fromtimestamp(ts)).weekday()]} {datetime.fromtimestamp(ts).strftime("%d %b %H:%M")}")


# Function to return the timestamp in human readable format (only hour, minutes and optionally seconds): eg. 15:08:12
def get_hour_min_from_ts(ts, show_seconds=False):
    if show_seconds:
        out_strf = "%H:%M:%S"
    else:
        out_strf = "%H:%M"
    return (str(datetime.fromtimestamp(ts).strftime(out_strf)))


# Function to return the range between two timestamps; eg. Sun 21 Apr 14:09 - 14:15
def get_range_of_dates_from_tss(ts1, ts2, between_sep=" - ", short=False):
    ts1_strf = datetime.fromtimestamp(ts1).strftime("%Y%m%d")
    ts2_strf = datetime.fromtimestamp(ts2).strftime("%Y%m%d")

    if ts1_strf == ts2_strf:
        if short:
            out_str = f"{get_short_date_from_ts(ts1)}{between_sep}{get_hour_min_from_ts(ts2)}"
        else:
            out_str = f"{get_date_from_ts(ts1)}{between_sep}{get_hour_min_from_ts(ts2, show_seconds=True)}"
    else:
        if short:
            out_str = f"{get_short_date_from_ts(ts1)}{between_sep}{get_short_date_from_ts(ts2)}"
        else:
            out_str = f"{get_date_from_ts(ts1)}{between_sep}{get_date_from_ts(ts2)}"
    return (str(out_str))


# Signal handler for SIGUSR1 allowing to switch active/inactive email notifications
def toggle_active_inactive_notifications_signal_handler(sig, frame):
    global active_inactive_notification
    active_inactive_notification = not active_inactive_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [active/inactive status changes = {active_inactive_notification}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGUSR2 allowing to switch played game changes notifications
def toggle_game_change_notifications_signal_handler(sig, frame):
    global game_change_notification
    game_change_notification = not game_change_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [game changes = {game_change_notification}]")
    print_cur_ts("Timestamp:\t\t\t")


# Signal handler for SIGCONT allowing to switch all status changes notifications
def toggle_all_status_changes_notifications_signal_handler(sig, frame):
    global status_notification
    status_notification = not status_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [all status changes = {status_notification}]")
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


# Main function monitoring gaming activity of the specified Steam user
def steam_monitor_user(steamid, error_notification, csv_file_name, csv_exists):

    alive_counter = 0
    status_ts = 0
    status_ts_old = 0
    status_online_start_ts = 0
    status_online_start_ts_old = 0
    game_ts = 0
    game_ts_old = 0
    status = 0

    try:
        if csv_file_name:
            csv_file = open(csv_file_name, 'a', newline='', buffering=1, encoding="utf-8")
            csvwriter = csv.DictWriter(csv_file, fieldnames=csvfieldnames, quoting=csv.QUOTE_NONNUMERIC)
            if not csv_exists:
                csvwriter.writeheader()
            csv_file.close()
    except Exception as e:
        print(f"* Error - {e}")

    try:
        s_api = steam.webapi.WebAPI(key=STEAM_API_KEY)
        s_api.ISteamUser.GetPlayerSummaries(steamids=str(steamid))
        s_user = s_api.call('ISteamUser.GetPlayerSummaries', steamids=str(steamid))
        s_api.IPlayerService.GetRecentlyPlayedGames(steamid=steamid, count=5)
        s_played = s_api.call('IPlayerService.GetRecentlyPlayedGames', steamid=steamid, count=5)
    except Exception as e:
        print(f"Error - {e}")
        sys.exit(1)

    try:
        username = s_user["response"]["players"][0].get("personaname")
    except:
        print(f"Error: user with Steam ID {steamid} does not exist!")
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

    try:
        if os.path.isfile(steam_last_status_file):
            with open(steam_last_status_file, 'r', encoding="utf-8") as f:
                last_status_read = json.load(f)
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
                    with open(steam_last_status_file, 'w', encoding="utf-8") as f:
                        json.dump(last_status_to_save, f, indent=2)

    except Exception as e:
        print(f"Error - {e}")

    try:
        if csv_file_name and (status != last_status):
            write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), steam_personastates[status], gamename, gameid)
    except Exception as e:
        print(f"* Error: cannot write CSV entry - {e}")

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
        with open(steam_last_status_file, 'w', encoding="utf-8") as f:
            json.dump(last_status_to_save, f, indent=2)

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

    if "games" in s_played["response"].keys():
        print(f"\nList of recently played games:")
        for i, game in enumerate(s_played["response"]["games"]):
            print(f"{i + 1} {game.get("name")}")

    status_old = status
    gameid_old = gameid
    gamename_old = gamename

    print_cur_ts("\nTimestamp:\t\t\t")

    alive_counter = 0

    # Main loop
    while True:
        try:
            s_api = steam.webapi.WebAPI(key=STEAM_API_KEY)
            s_api.ISteamUser.GetPlayerSummaries(steamids=str(steamid))
            s_user = s_api.call('ISteamUser.GetPlayerSummaries', steamids=str(steamid))
            s_api.IPlayerService.GetRecentlyPlayedGames(steamid=steamid, count=5)
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
            print(f"Error, retrying in {display_time(sleep_interval)} - {e}")
            if 'Forbidden' in str(e):
                print("* API key might not be valid anymore!")
                if error_notification and not email_sent:
                    m_subject = f"steam_monitor: API key error! (user: {username})"
                    m_body = f"API key might not be valid anymore: {e}{get_cur_ts("\n\nTimestamp: ")}"
                    print(f"Sending email notification to {RECEIVER_EMAIL}")
                    send_email(m_subject, m_body, "", SMTP_SSL)
                    email_sent = True

            print_cur_ts("Timestamp:\t\t\t")

            time.sleep(sleep_interval)

            continue

        change = False
        act_inact_flag = False

        # Player status changed
        if status != status_old:
            status_ts = int(time.time())

            last_status_to_save = []
            last_status_to_save.append(status_ts)
            last_status_to_save.append(status)
            with open(steam_last_status_file, 'w', encoding="utf-8") as f:
                json.dump(last_status_to_save, f, indent=2)

            print(f"Steam user {username} changed status from {steam_personastates[status_old]} to {steam_personastates[status]}")
            print(f"User was {steam_personastates[status_old]} for {calculate_timespan(int(status_ts), int(status_ts_old))} ({get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)})")

            m_subject_was_since = f", was {steam_personastates[status_old]}: {get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)}"
            m_subject_after = calculate_timespan(int(status_ts), int(status_ts_old), show_seconds=False)
            m_body_was_since = f" ({get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)})"

            # Player got online
            if status_old == 0 and status > 0:
                print(f"*** User got ACTIVE ! (was offline since {get_date_from_ts(status_ts_old)})")
                if (status_ts - status_ts_old) > OFFLINE_INTERRUPT:
                    status_online_start_ts = status_ts
                else:
                    status_online_start_ts = status_online_start_ts_old
                    print(f"Short offline interruption, online start timestamp set back to {get_date_from_ts(status_online_start_ts_old)}")
                act_inact_flag = True

            # Player got offline
            if status_old > 0 and status == 0:
                if status_online_start_ts > 0:
                    m_subject_after = calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)
                    online_since_msg = f"(after {calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)}: {get_range_of_dates_from_tss(int(status_online_start_ts), int(status_ts), short=True)})"
                    m_subject_was_since = f", was available: {get_range_of_dates_from_tss(int(status_online_start_ts), int(status_ts), short=True)}"
                    m_body_was_since = f" ({get_range_of_dates_from_tss(int(status_ts_old), int(status_ts), short=True)})\n\nUser was available for {calculate_timespan(int(status_ts), int(status_online_start_ts), show_seconds=False)} ({get_range_of_dates_from_tss(int(status_online_start_ts), int(status_ts), short=True)})"
                else:
                    online_since_msg = ""
                print(f"*** User got OFFLINE ! {online_since_msg}")
                status_online_start_ts_old = status_online_start_ts
                status_online_start_ts = 0
                act_inact_flag = True

            user_in_game = ""
            if gameid:
                print(f"User is currently in-game: {gamename}")
                user_in_game = f"\n\nUser is currently in-game: {gamename}"

            change = True

            m_subject = f"Steam user {username} is now {steam_personastates[status]} (after {m_subject_after}{m_subject_was_since})"
            m_body = f"Steam user {username} changed status from {steam_personastates[status_old]} to {steam_personastates[status]}\n\nUser was {steam_personastates[status_old]} for {calculate_timespan(int(status_ts), int(status_ts_old))}{m_body_was_since}{user_in_game}{get_cur_ts("\n\nTimestamp: ")}"
            if status_notification or (active_inactive_notification and act_inact_flag):
                print(f"Sending email notification to {RECEIVER_EMAIL}")
                send_email(m_subject, m_body, "", SMTP_SSL)
            status_ts_old = status_ts

        # Player started/stopped/changed the game
        if gameid != gameid_old:
            game_ts = int(time.time())

            # User changed the game
            if gameid_old and gameid:
                print(f"Steam user {username} changed game from '{gamename_old}' to '{gamename}' after {calculate_timespan(int(game_ts), int(game_ts_old))}")
                print(f"User played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=" to ")}")
                m_subject = f"Steam user {username} changed game to '{gamename}' (after {calculate_timespan(int(game_ts), int(game_ts_old), show_seconds=False)}: {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True)})"
                m_body = f"Steam user {username} changed game from '{gamename_old}' to '{gamename}' after {calculate_timespan(int(game_ts), int(game_ts_old))}\n\nUser played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=" to ")}{get_cur_ts("\n\nTimestamp: ")}"

            # User started playing new game
            elif not gameid_old and gameid:
                print(f"Steam user {username} started playing '{gamename}'")
                m_subject = f"Steam user {username} now plays '{gamename}'"
                m_body = f"Steam user {username} now plays '{gamename}'{get_cur_ts("\n\nTimestamp: ")}"

            # User stopped playing the game
            elif gameid_old and not gameid:
                print(f"Steam user {username} stopped playing '{gamename_old}' after {calculate_timespan(int(game_ts), int(game_ts_old))}")
                print(f"User played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=" to ")}")
                m_subject = f"Steam user {username} stopped playing '{gamename_old}' (after {calculate_timespan(int(game_ts), int(game_ts_old), show_seconds=False)}: {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True)})"
                m_body = f"Steam user {username} stopped playing '{gamename_old}' after {calculate_timespan(int(game_ts), int(game_ts_old))}\n\nUser played game from {get_range_of_dates_from_tss(int(game_ts_old), int(game_ts), short=True, between_sep=" to ")}{get_cur_ts("\n\nTimestamp: ")}"

            change = True

            if game_change_notification:
                print(f"Sending email notification to {RECEIVER_EMAIL}")
                send_email(m_subject, m_body, "", SMTP_SSL)

            game_ts_old = game_ts

        if change:
            alive_counter = 0

            try:
                if csv_file_name:
                    write_csv_entry(csv_file_name, datetime.fromtimestamp(int(time.time())), steam_personastates[status], gamename, gameid)
            except Exception as e:
                print(f"* Error: cannot write CSV entry - {e}")

            print_cur_ts("Timestamp:\t\t\t")

        status_old = status
        gameid_old = gameid
        gamename_old = gamename
        alive_counter += 1

        if alive_counter >= TOOL_ALIVE_COUNTER and status == 0:
            print_cur_ts("Alive check, timestamp:\t\t")
            alive_counter = 0

        if status > 0:
            time.sleep(STEAM_ACTIVE_CHECK_INTERVAL)
        else:
            time.sleep(STEAM_CHECK_INTERVAL)

if __name__ == "__main__":

    stdout_bck = sys.stdout

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            os.system('clear')
    except:
        print("* Cannot clear the screen contents")

    print(f"Steam Monitoring Tool v{VERSION}\n")

    parser = argparse.ArgumentParser("steam_monitor")
    parser.add_argument("STEAM_ID", nargs="?", help="User's Steam ID (steam64)", type=int)
    parser.add_argument("-u", "--steam_api_key", help="Steam Web API key to override the value defined within the script (STEAM_API_KEY)", type=str)
    parser.add_argument("-r", "--resolve_community_url", help="Use Steam community URL & resolve it to Steam ID (steam64)", type=str)
    parser.add_argument("-a", "--active_inactive_notification", help="Send email notification once user changes status from active to inactive and vice versa (online/offline)", action='store_true')
    parser.add_argument("-g", "--game_change_notification", help="Send email notification once user starts/changes/stops playing the game", action='store_true')
    parser.add_argument("-s", "--status_notification", help="Send email notification for all player status changes (online/away/snooze/offline)", action='store_true')
    parser.add_argument("-e", "--error_notification", help="Disable sending email notifications in case of errors like invalid API key", action='store_false')
    parser.add_argument("-c", "--check_interval", help="Time between monitoring checks if user is offline, in seconds", type=int)
    parser.add_argument("-k", "--active_check_interval", help="Time between monitoring checks if user is NOT offline, in seconds", type=int)
    parser.add_argument("-b", "--csv_file", help="Write all status & game changes to CSV file", type=str, metavar="CSV_FILENAME")
    parser.add_argument("-d", "--disable_logging", help="Disable logging to file 'steam_monitor_user.log' file", action='store_true')
    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.steam_api_key:
        STEAM_API_KEY = args.steam_api_key

    if not STEAM_API_KEY or STEAM_API_KEY == "your_steam_web_api_key":
        print("* Error: STEAM_API_KEY (-u / --steam_api_key) value is empty or incorrect")
        sys.exit(1)

    if args.check_interval:
        STEAM_CHECK_INTERVAL = args.check_interval
        TOOL_ALIVE_COUNTER = TOOL_ALIVE_INTERVAL / STEAM_CHECK_INTERVAL

    if args.active_check_interval:
        STEAM_ACTIVE_CHECK_INTERVAL = args.active_check_interval

    s_id = 0
    if args.STEAM_ID:
        s_id = int(args.STEAM_ID)

    sys.stdout.write("* Checking internet connectivity ... ")
    sys.stdout.flush()
    check_internet()
    print("")

    if args.resolve_community_url:
        print(f"* Resolving Steam community URL to Steam ID: {args.resolve_community_url}\n")
        try:
            s_id = steam.steamid.steam64_from_url(args.resolve_community_url)
            if s_id:
                s_id = int(s_id)
        except Exception as e:
            print("* Error: cannot get Steam ID for specified community URL")
            print("*", e)
            sys.exit(1)

    if not s_id:
        print("* Error: STEAM_ID needs to be defined !")
        sys.exit(1)

    if args.csv_file:
        csv_enabled = True
        csv_exists = os.path.isfile(args.csv_file)
        try:
            csv_file = open(args.csv_file, 'a', newline='', buffering=1, encoding="utf-8")
        except Exception as e:
            print(f"* Error: CSV file cannot be opened for writing - {e}")
            sys.exit(1)
        csv_file.close()
    else:
        csv_enabled = False
        csv_file = None
        csv_exists = False

    if not args.disable_logging:
        ST_LOGFILE = f"{ST_LOGFILE}_{s_id}.log"
        sys.stdout = Logger(ST_LOGFILE)

    active_inactive_notification = args.active_inactive_notification
    game_change_notification = args.game_change_notification
    status_notification = args.status_notification

    print(f"* Steam timers:\t\t\t[check interval: {display_time(STEAM_CHECK_INTERVAL)}] [active check interval: {display_time(STEAM_ACTIVE_CHECK_INTERVAL)}]")
    print(f"* Email notifications:\t\t[active/inactive status changes = {active_inactive_notification}] [game changes = {game_change_notification}]\n*\t\t\t\t[all status changes = {status_notification}] [errors = {args.error_notification}]")
    print(f"* Output logging disabled:\t{args.disable_logging}")
    if csv_enabled:
        print(f"* CSV logging enabled:\t\t{csv_enabled} ({args.csv_file})")
    else:
        print(f"* CSV logging enabled:\t\t{csv_enabled}")

    out = f"\nMonitoring user with Steam ID {s_id}"
    print(out)
    print("-" * len(out))

    # We define signal handlers only for Linux, Unix & MacOS since Windows has limited number of signals supported
    if platform.system() != 'Windows':
        signal.signal(signal.SIGUSR1, toggle_active_inactive_notifications_signal_handler)
        signal.signal(signal.SIGUSR2, toggle_game_change_notifications_signal_handler)
        signal.signal(signal.SIGCONT, toggle_all_status_changes_notifications_signal_handler)
        signal.signal(signal.SIGTRAP, increase_active_check_signal_handler)
        signal.signal(signal.SIGABRT, decrease_active_check_signal_handler)

    steam_monitor_user(s_id, args.error_notification, args.csv_file, csv_exists)

    sys.stdout = stdout_bck
    sys.exit(0)

"""Tests for the HTML notification body, its Discord markdown form and its match with the plain text."""

import copy
import difflib
import html as html_module
import json
import os
import re
import time
from pathlib import Path

import pytest

import steam_monitor as monitor


STEAM_ID = 76561201960435530
PROFILE_URL = "https://steamcommunity.com/id/testplayer/"
AVATAR_URL = "https://avatars.steamstatic.com/test_full.jpg"

FRIEND_PROFILES = {
    "1": {"personaname": "FirstFriend", "realname": "First Person"},
    "2": {"personaname": "SecondFriend", "realname": ""},
}

APP_NAMES = {440: "Team Fortress 2", 570: "Dota 2"}


# One monitoring cycle's worth of Steam state, so a scenario reads as the timeline it represents
def cycle(personaname="TestPlayer", personastate=0, gameid=None, gamename="", level=42, xp=5000, friends=("1",), owned=(440,)):
    return {"personaname": personaname, "personastate": personastate, "gameid": gameid, "gamename": gamename, "level": level, "xp": xp, "friends": tuple(friends), "owned": tuple(owned)}


# The timeline that fires every notification the monitor can send at least once
SCENARIO = [
    cycle(),
    cycle(personastate=1),
    cycle(personastate=1, gameid=440, gamename="Team Fortress 2"),
    cycle(personastate=1, gameid=570, gamename="Dota 2"),
    cycle(personastate=1),
    cycle(personastate=3),
    cycle(personastate=4),
    cycle(personastate=0, owned=(440, 570)),
    cycle(level=43, xp=5400),
    cycle(level=43, xp=5400, friends=("1", "2")),
    cycle(level=43, xp=5400, friends=("2",)),
    cycle(personaname="RenamedPlayer", level=43, xp=5400, friends=("2",)),
]


class StopScenario(Exception):
    pass


class ScriptedSteamWebAPI:
    # Answers each Steam endpoint from the scenario entry for the current cycle
    def __init__(self, scenario, fail_cycles=()):
        self.scenario = scenario
        self.fail_cycles = set(fail_cycles)
        self.index = 0

    @property
    def state(self):
        return self.scenario[min(self.index, len(self.scenario) - 1)]

    def call(self, endpoint, **kwargs):
        state = self.state
        if endpoint == "ISteamUser.GetPlayerSummaries":
            steamids = str(kwargs.get("steamids", ""))
            # The friend lookup reuses this endpoint, told apart by the ids it asks for
            if steamids and str(STEAM_ID) not in steamids:
                return {"response": {"players": [{"steamid": sid, **FRIEND_PROFILES.get(sid, {"personaname": f"Friend{sid}", "realname": ""})} for sid in steamids.split(",")]}}
            if self.index in self.fail_cycles:
                raise RuntimeError("Steam returned no profile")
            player = {"steamid": str(STEAM_ID), "personaname": state["personaname"], "personastate": state["personastate"], "communityvisibilitystate": 3, "profileurl": PROFILE_URL, "avatarfull": AVATAR_URL, "timecreated": 1300000000, "lastlogoff": 1700000000}
            if state["gameid"]:
                player["gameid"] = state["gameid"]
                player["gameextrainfo"] = state["gamename"]
            return {"response": {"players": [copy.deepcopy(player)]}}
        if endpoint == "IPlayerService.GetRecentlyPlayedGames":
            return {"response": {"games": []}}
        if endpoint == "IPlayerService.GetSteamLevel":
            return {"response": {"player_level": state["level"]}}
        if endpoint == "IPlayerService.GetBadges":
            return {"response": {"player_xp": state["xp"], "player_xp_needed_to_level_up": 100, "player_xp_needed_current_level": 4900, "badges": []}}
        if endpoint == "ISteamUser.GetFriendList":
            return {"friendslist": {"friends": [{"steamid": sid, "friend_since": 1600000000} for sid in state["friends"]]}}
        if endpoint == "IPlayerService.GetOwnedGames":
            wanted = kwargs.get("appids_filter") or []
            # A filtered lookup only answers for games the account still owns, the way Steam does
            appids = [appid for appid in state["owned"] if not wanted or appid in wanted]
            if kwargs.get("include_appinfo"):
                return {"response": {"games": [{"appid": appid, "name": APP_NAMES.get(appid, f"Game {appid}")} for appid in appids]}}
            return {"response": {"games": [{"appid": appid} for appid in appids]}}
        if endpoint == "ISteamUser.GetPlayerBans":
            return {"players": []}
        return {}


# Reduces one HTML body back to the text it represents, independently of the module's own converter
def html_to_text(body_html):
    text = re.sub(r"(?is)</?(?:html|head|body)\s*>", "", str(body_html or ""))
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?s)<[^>]+>", "", text)
    return html_module.unescape(text)


# Returns the unified diff between the plain body and the text the HTML body reduces to, empty when they match
def structural_diff(body, body_html):
    reduced = html_to_text(body_html)
    if reduced == body:
        return ""
    return "\n".join(difflib.unified_diff(body.split("\n"), reduced.split("\n"), fromfile="plain", tofile="html-reduced", lineterm=""))


# Collects every alert the monitoring loop tries to send, without delivering any of them
def capture_alerts(tmp_path, monkeypatch, scenario, fail_cycles=(), api_class=None):
    captured = []

    def fake_send(notification_type, subject, body, body_html="", **kwargs):
        captured.append({"type": notification_type, "subject": subject, "body": body, "body_html": body_html, "webhook_body": kwargs.get("webhook_body") or body, "discord": monitor.html_body_to_discord_markdown(kwargs.get("webhook_body_html") or body_html)})
        return bool(kwargs.get("email_enabled")), bool(kwargs.get("webhook_enabled"))

    api = (api_class or ScriptedSteamWebAPI)(scenario, fail_cycles=fail_cycles)
    clock = [float(int(time.time())) - 86400]

    def advance(seconds):
        # Each sleep is one cycle boundary, so the scenario steps in lockstep with the loop
        clock[0] += max(seconds, 1)
        api.index += 1
        if api.index >= len(scenario):
            raise StopScenario()

    for name, value in {"STATUS_NOTIFICATION": True, "ACTIVE_INACTIVE_NOTIFICATION": True, "GAME_CHANGE_NOTIFICATION": True, "STEAM_LEVEL_XP_NOTIFICATION": True, "STEAM_LEVEL_XP_CHECK": True, "FRIENDS_NOTIFICATION": True, "FRIENDS_CHECK": True, "GAMES_LIBRARY_NOTIFICATION": True, "GAMES_LIBRARY_CHECK": True, "NAME_CHANGE_NOTIFICATION": True, "ERROR_NOTIFICATION": True, "STEAM_CHECK_INTERVAL": 60, "STEAM_ACTIVE_CHECK_INTERVAL": 30, "ERROR_ALERT_AFTER_SECONDS": 0, "FILE_SUFFIX": "", "VERBOSE_MODE": False, "DEBUG_MODE": False}.items():
        monkeypatch.setattr(monitor, name, value)
    for name, value in (("SMTP_HOST", "smtp.example.com"), ("SMTP_PORT", 587), ("SMTP_USER", "sender@example.com"), ("SMTP_PASSWORD", "test-password"), ("SENDER_EMAIL", "sender@example.com"), ("RECEIVER_EMAIL", "receiver@example.com")):
        monkeypatch.setattr(monitor, name, value)
    monkeypatch.setattr(monitor, "send_notification_channels", fake_send)
    monkeypatch.setattr(monitor, "steam_web_api_client", lambda *args, **kwargs: api)
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    monkeypatch.setattr(monitor.time, "sleep", advance)
    monkeypatch.chdir(tmp_path)

    try:
        monitor.steam_monitor_user(STEAM_ID, "", None)
    except StopScenario:
        pass
    return captured


@pytest.fixture
# Every alert the scenario produces, including the failure alert and the recovery that answers it
def scenario_alerts(tmp_path, monkeypatch, capsys):
    alerts = capture_alerts(tmp_path, monkeypatch, SCENARIO)
    alerts.extend(capture_alerts(tmp_path, monkeypatch, [SCENARIO[0]] * 4, fail_cycles=(1, 2)))
    capsys.readouterr()
    return alerts


# Verifies a value taken from Steam is escaped before it reaches the HTML body
def test_untrusted_text_is_escaped():
    assert monitor.html_text("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert monitor.html_text("line\nbreak") == "line<br>break"
    assert monitor.escape_html_attr('" onload="x') == "&quot; onload=&quot;x"


# Verifies a crafted display name cannot inject markup through the bolded profile link
def test_a_crafted_name_cannot_inject_markup():
    rendered = monitor.steam_user_html('<img src=x onerror=alert(1)>', STEAM_ID)

    assert "<img" not in rendered
    assert "&lt;img src=x onerror=alert(1)&gt;" in rendered
    assert rendered.startswith(f'<b><a href="https://steamcommunity.com/profiles/{STEAM_ID}">')


# Verifies an entity without a known URL still renders as bold text rather than an empty link
def test_an_entity_without_a_url_renders_unlinked():
    assert monitor.steam_user_html("TestPlayer", None) == "<b>TestPlayer</b>"
    assert monitor.steam_game_html("Team Fortress 2", None) == "<b>Team Fortress 2</b>"
    assert monitor.html_link("", "label") == "label"


# Verifies the store and profile links are built from the ids the monitor already holds
def test_entity_links_point_at_steam():
    assert monitor.steam_profile_url(STEAM_ID) == f"https://steamcommunity.com/profiles/{STEAM_ID}"
    assert monitor.steam_store_url(440) == "https://store.steampowered.com/app/440/"
    assert monitor.steam_store_url("570") == "https://store.steampowered.com/app/570/"
    assert monitor.steam_store_url("not-an-appid") == ""
    assert monitor.steam_store_url(None) == ""


# Verifies a friend entry keeps the real name and the Steam64 ID the plain line carries
def test_friend_entries_keep_the_plain_details():
    assert monitor.steam_friend_line_html("FirstFriend", "First Person", "1") == '- <b><a href="https://steamcommunity.com/profiles/1">FirstFriend</a></b> (First Person) [1]'
    assert monitor.steam_friend_line_html("SecondFriend", "", "2") == '- <b><a href="https://steamcommunity.com/profiles/2">SecondFriend</a></b> [2]'
    assert monitor.steam_friend_line_html("", "", "3") == '- <b><a href="https://steamcommunity.com/profiles/3">3</a></b> [3]'


# Verifies a bare URL in an alert becomes a link while one already inside an attribute is left alone
def test_bare_urls_are_linked_once():
    assert monitor.html_autolink_urls("Guide: https://example.test/a") == 'Guide: <a href="https://example.test/a">https://example.test/a</a>'
    assert monitor.html_autolink_urls("See https://example.test/a.") == 'See <a href="https://example.test/a">https://example.test/a</a>.'
    assert monitor.html_autolink_urls('<a href="https://example.test/a">x</a>') == '<a href="https://example.test/a">x</a>'


# Verifies the Discord body carries the email's emphasis and links instead of raw markup
def test_discord_markdown_mirrors_the_html_body():
    body_html = monitor.html_email_body('Steam user <b><a href="https://steamcommunity.com/profiles/1">Name</a></b> is now <b>online</b><br><br>Note: <i>quiet</i>')

    assert monitor.html_body_to_discord_markdown(body_html) == "Steam user **[Name](https://steamcommunity.com/profiles/1)** is now **online**\n\nNote: *quiet*"


# Verifies a link whose label repeats its destination is left bare, which Discord turns into a link itself
def test_a_self_labeled_link_stays_bare_in_discord():
    body_html = '<a href="https://example.test/a">https://example.test/a</a>'

    assert monitor.html_body_to_discord_markdown(body_html) == "https://example.test/a"


# Verifies a tag the markdown subset has no form for is dropped rather than printed
def test_unsupported_markup_is_dropped_in_discord():
    assert monitor.html_body_to_discord_markdown("<p>text</p><ul><li>item</li></ul>") == "textitem"
    assert monitor.html_body_to_discord_markdown("<b></b>done") == "done"


# Verifies the failure alert bolds its summary and the two values that say how bad the outage is
def test_the_failure_alert_bolds_its_summary_and_outage_fields():
    advice = monitor.make_recovery_advice("steam.unavailable", "Steam is unreachable", "Retry later", True)

    rendered = monitor.recovery_alert_body_html(advice, 60, failed_checks=2, failing_since=1700000000)

    assert rendered.startswith("<html><head></head><body><b>Steam is unreachable</b><br><br>")
    assert "Failed checks in a row: <b>2</b>" in rendered
    assert "Failing since: <b>" in rendered
    # The retry delay is configured rather than observed, so it carries no emphasis
    assert "Next retry in: 1 minute" in rendered
    assert rendered.endswith("</body></html>")


# Verifies a library entry names the game and keeps the application ID next to it
def test_library_entries_name_the_game():
    names = {570: "Dota 2"}

    assert monitor.steam_app_label(570, names) == "Dota 2 (570)"
    assert monitor.steam_app_label_html(570, names) == '<b><a href="https://store.steampowered.com/app/570/">Dota 2</a></b> (570)'


# Verifies an unresolved application ID still renders as a bold store link rather than disappearing
def test_an_unnamed_library_entry_falls_back_to_the_id():
    assert monitor.steam_app_label(999, {}) == "999"
    assert monitor.steam_app_label_html(999, {}) == '<b><a href="https://store.steampowered.com/app/999/">999</a></b>'


# Verifies a game name taken from Steam is escaped before it reaches the HTML body
def test_a_crafted_game_name_cannot_inject_markup():
    rendered = monitor.steam_app_label_html(570, {570: "<script>alert(1)</script>"})

    assert "<script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered


# Verifies names are read from an owned-games response and from a saved library file, skipping unusable entries
def test_app_names_are_read_from_steam_and_from_the_saved_file():
    owned = {"response": {"games": [{"appid": 570, "name": "Dota 2"}, {"appid": 440, "name": ""}, {"name": "No id"}, "junk"]}}

    assert monitor.app_names_from_owned(owned) == {570: "Dota 2"}
    assert monitor.saved_app_names({"app_names": {"570": "Dota 2", "bad": "x", "440": ""}}) == {570: "Dota 2"}
    assert monitor.saved_app_names({}) == {}


# Verifies a failed name lookup leaves the alert on the application IDs instead of stopping the check
def test_a_failed_name_lookup_is_survivable():
    class Failing:
        def call(self, *args, **kwargs):
            raise RuntimeError("Steam is unreachable")

    assert monitor.fetch_app_names(Failing(), STEAM_ID, [570]) == {}
    assert monitor.fetch_app_names(Failing(), STEAM_ID, []) == {}


# Verifies the webhook copy of an alert leaves out the timestamp the email carries
def test_the_webhook_body_has_no_timestamp():
    advice = monitor.make_recovery_advice("steam.unavailable", "Steam is unreachable", "Retry later", True)

    assert "Timestamp: " not in monitor.recovery_alert_body_html(advice, 60, timestamp=False)
    assert "Timestamp: " in monitor.recovery_alert_body_html(advice, 60)


# Verifies the scenario reaches every notification type, so the structural check is not silently narrow
def test_the_scenario_covers_every_notification_type(scenario_alerts):
    assert {alert["type"] for alert in scenario_alerts} == {"active", "inactive", "status", "game", "games", "level_xp", "friends", "name", "error"}


# Verifies a status subject names when the state started rather than the whole range, which the body already reports
def test_a_status_subject_names_when_the_state_started(scenario_alerts):
    subjects = [alert["subject"] for alert in scenario_alerts if alert["type"] in {"active", "inactive", "status"} and " is offline (" not in alert["subject"]]

    assert subjects
    for subject in subjects:
        assert re.fullmatch(r"Steam user \w+ is \w+ \(after .+ - (?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) \d{1,2} \w{3} \d{2}:\d{2}\)", subject), subject
        assert len(re.findall(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b", subject)) == 1


# Verifies going offline keeps the range, since that names the session the user was available for
def test_the_offline_subject_carries_the_availability_range(scenario_alerts):
    offline = [alert["subject"] for alert in scenario_alerts if " is offline (" in alert["subject"]]

    assert offline
    for subject in offline:
        assert re.fullmatch(r"Steam user \w+ is offline \(after .+: (?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) \d{1,2} \w{3} \d{2}:\d{2} - .+\)", subject), subject


# Verifies every alert carries an HTML body next to its plain one
def test_every_alert_has_an_html_body(scenario_alerts):
    missing = [alert["subject"] for alert in scenario_alerts if not alert["body_html"]]

    assert missing == []


# Verifies each HTML body reduces back to its plain body, so no line break was added or lost
def test_html_bodies_match_the_plain_text(scenario_alerts):
    mismatches = [f"{alert['type']}: {alert['subject']}\n{structural_diff(alert['body'], alert['body_html'])}" for alert in scenario_alerts if structural_diff(alert["body"], alert["body_html"])]

    assert mismatches == []


# Verifies every HTML body is one complete document, so no fragment reaches a mail client unwrapped
def test_html_bodies_are_complete_documents(scenario_alerts):
    for alert in scenario_alerts:
        assert alert["body_html"].startswith("<html><head></head><body>")
        assert alert["body_html"].endswith("</body></html>")


# Verifies the Discord body keeps the wording the ntfy body carries once its markers are removed
def test_discord_bodies_keep_the_plain_wording(scenario_alerts):
    for alert in scenario_alerts:
        stripped = re.sub(r"\[([^\]]*)\]\((?:[^)]*)\)", r"\1", alert["discord"]).replace("**", "").replace("*", "")

        assert stripped == alert["webhook_body"].strip()


# Verifies the monitored account and the games it plays are linked in every alert that names them
def test_alerts_link_the_entities_they_name(scenario_alerts):
    for alert in scenario_alerts:
        if alert["type"] in ("active", "inactive", "status", "friends", "games", "name", "level_xp"):
            assert f'href="https://steamcommunity.com/profiles/{STEAM_ID}"' in alert["body_html"]
    game_alerts = [alert for alert in scenario_alerts if alert["type"] == "game"]

    assert game_alerts
    for alert in game_alerts:
        assert "https://store.steampowered.com/app/" in alert["body_html"]


class NoBadgesSteamWebAPI(ScriptedSteamWebAPI):
    # Answers the badge endpoint with nothing, the shape a private or empty profile returns
    def call(self, endpoint, **kwargs):
        if endpoint == "IPlayerService.GetBadges":
            return {"response": {}}
        return super().call(endpoint, **kwargs)


# Verifies an unavailable XP value leaves no empty line behind in either body
def test_a_level_alert_without_xp_has_no_empty_line(tmp_path, monkeypatch, capsys):
    alerts = capture_alerts(tmp_path, monkeypatch, [cycle(), cycle(), cycle(level=43), cycle(level=43)], api_class=NoBadgesSteamWebAPI)
    capsys.readouterr()
    level_alerts = [alert for alert in alerts if alert["type"] == "level_xp"]

    assert level_alerts
    for alert in level_alerts:
        assert "Total XP after level change" not in alert["body"]
        assert "\n\n\n" not in alert["body"]
        assert "<br><br><br>" not in alert["body_html"]
        assert not structural_diff(alert["body"], alert["body_html"])


# Writes the captured alerts as JSON when PREVIEW_ALERTS_JSON names a destination, so a preview tool can render them
@pytest.mark.skipif(not os.environ.get("PREVIEW_ALERTS_JSON"), reason="set PREVIEW_ALERTS_JSON to dump the alerts")
def test_dump_the_alerts_for_a_preview(scenario_alerts):
    Path(os.environ["PREVIEW_ALERTS_JSON"]).write_text(json.dumps(scenario_alerts, indent=2), encoding="utf-8")

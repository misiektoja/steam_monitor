"""Exercises saved library comparisons through the real startup and polling paths, without network access."""

import copy
import csv
import json
import os
import socket
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest

import steam_monitor as monitor


STEAM_ID = 76561198000000000


class StopScenario(Exception):
    pass


class LibraryAPI:
    # Supplies complete libraries or failures independently of stable player observations.
    def __init__(self, observations):
        self.IPlayerService = SimpleNamespace(GetOwnedGames=SimpleNamespace(parameters={}))
        self.observations = observations
        self.index = 0
        self.current = []
        self.names = {}

    # Filtered name lookups do not consume another library observation.
    def call(self, endpoint, **arguments):
        if endpoint == "ISteamUser.GetPlayerSummaries":
            return {"response": {"players": [{"steamid": str(STEAM_ID), "personaname": "Library fixture", "personastate": 0, "communityvisibilitystate": 3, "lastlogoff": 0}]}}
        if endpoint == "IPlayerService.GetRecentlyPlayedGames":
            return {"response": {"games": []}}
        if endpoint == "IPlayerService.GetOwnedGames":
            wanted = arguments.get("appids_filter")
            if wanted:
                ids = sorted(set(wanted) & set(self.current))
            else:
                observed = self.observations[min(self.index, len(self.observations) - 1)]
                self.index += 1
                if isinstance(observed, BaseException):
                    raise observed
                if isinstance(observed, dict):
                    return copy.deepcopy(observed)
                self.current = list(observed)
                ids = self.current
            games = [{"appid": appid} for appid in ids]
            if arguments.get("include_appinfo"):
                for game in games:
                    game["name"] = self.names.get(game["appid"], "Game {}".format(game["appid"]))
            return {"response": {"game_count": len(games), "games": games}}
        raise AssertionError("Unexpected endpoint: " + endpoint)


@pytest.fixture(autouse=True)
# Isolates settings and files and blocks real delivery even if a test forgets to replace an API path.
def isolated_settings(tmp_path, monkeypatch):
    values = {"COLORED_OUTPUT": False, "COLOR_ENABLED": False, "DEBUG_MODE": False, "VERBOSE_MODE": False, "MONITORING_ACTIVE": False, "GAMES_LIBRARY_CHECK": True, "STEAM_LEVEL_XP_CHECK": False, "FRIENDS_CHECK": False, "REPORT_CHANGES_AFTER_RESTART": True, "FILE_SUFFIX": "", "STEAM_STATUS_FILE": "", "ERROR_NOTIFICATION": False, "ACTIVE_INACTIVE_NOTIFICATION": False, "STATUS_NOTIFICATION": False, "GAME_CHANGE_NOTIFICATION": False, "NAME_CHANGE_NOTIFICATION": False, "GAMES_LIBRARY_NOTIFICATION": False, "WEBHOOK_ENABLED": False, "WEBHOOK_GAMES_NOTIFICATION": False, "WEBHOOK_ERROR_NOTIFICATION": False, "STEAM_CHECK_INTERVAL": 60, "STEAM_ACTIVE_CHECK_INTERVAL": 30, "LIVENESS_REMINDER_SECONDS": 0}
    for name, value in values.items():
        monkeypatch.setattr(monitor, name, value, raising=False)
    monkeypatch.chdir(tmp_path)

    # Every test in this module must use its scripted API and notification doubles.
    def unexpected_network(*_args, **_kwargs):
        raise AssertionError("Unexpected network access")

    monkeypatch.setattr(socket.socket, "connect", unexpected_network)


# Runs startup plus the requested number of polling iterations with a deterministic detection clock.
def run_scenario(monkeypatch, observations, polls=1, csv_path=None, before_wait=None, api=None):
    api = LibraryAPI(observations) if api is None else api
    monkeypatch.setattr(monitor, "steam_web_api_client", lambda: api)
    clock = [1800000000.0]
    waits = []

    # Captures the boundary after each observation without changing its comparison logic.
    def wait(seconds):
        waits.append(seconds)
        if before_wait is not None:
            before_wait(len(waits))
        if len(waits) >= polls + 1:
            raise StopScenario()
        clock[0] += max(seconds, 1)

    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    monkeypatch.setattr(monitor.time, "sleep", wait)
    with pytest.raises(StopScenario):
        monitor.steam_monitor_user(STEAM_ID, "", str(csv_path) if csv_path else None)
    return api


# Writes only synthetic IDs to the target's existing games-snapshot format.
def save_library(tmp_path, ids, names=None):
    path = tmp_path / monitor.default_games_file(STEAM_ID)
    path.write_text(json.dumps({"game_count": len(ids), "appids": ids, "app_names": names or {}}), encoding="utf-8")
    return path


# Uses the existing eight-column format rather than an implementation-specific restart record.
def csv_rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


# Observes real channel gating while replacing only the final external delivery functions.
def delivery_probes(monkeypatch, email=True, webhook=True, failure=False):
    settings = {"SMTP_HOST": "smtp.example.com", "SMTP_PORT": 587, "SMTP_USER": "sender@example.com", "SMTP_PASSWORD": "synthetic-password", "SENDER_EMAIL": "sender@example.com", "RECEIVER_EMAIL": "receiver@example.com", "WEBHOOK_ENABLED": webhook, "WEBHOOK_PROVIDER": "discord", "WEBHOOK_URL": "https://discord.com/api/webhooks/123/synthetic-token", "GAMES_LIBRARY_NOTIFICATION": email, "WEBHOOK_GAMES_NOTIFICATION": webhook}
    for name, value in settings.items():
        monkeypatch.setattr(monitor, name, value)
    deliveries = []

    # Captures the email payload without contacting SMTP.
    def send_email(subject, body, body_html, *_args, **_kwargs):
        deliveries.append(("email", subject, body, body_html))
        return 1 if failure else 0

    # Captures the webhook payload before any HTTP request.
    def send_webhook(subject, body, notification_type, **kwargs):
        assert notification_type == "games"
        deliveries.append(("webhook", subject, body, kwargs["discord_description"]))
        return 1 if failure else 0

    monkeypatch.setattr(monitor, "send_email", send_email)
    monkeypatch.setattr(monitor, "send_webhook", send_webhook)
    return deliveries


# Restart must compare the loaded set before startup replaces it, including a same-count replacement.
def test_startup_compares_saved_library_before_replacing_it(tmp_path, monkeypatch, capsys):
    path = save_library(tmp_path, [10, 20], {"20": "Removed game"})
    csv_path = tmp_path / "profile.csv"
    run_scenario(monkeypatch, [[10, 30], [10, 30]], csv_path=csv_path)
    output = capsys.readouterr().out
    assert output.count("games library changed") == 1
    assert "Removed: Removed game (20)" in output
    with csv_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    assert rows[0]["Event"] == "games_library_change"
    assert rows[0]["OldValue"] == rows[0]["NewValue"] == "2"
    assert rows[0]["Delta"] == "0"
    assert json.loads(path.read_text(encoding="utf-8"))["appids"] == [10, 30]


# Missing and empty saved libraries are distinct: only an existing valid baseline can produce a change event.
@pytest.mark.parametrize("old,current,events", [(None, [10], 0), ([], [], 0), ([], [10], 1), ([10], [], 1), ([10], [10], 0), ([10], [10, 20], 1), ([10, 20], [10], 1)])
def test_first_unchanged_and_empty_libraries(tmp_path, monkeypatch, old, current, events):
    if old is not None:
        save_library(tmp_path, old)
    csv_path = tmp_path / "profile.csv"
    run_scenario(monkeypatch, [current, current], csv_path=csv_path)
    assert len(csv_rows(csv_path)) == events
    stored = json.loads((tmp_path / monitor.default_games_file(STEAM_ID)).read_text(encoding="utf-8"))
    assert stored["appids"] == current
    assert stored["game_count"] == len(current)
    assert set(stored) == {"game_count", "appids", "app_names"}


# Legacy inconsistent counts follow the valid ID set, while unusable files only discard their own baseline.
@pytest.mark.parametrize("contents,expected_events,warns", [('not json', 0, True), ('{"game_count": 1, "appids": ["bad"]}', 0, True), ('[]', 0, True), ('{"game_count": 9, "appids": [10, 20]}', 0, False), ('{"game_count": 9, "appids": [10]}', 1, False)])
def test_legacy_or_corrupt_snapshots(tmp_path, monkeypatch, capsys, contents, expected_events, warns):
    path = tmp_path / monitor.default_games_file(STEAM_ID)
    path.write_text(contents, encoding="utf-8")
    csv_path = tmp_path / "profile.csv"
    run_scenario(monkeypatch, [[10, 20], [10, 20]], csv_path=csv_path)
    assert len(csv_rows(csv_path)) == expected_events
    assert ("Cannot load the games library" in capsys.readouterr().out) is warns


# Failed HTTP/response observations leave the complete snapshot untouched until a later success compares it.
def test_failed_observations_recover_against_retained_baseline_once(tmp_path, monkeypatch):
    path = save_library(tmp_path, [10, 20], {"20": "Removed game"})
    original = path.read_bytes()
    csv_path = tmp_path / "profile.csv"

    # At the first two boundaries neither a request failure nor an incomplete response may write anything.
    def inspect_boundary(wait_count):
        if wait_count <= 2:
            assert path.read_bytes() == original
            assert not csv_rows(csv_path)

    run_scenario(monkeypatch, [RuntimeError("Unavailable"), {"response": {}}, [10, 30], [10, 30]], polls=3, csv_path=csv_path, before_wait=inspect_boundary)
    assert len(csv_rows(csv_path)) == 1
    assert json.loads(path.read_text(encoding="utf-8"))["appids"] == [10, 30]


# No old baseline still needs saving after an initial failure, even if the first success occurs in polling.
def test_first_poll_success_without_a_saved_baseline_is_persisted(tmp_path, monkeypatch):
    csv_path = tmp_path / "profile.csv"
    run_scenario(monkeypatch, [RuntimeError("Unavailable"), [10]], csv_path=csv_path)
    assert not csv_rows(csv_path)
    assert json.loads((tmp_path / monitor.default_games_file(STEAM_ID)).read_text(encoding="utf-8"))["appids"] == [10]


# A first failed request does not consume the opt-out's silent initialization; the following real change still reports.
@pytest.mark.parametrize("failure_first", [False, True])
def test_opt_out_silences_only_first_success(tmp_path, monkeypatch, failure_first):
    path = save_library(tmp_path, [10])
    monkeypatch.setattr(monitor, "REPORT_CHANGES_AFTER_RESTART", False)
    deliveries = delivery_probes(monkeypatch)
    csv_path = tmp_path / "profile.csv"
    observations = ([RuntimeError("Unavailable")] if failure_first else []) + [[10, 20], [10, 20], [10, 20, 30]]

    # The established current baseline is observable before any later change, with no stopped-period rows or alerts.
    def inspect_boundary(wait_count):
        first_success = 2 if failure_first else 1
        if wait_count == first_success:
            assert not csv_rows(csv_path)
            assert not deliveries
            assert json.loads(path.read_text(encoding="utf-8"))["appids"] == [10, 20]

    run_scenario(monkeypatch, observations, polls=len(observations) - 1, csv_path=csv_path, before_wait=inspect_boundary)
    rows = csv_rows(csv_path)
    assert len(rows) == 1
    assert (rows[0]["OldValue"], rows[0]["NewValue"]) == ("2", "3")
    assert [item[0] for item in deliveries] == ["email", "webhook"]


# Every successful observation refreshes its snapshot, including an unchanged library.
def test_unchanged_successes_refresh_snapshot(tmp_path, monkeypatch):
    path = save_library(tmp_path, [10])
    real_write = monitor.write_json_atomic
    snapshots = []

    # Records only games writes while retaining the actual atomic writer.
    def capture_write(destination, payload, *args, **kwargs):
        if str(destination) == path.name:
            snapshots.append(copy.deepcopy(payload))
        return real_write(destination, payload, *args, **kwargs)

    monkeypatch.setattr(monitor, "write_json_atomic", capture_write)
    run_scenario(monkeypatch, [[10], [10]])
    assert len(snapshots) == 2
    assert all(snapshot["appids"] == [10] for snapshot in snapshots)


# Channels are independent and their flags do not suppress complete local records.
@pytest.mark.parametrize("email,webhook", [(False, False), (True, False), (False, True), (True, True)])
def test_notification_flags_do_not_gate_csv_or_log(tmp_path, monkeypatch, capsys, email, webhook):
    save_library(tmp_path, [10])
    deliveries = delivery_probes(monkeypatch, email=email, webhook=webhook)
    csv_path = tmp_path / "profile.csv"
    run_scenario(monkeypatch, [[10, 20], [10, 20]], csv_path=csv_path)
    assert [item[0] for item in deliveries] == (["email"] if email else []) + (["webhook"] if webhook else [])
    assert len(csv_rows(csv_path)) == 1
    assert "Added: Game 20 (20)" in capsys.readouterr().out


# Global webhook disable remains stronger than its per-event switch.
def test_webhook_master_switch_is_preserved(tmp_path, monkeypatch):
    save_library(tmp_path, [10])
    deliveries = delivery_probes(monkeypatch, email=False, webhook=True)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", False)
    run_scenario(monkeypatch, [[20], [20]])
    assert not deliveries


# A prior CSV header stays compatible; its new row uses detection time, never the old file timestamp.
def test_existing_csv_schema_and_observation_time(tmp_path, monkeypatch, capsys):
    path = save_library(tmp_path, [10])
    os.utime(path, (1700000000, 1700000000))
    csv_path = tmp_path / "profile.csv"
    header = ['Date', 'Event', 'OldValue', 'NewValue', 'Delta', 'FriendSteamID', 'FriendPersona', 'FriendRealName']
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerow(["old date", "games_library_change", 0, 1, 1, "", "", ""])
    run_scenario(monkeypatch, [[20], [20]], csv_path=csv_path)
    rows = csv_rows(csv_path)
    assert len(rows) == 2
    assert list(rows[1]) == header
    assert None not in rows[1]
    assert rows[1]["Date"] == str(datetime.fromtimestamp(1800000000))
    output = capsys.readouterr().out
    assert datetime.fromtimestamp(1700000000).strftime("%a %d %b %Y, %H:%M:%S") in output
    assert "exact change time is unknown" in output


# Optional name resolution may be slow, but the event date stays at the successful observation rather than delivery time.
def test_name_lookup_delay_does_not_move_detection_time(tmp_path, monkeypatch):
    clock = [1800000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    csv_path = tmp_path / "profile.csv"
    monitor.init_profile_csv_file(str(csv_path))
    deliveries = delivery_probes(monkeypatch, webhook=False)

    # Advances the clock only during the optional supplemental request.
    def delayed_names(*_args):
        clock[0] += 300
        return {}

    monkeypatch.setattr(monitor, "fetch_app_names", delayed_names)
    monitor.observe_games_library(LibraryAPI([]), STEAM_ID, "Library fixture", {10}, {20}, {}, "memory-games.json", str(csv_path))
    assert csv_rows(csv_path)[0]["Date"] == str(datetime.fromtimestamp(1800000000))
    assert "Timestamp: " + monitor.get_date_from_ts(1800000000) in deliveries[0][2]


# A missing or implausible file time cannot discard valid IDs or fabricate a change timestamp.
@pytest.mark.parametrize("saved_time", [None, float("inf"), 1800001000])
def test_unusable_snapshot_time_is_optional_context(tmp_path, monkeypatch, capsys, saved_time):
    save_library(tmp_path, [10])
    real_mtime = monitor.os.path.getmtime

    # A stat failure affects the games timestamp only, leaving unrelated file handling intact.
    def games_mtime(path):
        if str(path).endswith("_games.json"):
            if saved_time is None:
                raise OSError("No timestamp")
            return saved_time
        return real_mtime(path)

    monkeypatch.setattr(monitor.os.path, "getmtime", games_mtime)
    run_scenario(monkeypatch, [[20], [20]])
    output = capsys.readouterr().out
    assert output.count("games library changed") == 1
    assert "Previous snapshot saved:" not in output
    assert "Cannot load the games library" not in output


# A failed replacement keeps the old file while memory advances, and an unchanged next observation retries saving.
def test_atomic_write_failure_keeps_file_without_repeating_change(tmp_path, monkeypatch, capsys):
    path = save_library(tmp_path, [10])
    original = path.read_bytes()
    real_replace = monitor.os.replace
    attempts = []

    # Fails one real atomic replacement rather than replacing the persistence implementation with a no-op.
    def fail_once(source, destination):
        if str(destination).endswith("_games.json"):
            attempts.append(destination)
            if len(attempts) == 1:
                raise PermissionError("Synthetic write denial")
        return real_replace(source, destination)

    # The first successful observation must leave the previous complete file on a failed replace.
    def inspect_boundary(wait_count):
        if wait_count == 1:
            assert path.read_bytes() == original

    monkeypatch.setattr(monitor.os, "replace", fail_once)
    csv_path = tmp_path / "profile.csv"
    run_scenario(monkeypatch, [[20], [20]], csv_path=csv_path, before_wait=inspect_boundary)
    assert len(attempts) == 2
    assert len(csv_rows(csv_path)) == 1
    assert json.loads(path.read_text(encoding="utf-8"))["appids"] == [20]
    assert "Cannot save the games library" in capsys.readouterr().out
    assert not list(tmp_path.glob(".*.tmp"))


# Delivery errors are not a reason to replay the same library event at every poll.
@pytest.mark.parametrize("raises", [False, True])
def test_notification_failure_does_not_stall_baseline(tmp_path, monkeypatch, raises):
    path = save_library(tmp_path, [10])
    deliveries = delivery_probes(monkeypatch, failure=True)
    if raises:
        # Covers an unexpected delivery exception in addition to ordinary failed return values.
        def fail_delivery(*_args, **_kwargs):
            deliveries.append(("exception",))
            raise RuntimeError("Synthetic delivery failure")

        monkeypatch.setattr(monitor, "send_notification_channels", fail_delivery)
    csv_path = tmp_path / "profile.csv"
    run_scenario(monkeypatch, [[20], [20]], csv_path=csv_path)
    assert len(deliveries) == (1 if raises else 2)
    assert len(csv_rows(csv_path)) == 1
    assert json.loads(path.read_text(encoding="utf-8"))["appids"] == [20]


# An unwritable profile CSV cannot keep the library baseline at an old value and repeat the event.
def test_csv_write_failure_does_not_stall_baseline(tmp_path, monkeypatch, capsys):
    path = save_library(tmp_path, [10])
    attempts = []

    # Simulates failure of the optional output only, preserving normal snapshot writes.
    def fail_csv(*_args, **_kwargs):
        attempts.append(True)
        raise PermissionError("Synthetic CSV denial")

    monkeypatch.setattr(monitor, "write_profile_csv_entry", fail_csv)
    run_scenario(monkeypatch, [[20], [20]], csv_path=tmp_path / "profile.csv")
    assert len(attempts) == 1
    assert json.loads(path.read_text(encoding="utf-8"))["appids"] == [20]
    assert capsys.readouterr().out.count("games library changed") == 1


# A missing removed-game name or failed name lookup does not turn a valid library difference into an outage.
def test_name_lookup_failure_uses_ids_without_losing_comparison(tmp_path, monkeypatch, capsys):
    save_library(tmp_path, [10])
    monkeypatch.setattr(monitor, "fetch_app_names", lambda *_args: {})
    run_scenario(monkeypatch, [RuntimeError("Startup unavailable"), [20], [20]], polls=2)
    output = capsys.readouterr().out
    assert output.count("games library changed") == 1
    assert "Added: 20" in output and "Removed: 10" in output


# Large startup differences use the same bounded notification path as live changes, while local data stays complete.
def test_large_restart_diff_keeps_full_log_and_summary_csv(tmp_path, monkeypatch, capsys):
    old_ids, new_ids = list(range(10, 20)), list(range(100, 112))
    save_library(tmp_path, old_ids, {str(appid): "Old game {}".format(appid) for appid in old_ids})
    deliveries = delivery_probes(monkeypatch)
    csv_path = tmp_path / "profile.csv"
    run_scenario(monkeypatch, [new_ids, new_ids], csv_path=csv_path)
    assert len(deliveries) == 2
    body = deliveries[0][2]
    assert "12 total, 7 omitted" in body and "10 total, 5 omitted" in body
    assert "Game 111 (111)" not in body and "Old game 19 (19)" not in body
    output = capsys.readouterr().out
    assert "Game 111 (111)" in output and "Old game 19 (19)" in output
    assert len(csv_rows(csv_path)) == 1


# Only a comparison against the snapshot loaded from disk spans a stopped period, so only it says the time is unknown.
@pytest.mark.parametrize("observations,context", [([[10], [10, 20]], False), ([[10, 20], [10, 20]], True), ([RuntimeError("Unavailable"), [10, 20]], True)])
def test_unknown_time_context_only_follows_a_saved_baseline(tmp_path, monkeypatch, capsys, observations, context):
    save_library(tmp_path, [10])
    deliveries = delivery_probes(monkeypatch, webhook=False)
    run_scenario(monkeypatch, observations)
    output = capsys.readouterr().out
    assert output.count("games library changed") == 1
    assert ("exact change time is unknown" in output) is context
    assert len(deliveries) == 1
    assert ("exact change time is unknown" in deliveries[0][2]) is context


# A list the alert shows in full keeps its plain form, and counts appear only when games are left out.
def test_omitted_counts_appear_only_when_details_are_cut(tmp_path, monkeypatch):
    save_library(tmp_path, [10])
    deliveries = delivery_probes(monkeypatch, webhook=False)
    run_scenario(monkeypatch, [[10], [20]])
    lines = deliveries[0][2].splitlines()
    assert "Added: Game 20 (20)" in lines
    assert "Removed: Game 10 (10)" in lines
    assert "omitted" not in deliveries[0][2]


# Unicode and hostile/long names retain HTML escaping and the existing transport length and mention guards.
def test_notification_unicode_escaping_and_transport_guards(tmp_path, monkeypatch):
    save_library(tmp_path, [10])
    deliveries = delivery_probes(monkeypatch)
    api = LibraryAPI([[20], [20]])
    api.names[20] = '<script> & @everyone 中文 🎮 ' + '界' * 5000
    run_scenario(monkeypatch, [], api=api)
    body, body_html = deliveries[0][2:]
    assert "中文" in body
    assert "<script>" not in body_html and "&lt;script&gt;" in body_html
    discord: Any = monitor.build_webhook_payload("Games", deliveries[1][3], "games")
    assert discord["allowed_mentions"] == {"parse": []}
    assert len(discord["embeds"][0]["description"]) <= monitor.WEBHOOK_EMBED_DESCRIPTION_LIMIT
    ntfy_body = monitor.truncate_utf8_bytes(body, monitor.NTFY_MESSAGE_LIMIT_BYTES, monitor.NTFY_TRUNCATION_SUFFIX)
    assert len(ntfy_body.encode("utf-8")) <= monitor.NTFY_MESSAGE_LIMIT_BYTES


# Disabling games tracking leaves a saved library alone and performs no library request.
def test_disabled_games_tracking_does_not_touch_snapshot(tmp_path, monkeypatch):
    path = save_library(tmp_path, [10])
    original = path.read_bytes()
    monkeypatch.setattr(monitor, "GAMES_LIBRARY_CHECK", False)
    api = run_scenario(monkeypatch, [[20]])
    assert api.index == 0
    assert path.read_bytes() == original

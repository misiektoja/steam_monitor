"""Tests that one monitoring cycle explains the Steam calls it makes and the ones that quietly degraded."""

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import copy
import json
import time

import pytest

import steam_monitor as monitor


STEAM_ID = 76561201960435530


PLAYER_SUMMARY = {
    "response": {
        "players": [
            {
                "steamid": str(STEAM_ID),
                "personaname": "TestPlayer",
                "personastate": 0,
                "communityvisibilitystate": 3,
                "profileurl": "https://steamcommunity.com/id/testplayer/",
                "avatarfull": "https://avatars.steamstatic.com/test_full.jpg",
                "timecreated": 1300000000,
                "lastlogoff": 1700000000,
            }
        ]
    }
}

RECENTLY_PLAYED = {"response": {"games": []}}


class StoppedAfterOneCycle(Exception):
    pass


class FakeSteamWebAPI:
    # Answers the Steam endpoints the monitoring cycle calls, failing the ones named in failing_endpoints
    def __init__(self, failing_endpoints=(), poll_error=None, healthy_polls=1, persona_state=0, healthy_after=None, **_kwargs):
        self.failing_endpoints = set(failing_endpoints)
        self.persona_state = persona_state
        # A poll error is raised only after the startup snapshot has succeeded, so the loop is actually reached
        self.poll_error = poll_error
        self.healthy_polls = healthy_polls
        # The poll succeeds again after this many polls, so a recovery can be exercised
        self.healthy_after = healthy_after
        self.polls = 0
        self.called = []

    def call(self, endpoint, **_kwargs):
        self.called.append(endpoint)
        if endpoint == "ISteamUser.GetPlayerSummaries" and self.poll_error is not None:
            self.polls += 1
            if self.polls > self.healthy_polls and (self.healthy_after is None or self.polls <= self.healthy_after):
                # A callable picks the error per poll, so an outage that changes category can be scripted
                error = self.poll_error(self.polls) if callable(self.poll_error) else self.poll_error
                assert isinstance(error, BaseException)
                raise error
        if endpoint in self.failing_endpoints:
            raise RuntimeError(f"{endpoint} is unavailable")
        if endpoint == "ISteamUser.GetPlayerSummaries":
            summary = copy.deepcopy(PLAYER_SUMMARY)
            summary["response"]["players"][0]["personastate"] = self.persona_state
            return summary
        if endpoint == "IPlayerService.GetRecentlyPlayedGames":
            return RECENTLY_PLAYED
        if endpoint == "IPlayerService.GetSteamLevel":
            return {"response": {"player_level": 42}}
        if endpoint == "IPlayerService.GetBadges":
            return {"response": {"player_xp": 5000, "player_xp_needed_to_level_up": 100, "player_xp_needed_current_level": 4900, "badges": []}}
        if endpoint == "ISteamUser.GetFriendList":
            return {"friendslist": {"friends": [{"steamid": "1", "friend_since": 1600000000}]}}
        if endpoint == "IPlayerService.GetOwnedGames":
            return {"response": {"games": [{"appid": 440}]}}
        if endpoint == "ISteamUser.GetPlayerBans":
            return {"players": []}
        return {}


# Runs one monitoring cycle with every tracked feature on and the named endpoints failing
def run_one_cycle(tmp_path, monkeypatch, failing_endpoints=(), diagnostics=True, poll_error=None, stop_after_sleeps=2, error_notifications=False, liveness_seconds=0, debug=None, persona_state=0, healthy_after=None):
    for name, value in (("SMTP_HOST", "smtp.example.com"), ("SMTP_PORT", 587), ("SMTP_USER", "sender@example.com"), ("SMTP_PASSWORD", "test-password"), ("SENDER_EMAIL", "sender@example.com"), ("RECEIVER_EMAIL", "receiver@example.com"), ("WEBHOOK_PROVIDER", "discord"), ("WEBHOOK_URL", "https://discord.com/api/webhooks/123/private-token")):
        monkeypatch.setattr(monitor, name, value)
    monkeypatch.setattr(monitor, "DEBUG_MODE", diagnostics if debug is None else debug)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", diagnostics)
    monkeypatch.setattr(monitor, "STEAM_LEVEL_XP_CHECK", True)
    monkeypatch.setattr(monitor, "FRIENDS_CHECK", True)
    monkeypatch.setattr(monitor, "GAMES_LIBRARY_CHECK", True)
    monkeypatch.setattr(monitor, "STEAM_CHECK_INTERVAL", 60)
    monkeypatch.setattr(monitor, "STEAM_ACTIVE_CHECK_INTERVAL", 30)
    monkeypatch.setattr(monitor, "LIVENESS_REMINDER_SECONDS", liveness_seconds)
    monkeypatch.setattr(monitor, "ACTIVE_INACTIVE_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", error_notifications)
    monkeypatch.setattr(monitor, "STEAM_LEVEL_XP_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "FRIENDS_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "GAMES_LIBRARY_NOTIFICATION", False)
    monkeypatch.setattr(monitor, "WEBHOOK_ENABLED", error_notifications)
    monkeypatch.setattr(monitor, "WEBHOOK_ERROR_NOTIFICATION", error_notifications)
    monkeypatch.setattr(monitor, "FILE_SUFFIX", "")
    # Keep every generated file inside the temporary directory
    monkeypatch.chdir(tmp_path)

    api = FakeSteamWebAPI(failing_endpoints, poll_error=poll_error, persona_state=persona_state, healthy_after=healthy_after)
    monkeypatch.setattr(monitor, "steam_web_api_client", lambda *args, **kwargs: api)

    sleeps = []
    # A fake clock advanced by each sleep, so the timed liveness reminder is deterministic
    clock = [float(int(time.time()))]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])

    def stop_after_the_first_cycle(seconds):
        sleeps.append(seconds)
        clock[0] += seconds
        # The first sleep is the one before the loop, the rest end each cycle
        if len(sleeps) >= stop_after_sleeps:
            raise StoppedAfterOneCycle()

    monkeypatch.setattr(monitor.time, "sleep", stop_after_the_first_cycle)

    with pytest.raises(StoppedAfterOneCycle):
        monitor.steam_monitor_user(STEAM_ID, "", None)
    return api, sleeps


# Verifies a healthy cycle names the Steam calls it makes and the interval it waits
def test_a_healthy_cycle_names_its_steam_calls(tmp_path, monkeypatch, capsys):
    api, sleeps = run_one_cycle(tmp_path, monkeypatch)

    output = capsys.readouterr().out
    assert "Opening the Steam Web API: steamid=76561201960435530, key=" in output
    assert "Polling Steam: steamid=76561201960435530" in output
    assert "Next check: due_in=1 minute, reason=user is offline" in output
    assert "IPlayerService.GetOwnedGames" in api.called
    assert sleeps[0] == 60


# Verifies a failing level lookup names the endpoint instead of degrading in silence
def test_a_failing_level_lookup_names_its_endpoint(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, failing_endpoints={"IPlayerService.GetSteamLevel"})

    output = capsys.readouterr().out
    assert "Fetching the Steam level (IPlayerService.GetSteamLevel): outcome=failed, error=RuntimeError" in output
    assert "Steam level or total XP is unavailable, so level and XP alerts cannot fire" in output


# Verifies a failing friends lookup names the endpoint and says the alert cannot fire
def test_a_failing_friends_lookup_names_its_endpoint(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, failing_endpoints={"ISteamUser.GetFriendList"})

    output = capsys.readouterr().out
    assert "Fetching the friends list (ISteamUser.GetFriendList): outcome=failed, error=RuntimeError" in output
    assert "The friends list is unavailable, so friends alerts cannot fire" in output


# Verifies a failing games library lookup names the endpoint and says the alert cannot fire
def test_a_failing_games_lookup_names_its_endpoint(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, failing_endpoints={"IPlayerService.GetOwnedGames"})

    output = capsys.readouterr().out
    assert "Fetching the games library (IPlayerService.GetOwnedGames): outcome=failed, error=RuntimeError" in output
    assert "The games library is unavailable, so games library alerts cannot fire" in output


# Verifies a failing badges lookup is reported, since total XP alerts depend on it alone
def test_a_failing_badges_lookup_names_its_endpoint(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, failing_endpoints={"IPlayerService.GetBadges"})

    output = capsys.readouterr().out
    assert "Fetching total XP (IPlayerService.GetBadges): outcome=failed, error=RuntimeError" in output
    assert "Steam level or total XP is unavailable, so level and XP alerts cannot fire" in output


# Verifies a verbose notice closes with the shared timestamp trailer instead of floating between blocks
def test_a_degraded_cycle_closes_its_verbose_notice_with_a_timestamp(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, failing_endpoints={"ISteamUser.GetFriendList"}, debug=False)

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    notice = next(index for index, line in enumerate(lines) if "The friends list is unavailable" in line)
    assert lines[notice + 1].startswith("Timestamp:")
    assert set(lines[notice + 2]) == {"\u2500"}


# Verifies a notice printed before monitoring starts stays a bare line, since the monitoring header closes that block
def test_a_verbose_notice_stays_bare_on_the_startup_screen(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "MONITORING_ACTIVE", False)

    monitor.verbose_notice("The friends list is unavailable, so friends alerts cannot fire")

    assert capsys.readouterr().out == "* The friends list is unavailable, so friends alerts cannot fire\n"


# Verifies a lasting outage is reported on the cycle it starts rather than on every cycle it continues
def test_a_lasting_outage_is_reported_once(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, failing_endpoints={"ISteamUser.GetFriendList"}, stop_after_sleeps=3)

    output = capsys.readouterr().out
    assert output.count("The friends list is unavailable, so friends alerts cannot fire") == 1


# Verifies the tracker reports each feature once while it is down and once when it comes back
def test_a_feature_outage_and_its_recovery_are_each_reported_once():
    tracker = monitor.FeatureOutageTracker()
    friends_down = {"friends": ("The friends list is unavailable", "The friends list is available again")}

    assert tracker.transitions(friends_down) == ["The friends list is unavailable"]
    assert tracker.transitions(friends_down) == []
    assert tracker.transitions({}) == ["The friends list is available again"]
    assert tracker.transitions({}) == []


# Verifies a working tracked feature produces no degradation warning
def test_a_healthy_cycle_reports_no_degradation(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch)

    output = capsys.readouterr().out
    assert "is unavailable, so" not in output


# Verifies the same degraded cycle prints nothing extra when neither diagnostic mode is on
def test_a_degraded_cycle_stays_quiet_without_diagnostics(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, failing_endpoints={"IPlayerService.GetSteamLevel", "ISteamUser.GetFriendList"}, diagnostics=False)

    output = capsys.readouterr().out
    assert "[DEBUG" not in output
    assert "is unavailable, so" not in output
    assert "Polling Steam:" not in output


# Returns an HTTP error carrying the given status, the way requests raises one
def http_error(status_code, message="request failed"):
    import requests as req

    response = req.Response()
    response.status_code = status_code
    return req.exceptions.HTTPError(message, response=response)


# Verifies a transient failure gets one short retry rather than waiting a whole polling interval
def test_a_transient_failure_retries_once_quickly(tmp_path, monkeypatch, capsys):
    _api, sleeps = run_one_cycle(tmp_path, monkeypatch, poll_error=TimeoutError("request timed out"), stop_after_sleeps=4)

    # The first sleep precedes the loop, then one short retry, then the full interval once the retry is spent
    assert sleeps[0] == 60
    assert sleeps[1] == monitor.TRANSIENT_RETRY_SECONDS
    assert sleeps[2] == 60
    output = capsys.readouterr().out
    assert f"* Error: The Steam Web API did not answer in time (retrying in {monitor.display_time(monitor.TRANSIENT_RETRY_SECONDS)})" in output


# Verifies a rate limit skips the short retry and waits the period Steam asked for
def test_a_rate_limit_waits_instead_of_retrying_quickly(tmp_path, monkeypatch, capsys):
    error = http_error(429)
    assert error.response is not None
    error.response.headers["Retry-After"] = "120"

    _api, sleeps = run_one_cycle(tmp_path, monkeypatch, poll_error=error, stop_after_sleeps=3)

    assert sleeps[0] == 60
    assert sleeps[1] == 120
    assert monitor.TRANSIENT_RETRY_SECONDS not in sleeps
    output = capsys.readouterr().out
    assert f"* Error: Steam is rate limiting requests (retrying in {monitor.display_time(120)})" in output


# Verifies a standard HTTP-date Retry-After value reaches the real monitoring sleep without crashing
def test_a_rate_limit_accepts_an_http_date(tmp_path, monkeypatch):
    error = http_error(429)
    assert error.response is not None
    error.response.headers["Retry-After"] = format_datetime(datetime.now(timezone.utc) + timedelta(seconds=120), usegmt=True)

    _api, sleeps = run_one_cycle(tmp_path, monkeypatch, poll_error=error, stop_after_sleeps=3)

    assert sleeps[0] == 60
    assert 115 <= sleeps[1] <= 120


# Verifies malformed and excessive Steam retry values fall back safely or stop at the one-hour cap
def test_steam_retry_after_values_are_bounded():
    malformed = http_error(429)
    excessive = http_error(429)
    assert malformed.response is not None and excessive.response is not None
    malformed.response.headers["Retry-After"] = "not-a-delay"
    excessive.response.headers["Retry-After"] = "999999"

    assert monitor.steam_retry_after_seconds(malformed.response, 60) == 60
    assert monitor.steam_retry_after_seconds(excessive.response, 60) == int(monitor.STEAM_MAX_RETRY_AFTER_SECONDS)


# Verifies the cap bounds only what Steam asked for, since clamping the tool's own polling interval would make
# a rate-limited run poll faster than it was configured to
def test_the_cap_does_not_shorten_the_tools_own_interval():
    unhelpful = http_error(429)
    assert unhelpful.response is not None
    beyond_the_cap = int(monitor.STEAM_MAX_RETRY_AFTER_SECONDS) + 600

    assert monitor.steam_retry_after_seconds(unhelpful.response, beyond_the_cap) == beyond_the_cap


# Verifies a failure that cannot be retried goes straight to the polling interval
def test_a_rejected_api_key_does_not_get_a_quick_retry(tmp_path, monkeypatch, capsys):
    _api, sleeps = run_one_cycle(tmp_path, monkeypatch, poll_error=http_error(403), stop_after_sleeps=3)

    assert sleeps[0] == 60
    assert sleeps[1] == 60
    assert monitor.TRANSIENT_RETRY_SECONDS not in sleeps
    assert "Steam rejected the configured Web API key" in capsys.readouterr().out


# Verifies the reminder keeps its own clock when the liveness banner is off, so switching the banner off neither
# silences a lasting failure nor brings back a block per cycle
def test_the_reminder_survives_where_the_banner_is_off(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "OUTAGE_REMINDER_SECONDS", 180)
    # The report lands on the third poll at 65 seconds, so the sixth and the ninth poll are the reminders
    _api, _sleeps = run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=http_error(503), stop_after_sleeps=9)

    output = capsys.readouterr().out
    assert output.count("* Error: The Steam Web API is temporarily unavailable") == 1
    assert output.count("* Monitoring degraded for 76561201960435530. ") == 2
    assert output.count("To fix: ") == 1


# Verifies a continuing outage is carried by the hourly reminder with a count, on a clock of its own rather
# than the liveness banner's
def test_a_continuing_outage_is_carried_by_the_hourly_reminder(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "OUTAGE_REMINDER_SECONDS", 240)
    _api, _sleeps = run_one_cycle(tmp_path, monkeypatch, poll_error=http_error(503), stop_after_sleeps=7, liveness_seconds=180)

    output = capsys.readouterr().out
    assert output.count("To fix: ") == 1
    assert output.count("The Steam Web API is temporarily unavailable") == 2
    assert "* Monitoring degraded for 76561201960435530. The Steam Web API is temporarily unavailable since " in output
    assert ", 6 failed checks\n" in output
    assert output.count("Liveness check, timestamp:") == 1
    assert "Monitoring healthy" not in output


# Verifies a failure that clears says so, since a throttled failure no longer stops printing when it is over
def test_a_cleared_outage_reports_its_recovery(tmp_path, monkeypatch, capsys):
    _api, _sleeps = run_one_cycle(tmp_path, monkeypatch, poll_error=http_error(503), stop_after_sleeps=3, healthy_after=2)

    output = capsys.readouterr().out
    assert "* Monitoring recovered for 76561201960435530 after " in output


# Verifies a check that reported the end of an outage restarts the quiet clock, since the banner speaks for a
# check that said nothing and would otherwise contradict the recovery line above it
def test_a_check_that_reported_a_recovery_does_not_claim_it_was_quiet(tmp_path, monkeypatch, capsys):
    _api, _sleeps = run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=http_error(503), stop_after_sleeps=6, healthy_after=3, liveness_seconds=180)

    output = capsys.readouterr().out
    assert "* Monitoring recovered for 76561201960435530 after " in output, "the check under test reported no recovery"
    assert "Monitoring healthy" not in output


# Verifies the reporter reports a new failure in full, stays quiet while it lasts and reminds once the reminder interval passes
def test_the_outage_reporter_reports_once_then_on_the_cadence(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    monkeypatch.setattr(monitor, "OUTAGE_REMINDER_SECONDS", 180)
    reporter = monitor.OutageReporter()
    advice = monitor.classify_recovery_error(RuntimeError("boom"), context="runtime")

    assert reporter.failed(advice) == "full"
    clock[0] += 60
    assert reporter.failed(advice) == ""
    clock[0] += 119
    assert reporter.failed(advice) == ""
    clock[0] += 1
    assert reporter.failed(advice) == "reminder"
    assert reporter.failed(advice) == ""
    assert reporter.recovered() is not None
    assert reporter.recovered() is None


# Verifies the reporter waits for the next check to confirm a retryable failure, and the first check still counts
def test_the_outage_reporter_confirms_a_retryable_failure(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    reporter = monitor.OutageReporter(confirm_checks=2)
    retryable = monitor.classify_recovery_error(RuntimeError("boom"), context="runtime")
    rejected = monitor.classify_recovery_error(http_error(403), context="runtime")

    assert reporter.failed(retryable) == ""
    assert reporter.recovered() is None, "a failure that was never reported recovers in silence"
    assert reporter.failed(retryable) == ""
    clock[0] += 5
    assert reporter.failed(retryable) == "full"
    assert (reporter.since, reporter.failures) == (1000000, 2)
    assert reporter.recovered() == 5
    assert reporter.failed(rejected) == "full", "a failure nothing can retry away is not held for confirmation"


# Verifies the reporter treats every network code as one outage and any other change as a one-line note
def test_the_outage_reporter_merges_network_codes_and_notes_other_changes(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    reporter = monitor.OutageReporter()
    timeout = monitor.classify_recovery_error(TimeoutError("request timed out"), context="runtime")
    unreachable = monitor.classify_recovery_error(OSError("connection refused"), context="runtime")
    unavailable = monitor.classify_recovery_error(http_error(503), context="runtime")
    rejected = monitor.classify_recovery_error(http_error(403), context="runtime")
    assert (monitor.outage_family(timeout.code), monitor.outage_family(unreachable.code)) == ("network", "network")

    assert reporter.failed(timeout) == "full"
    assert reporter.failed(unreachable) == ""
    assert reporter.failed(timeout) == ""
    assert reporter.failed(unavailable) == "changed"
    assert reporter.failed(unavailable) == ""
    assert reporter.failed(rejected) == "full"
    assert reporter.since == 1000000


# Verifies a category change mid-outage keeps the outage start, so the alert delay and the reminder still elapse
def test_an_outage_that_changes_category_keeps_its_start(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    reporter = monitor.OutageReporter()
    first = monitor.classify_recovery_error(RuntimeError("boom"), context="runtime")
    second = monitor.classify_recovery_error(OSError(24, "Too many open files"))
    assert first.code != second.code

    assert reporter.failed(first) == "full"
    for index in range(60):
        clock[0] += 15
        reporter.failed(second if index % 2 else first)

    assert reporter.since == 1000000
    assert reporter.recovered() == 900


# Verifies the reminder follows the clock, so a run that retries faster than it polls does not remind more often
def test_the_outage_reminder_follows_the_clock_not_the_check_count(monkeypatch):
    clock = [1000000.0]
    monkeypatch.setattr(monitor.time, "time", lambda: clock[0])
    reporter = monitor.OutageReporter()
    advice = monitor.classify_recovery_error(RuntimeError("boom"), context="runtime")

    monkeypatch.setattr(monitor, "OUTAGE_REMINDER_SECONDS", 900)
    assert reporter.failed(advice) == "full"
    outcomes = []
    for _ in range(60):
        clock[0] += 15
        outcomes.append(reporter.failed(advice))

    assert outcomes.count("reminder") == 1


# Verifies a delivered error channel stays suppressed while a failed channel retries during the same outage, once
# its five minute hold has passed, so a webhook service that is down is not dialled on every cycle
@pytest.mark.parametrize("stop_after_sleeps,expected", [(12, [(True, True)]), (14, [(True, True), (False, True)])])
def test_a_continuing_outage_retries_only_failed_notification_channels(tmp_path, monkeypatch, capsys, stop_after_sleeps, expected):
    deliveries = []

    # Records which delivery channels each outage cycle requests
    def record_delivery(*_args, **kwargs):
        deliveries.append((kwargs["email_enabled"], kwargs["webhook_enabled"]))
        return True, False

    monkeypatch.setattr(monitor, "send_notification_channels", record_delivery)
    run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=http_error(503), stop_after_sleeps=stop_after_sleeps, error_notifications=True)

    assert deliveries == expected
    assert "* The webhook alert is on hold for 5 minutes after 1 attempt, then tried again" in capsys.readouterr().out


# Verifies a failure the tool can retry away is alerted only once the outage has lasted the alert delay, so a
# blip of a few cycles reaches nobody while a real outage still does
@pytest.mark.parametrize("stop_after_sleeps,expected", [(7, []), (8, [(True, True)])])
def test_a_retryable_failure_is_alerted_once_the_outage_has_lasted(tmp_path, monkeypatch, stop_after_sleeps, expected):
    deliveries = []
    monkeypatch.setattr(monitor, "send_notification_channels", lambda *_args, **kwargs: deliveries.append((kwargs["email_enabled"], kwargs["webhook_enabled"])) or (True, True))

    # The short retry and then one minute intervals put the seventh failing cycle past the five minute delay
    run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=http_error(503), stop_after_sleeps=stop_after_sleeps, error_notifications=True)

    assert deliveries == expected


# Verifies one outage earns one alert per channel however the failure changes, since alternating categories used
# to forget the delivered alert on every transition and send one per cycle
def test_alternating_failure_categories_deliver_one_alert(tmp_path, monkeypatch):
    deliveries = []
    monkeypatch.setattr(monitor, "send_notification_channels", lambda *args, **kwargs: deliveries.append(args[1]) or (True, True))

    # A rejected key is alerted at once while an unavailable service waits five minutes, so each return to the
    # rejected key used to look like a fresh failure and earn another alert
    run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=lambda polls: http_error(403 if polls % 2 else 503), stop_after_sleeps=5, error_notifications=True)

    assert len(deliveries) == 1


# Verifies a failure nothing here can retry away is alerted on the first cycle, since waiting would change nothing
def test_a_failure_that_cannot_clear_itself_is_alerted_at_once(tmp_path, monkeypatch):
    deliveries = []
    monkeypatch.setattr(monitor, "send_notification_channels", lambda *args, **kwargs: deliveries.append(args[1]) or (True, True))

    run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=http_error(403), stop_after_sleeps=2, error_notifications=True)

    assert len(deliveries) == 1
    assert deliveries[0] == "Steam Monitor error: Steam rejected the configured Web API key (user: TestPlayer)"


# Verifies a retry that reaches the screen on a quiet cycle still ends with a timestamp
def test_a_delivery_retry_on_a_quiet_cycle_ends_with_a_timestamp(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(monitor, "webhook_event_enabled", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(monitor, "send_email", lambda *_args, **_kwargs: 1)
    run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=http_error(503), stop_after_sleeps=16, error_notifications=True, liveness_seconds=180)

    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    deliveries = [index for index, line in enumerate(lines) if line.startswith("Sending email notification")]

    assert len(deliveries) > 1, lines
    for index in deliveries:
        assert any(line.startswith("Timestamp:") for line in lines[index + 1:index + 3]), lines[index:index + 3]


# Verifies a healthy poll reports the state it read, not only the call it was about to make
def test_a_healthy_cycle_reports_its_poll_outcome(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch)

    output = capsys.readouterr().out
    assert "Polling Steam: steamid=76561201960435530, endpoints=ISteamUser.GetPlayerSummaries" in output
    assert "Polling Steam: steamid=76561201960435530, personastate=0, outcome=OK" in output


# Verifies a quiet cycle leaves verbose silent, since one line per check buries the events worth reading
def test_a_quiet_cycle_stays_silent_in_verbose(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, debug=False)

    output = capsys.readouterr().out
    assert "Completed check" not in output
    assert "[DEBUG" not in output


# Verifies the completed check is still recorded for anyone who asked for the full trace
def test_a_quiet_cycle_records_the_completed_check_in_debug(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch)

    output = capsys.readouterr().out
    assert "Completed check: check=#1, user=76561201960435530, outcome=OK" in output


# Verifies a failed cycle is recorded like a healthy one, so a trace never ends without saying how the check went
def test_a_failed_cycle_records_its_outcome_in_debug(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, poll_error=http_error(403), stop_after_sleeps=3)

    output = capsys.readouterr().out
    assert "Completed check: check=#1, user=76561201960435530, outcome=failed, code=auth.api_key_invalid, error=HTTPError: " in output


# Verifies every wait a failing check leads into says how long it is and what it is waiting for, since the three
# paths wait for different reasons and a trace that stops at the failure leaves the pause unexplained
def test_every_wait_after_a_failure_says_how_long_it_is_and_why(tmp_path, monkeypatch, capsys):
    rate_limited = http_error(429)
    assert rate_limited.response is not None
    rate_limited.response.headers["Retry-After"] = "120"

    run_one_cycle(tmp_path, monkeypatch, poll_error=rate_limited, stop_after_sleeps=3)
    assert "Retry wait: check=#1, due_in=2 minutes, reason=steam rate limited the request" in capsys.readouterr().out

    run_one_cycle(tmp_path, monkeypatch, poll_error=http_error(503), stop_after_sleeps=3)
    output = capsys.readouterr().out
    assert f"Retry wait: check=#1, due_in={monitor.display_time(monitor.TRANSIENT_RETRY_SECONDS)}, reason=one short retry before the full interval" in output
    assert "Retry wait: check=#2, due_in=1 minute, reason=waiting the polling interval after a failed check" in output


# Verifies the liveness banner says what it is reporting rather than printing a bare timestamp
def test_the_liveness_banner_explains_itself(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, liveness_seconds=60)

    output = capsys.readouterr().out
    assert "Monitoring healthy for 76561201960435530. The user is offline with no status or game change since the last check" in output
    assert "Liveness check, timestamp:" in output


# Verifies the banner explains itself without --verbose too, so a plain run never prints a bare timestamp
def test_the_liveness_banner_explains_itself_without_diagnostics(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, liveness_seconds=60, diagnostics=False)

    output = capsys.readouterr().out
    assert "* Monitoring healthy for 76561201960435530. The user is offline with no status or game change since the last check" in output
    assert "Liveness check, timestamp:" in output


# Verifies the banner follows the clock, so a target polled on the shorter active interval is not reminded more often
def test_the_liveness_banner_follows_the_clock_not_the_check_count(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, liveness_seconds=120, stop_after_sleeps=5, persona_state=1)

    assert capsys.readouterr().out.count("Monitoring healthy for") == 1


# Verifies an online target still reports the liveness banner, since nothing changed there either
def test_the_liveness_banner_reports_an_online_target(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, liveness_seconds=30, persona_state=1)

    output = capsys.readouterr().out
    assert "Monitoring healthy for 76561201960435530. The user is online with no status or game change since the last check" in output
    assert "Liveness check, timestamp:" in output


# Verifies a cycle stays silent about its progress when neither diagnostic mode is on
def test_a_quiet_cycle_stays_silent_without_diagnostics(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, diagnostics=False)

    output = capsys.readouterr().out
    assert "Completed check" not in output
    assert "outcome=OK" not in output


# Fails a poll with a timeout and then an unreachable host, the way one internet outage classifies
def flapping_network(polls):
    return TimeoutError("request timed out") if polls % 2 else OSError("connection refused")


# Verifies a failure the short retry clears prints nothing, since a blip is not worth a report
def test_a_blip_absorbed_by_the_short_retry_prints_nothing(tmp_path, monkeypatch, capsys):
    _api, sleeps = run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=http_error(503), stop_after_sleeps=4, healthy_after=2)

    output = capsys.readouterr().out
    assert "* Error:" not in output
    assert "Monitoring recovered" not in output
    assert sleeps[1] == monitor.TRANSIENT_RETRY_SECONDS


# Verifies the short retry failing too is what makes the failure worth a report, and then its recovery worth a line
def test_a_failure_confirmed_by_the_short_retry_is_reported(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=http_error(503), stop_after_sleeps=5, healthy_after=3)

    output = capsys.readouterr().out
    assert output.count("* Error: The Steam Web API is temporarily unavailable (retrying in 1 minute)") == 1
    assert "(retrying in 5 seconds)" not in output, "the first failing poll is the one the short retry confirms in silence"
    assert "* Monitoring recovered for 76561201960435530 after 1 minute, 5 seconds" in output


# Verifies verbose is the mode that wants every decision, so it sees the first failing poll and its recovery
def test_verbose_reports_the_first_failing_poll(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, poll_error=http_error(503), stop_after_sleeps=4, healthy_after=2)

    output = capsys.readouterr().out
    assert output.count("* Error: The Steam Web API is temporarily unavailable (retrying in 5 seconds)") == 1
    assert "* Monitoring recovered for 76561201960435530 after 5 seconds" in output


# Verifies a failure nothing here can retry away gains nothing from a confirming poll, so it is reported at once
def test_a_failure_that_cannot_clear_itself_is_reported_at_once(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=http_error(403), stop_after_sleeps=2)

    assert capsys.readouterr().out.count("* Error: Steam rejected the configured Web API key") == 1


# Verifies an internet outage that classifies as a timeout on one poll and as unreachable on the next is one
# outage, so it is reported once rather than on every change
def test_an_internet_outage_that_flaps_is_one_outage(tmp_path, monkeypatch, capsys):
    run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=flapping_network, stop_after_sleeps=12)

    output = capsys.readouterr().out
    assert output.count("* Error:") == 1
    assert output.count("To fix: ") == 1
    assert "Monitoring failure changed" not in output


# Verifies a reported outage that starts failing differently is still one outage, so the change is one line
# rather than a second report
def test_a_second_failure_category_is_noted_in_one_line(tmp_path, monkeypatch, capsys):

    # Changes the simulated outage from an HTTP error to a timeout
    def changing(polls):
        return http_error(503) if polls < 6 else TimeoutError("request timed out")

    run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=changing, stop_after_sleeps=10)

    lines = capsys.readouterr().out.splitlines()
    reports = [line for line in lines if line.startswith("* Error:")]
    changes = [number for number, line in enumerate(lines) if line.startswith("* Monitoring failure changed for 76561201960435530. ")]
    assert len(reports) == 1 and "temporarily unavailable" in reports[0]
    assert len(changes) == 1 and lines[changes[0]].endswith("The Steam Web API did not answer in time")
    assert lines[changes[0] + 1].startswith("Timestamp:")
    assert "\n".join(lines).count("To fix: ") == 1


# Verifies a flapping internet outage alerts once, since each network failure is the same outage to the channels too
def test_an_internet_outage_that_flaps_alerts_once(tmp_path, monkeypatch):
    deliveries = []
    monkeypatch.setattr(monitor, "send_notification_channels", lambda *args, **kwargs: deliveries.append(args[1]) or (True, True))

    run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=flapping_network, stop_after_sleeps=12, error_notifications=True)

    assert len(deliveries) == 1


# Verifies a games-library file written by an earlier release loads instead of stopping the run, since it counted
# the response list while deduplicating the IDs and the two can disagree in a file this tool wrote itself
def test_a_legacy_games_library_file_still_loads(tmp_path, monkeypatch, capsys):
    legacy = tmp_path / monitor.default_games_file(STEAM_ID)
    legacy.write_text(json.dumps({"game_count": 3, "appids": [10, 20]}), encoding="utf-8")

    run_one_cycle(tmp_path, monkeypatch, diagnostics=False)

    output = capsys.readouterr().out
    assert "Cannot load the games library" not in output
    assert "games library changed" not in output


# Verifies a saved games library this tool cannot use costs the comparison baseline rather than the whole run
def test_an_unusable_games_library_file_does_not_stop_the_run(tmp_path, monkeypatch, capsys):
    unusable = tmp_path / monitor.default_games_file(STEAM_ID)
    unusable.write_text(json.dumps({"game_count": 3, "appids": ["ten"]}), encoding="utf-8")

    run_one_cycle(tmp_path, monkeypatch, diagnostics=False)

    output = capsys.readouterr().out
    assert "* Warning: Cannot load the games library" in output
    assert "starts a fresh baseline" in output
    assert "games library changed" not in output


# Verifies a cleared outage answers the failure alert on the same channel, so an inbox is not left with an outage that never ends
def test_a_cleared_outage_answers_the_failure_alert(tmp_path, monkeypatch):
    deliveries = []
    monkeypatch.setattr(monitor, "send_notification_channels", lambda *args, **kwargs: deliveries.append(args[1]) or (True, True))

    run_one_cycle(tmp_path, monkeypatch, diagnostics=False, poll_error=http_error(403), stop_after_sleeps=3, healthy_after=2, error_notifications=True)

    assert len(deliveries) == 2
    assert deliveries[0] == "Steam Monitor error: Steam rejected the configured Web API key (user: TestPlayer)"
    assert deliveries[1].startswith("Steam Monitor recovered: monitoring TestPlayer resumed after ")

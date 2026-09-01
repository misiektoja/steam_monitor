"""Tests the guided setup wizard, the zero-argument welcome screen and the input normalizers."""

import itertools
import os
import pty
import re
import select
import subprocess
import sys
from pathlib import Path

import signal
import pytest

import steam_monitor as monitor


REPO_ROOT = Path(__file__).resolve().parents[1]
STEAM64 = 76561197960435530
API_KEY = "A" * 32
WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/verysecrettokenvalue"


@pytest.fixture
# Restores every module-level setting the wizard reads or writes back, plus the secrets it exports on save
def wizard_globals(monkeypatch):
    snapshot = {name: value for name, value in vars(monitor).items() if name.isupper()}
    environment_snapshot = {name: os.environ.get(name) for name in monitor.SECRET_KEYS}
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", False)
    monkeypatch.setattr(monitor, "STEAM_API_KEY", "your_steam_web_api_key")
    yield
    for name, value in snapshot.items():
        setattr(monitor, name, value)
    for name, value in environment_snapshot.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


@pytest.fixture(autouse=True)
# Keeps the wizard's mail server sign-in check offline, so a scripted run never opens a connection
def accepted_smtp_sign_in(monkeypatch):
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: None)


# Returns an input function that replays scripted answers and records the prompts it was asked
def scripted_input(answers, transcript=None):
    remaining = list(answers)

    def respond(prompt):
        if transcript is not None:
            transcript.append(prompt)
        if not remaining:
            raise EOFError("the script ran out of answers")
        return remaining.pop(0)

    return respond


# Runs the whole wizard offline with a scripted operator and no real Steam call
def run_wizard(tmp_path, monkeypatch, answers, secrets=None, transcript=None, initial_target=None, validator=None, input_func=None):
    monkeypatch.setattr(monitor, "validate_steam_api_key", validator or (lambda _key, timeout=10: True))
    monkeypatch.setattr(monitor, "run_doctor", lambda **_kwargs: 0)
    secret_answers = list(secrets or [API_KEY])

    def fake_getpass(prompt):
        if transcript is not None:
            transcript.append(prompt)
        return secret_answers.pop(0) if secret_answers else ""

    code = monitor.run_setup_wizard(
        initial_target=initial_target,
        config_file=str(tmp_path / "steam_monitor.conf"),
        env_file=str(tmp_path / ".env"),
        input_func=input_func or scripted_input(answers, transcript),
        getpass_func=fake_getpass,
        interactive=True,
    )
    return code


# The shortest answer script that reaches Save: target, two intervals, no email, no webhook, save, no doctor
def minimal_answers(target=str(STEAM64)):
    return [target, "y", "5m", "45s", "n", "n", "y", "", "", "1", "n", "n"]


# Verifies explicit setup keeps the shared startup screen-clearing behavior
def test_setup_cli_clears_screen_before_wizard(tmp_path, monkeypatch, wizard_globals):
    clear_calls = []
    monkeypatch.setattr(monitor, "CLEAR_SCREEN", True)
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled: clear_calls.append(enabled))
    monkeypatch.setattr(monitor, "print_startup_banner", lambda: None)
    monkeypatch.setattr(monitor.signal, "signal", lambda *args: None)
    monkeypatch.setattr(monitor, "find_config_file", lambda _path=None: None)
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **_kwargs: 0)
    monkeypatch.setattr(monitor.sys, "argv", ["steam_monitor", "--setup", "--config-file", str(tmp_path / "steam_monitor.conf"), "--env-file", "none"])

    with pytest.raises(SystemExit) as exit_error:
        monitor.main()

    assert exit_error.value.code == 0
    assert clear_calls == [True]


# Verifies a duration is accepted in the formats people actually type
@pytest.mark.parametrize("value,expected", [
    ("30s", 30), ("2m", 120), ("1.5h", 5400), ("1h 30m", 5400), ("1h30m", 5400),
    ("1d", 86400), ("90", 90), ("2 minutes", 120), ("45 sec", 45), ("  3h  ", 10800),
])
def test_durations_accept_human_formats(value, expected):
    assert monitor.parse_duration_input(value) == expected


# Verifies anything that is not a duration is refused rather than silently read as seconds
@pytest.mark.parametrize("value", ["", "   ", "abc", "5x", "-10", "0", "m", None, True, "1h abc"])
def test_non_durations_are_refused(value):
    assert monitor.parse_duration_input(value) is None


# Verifies every way a Steam profile is written normalizes to one canonical Steam64 ID
@pytest.mark.parametrize("value", [
    str(STEAM64),
    f"https://steamcommunity.com/profiles/{STEAM64}",
    f"https://steamcommunity.com/profiles/{STEAM64}/",
    f"steamcommunity.com/profiles/{STEAM64}",
    f"http://www.steamcommunity.com/profiles/{STEAM64}",
])
def test_every_target_form_normalizes_to_one_id(value):
    assert monitor.normalize_steam_target(value) == (STEAM64, None)


# Verifies a Steam3 identifier is accepted, since it is what a console or profile page shows
def test_a_steam3_identifier_is_accepted():
    steam64, vanity = monitor.normalize_steam_target("[U:1:22202]")

    assert vanity is None
    assert steam64 == int(monitor.steam.steamid.SteamID("[U:1:22202]").as_64)


# Verifies a vanity name is handed back for resolution rather than guessed at
@pytest.mark.parametrize("value,expected", [
    ("misiektoja", "misiektoja"),
    ("https://steamcommunity.com/id/misiektoja/", "misiektoja"),
    ("steamcommunity.com/id/misiektoja", "misiektoja"),
    ("https://steamcommunity.com/id/name.with.dot/", "name.with.dot"),
])
def test_a_vanity_name_is_returned_for_resolution(value, expected):
    assert monitor.normalize_steam_target(value) == (None, expected)


# Verifies an unusable target is refused with guidance rather than accepted and failing later
@pytest.mark.parametrize("value", ["", "   ", "not a url", "https://example.com/id/x", "https://steamcommunity.com/", "https://steamcommunity.com/app/440", None, True])
def test_an_unusable_target_is_refused(value):
    with pytest.raises(ValueError):
        monitor.normalize_steam_target(value)


# Verifies the wizard writes nothing at all until Save is chosen
def test_nothing_is_written_before_save(tmp_path, monkeypatch, wizard_globals):
    # Discard, confirm the discard
    answers = [str(STEAM64), "y", "5m", "45s", "n", "n", "y", "", "", "3", "y"]

    code = run_wizard(tmp_path, monkeypatch, answers)

    assert code == 1
    assert not (tmp_path / "steam_monitor.conf").exists()
    assert not (tmp_path / ".env").exists()


# Verifies declining the discard keeps every answer rather than restarting
def test_declining_the_discard_keeps_the_answers(tmp_path, monkeypatch, wizard_globals, capsys):
    # Discard, decline the discard, then save, then decline doctor
    answers = [str(STEAM64), "y", "5m", "45s", "n", "n", "y", "", "", "3", "n", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers) == 0

    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    assert values["STEAM_CHECK_INTERVAL"] == 300
    assert "Setup answers retained." in capsys.readouterr().out


# Verifies saving writes both files with the answers given
def test_saving_writes_both_files(tmp_path, monkeypatch, wizard_globals):
    assert run_wizard(tmp_path, monkeypatch, minimal_answers()) == 0

    config = tmp_path / "steam_monitor.conf"
    env_file = tmp_path / ".env"
    assert config.exists() and env_file.exists()
    values = monitor.parse_config_content(config.read_text(encoding="utf-8"))
    assert values["STEAM_CHECK_INTERVAL"] == 300
    assert values["STEAM_ACTIVE_CHECK_INTERVAL"] == 45
    assert f'STEAM_API_KEY="{API_KEY}"' in env_file.read_text(encoding="utf-8")


# Verifies a fresh wizard resolves a vanity target after collecting its Steam Web API key
def test_fresh_setup_resolves_vanity_after_authentication(tmp_path, monkeypatch, wizard_globals, capsys):
    monkeypatch.setattr(monitor, "resolve_steam_community_url", lambda _url, key: STEAM64 if key == API_KEY else pytest.fail("wrong API key"))

    assert run_wizard(tmp_path, monkeypatch, minimal_answers(target="misiektoja")) == 0

    assert f"Resolved 'misiektoja' to Steam64 ID {STEAM64}." in capsys.readouterr().out


# Verifies the generated configuration survives the tool's own parser, so the next run can read it
def test_the_generated_configuration_round_trips(tmp_path, monkeypatch, wizard_globals):
    run_wizard(tmp_path, monkeypatch, minimal_answers())

    monitor.validate_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"), "<generated>")


# Verifies the secret goes only to the dotenv file and never into the configuration
def test_the_secret_never_reaches_the_configuration(tmp_path, monkeypatch, wizard_globals):
    run_wizard(tmp_path, monkeypatch, minimal_answers())

    assert API_KEY not in (tmp_path / "steam_monitor.conf").read_text(encoding="utf-8")
    assert API_KEY in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies editing one section reverts only that section and leaves the other answers standing
def test_editing_one_section_keeps_the_others(tmp_path, monkeypatch, wizard_globals):
    answers = [
        str(STEAM64), "y", "5m", "45s", "n", "n", "y", "", "",   # target, persist, polling, no email, no webhook, output files
        "2", "2", "9m", "70s",                      # review, choose Polling, new intervals
        "1", "n", "n",                              # save, decline doctor, decline monitoring
    ]

    assert run_wizard(tmp_path, monkeypatch, answers) == 0

    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    assert values["STEAM_CHECK_INTERVAL"] == 540
    assert values["STEAM_ACTIVE_CHECK_INTERVAL"] == 70
    # The target and the API key came from earlier sections and must have survived the edit
    assert f'STEAM_API_KEY="{API_KEY}"' in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies editing the target section asks for it again rather than keeping the previous answer
def test_editing_the_target_section_asks_again(tmp_path, monkeypatch, wizard_globals, capsys):
    other_id = "76561197960287930"
    answers = [
        str(STEAM64), "y", "5m", "45s", "n", "n", "y", "", "",
        "2", "1", other_id, "y",   # review, choose Target, give a different profile, persist it
        "1", "n", "n",
    ]

    run_wizard(tmp_path, monkeypatch, answers)

    summary = capsys.readouterr().out.rsplit("Setup summary", 1)[1]
    assert other_id in summary
    assert str(STEAM64) not in summary
    assert monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))["TARGET_STEAM_ID"] == other_id


# Verifies declining email turns every email alert off, so the summary cannot promise alerts that never fire
def test_declining_email_turns_every_email_alert_off(tmp_path, monkeypatch, wizard_globals):
    run_wizard(tmp_path, monkeypatch, minimal_answers())

    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    for key in ("ACTIVE_INACTIVE_NOTIFICATION", "GAME_CHANGE_NOTIFICATION", "ERROR_NOTIFICATION"):
        assert values[key] is False


# Verifies a blank key is offered the way out rather than only being asked for again
def test_an_empty_api_key_answer_is_asked_again(tmp_path, monkeypatch, wizard_globals):
    transcript = []
    # The extra "n" declines "Continue without the Steam Web API key?", which asks for the key a second time
    answers = [str(STEAM64), "y", "5m", "45s", "n", "n", "n", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=["", API_KEY], transcript=transcript) == 0

    assert any("Continue without the Steam Web API key?" in prompt for prompt in transcript)
    assert f'STEAM_API_KEY="{API_KEY}"' in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies a key Steam refuses is offered again, since a mistyped key is the common case
def test_a_rejected_api_key_is_asked_again(tmp_path, monkeypatch, wizard_globals):
    accepted = [False, True]
    transcript = []
    # The extra "y" accepts the offer to enter the refused key again
    answers = [str(STEAM64), "y", "5m", "45s", "y", "n", "n", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=["bad-key", API_KEY], transcript=transcript, validator=lambda _key, timeout=10: accepted.pop(0)) == 0

    assert any("Try entering the Steam Web API key again?" in prompt for prompt in transcript)
    assert f'STEAM_API_KEY="{API_KEY}"' in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies a key Steam keeps refusing can be given up on, since it cannot be corrected from inside the loop
def test_a_rejected_api_key_can_be_abandoned(tmp_path, monkeypatch, wizard_globals):
    # The extra "n" declines entering the refused key again
    answers = [str(STEAM64), "y", "5m", "45s", "n", "n", "n", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=["bad-key"], validator=lambda _key, timeout=10: False) == 0

    assert not (tmp_path / ".env").exists(), "a refused key was written anyway"


# The answers that reach each mail server question, so every one of them can be left blank in turn
EMAIL_ANSWERS_BEFORE = {
    "SMTP_HOST": [],
    "SMTP_USER": ["smtp.example.com", "587", "y"],
    "SENDER_EMAIL": ["smtp.example.com", "587", "y", "monitor"],
    "RECEIVER_EMAIL": ["smtp.example.com", "587", "y", "monitor", "sender@example.com"],
}


@pytest.mark.parametrize("abandoned", sorted(EMAIL_ANSWERS_BEFORE))
# Verifies an abandoned mail server answer switches email off rather than writing half a configuration
def test_an_abandoned_mail_server_answer_turns_email_off(tmp_path, monkeypatch, wizard_globals, capsys, abandoned):
    monkeypatch.setattr(monitor, "ERROR_NOTIFICATION", True)
    monkeypatch.setattr(monitor, "GAME_CHANGE_NOTIFICATION", True)
    # Cleared so the prompts have no default to fall back on, which is what a first-time setup looks like
    for name in EMAIL_ANSWERS_BEFORE:
        monkeypatch.setattr(monitor, name, "")
    # One blank mail server answer, then declining to enter it again, then declining webhooks
    answers = [str(STEAM64), "y", "5m", "45s", "y"] + EMAIL_ANSWERS_BEFORE[abandoned] + ["", "n", "n", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers) == 0

    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    assert values["ERROR_NOTIFICATION"] is False
    assert values["GAME_CHANGE_NOTIFICATION"] is False
    assert "Email notifications stay off" in capsys.readouterr().out


# Verifies a blank destination is told apart from a malformed one and that skipping it leaves the channel off
def test_a_blank_webhook_url_is_worded_as_a_blank_one(tmp_path, monkeypatch, wizard_globals, capsys):
    transcript = []
    # The "y" accepts continuing without a URL, which is what the blank wording offers
    answers = [str(STEAM64), "y", "5m", "45s", "n", "y", "1", "y", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, ""], transcript=transcript) == 0

    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    assert values["WEBHOOK_ENABLED"] is False
    assert values["WEBHOOK_ERROR_NOTIFICATION"] is False
    assert any("Continue without the webhook URL?" in prompt for prompt in transcript)
    assert "complete HTTPS webhook URL" not in capsys.readouterr().out
    assert "WEBHOOK_URL" not in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies a URL the wizard cannot use can be given up on, which leaves the channel and its alerts off
def test_a_malformed_webhook_url_can_be_abandoned(tmp_path, monkeypatch, wizard_globals, capsys):
    # The "n" declines entering the malformed URL again
    answers = [str(STEAM64), "y", "5m", "45s", "n", "y", "1", "n", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "not-a-url"]) == 0

    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    assert values["WEBHOOK_ENABLED"] is False
    assert values["WEBHOOK_ERROR_NOTIFICATION"] is False
    assert "complete HTTPS webhook URL" in capsys.readouterr().out
    assert "WEBHOOK_URL" not in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies a token pasted with its authorization scheme can be given up on without losing the topic already entered
def test_a_pasted_ntfy_authorization_scheme_can_be_abandoned(tmp_path, monkeypatch, wizard_globals):
    transcript = []
    # The "n" declines entering the token again, leaving the topic URL that was already accepted
    answers = [str(STEAM64), "y", "5m", "45s", "n", "y", "2", "y", "n", "n", "1", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "private-topic", "Bearer tk_a_real_looking_token"], transcript=transcript) == 0

    assert any("Try entering the ntfy access token again?" in prompt for prompt in transcript)
    env = (tmp_path / ".env").read_text(encoding="utf-8")
    assert 'WEBHOOK_URL="https://ntfy.sh/private-topic"' in env
    assert "NTFY_ACCESS_TOKEN" not in env


# Verifies a blank token is read as no token, so an optional answer cannot trap the wizard or save an empty secret
def test_a_blank_ntfy_access_token_means_no_token(tmp_path, monkeypatch, wizard_globals):
    answers = [str(STEAM64), "y", "5m", "45s", "n", "y", "2", "y", "n", "1", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "private-topic", ""]) == 0

    env = (tmp_path / ".env").read_text(encoding="utf-8")
    assert 'WEBHOOK_URL="https://ntfy.sh/private-topic"' in env
    assert "NTFY_ACCESS_TOKEN" not in env


# Verifies the webhook service is chosen before the URL is pasted, the shared order across these tools
def test_the_webhook_service_is_chosen_before_the_url(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = [str(STEAM64), "y", "5m", "45s", "n", "y", "1", "1", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, WEBHOOK_URL]) == 0

    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    assert values["WEBHOOK_ENABLED"] is True
    assert values["WEBHOOK_PROVIDER"] == "discord"
    assert values["WEBHOOK_ACTIVE_NOTIFICATION"] is True and values["WEBHOOK_STATUS_NOTIFICATION"] is False
    assert "Which webhook service should receive alerts?" in capsys.readouterr().out
    assert WEBHOOK_URL in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies a bare ntfy topic name is expanded to a full ntfy.sh URL, as the shared prompt promises
def test_a_bare_ntfy_topic_becomes_a_full_url(tmp_path, monkeypatch, wizard_globals):
    answers = [str(STEAM64), "y", "5m", "45s", "n", "y", "2", "n", "n", "1", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "my-topic"]) == 0

    assert "https://ntfy.sh/my-topic" in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies a rejected duration is asked again instead of being stored as something else
def test_a_rejected_duration_is_asked_again(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = [str(STEAM64), "y", "banana", "5m", "45s", "n", "n", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers) == 0

    assert "Enter a positive duration such as" in capsys.readouterr().out
    assert monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))["STEAM_CHECK_INTERVAL"] == 300


# Verifies a rejected target is asked again with the guidance the reader needs
def test_a_rejected_target_is_asked_again(tmp_path, monkeypatch, wizard_globals, capsys):
    # the rejected link is followed by the retry offer, which the blank answer accepts
    answers = ["https://example.com/nope", "", str(STEAM64), "y", "5m", "45s", "n", "n", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers) == 0
    assert "Enter a Steam64 ID" in capsys.readouterr().out


# Verifies an existing configuration is replaced only after the user agrees, and is backed up rather than overwritten
def test_an_existing_configuration_is_backed_up(tmp_path, monkeypatch, wizard_globals):
    config = tmp_path / "steam_monitor.conf"
    config.write_text("CLEAR_SCREEN = False\n", encoding="utf-8")

    run_wizard(tmp_path, monkeypatch, ["y", *minimal_answers()])

    backups = list(tmp_path.glob("steam_monitor.conf.*.bak"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "CLEAR_SCREEN = False\n"


# Verifies the secret prompts do not repeat where secrets are stored, which the header already said once
def test_secret_prompts_do_not_repeat_the_destination(tmp_path, monkeypatch, wizard_globals):
    transcript = []

    run_wizard(tmp_path, monkeypatch, minimal_answers(), transcript=transcript)

    secret_prompts = [prompt for prompt in transcript if "API key" in prompt and "hidden" not in prompt]
    assert secret_prompts
    for prompt in secret_prompts:
        assert ".env" not in prompt and "dotenv" not in prompt.casefold()


# Verifies the shared prompt wording is used, since a user of two of these tools learns it once
def test_the_shared_prompt_wording_is_used(tmp_path, monkeypatch, wizard_globals):
    transcript = []

    run_wizard(tmp_path, monkeypatch, minimal_answers(), transcript=transcript)

    assert any(prompt.startswith("Run doctor now? It writes no files and offers real delivery tests only with separate approval.") for prompt in transcript)


# Runs the wizard with a real doctor call, so the values it hands over can be inspected
def run_wizard_with_doctor(tmp_path, monkeypatch, answers, secrets, observed):
    monkeypatch.setattr(monitor, "validate_steam_api_key", lambda _key, timeout=10: True)

    def record_doctor(**kwargs):
        observed["values"] = {name: getattr(monitor, name) for name in ("STEAM_API_KEY", "SMTP_PASSWORD", "WEBHOOK_URL")}
        observed["sources"] = monitor.doctor_secret_sources(kwargs.get("env_path"))
        return 0

    monkeypatch.setattr(monitor, "run_doctor", record_doctor)
    remaining_secrets = list(secrets)
    return monitor.run_setup_wizard(
        config_file=str(tmp_path / "steam_monitor.conf"),
        env_file=str(tmp_path / ".env"),
        input_func=scripted_input(answers),
        getpass_func=lambda _prompt: remaining_secrets.pop(0) if remaining_secrets else "",
        interactive=True,
    )


# Verifies the secrets just entered survive into doctor, which the config placeholders used to overwrite
def test_doctor_sees_the_secrets_setup_just_saved(tmp_path, monkeypatch, wizard_globals):
    observed = {}
    monkeypatch.setattr(monitor, "EXPORTED_SECRET_KEYS", frozenset())
    for secret in monitor.SECRET_KEYS:
        monkeypatch.delenv(secret, raising=False)

    answers = [
        str(STEAM64), "y", "5m", "45s",
        "y", "smtp.example.test", "587", "y", "user@example.test", "user@example.test", "rcpt@example.test", "1",
        "y", "1", "1",
        "y", "", "",
        "1", "y", "n",
    ]
    assert run_wizard_with_doctor(tmp_path, monkeypatch, answers, [API_KEY, "smtp-password", WEBHOOK_URL], observed) == 0

    assert observed["values"] == {"STEAM_API_KEY": API_KEY, "SMTP_PASSWORD": "smtp-password", "WEBHOOK_URL": WEBHOOK_URL}
    from_file, from_environment, from_settings, _ = observed["sources"]
    assert sorted(from_file) == ["SMTP_PASSWORD", "STEAM_API_KEY", "WEBHOOK_URL"]
    assert not from_environment and not from_settings


# Verifies a secret exported before startup still wins over the value setup wrote, as it will when monitoring runs
def test_an_exported_secret_still_wins_after_setup(tmp_path, monkeypatch, wizard_globals):
    observed = {}
    monkeypatch.setattr(monitor, "EXPORTED_SECRET_KEYS", frozenset({"STEAM_API_KEY"}))
    monkeypatch.setenv("STEAM_API_KEY", "E" * 32)

    answers = [str(STEAM64), "y", "5m", "45s", "n", "n", "y", "", "", "1", "y", "n"]
    assert run_wizard_with_doctor(tmp_path, monkeypatch, answers, [API_KEY], observed) == 0

    assert observed["values"]["STEAM_API_KEY"] == "E" * 32
    assert monitor.doctor_secret_sources(str(tmp_path / ".env"))[1] == ["STEAM_API_KEY"]


# Verifies hidden prompts are colorized like the visible ones, so one question does not look different
def test_hidden_prompts_are_colorized_like_the_visible_ones(monkeypatch):
    monkeypatch.setattr(monitor, "COLOR_ENABLED", True)
    monkeypatch.setattr(monitor, "_COLOR_STYLES", {name: monitor._build_ansi_sequence(value) for name, value in monitor.DEFAULT_COLOR_THEME.items() if monitor._build_ansi_sequence(value)})
    prompts = []

    monitor._wizard_ask_secret("SMTP password", getpass_func=lambda prompt: prompts.append(prompt) or "secret")
    visible = monitor._wizard_input("Receiver email: ", input_func=lambda prompt: prompts.append(prompt) or "")

    assert visible == ""
    hidden_prompt, visible_prompt = prompts
    assert hidden_prompt == monitor.colorize("info", "SMTP password: ")
    assert hidden_prompt.startswith(visible_prompt[:visible_prompt.index("R")])
    assert hidden_prompt.endswith(monitor.ANSI_RESET)


# Verifies the persist answer puts the target in the config file, so the tool runs without arguments
def test_a_persisted_target_reaches_the_config_file(tmp_path, monkeypatch, wizard_globals):
    assert run_wizard(tmp_path, monkeypatch, minimal_answers()) == 0

    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    assert values["TARGET_STEAM_ID"] == str(STEAM64)


# Verifies declining the persist question leaves the target out of the written config
def test_a_declined_persist_leaves_the_target_out_of_the_config(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = [str(STEAM64), "n", "5m", "45s", "n", "n", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers) == 0

    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    assert values["TARGET_STEAM_ID"] == ""
    # Without a persisted target the printed commands have to carry it
    assert str(STEAM64) in capsys.readouterr().out


# Verifies the persist question is asked with the wording the sibling monitors use
def test_the_target_section_asks_whether_to_persist(tmp_path, monkeypatch, wizard_globals):
    transcript = []

    run_wizard(tmp_path, monkeypatch, minimal_answers(), transcript=transcript)

    assert any(prompt.startswith("Persist this target in the generated config? [Y/n]") for prompt in transcript)


# Verifies duration prompts name the accepted units and show the stored seconds beside a readable form
def test_duration_prompts_show_the_units_and_the_stored_seconds(tmp_path, monkeypatch, wizard_globals):
    transcript = []

    run_wizard(tmp_path, monkeypatch, minimal_answers(), transcript=transcript)

    polling = [prompt for prompt in transcript if "polling interval" in prompt]
    assert len(polling) == 2
    for prompt in polling:
        assert "(seconds or use s/m/h/d)" in prompt
    assert "[120s - 2m]" in polling[0]
    assert "[60s - 1m]" in polling[1]


# Verifies a wizard duration is rendered as raw seconds plus a readable form, the way the siblings render it
@pytest.mark.parametrize("seconds,expected", [
    (60, "60s - 1m"), (120, "120s - 2m"), (3600, "3600s - 1h"), (5400, "5400s - 1h 30m"), (86400, "86400s - 1d"),
])
def test_wizard_durations_show_seconds_and_a_readable_form(seconds, expected):
    assert monitor._wizard_format_duration(seconds) == expected


# Verifies prompts go through the shared colorized reader rather than a bare input call
@pytest.mark.parametrize("ask,arguments", [
    (lambda: monitor._wizard_ask_text("Question"), ()),
    (lambda: monitor._wizard_ask_yes_no("Question?"), ()),
    (lambda: monitor._wizard_ask_duration("Question", 60), ()),
])
def test_wizard_prompts_are_colorized(monkeypatch, ask, arguments):
    parts = []
    monkeypatch.setattr(monitor, "colorize", lambda part, text: parts.append(part) or f"<{part}>{text}")
    monkeypatch.setattr("builtins.input", lambda _prompt: "")

    ask()

    assert "info" in parts


# Verifies a non-interactive run explains itself and names the alternative instead of hanging
def test_a_non_interactive_run_names_the_alternative(capsys):
    code = monitor.run_setup_wizard(interactive=False)

    output = capsys.readouterr().out
    assert code == 1
    assert "needs an interactive terminal" in output
    assert "--generate-config" in output
    assert monitor.QUICK_START_GUIDE_URL in output


# Verifies an interrupt during questioning leaves the destination files untouched
def test_an_interrupt_writes_nothing(tmp_path, monkeypatch, wizard_globals, capsys):
    monkeypatch.setattr(monitor, "validate_steam_api_key", lambda _key, timeout=10: True)

    def interrupt(_prompt):
        raise KeyboardInterrupt

    code = monitor.run_setup_wizard(
        config_file=str(tmp_path / "steam_monitor.conf"),
        env_file=str(tmp_path / ".env"),
        input_func=interrupt,
        getpass_func=lambda _prompt: API_KEY,
        interactive=True,
    )

    assert code == 1
    assert not (tmp_path / "steam_monitor.conf").exists()
    assert "Destination files were not changed." in capsys.readouterr().out


# Verifies the welcome screen offers the commands a newcomer needs next, in the order the siblings print them
def test_the_welcome_screen_offers_the_shared_commands(capsys):
    monitor.print_welcome_screen(interactive=False)

    output = capsys.readouterr().out
    labels = ("Quickest start (already configured):", "Easiest start (guided setup wizard):", "Check setup before monitoring:", "Show profile details and exit:", "Full options:")
    positions = [output.find(label) for label in labels]

    assert -1 not in positions
    assert positions == sorted(positions)
    assert monitor.QUICK_START_GUIDE_URL in output


# Verifies the welcome commands are written for this install and leave placeholders readable
def test_the_welcome_commands_suit_the_install(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    monkeypatch.delenv(monitor.INSTALL_METHOD_ENV_VAR, raising=False)

    monitor.print_welcome_screen(interactive=False)

    output = capsys.readouterr().out
    assert "steam_monitor <steam_target>" in output
    assert "'<steam_target>'" not in output


# Verifies the wizard is not offered when there is no terminal to answer on, where the bare run stays a usage error
def test_the_welcome_screen_does_not_offer_the_wizard_without_a_terminal(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **_kwargs: pytest.fail("the wizard ran without a terminal"))

    assert monitor.print_welcome_screen(interactive=False) == 1
    assert "Run the guided setup wizard now?" not in capsys.readouterr().out


# Verifies answering no to the welcome offer exits cleanly rather than starting anything
def test_declining_the_welcome_offer_exits_cleanly(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **_kwargs: pytest.fail("the wizard ran after being declined"))

    assert monitor.print_welcome_screen(input_func=lambda _prompt: "n", interactive=True) == 0
    capsys.readouterr()


# Returns the transcript of running the real CLI with no arguments in a pseudo-terminal
def capture_welcome_pty():
    controller, worker = pty.openpty()
    process = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "steam_monitor.py")],
        stdin=worker, stdout=worker, stderr=worker, cwd=str(REPO_ROOT),
        env={**os.environ, "TERM": "xterm", "NO_COLOR": "1"},
    )
    os.close(worker)
    chunks = []
    try:
        # The welcome screen ends by asking a question, so the answer has to be supplied
        os.write(controller, b"n\n")
        while True:
            ready, _, _ = select.select([controller], [], [], 30)
            if not ready:
                break
            try:
                data = os.read(controller, 65536)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
    finally:
        os.close(controller)
        process.wait(timeout=30)
    return b"".join(chunks).decode("utf-8", errors="replace"), process.returncode


@pytest.mark.skipif(sys.platform == "win32", reason="pty is not available on Windows")
# Verifies the zero-argument screen holds the layout contract on the path a newcomer actually walks
def test_the_welcome_transcript_holds_the_output_contract():
    raw, exit_code = capture_welcome_pty()
    text = re.sub(r"\x1B\[[0-9;]*[A-Za-z]", "", raw)
    lines = [line[:-1] if line.endswith("\r") else line for line in text.split("\n")]

    assert "usage:" not in text, "the argparse usage error still reaches a newcomer"
    assert monitor.QUICK_START_GUIDE_URL in text
    assert "Run the guided setup wizard now?" in text

    doubles = [index for index in range(len(lines) - 1) if not lines[index].strip() and not lines[index + 1].strip()]
    assert not doubles, f"double blank lines at {doubles}:\n{text}"
    assert exit_code == 0


# Returns the transcript of driving the real wizard through a pseudo-terminal with scripted answers
def capture_wizard_pty(tmp_path, script):
    controller, worker = pty.openpty()
    process = subprocess.Popen(
        [sys.executable, str(REPO_ROOT / "steam_monitor.py"), "--setup",
         "--config-file", str(tmp_path / "w.conf"), "--env-file", str(tmp_path / ".env")],
        stdin=worker, stdout=worker, stderr=worker, cwd=str(REPO_ROOT),
        # A key already in the environment means the wizard asks to replace it rather than opening a hidden
        # prompt, which getpass reads from /dev/tty and a scripted pty therefore cannot answer
        env={**os.environ, "TERM": "xterm", "NO_COLOR": "1", "STEAM_API_KEY": API_KEY},
    )
    os.close(worker)
    chunks = []
    try:
        os.write(controller, script)
        while True:
            ready, _, _ = select.select([controller], [], [], 30)
            if not ready:
                break
            try:
                data = os.read(controller, 65536)
            except OSError:
                break
            if not data:
                break
            chunks.append(data)
    finally:
        os.close(controller)
        process.wait(timeout=30)
    return b"".join(chunks).decode("utf-8", errors="replace")


@pytest.mark.skipif(sys.platform == "win32", reason="pty is not available on Windows")
# Verifies the wizard layout holds on the path a user walks, which is the seam unit tests cannot see
def test_the_wizard_transcript_holds_the_output_contract(tmp_path):
    # Target, persist it, both intervals, keep the existing key, no email, no webhook,
    # save, decline doctor, which also removes the launch offer
    raw = capture_wizard_pty(tmp_path, b"76561197960435530\ny\n5m\n45s\nn\nn\nn\ny\n\nlast_status.json\n1\nn\n")
    text = re.sub(r"\x1B\[[0-9;]*[A-Za-z]", "", raw)
    # The transcript ends with the blank line that closes the Next steps block, so only the body is checked
    lines = [line[:-1] if line.endswith("\r") else line for line in text.rstrip("\r\n").split("\n")]

    heading_index = next(index for index, line in enumerate(lines) if line.strip() == "Setup Wizard")

    # The heading follows the banner's own blank line rather than carrying a second one
    assert lines[heading_index - 1].strip() == ""
    assert lines[heading_index - 2].strip() != ""

    # The paragraphs and the destinations block appear in the agreed order
    order = [
        "This asks a few questions and writes a ready-to-run configuration.",
        "Press Enter to accept the shown default. Ctrl+C cancels.",
        "Secrets go to the dotenv file. Non-secret settings go to the config file.",
        "Detected install method:",
        "Configuration:",
        "Dotenv:",
        "Steam profile URL or ID to monitor",
        "Write the normal per-target log file?",
        "Optional CSV output path (blank disables it)",
        "Optional status file path (blank uses the default name in the working directory)",
        "Setup summary",
        "Saved files",
        "Next steps",
    ]
    positions = [text.index(fragment) for fragment in order]
    assert positions == sorted(positions), order

    doubles = [index for index in range(len(lines) - 1) if not lines[index].strip() and not lines[index + 1].strip()]
    assert not doubles, f"double blank lines at {doubles}:\n{text}"

    assert (tmp_path / "w.conf").exists()


# Verifies the output section records the log choice and the CSV destination it was given
def test_the_output_section_records_the_log_and_csv_choices(tmp_path, wizard_globals):
    baseline = {name: value for name, value in vars(monitor).items() if name in monitor._config_allowed_names()}
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", baseline)

    monitor._wizard_collect_output_section(state, input_func=scripted_input(["n", str(tmp_path / "activity.csv"), ""]))

    assert state.config_values["DISABLE_LOGGING"] is True
    assert state.config_values["CSV_FILE"] == str(tmp_path / "activity.csv")
    assert state.config_values["STEAM_STATUS_FILE"] == ""


# Verifies the status file answer is kept, so a restart resumes from the file the user chose
def test_the_output_section_records_the_status_file_choice(tmp_path, wizard_globals):
    baseline = {name: value for name, value in vars(monitor).items() if name in monitor._config_allowed_names()}
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", baseline)

    monitor._wizard_collect_output_section(state, input_func=scripted_input(["y", "", str(tmp_path / "last_status.json")]))

    assert state.config_values["STEAM_STATUS_FILE"] == str(tmp_path / "last_status.json")


# Verifies a blank CSV answer disables CSV output rather than storing an empty path as a file name
def test_a_blank_csv_answer_disables_csv_output(tmp_path, wizard_globals):
    baseline = {name: value for name, value in vars(monitor).items() if name in monitor._config_allowed_names()}
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", baseline)

    monitor._wizard_collect_output_section(state, input_func=scripted_input(["y", "", ""]))

    assert state.config_values["DISABLE_LOGGING"] is False
    assert state.config_values["CSV_FILE"] == ""


# Verifies a CSV answer without an extension is saved as a .csv file while an explicit extension is left alone
def test_the_csv_answer_gains_a_csv_extension_when_it_has_none(tmp_path, wizard_globals):
    baseline = {name: value for name, value in vars(monitor).items() if name in monitor._config_allowed_names()}
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", baseline)

    monitor._wizard_collect_output_section(state, input_func=scripted_input(["y", str(tmp_path / "activity"), ""]))
    assert state.config_values["CSV_FILE"] == str(tmp_path / "activity.csv")

    monitor._wizard_collect_output_section(state, input_func=scripted_input(["y", str(tmp_path / "activity.txt"), ""]))
    assert state.config_values["CSV_FILE"] == str(tmp_path / "activity.txt")


# Verifies a status file answer without an extension is saved as a .json file while an explicit extension is left alone
def test_the_status_file_answer_gains_a_json_extension_when_it_has_none(tmp_path, wizard_globals):
    baseline = {name: value for name, value in vars(monitor).items() if name in monitor._config_allowed_names()}
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", baseline)

    monitor._wizard_collect_output_section(state, input_func=scripted_input(["y", "", str(tmp_path / "profile")]))
    assert state.config_values["STEAM_STATUS_FILE"] == str(tmp_path / "profile.json")

    monitor._wizard_collect_output_section(state, input_func=scripted_input(["y", "", str(tmp_path / "profile.txt")]))
    assert state.config_values["STEAM_STATUS_FILE"] == str(tmp_path / "profile.txt")


# Verifies a declined email section clears the mail server, so the written config cannot contradict the summary
def test_a_declined_email_section_clears_the_mail_server(tmp_path, wizard_globals):
    baseline = {name: value for name, value in vars(monitor).items() if name in monitor._config_allowed_names()}
    baseline.update({"SMTP_HOST": "smtp.example.com", "SMTP_USER": "monitor", "SENDER_EMAIL": "sender@example.com", "RECEIVER_EMAIL": "receiver@example.com"})
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", baseline)
    state.secret_updates["SMTP_PASSWORD"] = "private-password"

    monitor._wizard_collect_email_section(state, input_func=scripted_input(["n"]))

    assert not any(monitor.doctor_value_is_set(state.config_values[name]) for name in ("SMTP_HOST", "SMTP_USER", "SENDER_EMAIL", "RECEIVER_EMAIL"))
    assert "SMTP_PASSWORD" not in state.secret_updates
    assert "smtp.example.com" not in monitor.generate_config_with_current_values(state.config_values)


# The mail server answers the wizard asks for before the hidden password prompt
EMAIL_ANSWERS = ["smtp.example.com", "587", "y", "monitor", "sender@example.com", "receiver@example.com"]


# Verifies the wizard signs in with exactly the answers just given, so a wrong password is caught during setup
def test_the_wizard_signs_in_with_the_collected_mail_server(tmp_path, monkeypatch, wizard_globals, capsys):
    attempts = []
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: attempts.append((values, password)) or None)
    answers = [str(STEAM64), "y", "5m", "45s", "y"] + EMAIL_ANSWERS + ["1", "n", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "smtp-password"]) == 0

    assert len(attempts) == 1
    values, password = attempts[0]
    assert values == {"SMTP_HOST": "smtp.example.com", "SMTP_PORT": 587, "SMTP_SSL": True, "SMTP_USER": "monitor", "SENDER_EMAIL": "sender@example.com", "RECEIVER_EMAIL": "receiver@example.com"}
    assert password == "smtp-password"
    assert "The mail server accepted the sign-in. No email was sent." in capsys.readouterr().out


# Verifies a refused sign-in offers the mail server questions again rather than saving settings that cannot work
def test_a_refused_mail_server_sign_in_offers_another_attempt(tmp_path, monkeypatch, wizard_globals, capsys):
    advice = monitor.make_recovery_advice("smtp.authentication", "The mail server rejected the sign-in", "Use an app password", False, "535 authentication failed")
    results = [advice, None]
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: results.pop(0))
    transcript = []
    answers = [str(STEAM64), "y", "5m", "45s", "y"] + EMAIL_ANSWERS + ["y"] + EMAIL_ANSWERS + ["1", "n", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "wrong", "right"], transcript=transcript) == 0

    output = capsys.readouterr().out
    assert "The mail server rejected the sign-in: 535 authentication failed" in output
    assert "To fix: Use an app password" in output
    assert any("Try entering the mail server settings again?" in prompt for prompt in transcript)
    assert not results


# Verifies declining the retry keeps the answers, since being offline is the usual reason a correct setup fails here
def test_declining_the_sign_in_retry_keeps_the_mail_server_settings(tmp_path, monkeypatch, wizard_globals, capsys):
    advice = monitor.make_recovery_advice("smtp.connection", "The SMTP server could not be reached", "Check SMTP_HOST", True)
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: advice)
    answers = [str(STEAM64), "y", "5m", "45s", "y"] + EMAIL_ANSWERS + ["n", "1", "n", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "smtp-password"]) == 0

    assert "The settings were kept without being checked. Run --doctor to check the sign-in again." in capsys.readouterr().out
    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    assert values["SMTP_HOST"] == "smtp.example.com"
    assert values["SMTP_USER"] == "monitor"


# Verifies giving up on a refused sign-in switches every email alert off rather than saving settings that cannot work
def test_abandoning_a_refused_sign_in_switches_email_off(tmp_path, monkeypatch, wizard_globals, capsys):
    advice = monitor.make_recovery_advice("smtp.authentication", "The mail server rejected the sign-in", "Use an app password", False, "535 authentication failed")
    monkeypatch.setattr(monitor, "_wizard_verify_smtp", lambda values, password: advice)
    answers = [str(STEAM64), "y", "5m", "45s", "y"] + EMAIL_ANSWERS + ["n", "n", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "wrong"]) == 0

    assert "Email notifications stay off until the mail server accepts the settings." in capsys.readouterr().out
    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    assert all(values[name] is False for name in monitor.WIZARD_EMAIL_NOTIFICATION_KEYS)


# Verifies Ctrl+C at the welcome offer reports one line instead of a traceback
def test_interrupting_the_welcome_offer_reports_a_cancellation(monkeypatch, capsys):
    def interrupt(_prompt):
        raise KeyboardInterrupt

    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **_kwargs: pytest.fail("the wizard ran after being interrupted"))

    assert monitor.print_welcome_screen(input_func=interrupt, interactive=True) == 1
    assert "Setup cancelled." in capsys.readouterr().out


# Returns an input function that answers the script and then interrupts the next prompt, as Ctrl+C does
def answers_then_interrupt(answers):
    remaining = list(answers)

    def respond(_prompt):
        if not remaining:
            raise KeyboardInterrupt
        return remaining.pop(0)

    return respond


# Verifies an interrupt before the save says the destination files are untouched
def test_interrupting_the_questions_reports_untouched_files(tmp_path, monkeypatch, wizard_globals, capsys):
    code = run_wizard(tmp_path, monkeypatch, [], input_func=answers_then_interrupt([]))

    assert code == 1
    assert "Setup cancelled. Destination files were not changed." in capsys.readouterr().out
    assert not (tmp_path / "steam_monitor.conf").exists()


# Verifies an interrupt at the doctor offer reports the saved setup instead of a cancellation
def test_interrupting_the_doctor_offer_keeps_the_saved_setup(tmp_path, monkeypatch, wizard_globals, capsys):
    code = run_wizard(tmp_path, monkeypatch, [], input_func=answers_then_interrupt(minimal_answers()[:-2]))

    output = capsys.readouterr().out
    assert code == 0
    assert "Setup is saved. Use the commands below when ready." in output
    assert "Setup cancelled" not in output
    assert "Next steps" in output
    assert (tmp_path / "steam_monitor.conf").is_file()


# Verifies an interrupt at the launch offer reports the saved setup and points at the printed command
def test_interrupting_the_launch_offer_keeps_the_saved_setup(tmp_path, monkeypatch, wizard_globals, capsys):
    code = run_wizard(tmp_path, monkeypatch, [], input_func=answers_then_interrupt(minimal_answers()[:-2] + ["y"]))

    output = capsys.readouterr().out
    assert code == 0
    assert "Setup is saved. Start monitoring with the command above when ready." in output
    assert "Setup cancelled" not in output
    assert (tmp_path / "steam_monitor.conf").is_file()


# Verifies a prompt runs with Python's default Ctrl+C behavior, so the signal handler cannot pre-empt it
def test_prompts_restore_the_default_interrupt_handler():
    observed = {}

    def answer(_prompt):
        observed["during"] = signal.getsignal(signal.SIGINT)
        return "value"

    previous_handler = signal.signal(signal.SIGINT, monitor.signal_handler)
    try:
        assert monitor._wizard_input("Prompt: ", input_func=answer) == "value"
        assert observed["during"] is signal.default_int_handler
        assert signal.getsignal(signal.SIGINT) is monitor.signal_handler
    finally:
        signal.signal(signal.SIGINT, previous_handler)


# Verifies a destination that cannot be written is refused before the first question is asked
def test_an_unwritable_destination_is_refused_before_any_question(tmp_path, capsys):
    def refuse_every_question(prompt=""):
        raise AssertionError(f"Setup asked a question before checking its destinations: {prompt!r}")

    code = monitor.run_setup_wizard(config_file="/steam_monitor_unwritable_root.conf", env_file=str(tmp_path / ".env"), input_func=refuse_every_question, interactive=True)

    out = capsys.readouterr().out
    assert code == 1
    assert "Configuration destination is not writable" in out
    assert "To fix:" in out


# Verifies a directory given as a destination is refused rather than failing at the save step
def test_a_directory_destination_is_refused(tmp_path, capsys):
    code = monitor.run_setup_wizard(config_file=str(tmp_path), env_file=str(tmp_path / ".env"), interactive=True)

    out = capsys.readouterr().out
    assert code == 1
    assert "must be a file path, not a directory" in out


# Verifies the disabled config setting is refused, since setup exists to write one
def test_a_disabled_config_destination_is_refused(tmp_path, capsys):
    code = monitor.run_setup_wizard(config_file="none", env_file=str(tmp_path / ".env"), interactive=True)

    out = capsys.readouterr().out
    assert code == 1
    assert "--setup requires a config destination" in out


# Verifies an existing config can be kept by sending the run to another path instead
def test_an_existing_config_can_be_redirected_to_another_path(tmp_path, monkeypatch, wizard_globals):
    config = tmp_path / "steam_monitor.conf"
    config.write_text("CLEAR_SCREEN = False\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere.conf"

    code = run_wizard(tmp_path, monkeypatch, ["n", str(elsewhere), *minimal_answers()])

    assert code == 0
    assert config.read_text(encoding="utf-8") == "CLEAR_SCREEN = False\n"
    assert monitor.parse_config_content(elsewhere.read_text(encoding="utf-8"), str(elsewhere))["TARGET_STEAM_ID"] == str(STEAM64)


# Verifies declining to replace an existing config and naming no alternative ends the run without writing
def test_declining_an_existing_config_without_an_alternative_writes_nothing(tmp_path, monkeypatch, wizard_globals, capsys):
    config = tmp_path / "steam_monitor.conf"
    config.write_text("CLEAR_SCREEN = False\n", encoding="utf-8")

    code = run_wizard(tmp_path, monkeypatch, ["n", ""])

    out = capsys.readouterr().out
    assert code == 1
    assert config.read_text(encoding="utf-8") == "CLEAR_SCREEN = False\n"
    assert not (tmp_path / ".env").exists()
    assert "Setup cancelled. Destination files were not changed." in out


# Returns the answers for one email run with the extra answer the dotenv replace prompt needs
def email_answers_with_smtp_replace(replace):
    return [str(STEAM64), "y", "5m", "45s", "y", *EMAIL_ANSWERS, replace, "1", "n", "y", "", "", "1", "n", "n"]


# Verifies a secret already in the dotenv file is kept when the replacement is declined
def test_an_existing_dotenv_secret_is_kept_unless_the_replacement_is_confirmed(tmp_path, monkeypatch, wizard_globals):
    env_file = tmp_path / ".env"
    env_file.write_text('SMTP_PASSWORD="original"\n', encoding="utf-8")

    code = run_wizard(tmp_path, monkeypatch, email_answers_with_smtp_replace("n"), secrets=[API_KEY, "typed-password"])

    written = env_file.read_text(encoding="utf-8")
    assert code == 0
    assert 'SMTP_PASSWORD="original"' in written
    assert "typed-password" not in written


# Verifies a confirmed replacement does reach the dotenv file
def test_a_confirmed_dotenv_secret_replacement_is_written(tmp_path, monkeypatch, wizard_globals):
    env_file = tmp_path / ".env"
    env_file.write_text('SMTP_PASSWORD="original"\n', encoding="utf-8")

    code = run_wizard(tmp_path, monkeypatch, email_answers_with_smtp_replace("y"), secrets=[API_KEY, "typed-password"])

    assert code == 0
    assert 'SMTP_PASSWORD="typed-password"' in env_file.read_text(encoding="utf-8")


# Verifies debug output is off while a hidden wizard answer is read and restored afterwards
def test_a_hidden_wizard_answer_is_read_with_debug_output_off(monkeypatch):
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    seen = []

    answer = monitor._wizard_ask_secret("SMTP password", getpass_func=lambda prompt: seen.append(monitor.DEBUG_MODE) or "secret")

    assert answer == "secret"
    assert seen == [False]
    assert monitor.DEBUG_MODE is True


# Verifies a target that already is a Steam64 ID is not echoed back, since only a value the wizard changed is news
def test_the_canonical_target_is_not_echoed_back(tmp_path, monkeypatch, wizard_globals, capsys):
    assert run_wizard(tmp_path, monkeypatch, minimal_answers()) == 0

    assert "Using Steam64 ID" not in capsys.readouterr().out


# Verifies the screen closes with one blank line, the way it does in every sibling
def test_the_welcome_screen_closes_with_a_blank_line(capsys):
    monitor.print_welcome_screen(interactive=False)

    assert capsys.readouterr().out.endswith(f"{monitor.QUICK_START_GUIDE_URL}\n\n")


# Verifies the guide link opens the setup page the sibling monitors link, with no section fragment
def test_the_welcome_guide_link_opens_the_shared_setup_page():
    assert monitor.QUICK_START_GUIDE_URL.endswith("/setup-and-first-run/")


# Verifies setup keeps a copy of the replaced configuration but never of the replaced secrets
def test_setup_backs_up_the_config_but_not_the_dotenv(tmp_path, monkeypatch, capsys, wizard_globals):
    (tmp_path / "steam_monitor.conf").write_text("STEAM_CHECK_INTERVAL = 60\n", encoding="utf-8")
    (tmp_path / ".env").write_text("SMTP_PASSWORD=old-password\n", encoding="utf-8")

    assert run_wizard(tmp_path, monkeypatch, ["y", *minimal_answers()]) == 0

    lines = capsys.readouterr().out.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip() == "Saved files")
    block = list(itertools.takewhile(lambda line: line.startswith("  ") or not line.strip(), lines[start + 1:]))
    # Matched on the label alone, since the temporary directory name can carry the word too
    labels = [line.split(":", 1)[0].strip() for line in block if ":" in line]

    assert [label for label in labels if label.casefold().endswith("backup")] == ["Backup"], block
    assert sorted(entry.name for entry in tmp_path.iterdir() if entry.name.startswith(".env")) == [".env"]


# Verifies the wizard says it is contacting Steam, since the key check blocks the prompt with no output
def test_the_wizard_announces_the_key_check(tmp_path, capsys, wizard_globals):
    baseline = {name: value for name, value in vars(monitor).items() if name in monitor._config_allowed_names()}
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", baseline)

    monitor._wizard_collect_auth_section(state, getpass_func=lambda _prompt: API_KEY, validator=lambda _key: True)

    lines = capsys.readouterr().out.splitlines()
    assert lines.index("  Checking the key with Steam ...") < lines.index("  Steam accepted the key.")


# Verifies the review can move the configuration file, since the summary shows a destination it could not change
def test_the_destination_section_moves_the_configuration_file(tmp_path):
    moved = tmp_path / "elsewhere"
    moved.mkdir()
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", dict(vars(monitor)))

    monitor._wizard_collect_destination_section(state, input_func=scripted_input([str(moved / "steam_monitor.conf"), ""]))

    assert state.config_path == moved / "steam_monitor.conf"
    assert state.env_path == tmp_path / ".env"
    assert state.config_values["DOTENV_FILE"] == str(tmp_path / ".env")


# Verifies moving the dotenv re-asks every section holding a secret, since a kept secret was never queued
def test_moving_the_dotenv_destination_re_asks_the_secret_sections(tmp_path, monkeypatch, capsys):
    asked = []
    for name in ("_wizard_collect_auth_section", "_wizard_collect_email_section", "_wizard_collect_webhook_section"):
        monkeypatch.setattr(monitor, name, lambda state, section=name, **kwargs: asked.append(section))
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", dict(vars(monitor)))

    monitor._wizard_collect_destination_section(state, input_func=scripted_input(["", str(tmp_path / ".env-moved")]))

    assert state.env_path == tmp_path / ".env-moved"
    assert state.config_values["DOTENV_FILE"] == str(tmp_path / ".env-moved")
    assert asked == ["_wizard_collect_auth_section", "_wizard_collect_email_section", "_wizard_collect_webhook_section"]
    assert "The dotenv destination changed" in capsys.readouterr().out


# Verifies one file cannot hold both, since saving the configuration would overwrite the secrets beside it
def test_the_dotenv_destination_cannot_be_the_configuration_file(tmp_path, capsys):
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", dict(vars(monitor)))

    monitor._wizard_collect_destination_section(state, input_func=scripted_input(["", str(tmp_path / "steam_monitor.conf"), ""]))

    assert state.env_path == tmp_path / ".env"
    assert "has to be a different file" in capsys.readouterr().out


# Verifies the port question rejects a number no TCP port can be, instead of saving it for the doctor to reject
def test_the_smtp_port_question_rejects_a_number_above_the_port_range(capsys):
    answers = iter(["70000", "2525"])

    chosen = monitor._wizard_ask_positive_int("SMTP port", 587, maximum=65535, input_func=lambda _prompt: next(answers))

    assert chosen == 2525
    assert "  Enter a whole number from 1 through 65535." in capsys.readouterr().out


# Verifies declining the retry offer keeps the saved value rather than asking the same question forever
def test_declining_the_retry_offer_keeps_the_saved_number(capsys):
    answers = iter(["", "n"])

    assert monitor._wizard_ask_positive_int("SMTP port", 587, maximum=65535, input_func=lambda _prompt: next(answers)) == 587


# Verifies a rerun that keeps the loaded secrets leaves every one of them out of the rebuilt configuration file
def test_a_rerun_keeps_loaded_secrets_out_of_the_configuration(tmp_path, monkeypatch, wizard_globals):
    loaded = {"STEAM_API_KEY": "B" * 32, "SMTP_PASSWORD": "mail-secret-value", "WEBHOOK_URL": WEBHOOK_URL, "NTFY_ACCESS_TOKEN": "ntfy-secret-value"}
    for name, value in loaded.items():
        monkeypatch.setattr(monitor, name, value)
    (tmp_path / "steam_monitor.conf").write_text("# earlier config\n", encoding="utf-8")
    # rebuild, target, persist, polling, keep the loaded key, no email, no webhook, output files, save, decline doctor and monitoring
    answers = ["y", str(STEAM64), "y", "5m", "45s", "n", "n", "n", "y", "", "", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=[]) == 0

    written = (tmp_path / "steam_monitor.conf").read_text(encoding="utf-8")
    for value in loaded.values():
        assert value not in written
    assert "your_steam_web_api_key" in written


# Verifies the configuration renderer keeps the template placeholder for every secret whatever the values hold
def test_the_configuration_renderer_never_writes_a_secret():
    values = {name: f"real-{name.lower()}" for name in monitor.SECRET_KEYS}
    values["STEAM_CHECK_INTERVAL"] = 4321

    rendered = monitor.generate_config_with_current_values(values)

    assert "STEAM_CHECK_INTERVAL = 4321" in rendered
    assert not any(value in rendered for value in values.values() if isinstance(value, str))


# Verifies a blank target answer whose retry is declined ends the section instead of asking the same question forever
def test_declining_the_target_retry_ends_the_section_without_a_target(tmp_path, capsys):
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", {})
    transcript = []

    monitor._wizard_collect_target_section(state, input_func=scripted_input(["", "n"], transcript))

    assert state.target == ""
    assert state.config_values["TARGET_STEAM_ID"] == ""
    assert not any(prompt.startswith("Persist this target") for prompt in transcript)
    assert "No target selected. Nothing can be monitored until one is set." in capsys.readouterr().out


# Verifies a rejected target answer offers another attempt and declining it keeps the target already given
def test_a_rejected_target_answer_offers_a_retry_and_keeps_the_previous_target(tmp_path):
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", {})
    state.target = str(STEAM64)
    transcript = []

    monitor._wizard_collect_target_section(state, input_func=scripted_input(["someone@example.com", "n", "y"], transcript))

    assert state.target == str(STEAM64)
    assert any(prompt.startswith("Try entering the Steam profile URL or ID to monitor again?") for prompt in transcript)
    assert any(prompt.startswith("Persist this target") for prompt in transcript)


# Verifies declining email clears only the alerts the wizard offers, so alerts enabled by hand survive
def test_declining_email_keeps_the_alerts_the_wizard_never_offers(tmp_path, wizard_globals):
    baseline = {name: value for name, value in vars(monitor).items() if name in monitor._config_allowed_names()}
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", baseline)
    for key in ("STEAM_LEVEL_XP_NOTIFICATION", "FRIENDS_NOTIFICATION", "GAMES_LIBRARY_NOTIFICATION", "ACTIVE_INACTIVE_NOTIFICATION", "GAME_CHANGE_NOTIFICATION"):
        state.config_values[key] = True

    monitor._wizard_disable_email(state)

    for key in ("STEAM_LEVEL_XP_NOTIFICATION", "FRIENDS_NOTIFICATION", "GAMES_LIBRARY_NOTIFICATION"):
        assert state.config_values[key] is True
    for key in monitor.WIZARD_EMAIL_NOTIFICATION_KEYS:
        assert state.config_values[key] is False


# Verifies the launch offer only follows a doctor run that passed, so a declined doctor ends at the printed commands
def test_declining_the_doctor_removes_the_launch_offer(tmp_path, monkeypatch, wizard_globals):
    transcript = []
    launched = []
    monkeypatch.setattr(monitor, "_wizard_launch_monitor", lambda arguments: launched.append(arguments) or 0)

    code = run_wizard(tmp_path, monkeypatch, minimal_answers()[:-2] + ["n", "y"], transcript=transcript)

    assert code == 0
    assert launched == []
    assert not any("Start monitoring now?" in prompt for prompt in transcript)


# Verifies a doctor run that passed is what unlocks the launch offer
def test_a_passed_doctor_run_unlocks_the_launch_offer(tmp_path, monkeypatch, wizard_globals):
    transcript = []
    launched = []
    monkeypatch.setattr(monitor, "_wizard_launch_monitor", lambda arguments: launched.append(arguments) or 0)

    code = run_wizard(tmp_path, monkeypatch, minimal_answers()[:-2] + ["y", "y"], transcript=transcript)

    assert code == 0
    assert len(launched) == 1
    assert any("Start monitoring now?" in prompt for prompt in transcript)


# Verifies a doctor run that failed keeps the launch offer away and labels the command to run after the fix
def test_a_failed_doctor_run_removes_the_launch_offer(tmp_path, monkeypatch, wizard_globals, capsys):
    transcript = []
    launched = []
    monkeypatch.setattr(monitor, "validate_steam_api_key", lambda _key, timeout=10: True)
    monkeypatch.setattr(monitor, "run_doctor", lambda **_kwargs: 1)
    monkeypatch.setattr(monitor, "_wizard_launch_monitor", lambda arguments: launched.append(arguments) or 0)

    code = monitor.run_setup_wizard(config_file=str(tmp_path / "steam_monitor.conf"), env_file=str(tmp_path / ".env"), input_func=scripted_input(minimal_answers()[:-2] + ["y", "y"], transcript), getpass_func=lambda prompt: API_KEY, interactive=True)

    assert code == 0
    assert launched == []
    assert not any("Start monitoring now?" in prompt for prompt in transcript)
    assert "After Doctor passes, start monitoring:" in capsys.readouterr().out


# Verifies the webhook question defaults to the saved switch, so a rerun over a configured webhook proposes keeping it
def test_the_webhook_question_defaults_to_the_saved_switch(tmp_path, monkeypatch, wizard_globals):
    baseline = {name: value for name, value in vars(monitor).items() if name in monitor._config_allowed_names()}
    state = monitor.WizardSetupState(tmp_path / "steam_monitor.conf", tmp_path / ".env", baseline)
    state.config_values["WEBHOOK_ENABLED"] = True
    seen = []
    monkeypatch.setattr(monitor, "_wizard_ask_yes_no", lambda question, default=False, **kwargs: seen.append((question, default)) or False)

    monitor._wizard_collect_webhook_section(state)

    assert seen == [("Set up webhook alerts (Discord, ntfy etc.)?", True)]

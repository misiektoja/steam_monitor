"""Tests the guided setup wizard, the zero-argument welcome screen and the input normalizers."""

import os
import pty
import re
import select
import subprocess
import sys
from pathlib import Path

import pytest

import steam_monitor as monitor


REPO_ROOT = Path(__file__).resolve().parents[1]
STEAM64 = 76561197960435530
API_KEY = "A" * 32
WEBHOOK_URL = "https://discord.com/api/webhooks/123456789/verysecrettokenvalue"


@pytest.fixture
# Restores every module-level setting the wizard reads or writes back
def wizard_globals(monkeypatch):
    snapshot = {name: value for name, value in vars(monitor).items() if name.isupper()}
    monkeypatch.setattr(monitor, "COLORED_OUTPUT", False)
    monkeypatch.setattr(monitor, "STEAM_API_KEY", "your_steam_web_api_key")
    yield
    for name, value in snapshot.items():
        setattr(monitor, name, value)


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
def run_wizard(tmp_path, monkeypatch, answers, secrets=None, transcript=None, initial_target=None):
    monkeypatch.setattr(monitor, "validate_steam_api_key", lambda _key, timeout=10: True)
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
        input_func=scripted_input(answers, transcript),
        getpass_func=fake_getpass,
        interactive=True,
    )
    return code


# The shortest answer script that reaches Save: target, two intervals, no email, no webhook, save, no doctor
def minimal_answers(target=str(STEAM64)):
    return [target, "y", "5m", "45s", "n", "n", "1", "n", "n"]


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
    answers = [str(STEAM64), "y", "5m", "45s", "n", "n", "3", "y"]

    code = run_wizard(tmp_path, monkeypatch, answers)

    assert code == 1
    assert not (tmp_path / "steam_monitor.conf").exists()
    assert not (tmp_path / ".env").exists()


# Verifies declining the discard keeps every answer rather than restarting
def test_declining_the_discard_keeps_the_answers(tmp_path, monkeypatch, wizard_globals, capsys):
    # Discard, decline the discard, then save, then decline doctor
    answers = [str(STEAM64), "y", "5m", "45s", "n", "n", "3", "n", "1", "n", "n"]

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
        str(STEAM64), "y", "5m", "45s", "n", "n",   # target, persist, polling, no email, no webhook
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
        str(STEAM64), "y", "5m", "45s", "n", "n",
        "2", "1", other_id, "y",   # review, choose Target, give a different profile, persist it
        "1", "n", "n",
    ]

    run_wizard(tmp_path, monkeypatch, answers)

    assert f"Steam64 ID {other_id}" in capsys.readouterr().out


# Verifies declining email turns every email alert off, so the summary cannot promise alerts that never fire
def test_declining_email_turns_every_email_alert_off(tmp_path, monkeypatch, wizard_globals):
    run_wizard(tmp_path, monkeypatch, minimal_answers())

    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    for key in ("ACTIVE_INACTIVE_NOTIFICATION", "GAME_CHANGE_NOTIFICATION", "ERROR_NOTIFICATION"):
        assert values[key] is False


# Verifies the webhook service is chosen before the URL is pasted, the shared order across these tools
def test_the_webhook_service_is_chosen_before_the_url(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = [str(STEAM64), "y", "5m", "45s", "n", "y", "1", "1", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, WEBHOOK_URL]) == 0

    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    assert values["WEBHOOK_ENABLED"] is True
    assert values["WEBHOOK_PROVIDER"] == "discord"
    assert values["WEBHOOK_ACTIVE_NOTIFICATION"] is True and values["WEBHOOK_STATUS_NOTIFICATION"] is False
    assert "Which webhook service should receive alerts?" in capsys.readouterr().out
    assert WEBHOOK_URL in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies a bare ntfy topic name is expanded to a full ntfy.sh URL, as the shared prompt promises
def test_a_bare_ntfy_topic_becomes_a_full_url(tmp_path, monkeypatch, wizard_globals):
    answers = [str(STEAM64), "y", "5m", "45s", "n", "y", "2", "n", "n", "1", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers, secrets=[API_KEY, "my-topic"]) == 0

    assert "https://ntfy.sh/my-topic" in (tmp_path / ".env").read_text(encoding="utf-8")


# Verifies a rejected duration is asked again instead of being stored as something else
def test_a_rejected_duration_is_asked_again(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = [str(STEAM64), "y", "banana", "5m", "45s", "n", "n", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers) == 0

    assert "Enter a positive duration such as" in capsys.readouterr().out
    assert monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))["STEAM_CHECK_INTERVAL"] == 300


# Verifies a rejected target is asked again with the guidance the reader needs
def test_a_rejected_target_is_asked_again(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = ["https://example.com/nope", str(STEAM64), "y", "5m", "45s", "n", "n", "1", "n", "n"]

    assert run_wizard(tmp_path, monkeypatch, answers) == 0
    assert "Enter a Steam64 ID" in capsys.readouterr().out


# Verifies an existing configuration is backed up rather than overwritten
def test_an_existing_configuration_is_backed_up(tmp_path, monkeypatch, wizard_globals):
    config = tmp_path / "steam_monitor.conf"
    config.write_text("CLEAR_SCREEN = False\n", encoding="utf-8")

    run_wizard(tmp_path, monkeypatch, minimal_answers())

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


# Verifies the persist answer puts the target in the config file, so the tool runs without arguments
def test_a_persisted_target_reaches_the_config_file(tmp_path, monkeypatch, wizard_globals):
    assert run_wizard(tmp_path, monkeypatch, minimal_answers()) == 0

    values = monitor.parse_config_content((tmp_path / "steam_monitor.conf").read_text(encoding="utf-8"))
    assert values["TARGET_STEAM_ID"] == str(STEAM64)


# Verifies declining the persist question leaves the target out of the written config
def test_a_declined_persist_leaves_the_target_out_of_the_config(tmp_path, monkeypatch, wizard_globals, capsys):
    answers = [str(STEAM64), "n", "5m", "45s", "n", "n", "1", "n", "n"]

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


# Verifies the welcome screen offers the four commands a newcomer needs next
def test_the_welcome_screen_offers_four_commands(capsys):
    monitor.print_welcome_screen(interactive=False)

    output = capsys.readouterr().out
    assert "Quickest start (already configured):" in output
    assert "Easiest start (guided setup wizard):" in output
    assert "Check setup before monitoring:" in output
    assert "Full options:" in output
    assert monitor.QUICK_START_GUIDE_URL in output


# Verifies the welcome commands are written for this install and leave placeholders readable
def test_the_welcome_commands_suit_the_install(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["/usr/local/bin/steam_monitor"])
    monkeypatch.delenv(monitor.INSTALL_METHOD_ENV_VAR, raising=False)

    monitor.print_welcome_screen(interactive=False)

    output = capsys.readouterr().out
    assert "steam_monitor <steam_target>" in output
    assert "'<steam_target>'" not in output


# Verifies the wizard is not offered when there is no terminal to answer on
def test_the_welcome_screen_does_not_offer_the_wizard_without_a_terminal(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "run_setup_wizard", lambda **_kwargs: pytest.fail("the wizard ran without a terminal"))

    assert monitor.print_welcome_screen(interactive=False) == 0
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
    # save, decline doctor, decline monitoring
    raw = capture_wizard_pty(tmp_path, b"76561197960435530\ny\n5m\n45s\nn\nn\nn\n1\nn\nn\n")
    text = re.sub(r"\x1B\[[0-9;]*[A-Za-z]", "", raw)
    lines = [line[:-1] if line.endswith("\r") else line for line in text.split("\n")]

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
        "Setup summary",
        "Saved files",
        "Next steps",
    ]
    positions = [text.index(fragment) for fragment in order]
    assert positions == sorted(positions), order

    doubles = [index for index in range(len(lines) - 1) if not lines[index].strip() and not lines[index + 1].strip()]
    assert not doubles, f"double blank lines at {doubles}:\n{text}"

    assert (tmp_path / "w.conf").exists()

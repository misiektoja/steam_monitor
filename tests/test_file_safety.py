"""Tests that files are replaced atomically, backed up first, and that untrusted text cannot reach a terminal."""

import json
import os
import stat
from pathlib import Path

import pytest

import steam_monitor as monitor


# Verifies a state file is replaced through a temporary file, so a crash cannot leave it half written
def test_state_writes_are_atomic(tmp_path, monkeypatch):
    destination = tmp_path / "state.json"
    destination.write_text('{"previous": true}', encoding="utf-8")
    observed = {}
    real_replace = os.replace

    def record_replace(source, target):
        observed["source"] = str(source)
        observed["target"] = str(target)
        # The destination still holds the previous content right up to the rename
        observed["target_before_replace"] = Path(target).read_text(encoding="utf-8")
        return real_replace(source, target)

    monkeypatch.setattr(monitor.os, "replace", record_replace)

    monitor.write_json_atomic(destination, {"game_count": 3, "appids": [10, 20]})

    assert observed["target"] == str(destination)
    assert observed["source"] != str(destination)
    assert observed["target_before_replace"] == '{"previous": true}'
    assert json.loads(destination.read_text(encoding="utf-8")) == {"game_count": 3, "appids": [10, 20]}


# Verifies a failed write leaves the previous state file intact rather than truncating it
def test_a_failed_state_write_leaves_the_previous_file(tmp_path, monkeypatch):
    destination = tmp_path / "state.json"
    destination.write_text('{"previous": true}', encoding="utf-8")

    def refuse_replace(_source, _target):
        raise OSError("disk full")

    monkeypatch.setattr(monitor.os, "replace", refuse_replace)

    with pytest.raises(OSError):
        monitor.write_json_atomic(destination, {"new": True})

    assert destination.read_text(encoding="utf-8") == '{"previous": true}'
    # The temporary file is cleaned up rather than left beside the real one
    assert [entry.name for entry in tmp_path.iterdir()] == ["state.json"]


# Verifies the parent directory is created rather than the write failing on a fresh install
def test_a_state_write_creates_its_directory(tmp_path):
    destination = tmp_path / "nested" / "deeper" / "state.json"

    monitor.write_json_atomic(destination, {"ok": True})

    assert json.loads(destination.read_text(encoding="utf-8")) == {"ok": True}


# Verifies a replaced file is copied to a timestamped private backup first
def test_a_backup_is_created_before_a_replace(tmp_path):
    destination = tmp_path / "steam_monitor.conf"
    destination.write_text("CLEAR_SCREEN = False\n", encoding="utf-8")

    backup_path = monitor.create_timestamped_backup(destination)

    assert backup_path is not None
    backup = Path(backup_path)
    assert backup.name.startswith("steam_monitor.conf.")
    assert backup.name.endswith(".bak")
    assert backup.read_text(encoding="utf-8") == "CLEAR_SCREEN = False\n"
    if os.name == "posix":
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600


# Verifies a second backup in the same second gets its own name instead of overwriting the first
def test_backups_never_overwrite_each_other(tmp_path, monkeypatch):
    destination = tmp_path / "tool.conf"
    destination.write_text("first\n", encoding="utf-8")
    first = monitor.create_timestamped_backup(destination)

    destination.write_text("second\n", encoding="utf-8")
    second = monitor.create_timestamped_backup(destination)

    assert first is not None and second is not None
    assert first != second
    assert Path(first).read_text(encoding="utf-8") == "first\n"
    assert Path(second).read_text(encoding="utf-8") == "second\n"


# Verifies nothing is backed up when there is no previous file to lose
def test_no_backup_is_made_for_a_new_file(tmp_path):
    assert monitor.create_timestamped_backup(tmp_path / "absent.conf") is None


# Verifies a backup that cannot get a unique name fails loudly instead of silently skipping
def test_an_exhausted_backup_name_space_raises(tmp_path):
    destination = tmp_path / "tool.conf"
    destination.write_text("content\n", encoding="utf-8")

    with pytest.raises(OSError, match="unique backup"):
        monitor.create_timestamped_backup(destination, attempts=0)


# Verifies replacing a secret leaves no copy of the old one, since a stale credential on disk outlives its usefulness
def test_saving_a_secret_leaves_no_copy_of_the_previous_dotenv(tmp_path):
    destination = tmp_path / ".env"
    destination.write_text('WEBHOOK_URL="https://ntfy.sh/old-topic"\n', encoding="utf-8")

    result = monitor.update_dotenv_file(destination, {"WEBHOOK_URL": "https://ntfy.sh/new-topic"})

    assert "backup_path" not in result
    assert [entry.name for entry in tmp_path.iterdir()] == [".env"]
    assert destination.read_text(encoding="utf-8") == 'WEBHOOK_URL="https://ntfy.sh/new-topic"\n'


# Verifies terminal control sequences in a remote display name are stripped before output
def test_terminal_control_sequences_are_stripped():
    hostile = "Player\x1b[31m\x1b[2JRED\x07"

    cleaned = monitor.sanitize_untrusted_text(hostile)

    assert "\x1b" not in cleaned
    assert "\x07" not in cleaned
    assert cleaned == "PlayerRED"


# Verifies newlines and carriage returns cannot forge extra output lines
def test_line_breaks_cannot_forge_output():
    hostile = "Player\r\n* Error: something fake\nmore"

    cleaned = monitor.sanitize_untrusted_text(hostile)

    assert "\n" not in cleaned
    assert "\r" not in cleaned


# Verifies ordinary text including non-ASCII display names survives untouched
def test_ordinary_display_names_survive():
    assert monitor.sanitize_untrusted_text("Jan Kowalski") == "Jan Kowalski"
    assert monitor.sanitize_untrusted_text("  spaced  ") == "spaced"
    assert monitor.sanitize_untrusted_text(" Player_1 [EU]") == "Player_1 [EU]"
    # Display names are frequently non-ASCII, so the control-character filter must not strip real letters
    assert monitor.sanitize_untrusted_text("Zażółć gęślą jaźń") == "Zażółć gęślą jaźń"
    assert monitor.sanitize_untrusted_text("玩家一号") == "玩家一号"


# Verifies an absent value renders as an empty string rather than the word None
def test_an_absent_value_renders_empty():
    assert monitor.sanitize_untrusted_text(None) == ""


# Verifies an unbounded remote string cannot flood the terminal or the log
def test_an_overlong_value_is_truncated():
    cleaned = monitor.sanitize_untrusted_text("A" * 5000)

    assert len(cleaned) == 259
    assert cleaned.endswith("...")


# Verifies persona history sanitizes third-party names at the real terminal sink
def test_persona_history_cannot_forge_an_output_line(monkeypatch, capsys):
    monkeypatch.setattr(monitor, "fetch_persona_name_history", lambda _steamid: [{"name": "Player\n* Error: forged", "timechanged": "date\n* Error: time"}])

    monitor.display_persona_name_history(76561197960265740)

    output = capsys.readouterr().out
    assert "\n* Error: forged" not in output
    assert "\n* Error: time" not in output
    assert "Player* Error: forged" in output


# Verifies achievement text sanitizes every Steam-controlled field at the real terminal sink
def test_achievement_text_cannot_forge_output_lines(monkeypatch, capsys):
    achievement = {"game": "Game\n* Error: game", "name": "Badge\n* Error: badge", "description": "Text\n* Error: detail", "unlocktime": 0}
    monkeypatch.setattr(monitor, "fetch_recent_achievements", lambda *_args, **_kwargs: [achievement])

    monitor.display_recent_achievements(76561197960265740, object(), {})

    output = capsys.readouterr().out
    assert "\n* Error:" not in output
    assert "Game* Error: game" in output
    assert "Badge* Error: badge" in output
    assert "Text* Error: detail" in output


# Verifies no outbound request in the module can be added without the TLS setting, which a runtime test cannot prove
def test_every_outbound_request_passes_the_tls_setting():
    source = (Path(__file__).resolve().parents[1] / "steam_monitor.py").read_text(encoding="utf-8")
    offenders = []
    for number, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        makes_request = any(marker in stripped for marker in ("req.get(", "req.post(", "WEBHOOK_SESSION.get(", "WEBHOOK_SESSION.post("))
        if makes_request and "verify=" not in stripped:
            offenders.append(f"{number}: {stripped}")

    assert not offenders, "outbound requests missing verify=VERIFY_SSL:\n" + "\n".join(offenders)


# Verifies the minimum supported Python version is declared once and matches the packaging metadata
def test_the_minimum_python_version_is_declared_once():
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")

    assert f'requires-python = ">={monitor.MINIMUM_PYTHON_VERSION_TEXT}"' in pyproject
    assert f"Programming Language :: Python :: {monitor.MINIMUM_PYTHON_VERSION_TEXT}" in pyproject
    assert monitor.MINIMUM_PYTHON_VERSION_TEXT == ".".join(str(part) for part in monitor.MINIMUM_PYTHON_VERSION)

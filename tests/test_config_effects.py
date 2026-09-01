"""Tests that configuration, exported secrets and diagnostic flags reach the code that consumes them."""

from pathlib import Path
from typing import Optional

import pytest

import steam_monitor as monitor


LOCAL_TEST_DIR = Path(__file__).resolve().parents[1] / "local"
LOCAL_TEST_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture
# Restores every module-level setting the startup path mutates, so one test cannot leak into the next
def restored_globals():
    snapshot = {name: value for name, value in vars(monitor).items() if name.isupper()}
    yield
    for name, value in snapshot.items():
        setattr(monitor, name, value)
    for name in [name for name in vars(monitor) if name.isupper() and name not in snapshot]:
        delattr(monitor, name)


# Returns a config file that keeps a real startup run quiet and non-destructive
def write_config(directory, extra=""):
    config = Path(directory) / "steam_monitor.conf"
    config.write_text("CLEAR_SCREEN = False\nDISABLE_LOGGING = True\n" + extra, encoding="utf-8")
    return config


# Drives the real command line and returns the diagnostic state observed inside the config loader and the connectivity check
def run_startup(monkeypatch, argv, config_path, env_path="none", exported_api_key="test-api-key-value", target: Optional[str] = "76561197960435530"):
    observed = {}
    real_load_config_file = monitor.load_config_file

    def recording_load_config_file(path, namespace=None, report_errors=True):
        observed["debug_during_config_load"] = monitor.DEBUG_MODE
        observed["verbose_during_config_load"] = monitor.VERBOSE_MODE
        return real_load_config_file(path, namespace=namespace, report_errors=report_errors)

    def recording_check_internet(url=None, timeout=None):
        observed["debug_during_connectivity_check"] = monitor.DEBUG_MODE
        observed["verbose_during_connectivity_check"] = monitor.VERBOSE_MODE
        observed["connectivity_url"] = monitor.CHECK_INTERNET_URL if url is None else url
        observed["connectivity_timeout"] = monitor.CHECK_INTERNET_TIMEOUT if timeout is None else timeout
        return True

    def stop_before_monitoring(*_args, **_kwargs):
        observed["debug_at_monitoring_start"] = monitor.DEBUG_MODE
        observed["verbose_at_monitoring_start"] = monitor.VERBOSE_MODE
        observed["steam_api_key_at_monitoring_start"] = monitor.STEAM_API_KEY
        observed["monitored_steam_id"] = _args[0]
        raise SystemExit(0)

    monkeypatch.setattr(monitor, "load_config_file", recording_load_config_file)
    monkeypatch.setattr(monitor, "check_internet", recording_check_internet)
    monkeypatch.setattr(monitor, "steam_monitor_user", stop_before_monitoring)
    monkeypatch.setenv("STEAM_API_KEY", exported_api_key)
    command = ["steam_monitor.py"] + ([str(target)] if target is not None else []) + ["--env-file", str(env_path), "--config-file", str(config_path)] + argv
    monkeypatch.setattr("sys.argv", command)

    with pytest.raises(SystemExit) as exit_info:
        monitor.main()
    assert exit_info.value.code == 0
    return observed


# Verifies a check interval longer than the liveness interval leaves the configured reminder alone
def test_a_long_check_interval_keeps_the_configured_liveness_interval(tmp_path, monkeypatch, restored_globals):
    config_path = write_config(tmp_path, "LIVENESS_CHECK_INTERVAL = 43200\n")

    run_startup(monkeypatch, ["--check-interval", "86400"], config_path)

    assert monitor.LIVENESS_REMINDER_SECONDS == 43200


# Verifies an exported secret is applied even when no dotenv file exists, which the documentation promises
def test_exported_secret_applies_without_a_dotenv_file(monkeypatch):
    monkeypatch.setenv("STEAM_API_KEY", "exported-key")
    namespace = {"STEAM_API_KEY": "your_steam_web_api_key"}

    applied = monitor.load_secrets_from_environment(namespace=namespace)

    assert namespace["STEAM_API_KEY"] == "exported-key"
    assert ("STEAM_API_KEY", True) in applied


# Verifies an unchanged secret is reported as applied but not as changed, which SIGHUP uses to stay quiet
def test_unchanged_secret_is_not_reported_as_changed(monkeypatch):
    monkeypatch.setenv("STEAM_API_KEY", "same-key")
    namespace = {"STEAM_API_KEY": "same-key"}

    assert ("STEAM_API_KEY", False) in monitor.load_secrets_from_environment(namespace=namespace)


# Verifies each secret is attributed to its effective source when both sources define the same name
def test_secret_sources_separate_the_dotenv_file_from_the_environment(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text('STEAM_API_KEY="from-file"\nWEBHOOK_URL="https://ntfy.sh/file-topic"\n', encoding="utf-8")
    monkeypatch.setenv("STEAM_API_KEY", "from-environment")
    monkeypatch.setenv("SMTP_PASSWORD", "exported-only")
    monkeypatch.setenv("WEBHOOK_URL", "https://ntfy.sh/file-topic")
    monkeypatch.delenv("NTFY_ACCESS_TOKEN", raising=False)

    sources = monitor.secret_sources(env_file, exported_keys={"STEAM_API_KEY", "SMTP_PASSWORD"})

    assert sources == {"STEAM_API_KEY": "environment", "SMTP_PASSWORD": "environment", "WEBHOOK_URL": str(env_file)}


# Verifies dotenv loading cannot replace a secret that was already exported by the caller
def test_exported_secret_wins_over_the_dotenv_file(tmp_path, monkeypatch):
    from dotenv import load_dotenv
    env_file = tmp_path / ".env"
    env_file.write_text('STEAM_API_KEY="from-file"\n', encoding="utf-8")
    monkeypatch.setenv("STEAM_API_KEY", "from-environment")
    exported_keys = frozenset(secret for secret in monitor.SECRET_KEYS if monitor.os.getenv(secret) is not None)

    load_dotenv(env_file, override=False)
    namespace = {"STEAM_API_KEY": "from-config"}
    monitor.load_secrets_from_environment(namespace)

    assert namespace["STEAM_API_KEY"] == "from-environment"
    assert monitor.secret_sources(env_file, exported_keys=exported_keys)["STEAM_API_KEY"] == "environment"


# Verifies the real startup consumer keeps the exported key when its dotenv file defines the same name
def test_real_startup_keeps_exported_secret_precedence(tmp_path, monkeypatch, restored_globals):
    config = write_config(tmp_path)
    env_file = tmp_path / ".env"
    env_file.write_text('STEAM_API_KEY="from-file"\n', encoding="utf-8")

    observed = run_startup(monkeypatch, [], config, env_path=env_file, exported_api_key="from-environment")

    assert observed["steam_api_key_at_monitoring_start"] == "from-environment"
    assert monitor.secret_sources(env_file)["STEAM_API_KEY"] == "environment"


# Verifies SIGHUP refreshes file secrets without replacing values exported when the process started
def test_dotenv_reload_preserves_exported_secrets(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text('STEAM_API_KEY="new-file-key"\nSMTP_PASSWORD="new-file-password"\n', encoding="utf-8")
    monkeypatch.setenv("STEAM_API_KEY", "exported-key")
    monkeypatch.setenv("SMTP_PASSWORD", "old-file-password")

    monitor.reload_dotenv_secrets(env_file, exported_keys={"STEAM_API_KEY"})

    assert monitor.os.getenv("STEAM_API_KEY") == "exported-key"
    assert monitor.os.getenv("SMTP_PASSWORD") == "new-file-password"


# Verifies no source is reported when nothing was exported
def test_secret_sources_are_empty_when_nothing_is_exported(monkeypatch):
    for secret in monitor.SECRET_KEYS:
        monkeypatch.delenv(secret, raising=False)

    assert monitor.secret_sources(None) == {}


# Verifies --debug wins over a config file that disables it, already inside the config loader
def test_debug_flag_survives_a_config_that_disables_it(tmp_path, monkeypatch, restored_globals):
    config = write_config(tmp_path, "DEBUG_MODE = False\nVERBOSE_MODE = False\n")

    observed = run_startup(monkeypatch, ["--debug"], config)

    assert observed["debug_during_config_load"] is True
    assert observed["debug_during_connectivity_check"] is True
    assert observed["debug_at_monitoring_start"] is True


# Verifies --verbose wins over a config file that disables it, already inside the config loader
def test_verbose_flag_survives_a_config_that_disables_it(tmp_path, monkeypatch, restored_globals):
    config = write_config(tmp_path, "DEBUG_MODE = False\nVERBOSE_MODE = False\n")

    observed = run_startup(monkeypatch, ["--verbose"], config)

    assert observed["verbose_during_config_load"] is True
    assert observed["verbose_during_connectivity_check"] is True
    assert observed["verbose_at_monitoring_start"] is True
    # Verbose does not turn debug on either, so the two flags stay independent in both directions
    assert observed["debug_at_monitoring_start"] is False


# Verifies a config file can still enable debug mode on its own, from the moment it is loaded
def test_config_file_can_enable_debug_mode_without_a_flag(tmp_path, monkeypatch, restored_globals):
    config = write_config(tmp_path, "DEBUG_MODE = True\n")

    observed = run_startup(monkeypatch, [], config)

    assert observed["debug_during_config_load"] is False
    assert observed["debug_during_connectivity_check"] is True
    # Debug and verbose are independent, so a config that enables only debug leaves verbose off
    assert observed["verbose_during_connectivity_check"] is False


# Verifies neither mode turns itself on when nothing asks for it
def test_diagnostics_stay_off_by_default(tmp_path, monkeypatch, restored_globals):
    config = write_config(tmp_path)

    observed = run_startup(monkeypatch, [], config)

    assert observed["debug_at_monitoring_start"] is False
    assert observed["verbose_at_monitoring_start"] is False


# Verifies the connectivity check reads the configured URL and timeout rather than the values bound at import time
def test_connectivity_check_honors_the_configured_url_and_timeout(tmp_path, monkeypatch, restored_globals):
    config = write_config(tmp_path, 'CHECK_INTERNET_URL = "https://example.invalid/probe"\nCHECK_INTERNET_TIMEOUT = 9\n')

    observed = run_startup(monkeypatch, [], config)

    assert observed["connectivity_url"] == "https://example.invalid/probe"
    assert observed["connectivity_timeout"] == 9


# Verifies positional vanity forms reach the real startup consumer as one canonical Steam64 ID
@pytest.mark.parametrize("target,expected_url", [
    ("misiektoja", "https://steamcommunity.com/id/misiektoja/"),
    ("https://steamcommunity.com/id/name.with.dot/?view=all", "https://steamcommunity.com/id/name.with.dot/?view=all"),
])
def test_positional_vanity_forms_are_resolved_before_monitoring(tmp_path, monkeypatch, restored_globals, target, expected_url):
    config = write_config(tmp_path)
    resolved = 76561197960435530
    monkeypatch.setattr(monitor, "resolve_steam_community_url", lambda url, _key: resolved if url == expected_url else pytest.fail("unexpected URL"))

    observed = run_startup(monkeypatch, [], config, target=target)

    assert observed["monitored_steam_id"] == resolved


# Verifies a configured FILE_SUFFIX names the log file, which is what the setting documents
def test_configured_file_suffix_names_the_log_file(tmp_path, monkeypatch, restored_globals, capsys):
    config = tmp_path / "steam_monitor.conf"
    config.write_text(f'CLEAR_SCREEN = False\nDISABLE_LOGGING = False\nST_LOGFILE = "{tmp_path / "steam_monitor"}"\nFILE_SUFFIX = "mybox"\n', encoding="utf-8")

    run_startup(monkeypatch, [], config)

    assert f"Output:{'':<23}{tmp_path / 'steam_monitor_mybox.log'}" in capsys.readouterr().out


# Verifies the command line still wins over a configured suffix
def test_the_file_suffix_flag_wins_over_the_configured_value(tmp_path, monkeypatch, restored_globals, capsys):
    config = tmp_path / "steam_monitor.conf"
    config.write_text(f'CLEAR_SCREEN = False\nDISABLE_LOGGING = False\nST_LOGFILE = "{tmp_path / "steam_monitor"}"\nFILE_SUFFIX = "mybox"\n', encoding="utf-8")

    run_startup(monkeypatch, ["--file-suffix", "fromcli"], config)

    assert f"Output:{'':<23}{tmp_path / 'steam_monitor_fromcli.log'}" in capsys.readouterr().out


# Verifies an unset suffix still falls back to the monitored Steam ID
def test_an_unset_file_suffix_falls_back_to_the_steam_id(tmp_path, monkeypatch, restored_globals, capsys):
    config = tmp_path / "steam_monitor.conf"
    config.write_text(f'CLEAR_SCREEN = False\nDISABLE_LOGGING = False\nST_LOGFILE = "{tmp_path / "steam_monitor"}"\n', encoding="utf-8")

    run_startup(monkeypatch, [], config)

    assert f"Output:{'':<23}{tmp_path / 'steam_monitor_76561197960435530.log'}" in capsys.readouterr().out


# Verifies the legacy -r URL option still reaches the same monitoring consumer
def test_legacy_resolve_url_option_remains_supported(tmp_path, monkeypatch, restored_globals):
    config = write_config(tmp_path)
    resolved = 76561197960435530
    profile_url = "https://steamcommunity.com/id/misiektoja/"
    monkeypatch.setattr(monitor, "resolve_steam_community_url", lambda url, _key: resolved if url == profile_url else pytest.fail("unexpected URL"))

    observed = run_startup(monkeypatch, ["-r", profile_url], config, target=None)

    assert observed["monitored_steam_id"] == resolved


# Verifies an unedited webhook destination switches the channel off instead of being treated as configured
def test_a_placeholder_webhook_url_switches_the_channel_off(tmp_path, monkeypatch, restored_globals):
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    config = write_config(tmp_path, 'WEBHOOK_ENABLED = True\nWEBHOOK_URL = "your_webhook_url"\n')

    run_startup(monkeypatch, [], config)

    assert monitor.WEBHOOK_ENABLED is False


# Verifies a real destination still leaves the webhook channel on
def test_a_configured_webhook_url_keeps_the_channel_on(tmp_path, monkeypatch, restored_globals):
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    config = write_config(tmp_path, 'WEBHOOK_ENABLED = True\nWEBHOOK_URL = "https://ntfy.sh/some-topic"\n')

    run_startup(monkeypatch, [], config)

    assert monitor.WEBHOOK_ENABLED is True


# Verifies an unedited placeholder is never reported as a loaded secret, whichever layer supplied it
def test_placeholder_secrets_are_not_reported_as_loaded(tmp_path, monkeypatch, restored_globals):
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    config = write_config(tmp_path, 'WEBHOOK_URL = "your_webhook_url"\nSMTP_PASSWORD = "your_smtp_password"\n')

    run_startup(monkeypatch, [], config)

    from_file, from_environment, from_settings, from_command_line = monitor.doctor_secret_sources(None)
    assert "WEBHOOK_URL" not in from_file + from_environment + from_settings + from_command_line
    assert "SMTP_PASSWORD" not in from_file + from_environment + from_settings + from_command_line


# Verifies the settings count is a debug trace rather than a verbose line, since it says nothing a user acts on
def test_the_config_settings_count_is_a_debug_only_trace(tmp_path, monkeypatch, capsys):
    config = tmp_path / "steam_monitor.conf"
    config.write_text("CLEAR_SCREEN = False\nDISABLE_LOGGING = True\n", encoding="utf-8")
    namespace = {}

    monkeypatch.setattr(monitor, "VERBOSE_MODE", True)
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    monitor.load_config_file(config, namespace=namespace)
    assert "settings from the configuration file" not in capsys.readouterr().out

    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    monkeypatch.setattr(monitor, "DEBUG_MODE", True)
    monitor.load_config_file(config, namespace=namespace)
    assert "Configuration applied" in capsys.readouterr().out


# Verifies verbose says why email alerts are off when SMTP_HOST is still the shipped placeholder
def test_the_email_placeholder_notice_explains_why_alerts_are_off(tmp_path, monkeypatch, restored_globals, capsys):
    config = write_config(tmp_path, "ERROR_NOTIFICATION = True\n")

    run_startup(monkeypatch, ["--verbose"], config)

    assert "Email notifications are off because SMTP_HOST is still the shipped placeholder" in capsys.readouterr().out


# Verifies debug keeps whatever is already on the screen, since a cleared terminal loses the run being compared against
@pytest.mark.parametrize("flag,expected", [("--debug", False), ("--verbose", True)])
def test_only_debug_mode_keeps_the_screen(tmp_path, monkeypatch, restored_globals, flag, expected):
    cleared = []
    monkeypatch.setattr(monitor, "clear_screen", lambda enabled=True: cleared.append(bool(enabled)))
    monkeypatch.setattr(monitor, "DEBUG_MODE", False)
    monkeypatch.setattr(monitor, "VERBOSE_MODE", False)
    config = tmp_path / "steam_monitor.conf"
    config.write_text("CLEAR_SCREEN = True\nDISABLE_LOGGING = True\n", encoding="utf-8")

    run_startup(monkeypatch, [flag], config)

    assert cleared == [expected]


# Verifies the one-shot commands keep whatever is already on the screen, so their output stays scrollable
@pytest.mark.parametrize(("argv", "expected"), ((["steam_monitor", "--doctor"], True), (["steam_monitor", "--set-steam-api-key"], True), (["steam_monitor", "--send-test-email"], True), (["steam_monitor", "--help"], True), (["steam_monitor", "76561198000000000"], False)))
def test_one_shot_commands_keep_the_terminal_history(monkeypatch, argv, expected):
    monkeypatch.setattr(monitor.sys, "argv", argv)

    assert monitor.keep_terminal_history() is expected


# Verifies a redirected stdout is never cleared, so no escape sequence or TERM warning reaches the captured output
def test_a_redirected_stdout_is_never_cleared(monkeypatch):
    commands = []
    monkeypatch.setattr(monitor.sys.stdout, "isatty", lambda: False, raising=False)
    monkeypatch.setattr(monitor.os, "system", lambda command: commands.append(command))

    monitor.clear_screen(True)

    assert commands == []


@pytest.mark.parametrize("key, position", [("SMTP_PASSWORD", 2), ("STEAM_API_KEY", 3)])
# Verifies a secret passed as an argument is reported under the command line rather than the configuration file
def test_a_command_line_secret_lands_in_its_own_bucket(monkeypatch, key, position):
    for name in monitor.SECRET_KEYS:
        monkeypatch.setattr(monitor, name, "your_placeholder", raising=False)
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(monitor, "COMMAND_LINE_SECRET_KEYS", {"STEAM_API_KEY"})
    monkeypatch.setattr(monitor, key, "a-real-secret-value")

    buckets = monitor.doctor_secret_sources(None)

    assert buckets[position] == [key]
    assert [names for index, names in enumerate(buckets) if index != position] == [[], [], []]


# Verifies a key passed as an argument is reported as coming from the command line, not from the environment
def test_startup_records_an_argument_supplied_key_as_a_command_line_secret(monkeypatch, tmp_path, restored_globals):
    config = write_config(tmp_path)

    run_startup(monkeypatch, ["--steam-api-key", "F" * 32], config)

    assert monitor.COMMAND_LINE_SECRET_KEYS == frozenset({"STEAM_API_KEY"})
    assert monitor.doctor_secret_sources(None)[3] == ["STEAM_API_KEY"]
    assert [row.value for row in monitor.build_startup_summary("76561197960435530") if row.label == "Secrets from command line"] == ["STEAM_API_KEY"]


# Verifies the doctor reports that secret under the command line rather than the configuration file
def test_the_doctor_reports_a_command_line_secret_as_such(monkeypatch):
    for name in monitor.SECRET_KEYS:
        monkeypatch.setattr(monitor, name, "your_placeholder", raising=False)
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(monitor, "COMMAND_LINE_SECRET_KEYS", frozenset({"STEAM_API_KEY"}))
    monkeypatch.setattr(monitor, "STEAM_API_KEY", "a-real-api-key-value")

    labels = [check.label for check in monitor.doctor_secret_checks(None)]

    assert "Secrets loaded from the command line" in labels
    assert "Secrets loaded from the configuration file or command line" not in labels


# Verifies the status file destination from the command line reaches the file the monitor saves to
def test_the_status_file_from_the_command_line_reaches_the_monitor(monkeypatch, tmp_path, restored_globals):
    config = write_config(tmp_path)
    destination = tmp_path / "history" / "last_status.json"

    run_startup(monkeypatch, ["--status-file", str(destination)], config)

    assert monitor.resolve_status_file("misiektoja") == str(destination)


# Verifies the status file destination from the config file reaches the same place
def test_the_status_file_from_the_config_file_reaches_the_monitor(monkeypatch, tmp_path, restored_globals):
    config = write_config(tmp_path, 'STEAM_STATUS_FILE = "saved_status.json"\n')

    run_startup(monkeypatch, [], config)

    assert monitor.resolve_status_file("misiektoja").endswith("saved_status.json")


# Verifies the default status file name is still the per-display-name one, so an upgrade keeps its history
def test_the_default_status_file_keeps_the_existing_name(monkeypatch, tmp_path, restored_globals):
    config = write_config(tmp_path)

    run_startup(monkeypatch, [], config)

    assert monitor.resolve_status_file("misiektoja") == "steam_misiektoja_last_status.json"


"""Tests that configuration, exported secrets and diagnostic flags reach the code that consumes them."""

from pathlib import Path

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
def run_startup(monkeypatch, argv, config_path):
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
        raise SystemExit(0)

    monkeypatch.setattr(monitor, "load_config_file", recording_load_config_file)
    monkeypatch.setattr(monitor, "check_internet", recording_check_internet)
    monkeypatch.setattr(monitor, "steam_monitor_user", stop_before_monitoring)
    monkeypatch.setenv("STEAM_API_KEY", "test-api-key-value")
    monkeypatch.setattr(
        "sys.argv",
        ["steam_monitor.py", "76561197960435530", "--env-file", "none", "--config-file", str(config_path)] + argv,
    )

    with pytest.raises(SystemExit) as exit_info:
        monitor.main()
    assert exit_info.value.code == 0
    return observed


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


# Verifies each secret is attributed to the dotenv file or to the wider environment, never to both
def test_secret_sources_separate_the_dotenv_file_from_the_environment(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text('STEAM_API_KEY="from-file"\n', encoding="utf-8")
    # load_dotenv copies file values into the environment, which is the case the attribution has to survive
    monkeypatch.setenv("STEAM_API_KEY", "from-file")
    monkeypatch.setenv("SMTP_PASSWORD", "exported-only")
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    monkeypatch.delenv("NTFY_ACCESS_TOKEN", raising=False)

    sources = monitor.secret_sources(env_file)

    assert sources == {"STEAM_API_KEY": str(env_file), "SMTP_PASSWORD": "environment"}


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

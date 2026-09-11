import copy

import pytest

import steam_monitor as monitor


@pytest.fixture(autouse=True)
# Keeps entry-point tests from leaking loaded configuration into later tests
def isolated_runtime(monkeypatch, tmp_path):
    for name, value in list(vars(monitor).items()):
        if name.isupper():
            monkeypatch.setattr(monitor, name, copy.copy(value) if isinstance(value, (dict, list, set)) else value)
    if hasattr(monitor, "SECRET_SOURCES"):
        monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
    for name in ("DOTENV_RELOAD_STATE", "DOTENV_BASE_VALUES"):
        if hasattr(monitor, name):
            monkeypatch.setattr(monitor, name, {})
    for key in monitor.SECRET_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize("content", ["'SMTP_PASSWORD'='synthetic-old'\n", "export 'SMTP_PASSWORD'='xxxxxxxx\nxxxxxxxx'\n"])
# Quoted keys participate in both replacement confirmation and complete assignment updates
def test_quoted_saved_secret_is_detected_and_removed(tmp_path, content):
    path = tmp_path / "private.env"
    path.write_text(content + "KEEP=untouched\n", encoding="utf-8")
    assert monitor._dotenv_contains_key(path, "SMTP_PASSWORD")
    monitor.update_dotenv_file(path, {"SMTP_PASSWORD": ""})
    assert not monitor._dotenv_contains_key(path, "SMTP_PASSWORD")
    assert path.read_text(encoding="utf-8") == "KEEP=untouched\n"


# Explicit empty dotenv values override nonempty configuration values
def test_empty_saved_secret_overrides_configuration(monkeypatch, tmp_path):
    path = tmp_path / "private.env"
    path.write_text('SMTP_PASSWORD=""\n', encoding="utf-8")
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.setattr(monitor, "SMTP_PASSWORD", "synthetic-config")
    assert monitor.effective_secret_after_setup("SMTP_PASSWORD", path, {}) == ("", False)


# Nonempty exported credentials override the saved value and any pending replacement
def test_exported_secret_keeps_precedence(monkeypatch, tmp_path):
    path = tmp_path / "private.env"
    path.write_text('SMTP_PASSWORD="synthetic-file"\n', encoding="utf-8")
    monkeypatch.setenv("SMTP_PASSWORD", "synthetic-export")
    if hasattr(monitor, "SECRET_SOURCES"):
        monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
    if hasattr(monitor, "EXPORTED_SECRET_KEYS"):
        monkeypatch.setattr(monitor, "EXPORTED_SECRET_KEYS", frozenset({"SMTP_PASSWORD"}))
    assert monitor.effective_secret_after_setup("SMTP_PASSWORD", path, {"SMTP_PASSWORD": "synthetic-new"}) == ("synthetic-export", True)


# Recovery commands stay readable independently of the installation directory
def test_recovery_prefix_uses_short_names(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["/opt/private/tools/steam_monitor.py"])
    assert monitor.install_command_prefix() == ["python3", "steam_monitor.py"]


@pytest.mark.parametrize("override", [False, True])
# Setup resolves the selected file before offering saved answers or looking for credentials
def test_setup_keeps_saved_dotenv_destination(monkeypatch, tmp_path, override):
    import sys
    config = tmp_path / "settings.conf"
    saved = tmp_path / "saved.env"
    explicit = tmp_path / "explicit.env"
    saved.write_text('SMTP_PASSWORD="synthetic-saved"\n', encoding="utf-8")
    explicit.write_text('SMTP_PASSWORD="synthetic-explicit"\n', encoding="utf-8")
    config.write_text(f"DOTENV_FILE={str(saved)!r}\nDISABLE_LOGGING=True\n", encoding="utf-8")
    recorded = []

    class Captured(BaseException):
        pass

    # Stops at the first section after destination and baseline resolution
    def collect(state, *args, **kwargs):
        recorded.append((state.env_path, state.config_values["DISABLE_LOGGING"]))
        raise Captured
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(monitor, "_wizard_choose_config_destination", lambda *args, **kwargs: config)
    monkeypatch.setattr(monitor, "_wizard_collect_target_section", collect)
    with pytest.raises(Captured):
        monitor.run_setup_wizard(config_file=config, env_file=explicit if override else None)
    assert recorded == [(explicit if override else saved, True)]


# Doctor remains reachable when startup receives a quoted liveness interval
def test_doctor_handles_quoted_liveness_before_arithmetic(monkeypatch, tmp_path):
    import sys
    config = tmp_path / "settings.conf"
    config.write_text('LIVENESS_CHECK_INTERVAL="3600"\n', encoding="utf-8")
    errors = []

    # Records the validation reached through normal startup without contacting external services
    def doctor(*args, **kwargs):
        errors.extend(monitor.runtime_configuration_errors())
        return 1
    monkeypatch.setattr(sys, "argv", [monitor.__file__, "--doctor", "--config-file", str(config), "--env-file", "none"])
    monkeypatch.setattr(monitor, "run_doctor", doctor)
    with pytest.raises(SystemExit) as stopped:
        monitor.main()
    assert stopped.value.code == 1
    assert any("LIVENESS_CHECK_INTERVAL" in error for error in errors)


@pytest.mark.parametrize("exported", [False, True])
# Doctor after saving reads the saved file even when setup did not rewrite it
def test_post_save_uses_saved_empty_value_and_real_exports(monkeypatch, tmp_path, exported):
    env = tmp_path / "private.env"
    env.write_text('SMTP_PASSWORD=""\n', encoding="utf-8")
    config = tmp_path / "settings.conf"
    config.write_text('SMTP_PASSWORD="synthetic-config"\n', encoding="utf-8")
    state = monitor.WizardSetupState(config, env, {"SMTP_PASSWORD": "synthetic-config"})
    if exported:
        monkeypatch.setenv("SMTP_PASSWORD", "synthetic-export")
    monitor._wizard_apply_saved_values(state)
    assert monitor.SMTP_PASSWORD == ("synthetic-export" if exported else "")


# Resolving a saved dotenv path cannot overwrite the configuration with secret assignments
def test_setup_refuses_a_shared_config_and_dotenv_destination(tmp_path):
    config = tmp_path / "settings.conf"
    original = f"DOTENV_FILE={str(config)!r}\n"
    config.write_text(original, encoding="utf-8")
    state = monitor.WizardSetupState(config, tmp_path / "fallback.env", {})
    with pytest.raises(ValueError, match="different files"):
        monitor._wizard_seed_destination(state, None)
    assert config.read_text(encoding="utf-8") == original

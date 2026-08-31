# Offline test suite

These tests cover logic in `steam_monitor.py` that can run without network access.
Steam client and Web API calls are replaced with test doubles.

## Running

From the repository root:

```bash
pip install -e '.[test]'
python -m pytest
```

`pyproject.toml` puts the repository root first on `sys.path`, so the tests use the
working tree instead of an installed copy of the module.

Lint the same way CI does:

```bash
pip install -e '.[lint]'
python -m ruff check steam_monitor.py tests
```

CI runs both on every push and pull request, across Python 3.9 through 3.14,
and again before anything is published to PyPI.

## Layout

| File | Area under test |
| --- | --- |
| `test_config_effects.py` | Diagnostic flag precedence, exported secret loading and secret source attribution |
| `test_config_loading.py` | Declarative config parsing, rejected content and the generated template |
| `test_diagnostics_output.py` | Verbose and debug output for email, webhook, connectivity and secret redaction |
| `test_install_method_commands.py` | Install method detection, printed commands, masked secrets and guide links |
| `test_monitoring_diagnostics.py` | One monitoring cycle: Steam calls named, degraded features reported, quiet by default |
| `test_repository_contracts.py` | Governance documents, issue templates, action pinning, release gating and the CI contract |
| `test_repository_metadata.py` | Governance files, citation, funding, line endings, the declared editor style, the pinned linter and release integrity |
| `test_secret_inputs.py` | Atomic dotenv updates, hidden webhook and ntfy entry, refusal to save invalid input |
| `test_steam_monitor.py` | Profile URL resolution for numeric, Steam3, invite and vanity forms |
| `test_webhook_notifications.py` | Startup rollups, notification summary coloring, webhook settings and URL validation |

## Conventions

* Keep every test offline. If a code path needs network access, stub it with
  `monkeypatch` rather than skipping the test.
* Restore module-level globals you change. Tests share one imported module, so a
  leaked global affects whatever runs next.
* Replace Steam calls and notification delivery with test doubles.
* Never use a real Steam Web API key, SMTP password or webhook URL.

A change to the monitoring loop, authentication or Steam data handling is not
verified by this suite alone. Exercise it against a real account and say so in the
pull request, without usernames or credentials.

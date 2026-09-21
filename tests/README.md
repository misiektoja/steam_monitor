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

Build the documentation site the same way CI does:

```bash
pip install -r docs/requirements.txt
mkdocs build --strict
```

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
| `test_notification_receipts.py` | SMTP acceptance despite cleanup failures, receipt controls and unchanged notification content |
| `test_configuration_notification_boundaries.py` | Invalid output settings, CLI precedence and strict webhook fields with legacy JSON support |
| `test_boundary_regressions.py` | Real notification transports, literal secret resolution and malformed startup paths |
| `test_resource_boundaries.py` | Optional network work stops after real transport resource exhaustion |
| `test_release_boundaries.py` | Real HTTP retries, Discord mention safety, unrenderable templates, SMTP password round trips, split terminal writes and the width cap without wcwidth |
| `test_compact_commands.py` | Literal short command prefixes, real help output and dependency hints |
| `test_release_safety.py` | Credential preservation, private errors, timing checks, saved-state compatibility and real Steam rate limits |
| `test_recovery_safety.py` | Real dotenv reloads, setup backups, oversized counts and provider-error privacy |
| `test_secret_policy.py` | Shared credential priority, reload ownership and setup destination conflicts |
| `test_smtp_error_privacy.py` | Short and escaped passwords in rejected SMTP sign-ins through commands, setup, Doctor and delivery |
| `test_setup_resolution_regressions.py` | Saved dotenv destinations, empty secrets, export precedence and recovery paths |
| `test_dotenv_quoted_keys.py` | Quoted dotenv keys, export prefixes, multiline values and duplicate removal |
| `test_documentation_layout.py` | Unique anchors, main screenshot placement and matching entry-page feature summaries |
| `test_config_effects.py` | Diagnostic flag precedence, exported secret loading and secret source attribution |
| `test_config_upgrades.py` | Replay of every shipped config template, retired settings and generated-file destinations |
| `test_config_loading.py` | Declarative config parsing, rejected content and the generated template |
| `test_diagnostics_output.py` | Verbose and debug output for email, webhook, connectivity, TLS and secret redaction |
| `test_documentation.py` | Documentation site pages, guide links, navigation, documented flags, settings and doctor markers |
| `test_startup_summary_channels.py` | Summary rows naming the webhook provider, the mail server, the masked recipient, the delivery confirmations and the runtime |
| `test_startup_ui.py` | Startup summary rows, per-row routing, width-aware truncation and the grouped help |
| `test_setup_wizard.py` | The setup wizard, per-section editing, input normalizers, the welcome screen and their terminal output contract |
| `test_partial_setup_save.py` | Real wizard inputs and filesystem failures after configuration replacement |
| `test_doctor.py` | The doctor report, its checks, delivery-test consent, exit code and its terminal output contract |
| `test_help_screen.py` | The `--help` screen: the option groups, the worked examples and the version banner |
| `test_recovery_errors.py` | The recovery code taxonomy, classifier, rendered fix lines, hint deduplication and secret redaction |
| `test_file_safety.py` | Atomic state writes, timestamped backups, untrusted text sanitizing and the declared Python minimum |
| `test_install_method_commands.py` | Install method detection, printed commands, masked secrets and guide links |
| `test_monitoring_diagnostics.py` | One monitoring cycle: Steam calls named, degraded features reported, quiet by default |
| `test_email_html.py` | HTML notification bodies: escaping, Steam profile and store links, the Discord markdown form and the plain-text match |
| `test_repository_contracts.py` | Governance documents, issue templates, action pinning, release gating and the CI contract |
| `test_repository_metadata.py` | Governance files, citation, funding, line endings, the declared editor style, the pinned linter and release integrity |
| `test_tls_verification.py` | Every connection honouring `VERIFY_SSL` and the single shared TLS context builder |
| `test_secret_inputs.py` | Atomic dotenv updates, hidden webhook and ntfy entry, refusal to save invalid input |
| `test_steam_monitor.py` | Profile URL resolution for numeric, Steam3, invite and vanity forms |
| `test_webhook_notifications.py` | Startup rollups, notification summary coloring, webhook settings and URL validation |
| `test_moved_private_settings.py` | Kept credentials across dotenv destination changes and startup error handling |
| `test_real_rate_limit.py` | Real-client rate-limit alerts and fatal resource failures |

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

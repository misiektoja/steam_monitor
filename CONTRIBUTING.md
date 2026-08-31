# Contributing

steam_monitor is a real-time OSINT tool for tracking Steam player activity. Bug reports, documentation fixes and code contributions are welcome.

## Before contributing

Open an issue or a [discussion](https://github.com/misiektoja/steam_monitor/discussions) before starting substantial work, so an approach is agreed before you write it. Suspected vulnerabilities go through [SECURITY.md](SECURITY.md), never a public issue. [SUPPORT.md](SUPPORT.md) covers where to ask a usage question.

Contribute only code you have the right to license under GPL-3.0-or-later.

Never commit Steam Web API keys, SMTP passwords, webhook URLs or ntfy tokens, generated configuration files, log files or CSV exports. Keep scratch files and local test state out of commits. Secret scanning and gitleaks run on every change, but they are a backstop, not the first line of defense.

## Development setup

```sh
git clone https://github.com/misiektoja/steam_monitor.git
cd steam_monitor
pip install -e '.[test]'
```

The test extra already includes Pillow, which the ntfy artwork tests need. The `ntfy-images` extra installs the same dependency for normal use.

Optional local hooks catch what CI would reject before a commit is written:

```sh
pip install pre-commit
pre-commit install
```

## Development checks

```sh
python -m pytest
python -m ruff check steam_monitor.py tests
```

The default suite is offline. It never contacts Steam and network calls are replaced with local test doubles. See [tests/README.md](tests/README.md) for what each test file covers.

CI runs the same two checks on every push and pull request, across Python 3.9 through 3.14. The linter is pinned in the `lint` extra so a new ruff release cannot fail a build on a rule that did not exist when the change was written; the pre-commit hook pins the same version.

A change to the monitoring loop, authentication or Steam data handling is not verified by the offline suite alone. Exercise it against a real account and say so in the pull request, without usernames or credentials.

## What a change needs

- **Tests.** New behavior needs a test. A bug fix needs a test that fails without it. Match the existing files in `tests/`.
- **Documentation.** User-facing behavior belongs in [README.md](README.md), which is the reference for this project. Document a new configuration setting or command-line option in the section that covers its feature.
- **A release-notes entry.** Add it under the unreleased section of [RELEASE_NOTES.md](RELEASE_NOTES.md), following the existing category and prefix style. Write it for a user, not as an implementation log.
- **A Conventional Commits message.** Use the scope the repository already uses for that area.

Pull requests target `dev`. The pull request template lists the checks to report.

## Code style

The codebase favors complete implementations over minimal patches, explicit validation of anything Steam supplies and one concise summary comment directly above each shared function. Follow the surrounding code rather than introducing a new style.

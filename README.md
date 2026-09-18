# steam_monitor

<p align="left">
  <img src="https://img.shields.io/github/v/release/misiektoja/steam_monitor?style=flat-square&color=blue" alt="GitHub Release" />
  <img src="https://img.shields.io/pypi/v/steam_monitor?style=flat-square&color=teal" alt="PyPI Version" />
  <img src="https://img.shields.io/github/stars/misiektoja/steam_monitor?style=flat-square&color=magenta" alt="GitHub Stars" />
  <img src="https://img.shields.io/badge/python-3.6+-blueviolet?style=flat-square" alt="Python Versions" />
  <img src="https://img.shields.io/github/license/misiektoja/steam_monitor?style=flat-square&color=blue" alt="License" />
  <a href="https://scorecard.dev/viewer/?uri=github.com/misiektoja/steam_monitor"><img src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fapi.scorecard.dev%2Fprojects%2Fgithub.com%2Fmisiektoja%2Fsteam_monitor&query=%24.score&label=openssf%20scorecard&style=flat-square" alt="OpenSSF Scorecard" /></a>
  <img src="https://img.shields.io/github/last-commit/misiektoja/steam_monitor?style=flat-square&color=green" alt="Last Commit" />
  <img src="https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square" alt="Maintenance" />
</p>

Powerful tool for real-time tracking of **Steam players' activities**.

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/assets/steam_monitor.png" alt="steam_monitor_screenshot" width="85%"/>
</p>

<a id="quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/steam_monitor/installation/#new-to-python-check-and-install) first.

Install from PyPI:

```sh
pip install steam_monitor
```

Run the setup wizard:

```sh
steam_monitor --setup
```

The wizard asks for the target, the Steam Web API key and optional notifications. Review the settings before saving them. See [Setup & First Run](https://misiektoja.github.io/steam_monitor/setup-and-first-run/) for how to get the Steam Web API key and the required privacy settings.

For the manual single-file method, optional dependencies and upgrade commands, see [Installation](https://misiektoja.github.io/steam_monitor/installation/).

<a id="features"></a>
## Features

### 🔍 Activity and Profile Tracking

* **Gaming activity**: Detect online and offline status, game starts, finishes and changes.
* **Profile changes**: Track persona names, Steam level, XP, friends and game libraries.
* **Session statistics**: Measure time in each state, time per game and games played.

### 📊 Profile Insights

* **Profile details**: View badges, bans, friends, top games and recent playtime.
* **Optional detail**: Include friendship dates, persona name history and recent achievements.
* **Profile URLs**: Resolve Steam community links without looking up a numeric ID.

### 🔔 Notifications and History

* **Event alerts**: Configure email, Discord and ntfy notifications independently.
* **CSV history**: Save activity and profile changes with timestamps.
* **Session continuity**: Save status across restarts and preserve statistics through short offline interruptions.

### ⚙️ Setup and Configuration

* **Guided setup**: Review settings with `--setup` and check readiness with `--doctor`.
* **Flexible settings**: Use config files, dotenv files, environment variables and command-line options.
* **Terminal and runtime controls**: Customize colours and adjust the running monitor through supported signals.

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install--run) above for first-time setup. The table uses PyPI commands. For the manual script equivalents, see [Run Individual Commands](https://misiektoja.github.io/steam_monitor/setup-and-first-run/#run-individual-commands).

Replace the target placeholders with a Steam64 ID or complete Steam community profile URL. Monitoring requires the [Steam Web API key](https://misiektoja.github.io/steam_monitor/setup-and-first-run/#steam-web-api-key) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `steam_monitor --setup` |
| Start monitoring with existing authentication | `steam_monitor <steam_target>` |
| Check authentication, connectivity and one target | `steam_monitor --doctor <steam_target>` |
| Enter or replace securely the Steam Web API key | `steam_monitor --set-steam-api-key` |
| Configure and test webhook alerts | Use the setup wizard or follow [Webhook Settings](https://misiektoja.github.io/steam_monitor/configuration/#webhook-settings) |
| Save an SMTP password for email alerts | `steam_monitor --set-smtp-password` |
| Send a test email | `steam_monitor --send-test-email` |
| Save a new webhook URL | `steam_monitor --set-webhook-url` |
| Send a test webhook | `steam_monitor --send-test-webhook` |
| Show profile details once | `steam_monitor <steam_target> -i` |
| Also list friends and recent achievements | `steam_monitor <steam_target> -i --list-friends --achievements` |
| Resolve a community URL to a Steam64 ID | `steam_monitor -r <community_url>` |
| Write every change to a CSV file | `steam_monitor <steam_target> -b changes.csv` |
| Use a specific configuration and secrets file | `steam_monitor --config-file steam_monitor.conf --env-file .env <steam_target>` |
| List every supported command-line flag | `steam_monitor --help` |

The monitored account must expose the activity described in [User Privacy Settings](https://misiektoja.github.io/steam_monitor/setup-and-first-run/#user-privacy-settings).

Running the tool with no arguments offers the wizard if you have not saved a profile. If a profile is already saved, it starts monitoring that profile.

The tool runs until interrupted (`Ctrl+C`). Use `tmux` or `screen` for persistence and run multiple copies to monitor several profiles.

For the Web API key, saved profiles and notification setup, see the [full Setup & First Run guide](https://misiektoja.github.io/steam_monitor/setup-and-first-run/).

For email and webhook setup, see [Configuration](https://misiektoja.github.io/steam_monitor/configuration/). For notification choices, user information commands and output files, see [Usage](https://misiektoja.github.io/steam_monitor/usage/).

If a run fails, start with [Doctor Preflight](https://misiektoja.github.io/steam_monitor/troubleshooting/#doctor-preflight).

<a id="documentation"></a>
## Documentation

Full documentation is available at **[misiektoja.github.io/steam_monitor](https://misiektoja.github.io/steam_monitor/)**:

| Page | What it covers |
| --- | --- |
| [Installation](https://misiektoja.github.io/steam_monitor/installation/) | Python walkthrough, PyPI or manual installation, upgrades |
| [Setup & First Run](https://misiektoja.github.io/steam_monitor/setup-and-first-run/) | Setup wizard, the Steam Web API key, profile visibility, the first monitoring run |
| [Configuration](https://misiektoja.github.io/steam_monitor/configuration/) | Config file, SMTP, webhooks, storing secrets, check intervals |
| [Usage](https://misiektoja.github.io/steam_monitor/usage/) | Monitoring mode, user information mode, notifications, CSV export, signals, terminal output |
| [Troubleshooting](https://misiektoja.github.io/steam_monitor/troubleshooting/) | `--doctor` preflight checks, what to do when something fails, `--verbose` and `--debug` output |
| [Testing](https://misiektoja.github.io/steam_monitor/testing/) | Running the offline suite, the linter and the docs build |
| [About](https://misiektoja.github.io/steam_monitor/about/) | Requirements, change log, contributing, security, license, support |

<a id="change-log"></a>
## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/steam_monitor/blob/main/RELEASE_NOTES.md).

<a id="contributing"></a>
## Contributing

Bug reports, documentation fixes and code contributions are welcome. See [CONTRIBUTING.md](https://github.com/misiektoja/steam_monitor/blob/main/CONTRIBUTING.md) for the development setup, the checks CI enforces and what a change needs before it is merged. Participation is covered by the [Code of Conduct](https://github.com/misiektoja/steam_monitor/blob/main/CODE_OF_CONDUCT.md).

<a id="security"></a>
## Security

Report a suspected vulnerability privately through [GitHub security advisories](https://github.com/misiektoja/steam_monitor/security/advisories/new), never as a public issue. [SECURITY.md](https://github.com/misiektoja/steam_monitor/blob/main/SECURITY.md) covers the reporting process and the supported versions.

<a id="maintainers"></a>
## Maintainers

- **misiektoja** ([@misiektoja](https://github.com/misiektoja))

<a id="license"></a>
## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/steam_monitor/blob/main/LICENSE). Dependency licenses are listed in [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/steam_monitor/blob/main/THIRD_PARTY_NOTICES.md).

<a id="support"></a>
## Support

Questions, bug reports and vulnerability reports each have a place, listed in [SUPPORT.md](https://github.com/misiektoja/steam_monitor/blob/main/SUPPORT.md).

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).

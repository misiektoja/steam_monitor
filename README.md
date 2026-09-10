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

**Full documentation: [misiektoja.github.io/steam_monitor](https://misiektoja.github.io/steam_monitor/)**

<a id="-quick-install"></a>
<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](https://misiektoja.github.io/steam_monitor/installation/#new-to-python-install-everything) first.

Install from PyPI:

```sh
pip install steam_monitor
```

Run the setup wizard:

```sh
steam_monitor --setup
```

The wizard asks for the target, authentication, polling intervals and optional notifications. Review the settings before saving them. See [Setup & First Run](https://misiektoja.github.io/steam_monitor/setup-and-first-run/) for the service-specific steps.

For the manual single-file method, dependencies and upgrade commands, see [Installation](https://misiektoja.github.io/steam_monitor/installation/).

<p align="center">
   <img src="https://raw.githubusercontent.com/misiektoja/steam_monitor/refs/heads/main/assets/steam_monitor.png" alt="steam_monitor_screenshot" width="85%"/>
</p>

## Features

- **Real-time tracking** of Steam users' gaming activity, including when a user gets online or offline and which games they play
- **Detailed user information** display mode covering profile details, Steam level and XP, badges, ban status, friends, top games, recently played games, persona name history and recent achievements
- **Steam community URL resolution**, so you do not need to know the numeric ID
- **Change tracking** for Steam level and XP, display (persona) names, the friends list and the games library
- **Email and webhook notifications** through Discord, ntfy and compatible services, configurable per event
- **Guided setup** with `--setup`, and **preflight diagnostics** with `--doctor`
- **CSV export** of every activity and profile change, with **status persistence** across restarts
- **Flexible configuration** through config files, dotenv files, environment variables and command-line arguments

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install-run) for first-time setup. These examples use the PyPI command. See [Command Format by Installation Method](https://misiektoja.github.io/steam_monitor/usage/#command-format) for manual-script equivalents.

Replace the target placeholders with a Steam64 ID or complete Steam community profile URL. Monitoring requires the [Steam Web API key](https://misiektoja.github.io/steam_monitor/setup-and-first-run/#steam-web-api-key) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `steam_monitor --setup` |
| Start monitoring with saved credentials | `steam_monitor <steam_target>` |
| Check setup before monitoring | `steam_monitor --doctor <steam_target>` |
| Enter or replace credentials through hidden prompts | `steam_monitor --set-steam-api-key` |
| Use a specific configuration and secrets file | `steam_monitor --config-file steam_monitor.conf --env-file .env <steam_target>` |
| Show profile details once | `steam_monitor <steam_target> -i` |
| List every supported command-line option | `steam_monitor --help` |

The monitored account must expose the activity described in [User Privacy Settings](https://misiektoja.github.io/steam_monitor/setup-and-first-run/#user-privacy-settings).

Monitoring runs until you press `Ctrl+C`. For email, Discord and ntfy alerts, CSV output and service-specific commands, see [Usage](https://misiektoja.github.io/steam_monitor/usage/). If a run fails, start with [Doctor Preflight](https://misiektoja.github.io/steam_monitor/troubleshooting/#doctor-preflight).

## Documentation

| Page | What it covers |
| --- | --- |
| [Installation](https://misiektoja.github.io/steam_monitor/installation/) | Python walkthrough, PyPI or manual installation, upgrades |
| [Setup & First Run](https://misiektoja.github.io/steam_monitor/setup-and-first-run/) | The guided wizard, the Steam Web API key, profile visibility |
| [Configuration](https://misiektoja.github.io/steam_monitor/configuration/) | Config file, SMTP, webhooks, storing secrets, check intervals |
| [Usage](https://misiektoja.github.io/steam_monitor/usage/) | Monitoring mode, user information mode, notifications, CSV export, signals, coloring logs with GRC |
| [Troubleshooting](https://misiektoja.github.io/steam_monitor/troubleshooting/) | `--doctor` preflight checks, what to do when something fails, `--verbose` and `--debug` output |
| [Testing](https://misiektoja.github.io/steam_monitor/testing/) | Running the offline suite, the linter and the docs build |
| [About](https://misiektoja.github.io/steam_monitor/about/) | Requirements, change log, contributing, security, license, support |

## Change Log

See [RELEASE_NOTES.md](https://github.com/misiektoja/steam_monitor/blob/main/RELEASE_NOTES.md).

## Contributing

Bug reports, documentation fixes and code contributions are welcome. See [CONTRIBUTING.md](https://github.com/misiektoja/steam_monitor/blob/main/CONTRIBUTING.md) for the development setup, the checks CI enforces and what a change needs before it is merged. Participation is covered by the [Code of Conduct](https://github.com/misiektoja/steam_monitor/blob/main/CODE_OF_CONDUCT.md).

## Security

Report a suspected vulnerability privately through [GitHub security advisories](https://github.com/misiektoja/steam_monitor/security/advisories/new), never as a public issue. [SECURITY.md](https://github.com/misiektoja/steam_monitor/blob/main/SECURITY.md) covers the reporting process and the supported versions.

## License

Licensed under GPLv3. See [LICENSE](https://github.com/misiektoja/steam_monitor/blob/main/LICENSE). Dependency licenses are listed in [THIRD_PARTY_NOTICES.md](https://github.com/misiektoja/steam_monitor/blob/main/THIRD_PARTY_NOTICES.md).

## Support

Questions, bug reports and vulnerability reports each have a place, listed in [SUPPORT.md](https://github.com/misiektoja/steam_monitor/blob/main/SUPPORT.md).

If the project is useful to you, you can support its development through [GitHub Sponsors](https://github.com/sponsors/misiektoja) or [Buy Me a Coffee](https://buymeacoffee.com/misiektoja).

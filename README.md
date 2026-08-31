# steam_monitor

<p align="left">
  <img src="https://img.shields.io/github/v/release/misiektoja/steam_monitor?style=flat-square&color=blue" alt="GitHub Release" />
  <img src="https://img.shields.io/pypi/v/steam_monitor?style=flat-square&color=teal" alt="PyPI Version" />
  <img src="https://img.shields.io/github/stars/misiektoja/steam_monitor?style=flat-square&color=magenta" alt="GitHub Stars" />
  <img src="https://img.shields.io/badge/python-3.6+-blueviolet?style=flat-square" alt="Python Versions" />
  <img src="https://img.shields.io/github/license/misiektoja/steam_monitor?style=flat-square&color=blue" alt="License" />
  <img src="https://img.shields.io/github/last-commit/misiektoja/steam_monitor?style=flat-square&color=green" alt="Last Commit" />
  <img src="https://img.shields.io/badge/maintenance-active-brightgreen?style=flat-square" alt="Maintenance" />
</p>

Powerful tool for real-time tracking of **Steam players' activities**.

**Full documentation: [misiektoja.github.io/steam_monitor](https://misiektoja.github.io/steam_monitor/)**

### 🚀 Quick Install

```sh
pip install steam_monitor
```

Then answer a few questions and it writes a ready-to-run configuration:

```sh
steam_monitor --setup
```

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

## Documentation

| Page | What it covers |
| --- | --- |
| [Installation](https://misiektoja.github.io/steam_monitor/installation/) | Requirements, installing from PyPI or by hand, upgrading |
| [Setup & First Run](https://misiektoja.github.io/steam_monitor/setup-and-first-run/) | The guided wizard, the Steam Web API key, profile visibility |
| [Configuration](https://misiektoja.github.io/steam_monitor/configuration/) | Config file, SMTP, webhooks, storing secrets, check intervals |
| [Usage](https://misiektoja.github.io/steam_monitor/usage/) | Monitoring mode, user information mode, notifications, CSV export, signals |
| [Troubleshooting](https://misiektoja.github.io/steam_monitor/troubleshooting/) | `--doctor` preflight checks, and what to do when something fails |
| [Debugging Tools](https://misiektoja.github.io/steam_monitor/debugging/) | `--verbose` and `--debug` output, coloring logs with GRC |
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

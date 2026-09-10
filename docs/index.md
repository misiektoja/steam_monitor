# steam_monitor

Real-time tracker for Steam players' activity, with detailed profile insights and instant alerts.

<a id="-quick-install"></a>
<a id="-quick-install-run"></a>
### 🚀 Quick Install & Run

New to Python or unsure what is installed? Follow the [Python install walkthrough](installation.md#new-to-python-install-everything) first.

Install from PyPI:

```sh
pip install steam_monitor
```

Run the setup wizard:

```sh
steam_monitor --setup
```

The wizard asks for the target, authentication, polling intervals and optional notifications. Review the settings before saving them. See [Setup & First Run](setup-and-first-run.md) for the service-specific steps.

For the manual single-file method, dependencies and upgrade commands, see [Installation](installation.md).

## Features

### Activity and Profile Tracking

* **Gaming activity**: Detect online and offline status, game starts, finishes and changes.
* **Profile changes**: Track persona names, Steam level, XP, friends and game libraries.
* **Session statistics**: Measure time in each state, time per game and games played.

### Profile Insights

* **Profile details**: View badges, bans, friends, top games and recent playtime.
* **Optional detail**: Include friendship dates, persona name history and recent achievements.
* **Profile URLs**: Resolve Steam community links without looking up a numeric ID.

### Notifications and History

* **Event alerts**: Configure email, Discord and ntfy notifications independently.
* **CSV history**: Save activity and profile changes with timestamps.
* **Session continuity**: Save status across restarts and preserve statistics through short offline interruptions.

### Setup and Configuration

* **Guided setup**: Review settings with `--setup` and check readiness with `--doctor`.
* **Flexible settings**: Use config files, dotenv files, environment variables and command-line options.
* **Terminal and runtime controls**: Customize colours and adjust the running monitor through supported signals.

## Screenshots

![steam_monitor](https://raw.githubusercontent.com/misiektoja/steam_monitor/main/assets/steam_monitor.png)

<a id="common-commands"></a>
## Common Commands

Use [Quick Install & Run](#-quick-install-run) for first-time setup. These examples use the PyPI command. See [Command Format by Installation Method](usage.md#command-format) for manual-script equivalents.

Replace the target placeholders with a Steam64 ID or complete Steam community profile URL. Monitoring requires the [Steam Web API key](setup-and-first-run.md#steam-web-api-key) described in the setup guide.

| I want to... | Run this |
| --- | --- |
| Configure the target, credentials and alerts | `steam_monitor --setup` |
| Start monitoring with saved credentials | `steam_monitor <steam_target>` |
| Check setup before monitoring | `steam_monitor --doctor <steam_target>` |
| Enter or replace credentials through hidden prompts | `steam_monitor --set-steam-api-key` |
| Use a specific configuration and secrets file | `steam_monitor --config-file steam_monitor.conf --env-file .env <steam_target>` |
| Show profile details once | `steam_monitor <steam_target> -i` |
| List every supported command-line option | `steam_monitor --help` |

The monitored account must expose the activity described in [User Privacy Settings](setup-and-first-run.md#user-privacy-settings).

Monitoring runs until you press `Ctrl+C`. For email, Discord and ntfy alerts, CSV output and service-specific commands, see [Usage](usage.md). If a run fails, start with [Doctor Preflight](troubleshooting.md#doctor-preflight).

## Documentation

* [Installation](installation.md) - Python setup, package or manual install and upgrades
* [Setup & First Run](setup-and-first-run.md) - credentials, target selection and the setup wizard
* [Configuration](configuration.md) - settings, notifications and secret storage
* [Usage](usage.md) - monitoring, output and command options
* [Troubleshooting](troubleshooting.md) - Doctor checks and recovery steps

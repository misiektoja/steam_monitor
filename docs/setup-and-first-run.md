# Setup & First Run

This page assumes steam_monitor is already installed. If it is not, start with [Installation](installation.md).

## Guided Setup

The quickest way to a working configuration is to answer a few questions:

```sh
steam_monitor --setup
```

It asks for the profile to monitor, whether to save that profile in the config file, how often to check, your Steam Web API key and whether you want email or webhook alerts. Enter accepts the shown default and Ctrl+C cancels. **Nothing is written until you choose Save**: the answers are held until the end, where a summary shows exactly what is about to be written and lets you go back and change **one section without losing the other answers**.

Answers are accepted in the formats people actually paste. The profile takes a **Steam64 ID, a Steam3 identifier, a vanity name or a full profile URL**, and is normalized to one canonical Steam64 ID. During fresh setup, a vanity name is resolved after the API key step. Intervals take **`30s`, `2m`, `1.5h`, `1h 30m`, `1d`** or a plain number of seconds. Supported units are `s`, `m`, `h` and `d`.

For webhook alerts, setup asks which service receives them, then takes the Discord webhook URL or an ntfy topic. A bare ntfy.sh topic name is expanded to its full URL. For ntfy it also offers a separate access token and artwork attachments.

Secrets are typed at a hidden prompt and go to the dotenv file. Non-secret settings go to the config file. Existing files are backed up before being replaced. When it finishes, setup offers to run [`--doctor`](troubleshooting.md#doctor-preflight) and prints the exact commands to start monitoring. For a local install it then offers to **start monitoring right away**.

If the config file names a target in [`TARGET_STEAM_ID`](configuration.md#target-profile), running the tool with no arguments starts monitoring that profile. With no saved target, running it **with no arguments at all** prints the same four commands and offers to start the wizard.

If there is no terminal to answer on, setup says so and points at `--generate-config` instead of hanging.

## Quick Start

If you would rather configure it by hand, first save your [Steam Web API key](#steam-web-api-key) through the hidden prompt:

```sh
steam_monitor --set-steam-api-key
```

Then pass the profile as `steam_target` to start monitoring:

```sh
steam_monitor <steam_target>
```

Or if you installed [manually](installation.md#manual-installation):

```sh
python3 steam_monitor.py --set-steam-api-key
python3 steam_monitor.py <steam_target>
```

To get the list of all supported command-line arguments / flags:

```sh
steam_monitor --help
```

## Steam Web API key

You can get the Steam Web API key here: [http://steamcommunity.com/dev/apikey](http://steamcommunity.com/dev/apikey)

Provide the `STEAM_API_KEY` secret using one of the following methods:

 - Answer the questions in `--setup`, which validates and saves it for you (recommended)
 - Save and validate it through a hidden prompt with `--set-steam-api-key`
 - Set it as an [environment variable](configuration.md#storing-secrets), for example `export STEAM_API_KEY=...`
 - Add it to a [.env file](configuration.md#storing-secrets) as `STEAM_API_KEY=...` for persistent use
 - Pass it at runtime with `-u` / `--steam-api-key`

The recommended command keeps the key out of shell history and process listings. It validates the key against the Steam Web API before atomically updating `.env`:

```sh
steam_monitor --set-steam-api-key
```

For a custom private settings file:

```sh
steam_monitor --set-steam-api-key --env-file /path/.env-steam_monitor
```

A key passed with `-u` / `--steam-api-key` may remain visible in shell history or process listings.

Fallback:

 - Hard-code it in the code or config file

If you store the `STEAM_API_KEY` in a dotenv file you can update its value and send a `SIGHUP` signal to the process to reload the file with the new API key without restarting the tool. More info in [Storing Secrets](configuration.md#storing-secrets) and [Signal Controls (macOS/Linux/Unix)](usage.md#signal-controls-macoslinuxunix).

## User Privacy Settings

In order to monitor Steam user activity, proper privacy settings need to be enabled on the monitored user account.

The user should go to [Steam Privacy Settings](https://steamcommunity.com/my/edit/settings).

The value in **My Profile → Game details** should be set to **Friends Only** or **Public**.

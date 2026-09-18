# Setup & First Run

<a id="run-the-setup-wizard"></a>
## Run the setup wizard

Already installed? Run the setup command below for your installation and follow the prompts. Otherwise, start with [Installation](installation.md).

Setup asks who to monitor, your Steam Web API key, how often to check and which alerts and output files you want. You can review your answers before saving. Regular settings go in `steam_monitor.conf` and private values go in `.env`. Keep `.env` private.

Press Enter to accept a default or Ctrl+C to cancel. Cancelling before saving leaves your files untouched. Cancelling after saving keeps the saved settings. For changes to an existing setup, see [Configuration File](configuration.md#configuration-file).

After saving, follow the offered Doctor checks and monitoring steps.

=== "PyPI"

    ```sh
    steam_monitor --setup
    ```

=== "Manual Python script on macOS or Linux"

    ```sh
    python3 steam_monitor.py --setup
    ```

=== "Manual Python script on Windows"

    ```powershell
    python steam_monitor.py --setup
    ```

A **target** is the Steam profile you want to monitor. Enter a Steam64 ID, Steam3 identifier, vanity name or full profile URL. The wizard asks for your Steam Web API key. See [Steam Web API key](#steam-web-api-key) for how to get one.

The polling prompts accept plain seconds or the `s`, `m`, `h` and `d` units. They show both the seconds and a readable form of the default.

With a saved target, running Steam Monitor without a target starts monitoring that profile. If no target is saved, an interactive no-argument run offers setup.

<a id="before-you-start"></a>
## Before you start

You need three things before the first monitoring run:

1. A Steam target. A Steam64 ID, Steam3 identifier, vanity name or complete community profile URL all work.
2. A Steam Web API key. See [Steam Web API key](#steam-web-api-key).
3. The monitored account must publish its game details. See [User Privacy Settings](#user-privacy-settings).

<a id="steam-web-api-key"></a>
## Steam Web API key

You can get the Steam Web API key here: [http://steamcommunity.com/dev/apikey](http://steamcommunity.com/dev/apikey)

Provide the `STEAM_API_KEY` secret using one of the following methods:

 - Answer the questions in `--setup`, which validates and saves it for you (recommended)
 - Save and validate it through a hidden prompt with `--set-steam-api-key`
 - Set it as an [environment variable](configuration.md#storing-secrets), for example `export STEAM_API_KEY=...`
 - Add it to a [.env file](configuration.md#storing-secrets) as `STEAM_API_KEY=...` for persistent use
 - Pass it at runtime with `-u` / `--steam-api-key`

The hidden prompt validates the key with Steam before saving it to `.env`:

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

<a id="user-privacy-settings"></a>
## User Privacy Settings

In order to monitor Steam user activity, proper privacy settings need to be enabled on the monitored user account.

The user should go to [Steam Privacy Settings](https://steamcommunity.com/my/edit/settings).

The value in **My Profile → Game details** should be set to **Friends Only** or **Public**.

<a id="not-sure-which-command-you-need"></a>
## Not sure which command you need?

| I want to... | Run this |
| --- | --- |
| Set up Steam Monitor for the first time | Use the setup command for your installation above |
| Start monitoring with existing credentials | `steam_monitor <steam_target>`, which accepts a Steam64 ID, Steam3 identifier, vanity name or profile URL |
| Start the profile saved in `TARGET_STEAM_ID` | `steam_monitor --config-file steam_monitor.conf` |
| Check the API key, connectivity and one target | `steam_monitor --doctor <steam_target>` |
| Most securely enter or replace `STEAM_API_KEY` | Run `steam_monitor --set-steam-api-key` and enter the key at the hidden prompt |
| Save an SMTP password for email alerts | Run `steam_monitor --set-smtp-password` |
| Send a test email | Run `steam_monitor --send-test-email` |
| Set up webhook alerts | Run the setup wizard and choose webhook alerts |
| Save a new webhook URL | Run `steam_monitor --set-webhook-url` |
| Send a test webhook | Run `steam_monitor --send-test-webhook` |
| Show detailed profile information and exit | `steam_monitor <steam_target> -i` |
| Also list friends and recent achievements | `steam_monitor <steam_target> -i --list-friends --achievements` |
| Resolve a community URL to a Steam64 ID | `steam_monitor -r COMMUNITY_URL` |
| Write every change to a CSV file | `steam_monitor <steam_target> -b changes.csv` |
| List every supported command-line flag | `steam_monitor --help` |

<a id="run-individual-commands"></a>
## Run Individual Commands

The examples below use PyPI. For a manual script, replace `steam_monitor` with `python3 steam_monitor.py` on macOS or Linux. Use `python steam_monitor.py` on Windows and run it from the directory holding the script or give its full path. See [Command Format by Installation Method](usage.md#command-format-by-installation-method).

Throughout this page `<steam_target>` means a Steam64 ID, Steam3 identifier, vanity name or complete community profile URL.

<a id="save-the-steam-web-api-key"></a>
### Save the Steam Web API key

To configure credentials without the wizard, `--set-steam-api-key` is the recommended and most secure entry method. It reads the key through a hidden prompt, so the value does not appear on screen or in the command line. It validates the key with Steam before updating only `STEAM_API_KEY`. If validation fails, it does not change the `.env` file.

```sh
steam_monitor --set-steam-api-key
```

Use `--env-file PATH` to select another `.env` file. The `-u` and `--steam-api-key` options still work, but their values may appear in shell history or process listings.

<a id="save-notification-credentials"></a>
### Save notification credentials

The SMTP password is entered through a hidden prompt, checked against the mail server and saved as `SMTP_PASSWORD` in `.env`:

```sh
steam_monitor --set-smtp-password
```

A webhook URL is the private address used to deliver notifications. Treat it like a password because anyone who has it may be able to post through it. Follow the [webhook setup steps](configuration.md#webhook-settings) then save the link:

```sh
steam_monitor --set-webhook-url
```

The link is entered through a hidden prompt and saved as `WEBHOOK_URL` in `.env`. This command only saves the link. It does not turn on webhook alerts or send a message. See [Webhook Settings](configuration.md#webhook-settings) to choose your alerts then run `steam_monitor --send-test-webhook` to test them.

<a id="start-monitoring"></a>
### Start monitoring

The first example uses a positional target. The second uses a saved `TARGET_STEAM_ID`:

```sh
steam_monitor <steam_target>
steam_monitor --config-file steam_monitor.conf
```

For a [manual script](installation.md#install-the-manual-script):

```sh
python3 steam_monitor.py <steam_target>
```

To check the setup before the first run, without writing anything:

```sh
steam_monitor --doctor <steam_target>
```

See [Doctor Preflight](troubleshooting.md#doctor-preflight) for what it reports.

To see all supported command-line arguments and flags:

```sh
steam_monitor --help
```

<a id="next-step"></a>
## Next Step

Run [Doctor](troubleshooting.md#doctor-preflight) before an unattended run to confirm the API key, connectivity and notification settings.

With the API key saved and a first run working, continue to [Configuration](configuration.md) for the target profile, SMTP, webhooks and secrets. See [Usage](usage.md) for command formats, monitoring, listing commands, notifications and output files.

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import steam_monitor


LOCAL_TEST_DIR = Path(__file__).resolve().parents[1] / "local"
LOCAL_TEST_DIR.mkdir(parents=True, exist_ok=True)


class SecretInputTests(unittest.TestCase):
    # Creates one temporary test directory inside the project local directory
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(dir=str(LOCAL_TEST_DIR))
        self.destination = Path(self.tempdir.name) / ".env"

    # Cleans up the temporary test directory after each test
    def tearDown(self):
        self.tempdir.cleanup()

    # Verifies dotenv updates preserve unrelated settings and replace duplicate secret assignments
    def test_atomic_dotenv_update(self):
        self.destination.write_text("KEEP=value\nWEBHOOK_URL=old\nexport WEBHOOK_URL=duplicate\n", encoding="utf-8")
        result = steam_monitor.update_dotenv_file(self.destination, {"WEBHOOK_URL": "https://ntfy.sh/private-topic"})

        content = self.destination.read_text(encoding="utf-8")
        self.assertEqual(content, 'KEEP=value\nWEBHOOK_URL="https://ntfy.sh/private-topic"\n')
        self.assertEqual(result["updated_keys"], ("WEBHOOK_URL",))
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.destination.stat().st_mode), 0o600)

    # Verifies the monitoring command carries a target only when the config file will not supply one
    def test_next_steps_carry_the_target_the_config_does_not_supply(self):
        for saved, expects_placeholder in (("", True), ('TARGET_STEAM_ID = "76561198000000000"', False)):
            with self.subTest(saved=saved):
                config_path = Path(self.tempdir.name) / "steam_monitor.conf"
                config_path.write_text(saved + "\n", encoding="utf-8")
                destination = Path(self.tempdir.name) / f"secrets{len(saved)}.env"
                printed = []
                with patch("steam_monitor.find_config_file", return_value=str(config_path)), patch("builtins.print", side_effect=lambda *args, printed=printed, **kwargs: printed.append(" ".join(str(item) for item in args))):
                    steam_monitor.run_set_steam_api_key(env_file=str(destination), interactive=True, getpass_func=lambda prompt: "A" * 32, validator=lambda key: True)

                output = "\n".join(printed)
                self.assertIn("Check setup again:", output)
                self.assertIn("After Doctor passes, start monitoring:", output)
                self.assertNotIn("<steam_target>", output.split("After Doctor passes, start monitoring:", 1)[0])
                self.assertEqual("<steam_target>" in output, expects_placeholder)
                self.assertNotIn("76561198000000000", output)


    # Verifies hidden webhook entry saves the URL without displaying it
    def test_hidden_webhook_entry(self):
        secret = "https://discord.com/api/webhooks/123/private-token"
        with patch("builtins.print") as output:
            result = steam_monitor.run_set_webhook_url(env_file=str(self.destination), interactive=True, getpass_func=lambda prompt: secret)

        self.assertEqual(result, str(self.destination.resolve()))
        content = self.destination.read_text(encoding="utf-8")
        self.assertIn('WEBHOOK_URL="https://discord.com/api/webhooks/123/private-token"', content)
        self.assertNotIn("WEBHOOK_PROVIDER", content)
        rendered = "\n".join(" ".join(str(item) for item in call.args) for call in output.call_args_list)
        self.assertNotIn(secret, rendered)

    # Verifies public ntfy entry stores only the private URL
    def test_hidden_ntfy_entry_stores_only_url(self):
        replacement_prompt = Mock(side_effect=AssertionError("replacement prompt used"))
        result = steam_monitor.run_set_webhook_url(env_file=str(self.destination), interactive=True, input_func=replacement_prompt, getpass_func=lambda prompt: "https://ntfy.sh/private-topic")

        self.assertEqual(result, str(self.destination.resolve()))
        content = self.destination.read_text(encoding="utf-8")
        self.assertIn('WEBHOOK_URL="https://ntfy.sh/private-topic"', content)
        self.assertNotIn("WEBHOOK_PROVIDER", content)
        replacement_prompt.assert_not_called()

    # Verifies self-hosted ntfy entry does not mix provider configuration into dotenv
    def test_hidden_self_hosted_ntfy_entry_stores_only_url(self):
        replacement_prompt = Mock(side_effect=AssertionError("provider prompt used"))
        result = steam_monitor.run_set_webhook_url(env_file=str(self.destination), interactive=True, input_func=replacement_prompt, getpass_func=lambda prompt: "https://ntfy.example.test/private-topic")

        self.assertEqual(result, str(self.destination.resolve()))
        self.assertNotIn("WEBHOOK_PROVIDER", self.destination.read_text(encoding="utf-8"))
        replacement_prompt.assert_not_called()

    # Verifies an invalid webhook URL never changes an existing dotenv file
    def test_invalid_webhook_entry_is_not_saved(self):
        self.destination.write_text("KEEP=value\n", encoding="utf-8")
        with self.assertRaisesRegex(steam_monitor.SecretConfigurationError, "complete HTTPS"):
            steam_monitor.run_set_webhook_url(env_file=str(self.destination), interactive=True, getpass_func=lambda prompt: "http://example.test/topic")

        self.assertEqual(self.destination.read_text(encoding="utf-8"), "KEEP=value\n")

    # Verifies noninteractive secret entry fails before prompting or writing
    def test_noninteractive_entry_is_rejected(self):
        hidden_prompt = Mock(side_effect=AssertionError("hidden prompt used"))
        with self.assertRaisesRegex(steam_monitor.SecretConfigurationError, "interactive terminal"):
            steam_monitor.run_set_webhook_url(env_file=str(self.destination), interactive=False, getpass_func=hidden_prompt)

        hidden_prompt.assert_not_called()
        self.assertFalse(self.destination.exists())

    # Verifies replacement requires confirmation before the hidden prompt is shown
    def test_existing_secret_replacement_can_be_cancelled(self):
        self.destination.write_text('WEBHOOK_URL="https://ntfy.sh/old-topic"\n', encoding="utf-8")
        hidden_prompt = Mock(side_effect=AssertionError("hidden prompt used"))
        with self.assertRaisesRegex(steam_monitor.RecoveryError, "left as it is"):
            steam_monitor.run_set_webhook_url(env_file=str(self.destination), interactive=True, input_func=lambda prompt: "n", getpass_func=hidden_prompt)

        hidden_prompt.assert_not_called()
        self.assertIn("old-topic", self.destination.read_text(encoding="utf-8"))

    # Verifies hidden Steam API key entry validates and atomically saves the secret
    def test_hidden_steam_api_key_entry(self):
        api_key = "A" * 32
        validator = Mock(return_value=True)
        with patch("builtins.print") as output:
            result = steam_monitor.run_set_steam_api_key(env_file=str(self.destination), interactive=True, getpass_func=lambda prompt: api_key, validator=validator)

        self.assertEqual(result, str(self.destination.resolve()))
        validator.assert_called_once_with(api_key)
        self.assertIn(f'STEAM_API_KEY="{api_key}"', self.destination.read_text(encoding="utf-8"))
        rendered = "\n".join(" ".join(str(item) for item in call.args) for call in output.call_args_list)
        self.assertNotIn(api_key, rendered)

    # Verifies the one-shot command announces the Steam call before it blocks, the way the sibling commands do
    def test_the_key_command_announces_the_check_before_validating(self):
        seen = {}

        def validator(_key):
            seen["printed"] = [" ".join(str(item) for item in call.args) for call in output.call_args_list]
            return True

        with patch("builtins.print") as output:
            steam_monitor.run_set_steam_api_key(env_file=str(self.destination), interactive=True, getpass_func=lambda prompt: "A" * 32, validator=validator)

        self.assertTrue(any("Checking the entered Steam Web API key" in line for line in seen["printed"]), seen["printed"])

    # Verifies failed Steam API key validation leaves private settings unchanged
    def test_invalid_steam_api_key_is_not_saved(self):
        self.destination.write_text("KEEP=value\n", encoding="utf-8")
        with self.assertRaisesRegex(steam_monitor.SecretConfigurationError, "invalid"):
            steam_monitor.run_set_steam_api_key(env_file=str(self.destination), interactive=True, getpass_func=lambda prompt: "bad-key", validator=lambda value: False)

        self.assertEqual(self.destination.read_text(encoding="utf-8"), "KEEP=value\n")

    # Verifies live Steam API key validation checks a known public profile
    def test_steam_api_key_validation(self):
        response = Mock(status_code=200)
        response.json.return_value = {"response": {"players": []}}
        with patch.object(steam_monitor.req, "get", return_value=response) as request:
            self.assertTrue(steam_monitor.validate_steam_api_key("A" * 32))

        request.assert_called_once_with("https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/", params={"key": "A" * 32, "steamids": "76561197960287930"}, timeout=10, verify=steam_monitor.VERIFY_SSL)

    # Verifies the SMTP password is accepted by the mail server before it reaches the dotenv file
    def test_smtp_password_is_signed_in_before_it_is_saved(self):
        password = "app-password-value"
        sign_in = Mock(return_value="monitor@example.test")
        with patch("builtins.print") as output:
            result = steam_monitor.run_set_smtp_password(env_file=str(self.destination), interactive=True, getpass_func=lambda prompt: password, sign_in=sign_in)

        self.assertEqual(result, str(self.destination.resolve()))
        sign_in.assert_called_once_with(password, timeout=5)
        self.assertIn(f'SMTP_PASSWORD="{password}"', self.destination.read_text(encoding="utf-8"))
        rendered = "\n".join(" ".join(str(item) for item in call.args) for call in output.call_args_list)
        self.assertNotIn(password, rendered)
        self.assertIn("The mail server accepted the password for monitor@example.test", rendered)

    # Verifies a password the mail server rejects leaves private settings unchanged
    def test_refused_smtp_password_is_not_saved(self):
        self.destination.write_text("KEEP=value\n", encoding="utf-8")
        refuse = Mock(side_effect=steam_monitor.smtplib.SMTPAuthenticationError(535, b"authentication failed"))
        with self.assertRaisesRegex(steam_monitor.SecretConfigurationError, "did not accept the password"):
            steam_monitor.run_set_smtp_password(env_file=str(self.destination), interactive=True, getpass_func=lambda prompt: "wrong", sign_in=refuse)

        self.assertEqual(self.destination.read_text(encoding="utf-8"), "KEEP=value\n")

    # Verifies the sign-in uses the configured mail server and restores the password it borrowed
    def test_smtp_sign_in_uses_the_configured_mail_server(self):
        session = Mock()
        with patch.multiple(steam_monitor, SMTP_HOST="smtp.example.test", SMTP_USER="monitor@example.test", SENDER_EMAIL="monitor@example.test", RECEIVER_EMAIL="alerts@example.test", SMTP_PASSWORD="saved", SMTP_SSL=True):
            with patch.object(steam_monitor, "smtp_connect_and_login", return_value=session) as connect:
                self.assertEqual(steam_monitor.smtp_sign_in("entered", timeout=5), "monitor@example.test")
            connect.assert_called_once_with(True, smtp_timeout=5)
            session.quit.assert_called_once()
            self.assertEqual(steam_monitor.SMTP_PASSWORD, "saved")

    # Verifies an unconfigured mail server is reported instead of a bare connection failure
    def test_smtp_sign_in_reports_incomplete_settings(self):
        with patch.multiple(steam_monitor, SMTP_HOST="your_smtp_server_ssl", SMTP_USER="your_smtp_username", SENDER_EMAIL="your_sender_email", RECEIVER_EMAIL="your_receiver_email"):
            with self.assertRaisesRegex(steam_monitor.SecretConfigurationError, "settings are incomplete"):
                steam_monitor.smtp_sign_in("entered")

    # Verifies a blank password is refused rather than saved as an empty secret
    def test_blank_smtp_password_is_refused(self):
        with self.assertRaisesRegex(steam_monitor.SecretConfigurationError, "No SMTP password"):
            steam_monitor.smtp_sign_in("")

    # Verifies an interrupted entry reports the cancel itself, with the command that resumes it
    def test_an_interrupted_entry_reports_the_cancel_and_writes_nothing(self):
        def interrupt(prompt=""):
            raise KeyboardInterrupt

        with self.assertRaises(steam_monitor.RecoveryError) as raised:
            steam_monitor.run_set_smtp_password(env_file=str(self.destination), interactive=True, getpass_func=interrupt, sign_in=Mock(side_effect=AssertionError("signed in")))

        advice = raised.exception.advice
        self.assertEqual(advice.summary, "SMTP password setup was cancelled and the dotenv file was not changed")
        self.assertIn("Run --set-smtp-password again when you have the value ready", advice.fix)
        self.assertIn(steam_monitor.SMTP_GUIDE_URL, advice.fix)
        self.assertFalse(self.destination.exists())

    # Verifies a declined replacement reports the kept value rather than a cancelled entry
    def test_a_declined_replacement_reports_the_kept_value(self):
        self.destination.write_text('SMTP_PASSWORD="original"\n', encoding="utf-8")

        with self.assertRaises(steam_monitor.RecoveryError) as raised:
            steam_monitor.run_set_smtp_password(env_file=str(self.destination), interactive=True, input_func=lambda prompt: "n", getpass_func=Mock(side_effect=AssertionError("hidden prompt used")))

        advice = raised.exception.advice
        self.assertEqual(advice.summary, "The saved SMTP password was left as it is and the dotenv file was not changed")
        self.assertIn("answer y to replace the saved value", advice.fix)
        self.assertIn('SMTP_PASSWORD="original"', self.destination.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

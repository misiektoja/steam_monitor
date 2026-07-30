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
        with self.assertRaisesRegex(steam_monitor.SecretConfigurationError, "cancelled"):
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

        request.assert_called_once_with("https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/", params={"key": "A" * 32, "steamids": "76561197960287930"}, timeout=10)


if __name__ == "__main__":
    unittest.main()

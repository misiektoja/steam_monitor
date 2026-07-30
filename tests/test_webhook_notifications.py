import argparse
import unittest
from unittest.mock import Mock, patch

import steam_monitor


class FakeResponse:
    # Builds one fake HTTP response for webhook delivery tests
    def __init__(self, status_code=200, headers=None, payload=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload

    # Returns the configured fake JSON response
    def json(self):
        if self._payload is None:
            raise ValueError("No JSON body")
        return self._payload


class WebhookNotificationTests(unittest.TestCase):
    # Saves webhook globals and applies a valid baseline before each test
    def setUp(self):
        self.settings = {
            "ACTIVE_INACTIVE_NOTIFICATION": True,
            "STATUS_NOTIFICATION": False,
            "GAME_CHANGE_NOTIFICATION": True,
            "STEAM_LEVEL_XP_NOTIFICATION": True,
            "FRIENDS_NOTIFICATION": False,
            "GAMES_LIBRARY_NOTIFICATION": True,
            "NAME_CHANGE_NOTIFICATION": False,
            "ERROR_NOTIFICATION": True,
            "DOTENV_FILE": "",
            "STEAM_API_KEY": "",
            "stdout_bck": None,
            "WEBHOOK_ENABLED": True,
            "WEBHOOK_PROVIDER": "discord",
            "WEBHOOK_URL": "https://discord.com/api/webhooks/123/private-token",
            "WEBHOOK_USERNAME": "Steam Monitor",
            "WEBHOOK_AVATAR_URL": "",
            "WEBHOOK_ACTIVE_NOTIFICATION": False,
            "WEBHOOK_INACTIVE_NOTIFICATION": False,
            "WEBHOOK_STATUS_NOTIFICATION": True,
            "WEBHOOK_GAME_CHANGE_NOTIFICATION": False,
            "WEBHOOK_LEVEL_XP_NOTIFICATION": False,
            "WEBHOOK_FRIENDS_NOTIFICATION": False,
            "WEBHOOK_GAMES_NOTIFICATION": False,
            "WEBHOOK_NAME_CHANGE_NOTIFICATION": False,
            "WEBHOOK_ERROR_NOTIFICATION": True,
            "WEBHOOK_HEADERS": {},
            "WEBHOOK_TEMPLATE": {
                "username": "{username}",
                "allowed_mentions": {"parse": []},
                "embeds": [{"title": "{title}", "description": "{description}", "color": "{color}", "thumbnail": {"url": "{image_url}"}}],
            },
            "WEBHOOK_TRANSFORMS": [],
            "NTFY_ACCESS_TOKEN": "",
            "NTFY_IMAGES": False,
        }
        self.originals = {name: getattr(steam_monitor, name) for name in self.settings}
        for name, value in self.settings.items():
            setattr(steam_monitor, name, value)

    # Restores webhook globals after each test
    def tearDown(self):
        for name, value in self.originals.items():
            setattr(steam_monitor, name, value)

    # Verifies startup email and webhook summaries use compact single-line category rollups
    def test_startup_notification_summaries_use_compact_rollups(self):
        expected_email = "* Notifications (email):        On (online/offline, game changes, level/XP changes, games library, errors)"
        expected_webhook = "* Notifications (webhook):      On (all status changes, errors)"
        self.assertEqual(steam_monitor._startup_notification_summary_lines(), [expected_email, expected_webhook])

    # Verifies webhook categories remain off while the master switch is disabled
    def test_startup_webhook_summary_respects_master_switch(self):
        steam_monitor.WEBHOOK_ENABLED = False
        self.assertEqual(steam_monitor._startup_notification_summary_lines()[1], "* Notifications (webhook):      Off")

    # Verifies the generated config exposes supported webhook options without compact ntfy mode
    def test_config_block_contains_webhook_options(self):
        shared_options = ("WEBHOOK_ENABLED", "WEBHOOK_PROVIDER", "WEBHOOK_URL", "WEBHOOK_USERNAME", "WEBHOOK_AVATAR_URL", "WEBHOOK_HEADERS", "WEBHOOK_TEMPLATE", "WEBHOOK_TRANSFORMS", "NTFY_ACCESS_TOKEN", "NTFY_IMAGES")
        for option in shared_options:
            self.assertIn(f"{option} =", steam_monitor.CONFIG_BLOCK)
        self.assertNotIn("NTFY_SHORT", steam_monitor.CONFIG_BLOCK)
        self.assertFalse(hasattr(steam_monitor, "NTFY_SHORT"))
        self.assertIn("WEBHOOK_URL", steam_monitor.SECRET_KEYS)
        self.assertIn("NTFY_ACCESS_TOKEN", steam_monitor.SECRET_KEYS)
        self.assertNotIn("WEBHOOK_PROVIDER", steam_monitor.SECRET_KEYS)

    # Verifies private webhook destinations require complete credential-free HTTPS URLs
    def test_webhook_url_validation(self):
        self.assertTrue(steam_monitor.validate_webhook_url("https://ntfy.sh/private-topic"))
        self.assertFalse(steam_monitor.validate_webhook_url("http://ntfy.sh/private-topic"))
        self.assertFalse(steam_monitor.validate_webhook_url("https://user:pass@example.test/topic"))
        self.assertFalse(steam_monitor.validate_webhook_url("https://example.test"))

    # Verifies distinctive Discord and public ntfy URLs select the proper payload provider
    def test_webhook_provider_detection(self):
        self.assertEqual(steam_monitor.detect_webhook_provider("https://discord.com/api/webhooks/123/private-token"), "discord")
        self.assertEqual(steam_monitor.detect_webhook_provider("https://canary.discord.com/api/v10/webhooks/123/private-token"), "discord")
        self.assertEqual(steam_monitor.detect_webhook_provider("https://ntfy.sh/private-topic"), "ntfy")
        self.assertEqual(steam_monitor.detect_webhook_provider("https://ntfy.example.test/private-topic"), "")
        self.assertEqual(steam_monitor.detect_webhook_provider("https://example.test/custom-hook"), "")

    # Verifies Discord delivery uses the configured template and disables mentions
    def test_discord_payload_delivery(self):
        response = FakeResponse(204)
        with patch.object(steam_monitor.WEBHOOK_SESSION, "post", return_value=response) as post:
            result = steam_monitor.send_webhook("Status title", "Status body", "status")

        self.assertEqual(result, 0)
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["embeds"][0]["title"], "Status title")
        self.assertEqual(payload["embeds"][0]["description"], "Status body")
        self.assertEqual(payload["allowed_mentions"], {"parse": []})
        self.assertNotIn("thumbnail", payload["embeds"][0])

    # Verifies ntfy delivery uses native text with title metadata and Bearer authentication
    def test_ntfy_native_delivery_with_access_token(self):
        steam_monitor.WEBHOOK_PROVIDER = "ntfy"
        steam_monitor.WEBHOOK_URL = "https://ntfy.example.test/private-topic"
        steam_monitor.NTFY_ACCESS_TOKEN = "tk_private"
        response = FakeResponse(200)
        with patch.object(steam_monitor.WEBHOOK_SESSION, "post", return_value=response) as post:
            result = steam_monitor.send_webhook("Steam title", "Steam body", "status", ntfy_priority=4, ntfy_tags="video_game,steam")

        self.assertEqual(result, 0)
        self.assertEqual(post.call_args.kwargs["data"], b"Steam body")
        self.assertEqual(post.call_args.kwargs["params"], {"title": "Steam title", "priority": 4, "tags": "video_game,steam"})
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer tk_private")
        self.assertEqual(post.call_args.kwargs["headers"]["Content-Type"], "text/plain; charset=utf-8")

    # Verifies a rejected ntfy image attachment is retried once as text
    def test_ntfy_image_failure_falls_back_to_text(self):
        steam_monitor.WEBHOOK_PROVIDER = "ntfy"
        steam_monitor.WEBHOOK_URL = "https://ntfy.example.test/private-topic"
        steam_monitor.NTFY_IMAGES = True
        responses = [FakeResponse(413), FakeResponse(200)]
        image_url = "https://cdn.akamai.steamstatic.com/steam/apps/10/header.jpg"
        with patch.object(steam_monitor, "build_ntfy_image", return_value=b"jpeg-data"), patch.object(steam_monitor.WEBHOOK_SESSION, "post", side_effect=responses) as post:
            result = steam_monitor.send_webhook("Steam title", "Steam body", "game", force=True, image_url=image_url)

        self.assertEqual(result, 0)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args_list[0].kwargs["headers"]["Content-Type"], "image/jpeg")
        self.assertEqual(post.call_args_list[1].kwargs["data"], b"Steam body")

    # Verifies webhook templates, transformations and dynamic headers share placeholders
    def test_custom_template_transforms_and_headers(self):
        steam_monitor.WEBHOOK_TRANSFORMS = [("title", "upper")]
        steam_monitor.WEBHOOK_HEADERS = {"X-Alert-Title": "{title}"}
        steam_monitor.WEBHOOK_TEMPLATE = {"content": "{title}", "allowed_mentions": {"parse": ["everyone"]}}
        response = FakeResponse(200)
        with patch.object(steam_monitor.WEBHOOK_SESSION, "post", return_value=response) as post:
            result = steam_monitor.send_webhook("Mixed title", "Body", "game", force=True)

        self.assertEqual(result, 0)
        self.assertEqual(post.call_args.kwargs["json"]["content"], "MIXED TITLE")
        self.assertEqual(post.call_args.kwargs["json"]["allowed_mentions"], {"parse": []})
        self.assertEqual(post.call_args.kwargs["headers"]["X-Alert-Title"], "MIXED TITLE")

    # Verifies webhook rate-limit delays are capped before retrying
    def test_rate_limit_retry_is_bounded(self):
        sleeps = []
        responses = [FakeResponse(429, headers={"Retry-After": "3600"}), FakeResponse(204)]
        with patch.object(steam_monitor.WEBHOOK_SESSION, "post", side_effect=responses) as post:
            result = steam_monitor.send_webhook("Title", "Body", "status", sleeper=sleeps.append)

        self.assertEqual(result, 0)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(sleeps, [steam_monitor.WEBHOOK_MAX_RETRY_AFTER_SECONDS])

    # Verifies email and webhook delivery decisions remain independent
    def test_notification_channels_are_independent(self):
        with patch.object(steam_monitor, "send_email", return_value=0) as email, patch.object(steam_monitor, "send_webhook", return_value=0) as webhook:
            attempted = steam_monitor.send_notification_channels("status", "Title", "Body", email_enabled=False, webhook_enabled=True)

        self.assertEqual(attempted, (False, True))
        email.assert_not_called()
        webhook.assert_called_once_with("Title", "Body", "status", force=True, image_url="", ntfy_priority=0, ntfy_tags="")

    # Verifies invalid custom headers are rejected before any request is attempted
    def test_invalid_headers_are_rejected(self):
        steam_monitor.WEBHOOK_HEADERS = {"Bad\nName": "value"}
        with patch.object(steam_monitor.WEBHOOK_SESSION, "post") as post:
            result = steam_monitor.send_webhook("Title", "Body", "status")

        self.assertEqual(result, 1)
        post.assert_not_called()

    # Verifies private webhook and Steam API values are removed from error-shaped text
    def test_secret_redaction(self):
        steam_monitor.STEAM_API_KEY = "A" * 32
        steam_monitor.WEBHOOK_URL = "https://discord.com/api/webhooks/123/private-token"
        text = f"failed https://api.steampowered.com/test?key={'A' * 32} WEBHOOK_URL={steam_monitor.WEBHOOK_URL}"

        redacted = steam_monitor.sanitize_error_text(text)

        self.assertNotIn("A" * 32, redacted)
        self.assertNotIn("private-token", redacted)
        self.assertIn("<redacted>", redacted)

    # Verifies image URLs are limited to expected Steam HTTPS hosts
    def test_steam_image_allowlist(self):
        self.assertTrue(steam_monitor.steam_image_url_is_allowed("https://cdn.akamai.steamstatic.com/steam/apps/10/header.jpg"))
        self.assertTrue(steam_monitor.steam_image_url_is_allowed("https://avatars.akamai.steamstatic.com/avatar_full.jpg"))
        self.assertFalse(steam_monitor.steam_image_url_is_allowed("https://example.test/header.jpg"))
        self.assertFalse(steam_monitor.steam_image_url_is_allowed("http://cdn.akamai.steamstatic.com/steam/apps/10/header.jpg"))
        self.assertEqual(steam_monitor.normalize_steam_image_url("avatars.steamstatic.com/avatar_full.jpg"), "https://avatars.steamstatic.com/avatar_full.jpg")
        self.assertEqual(steam_monitor.normalize_steam_image_url("//avatars.steamstatic.com/avatar_full.jpg"), "https://avatars.steamstatic.com/avatar_full.jpg")
        self.assertEqual(steam_monitor.normalize_steam_image_url("https://example.test/header.jpg"), "")

    # Verifies one-run CLI overrides enable only the selected webhook choices
    def test_runtime_overrides(self):
        args = argparse.Namespace(
            webhook_provider="ntfy",
            webhook_url="https://ntfy.example.test/private-topic",
            webhook_enabled=None,
            webhook_active=True,
            webhook_inactive=None,
            webhook_status=None,
            webhook_game_changes=None,
            webhook_level_xp=None,
            webhook_friends=None,
            webhook_games=None,
            webhook_name_change=None,
            webhook_errors=False,
        )
        parser = Mock()
        steam_monitor.apply_webhook_cli_overrides(args, parser)

        self.assertEqual(steam_monitor.WEBHOOK_PROVIDER, "ntfy")
        self.assertEqual(steam_monitor.WEBHOOK_URL, "https://ntfy.example.test/private-topic")
        self.assertTrue(steam_monitor.WEBHOOK_ENABLED)
        self.assertTrue(steam_monitor.WEBHOOK_ACTIVE_NOTIFICATION)
        self.assertFalse(steam_monitor.WEBHOOK_ERROR_NOTIFICATION)
        parser.error.assert_not_called()

    # Verifies a known URL corrects a mismatched configured provider unless CLI explicitly overrides it
    def test_runtime_provider_detection_corrects_config_mismatch(self):
        args = argparse.Namespace(
            webhook_provider=None,
            webhook_url="https://ntfy.sh/private-topic",
            webhook_enabled=None,
            webhook_active=None,
            webhook_inactive=None,
            webhook_status=None,
            webhook_game_changes=None,
            webhook_level_xp=None,
            webhook_friends=None,
            webhook_games=None,
            webhook_name_change=None,
            webhook_errors=None,
        )
        parser = Mock()
        with patch("builtins.print") as output:
            steam_monitor.apply_webhook_cli_overrides(args, parser)

        self.assertEqual(steam_monitor.WEBHOOK_PROVIDER, "ntfy")
        self.assertTrue(any("Using ntfy" in str(call.args) for call in output.call_args_list))
        parser.error.assert_not_called()
        with patch.object(steam_monitor.WEBHOOK_SESSION, "post", return_value=FakeResponse(200)) as post:
            self.assertEqual(steam_monitor.send_webhook("Steam title", "Steam body", "status", force=True), 0)
        self.assertEqual(post.call_args.kwargs["data"], b"Steam body")
        self.assertNotIn("json", post.call_args.kwargs)

    # Verifies scheme-less Steam avatars become valid Discord thumbnail URLs
    def test_discord_payload_normalizes_scheme_less_steam_avatar(self):
        response = FakeResponse(204)
        with patch.object(steam_monitor.WEBHOOK_SESSION, "post", return_value=response) as post:
            result = steam_monitor.send_webhook("Status title", "Status body", "status", image_url="avatars.steamstatic.com/avatar_full.jpg")

        self.assertEqual(result, 0)
        self.assertEqual(post.call_args.kwargs["json"]["embeds"][0]["thumbnail"]["url"], "https://avatars.steamstatic.com/avatar_full.jpg")

    # Verifies test webhook delivery does not require a Steam target or API key
    def test_send_test_webhook_cli_is_steam_independent(self):
        delivery = Mock(return_value=0)
        with patch.object(steam_monitor.sys, "argv", ["steam_monitor.py", "--send-test-webhook", "--env-file", "none"]), patch.object(steam_monitor, "check_internet", return_value=True), patch.object(steam_monitor, "send_webhook", delivery), patch.object(steam_monitor, "clear_screen"), patch.object(steam_monitor.signal, "signal"), self.assertRaises(SystemExit) as exit_info:
            steam_monitor.main()

        self.assertEqual(exit_info.exception.code, 0)
        delivery.assert_called_once_with("Steam Monitor test", "Your webhook alerts are set up correctly.", "status", force=True)

    # Verifies long ntfy messages stay below the server attachment boundary with a visible truncation marker
    def test_ntfy_message_stays_below_attachment_boundary(self):
        title, message = steam_monitor.build_ntfy_webhook_message("Title", ("a" * steam_monitor.NTFY_MESSAGE_LIMIT_BYTES) + "\U0001f3ae")
        self.assertEqual(title, "Title")
        self.assertTrue(message.endswith(steam_monitor.NTFY_TRUNCATION_SUFFIX))
        self.assertLessEqual(len(message.encode("utf-8")), steam_monitor.NTFY_MESSAGE_LIMIT_BYTES)
        self.assertLess(len(message.encode("utf-8")), 4096)
        self.assertNotIn("\ufffd", message)


if __name__ == "__main__":
    unittest.main()

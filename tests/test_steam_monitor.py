import unittest
from unittest.mock import Mock, patch

import steam_monitor


class ResolveSteamCommunityUrlTests(unittest.TestCase):
    # Builds a mocked HTTP response for resolver tests
    def make_response(self, status_code=200, payload=None, headers=None):
        response = Mock()
        response.status_code = status_code
        response.headers = headers or {}
        response.json.return_value = payload or {}
        return response

    # Verifies that numeric profile URLs are resolved without an HTTP request
    def test_resolves_numeric_profile_url_locally(self):
        with patch.object(steam_monitor.req, "get") as get_mock:
            result = steam_monitor.resolve_steam_community_url("https://steamcommunity.com/profiles/76561197960265740/", "test-key")

        self.assertEqual(result, 76561197960265740)
        get_mock.assert_not_called()

    # Verifies that Steam3 profile URLs are resolved without an HTTP request
    def test_resolves_steam3_profile_url_locally(self):
        with patch.object(steam_monitor.req, "get") as get_mock:
            result = steam_monitor.resolve_steam_community_url("https://steamcommunity.com/profiles/[U:1:12]/", "test-key")

        self.assertEqual(result, 76561197960265740)
        get_mock.assert_not_called()

    # Verifies that Steam invite URLs are decoded without an HTTP request
    def test_resolves_steam_invite_url_locally(self):
        with patch.object(steam_monitor.req, "get") as get_mock:
            result = steam_monitor.resolve_steam_community_url("https://steamcommunity.com/user/cv-dgb/", "test-key")

        self.assertEqual(result, 76561197960389184)
        get_mock.assert_not_called()

    # Verifies that vanity profile URLs use the official Steam Web API
    def test_resolves_vanity_url_through_web_api(self):
        response = self.make_response(payload={"response": {"steamid": "76561197960265740", "success": 1}})
        with patch.object(steam_monitor.req, "get", return_value=response) as get_mock:
            result = steam_monitor.resolve_steam_community_url("https://steamcommunity.com/id/misiektoja/", "test-key")

        self.assertEqual(result, 76561197960265740)
        get_mock.assert_called_once_with("https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/", params={"key": "test-key", "vanityurl": "misiektoja", "url_type": 1}, timeout=30)

    # Verifies that API no-match responses produce a useful resolver error
    def test_reports_unresolved_vanity_url(self):
        response = self.make_response(payload={"response": {"success": 42, "message": "No match"}})
        with patch.object(steam_monitor.req, "get", return_value=response):
            with self.assertRaisesRegex(ValueError, "No match"):
                steam_monitor.resolve_steam_community_url("https://steamcommunity.com/id/does-not-exist/", "test-key")

    # Verifies that malformed API payloads produce a controlled resolver error
    def test_reports_invalid_api_response(self):
        response = self.make_response(payload={"response": None})
        with patch.object(steam_monitor.req, "get", return_value=response):
            with self.assertRaisesRegex(ValueError, "invalid response"):
                steam_monitor.resolve_steam_community_url("https://steamcommunity.com/id/misiektoja/", "test-key")

    # Verifies that API rate limits include retry guidance when available
    def test_reports_api_rate_limit(self):
        response = self.make_response(status_code=429, headers={"Retry-After": "60"})
        with patch.object(steam_monitor.req, "get", return_value=response):
            with self.assertRaisesRegex(ValueError, "Retry after 60"):
                steam_monitor.resolve_steam_community_url("https://steamcommunity.com/id/misiektoja/", "test-key")

    # Verifies that non-Steam and group URLs are rejected before any request
    def test_rejects_unsupported_urls(self):
        with self.assertRaisesRegex(ValueError, "Invalid Steam community URL"):
            steam_monitor.resolve_steam_community_url("https://example.com/id/misiektoja/", "test-key")
        with self.assertRaisesRegex(ValueError, "Only Steam user profile URLs are supported"):
            steam_monitor.resolve_steam_community_url("https://steamcommunity.com/groups/Valve/", "test-key")


if __name__ == "__main__":
    unittest.main()

"""
Tests for cascade_rest.publishing module

Tests publishing, workflow, and subscriber operations
"""

import unittest
from unittest.mock import patch, MagicMock
import pytest

from cascade_rest.publishing import (
    publish_asset,
    check_out_asset,
    check_in_asset,
    list_subscribers_single_asset,
)


class TestPublishingOperations(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.cms_path = "https://cms.example.com"
        self.auth = {"u": "testuser", "p": "testpass"}

        self.sample_success_response = {
            "success": "true",
            "message": "Operation completed successfully",
        }

        self.sample_checkout_response = {
            "checkOutReturn": {
                "success": "true",
                "workingCopyIdentifier": {"id": "working123", "type": "page"},
            }
        }

        self.sample_subscribers_response = {
            "listSubscribersReturn": {
                "success": "true",
                "subscribers": {
                    "assetIdentifier": [
                        {"id": "user1", "type": "user"},
                        {"id": "user2", "type": "user"},
                    ]
                },
            }
        }

    @patch("cascade_rest.publishing.requests.post")
    def test_publish_asset_basic(self, mock_post):
        """Test basic asset publishing"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        result = publish_asset(self.cms_path, self.auth, "page", "test123")

        # Verify API call
        expected_payload = {"publishInformation": {"unpublish": False}}

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/publish/page/test123",
            params=self.auth,
            json=expected_payload,
        )

        # Verify result
        self.assertEqual(result, self.sample_success_response)

    @patch("cascade_rest.publishing.requests.post")
    def test_publish_asset_with_destinations(self, mock_post):
        """Test asset publishing with specific destinations"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        destinations = ["dest1", "dest2", "dest3"]

        result = publish_asset(
            self.cms_path, self.auth, "page", "test123", destinations=destinations
        )

        # Verify API call includes destinations
        expected_payload = {
            "publishInformation": {
                "unpublish": False,
                "destinations": [
                    {"id": "dest1", "type": "destination"},
                    {"id": "dest2", "type": "destination"},
                    {"id": "dest3", "type": "destination"},
                ],
            }
        }

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/publish/page/test123",
            params=self.auth,
            json=expected_payload,
        )

    @patch("cascade_rest.publishing.requests.post")
    def test_unpublish_asset(self, mock_post):
        """Test asset unpublishing"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        result = publish_asset(
            self.cms_path, self.auth, "page", "test123", unpublish=True
        )

        # Verify unpublish flag is set
        expected_payload = {"publishInformation": {"unpublish": True}}

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/publish/page/test123",
            params=self.auth,
            json=expected_payload,
        )

    @patch("cascade_rest.publishing.requests.post")
    def test_unpublish_with_destinations(self, mock_post):
        """Test unpublishing with specific destinations"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        destinations = ["dest1"]

        result = publish_asset(
            self.cms_path,
            self.auth,
            "page",
            "test123",
            destinations=destinations,
            unpublish=True,
        )

        # Verify both unpublish and destinations are set
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        publish_info = payload["publishInformation"]

        self.assertTrue(publish_info["unpublish"])
        self.assertEqual(len(publish_info["destinations"]), 1)
        self.assertEqual(publish_info["destinations"][0]["id"], "dest1")

    @patch("cascade_rest.publishing.requests.post")
    def test_check_out_asset(self, mock_post):
        """Test asset checkout"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_checkout_response
        mock_post.return_value = mock_response

        result = check_out_asset(self.cms_path, self.auth, "page", "test123")

        # Verify API call
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/checkOut/page/test123", params=self.auth
        )

        # Verify result
        self.assertEqual(result, self.sample_checkout_response)

    @patch("cascade_rest.publishing.requests.post")
    def test_check_in_asset_with_comments(self, mock_post):
        """Test asset checkin with comments"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        comments = "Fixed typo in title"

        result = check_in_asset(self.cms_path, self.auth, "page", "test123", comments)

        # Verify API call includes comments
        expected_payload = {"comments": comments}

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/checkIn/page/test123",
            params=self.auth,
            json=expected_payload,
        )

    @patch("cascade_rest.publishing.requests.post")
    def test_check_in_asset_without_comments(self, mock_post):
        """Test asset checkin without comments"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        result = check_in_asset(self.cms_path, self.auth, "page", "test123")

        # Verify API call with empty payload
        expected_payload = {}

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/checkIn/page/test123",
            params=self.auth,
            json=expected_payload,
        )

    @patch("cascade_rest.publishing.requests.post")
    def test_check_in_asset_empty_comments(self, mock_post):
        """Test asset checkin with empty string comments"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        result = check_in_asset(self.cms_path, self.auth, "page", "test123", "")

        # Should result in empty payload when comments are empty string
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        self.assertEqual(payload, {})

    @patch("cascade_rest.publishing.requests.post")
    def test_list_subscribers_single_asset(self, mock_post):
        """Test listing asset subscribers"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_subscribers_response
        mock_post.return_value = mock_response

        result = list_subscribers_single_asset(
            self.cms_path, self.auth, "page", "test123"
        )

        # Verify API call
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/listSubscribers/page/test123", params=self.auth
        )

        # Verify result
        self.assertEqual(result, self.sample_subscribers_response)

    def test_list_subscribers_empty_asset_id(self):
        """Test listing subscribers with empty asset ID"""
        result = list_subscribers_single_asset(self.cms_path, self.auth, "page", "")

        # Should return False for empty asset ID
        self.assertFalse(result)

    def test_list_subscribers_none_asset_id(self):
        """Test listing subscribers with None asset ID"""
        result = list_subscribers_single_asset(self.cms_path, self.auth, "page", "")  # type: ignore

        # Should return False for None asset ID
        self.assertFalse(result)


class TestParametrizedPublishing:
    """Pytest-style parametrized tests for publishing operations"""

    @pytest.mark.parametrize(
        "asset_type,asset_id,expected_url",
        [
            ("page", "123", "https://cms.example.com/api/v1/publish/page/123"),
            ("file", "456", "https://cms.example.com/api/v1/publish/file/456"),
            ("folder", "789", "https://cms.example.com/api/v1/publish/folder/789"),
        ],
    )
    def test_publish_url_construction(self, asset_type, asset_id, expected_url):
        """Test URL construction for publishing different asset types"""
        cms_path = "https://cms.example.com"
        auth = {"u": "user", "p": "pass"}

        with patch("cascade_rest.publishing.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"success": "true"}
            mock_post.return_value = mock_response

            publish_asset(cms_path, auth, asset_type, asset_id)

            mock_post.assert_called_once()
            call_args = mock_post.call_args
            self.assertEqual(call_args[0][0], expected_url)

    @pytest.mark.parametrize(
        "unpublish,expected_flag",
        [
            (True, True),
            (False, False),
            (None, False),  # Test default behavior
        ],
    )
    def test_publish_unpublish_flag(self, unpublish, expected_flag):
        """Test unpublish flag behavior"""
        cms_path = "https://cms.example.com"
        auth = {"u": "user", "p": "pass"}

        with patch("cascade_rest.publishing.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"success": "true"}
            mock_post.return_value = mock_response

            if unpublish is None:
                publish_asset(cms_path, auth, "page", "123")
            else:
                publish_asset(cms_path, auth, "page", "123", unpublish=unpublish)

            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["publishInformation"]["unpublish"] == expected_flag

    @pytest.mark.parametrize(
        "destinations,expected_count",
        [
            (None, 0),
            ([], 0),
            (["dest1"], 1),
            (["dest1", "dest2"], 2),
            (["dest1", "dest2", "dest3"], 3),
        ],
    )
    def test_destinations_parameter(self, destinations, expected_count):
        """Test destinations parameter handling"""
        cms_path = "https://cms.example.com"
        auth = {"u": "user", "p": "pass"}

        with patch("cascade_rest.publishing.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"success": "true"}
            mock_post.return_value = mock_response

            publish_asset(cms_path, auth, "page", "123", destinations=destinations)

            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            publish_info = payload["publishInformation"]

            if expected_count == 0:
                assert "destinations" not in publish_info
            else:
                assert len(publish_info["destinations"]) == expected_count
                # Check that all destinations have correct structure
                for dest in publish_info["destinations"]:
                    assert "id" in dest
                    assert dest["type"] == "destination"


class TestPublishingErrorHandling(unittest.TestCase):
    """Test error scenarios for publishing operations"""

    def setUp(self):
        self.cms_path = "https://cms.example.com"
        self.auth = {"u": "user", "p": "pass"}

    @patch("cascade_rest.publishing.requests.post")
    def test_publish_network_error(self, mock_post):
        """Test publishing with network error"""
        import requests

        mock_post.side_effect = requests.ConnectionError("Network error")

        with self.assertRaises(requests.ConnectionError):
            publish_asset(self.cms_path, self.auth, "page", "test123")

    @patch("cascade_rest.publishing.requests.post")
    def test_checkout_unauthorized_error(self, mock_post):
        """Test checkout with unauthorized error"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "success": "false",
            "message": "Unauthorized",
        }
        mock_post.return_value = mock_response

        result = check_out_asset(self.cms_path, self.auth, "page", "test123")

        # Should still return the response even on error status
        self.assertEqual(result["success"], "false")

    @patch("cascade_rest.publishing.requests.post")
    def test_checkin_with_json_error(self, mock_post):
        """Test checkin with JSON parsing error"""
        import json

        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response

        with self.assertRaises(json.JSONDecodeError):
            check_in_asset(self.cms_path, self.auth, "page", "test123")


class TestWorkflowOperations(unittest.TestCase):
    """Test workflow-related publishing operations"""

    def setUp(self):
        self.cms_path = "https://cms.example.com"
        self.auth = {"u": "testuser", "p": "testpass"}

    @patch("cascade_rest.publishing.requests.post")
    def test_checkout_checkin_workflow(self, mock_post):
        """Test complete checkout-checkin workflow"""
        # Mock responses for checkout and checkin
        checkout_response = {
            "checkOutReturn": {
                "success": "true",
                "workingCopyIdentifier": {"id": "working123", "type": "page"},
            }
        }

        checkin_response = {"success": "true", "message": "Checked in successfully"}

        mock_post.side_effect = [
            MagicMock(json=lambda: checkout_response),
            MagicMock(json=lambda: checkin_response),
        ]

        # Perform checkout
        checkout_result = check_out_asset(self.cms_path, self.auth, "page", "test123")

        # Perform checkin
        checkin_result = check_in_asset(
            self.cms_path, self.auth, "page", "test123", "Updated content"
        )

        # Verify both operations were called
        self.assertEqual(mock_post.call_count, 2)

        # Verify checkout result
        self.assertEqual(checkout_result, checkout_response)

        # Verify checkin result
        self.assertEqual(checkin_result, checkin_response)


if __name__ == "__main__":
    unittest.main(verbosity=2)

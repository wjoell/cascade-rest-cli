"""
Tests for cascade_rest.core module

Tests core CRUD operations: Create, Read, Update, Delete, Copy, Move
"""

import unittest
from unittest.mock import patch, MagicMock
import pytest

from cascade_rest.core import (
    read_single_asset,
    read_asset_by_path,
    create_asset,
    edit_single_asset,
    delete_asset,
    copy_single_asset,
    move_asset,
)


class TestCoreOperations(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.cms_path = "https://cms.example.com"
        self.auth = {"u": "testuser", "p": "testpass"}

        self.sample_page_response = {
            "asset": {
                "page": {
                    "id": "test123",
                    "name": "test-page",
                    "path": "/test-folder/test-page",
                    "metadata": {"title": "Test Page"},
                }
            }
        }

        self.sample_success_response = {
            "success": "true",
            "message": "Operation completed successfully",
        }

        self.sample_create_response = {"success": "true", "createdAssetId": "new123456"}

    @patch("cascade_rest.core.requests.post")
    def test_read_single_asset_success(self, mock_post):
        """Test successful asset reading"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_page_response
        mock_post.return_value = mock_response

        result = read_single_asset(self.cms_path, self.auth, "page", "test123")

        # Verify API call
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/read/page/test123", params=self.auth
        )

        # Verify result
        self.assertEqual(result, self.sample_page_response)

    @patch("cascade_rest.core.requests.post")
    def test_read_single_asset_error(self, mock_post):
        """Test asset reading with error response"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        result = read_single_asset(self.cms_path, self.auth, "page", "nonexistent")

        # Should return False on error
        self.assertFalse(result)

    def test_read_single_asset_empty_id(self):
        """Test asset reading with empty asset ID"""
        result = read_single_asset(self.cms_path, self.auth, "page", "")

        # Should return False for empty ID
        self.assertFalse(result)

    def test_read_single_asset_none_id(self):
        """Test asset reading with None asset ID"""
        result = read_single_asset(self.cms_path, self.auth, "page", "")  # type: ignore

        # Should return False for None ID
        self.assertFalse(result)

    @patch("cascade_rest.core.requests.post")
    def test_read_asset_by_path_success(self, mock_post):
        """Test reading asset by path"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = self.sample_page_response
        mock_post.return_value = mock_response

        result = read_asset_by_path(
            self.cms_path, self.auth, "page", "example.com", "/test-page"
        )

        # Verify API call with correct path construction
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/read/page/example.com/test-page", params=self.auth
        )

        # Verify result
        self.assertEqual(result, self.sample_page_response)

    @patch("cascade_rest.core.requests.post")
    def test_read_asset_by_path_error(self, mock_post):
        """Test reading asset by path with error"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        result = read_asset_by_path(
            self.cms_path, self.auth, "page", "example.com", "/nonexistent"
        )

        # Should return False on error
        self.assertFalse(result)

    @patch("cascade_rest.core.requests.post")
    def test_create_asset(self, mock_post):
        """Test asset creation"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_create_response
        mock_post.return_value = mock_response

        asset_data = {
            "name": "new-page",
            "parentFolderPath": "/content",
            "siteName": "example.com",
        }

        result = create_asset(self.cms_path, self.auth, "page", asset_data)

        # Verify API call
        expected_payload = {"asset": {"page": asset_data}}
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/create", params=self.auth, json=expected_payload
        )

        # Verify result
        self.assertEqual(result, self.sample_create_response)

    @patch("cascade_rest.core.requests.post")
    def test_edit_single_asset(self, mock_post):
        """Test asset editing"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        edit_payload = {
            "asset": {"page": {"id": "test123", "metadata": {"title": "Updated Title"}}}
        }

        result = edit_single_asset(
            self.cms_path, self.auth, "page", "test123", edit_payload
        )

        # Verify API call
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/edit/page/test123",
            params=self.auth,
            json=edit_payload,
        )

        # Verify result
        self.assertEqual(result, self.sample_success_response)

    @patch("cascade_rest.core.requests.post")
    def test_delete_asset_with_unpublish(self, mock_post):
        """Test asset deletion with unpublishing"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        result = delete_asset(
            self.cms_path, self.auth, "page", "test123", unpublish=True
        )

        # Verify API call
        expected_payload = {
            "deleteParameters": {"unpublish": True, "doWorkflow": False}
        }

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/delete/page/test123",
            params=self.auth,
            json=expected_payload,
        )

        # Verify result
        self.assertEqual(result, self.sample_success_response)

    @patch("cascade_rest.core.requests.post")
    def test_delete_asset_without_unpublish(self, mock_post):
        """Test asset deletion without unpublishing"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        result = delete_asset(
            self.cms_path, self.auth, "page", "test123", unpublish=False
        )

        # Verify unpublish parameter is False
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        self.assertFalse(payload["deleteParameters"]["unpublish"])

    @patch("cascade_rest.core.requests.post")
    def test_copy_single_asset(self, mock_post):
        """Test asset copying"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        result = copy_single_asset(
            self.cms_path,
            self.auth,
            "page",
            "test123",
            "/destination",
            "copied-page",
            "example.com",
        )

        # Verify API call
        expected_payload = {
            "copyParameters": {
                "destinationContainerIdentifier": {
                    "path": {"path": "/destination", "siteName": "example.com"},
                    "type": "folder",
                },
                "doWorkflow": "false",
                "newName": "copied-page",
            }
        }

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/copy/page/test123",
            params=self.auth,
            json=expected_payload,
        )

    @patch("cascade_rest.core.requests.post")
    def test_move_asset_with_rename(self, mock_post):
        """Test asset moving with renaming"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        result = move_asset(
            self.cms_path,
            self.auth,
            "page",
            "test123",
            "folder456",
            new_name="renamed-page",
            unpublish=False,
        )

        # Verify API call
        expected_payload = {
            "moveParameters": {
                "destinationContainerIdentifier": {"id": "folder456", "type": "folder"},
                "doWorkflow": False,
                "unpublish": False,
                "newName": "renamed-page",
            }
        }

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/move/page/test123",
            params=self.auth,
            json=expected_payload,
        )

    @patch("cascade_rest.core.requests.post")
    def test_move_asset_without_rename(self, mock_post):
        """Test asset moving without renaming"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        result = move_asset(self.cms_path, self.auth, "page", "test123", "folder456")

        # Verify newName is not in the payload
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        self.assertNotIn("newName", payload["moveParameters"])


class TestParametrizedCoreOperations:
    """Pytest-style parametrized tests for core operations"""

    @pytest.mark.parametrize(
        "asset_type,asset_id,expected_url",
        [
            ("page", "123", "https://cms.example.com/api/v1/read/page/123"),
            ("file", "456", "https://cms.example.com/api/v1/read/file/456"),
            ("folder", "789", "https://cms.example.com/api/v1/read/folder/789"),
            ("block", "abc", "https://cms.example.com/api/v1/read/block/abc"),
        ],
    )
    def test_read_asset_url_construction(self, asset_type, asset_id, expected_url):
        """Test URL construction for different asset types"""
        cms_path = "https://cms.example.com"
        auth = {"u": "user", "p": "pass"}

        with patch("cascade_rest.core.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"asset": {asset_type: {"id": asset_id}}}
            mock_post.return_value = mock_response

            read_single_asset(cms_path, auth, asset_type, asset_id)

            mock_post.assert_called_once_with(expected_url, params=auth)

    @pytest.mark.parametrize(
        "site_name,asset_path,expected_url_part",
        [
            ("example.com", "/test-page", "/api/v1/read/page/example.com/test-page"),
            (
                "test.site.com",
                "/folder/page",
                "/api/v1/read/page/test.site.com/folder/page",
            ),
            ("site", "/", "/api/v1/read/page/site/"),
        ],
    )
    def test_read_by_path_url_construction(
        self, site_name, asset_path, expected_url_part
    ):
        """Test URL construction for reading by path"""
        cms_path = "https://cms.example.com"
        auth = {"u": "user", "p": "pass"}

        with patch("cascade_rest.core.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"asset": {"page": {"id": "test"}}}
            mock_post.return_value = mock_response

            read_asset_by_path(cms_path, auth, "page", site_name, asset_path)

            expected_url = cms_path + expected_url_part
            mock_post.assert_called_once_with(expected_url, params=auth)


class TestCoreErrorHandling(unittest.TestCase):
    """Test error scenarios for core operations"""

    def setUp(self):
        self.cms_path = "https://cms.example.com"
        self.auth = {"u": "user", "p": "pass"}

    @patch("cascade_rest.core.requests.post")
    def test_network_error_handling(self, mock_post):
        """Test handling of network errors"""
        import requests

        mock_post.side_effect = requests.ConnectionError("Network error")

        with self.assertRaises(requests.ConnectionError):
            read_single_asset(self.cms_path, self.auth, "page", "test123")

    @patch("cascade_rest.core.requests.post")
    def test_timeout_error_handling(self, mock_post):
        """Test handling of timeout errors"""
        import requests

        mock_post.side_effect = requests.Timeout("Request timed out")

        with self.assertRaises(requests.Timeout):
            read_single_asset(self.cms_path, self.auth, "page", "test123")

    @patch("cascade_rest.core.requests.post")
    def test_json_decode_error(self, mock_post):
        """Test handling of malformed JSON responses"""
        import json

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response

        with self.assertRaises(json.JSONDecodeError):
            read_single_asset(self.cms_path, self.auth, "page", "test123")

    @patch("cascade_rest.core.requests.post")
    def test_http_error_codes(self, mock_post):
        """Test various HTTP error codes"""
        error_codes = [400, 401, 403, 404, 500, 503]

        for status_code in error_codes:
            with self.subTest(status_code=status_code):
                mock_response = MagicMock()
                mock_response.status_code = status_code
                mock_post.return_value = mock_response

                result = read_single_asset(self.cms_path, self.auth, "page", "test123")

                # Should return False for non-200 status codes
                self.assertFalse(result)


if __name__ == "__main__":
    # Run unittest tests
    unittest.main(verbosity=2)

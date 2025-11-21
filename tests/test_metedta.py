"""
Tests for cascade_rest.metadata module

Tests metadata field operations, tags, and dynamic fields
"""

import unittest
from unittest.mock import patch, MagicMock
import pytest

from cascade_rest.metadata import (
    read_single_asset_metadata_value,
    set_single_asset_metadata_value,
    update_single_asset_dynamic_metadata_value,
    set_or_replace_single_asset_tag,
    get_dynamic_field,
    METADATA_ALLOWED_KEYS,
)


class TestMetadataOperations(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.cms_path = "https://cms.example.com"
        self.auth = {"u": "testuser", "p": "testpass"}

        self.sample_page_with_metadata = {
            "asset": {
                "page": {
                    "id": "test123",
                    "name": "test-page",
                    "metadata": {
                        "title": "Test Page Title",
                        "displayName": "Test Display Name",
                        "summary": "Test summary content",
                        "author": "Test Author",
                        "keywords": "test, page, metadata",
                        "dynamicFields": [
                            {"name": "category", "fieldValues": [{"value": "news"}]},
                            {"name": "priority", "fieldValues": [{"value": "high"}]},
                            {"name": "empty-field", "fieldValues": []},
                        ],
                    },
                    "tags": [{"name": "existing-tag"}, {"name": "another-tag"}],
                }
            }
        }

        self.sample_success_response = {
            "success": "true",
            "message": "Operation completed successfully",
        }

    def test_metadata_allowed_keys_constant(self):
        """Test that METADATA_ALLOWED_KEYS contains expected values"""
        expected_keys = [
            "displayName",
            "title",
            "summary",
            "teaser",
            "keywords",
            "metaDescription",
            "author",
        ]

        self.assertEqual(METADATA_ALLOWED_KEYS, expected_keys)

        # Test that all keys are strings
        for key in METADATA_ALLOWED_KEYS:
            self.assertIsInstance(key, str)

    @patch("cascade_rest.metadata.requests.post")
    def test_read_single_asset_metadata_value(self, mock_post):
        """Test reading a metadata field value"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_page_with_metadata
        mock_post.return_value = mock_response

        result = read_single_asset_metadata_value(
            self.cms_path, self.auth, "page", "test123", "title"
        )

        # Verify API call
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/read/page/test123", params=self.auth
        )

        # Verify result
        self.assertEqual(result, "Test Page Title")

    @patch("cascade_rest.metadata.requests.post")
    def test_read_metadata_with_tuple_asset_id(self, mock_post):
        """Test reading metadata with tuple asset ID"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_page_with_metadata
        mock_post.return_value = mock_response

        # Pass asset as tuple (common pattern in original code)
        result = read_single_asset_metadata_value(
            self.cms_path, self.auth, "page", ("test123", "extra"), "author"
        )

        # Should extract first element of tuple as asset ID
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/read/page/test123", params=self.auth
        )

        self.assertEqual(result, "Test Author")

    def test_read_metadata_invalid_field(self):
        """Test reading metadata with invalid field name"""
        result = read_single_asset_metadata_value(
            self.cms_path, self.auth, "page", "test123", "invalid_field"
        )

        # Should return False for invalid field names
        self.assertFalse(result)

    @patch("cascade_rest.metadata.requests.post")
    def test_set_single_asset_metadata_value_new_value(self, mock_post):
        """Test setting metadata value for empty field"""
        # Mock read response (first call)
        read_response = self.sample_page_with_metadata.copy()
        read_response["asset"]["page"]["metadata"]["summary"] = ""  # Empty field

        # Mock edit response (second call)
        edit_response = self.sample_success_response

        mock_post.side_effect = [
            MagicMock(json=lambda: read_response),
            MagicMock(json=lambda: edit_response),
        ]

        result = set_single_asset_metadata_value(
            self.cms_path, self.auth, "page", "test123", "summary", "New summary"
        )

        # Verify both read and edit calls were made
        self.assertEqual(mock_post.call_count, 2)

        # Verify edit call payload
        edit_call_args = mock_post.call_args_list[1]
        payload = edit_call_args[1]["json"]
        self.assertEqual(payload["asset"]["page"]["metadata"]["summary"], "New summary")

    @patch("cascade_rest.metadata.requests.post")
    def test_set_single_asset_metadata_value_update_existing(self, mock_post):
        """Test updating existing metadata value"""
        # Mock read and edit responses
        mock_post.side_effect = [
            MagicMock(json=lambda: self.sample_page_with_metadata),
            MagicMock(json=lambda: self.sample_success_response),
        ]

        result = set_single_asset_metadata_value(
            self.cms_path, self.auth, "page", "test123", "title", "Updated Title"
        )

        # Verify both calls were made
        self.assertEqual(mock_post.call_count, 2)

        # Verify the title was updated in the payload
        edit_call_args = mock_post.call_args_list[1]
        payload = edit_call_args[1]["json"]
        self.assertEqual(payload["asset"]["page"]["metadata"]["title"], "Updated Title")

    def test_set_metadata_invalid_field(self):
        """Test setting metadata with invalid field name"""
        result = set_single_asset_metadata_value(
            self.cms_path, self.auth, "page", "test123", "invalid_field", "value"
        )

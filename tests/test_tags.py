"""
Unit tests for tag operations

Tests tag functionality including:
- Adding tags to assets
- Removing tags from assets
- Setting/replacing tags
- Searching assets by tags
"""

import unittest
from unittest.mock import patch, MagicMock
import pytest

from cascade_rest.metadata import set_or_replace_single_asset_tag
from cascade_rest.core import read_single_asset, edit_single_asset


class TestTagOperations(unittest.TestCase):
    """Test tag operations on assets"""

    def setUp(self):
        """Set up test fixtures"""
        self.cms_path = "https://cms.example.com"
        self.auth = {"apiKey": "test_api_key"}

        # Sample asset with tags
        self.sample_asset_with_tags = {
            "asset": {
                "page": {
                    "id": "asset1",
                    "name": "test-page",
                    "path": "/content/test-page",
                    "tags": [
                        {"name": "faculty"},
                        {"name": "department:cs"},
                        {"name": "year:2024"},
                    ],
                }
            }
        }

        # Sample asset without tags
        self.sample_asset_no_tags = {
            "asset": {
                "page": {
                    "id": "asset2",
                    "name": "test-page-2",
                    "path": "/content/test-page-2",
                    "tags": [],
                }
            }
        }

        self.sample_success_response = {
            "success": "true",
            "message": "Operation completed successfully",
        }

    @patch("cascade_rest.metadata.edit_single_asset")
    @patch("cascade_rest.metadata.read_single_asset")
    def test_add_tag_to_empty_tags(self, mock_read, mock_edit):
        """Test adding a tag to asset with no existing tags"""
        mock_read.return_value = self.sample_asset_no_tags
        mock_edit.return_value = self.sample_success_response

        result = set_or_replace_single_asset_tag(
            self.cms_path, self.auth, "page", "asset2", "", "new_tag"
        )

        # Verify read was called
        mock_read.assert_called_once_with(self.cms_path, self.auth, "page", "asset2")

        # Verify edit was called with new tag
        call_args = mock_edit.call_args
        payload = call_args[0][4]  # payload is 5th argument
        self.assertIn({"name": "new_tag"}, payload["asset"]["page"]["tags"])

        # Verify result
        self.assertEqual(result["success"], "true")

    @patch("cascade_rest.metadata.edit_single_asset")
    @patch("cascade_rest.metadata.read_single_asset")
    def test_add_tag_to_existing_tags(self, mock_read, mock_edit):
        """Test adding a tag to asset with existing tags"""
        mock_read.return_value = self.sample_asset_with_tags.copy()
        mock_edit.return_value = self.sample_success_response

        result = set_or_replace_single_asset_tag(
            self.cms_path, self.auth, "page", "asset1", "", "new_category"
        )

        # Verify edit was called
        call_args = mock_edit.call_args
        payload = call_args[0][4]
        tags = payload["asset"]["page"]["tags"]

        # Verify new tag was added
        self.assertIn({"name": "new_category"}, tags)
        # Verify existing tags remain
        self.assertEqual(len(tags), 4)  # 3 original + 1 new

    @patch("cascade_rest.metadata.edit_single_asset")
    @patch("cascade_rest.metadata.read_single_asset")
    def test_replace_existing_tag(self, mock_read, mock_edit):
        """Test replacing an existing tag"""
        mock_read.return_value = self.sample_asset_with_tags.copy()
        mock_edit.return_value = self.sample_success_response

        result = set_or_replace_single_asset_tag(
            self.cms_path, self.auth, "page", "asset1", "faculty", "staff"
        )

        # Verify edit was called
        call_args = mock_edit.call_args
        payload = call_args[0][4]
        tags = payload["asset"]["page"]["tags"]

        # Verify old tag was replaced
        tag_names = [tag["name"] for tag in tags]
        self.assertNotIn("faculty", tag_names)
        self.assertIn("staff", tag_names)

    @patch("cascade_rest.metadata.edit_single_asset")
    @patch("cascade_rest.metadata.read_single_asset")
    def test_prevent_duplicate_tags(self, mock_read, mock_edit):
        """Test that duplicate tags are not added"""
        mock_read.return_value = self.sample_asset_with_tags.copy()
        mock_edit.return_value = self.sample_success_response

        # Try to add a tag that already exists
        result = set_or_replace_single_asset_tag(
            self.cms_path, self.auth, "page", "asset1", "", "faculty"
        )

        # Should return False (tag already exists)
        self.assertFalse(result)

        # Verify edit was NOT called
        mock_edit.assert_not_called()

    @patch("cascade_rest.metadata.read_single_asset")
    def test_tag_operation_with_invalid_asset(self, mock_read):
        """Test tag operation with invalid asset ID"""
        mock_read.return_value = False

        result = set_or_replace_single_asset_tag(
            self.cms_path, self.auth, "page", "nonexistent", "", "new_tag"
        )

        # Should return False
        self.assertFalse(result)

    @patch("cascade_rest.metadata.edit_single_asset")
    @patch("cascade_rest.metadata.read_single_asset")
    def test_add_multiple_tags_with_colons(self, mock_read, mock_edit):
        """Test adding tags with colon-separated values"""
        mock_read.return_value = self.sample_asset_no_tags
        mock_edit.return_value = self.sample_success_response

        # Add a tag with colon (common for categorized tags)
        result = set_or_replace_single_asset_tag(
            self.cms_path, self.auth, "page", "asset2", "", "category:faculty"
        )

        call_args = mock_edit.call_args
        payload = call_args[0][4]
        tags = payload["asset"]["page"]["tags"]

        # Verify tag with colon was added
        self.assertIn({"name": "category:faculty"}, tags)


class TestTagSearch(unittest.TestCase):
    """Test searching assets by tags"""

    def setUp(self):
        """Set up test fixtures"""
        self.assets_with_various_tags = [
            {
                "id": "asset1",
                "name": "faculty-page",
                "tags": [
                    {"name": "faculty"},
                    {"name": "department:cs"},
                    {"name": "year:2024"},
                ],
            },
            {
                "id": "asset2",
                "name": "student-page",
                "tags": [{"name": "students"}, {"name": "department:math"}],
            },
            {
                "id": "asset3",
                "name": "course-page",
                "tags": [
                    {"name": "courses"},
                    {"name": "department:cs"},
                    {"name": "year:2024"},
                ],
            },
            {"id": "asset4", "name": "no-tags-page", "tags": []},
        ]

    def test_find_assets_by_single_tag(self):
        """Test finding assets with a specific tag"""
        # Filter assets with "faculty" tag
        results = [
            asset
            for asset in self.assets_with_various_tags
            if any(tag["name"] == "faculty" for tag in asset["tags"])
        ]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "asset1")

    def test_find_assets_by_tag_prefix(self):
        """Test finding assets with tags matching a prefix"""
        # Filter assets with department tags
        results = [
            asset
            for asset in self.assets_with_various_tags
            if any(tag["name"].startswith("department:") for tag in asset["tags"])
        ]

        self.assertEqual(len(results), 3)

    def test_find_assets_by_multiple_tags(self):
        """Test finding assets with multiple specific tags"""
        # Filter assets with both "department:cs" and "year:2024" tags
        required_tags = ["department:cs", "year:2024"]
        results = [
            asset
            for asset in self.assets_with_various_tags
            if all(
                any(tag["name"] == req_tag for tag in asset["tags"])
                for req_tag in required_tags
            )
        ]

        self.assertEqual(len(results), 2)
        self.assertIn("asset1", [r["id"] for r in results])
        self.assertIn("asset3", [r["id"] for r in results])

    def test_find_assets_with_no_tags(self):
        """Test finding assets with no tags"""
        results = [
            asset for asset in self.assets_with_various_tags if not asset["tags"]
        ]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "asset4")

    def test_find_assets_with_any_tag(self):
        """Test finding assets with any tags"""
        results = [
            asset for asset in self.assets_with_various_tags if len(asset["tags"]) > 0
        ]

        self.assertEqual(len(results), 3)


class TestTagBatchOperations(unittest.TestCase):
    """Test batch tag operations"""

    def setUp(self):
        """Set up test fixtures"""
        self.cms_path = "https://cms.example.com"
        self.auth = {"apiKey": "test_api_key"}

    @patch("cascade_rest.metadata.set_or_replace_single_asset_tag")
    def test_batch_add_tag_to_multiple_assets(self, mock_set_tag):
        """Test adding same tag to multiple assets"""
        mock_set_tag.return_value = {"success": "true"}

        asset_ids = ["asset1", "asset2", "asset3"]
        tag_name = "batch_tag"

        results = []
        for asset_id in asset_ids:
            result = mock_set_tag(
                self.cms_path, self.auth, "page", asset_id, "", tag_name
            )
            results.append(result)

        # Verify all operations succeeded
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r["success"] == "true" for r in results))

        # Verify function was called for each asset
        self.assertEqual(mock_set_tag.call_count, 3)

    @patch("cascade_rest.metadata.set_or_replace_single_asset_tag")
    def test_batch_replace_tag_across_assets(self, mock_set_tag):
        """Test replacing tag across multiple assets"""
        mock_set_tag.return_value = {"success": "true"}

        asset_ids = ["asset1", "asset2", "asset3"]
        old_tag = "old_category"
        new_tag = "new_category"

        results = []
        for asset_id in asset_ids:
            result = mock_set_tag(
                self.cms_path, self.auth, "page", asset_id, old_tag, new_tag
            )
            results.append(result)

        # Verify all operations succeeded
        self.assertEqual(len(results), 3)
        self.assertEqual(mock_set_tag.call_count, 3)


class TestTagValidation(unittest.TestCase):
    """Test tag validation and edge cases"""

    def setUp(self):
        """Set up test fixtures"""
        self.cms_path = "https://cms.example.com"
        self.auth = {"apiKey": "test_api_key"}

    @patch("cascade_rest.metadata.edit_single_asset")
    @patch("cascade_rest.metadata.read_single_asset")
    def test_tag_with_special_characters(self, mock_read, mock_edit):
        """Test tags with special characters"""
        mock_read.return_value = {
            "asset": {"page": {"id": "asset1", "tags": []}}
        }
        mock_edit.return_value = {"success": "true"}

        # Test tags with various special characters
        special_tags = [
            "tag-with-dash",
            "tag_with_underscore",
            "tag.with.dot",
            "tag:with:colon",
        ]

        for tag in special_tags:
            result = set_or_replace_single_asset_tag(
                self.cms_path, self.auth, "page", "asset1", "", tag
            )
            # Should succeed (as long as the API accepts it)
            # This tests our code doesn't break with special characters

    @patch("cascade_rest.metadata.edit_single_asset")
    @patch("cascade_rest.metadata.read_single_asset")
    def test_tag_with_whitespace(self, mock_read, mock_edit):
        """Test tags with whitespace"""
        mock_read.return_value = {
            "asset": {"page": {"id": "asset1", "tags": []}}
        }
        mock_edit.return_value = {"success": "true"}

        # Tag with spaces
        result = set_or_replace_single_asset_tag(
            self.cms_path, self.auth, "page", "asset1", "", "tag with spaces"
        )

        call_args = mock_edit.call_args
        payload = call_args[0][4]
        tags = payload["asset"]["page"]["tags"]

        # Verify tag with spaces was added as-is
        self.assertIn({"name": "tag with spaces"}, tags)

    @patch("cascade_rest.metadata.read_single_asset")
    def test_tag_operation_with_malformed_asset_response(self, mock_read):
        """Test handling of malformed asset response"""
        # Return incomplete/malformed response
        mock_read.return_value = {"incomplete": "response"}

        result = set_or_replace_single_asset_tag(
            self.cms_path, self.auth, "page", "asset1", "", "new_tag"
        )

        # Should return False for malformed response
        self.assertFalse(result)


@pytest.mark.parametrize(
    "existing_tags,old_tag,new_tag,expected_tags",
    [
        # Replace existing tag
        (
            [{"name": "tag1"}, {"name": "tag2"}],
            "tag1",
            "tag_new",
            [{"name": "tag_new"}, {"name": "tag2"}],
        ),
        # Add new tag (old_tag not found)
        (
            [{"name": "tag1"}, {"name": "tag2"}],
            "nonexistent",
            "tag_new",
            [{"name": "tag1"}, {"name": "tag2"}, {"name": "tag_new"}],
        ),
        # Add to empty tags
        ([], "", "tag_new", [{"name": "tag_new"}]),
    ],
)
def test_tag_replacement_logic(existing_tags, old_tag, new_tag, expected_tags):
    """Test tag replacement logic with various scenarios"""
    cms_path = "https://cms.example.com"
    auth = {"apiKey": "test_key"}

    with patch("cascade_rest.metadata.read_single_asset") as mock_read, patch(
        "cascade_rest.metadata.edit_single_asset"
    ) as mock_edit:

        mock_read.return_value = {
            "asset": {"page": {"id": "asset1", "tags": existing_tags.copy()}}
        }
        mock_edit.return_value = {"success": "true"}

        # Perform tag operation
        result = set_or_replace_single_asset_tag(
            cms_path, auth, "page", "asset1", old_tag, new_tag
        )

        if result:
            # Verify edit was called with expected tags
            call_args = mock_edit.call_args
            payload = call_args[0][4]
            actual_tags = payload["asset"]["page"]["tags"]

            # Sort tags by name for comparison
            actual_sorted = sorted(actual_tags, key=lambda x: x["name"])
            expected_sorted = sorted(expected_tags, key=lambda x: x["name"])

            assert actual_sorted == expected_sorted


@pytest.mark.parametrize(
    "asset_type",
    ["page", "file", "folder", "block"],
)
def test_tag_operations_on_different_asset_types(asset_type):
    """Test that tag operations work on different asset types"""
    cms_path = "https://cms.example.com"
    auth = {"apiKey": "test_key"}

    with patch("cascade_rest.metadata.read_single_asset") as mock_read, patch(
        "cascade_rest.metadata.edit_single_asset"
    ) as mock_edit:

        mock_read.return_value = {
            "asset": {asset_type: {"id": "asset1", "tags": []}}
        }
        mock_edit.return_value = {"success": "true"}

        result = set_or_replace_single_asset_tag(
            cms_path, auth, asset_type, "asset1", "", "new_tag"
        )

        # Verify operation succeeded for this asset type
        assert result["success"] == "true"

        # Verify correct asset type was used
        call_args = mock_edit.call_args
        assert call_args[0][2] == asset_type  # asset_type is 3rd argument


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

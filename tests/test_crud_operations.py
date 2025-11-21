"""
Unit tests for CRUD operations on various asset types

Tests Create, Read, Update, Delete operations for:
- Pages
- Files
- Folders
- Blocks
- Symlinks
"""

import unittest
from unittest.mock import patch, MagicMock
import pytest

from cascade_rest.core import (
    read_single_asset,
    create_asset,
    edit_single_asset,
    delete_asset,
)


class TestCRUDOperations(unittest.TestCase):
    """Test CRUD operations for various asset types"""

    def setUp(self):
        """Set up test fixtures"""
        self.cms_path = "https://cms.example.com"
        self.auth = {"apiKey": "test_api_key"}

        self.sample_success_response = {
            "success": "true",
            "message": "Operation completed successfully",
        }

        self.sample_create_response = {
            "success": "true",
            "createdAssetId": "new123456",
        }

    # Test CREATE operations for various asset types
    @patch("cascade_rest.core.requests.post")
    def test_create_page(self, mock_post):
        """Test creating a page asset"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_create_response
        mock_post.return_value = mock_response

        asset_data = {
            "name": "test-page",
            "parentFolderPath": "/content",
            "siteName": "example.com",
            "metadata": {"title": "Test Page", "displayName": "Test Page"},
            "structuredData": {},
        }

        result = create_asset(self.cms_path, self.auth, "page", asset_data)

        # Verify API call
        expected_payload = {"asset": {"page": asset_data}}
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/create", params=self.auth, json=expected_payload
        )

        # Verify result
        self.assertEqual(result["createdAssetId"], "new123456")
        self.assertEqual(result["success"], "true")

    @patch("cascade_rest.core.requests.post")
    def test_create_file(self, mock_post):
        """Test creating a file asset"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_create_response
        mock_post.return_value = mock_response

        asset_data = {
            "name": "test-file.pdf",
            "parentFolderPath": "/documents",
            "siteName": "example.com",
            "data": "base64_encoded_file_data",
        }

        result = create_asset(self.cms_path, self.auth, "file", asset_data)

        expected_payload = {"asset": {"file": asset_data}}
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/create", params=self.auth, json=expected_payload
        )
        self.assertEqual(result["createdAssetId"], "new123456")

    @patch("cascade_rest.core.requests.post")
    def test_create_folder(self, mock_post):
        """Test creating a folder asset"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_create_response
        mock_post.return_value = mock_response

        asset_data = {
            "name": "test-folder",
            "parentFolderPath": "/content",
            "siteName": "example.com",
        }

        result = create_asset(self.cms_path, self.auth, "folder", asset_data)

        expected_payload = {"asset": {"folder": asset_data}}
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/create", params=self.auth, json=expected_payload
        )
        self.assertEqual(result["createdAssetId"], "new123456")

    @patch("cascade_rest.core.requests.post")
    def test_create_block(self, mock_post):
        """Test creating a block asset"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_create_response
        mock_post.return_value = mock_response

        asset_data = {
            "name": "test-block",
            "parentFolderPath": "/_blocks",
            "siteName": "example.com",
            "xhtml": "<div>Test Block Content</div>",
        }

        result = create_asset(self.cms_path, self.auth, "block", asset_data)

        expected_payload = {"asset": {"block": asset_data}}
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/create", params=self.auth, json=expected_payload
        )
        self.assertEqual(result["createdAssetId"], "new123456")

    @patch("cascade_rest.core.requests.post")
    def test_create_symlink(self, mock_post):
        """Test creating a symlink asset"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_create_response
        mock_post.return_value = mock_response

        asset_data = {
            "name": "test-symlink",
            "parentFolderPath": "/content",
            "siteName": "example.com",
            "linkURL": "/target-page",
        }

        result = create_asset(self.cms_path, self.auth, "symlink", asset_data)

        expected_payload = {"asset": {"symlink": asset_data}}
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/create", params=self.auth, json=expected_payload
        )
        self.assertEqual(result["createdAssetId"], "new123456")

    # Test READ operations for various asset types
    @patch("cascade_rest.core.requests.post")
    def test_read_page(self, mock_post):
        """Test reading a page asset"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "asset": {
                "page": {
                    "id": "page123",
                    "name": "test-page",
                    "path": "/content/test-page",
                    "metadata": {"title": "Test Page"},
                }
            }
        }
        mock_post.return_value = mock_response

        result = read_single_asset(self.cms_path, self.auth, "page", "page123")

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/read/page/page123", params=self.auth
        )
        self.assertEqual(result["asset"]["page"]["id"], "page123")

    @patch("cascade_rest.core.requests.post")
    def test_read_file(self, mock_post):
        """Test reading a file asset"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "asset": {
                "file": {
                    "id": "file123",
                    "name": "document.pdf",
                    "path": "/documents/document.pdf",
                    "data": "base64_data",
                }
            }
        }
        mock_post.return_value = mock_response

        result = read_single_asset(self.cms_path, self.auth, "file", "file123")

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/read/file/file123", params=self.auth
        )
        self.assertEqual(result["asset"]["file"]["id"], "file123")

    @patch("cascade_rest.core.requests.post")
    def test_read_folder(self, mock_post):
        """Test reading a folder asset"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "asset": {
                "folder": {
                    "id": "folder123",
                    "name": "test-folder",
                    "path": "/content/test-folder",
                    "children": [],
                }
            }
        }
        mock_post.return_value = mock_response

        result = read_single_asset(self.cms_path, self.auth, "folder", "folder123")

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/read/folder/folder123", params=self.auth
        )
        self.assertEqual(result["asset"]["folder"]["id"], "folder123")

    @patch("cascade_rest.core.requests.post")
    def test_read_block(self, mock_post):
        """Test reading a block asset"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "asset": {
                "block": {
                    "id": "block123",
                    "name": "test-block",
                    "path": "/_blocks/test-block",
                    "xhtml": "<div>Content</div>",
                }
            }
        }
        mock_post.return_value = mock_response

        result = read_single_asset(self.cms_path, self.auth, "block", "block123")

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/read/block/block123", params=self.auth
        )
        self.assertEqual(result["asset"]["block"]["id"], "block123")

    # Test UPDATE operations for various asset types
    @patch("cascade_rest.core.requests.post")
    def test_update_page_metadata(self, mock_post):
        """Test updating page metadata"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        edit_payload = {
            "asset": {
                "page": {
                    "id": "page123",
                    "metadata": {"title": "Updated Title", "displayName": "Updated"},
                }
            }
        }

        result = edit_single_asset(
            self.cms_path, self.auth, "page", "page123", edit_payload
        )

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/edit/page/page123",
            params=self.auth,
            json=edit_payload,
        )
        self.assertEqual(result["success"], "true")

    @patch("cascade_rest.core.requests.post")
    def test_update_file_content(self, mock_post):
        """Test updating file content"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        edit_payload = {
            "asset": {"file": {"id": "file123", "data": "new_base64_content"}}
        }

        result = edit_single_asset(
            self.cms_path, self.auth, "file", "file123", edit_payload
        )

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/edit/file/file123",
            params=self.auth,
            json=edit_payload,
        )
        self.assertEqual(result["success"], "true")

    @patch("cascade_rest.core.requests.post")
    def test_update_block_xhtml(self, mock_post):
        """Test updating block XHTML content"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        edit_payload = {
            "asset": {"block": {"id": "block123", "xhtml": "<div>Updated Content</div>"}}
        }

        result = edit_single_asset(
            self.cms_path, self.auth, "block", "block123", edit_payload
        )

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/edit/block/block123",
            params=self.auth,
            json=edit_payload,
        )
        self.assertEqual(result["success"], "true")

    # Test DELETE operations for various asset types
    @patch("cascade_rest.core.requests.post")
    def test_delete_page_with_unpublish(self, mock_post):
        """Test deleting a page with unpublishing"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        result = delete_asset(
            self.cms_path, self.auth, "page", "page123", unpublish=True
        )

        expected_payload = {
            "deleteParameters": {"unpublish": True, "doWorkflow": False}
        }

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/delete/page/page123",
            params=self.auth,
            json=expected_payload,
        )
        self.assertEqual(result["success"], "true")

    @patch("cascade_rest.core.requests.post")
    def test_delete_file(self, mock_post):
        """Test deleting a file"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        result = delete_asset(
            self.cms_path, self.auth, "file", "file123", unpublish=False
        )

        expected_payload = {
            "deleteParameters": {"unpublish": False, "doWorkflow": False}
        }

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/delete/file/file123",
            params=self.auth,
            json=expected_payload,
        )
        self.assertEqual(result["success"], "true")

    @patch("cascade_rest.core.requests.post")
    def test_delete_folder(self, mock_post):
        """Test deleting a folder"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        result = delete_asset(
            self.cms_path, self.auth, "folder", "folder123", unpublish=False
        )

        expected_payload = {
            "deleteParameters": {"unpublish": False, "doWorkflow": False}
        }

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/delete/folder/folder123",
            params=self.auth,
            json=expected_payload,
        )
        self.assertEqual(result["success"], "true")

    @patch("cascade_rest.core.requests.post")
    def test_delete_block(self, mock_post):
        """Test deleting a block"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_success_response
        mock_post.return_value = mock_response

        result = delete_asset(
            self.cms_path, self.auth, "block", "block123", unpublish=False
        )

        expected_payload = {
            "deleteParameters": {"unpublish": False, "doWorkflow": False}
        }

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/delete/block/block123",
            params=self.auth,
            json=expected_payload,
        )
        self.assertEqual(result["success"], "true")


class TestCRUDErrorHandling(unittest.TestCase):
    """Test error handling in CRUD operations"""

    def setUp(self):
        self.cms_path = "https://cms.example.com"
        self.auth = {"apiKey": "test_api_key"}

    @patch("cascade_rest.core.requests.post")
    def test_read_nonexistent_asset(self, mock_post):
        """Test reading an asset that doesn't exist"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        result = read_single_asset(self.cms_path, self.auth, "page", "nonexistent")
        self.assertFalse(result)

    @patch("cascade_rest.core.requests.post")
    def test_create_asset_with_duplicate_name(self, mock_post):
        """Test creating an asset with a duplicate name"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": "false",
            "message": "Asset with this name already exists",
        }
        mock_post.return_value = mock_response

        asset_data = {
            "name": "duplicate-page",
            "parentFolderPath": "/content",
            "siteName": "example.com",
        }

        result = create_asset(self.cms_path, self.auth, "page", asset_data)
        self.assertEqual(result["success"], "false")

    @patch("cascade_rest.core.requests.post")
    def test_update_with_invalid_data(self, mock_post):
        """Test updating with invalid data"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": "false",
            "message": "Invalid metadata field",
        }
        mock_post.return_value = mock_response

        edit_payload = {
            "asset": {"page": {"id": "page123", "metadata": {"invalidField": "value"}}}
        }

        result = edit_single_asset(
            self.cms_path, self.auth, "page", "page123", edit_payload
        )
        self.assertEqual(result["success"], "false")

    @patch("cascade_rest.core.requests.post")
    def test_delete_nonexistent_asset(self, mock_post):
        """Test deleting an asset that doesn't exist"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "success": "false",
            "message": "Asset not found",
        }
        mock_post.return_value = mock_response

        result = delete_asset(
            self.cms_path, self.auth, "page", "nonexistent", unpublish=False
        )
        self.assertEqual(result["success"], "false")


@pytest.mark.parametrize(
    "asset_type,asset_id",
    [
        ("page", "page123"),
        ("file", "file456"),
        ("folder", "folder789"),
        ("block", "block012"),
        ("symlink", "symlink345"),
    ],
)
def test_crud_operations_for_all_asset_types(asset_type, asset_id):
    """Test CRUD operations work for all asset types"""
    cms_path = "https://cms.example.com"
    auth = {"apiKey": "test_key"}

    with patch("cascade_rest.core.requests.post") as mock_post:
        # Test READ
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "asset": {asset_type: {"id": asset_id, "name": f"test-{asset_type}"}}
        }
        mock_post.return_value = mock_response

        result = read_single_asset(cms_path, auth, asset_type, asset_id)
        assert result["asset"][asset_type]["id"] == asset_id

        # Verify correct URL was called
        expected_url = f"{cms_path}/api/v1/read/{asset_type}/{asset_id}"
        mock_post.assert_called_with(expected_url, params=auth)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Tests for cascade_rest.search module

Tests search, site listing, and audit operations
"""

import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pytest

from cascade_rest.search import search_assets, list_sites, read_audits


class TestSearchOperations(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures"""
        self.cms_path = "https://cms.example.com"
        self.auth = {"u": "testuser", "p": "testpass"}

        self.sample_search_response = {
            "searchReturn": {
                "success": "true",
                "matches": {
                    "match": [
                        {
                            "id": "match1",
                            "type": "page",
                            "path": {
                                "path": "/folder/page1",
                                "siteName": "example.com",
                            },
                        },
                        {
                            "id": "match2",
                            "type": "file",
                            "path": {
                                "path": "/folder/file1.pdf",
                                "siteName": "example.com",
                            },
                        },
                    ]
                },
            }
        }

        self.sample_sites_response = {
            "listSitesReturn": {
                "success": "true",
                "sites": {
                    "assetIdentifier": [
                        {
                            "id": "site1",
                            "type": "site",
                            "path": {"path": "example.com"},
                        },
                        {
                            "id": "site2",
                            "type": "site",
                            "path": {"path": "test.example.com"},
                        },
                    ]
                },
            }
        }

        self.sample_audits_response = {
            "readAuditsReturn": {
                "success": "true",
                "audits": {
                    "audit": [
                        {
                            "user": "admin",
                            "action": "edit",
                            "identifier": {"id": "page123", "type": "page"},
                            "date": "2023-01-15T10:30:00.000Z",
                        },
                        {
                            "user": "editor",
                            "action": "publish",
                            "identifier": {"id": "page123", "type": "page"},
                            "date": "2023-01-15T11:00:00.000Z",
                        },
                    ]
                },
            }
        }

    @patch("cascade_rest.search.requests.post")
    def test_search_assets_basic(self, mock_post):
        """Test basic asset search"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_search_response
        mock_post.return_value = mock_response

        result = search_assets(self.cms_path, self.auth, "test search")

        # Verify API call
        expected_payload = {"searchInformation": {"searchTerms": "test search"}}

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/search", params=self.auth, json=expected_payload
        )

        # Verify result
        self.assertEqual(result, self.sample_search_response)

    @patch("cascade_rest.search.requests.post")
    def test_search_assets_with_site_filter(self, mock_post):
        """Test asset search with site filter"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_search_response
        mock_post.return_value = mock_response

        result = search_assets(
            self.cms_path, self.auth, "test search", site_name="example.com"
        )

        # Verify siteName is included in the payload
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        self.assertEqual(payload["searchInformation"]["siteName"], "example.com")

    @patch("cascade_rest.search.requests.post")
    def test_search_assets_with_field_filters(self, mock_post):
        """Test asset search with field filters"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_search_response
        mock_post.return_value = mock_response

        search_fields = ["name", "title", "summary"]

        result = search_assets(
            self.cms_path, self.auth, "test search", search_fields=search_fields
        )

        # Verify searchFields is included in the payload
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        self.assertEqual(payload["searchInformation"]["searchFields"], search_fields)

    @patch("cascade_rest.search.requests.post")
    def test_search_assets_with_type_filters(self, mock_post):
        """Test asset search with type filters"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_search_response
        mock_post.return_value = mock_response

        search_types = ["page", "file"]

        result = search_assets(
            self.cms_path, self.auth, "test search", search_types=search_types
        )

        # Verify searchTypes is included in the payload
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        self.assertEqual(payload["searchInformation"]["searchTypes"], search_types)

    @patch("cascade_rest.search.requests.post")
    def test_search_assets_with_all_filters(self, mock_post):
        """Test asset search with all filters combined"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_search_response
        mock_post.return_value = mock_response

        result = search_assets(
            self.cms_path,
            self.auth,
            "comprehensive search",
            site_name="example.com",
            search_fields=["name", "title"],
            search_types=["page"],
        )

        # Verify all filters are included
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        search_info = payload["searchInformation"]

        self.assertEqual(search_info["searchTerms"], "comprehensive search")
        self.assertEqual(search_info["siteName"], "example.com")
        self.assertEqual(search_info["searchFields"], ["name", "title"])
        self.assertEqual(search_info["searchTypes"], ["page"])

    @patch("cascade_rest.search.requests.post")
    def test_list_sites(self, mock_post):
        """Test listing all sites"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_sites_response
        mock_post.return_value = mock_response

        result = list_sites(self.cms_path, self.auth)

        # Verify API call
        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/listSites", params=self.auth
        )

        # Verify result
        self.assertEqual(result, self.sample_sites_response)

    @patch("cascade_rest.search.requests.post")
    def test_read_audits_basic(self, mock_post):
        """Test basic audit reading"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_audits_response
        mock_post.return_value = mock_response

        result = read_audits(self.cms_path, self.auth)

        # Verify API call
        expected_payload = {"auditParameters": {}}

        mock_post.assert_called_once_with(
            f"{self.cms_path}/api/v1/readAudits",
            params=self.auth,
            json=expected_payload,
        )

        # Verify result
        self.assertEqual(result, self.sample_audits_response)

    @patch("cascade_rest.search.requests.post")
    def test_read_audits_with_asset_filter(self, mock_post):
        """Test audit reading with asset filter"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_audits_response
        mock_post.return_value = mock_response

        result = read_audits(
            self.cms_path, self.auth, asset_type="page", asset_id="test123"
        )

        # Verify identifier is included in the payload
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        expected_identifier = {"type": "page", "id": "test123"}
        self.assertEqual(payload["auditParameters"]["identifier"], expected_identifier)

    @patch("cascade_rest.search.requests.post")
    def test_read_audits_with_username_filter(self, mock_post):
        """Test audit reading with username filter"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_audits_response
        mock_post.return_value = mock_response

        result = read_audits(self.cms_path, self.auth, username="testuser")

        # Verify username is included in the payload
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        self.assertEqual(payload["auditParameters"]["username"], "testuser")

    @patch("cascade_rest.search.requests.post")
    def test_read_audits_with_date_filters(self, mock_post):
        """Test audit reading with date filters"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_audits_response
        mock_post.return_value = mock_response

        start_date = datetime(2023, 1, 1, 9, 0, 0)
        end_date = datetime(2023, 12, 31, 17, 30, 0)

        result = read_audits(
            self.cms_path, self.auth, start_date=start_date, end_date=end_date
        )

        # Verify dates are formatted correctly
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        audit_params = payload["auditParameters"]

        self.assertEqual(audit_params["startDate"], "Jan 01, 2023 09:00:00 AM")
        self.assertEqual(audit_params["endDate"], "Dec 31, 2023 05:30:00 PM")

    @patch("cascade_rest.search.requests.post")
    def test_read_audits_with_audit_type_filter(self, mock_post):
        """Test audit reading with audit type filter"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_audits_response
        mock_post.return_value = mock_response

        result = read_audits(self.cms_path, self.auth, audit_type="publish")

        # Verify audit type is included in the payload
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        self.assertEqual(payload["auditParameters"]["auditType"], "publish")

    @patch("cascade_rest.search.requests.post")
    def test_read_audits_with_all_filters(self, mock_post):
        """Test audit reading with all filters combined"""
        mock_response = MagicMock()
        mock_response.json.return_value = self.sample_audits_response
        mock_post.return_value = mock_response

        start_date = datetime(2023, 6, 1, 8, 0, 0)
        end_date = datetime(2023, 6, 30, 18, 0, 0)

        result = read_audits(
            self.cms_path,
            self.auth,
            asset_type="page",
            asset_id="test123",
            username="admin",
            start_date=start_date,
            end_date=end_date,
            audit_type="edit",
        )

        # Verify all filters are included
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        audit_params = payload["auditParameters"]

        self.assertEqual(audit_params["identifier"], {"type": "page", "id": "test123"})
        self.assertEqual(audit_params["username"], "admin")
        self.assertEqual(audit_params["startDate"], "Jun 01, 2023 08:00:00 AM")
        self.assertEqual(audit_params["endDate"], "Jun 30, 2023 06:00:00 PM")
        self.assertEqual(audit_params["auditType"], "edit")

    def test_read_audits_partial_asset_filter(self):
        """Test that asset filter requires both type and id"""
        with patch("cascade_rest.search.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = self.sample_audits_response
            mock_post.return_value = mock_response

            # Test with only asset_type
            result = read_audits(self.cms_path, self.auth, asset_type="page")

            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            # Should not include identifier since asset_id is missing
            self.assertNotIn("identifier", payload["auditParameters"])

            mock_post.reset_mock()

            # Test with only asset_id
            result = read_audits(self.cms_path, self.auth, asset_id="test123")

            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            # Should not include identifier since asset_type is missing
            self.assertNotIn("identifier", payload["auditParameters"])


class TestParametrizedSearch:
    """Pytest-style parametrized tests for search operations"""

    @pytest.mark.parametrize(
        "search_terms,expected_terms",
        [
            ("simple search", "simple search"),
            (
                "complex search with multiple words",
                "complex search with multiple words",
            ),
            ("special-chars_123", "special-chars_123"),
            ("", ""),  # Edge case
        ],
    )
    def test_search_terms_handling(self, search_terms, expected_terms):
        """Test search terms are properly passed through"""
        cms_path = "https://cms.example.com"
        auth = {"u": "user", "p": "pass"}

        with patch("cascade_rest.search.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"matches": {"match": []}}
            mock_post.return_value = mock_response

            search_assets(cms_path, auth, search_terms)

            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["searchInformation"]["searchTerms"] == expected_terms

    @pytest.mark.parametrize(
        "audit_type",
        ["login", "logout", "edit", "publish", "create", "delete", "move", "copy"],
    )
    def test_audit_type_values(self, audit_type):
        """Test various audit type values"""
        cms_path = "https://cms.example.com"
        auth = {"u": "user", "p": "pass"}

        with patch("cascade_rest.search.requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"audits": {"audit": []}}
            mock_post.return_value = mock_response

            read_audits(cms_path, auth, audit_type=audit_type)

            call_args = mock_post.call_args
            payload = call_args[1]["json"]
            assert payload["auditParameters"]["auditType"] == audit_type


class TestSearchErrorHandling(unittest.TestCase):
    """Test error scenarios for search operations"""

    def setUp(self):
        self.cms_path = "https://cms.example.com"
        self.auth = {"u": "user", "p": "pass"}

    @patch("cascade_rest.search.requests.post")
    def test_search_network_error(self, mock_post):
        """Test search with network error"""
        import requests

        mock_post.side_effect = requests.ConnectionError("Network error")

        with self.assertRaises(requests.ConnectionError):
            search_assets(self.cms_path, self.auth, "test")

    @patch("cascade_rest.search.requests.post")
    def test_sites_timeout_error(self, mock_post):
        """Test list sites with timeout error"""
        import requests

        mock_post.side_effect = requests.Timeout("Request timed out")

        with self.assertRaises(requests.Timeout):
            list_sites(self.cms_path, self.auth)

    @patch("cascade_rest.search.requests.post")
    def test_audits_malformed_response(self, mock_post):
        """Test audits with malformed JSON response"""
        import json

        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_post.return_value = mock_response

        with self.assertRaises(json.JSONDecodeError):
            read_audits(self.cms_path, self.auth)


class TestDateHandling(unittest.TestCase):
    """Test date formatting and handling in audit operations"""

    def setUp(self):
        self.cms_path = "https://cms.example.com"
        self.auth = {"u": "user", "p": "pass"}

    @patch("cascade_rest.search.requests.post")
    def test_date_formatting_edge_cases(self, mock_post):
        """Test date formatting with edge cases"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"audits": {"audit": []}}
        mock_post.return_value = mock_response

        # Test midnight
        midnight = datetime(2023, 1, 1, 0, 0, 0)
        # Test noon
        noon = datetime(2023, 6, 15, 12, 0, 0)
        # Test near midnight
        late_night = datetime(2023, 12, 31, 23, 59, 59)

        test_cases = [
            (midnight, "Jan 01, 2023 12:00:00 AM"),
            (noon, "Jun 15, 2023 12:00:00 PM"),
            (late_night, "Dec 31, 2023 11:59:59 PM"),
        ]

        for test_date, expected_format in test_cases:
            with self.subTest(date=test_date):
                mock_post.reset_mock()

                read_audits(self.cms_path, self.auth, start_date=test_date)

                call_args = mock_post.call_args
                payload = call_args[1]["json"]
                actual_format = payload["auditParameters"]["startDate"]
                self.assertEqual(actual_format, expected_format)

    @patch("cascade_rest.search.requests.post")
    def test_date_range_validation(self, mock_post):
        """Test date range scenarios"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"audits": {"audit": []}}
        mock_post.return_value = mock_response

        # Test with start date after end date (should still work, server handles validation)
        start_date = datetime(2023, 12, 31)
        end_date = datetime(2023, 1, 1)

        result = read_audits(
            self.cms_path, self.auth, start_date=start_date, end_date=end_date
        )

        # Should make the API call even with reversed dates
        mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)

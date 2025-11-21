"""
Unit tests for AdvancedFilter

Tests filter operators including:
- equals, contains, starts_with, ends_with, regex
- in, not_in
- greater_than, less_than
- date_after, date_before, date_between
- is_empty, is_not_empty
"""

import unittest
from datetime import datetime
import pytest

from advanced_filtering import AdvancedFilter


class TestAdvancedFilterOperators(unittest.TestCase):
    """Test AdvancedFilter operators"""

    def setUp(self):
        """Set up test fixtures"""
        self.filter = AdvancedFilter()

        # Sample assets for testing
        self.sample_assets = [
            {
                "id": "asset1",
                "name": "faculty-page",
                "path": "/content/faculty/john-doe",
                "metadata": {
                    "title": "Dr. John Doe",
                    "department": "Computer Science",
                    "academic_year": "2024-2025",
                },
                "createdDate": "2024-01-15",
                "status": "published",
                "priority": 10,
            },
            {
                "id": "asset2",
                "name": "student-page",
                "path": "/content/students/jane-smith",
                "metadata": {
                    "title": "Jane Smith",
                    "department": "Mathematics",
                    "academic_year": "2024-2025",
                },
                "createdDate": "2024-03-20",
                "status": "draft",
                "priority": 5,
            },
            {
                "id": "asset3",
                "name": "course-page",
                "path": "/content/courses/cs101",
                "metadata": {
                    "title": "Introduction to Computer Science",
                    "department": "Computer Science",
                    "academic_year": "2023-2024",
                },
                "createdDate": "2023-09-01",
                "status": "published",
                "priority": 8,
            },
        ]

    # Test text operators
    def test_equals_operator(self):
        """Test equals operator"""
        filter_expr = self.filter.create_filter_expression(
            "status", "equals", "published"
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "asset1")
        self.assertEqual(result[1]["id"], "asset3")

    def test_equals_operator_case_insensitive(self):
        """Test equals operator with case insensitive matching"""
        filter_expr = self.filter.create_filter_expression(
            "status", "equals", "PUBLISHED", case_sensitive=False
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 2)

    def test_contains_operator(self):
        """Test contains operator"""
        filter_expr = self.filter.create_filter_expression(
            "path", "contains", "faculty"
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "asset1")

    def test_contains_operator_case_insensitive(self):
        """Test contains operator with case insensitive matching"""
        filter_expr = self.filter.create_filter_expression(
            "metadata.title", "contains", "COMPUTER", case_sensitive=False
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 2)  # Matches both faculty and course pages

    def test_starts_with_operator(self):
        """Test starts_with operator"""
        filter_expr = self.filter.create_filter_expression(
            "name", "starts_with", "faculty"
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "faculty-page")

    def test_ends_with_operator(self):
        """Test ends_with operator"""
        filter_expr = self.filter.create_filter_expression("name", "ends_with", "page")
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 3)  # All assets end with "page"

    def test_regex_operator(self):
        """Test regex operator"""
        # Match assets with paths containing "faculty" or "students"
        filter_expr = self.filter.create_filter_expression(
            "path", "regex", r"/(faculty|students)/"
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 2)
        self.assertIn(result[0]["id"], ["asset1", "asset2"])

    def test_regex_operator_with_invalid_regex(self):
        """Test regex operator with invalid regex pattern"""
        filter_expr = self.filter.create_filter_expression(
            "path", "regex", "[invalid(regex"
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        # Should return empty list for invalid regex
        self.assertEqual(len(result), 0)

    # Test list operators
    def test_in_operator(self):
        """Test in operator"""
        filter_expr = self.filter.create_filter_expression(
            "metadata.department", "in", ["Computer Science", "Physics"]
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["metadata"]["department"], "Computer Science")
        self.assertEqual(result[1]["metadata"]["department"], "Computer Science")

    def test_not_in_operator(self):
        """Test not_in operator"""
        filter_expr = self.filter.create_filter_expression(
            "metadata.department", "not_in", ["Computer Science"]
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["metadata"]["department"], "Mathematics")

    # Test numeric operators
    def test_greater_than_operator(self):
        """Test greater_than operator"""
        filter_expr = self.filter.create_filter_expression("priority", "greater_than", 7)
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 2)
        self.assertTrue(all(asset["priority"] > 7 for asset in result))

    def test_less_than_operator(self):
        """Test less_than operator"""
        filter_expr = self.filter.create_filter_expression("priority", "less_than", 8)
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["priority"], 5)

    # Test date operators
    def test_date_after_operator(self):
        """Test date_after operator"""
        filter_expr = self.filter.create_filter_expression(
            "createdDate", "date_after", "2024-01-01"
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 2)
        self.assertIn(result[0]["id"], ["asset1", "asset2"])

    def test_date_before_operator(self):
        """Test date_before operator"""
        filter_expr = self.filter.create_filter_expression(
            "createdDate", "date_before", "2024-01-01"
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "asset3")

    def test_date_between_operator(self):
        """Test date_between operator"""
        filter_expr = self.filter.create_filter_expression(
            "createdDate", "date_between", ["2024-01-01", "2024-02-01"]
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "asset1")

    def test_date_formats_parsing(self):
        """Test various date format parsing"""
        # Test with different date formats
        assets_with_dates = [
            {"id": "d1", "date": "2024-01-15"},  # YYYY-MM-DD
            {"id": "d2", "date": "01/15/2024"},  # MM/DD/YYYY
            {"id": "d3", "date": "2024-01-15 10:30:00"},  # YYYY-MM-DD HH:MM:SS
        ]

        filter_expr = self.filter.create_filter_expression(
            "date", "date_after", "2024-01-01"
        )
        result = self.filter.apply_filters(assets_with_dates, [filter_expr])

        self.assertEqual(len(result), 3)  # All dates are after 2024-01-01

    # Test validation operators
    def test_is_empty_operator(self):
        """Test is_empty operator"""
        assets_with_empty = [
            {"id": "e1", "field": ""},
            {"id": "e2", "field": None},
            {"id": "e3", "field": "value"},
        ]

        filter_expr = self.filter.create_filter_expression("field", "is_empty", None)
        result = self.filter.apply_filters(assets_with_empty, [filter_expr])

        self.assertEqual(len(result), 2)
        self.assertIn(result[0]["id"], ["e1", "e2"])

    def test_is_not_empty_operator(self):
        """Test is_not_empty operator"""
        assets_with_empty = [
            {"id": "e1", "field": ""},
            {"id": "e2", "field": None},
            {"id": "e3", "field": "value"},
        ]

        filter_expr = self.filter.create_filter_expression("field", "is_not_empty", None)
        result = self.filter.apply_filters(assets_with_empty, [filter_expr])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "e3")

    # Test nested field access
    def test_nested_field_access(self):
        """Test accessing nested fields with dot notation"""
        filter_expr = self.filter.create_filter_expression(
            "metadata.department", "equals", "Computer Science"
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        self.assertEqual(len(result), 2)
        self.assertTrue(
            all(asset["metadata"]["department"] == "Computer Science" for asset in result)
        )

    def test_deeply_nested_field_access(self):
        """Test accessing deeply nested fields"""
        assets_with_deep_nesting = [
            {
                "id": "n1",
                "level1": {"level2": {"level3": {"value": "target"}}},
            },
            {
                "id": "n2",
                "level1": {"level2": {"level3": {"value": "other"}}},
            },
        ]

        filter_expr = self.filter.create_filter_expression(
            "level1.level2.level3.value", "equals", "target"
        )
        result = self.filter.apply_filters(assets_with_deep_nesting, [filter_expr])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "n1")

    # Test multiple filters (AND logic)
    def test_multiple_filters_and_logic(self):
        """Test applying multiple filters with AND logic"""
        filters = [
            self.filter.create_filter_expression("status", "equals", "published"),
            self.filter.create_filter_expression(
                "metadata.department", "equals", "Computer Science"
            ),
        ]
        result = self.filter.apply_filters(self.sample_assets, filters)

        # Should match only asset1 (published AND Computer Science)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "asset1")

    def test_complex_filter_with_or_logic(self):
        """Test complex filter with OR logic"""
        # Create complex filter: status=published OR department=Mathematics
        expr1 = self.filter.create_filter_expression("status", "equals", "published")
        expr2 = self.filter.create_filter_expression(
            "metadata.department", "equals", "Mathematics"
        )

        complex_filter = self.filter.create_complex_filter([expr1, expr2], logic="OR")
        result = self.filter.apply_complex_filter(self.sample_assets, complex_filter)

        # Should match asset1, asset2, and asset3
        self.assertEqual(len(result), 3)

    def test_complex_filter_with_and_logic(self):
        """Test complex filter with AND logic"""
        expr1 = self.filter.create_filter_expression("status", "equals", "published")
        expr2 = self.filter.create_filter_expression("priority", "greater_than", 7)

        complex_filter = self.filter.create_complex_filter([expr1, expr2], logic="AND")
        result = self.filter.apply_complex_filter(self.sample_assets, complex_filter)

        # Should match asset1 and asset3 (published AND priority > 7)
        self.assertEqual(len(result), 2)

    # Test edge cases
    def test_filter_empty_asset_list(self):
        """Test filtering empty asset list"""
        filter_expr = self.filter.create_filter_expression("field", "equals", "value")
        result = self.filter.apply_filters([], [filter_expr])

        self.assertEqual(len(result), 0)

    def test_filter_with_no_filters(self):
        """Test applying no filters returns all assets"""
        result = self.filter.apply_filters(self.sample_assets, [])

        self.assertEqual(len(result), 3)

    def test_filter_with_nonexistent_field(self):
        """Test filtering on field that doesn't exist"""
        filter_expr = self.filter.create_filter_expression(
            "nonexistent_field", "equals", "value"
        )
        result = self.filter.apply_filters(self.sample_assets, [filter_expr])

        # Should return empty list
        self.assertEqual(len(result), 0)

    def test_invalid_operator_raises_error(self):
        """Test that invalid operator raises ValueError"""
        with self.assertRaises(ValueError):
            self.filter.create_filter_expression("field", "invalid_operator", "value")

    def test_invalid_complex_filter_logic(self):
        """Test that invalid logic raises ValueError"""
        expr = self.filter.create_filter_expression("field", "equals", "value")

        with self.assertRaises(ValueError):
            self.filter.create_complex_filter([expr], logic="INVALID")


class TestAdvancedFilterPresets(unittest.TestCase):
    """Test preset filters"""

    def setUp(self):
        self.filter = AdvancedFilter()

    def test_create_preset_filters(self):
        """Test creating preset filters"""
        presets = self.filter.create_preset_filters()

        self.assertIn("recent_assets", presets)
        self.assertIn("published_assets", presets)
        self.assertIn("draft_assets", presets)

        # Verify structure
        self.assertEqual(presets["published_assets"]["operator"], "equals")
        self.assertEqual(presets["published_assets"]["value"], "published")


@pytest.mark.parametrize(
    "operator,field_value,filter_value,expected",
    [
        ("equals", "test", "test", True),
        ("equals", "test", "TEST", False),
        ("contains", "hello world", "world", True),
        ("contains", "hello world", "WORLD", False),
        ("starts_with", "prefix_test", "prefix", True),
        ("starts_with", "prefix_test", "test", False),
        ("ends_with", "test_suffix", "suffix", True),
        ("ends_with", "test_suffix", "test", False),
        ("greater_than", 10, 5, True),
        ("greater_than", 5, 10, False),
        ("less_than", 5, 10, True),
        ("less_than", 10, 5, False),
    ],
)
def test_operator_behavior_parametrized(operator, field_value, filter_value, expected):
    """Test various operator behaviors with parametrized inputs"""
    filter_obj = AdvancedFilter()
    asset = {"field": field_value}

    filter_expr = filter_obj.create_filter_expression(
        "field", operator, filter_value, case_sensitive=True
    )
    result = filter_obj.apply_filters([asset], [filter_expr])

    if expected:
        assert len(result) == 1
    else:
        assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

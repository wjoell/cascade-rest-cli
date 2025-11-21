"""
Advanced filtering system for Cascade REST CLI
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Callable
from functools import partial

from config import FILTER_OPERATORS, DATE_FORMATS
from logging_config import logger


class AdvancedFilter:
    """Advanced filtering system for asset searches"""

    def __init__(self):
        self.operators = FILTER_OPERATORS
        self.date_formats = DATE_FORMATS

    def create_filter_expression(
        self, field: str, operator: str, value: Any, case_sensitive: bool = False
    ) -> Dict[str, Any]:
        """Create a filter expression"""
        if operator not in self.operators:
            raise ValueError(
                f"Unknown operator: {operator}. Available: {self.operators}"
            )

        return {
            "field": field,
            "operator": operator,
            "value": value,
            "case_sensitive": case_sensitive,
        }

    def apply_filters(
        self, assets: List[Dict[str, Any]], filters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply multiple filters to a list of assets"""
        if not filters:
            return assets

        filtered_assets = []

        for asset in assets:
            if self._asset_matches_filters(asset, filters):
                filtered_assets.append(asset)

        logger.log_operation_end(
            "advanced_filtering",
            True,
            original_count=len(assets),
            filtered_count=len(filtered_assets),
            filter_count=len(filters),
        )

        return filtered_assets

    def _asset_matches_filters(
        self, asset: Dict[str, Any], filters: List[Dict[str, Any]]
    ) -> bool:
        """Check if an asset matches all filters (AND logic)"""
        for filter_expr in filters:
            if not self._asset_matches_filter(asset, filter_expr):
                return False
        return True

    def _asset_matches_filter(
        self, asset: Dict[str, Any], filter_expr: Dict[str, Any]
    ) -> bool:
        """Check if an asset matches a single filter"""
        field = filter_expr["field"]
        operator = filter_expr["operator"]
        value = filter_expr["value"]
        case_sensitive = filter_expr.get("case_sensitive", False)

        # Get field value from asset (support nested fields with dot notation)
        asset_value = self._get_nested_value(asset, field)

        if asset_value is None:
            return False

        # Apply the filter operator
        return self._apply_operator(asset_value, operator, value, case_sensitive)

    def _get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested value using dot notation (e.g., 'metadata.title')"""
        keys = field_path.split(".")
        current = data

        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None

        return current

    def _apply_operator(
        self, asset_value: Any, operator: str, filter_value: Any, case_sensitive: bool
    ) -> bool:
        """Apply a filter operator"""
        # Convert to strings for comparison if not case sensitive
        if (
            not case_sensitive
            and isinstance(asset_value, str)
            and isinstance(filter_value, str)
        ):
            asset_value = asset_value.lower()
            filter_value = filter_value.lower()

        if operator == "equals":
            return asset_value == filter_value

        elif operator == "contains":
            if not isinstance(asset_value, str) or not isinstance(filter_value, str):
                return False
            return filter_value in asset_value

        elif operator == "starts_with":
            if not isinstance(asset_value, str) or not isinstance(filter_value, str):
                return False
            return asset_value.startswith(filter_value)

        elif operator == "ends_with":
            if not isinstance(asset_value, str) or not isinstance(filter_value, str):
                return False
            return asset_value.endswith(filter_value)

        elif operator == "regex":
            if not isinstance(asset_value, str):
                return False
            try:
                return bool(re.search(filter_value, asset_value))
            except re.error:
                logger.log_error(Exception(f"Invalid regex: {filter_value}"))
                return False

        elif operator == "in":
            if isinstance(filter_value, (list, tuple)):
                return asset_value in filter_value
            return False

        elif operator == "not_in":
            if isinstance(filter_value, (list, tuple)):
                return asset_value not in filter_value
            return True

        elif operator == "greater_than":
            try:
                return float(asset_value) > float(filter_value)
            except (ValueError, TypeError):
                return False

        elif operator == "less_than":
            try:
                return float(asset_value) < float(filter_value)
            except (ValueError, TypeError):
                return False

        elif operator == "date_after":
            return self._compare_dates(asset_value, filter_value, "after")

        elif operator == "date_before":
            return self._compare_dates(asset_value, filter_value, "before")

        elif operator == "date_between":
            if not isinstance(filter_value, (list, tuple)) or len(filter_value) != 2:
                return False
            start_date, end_date = filter_value
            return self._compare_dates(
                asset_value, start_date, "after"
            ) and self._compare_dates(asset_value, end_date, "before")

        elif operator == "is_empty":
            return asset_value is None or asset_value == ""

        elif operator == "is_not_empty":
            return asset_value is not None and asset_value != ""

        else:
            logger.log_error(Exception(f"Unknown operator: {operator}"))
            return False

    def _compare_dates(
        self, asset_value: Any, filter_value: Any, comparison: str
    ) -> bool:
        """Compare dates with flexible parsing"""
        try:
            asset_date = self._parse_date(asset_value)
            filter_date = self._parse_date(filter_value)

            if asset_date is None or filter_date is None:
                return False

            if comparison == "after":
                return asset_date > filter_date
            elif comparison == "before":
                return asset_date < filter_date
            else:
                return asset_date == filter_date

        except Exception:
            return False

    def _parse_date(self, date_value: Any) -> Optional[datetime]:
        """Parse date from various formats"""
        if isinstance(date_value, datetime):
            return date_value

        if not isinstance(date_value, str):
            return None

        date_str = date_value.strip()

        # Try each format
        for fmt in self.date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Try ISO format
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            pass

        return None

    def create_complex_filter(
        self, expressions: List[Dict[str, Any]], logic: str = "AND"
    ) -> Dict[str, Any]:
        """Create complex filter with multiple expressions and logic"""
        if logic.upper() not in ["AND", "OR"]:
            raise ValueError("Logic must be 'AND' or 'OR'")

        return {"type": "complex", "logic": logic.upper(), "expressions": expressions}

    def apply_complex_filter(
        self, assets: List[Dict[str, Any]], complex_filter: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply complex filter with multiple expressions"""
        if complex_filter.get("type") != "complex":
            raise ValueError("Not a complex filter")

        logic = complex_filter["logic"]
        expressions = complex_filter["expressions"]

        filtered_assets = []

        for asset in assets:
            matches = []

            for expr in expressions:
                if (
                    isinstance(expr, dict)
                    and "type" in expr
                    and expr["type"] == "complex"
                ):
                    # Nested complex filter
                    nested_assets = [asset]
                    nested_result = self.apply_complex_filter(nested_assets, expr)
                    matches.append(len(nested_result) > 0)
                else:
                    # Simple filter
                    matches.append(self._asset_matches_filter(asset, expr))

            if logic == "AND":
                if all(matches):
                    filtered_assets.append(asset)
            else:  # OR
                if any(matches):
                    filtered_assets.append(asset)

        return filtered_assets

    def create_preset_filters(self) -> Dict[str, Dict[str, Any]]:
        """Create common filter presets"""
        return {
            "recent_assets": {
                "field": "createdDate",
                "operator": "date_after",
                "value": (datetime.now().replace(day=1)).strftime("%Y-%m-%d"),
                "description": "Assets created this month",
            },
            "published_assets": {
                "field": "status",
                "operator": "equals",
                "value": "published",
                "description": "Published assets only",
            },
            "draft_assets": {
                "field": "status",
                "operator": "equals",
                "value": "draft",
                "description": "Draft assets only",
            },
            "pages_with_images": {
                "field": "type",
                "operator": "equals",
                "value": "page",
                "description": "Page assets only",
            },
            "assets_with_metadata": {
                "field": "metadata",
                "operator": "is_not_empty",
                "value": "",
                "description": "Assets with metadata",
            },
        }


# Global advanced filter instance
advanced_filter = AdvancedFilter()

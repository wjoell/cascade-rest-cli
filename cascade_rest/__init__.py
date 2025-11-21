"""
Cascade REST API Library

A comprehensive Python library for interacting with Cascade Server REST API endpoints.

Usage:
    import cascade_rest

    # Basic operations
    result = cascade_rest.read_single_asset(cms_path, auth, "page", "asset_id")

    # Or import specific modules
    from cascade_rest.core import read_single_asset, create_asset
    from cascade_rest.publishing import publish_asset
    from cascade_rest.search import search_assets

Modules:
    core: Basic CRUD operations (Create, Read, Update, Delete)
    publishing: Publishing, workflow, and subscriber operations
    search: Search, site listing, and audit operations
    metadata: Metadata field operations and tag management
    folders: Folder navigation and structured data operations
    utils: Utility functions and reporting
"""

# Import all functions to make them available at package level
from .core import (
    read_single_asset,
    read_asset_by_path,
    create_asset,
    edit_single_asset,
    delete_asset,
    copy_single_asset,
    move_asset,
)

from .publishing import (
    publish_asset,
    check_out_asset,
    check_in_asset,
    list_subscribers_single_asset,
)

from .search import search_assets, list_sites, read_audits

from .metadata import (
    read_single_asset_metadata_value,
    set_single_asset_metadata_value,
    update_single_asset_dynamic_metadata_value,
    set_or_replace_single_asset_tag,
    get_dynamic_field,
    METADATA_ALLOWED_KEYS,
)

from .folders import (
    get_folder_children,
    get_folder_child_id_by_name,
    get_structured_data_node,
    find_structured_data_node_idx_single,
    find_structured_data_node_idx_collection,
)

from .utils import (
    report,
    report_out,
    message_out,
    reports,
    clear_reports,
    get_report_summary,
)

# Version information
__version__ = "2.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# For backwards compatibility, expose metadata allowed keys at package level
metadata_allowed_keys = METADATA_ALLOWED_KEYS


# Package-level convenience functions
def get_version():
    """Return the package version"""
    return __version__


def list_available_functions():
    """Return a list of all available functions in the package"""
    functions = []

    # Get all exported functions from __all__ if it exists, otherwise from globals
    for name in globals():
        if callable(globals()[name]) and not name.startswith("_"):
            functions.append(name)

    return sorted(functions)


# Optional: Define __all__ to control what gets imported with "from cascade_rest import *"
__all__ = [
    # Core operations
    "read_single_asset",
    "read_asset_by_path",
    "create_asset",
    "edit_single_asset",
    "delete_asset",
    "copy_single_asset",
    "move_asset",
    # Publishing operations
    "publish_asset",
    "check_out_asset",
    "check_in_asset",
    "list_subscribers_single_asset",
    # Search operations
    "search_assets",
    "list_sites",
    "read_audits",
    # Metadata operations
    "read_single_asset_metadata_value",
    "set_single_asset_metadata_value",
    "update_single_asset_dynamic_metadata_value",
    "set_or_replace_single_asset_tag",
    "get_dynamic_field",
    "METADATA_ALLOWED_KEYS",
    "metadata_allowed_keys",  # backwards compatibility
    # Folder operations
    "get_folder_children",
    "get_folder_child_id_by_name",
    "get_structured_data_node",
    "find_structured_data_node_idx_single",
    "find_structured_data_node_idx_collection",
    # Utility functions
    "report",
    "report_out",
    "message_out",
    "reports",
    "clear_reports",
    "get_report_summary",
    # Package functions
    "get_version",
    "list_available_functions",
]

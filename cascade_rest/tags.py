"""
Tag management functions for Cascade Server REST API
"""

from typing import Dict, Any, List, Optional, Union
import requests


def get_asset_tags(cms_path: str, auth: dict, asset_id: str, asset_type: str) -> Dict[str, Any]:
    """Get tags for a specific asset
    
    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_id: ID of the asset
        :asset_type: Type of the asset (page, file, etc.)
    """
    read_path = f"{cms_path}/api/v1/read/{asset_type}/{asset_id}"
    
    p = requests.post(read_path, params=auth)
    result = p.json()
    
    if result.get("success"):
        # Tags can be at different levels depending on asset type
        asset = result.get("asset", {})
        
        # Check for tags at the top level first
        tags = asset.get("tags", [])
        
        # If no tags at top level, check inside the asset type object
        if not tags and asset_type in asset:
            tags = asset[asset_type].get("tags", [])
        
        return {
            "success": True,
            "tags": tags
        }
    else:
        return result


def set_asset_tags(cms_path: str, auth: dict, asset_id: str, asset_type: str, tags: List[str]) -> Dict[str, Any]:
    """Set tags for a specific asset
    
    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_id: ID of the asset
        :asset_type: Type of the asset (page, file, etc.)
        :tags: List of tag names to set
    """
    # First, get the current asset data
    read_path = f"{cms_path}/api/v1/read/{asset_type}/{asset_id}"
    p = requests.post(read_path, params=auth)
    result = p.json()
    
    if not result.get("success"):
        return result
    
    # Convert tag names to tag objects
    tag_objects = [{"name": tag} for tag in tags]
    
    # Update the asset with new tags
    asset = result["asset"]
    # Tags are stored under the asset type key (e.g., asset.page.tags)
    if asset_type in asset:
        asset[asset_type]["tags"] = tag_objects
    else:
        # Fallback to top-level tags if structure is different
        asset["tags"] = tag_objects
    
    # Edit the asset (wrap in 'asset' key for API)
    edit_path = f"{cms_path}/api/v1/edit/{asset_type}/{asset_id}"
    p = requests.post(edit_path, params=auth, json={"asset": asset})
    
    return p.json()


def add_asset_tags(cms_path: str, auth: dict, asset_id: str, asset_type: str, tags: List[str]) -> Dict[str, Any]:
    """Add tags to a specific asset (preserving existing tags)
    
    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_id: ID of the asset
        :asset_type: Type of the asset (page, file, etc.)
        :tags: List of tag names to add
    """
    # First, get the current asset data
    read_path = f"{cms_path}/api/v1/read/{asset_type}/{asset_id}"
    p = requests.post(read_path, params=auth)
    result = p.json()
    
    if not result.get("success"):
        return result
    
    # Get existing tags from the correct location
    asset = result["asset"]
    if asset_type in asset:
        existing_tags = asset[asset_type].get("tags", [])
    else:
        existing_tags = asset.get("tags", [])
    
    existing_tag_names = {tag.get("name") for tag in existing_tags if tag.get("name")}
    
    # Add new tags (avoiding duplicates)
    new_tags = []
    for tag in tags:
        if tag not in existing_tag_names:
            new_tags.append({"name": tag})
    
    # Combine existing and new tags
    all_tags = existing_tags + new_tags
    
    # Update the asset with all tags in the correct location
    if asset_type in asset:
        asset[asset_type]["tags"] = all_tags
    else:
        asset["tags"] = all_tags
    
    # Edit the asset (wrap in 'asset' key for API)
    edit_path = f"{cms_path}/api/v1/edit/{asset_type}/{asset_id}"
    p = requests.post(edit_path, params=auth, json={"asset": asset})
    
    return p.json()


def remove_asset_tags(cms_path: str, auth: dict, asset_id: str, asset_type: str, tags: List[str]) -> Dict[str, Any]:
    """Remove tags from a specific asset
    
    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_id: ID of the asset
        :asset_type: Type of the asset (page, file, etc.)
        :tags: List of tag names to remove
    """
    # First, get the current asset data
    read_path = f"{cms_path}/api/v1/read/{asset_type}/{asset_id}"
    p = requests.post(read_path, params=auth)
    result = p.json()
    
    if not result.get("success"):
        return result
    
    # Get existing tags from the correct location and filter out the ones to remove
    asset = result["asset"]
    if asset_type in asset:
        existing_tags = asset[asset_type].get("tags", [])
    else:
        existing_tags = asset.get("tags", [])
    
    tags_to_remove = set(tags)
    
    # Keep only tags that are not in the removal list
    filtered_tags = [
        tag for tag in existing_tags 
        if tag.get("name") not in tags_to_remove
    ]
    
    # Update the asset with filtered tags in the correct location
    if asset_type in asset:
        asset[asset_type]["tags"] = filtered_tags
    else:
        asset["tags"] = filtered_tags
    
    # Edit the asset (wrap in 'asset' key for API)
    edit_path = f"{cms_path}/api/v1/edit/{asset_type}/{asset_id}"
    p = requests.post(edit_path, params=auth, json={"asset": asset})
    
    return p.json()


def search_assets_by_tag(cms_path: str, auth: dict, tag: str, site_name: Optional[str] = None, asset_types: Optional[List[str]] = None) -> Dict[str, Any]:
    """Search for assets that have a specific tag
    
    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :tag: Tag name to search for
        :site_name: Optional site name to limit search to
        :asset_types: Optional list of asset types to search (page, file, etc.)
    """
    from .search import search_assets
    
    search_fields = ["tags"]
    if asset_types:
        search_types = asset_types
    else:
        search_types = None
    
    result = search_assets(cms_path, auth, tag, site_name, search_fields, search_types)
    
    # Convert the search result format to match what the CLI expects
    if result.get("success"):
        return {
            "success": True,
            "assets": result.get("matches", [])
        }
    else:
        return result


def get_all_tags(cms_path: str, auth: dict, site_name: Optional[str] = None) -> Dict[str, Any]:
    """Get all unique tags used in a site
    
    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :site_name: Optional site name to limit search to
    """
    # This would require a more complex search or listing all assets
    # For now, return a placeholder response
    return {
        "success": False,
        "message": "get_all_tags not yet implemented - requires listing all assets to extract unique tags"
    }

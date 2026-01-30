"""
Core operations for Cascade Server REST API

Handles basic CRUD operations: Create, Read, Update, Delete
"""

import requests
from typing import Optional, Dict, Any, Union


def read_single_asset(
    cms_path: str, auth: dict, asset_type: str, asset_id: str
) -> Union[Dict[str, Any], bool]:
    """Use Cascade Server's REST API read endpoint to read a single asset

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string indicating asset type ("folder", "page", "file", etc.)
        :asset_id: string in r.json()['asset']['id']
    """
    if not asset_id:
        print(f"Error reading single asset: {asset_id}")
        return False

    page_id_path = f"{cms_path}/api/v1/read/{asset_type}/{asset_id}"
    p = requests.post(page_id_path, params=auth)

    if p.status_code == 200:
        print(f"Success reading single asset: {asset_id}")
        return p.json()
    else:
        print(f"Error reading single asset: {asset_id}")
        return False


def read_asset_by_path(
    cms_path: str, auth: dict, asset_type: str, site_name: str, asset_path: str
) -> Union[Dict[str, Any], bool]:
    """Use Cascade Server's REST API read endpoint to read a single asset by path

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string indicating asset type
        :site_name: string site name
        :asset_path: string path to the asset
    """
    asset_path_url = f"{cms_path}/api/v1/read/{asset_type}/{site_name}{asset_path}"
    p = requests.post(asset_path_url, params=auth)

    if p.status_code == 200:
        print(f"Success reading asset at path: {asset_path}")
        return p.json()
    else:
        print(f"Error reading asset at path: {asset_path}")
        return False


def create_asset(
    cms_path: str, auth: dict, asset_type: str, asset_data: dict
) -> Dict[str, Any]:
    """Use Cascade Server's REST API create endpoint to create a new asset

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string indicating asset type (page, folder, file, etc.)
        :asset_data: dict containing the asset data
    """
    create_path = f"{cms_path}/api/v1/create"
    payload = {"asset": {asset_type: asset_data}}

    p = requests.post(create_path, params=auth, json=payload)
    print(f"Creating {asset_type}", p.json())
    return p.json()


def edit_single_asset(
    cms_path: str, auth: dict, asset_type: str, asset_id: str, payload: dict
) -> Dict[str, Any]:
    """Use Cascade Server's REST API edit endpoint to edit a single asset

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string indicating asset type ("folder", "page", "file", etc.)
        :asset_id: string in r.json()['asset']['id']
        :payload: dict representation of asset object
    """
    page_edit_path = f"{cms_path}/api/v1/edit/{asset_type}/{asset_id}"
    update = requests.post(page_edit_path, params=auth, json=payload)
    return update.json()


def delete_asset(
    cms_path: str, auth: dict, asset_type: str, asset_id: str, unpublish: bool = True
) -> Dict[str, Any]:
    """Use Cascade Server's REST API delete endpoint to delete an asset

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string indicating asset type
        :asset_id: string ID of the asset to delete
        :unpublish: boolean indicating whether to unpublish the asset before deletion
    """
    delete_path = f"{cms_path}/api/v1/delete/{asset_type}/{asset_id}"
    delete_parameters = {
        "deleteParameters": {"unpublish": unpublish, "doWorkflow": False}
    }

    p = requests.post(delete_path, params=auth, json=delete_parameters)
    print(f"Deleting {asset_type} {asset_id}", p.json())
    return p.json()


def copy_single_asset(
    cms_path: str,
    auth: dict,
    asset_type: str,
    asset_id: str,
    new_path: str,
    new_name: str,
    site_name: str,
) -> Dict[str, Any]:
    """Use Cascade Server's REST API copy endpoint to copy a single asset

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string indicating asset type ("folder", "page", "file", etc.)
        :asset_id: string in r.json()['asset']['id']
        :new_path: string indicating destination folder path with no trailing slash
        :new_name: string indicating asset name; use file extensions for files
        :site_name: string in r.json()['asset']['siteName']
    """
    asset_id_path = f"{cms_path}/api/v1/copy/{asset_type}/{asset_id}"
    copy_parameters = {
        "copyParameters": {
            "destinationContainerIdentifier": {
                "path": {"path": new_path, "siteName": site_name},
                "type": "folder",
            },
            "doWorkflow": "false",
            "newName": new_name,
        }
    }
    p = requests.post(asset_id_path, params=auth, json=copy_parameters)
    print(new_name, p.json())
    return p.json()


def copy_asset_by_id(
    cms_path: str,
    auth: dict,
    asset_type: str,
    asset_id: str,
    destination_folder_id: str,
    new_name: str,
) -> Dict[str, Any]:
    """Use Cascade Server's REST API copy endpoint to copy an asset using folder ID
    
    This is the Asset Factory pattern - copying a base/template asset to create new assets.
    Uses folder ID instead of path for destination.

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string indicating asset type ("folder", "page", "file", etc.)
        :asset_id: string ID of the base asset to copy
        :destination_folder_id: ID of the destination folder
        :new_name: string name for the new copied asset
    """
    copy_path = f"{cms_path}/api/v1/copy/{asset_type}/{asset_id}"
    
    copy_parameters = {
        "copyParameters": {
            "destinationContainerIdentifier": {
                "id": destination_folder_id,
                "type": "folder",
            },
            "doWorkflow": False,
            "newName": new_name,
        }
    }
    
    p = requests.post(copy_path, params=auth, json=copy_parameters)
    result = p.json()
    
    if result.get("success"):
        print(f"✓ Copied {asset_type}: {new_name}")
    else:
        error_msg = result.get('message', 'Unknown error')
        
        # Check for common collision/duplicate errors
        if 'already exists' in error_msg.lower() or 'duplicate' in error_msg.lower():
            print(f"⚠️  Collision detected - {asset_type} '{new_name}' already exists")
            print(f"   Message: {error_msg}")
        else:
            print(f"✗ Failed to copy {asset_type}: {error_msg}")
    
    return result


def move_asset(
    cms_path: str,
    auth: dict,
    asset_type: str,
    asset_id: str,
    destination_folder_id: str,
    new_name: Optional[str] = None,
    unpublish: bool = False,
) -> Dict[str, Any]:
    """Use Cascade Server's REST API move endpoint to move/rename an asset

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string indicating asset type
        :asset_id: string ID of the asset to move
        :destination_folder_id: ID of the folder to move the asset to
        :new_name: optional new name for the asset (rename)
        :unpublish: whether to unpublish the asset from its current location
    """
    move_path = f"{cms_path}/api/v1/move/{asset_type}/{asset_id}"

    move_parameters = {
        "moveParameters": {
            "destinationContainerIdentifier": {
                "id": destination_folder_id,
                "type": "folder",
            },
            "doWorkflow": False,
            "unpublish": unpublish,
        }
    }

    if new_name:
        move_parameters["moveParameters"]["newName"] = new_name

    p = requests.post(move_path, params=auth, json=move_parameters)
    print(f"Moving {asset_type} {asset_id}", p.json())
    return p.json()

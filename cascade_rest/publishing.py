"""
Publishing operations for Cascade Server REST API

Handles publishing, unpublishing, and workflow operations
"""

import requests
from typing import Optional, List, Dict, Any, Union


def publish_asset(
    cms_path: str,
    auth: dict,
    asset_type: str,
    asset_id: str,
    destinations: Optional[List[str]] = None,
    unpublish: bool = False,
) -> Dict[str, Any]:
    """Use Cascade Server's REST API publish endpoint to publish an asset

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string indicating asset type
        :asset_id: string ID of the asset to publish
        :destinations: list of destination IDs (optional)
        :unpublish: boolean to indicate unpublish instead of publish
    """
    publish_path = f"{cms_path}/api/v1/publish/{asset_type}/{asset_id}"

    publish_info: Dict[str, Any] = {"publishInformation": {"unpublish": unpublish}}

    if destinations:
        publish_info["publishInformation"]["destinations"] = [
            {"id": dest_id, "type": "destination"} for dest_id in destinations
        ]

    p = requests.post(publish_path, params=auth, json=publish_info)
    action = "Unpublishing" if unpublish else "Publishing"
    print(f"{action} {asset_type} {asset_id}", p.json())
    return p.json()


def check_out_asset(
    cms_path: str, auth: dict, asset_type: str, asset_id: str
) -> Dict[str, Any]:
    """Use Cascade Server's REST API checkout endpoint to check out an asset

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string indicating asset type
        :asset_id: string ID of the asset to check out
    """
    checkout_path = f"{cms_path}/api/v1/checkOut/{asset_type}/{asset_id}"

    p = requests.post(checkout_path, params=auth)
    print(f"Checking out {asset_type} {asset_id}", p.json())
    return p.json()


def check_in_asset(
    cms_path: str, auth: dict, asset_type: str, asset_id: str, comments: str = ""
) -> Dict[str, Any]:
    """Use Cascade Server's REST API checkin endpoint to check in an asset

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string indicating asset type
        :asset_id: string ID of the asset to check in
        :comments: optional comments about the check-in
    """
    checkin_path = f"{cms_path}/api/v1/checkIn/{asset_type}/{asset_id}"

    payload = {}
    if comments:
        payload["comments"] = comments

    p = requests.post(checkin_path, params=auth, json=payload)
    print(f"Checking in {asset_type} {asset_id}", p.json())
    return p.json()


def list_subscribers_single_asset(
    cms_path: str, auth: dict, asset_type: str, asset_id: str
) -> Union[Dict[str, Any], bool]:
    """Use Cascade Server's REST API read endpoint to list subscribers for a single asset

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string indicating asset type ("folder", "page", "file", etc.)
        :asset_id: string in r.json()['asset']['id']
    """
    if not asset_id:
        print(f"Error reading single asset: {asset_id}")
        return False

    page_id_path = f"{cms_path}/api/v1/listSubscribers/{asset_type}/{asset_id}"
    p = requests.post(page_id_path, params=auth)
    print(f"Success reading single asset: {asset_id}")
    return p.json()

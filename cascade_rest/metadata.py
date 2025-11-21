"""
Metadata operations for Cascade Server REST API

Handles metadata field operations, tags, and dynamic fields
"""

import requests
from typing import Union, List, Dict, Any, Optional
from .core import read_single_asset, edit_single_asset
from .utils import report


# Allowed metadata field names
METADATA_ALLOWED_KEYS = [
    "displayName",
    "title",
    "summary",
    "teaser",
    "keywords",
    "metaDescription",
    "author",
]


def read_single_asset_metadata_value(
    cms_path: str,
    auth: dict,
    asset_type: str,
    asset: Union[str, tuple],
    field_name: str,
) -> Union[str, bool]:
    """Read in a single Cascade Server asset and get a metadata field value

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string ('page', 'folder', etc)
        :asset: string or tuple containing the asset ID in [0] position
        :field_name: string of the metadata field name to search for
    """
    if field_name not in METADATA_ALLOWED_KEYS:
        print("idx_error", asset, {})
        return False

    if isinstance(asset, (list, tuple)):
        asset_id = asset[0]
    else:
        asset_id = str(asset)

    page_id_path = f"{cms_path}/api/v1/read/{asset_type}/{asset_id}"
    p = requests.post(page_id_path, params=auth)
    payload = p.json()
    title = payload["asset"][asset_type]["metadata"]["title"]
    metadata_value = payload["asset"][asset_type]["metadata"][field_name]
    print(title, asset_id, field_name, metadata_value)
    return metadata_value


def set_single_asset_metadata_value(
    cms_path: str,
    auth: dict,
    asset_type: str,
    asset: Union[str, tuple],
    field_name: str,
    set_value: str,
) -> Union[Dict[str, Any], bool]:
    """Read in a single Cascade Server asset and set a metadata field value

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string ('page', 'folder', etc)
        :asset: string or tuple containing the asset ID in [0] position
        :field_name: string of the metadata field name to set
        :set_value: string of the replacement field value
    """
    if field_name not in METADATA_ALLOWED_KEYS:
        print("idx_error", asset, {})
        return False

    if isinstance(asset, (list, tuple)):
        asset_id = asset[0]
    else:
        asset_id = str(asset)

    page_id_path = f"{cms_path}/api/v1/read/{asset_type}/{asset_id}"
    p = requests.post(page_id_path, params=auth)
    payload = p.json()
    existing_value = payload["asset"][asset_type]["metadata"][field_name]
    payload["asset"][asset_type]["metadata"][field_name] = set_value

    page_edit_path = f"{cms_path}/api/v1/edit/{asset_type}/{asset_id}"

    try:
        update = requests.post(page_edit_path, params=auth, json=payload)
        if existing_value == "":
            print("set", asset, update.json())
        else:
            print("updated", asset, update.json())
        return update.json()

    except IndexError:
        print("idx_error", asset, {})
        return False
    except Exception as e:
        print("error", asset, {"error": str(e)})
        return False


def get_dynamic_field(name: str, field_list: List[Dict[str, Any]]) -> Union[int, bool]:
    """Find the index of a dynamic metadata field by name"""
    for idx, field in enumerate(field_list):
        if name in field.values():
            return idx
    return False


def update_single_asset_dynamic_metadata_value(
    cms_path: str,
    auth: dict,
    asset_type: str,
    asset: Union[str, tuple],
    field_name: str,
    match_value: str,
    new_value: str,
) -> bool:
    """Update a dynamic metadata field value

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string ('page', 'folder', etc)
        :asset: string or tuple containing the asset ID in [0] position
        :field_name: string of the dynamic metadata field name to search for
        :match_value: string of the field value to replace
        :new_value: string of the replacement field value
    """
    if isinstance(asset, (list, tuple)):
        asset_id = asset[0]
    else:
        asset_id = str(asset)

    page_id_path = f"{cms_path}/api/v1/read/{asset_type}/{asset_id}"
    p = requests.post(page_id_path, params=auth)
    payload = p.json()
    dynamic_fields = payload["asset"][asset_type]["metadata"]["dynamicFields"]

    field_idx = get_dynamic_field(field_name, dynamic_fields)
    if field_idx is not False:
        field_values = dynamic_fields[field_idx]["fieldValues"]
    else:
        print("field_error", asset_id, {"field": field_idx})
        return False

    page_edit_path = f"{cms_path}/api/v1/edit/{asset_type}/{asset_id}"

    try:
        if len(field_values) > 0:
            if field_values[0]["value"] == new_value:
                report("unchanged", asset, {})
            elif field_values[0]["value"] == match_value:
                field_values[0]["value"] = new_value
                update = requests.post(page_edit_path, params=auth, json=payload)
                print("updated", asset, update.json())
        else:
            field_values.append({"value": new_value})
            update = requests.post(page_edit_path, params=auth, json=payload)
            print("appended", asset, update.json())
        return True

    except IndexError:
        print("idx_error", asset, {})
        return False
    except Exception as e:
        print("error", asset, {"error": str(e)})
        return False


def set_or_replace_single_asset_tag(
    cms_path: str,
    auth: dict,
    asset_type: str,
    asset_id: str,
    old_tag_name: str,
    new_tag_name: str,
) -> Union[Dict[str, Any], bool]:
    """Replace or add a tag to an asset

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: string ('page', 'folder', etc)
        :asset_id: string in r.json()['asset']['id']
        :old_tag_name: string of the existing tag_name to replace if present
        :new_tag_name: string of the new or replacement tag name
    """
    payload = read_single_asset(cms_path, auth, asset_type, asset_id)
    if not payload:
        return False

    if not isinstance(payload, dict) or "asset" not in payload:
        return False

    asset_data = payload["asset"]
    if not isinstance(asset_data, dict) or asset_type not in asset_data:
        return False

    payload_tags = asset_data[asset_type]["tags"]
    found_old_tag_name = False

    if len(payload_tags) > 0:
        for idx, tag in enumerate(payload_tags):
            if new_tag_name in tag.get("name", ""):
                return False  # Tag already exists
            if old_tag_name in tag.get("name", ""):
                payload_tags[idx]["name"] = new_tag_name
                found_old_tag_name = True
        if not found_old_tag_name:
            payload_tags.extend([{"name": new_tag_name}])
    else:
        payload_tags = [{"name": new_tag_name}]
    if isinstance(payload, dict):
        payload["asset"][asset_type]["tags"] = payload_tags
        return edit_single_asset(cms_path, auth, asset_type, asset_id, payload)
    return False

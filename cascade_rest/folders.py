"""
Folder operations for Cascade Server REST API

Handles folder navigation and structured data operations
"""

import requests
from typing import List, Dict, Any, Optional, Union


def get_folder_children(
    cms_path: str, auth: dict, folder_id: str
) -> List[Dict[str, Any]]:
    """Use Cascade Server's REST API read endpoint to read a folder asset
    and return a list of child assets

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :folder_id: string in r.json()['asset']['id']
    """
    api_path = f"{cms_path}/api/v1/read/folder/{folder_id}"
    p = requests.post(api_path, params=auth)
    payload = p.json()
    children = payload["asset"]["folder"]["children"]
    return children


def get_folder_child_id_by_name(
    cms_path: str, auth: dict, folder_id: str, child_name: str
) -> str:
    """Get a child asset ID by name from a folder

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :folder_id: string in r.json()['asset']['id']
        :child_name: string asset name, match isolated from end of path
    """
    for child in get_folder_children(cms_path, auth, folder_id):
        if child_name == child["path"]["path"].split("/")[-1]:
            return child["id"]
    return ""


def get_structured_data_node(
    node_type: str,
    node_identifier: str,
    field_list: List[Dict[str, Any]],
    sdn_type_id_value: Optional[List[str]] = None,
) -> Union[int, bool]:
    """Find a structured data node by type and identifier

    Returns an index from list of dicts where 'type' and 'identifier'
    match supplied parameters. Optional sdn_type_id_value list will check
    structuredDataNodes list for dict containing 'type' [0], 'identifier' [1]
    and non-empty field of name [2]
    """
    for idx, field in enumerate(field_list):
        if (
            field.get("type", False) == node_type
            and field.get("identifier", False) == node_identifier
        ):
            if not sdn_type_id_value:
                print(idx)
                return idx
            else:
                for item in field.get("structuredDataNodes", []):
                    if (
                        item.get("type", False) == sdn_type_id_value[0]
                        and item.get("identifier", False) == sdn_type_id_value[1]
                        and item.get(sdn_type_id_value[2], "::ERROR::") != ""
                    ):
                        print(idx)
                        return idx
    return False


def find_structured_data_node_idx_single(
    node_type: str,
    node_identifier: str,
    field_list: List[Dict[str, Any]],
    sdn_type_id_value: Optional[List[str]] = None,
) -> Union[int, bool]:
    """Returns an int from list of dicts where 'type' and 'identifier'
    match supplied parameters. Optional sdn_type_id_value list will check
    structuredDataNodes list for dict containing 'type' [0], 'identifier' [1]
    and non-empty field of name [2]
    """
    for idx, field in enumerate(field_list):
        if (
            field.get("type", False) == node_type
            and field.get("identifier", False) == node_identifier
        ):
            if not sdn_type_id_value:
                print(idx)
                return idx
            else:
                for item in field.get("structuredDataNodes", []):
                    if (
                        item.get("type", False) == sdn_type_id_value[0]
                        and item.get("identifier", False) == sdn_type_id_value[1]
                        and item.get(sdn_type_id_value[2], "::ERROR::") != ""
                    ):
                        print(idx)
                        return idx
    return False


def find_structured_data_node_idx_collection(
    node_type: str,
    node_identifier: str,
    field_list: List[Dict[str, Any]],
    sdn_type_id_value: Optional[List[str]] = None,
) -> Union[int, bool]:
    """Returns an index from list of dicts where 'type' and 'identifier'
    match supplied parameters. Optional sdn_type_id_value list will check
    structuredDataNodes list for dict containing 'type' [0], 'identifier' [1]
    and non-empty field of name [2]
    """
    for idx, field in enumerate(field_list):
        if (
            field.get("type", False) == node_type
            and field.get("identifier", False) == node_identifier
        ):
            if not sdn_type_id_value:
                print(idx)
                return idx
            else:
                for item in field.get("structuredDataNodes", []):
                    if (
                        item.get("type", False) == sdn_type_id_value[0]
                        and item.get("identifier", False) == sdn_type_id_value[1]
                        and item.get(sdn_type_id_value[2], "::ERROR::") != ""
                    ):
                        print(idx)
                        return idx
    return False

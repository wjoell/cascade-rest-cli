"""
Search and discovery operations for Cascade Server REST API

Handles searching, site listing, and audit operations
"""

import requests
from datetime import datetime
from typing import Optional, List, Dict, Any


def search_assets(
    cms_path: str,
    auth: dict,
    search_terms: str,
    site_name: Optional[str] = None,
    search_fields: Optional[List[str]] = None,
    search_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Use Cascade Server's REST API search endpoint to find assets

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :search_terms: string to search for
        :site_name: optional site name to limit search to
        :search_fields: optional list of fields to search in (name, path, displayName, etc.)
        :search_types: optional list of asset types to search (page, folder, file, etc.)
    """
    search_path = f"{cms_path}/api/v1/search"

    search_info: Dict[str, Any] = {"searchInformation": {"searchTerms": search_terms}}

    if site_name:
        search_info["searchInformation"]["siteName"] = site_name

    if search_fields:
        search_info["searchInformation"]["searchFields"] = search_fields

    if search_types:
        search_info["searchInformation"]["searchTypes"] = search_types

    p = requests.post(search_path, params=auth, json=search_info)
    return p.json()


def list_sites(cms_path: str, auth: dict) -> Dict[str, Any]:
    """Use Cascade Server's REST API listSites endpoint to get a list of all sites

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
    """
    sites_path = f"{cms_path}/api/v1/listSites"

    p = requests.post(sites_path, params=auth)
    return p.json()


def read_audits(
    cms_path: str,
    auth: dict,
    asset_type: Optional[str] = None,
    asset_id: Optional[str] = None,
    username: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    audit_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Use Cascade Server's REST API readAudits endpoint to get audit information

    Parameters:
        :cms_path: URI to Cascade Server instance
        :auth: dict object with Cascade Server credentials
        :asset_type: optional asset type for filtering audits
        :asset_id: optional asset ID for filtering audits
        :username: optional username for filtering audits
        :start_date: optional start date for filtering audits
        :end_date: optional end date for filtering audits
        :audit_type: optional audit type for filtering (edit, publish, etc.)
    """
    audit_path = f"{cms_path}/api/v1/readAudits"

    audit_params = {"auditParameters": {}}

    # Add identifier if both asset_type and asset_id are provided
    if asset_type and asset_id:
        audit_params["auditParameters"]["identifier"] = {
            "type": asset_type,
            "id": asset_id,
        }

    if username:
        audit_params["auditParameters"]["username"] = username

    if start_date:
        audit_params["auditParameters"]["startDate"] = start_date.strftime(
            "%b %d, %Y %H:%M:%S %p"
        )

    if end_date:
        audit_params["auditParameters"]["endDate"] = end_date.strftime(
            "%b %d, %Y %H:%M:%S %p"
        )

    if audit_type:
        audit_params["auditParameters"]["auditType"] = audit_type

    p = requests.post(audit_path, params=auth, json=audit_params)
    print("Reading audits", p.json())
    return p.json()

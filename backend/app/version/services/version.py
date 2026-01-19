from typing import Any
from typing import Dict
from typing import Optional

import httpx
from loguru import logger
from packaging.version import Version

# Current version - update this with each release
CURRENT_VERSION = "0.1.25"
VERSION_CHECK_URL = "https://api.github.com/repos/socfortress/CoPilot/releases/latest"


async def get_latest_version() -> Optional[Dict[str, Any]]:
    """
    Fetch the latest version from GitHub releases

    Returns:
        dict: Release information including version, url, and body or None if unable to fetch
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(VERSION_CHECK_URL, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                return {
                    "tag_name": data.get("tag_name", "").lstrip("v"),
                    "html_url": data.get("html_url", ""),
                    "published_at": data.get("published_at", ""),
                    "body": data.get("body", ""),
                    "name": data.get("name", "").lstrip("v"),
                }
    except Exception as e:
        logger.warning(f"Failed to fetch latest version: {e}")
    return None


async def check_version_outdated() -> dict:
    """
    Check if current version is outdated

    Returns:
        dict: Version check results
    """
    release_info = await get_latest_version()

    if not release_info:
        return {
            "success": False,
            "message": "Unable to check for updates",
            "current_version": CURRENT_VERSION,
            "latest_version": None,
            "is_outdated": False,
            "release_url": None,
            "release_notes": None,
            "published_at": None,
        }

    latest_version = release_info.get("tag_name")

    try:
        current = Version(CURRENT_VERSION)
        latest = Version(latest_version)
        is_outdated = current < latest

        return {
            "success": True,
            "message": f"New version v{latest_version} available!" if is_outdated else "You're up to date",
            "current_version": CURRENT_VERSION,
            "latest_version": latest_version,
            "is_outdated": is_outdated,
            "release_url": release_info.get("html_url"),
            "release_notes": release_info.get("body"),
            "published_at": release_info.get("published_at"),
        }
    except Exception as e:
        logger.error(f"Error comparing versions: {e}")
        return {
            "success": False,
            "message": "Error checking version",
            "current_version": CURRENT_VERSION,
            "latest_version": latest_version,
            "is_outdated": False,
            "release_url": release_info.get("html_url"),
            "release_notes": None,
            "published_at": None,
        }

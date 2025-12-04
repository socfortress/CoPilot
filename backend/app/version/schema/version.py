from typing import Optional

from pydantic import BaseModel


class VersionCheckResponse(BaseModel):
    success: bool
    message: str
    current_version: str
    latest_version: Optional[str]
    is_outdated: bool
    release_url: Optional[str] = None
    release_notes: Optional[str] = None
    published_at: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "New version v0.1.5 available!",
                "current_version": "0.1.4",
                "latest_version": "0.1.5",
                "is_outdated": True,
                "release_url": "https://github.com/socfortress/CoPilot/releases/tag/v0.1.5",
                "release_notes": "## What's Changed\n* Feature 1\n* Feature 2",
                "published_at": "2025-12-03T18:48:20Z",
            },
        }

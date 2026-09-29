"""Validation of the branding fields shared by the global settings and the per-customer overrides.

One definition, so an override can never carry a payload the global settings would
have rejected (or the other way round). An empty value normalises to None.
"""
import base64
import re
from typing import Optional

from fastapi import HTTPException

ALLOWED_LOGO_MIME_TYPES = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/svg+xml", "image/webp"]
MAX_LOGO_BASE64_BYTES = 5 * 1024 * 1024  # 5MB base64 == ~3.75MB original

_HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_BASE64 = re.compile(r"^[A-Za-z0-9+/]*={0,2}$")


def validate_brand_color(value: Optional[str]) -> Optional[str]:
    """A hex colour (#RGB or #RRGGBB), lower-cased."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not _HEX_COLOR.match(value):
        raise HTTPException(status_code=400, detail="Invalid brand_color. Expected a hex color like #RGB or #RRGGBB")
    return value.lower()


def validate_logo_base64(value: Optional[str]) -> Optional[str]:
    """Base64 logo data within the size limit; a data URL is reduced to its payload."""
    if value is None:
        return None
    if value.startswith("data:"):
        value = value.split(",", 1)[1] if "," in value else value
    if not value:
        return None
    if len(value) > MAX_LOGO_BASE64_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Logo file too large. Maximum size is {MAX_LOGO_BASE64_BYTES // (1024 * 1024)}MB (base64-encoded)",
        )
    if not _BASE64.match(value):
        raise HTTPException(status_code=400, detail="Invalid base64 encoded string for logo_base64")
    try:
        base64.b64decode(value)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 data - cannot decode")
    return value


def validate_logo_mime_type(value: Optional[str]) -> Optional[str]:
    """One of the image types a logo may be served as."""
    if value is None or not value:
        return None
    if value not in ALLOWED_LOGO_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid MIME type. Allowed types are: {', '.join(ALLOWED_LOGO_MIME_TYPES)}")
    return value

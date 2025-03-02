from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import xml.etree.ElementTree as ET
from pydantic import BaseModel

from app.data_store.data_store_operations import upload_sysmon_config, download_sysmon_config, list_sysmon_configs


async def validate_sysmon_config(xml_content: str) -> None:
    """
    Validate a Sysmon configuration XML string.

    Args:
        xml_content: The XML content as a string

    Raises:
        HTTPException: If validation fails
    """
    try:
        root = ET.fromstring(xml_content)

        # Verify root element
        if root.tag != 'Sysmon':
            raise HTTPException(status_code=400, detail="Root element must be 'Sysmon'")

        # Verify EventFiltering element
        event_filtering = root.find("EventFiltering")
        if event_filtering is None:
            raise HTTPException(status_code=400, detail="Missing required 'EventFiltering' element")

        # Check for direct text content in EventFiltering (catches "adsf" issue)
        if event_filtering.text and event_filtering.text.strip():
            raise HTTPException(
                status_code=400,
                detail="Invalid text content found directly in EventFiltering element"
            )

        # Check for RuleGroup elements
        rule_groups = event_filtering.findall("RuleGroup")
        if not rule_groups:
            raise HTTPException(
                status_code=400,
                detail="EventFiltering must contain at least one RuleGroup"
            )

        # Check that each RuleGroup has required attributes
        for rule_group in rule_groups:
            if not rule_group.attrib.get("groupRelation"):
                raise HTTPException(
                    status_code=400,
                    detail="RuleGroup must have 'groupRelation' attribute"
                )

    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML syntax: {str(e)}")

async def check_config_exists(customer_code: str) -> bool:
    """Check if a sysmon config exists for the given customer"""
    try:
        await download_sysmon_config(customer_code)
        return True
    except HTTPException as e:
        if e.status_code == 404:
            return False
        raise

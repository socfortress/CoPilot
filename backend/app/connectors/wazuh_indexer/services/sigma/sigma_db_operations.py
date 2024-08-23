import os
import re
from datetime import datetime
from datetime import timedelta
from typing import List

import yaml
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.wazuh_indexer.models.sigma import SigmaQuery
from app.connectors.wazuh_indexer.schema.sigma import CreateSigmaQuery
from app.connectors.wazuh_indexer.schema.sigma import SigmaRuleUploadRequest
from app.connectors.wazuh_indexer.services.sigma.generate_query import (
    create_sigma_query_from_rule,
)
from app.connectors.wazuh_indexer.services.sigma.sigma_download import find_yaml_files


def parse_time_interval(interval: str) -> timedelta:
    match = re.match(r"(\d+)([smhd])", interval)
    if not match:
        raise ValueError(f"Invalid time interval format: {interval}")
    value, unit = match.groups()
    value = int(value)
    if unit == "s":
        return timedelta(seconds=value)
    elif unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    else:
        raise ValueError(f"Invalid time unit: {unit}")


def check_level(rule_levels: list, file_path):
    delete_file = False
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            if line.startswith("level:"):
                level = line.split(":")[1].strip()
                if level not in rule_levels:
                    delete_file = True
                    break
    if delete_file:
        logger.info(f"Deleting file: {file_path}")
        os.remove(file_path)  # delete the file if its level is not high or critical
        return False
    return True


def validate_title(title):
    # Check if title is a string
    if not isinstance(title, str):
        return False

    # Check if title length is within the limit
    if len(title) > 65535:
        return False

    # Check if title contains only allowed characters
    pattern = re.compile(r"^[a-zA-Z0-9,.\-_/ ]*$")
    if not pattern.match(title):
        return False

    return True


async def extract_title(file_path):
    # Load the YAML file
    with open(file_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    # Extract the title field
    title = data.get("title", "")

    # Validate the title
    if not validate_title(title):
        # Remove disallowed characters
        cleaned_title = re.sub(r"[^a-zA-Z0-9,.\-_/ ]", "", title)

        # Update the title field in the YAML data
        data["title"] = cleaned_title

        # Write the updated YAML data back to the file
        with open(file_path, "w", encoding="utf-8") as file:
            yaml.safe_dump(data, file)

        return cleaned_title

    return title


async def get_sigma_query_by_id(
    db: AsyncSession,
    sigma_query_id: int,
) -> SigmaQuery:
    """
    Retrieves a Sigma query by ID.

    Args:
        db (AsyncSession): The database session.
        sigma_query_id (int): The ID of the Sigma query.

    Returns:
        SigmaQuery: The Sigma query.
    """
    # Retrieve the Sigma query
    sigma_query = await db.execute(select(SigmaQuery).filter_by(id=sigma_query_id))
    sigma_query = sigma_query.scalars().first()

    if not sigma_query:
        raise HTTPException(
            status_code=404,
            detail="The Sigma query does not exist.",
        )

    return sigma_query


async def list_sigma_queries(
    db: AsyncSession,
) -> List[SigmaQuery]:
    """
    Retrieves a list of Sigma queries.

    Args:
        db (AsyncSession): The database session.

    Returns:
        List[SigmaQuery]: A list of Sigma queries.
    """
    # Retrieve the Sigma queries
    sigma_queries = await db.execute(select(SigmaQuery))
    sigma_queries = sigma_queries.scalars().all()

    return sigma_queries


async def list_active_sigma_queries(
    db: AsyncSession,
) -> List[SigmaQuery]:
    """
    Retrieves a list of active Sigma queries.

    Args:
        db (AsyncSession): The database session.

    Returns:
        List[SigmaQuery]: A list of active Sigma queries.
    """
    # Retrieve the active Sigma queries
    sigma_queries = await db.execute(select(SigmaQuery).filter_by(active=True))
    sigma_queries = sigma_queries.scalars().all()

    return sigma_queries


async def list_inactive_sigma_queries(
    db: AsyncSession,
) -> List[SigmaQuery]:
    """
    Retrieves a list of inactive Sigma queries.

    Args:
        db (AsyncSession): The database session.

    Returns:
        List[SigmaQuery]: A list of inactive Sigma queries.
    """
    # Retrieve the inactive Sigma queries
    sigma_queries = await db.execute(select(SigmaQuery).filter_by(active=False))
    sigma_queries = sigma_queries.scalars().all()

    return sigma_queries


async def create_sigma_query(
    sigma_query: CreateSigmaQuery,
    db: AsyncSession,
) -> SigmaQuery:
    """
    Creates a Sigma query.

    Args:
        sigma_query (CreateSigmaQuery): The Sigma query to create.
        db (AsyncSession): The database session.

    Returns:
        SigmaQuery: The created Sigma query.
    """
    # Create the Sigma query
    new_sigma_query = SigmaQuery(
        rule_name=sigma_query.rule_name,
        rule_query=sigma_query.rule_query,
        active=sigma_query.active,
        time_interval=sigma_query.time_interval,
    )

    # Add the Sigma query to the database
    db.add(new_sigma_query)

    try:
        await db.commit()
    except IntegrityError as e:
        logger.error(f"Failed to create the Sigma query: {e}")
        raise HTTPException(
            status_code=400,
            detail="Failed to create the Sigma query.",
        )

    return new_sigma_query


async def read_sigma_rule(file: str) -> str:
    with open(file, "r", encoding="utf-8") as f:
        return f.read()


async def get_existing_query(rule_name: str, db: AsyncSession):
    result = await db.execute(select(SigmaQuery).filter_by(rule_name=rule_name))
    return result.scalars().first()


async def update_sigma_query(existing_query: SigmaQuery, new_query: CreateSigmaQuery, db: AsyncSession):
    existing_query.rule_query = new_query.rule_query
    existing_query.active = new_query.active
    existing_query.time_interval = new_query.time_interval
    await db.commit()


async def process_sigma_file(file: str, db: AsyncSession):
    rule = await read_sigma_rule(file)
    title = await extract_title(file)
    query = await create_sigma_query_from_rule(rule)

    new_query = CreateSigmaQuery(
        rule_name=title,
        rule_query=query.query.bool.must[0].query_string.query,
        active=False,
        time_interval="5m",
    )

    existing_query = await get_existing_query(title, db)
    if existing_query:
        logger.info(f"Updating existing Sigma query: {title}")
        await update_sigma_query(existing_query, new_query, db)
    else:
        logger.info(f"Creating new Sigma query: {title}")
        await create_sigma_query(new_query, db)


async def add_sigma_queries_to_db(request: SigmaRuleUploadRequest, db: AsyncSession):
    yaml_files = list(await find_yaml_files())
    # Only add the CRITICAL Severity SIGMA files
    sigma_files = [file for file in yaml_files if check_level(request.rule_levels, file)]
    for file in sigma_files:
        await process_sigma_file(file, db)
    return None


async def delete_query_from_db(query, db: AsyncSession):
    try:
        await db.delete(query)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to delete the Sigma query: {e}")
        raise HTTPException(
            status_code=400,
            detail="Failed to delete the Sigma query.",
        )


async def delete_sigma_rule(rule_name: str, db: AsyncSession):
    query = await get_existing_query(rule_name, db)
    if query:
        await delete_query_from_db(query, db)
    else:
        raise HTTPException(
            status_code=404,
            detail="The Sigma rule does not exist.",
        )
    return None


async def set_sigma_query_active(rule_name: str, active: bool, db: AsyncSession):
    query = await get_existing_query(rule_name, db)
    if query:
        query.active = active
        query.last_updated = datetime.now()
        await db.commit()
    else:
        raise HTTPException(
            status_code=404,
            detail="The Sigma rule does not exist.",
        )
    return query


async def update_sigma_time_interval(rule_name: str, time_interval: str, db: AsyncSession):
    query = await get_existing_query(rule_name, db)
    if query:
        query.time_interval = time_interval
        query.last_updated = datetime.now()
        await db.commit()
    else:
        raise HTTPException(
            status_code=404,
            detail="The Sigma rule does not exist.",
        )
    return query

from typing import List

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import delete
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.connectors.wazuh_indexer.models.sigma import SigmaQuery
from app.connectors.wazuh_indexer.schema.sigma import CreateSigmaQuery

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

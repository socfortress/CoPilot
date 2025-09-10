from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.vulnerabilities.schema.vulnerabilities import (
    WazuhVulnerabilityData,
    AgentVulnerabilityOut,
    AgentVulnerabilitiesResponse,
    VulnerabilitySyncResponse,
    VulnerabilityStatsResponse
)
from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
    collect_indices
)
from app.db.universal_models import AgentVulnerabilities, Agents


def process_wazuh_document(document: Dict[str, Any]) -> WazuhVulnerabilityData:
    """
    Process a single Wazuh vulnerability document from Indexer

    Args:
        document: Raw document from Wazuh Indexer index

    Returns:
        WazuhVulnerabilityData: Processed vulnerability data
    """
    logger.info(f"Processing vulnerability document ID: {document.get('_id', 'unknown')}")
    try:
        source = document.get("_source", {})
        vuln_data = source.get("vulnerability", {})
        package_data = source.get("package", {})
        score_data = vuln_data.get("score", {})

        # Parse detected_at timestamp
        detected_at_str = vuln_data.get("detected_at")
        detected_at = datetime.fromisoformat(detected_at_str.replace('Z', '+00:00')) if detected_at_str else datetime.utcnow()

        # Parse published_at timestamp if available
        published_at_str = vuln_data.get("published_at")
        published_at = None
        if published_at_str:
            try:
                published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Could not parse published_at: {published_at_str}")

        # Parse and limit references to first 5 items if comma-separated
        references_raw = vuln_data.get("reference")
        references = None
        if references_raw:
            if isinstance(references_raw, str) and ',' in references_raw:
                # Split by comma, take first 5 items, and rejoin
                reference_list = [ref.strip() for ref in references_raw.split(',')]
                references = ', '.join(reference_list[:5])
            else:
                references = str(references_raw)

            # Also ensure the references field doesn't exceed database column limit (2048 chars)
            if len(references) > 2048:
                references = references[:2045] + "..."

        return WazuhVulnerabilityData(
            cve_id=vuln_data.get("id", "UNKNOWN_CVE"),
            severity=vuln_data.get("severity", "UNKNOWN"),
            title=package_data.get("name", "Unknown Package"),
            references=references,
            detected_at=detected_at,
            published_at=published_at,
            base_score=score_data.get("base"),
            package_name=package_data.get("name"),
            package_version=package_data.get("version"),
            package_architecture=package_data.get("architecture")
        )
    except Exception as e:
        logger.error(f"Error processing vulnerability document: {e}")
        logger.error(f"Document: {document}")
        raise


async def get_vulnerabilities_indices() -> List[str]:
    """Get all vulnerability indices from Wazuh Indexer"""
    try:
        indices = await collect_indices(all_indices=True)
        vuln_indices = [
            index for index in indices.indices_list
            if index.startswith("wazuh-states-vulnerabilities")
        ]
        logger.info(f"Found {len(vuln_indices)} vulnerability indices")
        return vuln_indices
    except Exception as e:
        logger.error(f"Error collecting vulnerability indices: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect vulnerability indices: {e}"
        )


async def fetch_vulnerabilities_from_indexer(
    agent_name: Optional[str] = None,
    customer_code: Optional[str] = None,
    severity_filter: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Fetch vulnerabilities from Wazuh Indexer indices

    Args:
        agent_name: Optional agent name filter
        customer_code: Optional customer code filter (used for index filtering)
        severity_filter: Optional list of severities to filter by

    Returns:
        List of vulnerability documents
    """
    es_client = None
    try:
        es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
        indices = await get_vulnerabilities_indices()

        if not indices:
            logger.warning("No vulnerability indices found")
            return []

        vulnerabilities = []

        # Build query
        query = {"query": {"bool": {"must": []}}}

        if agent_name:
            query["query"]["bool"]["must"].append({"match": {"agent.name": agent_name}})

        if severity_filter:
            query["query"]["bool"]["must"].append(
                {"terms": {"vulnerability.severity": severity_filter}}
            )

        # If no filters, match all
        if not query["query"]["bool"]["must"]:
            query = {"query": {"match_all": {}}}

        # Search across all vulnerability indices
        for index in indices:
            try:
                # Use scroll for large result sets
                page = await es_client.search(index=index, body=query, scroll="2m", size=1000)
                scroll_id = page["_scroll_id"]
                scroll_size = len(page["hits"]["hits"])

                vulnerabilities.extend(page["hits"]["hits"])

                # Continue scrolling through results
                while scroll_size > 0:
                    page = await es_client.scroll(scroll_id=scroll_id, scroll="2m")
                    scroll_id = page["_scroll_id"]
                    scroll_size = len(page["hits"]["hits"])
                    vulnerabilities.extend(page["hits"]["hits"])

                # Clear the scroll context when done with this index
                try:
                    await es_client.clear_scroll(scroll_id=scroll_id)
                except Exception as clear_error:
                    logger.warning(f"Could not clear scroll context: {clear_error}")

            except Exception as index_error:
                logger.error(f"Error querying index {index}: {index_error}")
                continue

        logger.info(f"Fetched {len(vulnerabilities)} vulnerabilities from Indexer")
        return vulnerabilities

    except Exception as e:
        logger.error(f"Error fetching vulnerabilities from Indexer: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch vulnerabilities: {e}"
        )
    finally:
        # Ensure the Elasticsearch client session is properly closed
        if es_client:
            try:
                await es_client.close()
            except Exception as close_error:
                logger.warning(f"Error closing Elasticsearch client: {close_error}")


async def get_agent_by_name(db_session: AsyncSession, agent_name: str) -> Optional[Agents]:
    """Get agent from database by hostname/name"""
    try:
        result = await db_session.execute(
            select(Agents).filter(Agents.hostname == agent_name)
        )
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error fetching agent {agent_name}: {e}")
        return None


async def sync_vulnerabilities_for_agent(
    db_session: AsyncSession,
    agent_name: str,
    customer_code: Optional[str] = None
) -> VulnerabilitySyncResponse:
    """
    Sync vulnerabilities for a specific agent

    Args:
        db_session: Database session to use
        agent_name: Name of the agent to sync vulnerabilities for
        customer_code: Optional customer code override

    Returns:
        VulnerabilitySyncResponse with sync results
    """
    try:
        # Get agent from database using the session
        result = await db_session.execute(
            select(Agents).filter(Agents.hostname == agent_name)
        )
        agent = result.scalars().first()

        if not agent:
            return VulnerabilitySyncResponse(
                success=False,
                message=f"Agent {agent_name} not found in database",
                synced_count=0,
                errors=[f"Agent {agent_name} not found"]
            )

        # Use agent's customer code if not provided
        if not customer_code:
            customer_code = agent.customer_code

        # Cache agent values to prevent lazy loading issues in the loop
        agent_id = agent.agent_id

        # Fetch vulnerabilities from Indexer
        vulnerability_docs = await fetch_vulnerabilities_from_indexer(
            agent_name=agent_name
        )

        logger.info(f"Fetched {len(vulnerability_docs)} vulnerabilities for agent {agent_name}")

        if not vulnerability_docs:
            return VulnerabilitySyncResponse(
                success=True,
                message=f"No vulnerabilities found for agent {agent_name}",
                synced_count=0,
                errors=[]
            )

        synced_count = 0
        errors = []

        # Process and add each vulnerability immediately
        for i, doc in enumerate(vulnerability_docs, 1):
            try:
                logger.info(f"Processing vulnerability {i}/{len(vulnerability_docs)} for agent {agent_name}")

                # Process the vulnerability document
                vuln_data = process_wazuh_document(doc)

                # Check if vulnerability already exists using the session
                existing_vuln_result = await db_session.execute(
                    select(AgentVulnerabilities).filter(
                        and_(
                            AgentVulnerabilities.agent_id == agent_id,
                            AgentVulnerabilities.cve_id == vuln_data.cve_id,
                            AgentVulnerabilities.package_name == vuln_data.package_name
                        )
                    )
                )

                existing_vuln_record = existing_vuln_result.scalars().first()
                if existing_vuln_record:
                    # Update existing vulnerability directly without triggering relationships
                    existing_vuln_record.severity = vuln_data.severity
                    existing_vuln_record.title = vuln_data.title
                    existing_vuln_record.references = vuln_data.references
                    existing_vuln_record.discovered_at = vuln_data.detected_at
                    if hasattr(vuln_data, 'base_score') and vuln_data.base_score:
                        existing_vuln_record.epss_score = str(vuln_data.base_score)
                    if hasattr(vuln_data, 'package_name'):
                        existing_vuln_record.package_name = vuln_data.package_name

                    # Mark the object as dirty so SQLAlchemy knows to update it
                    db_session.add(existing_vuln_record)
                    logger.info(f"Updated existing vulnerability {vuln_data.cve_id} for agent {agent_name}")
                else:
                    # Create new vulnerability record
                    new_vuln = AgentVulnerabilities.create_from_model(
                        vulnerability_data=vuln_data,
                        agent_id=agent_id,
                        customer_code=customer_code
                    )
                    db_session.add(new_vuln)
                    logger.info(f"Added new vulnerability {vuln_data.cve_id} for agent {agent_name}")

                # Commit each vulnerability immediately to the database
                await db_session.commit()
                logger.info(f"Committed vulnerability {vuln_data.cve_id} to database")

                synced_count += 1

            except Exception as vuln_error:
                await db_session.rollback()
                error_msg = f"Error processing vulnerability {doc.get('_id', 'unknown')}: {vuln_error}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue

        return VulnerabilitySyncResponse(
            success=True,
            message=f"Successfully synced {synced_count} vulnerabilities for agent {agent_name}",
            synced_count=synced_count,
            errors=errors
        )

    except Exception as e:
        await db_session.rollback()
        logger.error(f"Error syncing vulnerabilities for agent {agent_name}: {e}")
        return VulnerabilitySyncResponse(
            success=False,
            message=f"Failed to sync vulnerabilities for agent {agent_name}: {e}",
            synced_count=0,
            errors=[str(e)]
        )


async def sync_all_vulnerabilities(
    db_session: AsyncSession,
    customer_code: Optional[str] = None
) -> VulnerabilitySyncResponse:
    """
    Sync vulnerabilities for all agents or agents of a specific customer

    Args:
        db_session: Database session to use
        customer_code: Optional customer code to filter agents by.
                      If None, syncs vulnerabilities for all agents in database.

    Returns:
        VulnerabilitySyncResponse with sync results
    """
    try:
        logger.info(f"Starting bulk vulnerability sync for customer: {customer_code or 'all agents'}")

        # Build query to get agents using the session
        if customer_code:
            query = select(Agents).filter(Agents.customer_code == customer_code)
        else:
            query = select(Agents)

        # Execute query using the session
        result = await db_session.execute(query)
        agents = result.scalars().all()

        if not agents:
            message = "No agents found" + (f" for customer {customer_code}" if customer_code else " in database")
            return VulnerabilitySyncResponse(
                success=True,
                message=message,
                synced_count=0,
                errors=[]
            )

        total_synced = 0
        all_errors = []

        # Process each agent synchronously to maintain session consistency
        for agent in agents:
            # Cache agent values to prevent lazy loading issues
            agent_hostname = agent.hostname
            agent_customer_code = agent.customer_code

            if not agent_hostname:
                continue

            try:
                logger.info(f"Starting sync for agent: {agent_hostname}")
                result = await sync_vulnerabilities_for_agent(
                    db_session=db_session,
                    agent_name=agent_hostname,
                    customer_code=agent_customer_code
                )

                total_synced += result.synced_count
                all_errors.extend(result.errors)

            except Exception as agent_error:
                error_msg = f"Error syncing agent {agent_hostname}: {agent_error}"
                logger.error(error_msg)
                all_errors.append(error_msg)

        success_message = f"Completed vulnerability sync for {len(agents)} agents"
        if customer_code:
            success_message += f" (customer: {customer_code})"
        else:
            success_message += " (all agents in database)"

        return VulnerabilitySyncResponse(
            success=True,
            message=success_message,
            synced_count=total_synced,
            errors=all_errors
        )

    except Exception as e:
        logger.error(f"Error in bulk vulnerability sync: {e}")
        return VulnerabilitySyncResponse(
            success=False,
            message=f"Failed to sync vulnerabilities: {e}",
            synced_count=0,
            errors=[str(e)]
        )


async def get_vulnerabilities_by_agent(
    db_session: AsyncSession,
    agent_id: str,
    severity_filter: Optional[List[str]] = None
) -> AgentVulnerabilitiesResponse:
    """
    Get vulnerabilities for a specific agent from database

    Args:
        db_session: Database session to use
        agent_id: Agent ID to get vulnerabilities for
        severity_filter: Optional list of severities to filter by

    Returns:
        AgentVulnerabilitiesResponse with vulnerabilities
    """
    try:
        query = select(AgentVulnerabilities).filter(
            AgentVulnerabilities.agent_id == agent_id
        )

        if severity_filter:
            query = query.filter(AgentVulnerabilities.severity.in_(severity_filter))

        result = await db_session.execute(query)
        vulnerabilities = result.scalars().all()

        vuln_list = [
            AgentVulnerabilityOut(
                id=vuln.id,
                cve_id=vuln.cve_id,
                severity=vuln.severity,
                title=vuln.title,
                references=vuln.references,
                status=vuln.status,
                discovered_at=vuln.discovered_at,
                remediated_at=vuln.remediated_at,
                epss_score=vuln.epss_score,
                epss_percentile=vuln.epss_percentile,
                package_name=vuln.package_name,
                agent_id=vuln.agent_id,
                customer_code=vuln.customer_code
            )
            for vuln in vulnerabilities
        ]

        return AgentVulnerabilitiesResponse(
            vulnerabilities=vuln_list,
            success=True,
            message=f"Retrieved {len(vuln_list)} vulnerabilities for agent {agent_id}",
            total_count=len(vuln_list)
        )

    except Exception as e:
        logger.error(f"Error getting vulnerabilities for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get vulnerabilities for agent {agent_id}: {e}"
        )


async def get_vulnerability_statistics(
    db_session: AsyncSession,
    customer_code: Optional[str] = None
) -> VulnerabilityStatsResponse:
    """
    Get vulnerability statistics

    Args:
        db_session: Database session to use
        customer_code: Optional customer code to filter by

    Returns:
        VulnerabilityStatsResponse with statistics
    """
    try:
        query = select(AgentVulnerabilities)
        if customer_code:
            query = query.filter(AgentVulnerabilities.customer_code == customer_code)

        result = await db_session.execute(query)
        vulnerabilities = result.scalars().all()

        # Calculate statistics
        total = len(vulnerabilities)
        critical = sum(1 for v in vulnerabilities if v.severity.lower() == "critical")
        high = sum(1 for v in vulnerabilities if v.severity.lower() == "high")
        medium = sum(1 for v in vulnerabilities if v.severity.lower() == "medium")
        low = sum(1 for v in vulnerabilities if v.severity.lower() == "low")

        # Group by customer if no specific customer requested
        by_customer = {}
        if not customer_code:
            for vuln in vulnerabilities:
                if vuln.customer_code:
                    by_customer[vuln.customer_code] = by_customer.get(vuln.customer_code, 0) + 1

        return VulnerabilityStatsResponse(
            total_vulnerabilities=total,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            by_customer=by_customer,
            success=True,
            message="Vulnerability statistics retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Error getting vulnerability statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get vulnerability statistics: {e}"
        )


async def delete_vulnerabilities(
    db_session: AsyncSession,
    agent_name: Optional[str] = None,
    customer_code: Optional[str] = None
):
    """
    Delete vulnerabilities based on scope:
    - If neither agent_name nor customer_code provided: Delete ALL vulnerabilities
    - If agent_name provided: Delete vulnerabilities for that specific agent
    - If customer_code provided: Delete vulnerabilities for all agents of that customer

    Args:
        db_session: Database session to use
        agent_name: Optional agent name to delete vulnerabilities for
        customer_code: Optional customer code to delete vulnerabilities for

    Returns:
        VulnerabilityDeleteResponse with deletion results
    """
    from app.agents.vulnerabilities.schema.vulnerabilities import VulnerabilityDeleteResponse

    try:
        deleted_count = 0

        if agent_name:
            # Delete vulnerabilities for specific agent
            logger.info(f"Deleting vulnerabilities for agent: {agent_name}")

            # First get the agent to validate it exists and get agent_id
            agent_result = await db_session.execute(
                select(Agents).filter(Agents.hostname == agent_name)
            )
            agent = agent_result.scalars().first()

            if not agent:
                return VulnerabilityDeleteResponse(
                    success=False,
                    message=f"Agent {agent_name} not found in database",
                    deleted_count=0,
                    errors=[f"Agent {agent_name} not found"]
                )

            # Delete vulnerabilities for this agent
            from sqlalchemy import delete
            delete_stmt = delete(AgentVulnerabilities).where(
                AgentVulnerabilities.agent_id == agent.agent_id
            )
            result = await db_session.execute(delete_stmt)
            deleted_count = result.rowcount
            await db_session.commit()

            return VulnerabilityDeleteResponse(
                success=True,
                message=f"Successfully deleted {deleted_count} vulnerabilities for agent {agent_name}",
                deleted_count=deleted_count,
                errors=[]
            )

        elif customer_code:
            # Delete vulnerabilities for all agents of specific customer
            logger.info(f"Deleting vulnerabilities for customer: {customer_code}")

            from sqlalchemy import delete
            delete_stmt = delete(AgentVulnerabilities).where(
                AgentVulnerabilities.customer_code == customer_code
            )
            result = await db_session.execute(delete_stmt)
            deleted_count = result.rowcount
            await db_session.commit()

            return VulnerabilityDeleteResponse(
                success=True,
                message=f"Successfully deleted {deleted_count} vulnerabilities for customer {customer_code}",
                deleted_count=deleted_count,
                errors=[]
            )

        else:
            # Delete ALL vulnerabilities
            logger.warning("Deleting ALL vulnerabilities from database")

            from sqlalchemy import delete
            delete_stmt = delete(AgentVulnerabilities)
            result = await db_session.execute(delete_stmt)
            deleted_count = result.rowcount
            await db_session.commit()

            return VulnerabilityDeleteResponse(
                success=True,
                message=f"Successfully deleted ALL {deleted_count} vulnerabilities from database",
                deleted_count=deleted_count,
                errors=[]
            )

    except Exception as e:
        await db_session.rollback()
        logger.error(f"Error deleting vulnerabilities: {e}")
        return VulnerabilityDeleteResponse(
            success=False,
            message=f"Failed to delete vulnerabilities: {e}",
            deleted_count=0,
            errors=[str(e)]
        )

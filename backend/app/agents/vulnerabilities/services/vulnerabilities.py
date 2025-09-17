from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.vulnerabilities.schema.vulnerabilities import (
    AgentVulnerabilitiesResponse,
)
from app.agents.vulnerabilities.schema.vulnerabilities import AgentVulnerabilityOut
from app.agents.vulnerabilities.schema.vulnerabilities import VulnerabilitySearchItem
from app.agents.vulnerabilities.schema.vulnerabilities import (
    VulnerabilitySearchResponse,
)
from app.agents.vulnerabilities.schema.vulnerabilities import VulnerabilityStatsResponse
from app.agents.vulnerabilities.schema.vulnerabilities import VulnerabilitySyncResponse
from app.agents.vulnerabilities.schema.vulnerabilities import WazuhVulnerabilityData
from app.connectors.wazuh_indexer.utils.universal import collect_indices
from app.connectors.wazuh_indexer.utils.universal import (
    create_wazuh_indexer_client_async,
)
from app.db.universal_models import Agents
from app.db.universal_models import AgentVulnerabilities
from app.threat_intel.schema.epss import EpssThreatIntelRequest
from app.threat_intel.services.epss import collect_epss_score


async def get_epss_score_for_cve(cve_id: str) -> tuple[Optional[str], Optional[str]]:
    """
    Get EPSS score and percentile for a CVE ID

    Args:
        cve_id: CVE identifier to get EPSS score for

    Returns:
        Tuple of (epss_score, epss_percentile) or (None, None) if not found
    """
    try:
        epss_request = EpssThreatIntelRequest(cve=cve_id)
        epss_response = await collect_epss_score(epss_request)

        if epss_response.success and epss_response.data:
            # Get the first (and usually only) result
            epss_data = epss_response.data[0]
            return epss_data.epss, epss_data.percentile
        else:
            logger.debug(f"No EPSS data found for CVE: {cve_id}")
            return None, None

    except Exception as e:
        logger.warning(f"Error fetching EPSS score for CVE {cve_id}: {e}")
        return None, None


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
        detected_at = datetime.fromisoformat(detected_at_str.replace("Z", "+00:00")) if detected_at_str else datetime.utcnow()

        # Parse published_at timestamp if available
        published_at_str = vuln_data.get("published_at")
        published_at = None
        if published_at_str:
            try:
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Could not parse published_at: {published_at_str}")

        # Parse and limit references to first 5 items if comma-separated
        references_raw = vuln_data.get("reference")
        references = None
        if references_raw:
            if isinstance(references_raw, str) and "," in references_raw:
                # Split by comma, take first 5 items, and rejoin
                reference_list = [ref.strip() for ref in references_raw.split(",")]
                references = ", ".join(reference_list[:5])
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
            package_architecture=package_data.get("architecture"),
        )
    except Exception as e:
        logger.error(f"Error processing vulnerability document: {e}")
        logger.error(f"Document: {document}")
        raise


async def get_vulnerabilities_indices() -> List[str]:
    """Get all vulnerability indices from Wazuh Indexer"""
    try:
        indices = await collect_indices(all_indices=True)
        vuln_indices = [index for index in indices.indices_list if index.startswith("wazuh-states-vulnerabilities")]
        logger.info(f"Found {len(vuln_indices)} vulnerability indices")
        return vuln_indices
    except Exception as e:
        logger.error(f"Error collecting vulnerability indices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect vulnerability indices: {e}")


async def fetch_vulnerabilities_from_indexer(
    agent_name: Optional[str] = None,
    customer_code: Optional[str] = None,
    severity_filter: Optional[List[str]] = None,
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
            query["query"]["bool"]["must"].append({"terms": {"vulnerability.severity": severity_filter}})

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
        raise HTTPException(status_code=500, detail=f"Failed to fetch vulnerabilities: {e}")
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
        result = await db_session.execute(select(Agents).filter(Agents.hostname == agent_name))
        return result.scalars().first()
    except Exception as e:
        logger.error(f"Error fetching agent {agent_name}: {e}")
        return None


async def _sync_vulnerabilities_bulk_mode(
    db_session: AsyncSession,
    agent_id: str,
    agent_name: str,
    customer_code: str,
    vulnerability_docs: List[Dict[str, Any]],
) -> "VulnerabilitySyncResponse":
    """
    Ultra-fast bulk mode for processing large numbers of vulnerabilities.
    Uses SQLAlchemy bulk operations for maximum performance.
    """
    from app.agents.vulnerabilities.schema.vulnerabilities import (
        VulnerabilitySyncResponse,
    )

    try:
        logger.info(f"BULK MODE: Processing {len(vulnerability_docs)} vulnerabilities for agent {agent_name}")

        # Process all documents first
        processed_vulns = []
        errors = []

        for doc in vulnerability_docs:
            try:
                vuln_data = process_wazuh_document(doc)
                processed_vulns.append(vuln_data)
            except Exception as doc_error:
                error_msg = f"Error processing vulnerability {doc.get('_id', 'unknown')}: {doc_error}"
                logger.error(error_msg)
                errors.append(error_msg)

        if not processed_vulns:
            return VulnerabilitySyncResponse(
                success=True,
                message=f"No valid vulnerabilities to process for agent {agent_name}",
                synced_count=0,
                errors=errors,
            )

        # Get existing vulnerabilities for comparison
        existing_vulns_result = await db_session.execute(select(AgentVulnerabilities).filter(AgentVulnerabilities.agent_id == agent_id))
        existing_vulns = existing_vulns_result.scalars().all()

        # Create lookup for existing vulnerabilities
        existing_lookup = {}
        for vuln in existing_vulns:
            key = f"{vuln.cve_id}_{vuln.package_name or 'None'}"
            existing_lookup[key] = vuln

        # Prepare bulk operations
        new_vulnerabilities = []
        update_data = []

        for vuln_data in processed_vulns:
            key = f"{vuln_data.cve_id}_{vuln_data.package_name or 'None'}"

            if key in existing_lookup:
                # Prepare for bulk update
                existing_vuln = existing_lookup[key]
                update_data.append(
                    {
                        "id": existing_vuln.id,
                        "severity": vuln_data.severity,
                        "title": vuln_data.title,
                        "references": vuln_data.references,
                        "discovered_at": vuln_data.detected_at,
                        "epss_score": str(vuln_data.base_score)
                        if hasattr(vuln_data, "base_score") and vuln_data.base_score
                        else existing_vuln.epss_score,
                        "package_name": vuln_data.package_name,
                    },
                )
            else:
                # Prepare for bulk insert
                new_vuln = AgentVulnerabilities.create_from_model(
                    vulnerability_data=vuln_data,
                    agent_id=agent_id,
                    customer_code=customer_code,
                )
                new_vulnerabilities.append(new_vuln)

        # Execute bulk operations
        inserted_count = 0
        updated_count = 0

        if new_vulnerabilities:
            db_session.add_all(new_vulnerabilities)
            inserted_count = len(new_vulnerabilities)
            logger.info(f"BULK MODE: Prepared {inserted_count} new vulnerabilities for insertion")

        if update_data:
            # Use bulk update for existing vulnerabilities
            from sqlalchemy import update

            for data in update_data:
                stmt = (
                    update(AgentVulnerabilities)
                    .where(AgentVulnerabilities.id == data["id"])
                    .values(
                        {
                            "severity": data["severity"],
                            "title": data["title"],
                            "references": data["references"],
                            "discovered_at": data["discovered_at"],
                            "epss_score": data["epss_score"],
                            "package_name": data["package_name"],
                        },
                    )
                )
                await db_session.execute(stmt)
            updated_count = len(update_data)
            logger.info(f"BULK MODE: Executed {updated_count} vulnerability updates")

        # Single commit for all operations
        await db_session.commit()

        total_synced = inserted_count + updated_count
        logger.info(f"BULK MODE: Successfully synced {total_synced} vulnerabilities ({inserted_count} new, {updated_count} updated)")

        return VulnerabilitySyncResponse(
            success=True,
            message=f"BULK MODE: Successfully synced {total_synced} vulnerabilities for agent {agent_name} ({inserted_count} new, {updated_count} updated)",
            synced_count=total_synced,
            errors=errors,
        )

    except Exception as e:
        await db_session.rollback()
        logger.error(f"BULK MODE: Error syncing vulnerabilities for agent {agent_name}: {e}")
        return VulnerabilitySyncResponse(
            success=False,
            message=f"BULK MODE: Failed to sync vulnerabilities for agent {agent_name}: {e}",
            synced_count=0,
            errors=[str(e)],
        )


async def sync_vulnerabilities_for_agent(
    db_session: AsyncSession,
    agent_name: str,
    customer_code: Optional[str] = None,
    batch_size: int = 100,
    use_bulk_mode: bool = False,
) -> VulnerabilitySyncResponse:
    """
    Sync vulnerabilities for a specific agent

    Args:
        db_session: Database session to use
        agent_name: Name of the agent to sync vulnerabilities for
        customer_code: Optional customer code override
        batch_size: Number of vulnerabilities to process in each batch (default: 100)
        use_bulk_mode: If True, use ultra-fast bulk operations (default: False)

    Returns:
        VulnerabilitySyncResponse with sync results
    """
    try:
        # Get agent from database using the session
        result = await db_session.execute(select(Agents).filter(Agents.hostname == agent_name))
        agent = result.scalars().first()

        if not agent:
            return VulnerabilitySyncResponse(
                success=False,
                message=f"Agent {agent_name} not found in database",
                synced_count=0,
                errors=[f"Agent {agent_name} not found"],
            )

        # Use agent's customer code if not provided
        if not customer_code:
            customer_code = agent.customer_code

        # Cache agent values to prevent lazy loading issues in the loop
        agent_id = agent.agent_id

        # Fetch vulnerabilities from Indexer
        vulnerability_docs = await fetch_vulnerabilities_from_indexer(agent_name=agent_name)

        logger.info(f"Fetched {len(vulnerability_docs)} vulnerabilities for agent {agent_name}")

        if not vulnerability_docs:
            return VulnerabilitySyncResponse(
                success=True,
                message=f"No vulnerabilities found for agent {agent_name}",
                synced_count=0,
                errors=[],
            )

        synced_count = 0
        errors = []

        # Choose processing mode based on use_bulk_mode flag
        if use_bulk_mode:
            logger.info(f"Using BULK MODE for {len(vulnerability_docs)} vulnerabilities for agent {agent_name}")
            return await _sync_vulnerabilities_bulk_mode(db_session, agent_id, agent_name, customer_code, vulnerability_docs)

        # OPTIMIZATION: Process vulnerabilities in batches for better performance
        logger.info(f"Using BATCH MODE (batch_size={batch_size}) for {len(vulnerability_docs)} vulnerabilities for agent {agent_name}")

        # First, get all existing vulnerabilities for this agent to do bulk comparison
        logger.info(f"Fetching existing vulnerabilities for agent {agent_name} for comparison")
        existing_vulns_result = await db_session.execute(select(AgentVulnerabilities).filter(AgentVulnerabilities.agent_id == agent_id))
        existing_vulns = existing_vulns_result.scalars().all()

        # Create a lookup dictionary for fast comparison (agent_id + cve_id + package_name)
        existing_vulns_lookup = {}
        for vuln in existing_vulns:
            key = f"{vuln.agent_id}_{vuln.cve_id}_{vuln.package_name or 'None'}"
            existing_vulns_lookup[key] = vuln

        logger.info(f"Found {len(existing_vulns_lookup)} existing vulnerabilities for agent {agent_name}")

        # Process vulnerabilities in batches
        for batch_start in range(0, len(vulnerability_docs), batch_size):
            batch_end = min(batch_start + batch_size, len(vulnerability_docs))
            batch_docs = vulnerability_docs[batch_start:batch_end]

            logger.info(
                f"Processing batch {batch_start // batch_size + 1}: vulnerabilities {batch_start + 1}-{batch_end} of {len(vulnerability_docs)} for agent {agent_name}",
            )

            try:
                batch_updates = []
                batch_inserts = []
                batch_errors = []

                # Process each document in the batch
                for i, doc in enumerate(batch_docs):
                    try:
                        # Process the vulnerability document
                        vuln_data = process_wazuh_document(doc)

                        # Create lookup key
                        lookup_key = f"{agent_id}_{vuln_data.cve_id}_{vuln_data.package_name or 'None'}"

                        if lookup_key in existing_vulns_lookup:
                            # Update existing vulnerability
                            existing_vuln = existing_vulns_lookup[lookup_key]
                            existing_vuln.severity = vuln_data.severity
                            existing_vuln.title = vuln_data.title
                            existing_vuln.references = vuln_data.references
                            existing_vuln.discovered_at = vuln_data.detected_at
                            if hasattr(vuln_data, "base_score") and vuln_data.base_score:
                                existing_vuln.epss_score = str(vuln_data.base_score)
                            if hasattr(vuln_data, "package_name"):
                                existing_vuln.package_name = vuln_data.package_name

                            db_session.add(existing_vuln)
                            batch_updates.append(vuln_data.cve_id)
                        else:
                            # Create new vulnerability record
                            new_vuln = AgentVulnerabilities.create_from_model(
                                vulnerability_data=vuln_data,
                                agent_id=agent_id,
                                customer_code=customer_code,
                            )
                            db_session.add(new_vuln)
                            batch_inserts.append(vuln_data.cve_id)

                            # Add to lookup to avoid duplicates within the same batch
                            existing_vulns_lookup[lookup_key] = new_vuln

                    except Exception as doc_error:
                        error_msg = f"Error processing vulnerability {doc.get('_id', 'unknown')}: {doc_error}"
                        logger.error(error_msg)
                        batch_errors.append(error_msg)
                        continue

                # Commit the entire batch at once
                await db_session.commit()

                batch_synced = len(batch_updates) + len(batch_inserts)
                synced_count += batch_synced
                errors.extend(batch_errors)

                logger.info(
                    f"Batch {batch_start // batch_size + 1} completed: {len(batch_updates)} updates, {len(batch_inserts)} inserts, {len(batch_errors)} errors",
                )

            except Exception as batch_error:
                await db_session.rollback()
                error_msg = f"Error processing batch {batch_start}-{batch_end}: {batch_error}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue

        return VulnerabilitySyncResponse(
            success=True,
            message=f"Successfully synced {synced_count} vulnerabilities for agent {agent_name} ({len(errors)}",
            synced_count=synced_count,
            errors=errors,
        )

    except Exception as e:
        await db_session.rollback()
        logger.error(f"Error syncing vulnerabilities for agent {agent_name}: {e}")
        return VulnerabilitySyncResponse(
            success=False,
            message=f"Failed to sync vulnerabilities for agent {agent_name}: {e}",
            synced_count=0,
            errors=[str(e)],
        )


async def sync_all_vulnerabilities(
    db_session: AsyncSession,
    customer_code: Optional[str] = None,
    batch_size: int = 100,
    use_bulk_mode: bool = False,
) -> VulnerabilitySyncResponse:
    """
    Sync vulnerabilities for all agents or agents of a specific customer with performance options

    Args:
        db_session: Database session to use
        customer_code: Optional customer code to filter agents by.
                      If None, syncs vulnerabilities for all agents in database.
        batch_size: Number of vulnerabilities to process in each batch (default: 100)
        use_bulk_mode: Use ultra-fast bulk operations for large datasets (default: False)

    Returns:
        VulnerabilitySyncResponse with sync results
    """
    try:
        mode_info = "bulk mode" if use_bulk_mode else f"batch mode (size: {batch_size})"
        logger.info(f"Starting bulk vulnerability sync for customer: {customer_code or 'all agents'} using {mode_info}")

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
            return VulnerabilitySyncResponse(success=True, message=message, synced_count=0, errors=[])

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
                logger.info(f"Starting sync for agent: {agent_hostname} using {mode_info}")
                result = await sync_vulnerabilities_for_agent(
                    db_session=db_session,
                    agent_name=agent_hostname,
                    customer_code=agent_customer_code,
                    batch_size=batch_size,
                    use_bulk_mode=use_bulk_mode,
                )

                total_synced += result.synced_count
                all_errors.extend(result.errors)

            except Exception as agent_error:
                error_msg = f"Error syncing agent {agent_hostname}: {agent_error}"
                logger.error(error_msg)
                all_errors.append(error_msg)

        success_message = f"Completed vulnerability sync for {len(agents)} agents using {mode_info}"
        if customer_code:
            success_message += f" (customer: {customer_code})"
        else:
            success_message += " (all agents in database)"

        return VulnerabilitySyncResponse(success=True, message=success_message, synced_count=total_synced, errors=all_errors)

    except Exception as e:
        logger.error(f"Error in bulk vulnerability sync: {e}")
        return VulnerabilitySyncResponse(success=False, message=f"Failed to sync vulnerabilities: {e}", synced_count=0, errors=[str(e)])


async def get_vulnerabilities_by_agent(
    db_session: AsyncSession,
    agent_id: str,
    severity_filter: Optional[List[str]] = None,
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
        query = select(AgentVulnerabilities).filter(AgentVulnerabilities.agent_id == agent_id)

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
                customer_code=vuln.customer_code,
            )
            for vuln in vulnerabilities
        ]

        return AgentVulnerabilitiesResponse(
            vulnerabilities=vuln_list,
            success=True,
            message=f"Retrieved {len(vuln_list)} vulnerabilities for agent {agent_id}",
            total_count=len(vuln_list),
        )

    except Exception as e:
        logger.error(f"Error getting vulnerabilities for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get vulnerabilities for agent {agent_id}: {e}")


async def get_vulnerability_statistics(db_session: AsyncSession, customer_code: Optional[str] = None) -> VulnerabilityStatsResponse:
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
            message="Vulnerability statistics retrieved successfully",
        )

    except Exception as e:
        logger.error(f"Error getting vulnerability statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get vulnerability statistics: {e}")


async def delete_vulnerabilities(db_session: AsyncSession, agent_name: Optional[str] = None, customer_code: Optional[str] = None):
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
    from app.agents.vulnerabilities.schema.vulnerabilities import (
        VulnerabilityDeleteResponse,
    )

    try:
        deleted_count = 0

        if agent_name:
            # Delete vulnerabilities for specific agent
            logger.info(f"Deleting vulnerabilities for agent: {agent_name}")

            # First get the agent to validate it exists and get agent_id
            agent_result = await db_session.execute(select(Agents).filter(Agents.hostname == agent_name))
            agent = agent_result.scalars().first()

            if not agent:
                return VulnerabilityDeleteResponse(
                    success=False,
                    message=f"Agent {agent_name} not found in database",
                    deleted_count=0,
                    errors=[f"Agent {agent_name} not found"],
                )

            # Delete vulnerabilities for this agent
            from sqlalchemy import delete

            delete_stmt = delete(AgentVulnerabilities).where(AgentVulnerabilities.agent_id == agent.agent_id)
            result = await db_session.execute(delete_stmt)
            deleted_count = result.rowcount
            await db_session.commit()

            return VulnerabilityDeleteResponse(
                success=True,
                message=f"Successfully deleted {deleted_count} vulnerabilities for agent {agent_name}",
                deleted_count=deleted_count,
                errors=[],
            )

        elif customer_code:
            # Delete vulnerabilities for all agents of specific customer
            logger.info(f"Deleting vulnerabilities for customer: {customer_code}")

            from sqlalchemy import delete

            delete_stmt = delete(AgentVulnerabilities).where(AgentVulnerabilities.customer_code == customer_code)
            result = await db_session.execute(delete_stmt)
            deleted_count = result.rowcount
            await db_session.commit()

            return VulnerabilityDeleteResponse(
                success=True,
                message=f"Successfully deleted {deleted_count} vulnerabilities for customer {customer_code}",
                deleted_count=deleted_count,
                errors=[],
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
                errors=[],
            )

    except Exception as e:
        await db_session.rollback()
        logger.error(f"Error deleting vulnerabilities: {e}")
        return VulnerabilityDeleteResponse(
            success=False,
            message=f"Failed to delete vulnerabilities: {e}",
            deleted_count=0,
            errors=[str(e)],
        )


async def search_vulnerabilities_from_indexer(
    db_session: AsyncSession,
    customer_code: Optional[str] = None,
    agent_name: Optional[str] = None,
    severity: Optional[str] = None,
    cve_id: Optional[str] = None,
    package_name: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    include_epss: bool = True,
) -> VulnerabilitySearchResponse:
    """
    Search vulnerabilities directly from Wazuh indexer with filtering and pagination

    Args:
        db_session: Database session for agent lookup
        customer_code: Optional customer code filter
        agent_name: Optional agent hostname filter
        severity: Optional severity filter
        cve_id: Optional CVE ID filter
        package_name: Optional package name filter
        page: Page number for pagination
        page_size: Number of results per page
        include_epss: Whether to include EPSS scores (default: True, may impact performance)

    Returns:
        VulnerabilitySearchResponse with paginated results
    """
    logger.info(
        f"Searching vulnerabilities with filters: customer_code={customer_code}, "
        f"agent_name={agent_name}, severity={severity}, cve_id={cve_id}, "
        f"package_name={package_name}, page={page}, page_size={page_size}, "
        f"include_epss={include_epss}",
    )

    # Build filters applied dict for response
    filters_applied = {}
    if customer_code:
        filters_applied["customer_code"] = customer_code
    if agent_name:
        filters_applied["agent_name"] = agent_name
    if severity:
        filters_applied["severity"] = severity
    if cve_id:
        filters_applied["cve_id"] = cve_id
    if package_name:
        filters_applied["package_name"] = package_name

    # Create Elasticsearch client
    es_client = None
    try:
        # Initialize Elasticsearch client
        es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")

        # Always get all agents to build hostname to customer_code mapping
        # This ensures we can always provide customer_code in the response
        all_agents_query = select(Agents)
        all_agents_result = await db_session.execute(all_agents_query)
        all_agents = all_agents_result.scalars().all()

        # Build complete agent hostname to customer code mapping
        customer_agent_map = {}
        for agent in all_agents:
            if agent.hostname:
                customer_agent_map[agent.hostname] = agent.customer_code

        # Get agent information for filtering (if filters are applied)
        agent_hostnames = []

        if customer_code or agent_name:
            query = select(Agents)
            if customer_code:
                query = query.filter(Agents.customer_code == customer_code)
            if agent_name:
                query = query.filter(Agents.hostname == agent_name)

            result = await db_session.execute(query)
            agents = result.scalars().all()

            if not agents and (customer_code or agent_name):
                return VulnerabilitySearchResponse(
                    vulnerabilities=[],
                    total_count=0,
                    critical_count=0,
                    high_count=0,
                    medium_count=0,
                    low_count=0,
                    page=page,
                    page_size=page_size,
                    total_pages=0,
                    has_next=False,
                    has_previous=False,
                    success=True,
                    message="No agents found matching the specified criteria",
                    filters_applied=filters_applied,
                )

            # Build list of agent hostnames for Elasticsearch filtering
            for agent in agents:
                if agent.hostname:
                    agent_hostnames.append(agent.hostname)

        # Get vulnerability indices
        vuln_indices = await get_vulnerabilities_indices()
        if not vuln_indices:
            return VulnerabilitySearchResponse(
                vulnerabilities=[],
                total_count=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                page=page,
                page_size=page_size,
                total_pages=0,
                has_next=False,
                has_previous=False,
                success=True,
                message="No vulnerability indices found",
                filters_applied=filters_applied,
            )

        # Build Elasticsearch query
        es_query = {"bool": {"must": []}}

        # Add agent filter if specified
        if agent_hostnames:
            es_query["bool"]["must"].append({"terms": {"agent.name": agent_hostnames}})

        # Add severity filter
        if severity:
            es_query["bool"]["must"].append({"term": {"vulnerability.severity": severity}})

        # Add CVE ID filter
        if cve_id:
            es_query["bool"]["must"].append({"term": {"vulnerability.id": cve_id}})

        # Add package name filter
        if package_name:
            es_query["bool"]["must"].append({"wildcard": {"package.name": f"*{package_name}*"}})

        # Calculate pagination
        start_index = (page - 1) * page_size

        # Create Elasticsearch client
        es_client = None
        try:
            es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")

            # First, get total count and severity aggregations
            count_response = await es_client.count(index=",".join(vuln_indices), body={"query": es_query})
            total_count = count_response["count"]

            # Get severity aggregations
            agg_response = await es_client.search(
                index=",".join(vuln_indices),
                body={
                    "query": es_query,
                    "size": 0,  # We don't need documents, just aggregations
                    "aggs": {"severity_counts": {"terms": {"field": "vulnerability.severity", "size": 10}}},
                },
            )

            # Extract severity counts from aggregation response
            severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
            if "aggregations" in agg_response and "severity_counts" in agg_response["aggregations"]:
                for bucket in agg_response["aggregations"]["severity_counts"]["buckets"]:
                    severity = bucket["key"]
                    count = bucket["doc_count"]
                    if severity in severity_counts:
                        severity_counts[severity] = count

            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_previous = page > 1

            if total_count == 0:
                return VulnerabilitySearchResponse(
                    vulnerabilities=[],
                    total_count=0,
                    critical_count=0,
                    high_count=0,
                    medium_count=0,
                    low_count=0,
                    page=page,
                    page_size=page_size,
                    total_pages=0,
                    has_next=False,
                    has_previous=False,
                    success=True,
                    message="No vulnerabilities found matching the specified criteria",
                    filters_applied=filters_applied,
                )

            # Get the actual results with pagination
            search_response = await es_client.search(
                index=",".join(vuln_indices),
                body={
                    "query": es_query,
                    "sort": [{"vulnerability.detected_at": {"order": "desc"}}, {"vulnerability.severity": {"order": "asc"}}],
                    "from": start_index,
                    "size": page_size,
                },
            )

            vulnerabilities = []
            for hit in search_response["hits"]["hits"]:
                try:
                    source = hit["_source"]
                    agent_data = source.get("agent", {})
                    agent_hostname = agent_data.get("name", "unknown")

                    # Get customer code from our mapping
                    agent_customer_code = customer_agent_map.get(agent_hostname)

                    # Process the vulnerability data
                    vuln_data = process_wazuh_document(hit)

                    # Get EPSS score for the CVE (if requested)
                    epss_score, epss_percentile = None, None
                    if include_epss:
                        epss_score, epss_percentile = await get_epss_score_for_cve(vuln_data.cve_id)

                    vulnerability_item = VulnerabilitySearchItem(
                        cve_id=vuln_data.cve_id,
                        severity=vuln_data.severity,
                        title=vuln_data.title,
                        agent_name=agent_hostname,
                        customer_code=agent_customer_code,
                        references=vuln_data.references,
                        detected_at=vuln_data.detected_at,
                        published_at=vuln_data.published_at,
                        base_score=vuln_data.base_score,
                        package_name=vuln_data.package_name,
                        package_version=vuln_data.package_version,
                        package_architecture=vuln_data.package_architecture,
                        epss_score=epss_score,
                        epss_percentile=epss_percentile,
                    )
                    vulnerabilities.append(vulnerability_item)

                except Exception as e:
                    logger.error(f"Error processing vulnerability document: {e}")
                    continue

            # Sort vulnerabilities by EPSS score (highest to lowest) if EPSS is included
            if include_epss:
                # Sort by EPSS score descending, treating None/null as 0
                # Then by severity (Critical=0, High=1, Medium=2, Low=3) for tie-breaking
                severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

                def get_epss_sort_key(vuln):
                    # Convert EPSS score to float for sorting, handle string/None values
                    epss_score = vuln.epss_score
                    if epss_score is None:
                        epss_float = 0.0
                    else:
                        try:
                            epss_float = float(epss_score)
                        except (ValueError, TypeError):
                            epss_float = 0.0
                    return (
                        -epss_float,  # Negative for descending order
                        severity_order.get(vuln.severity, 4),  # Secondary sort by severity
                        vuln.cve_id  # Tertiary sort by CVE ID for consistency
                    )

                vulnerabilities.sort(key=get_epss_sort_key)
                logger.info(f"Sorted {len(vulnerabilities)} vulnerabilities by EPSS score (highest to lowest)")

            message = f"Found {len(vulnerabilities)} vulnerabilities on page {page} of {total_pages}"
            if filters_applied:
                message += f" with filters: {filters_applied}"
            if include_epss:
                message += " (sorted by EPSS score, highest to lowest)"
            else:
                message += " (sorted by detection date and severity)"

            return VulnerabilitySearchResponse(
                vulnerabilities=vulnerabilities,
                total_count=total_count,
                critical_count=severity_counts["Critical"],
                high_count=severity_counts["High"],
                medium_count=severity_counts["Medium"],
                low_count=severity_counts["Low"],
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=has_next,
                has_previous=has_previous,
                success=True,
                message=message,
                filters_applied=filters_applied,
            )

        except Exception as e:
            logger.error(f"Error searching vulnerabilities from indexer: {e}")
            return VulnerabilitySearchResponse(
                vulnerabilities=[],
                total_count=0,
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                page=page,
                page_size=page_size,
                total_pages=0,
                has_next=False,
                has_previous=False,
                success=False,
                message=f"Failed to search vulnerabilities: {e}",
                filters_applied=filters_applied if "filters_applied" in locals() else {},
            )
        finally:
            # Ensure the Elasticsearch client session is properly closed
            if es_client:
                try:
                    await es_client.close()
                except Exception as close_error:
                    logger.warning(f"Error closing Elasticsearch client: {close_error}")

    except Exception as e:
        logger.error(f"Unexpected error in search_vulnerabilities_from_indexer: {e}")
        return VulnerabilitySearchResponse(
            vulnerabilities=[],
            total_count=0,
            critical_count=0,
            high_count=0,
            medium_count=0,
            low_count=0,
            page=page,
            page_size=page_size,
            total_pages=0,
            has_next=False,
            has_previous=False,
            success=False,
            message=f"Unexpected error occurred: {e}",
            filters_applied=filters_applied if "filters_applied" in locals() else {},
        )

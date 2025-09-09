import asyncio
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


class VulnerabilityProcessor:
    """Processes raw Wazuh vulnerability data into database format"""

    @staticmethod
    def process_wazuh_document(document: Dict[str, Any]) -> WazuhVulnerabilityData:
        """
        Process a single Wazuh vulnerability document from Elasticsearch

        Args:
            document: Raw document from Wazuh Elasticsearch index

        Returns:
            WazuhVulnerabilityData: Processed vulnerability data
        """
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

            return WazuhVulnerabilityData(
                id=vuln_data.get("id", "UNKNOWN_CVE"),
                severity=vuln_data.get("severity", "UNKNOWN"),
                description=vuln_data.get("description", ""),
                reference=vuln_data.get("reference"),
                detected_at=detected_at,
                published_at=published_at,
                base=score_data.get("base"),
                package_name=package_data.get("name"),
                package_version=package_data.get("version"),
                package_architecture=package_data.get("architecture")
            )
        except Exception as e:
            logger.error(f"Error processing vulnerability document: {e}")
            logger.error(f"Document: {document}")
            raise


class VulnerabilityService:
    """Service class for vulnerability operations"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.processor = VulnerabilityProcessor()

    async def get_vulnerabilities_indices(self) -> List[str]:
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

    async def fetch_vulnerabilities_from_elasticsearch(
        self,
        agent_name: Optional[str] = None,
        customer_code: Optional[str] = None,
        severity_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch vulnerabilities from Wazuh Elasticsearch indices

        Args:
            agent_name: Optional agent name filter
            customer_code: Optional customer code filter (used for index filtering)
            severity_filter: Optional list of severities to filter by

        Returns:
            List of vulnerability documents
        """
        try:
            es_client = await create_wazuh_indexer_client_async("Wazuh-Indexer")
            indices = await self.get_vulnerabilities_indices()

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

                except Exception as index_error:
                    logger.error(f"Error querying index {index}: {index_error}")
                    continue

            logger.info(f"Fetched {len(vulnerabilities)} vulnerabilities from Elasticsearch")
            return vulnerabilities

        except Exception as e:
            logger.error(f"Error fetching vulnerabilities from Elasticsearch: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch vulnerabilities: {e}"
            )

    async def get_agent_by_name(self, agent_name: str) -> Optional[Agents]:
        """Get agent from database by hostname/name"""
        try:
            result = await self.db_session.execute(
                select(Agents).filter(Agents.hostname == agent_name)
            )
            return result.scalars().first()
        except Exception as e:
            logger.error(f"Error fetching agent {agent_name}: {e}")
            return None

    async def sync_vulnerabilities_for_agent(
        self,
        agent_name: str,
        customer_code: Optional[str] = None
    ) -> VulnerabilitySyncResponse:
        """
        Sync vulnerabilities for a specific agent

        Args:
            agent_name: Name of the agent to sync vulnerabilities for
            customer_code: Optional customer code override

        Returns:
            VulnerabilitySyncResponse with sync results
        """
        try:
            # Get agent from database
            agent = await self.get_agent_by_name(agent_name)
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

            # Fetch vulnerabilities from Elasticsearch
            vulnerability_docs = await self.fetch_vulnerabilities_from_elasticsearch(
                agent_name=agent_name
            )

            if not vulnerability_docs:
                return VulnerabilitySyncResponse(
                    success=True,
                    message=f"No vulnerabilities found for agent {agent_name}",
                    synced_count=0,
                    errors=[]
                )

            synced_count = 0
            errors = []

            for doc in vulnerability_docs:
                try:
                    # Process the vulnerability document
                    vuln_data = self.processor.process_wazuh_document(doc)

                    # Check if vulnerability already exists
                    existing_vuln = await self.db_session.execute(
                        select(AgentVulnerabilities).filter(
                            and_(
                                AgentVulnerabilities.agent_id == agent.agent_id,
                                AgentVulnerabilities.cve_id == vuln_data.cve_id,
                                AgentVulnerabilities.package_name == vuln_data.package_name
                            )
                        )
                    )

                    if existing_vuln.scalars().first():
                        # Update existing vulnerability
                        vuln = existing_vuln.scalars().first()
                        vuln.update_from_model(vuln_data)
                    else:
                        # Create new vulnerability record
                        new_vuln = AgentVulnerabilities.create_from_model(
                            vulnerability_data=vuln_data,
                            agent_id=agent.agent_id,
                            customer_code=customer_code
                        )
                        self.db_session.add(new_vuln)

                    synced_count += 1

                except Exception as vuln_error:
                    error_msg = f"Error processing vulnerability {doc.get('_id', 'unknown')}: {vuln_error}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue

            # Commit all changes
            await self.db_session.commit()

            return VulnerabilitySyncResponse(
                success=True,
                message=f"Successfully synced {synced_count} vulnerabilities for agent {agent_name}",
                synced_count=synced_count,
                errors=errors
            )

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error syncing vulnerabilities for agent {agent_name}: {e}")
            return VulnerabilitySyncResponse(
                success=False,
                message=f"Failed to sync vulnerabilities for agent {agent_name}: {e}",
                synced_count=0,
                errors=[str(e)]
            )

    async def sync_all_vulnerabilities(
        self,
        customer_code: Optional[str] = None
    ) -> VulnerabilitySyncResponse:
        """
        Sync vulnerabilities for all agents or agents of a specific customer

        Args:
            customer_code: Optional customer code to filter agents

        Returns:
            VulnerabilitySyncResponse with overall sync results
        """
        try:
            # Get agents to sync
            query = select(Agents)
            if customer_code:
                query = query.filter(Agents.customer_code == customer_code)

            result = await self.db_session.execute(query)
            agents = result.scalars().all()

            if not agents:
                return VulnerabilitySyncResponse(
                    success=True,
                    message="No agents found to sync",
                    synced_count=0,
                    errors=[]
                )

            total_synced = 0
            all_errors = []

            # Process agents in batches to avoid overwhelming the system
            batch_size = 10
            for i in range(0, len(agents), batch_size):
                batch = agents[i:i + batch_size]
                tasks = []

                for agent in batch:
                    if not agent.hostname:
                        continue

                    task = self.sync_vulnerabilities_for_agent(
                        agent_name=agent.hostname,
                        customer_code=agent.customer_code
                    )
                    tasks.append(task)

                # Run batch concurrently
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for result in results:
                        if isinstance(result, VulnerabilitySyncResponse):
                            total_synced += result.synced_count
                            all_errors.extend(result.errors)
                        else:
                            all_errors.append(str(result))

            return VulnerabilitySyncResponse(
                success=True,
                message=f"Completed vulnerability sync for {len(agents)} agents",
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
        self,
        agent_id: str,
        severity_filter: Optional[List[str]] = None
    ) -> AgentVulnerabilitiesResponse:
        """
        Get vulnerabilities for a specific agent from database

        Args:
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

            result = await self.db_session.execute(query)
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
        self,
        customer_code: Optional[str] = None
    ) -> VulnerabilityStatsResponse:
        """
        Get vulnerability statistics

        Args:
            customer_code: Optional customer code to filter by

        Returns:
            VulnerabilityStatsResponse with statistics
        """
        try:
            query = select(AgentVulnerabilities)
            if customer_code:
                query = query.filter(AgentVulnerabilities.customer_code == customer_code)

            result = await self.db_session.execute(query)
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


async def create_vulnerability_service(db_session: AsyncSession) -> VulnerabilityService:
    """Factory function to create VulnerabilityService instance"""
    return VulnerabilityService(db_session)

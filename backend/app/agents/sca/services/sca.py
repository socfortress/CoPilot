from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.sca.schema.sca import AgentScaOverviewItem
from app.agents.sca.schema.sca import ScaOverviewResponse
from app.agents.sca.schema.sca import ScaStatsResponse
from app.agents.wazuh.services.sca import collect_agent_sca
from app.db.universal_models import Agents


async def get_all_agents_from_db(
    db_session: AsyncSession,
    customer_code: Optional[str] = None,
) -> List[Agents]:
    """
    Get all agents from database, optionally filtered by customer code

    Args:
        db_session: Database session to use
        customer_code: Optional customer code to filter agents by

    Returns:
        List of Agent objects
    """
    try:
        query = select(Agents)
        if customer_code:
            query = query.filter(Agents.customer_code == customer_code)

        result = await db_session.execute(query)
        agents = result.scalars().all()

        logger.info(f"Found {len(agents)} agents" + (f" for customer {customer_code}" if customer_code else ""))
        return agents

    except Exception as e:
        logger.error(f"Error fetching agents from database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch agents: {e}")


async def collect_sca_for_all_agents(
    db_session: AsyncSession,
    customer_code: Optional[str] = None,
    agent_name: Optional[str] = None,
    policy_id: Optional[str] = None,
    policy_name: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
) -> List[AgentScaOverviewItem]:
    """
    Collect SCA results for all agents from Wazuh Manager

    Args:
        db_session: Database session to use
        customer_code: Optional customer code filter
        agent_name: Optional agent name filter
        policy_id: Optional policy ID filter
        policy_name: Optional policy name filter (partial matching)
        min_score: Optional minimum score filter
        max_score: Optional maximum score filter

    Returns:
        List of AgentScaOverviewItem objects
    """
    try:
        # Get agents from database
        agents = await get_all_agents_from_db(db_session, customer_code)

        if not agents:
            logger.warning("No agents found" + (f" for customer {customer_code}" if customer_code else ""))
            return []

        all_sca_results = []

        for agent in agents:
            # Skip if agent name filter is specified and doesn't match
            if agent_name and agent.hostname != agent_name:
                continue

            try:
                logger.info(f"Collecting SCA results for agent: {agent.hostname}")

                # Collect SCA data from Wazuh Manager for this agent
                sca_response = await collect_agent_sca(agent.agent_id)

                if not sca_response.success or not sca_response.sca:
                    logger.warning(f"No SCA data found for agent {agent.hostname}")
                    continue

                # Process each SCA policy result for this agent
                for sca_result in sca_response.sca:
                    # Apply filters
                    if policy_id and sca_result.policy_id != policy_id:
                        continue

                    if policy_name and policy_name.lower() not in sca_result.name.lower():
                        continue

                    if min_score is not None and sca_result.score < min_score:
                        continue

                    if max_score is not None and sca_result.score > max_score:
                        continue

                    # Create overview item
                    overview_item = AgentScaOverviewItem(
                        agent_id=agent.agent_id,
                        agent_name=agent.hostname,
                        customer_code=agent.customer_code,
                        policy_id=sca_result.policy_id,
                        policy_name=sca_result.name,
                        description=sca_result.description,
                        total_checks=sca_result.total_checks,
                        pass_count=sca_result.pass_count,
                        fail_count=sca_result.fail,
                        invalid_count=sca_result.invalid,
                        score=sca_result.score,
                        start_scan=sca_result.start_scan,
                        end_scan=sca_result.end_scan,
                        references=sca_result.references,
                        hash_file=sca_result.hash_file,
                    )

                    all_sca_results.append(overview_item)

            except Exception as e:
                logger.error(f"Error collecting SCA for agent {agent.hostname}: {e}")
                # Continue with other agents even if one fails
                continue

        logger.info(f"Collected SCA results for {len(all_sca_results)} policy results across agents")
        return all_sca_results

    except Exception as e:
        logger.error(f"Error collecting SCA for all agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to collect SCA results: {e}")


async def search_sca_overview(
    db_session: AsyncSession,
    customer_code: Optional[str] = None,
    agent_name: Optional[str] = None,
    policy_id: Optional[str] = None,
    policy_name: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
) -> ScaOverviewResponse:
    """
    Search SCA results across all agents with filtering and pagination

    Args:
        db_session: Database session for agent lookup
        customer_code: Optional customer code filter
        agent_name: Optional agent hostname filter
        policy_id: Optional policy ID filter
        policy_name: Optional policy name filter (partial matching)
        min_score: Optional minimum score filter
        max_score: Optional maximum score filter
        page: Page number for pagination
        page_size: Number of results per page

    Returns:
        ScaOverviewResponse with paginated results and statistics
    """
    logger.info(
        f"Searching SCA overview with filters: customer_code={customer_code}, "
        f"agent_name={agent_name}, policy_id={policy_id}, policy_name={policy_name}, "
        f"min_score={min_score}, max_score={max_score}, page={page}, page_size={page_size}",
    )

    # Build filters applied dict for response
    filters_applied = {}
    if customer_code:
        filters_applied["customer_code"] = customer_code
    if agent_name:
        filters_applied["agent_name"] = agent_name
    if policy_id:
        filters_applied["policy_id"] = policy_id
    if policy_name:
        filters_applied["policy_name"] = policy_name
    if min_score is not None:
        filters_applied["min_score"] = min_score
    if max_score is not None:
        filters_applied["max_score"] = max_score

    try:
        # Collect all SCA results with filtering
        all_sca_results = await collect_sca_for_all_agents(
            db_session=db_session,
            customer_code=customer_code,
            agent_name=agent_name,
            policy_id=policy_id,
            policy_name=policy_name,
            min_score=min_score,
            max_score=max_score,
        )

        total_count = len(all_sca_results)

        # Calculate pagination
        total_pages = (total_count + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        # Get paginated results
        paginated_results = all_sca_results[start_idx:end_idx]

        # Calculate statistics
        unique_agents = set(item.agent_id for item in all_sca_results)
        unique_policies = set(item.policy_id for item in all_sca_results)

        total_checks_all = sum(item.total_checks for item in all_sca_results)
        total_passes_all = sum(item.pass_count for item in all_sca_results)
        total_fails_all = sum(item.fail_count for item in all_sca_results)
        total_invalid_all = sum(item.invalid_count for item in all_sca_results)

        # Calculate average score
        average_score = sum(item.score for item in all_sca_results) / len(all_sca_results) if all_sca_results else 0.0

        return ScaOverviewResponse(
            sca_results=paginated_results,
            total_count=total_count,
            total_agents=len(unique_agents),
            total_policies=len(unique_policies),
            average_score=round(average_score, 2),
            total_checks_all_agents=total_checks_all,
            total_passes_all_agents=total_passes_all,
            total_fails_all_agents=total_fails_all,
            total_invalid_all_agents=total_invalid_all,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
            success=True,
            message=f"Found {total_count} SCA results across {len(unique_agents)} agents",
            filters_applied=filters_applied,
        )

    except Exception as e:
        logger.error(f"Error in SCA overview search: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search SCA results: {e}")


async def get_sca_statistics(
    db_session: AsyncSession,
    customer_code: Optional[str] = None,
) -> ScaStatsResponse:
    """
    Get SCA statistics across all agents or for a specific customer

    Args:
        db_session: Database session to use
        customer_code: Optional customer code to filter by

    Returns:
        ScaStatsResponse with SCA statistics
    """
    try:
        logger.info("Getting SCA statistics" + (f" for customer {customer_code}" if customer_code else " for all customers"))

        # Collect all SCA results
        all_sca_results = await collect_sca_for_all_agents(
            db_session=db_session,
            customer_code=customer_code,
        )

        if not all_sca_results:
            return ScaStatsResponse(
                total_agents_with_sca=0,
                total_policies=0,
                average_score_across_all=0.0,
                total_checks_all_agents=0,
                total_passes_all_agents=0,
                total_fails_all_agents=0,
                total_invalid_all_agents=0,
                by_customer={},
                success=True,
                message="No SCA results found",
            )

        # Calculate overall statistics
        unique_agents = set(item.agent_id for item in all_sca_results)
        unique_policies = set(item.policy_id for item in all_sca_results)

        total_checks_all = sum(item.total_checks for item in all_sca_results)
        total_passes_all = sum(item.pass_count for item in all_sca_results)
        total_fails_all = sum(item.fail_count for item in all_sca_results)
        total_invalid_all = sum(item.invalid_count for item in all_sca_results)

        average_score = sum(item.score for item in all_sca_results) / len(all_sca_results)

        # Group by customer if no specific customer requested
        by_customer = {}
        if not customer_code:
            customer_groups = {}
            for item in all_sca_results:
                cust_code = item.customer_code or "unknown"
                if cust_code not in customer_groups:
                    customer_groups[cust_code] = []
                customer_groups[cust_code].append(item)

            for cust_code, items in customer_groups.items():
                unique_agents_cust = set(item.agent_id for item in items)
                unique_policies_cust = set(item.policy_id for item in items)
                avg_score_cust = sum(item.score for item in items) / len(items)

                by_customer[cust_code] = {
                    "total_agents": len(unique_agents_cust),
                    "total_policies": len(unique_policies_cust),
                    "average_score": round(avg_score_cust, 2),
                    "total_checks": sum(item.total_checks for item in items),
                    "total_passes": sum(item.pass_count for item in items),
                    "total_fails": sum(item.fail_count for item in items),
                    "total_invalid": sum(item.invalid_count for item in items),
                }

        return ScaStatsResponse(
            total_agents_with_sca=len(unique_agents),
            total_policies=len(unique_policies),
            average_score_across_all=round(average_score, 2),
            total_checks_all_agents=total_checks_all,
            total_passes_all_agents=total_passes_all,
            total_fails_all_agents=total_fails_all,
            total_invalid_all_agents=total_invalid_all,
            by_customer=by_customer,
            success=True,
            message=f"SCA statistics calculated for {len(unique_agents)} agents",
        )

    except Exception as e:
        logger.error(f"Error getting SCA statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get SCA statistics: {e}")

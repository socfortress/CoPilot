import csv
import hashlib
import io
import json
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.sca.schema.sca import AgentScaOverviewItem
from app.agents.sca.schema.sca import ScaOverviewResponse
from app.agents.sca.schema.sca import ScaStatsResponse
from app.agents.sca.schema.sca import (
    SCAReportGenerateRequest,
    SCAReportGenerateResponse,
    SCAReportListResponse,
    SCAReportResponse,
)
from app.agents.wazuh.services.sca import collect_agent_sca
from app.auth.models.users import User
from app.data_store.data_store_operations import (
    delete_file_from_minio,
    retrieve_file_from_minio,
    store_file_in_minio,
)
from app.db.universal_models import Agents, SCAReport
from app.middleware.customer_access import customer_access_handler


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

        # Sort results by agent's minimum score (lowest first)
        if all_sca_results:
            # Group results by agent to find minimum score per agent
            agent_min_scores = {}
            agent_results = {}

            for result in all_sca_results:
                agent_id = result.agent_id
                if agent_id not in agent_min_scores:
                    agent_min_scores[agent_id] = result.score
                    agent_results[agent_id] = []
                else:
                    agent_min_scores[agent_id] = min(agent_min_scores[agent_id], result.score)
                agent_results[agent_id].append(result)

            # Sort agents by their minimum score (lowest first)
            sorted_agent_ids = sorted(agent_min_scores.keys(), key=lambda x: agent_min_scores[x])

            # Rebuild the results list with agents sorted by their minimum score
            all_sca_results = []
            for agent_id in sorted_agent_ids:
                # Sort policies within each agent by score (lowest first)
                agent_policies = sorted(agent_results[agent_id], key=lambda x: x.score)
                all_sca_results.extend(agent_policies)

            logger.info("Sorted SCA results by agent minimum scores (lowest first)")

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
            message=f"Found {total_count} SCA results across {len(unique_agents)} agents (sorted by agent minimum score, lowest first)",
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

async def collect_sca_for_report(
    db_session: AsyncSession,
    current_user: User,
    customer_code: str,
    agent_name: Optional[str] = None,
    policy_id: Optional[str] = None,
    min_score: Optional[int] = None,
    max_score: Optional[int] = None,
) -> List[AgentScaOverviewItem]:
    """
    Collect ALL SCA results from Wazuh Manager API for CSV report generation.

    This uses the same data collection method as the overview search,
    but without pagination to get all results for comprehensive reports.

    Args:
        db_session: Database session for agent lookup
        current_user: Current authenticated user for customer access filtering
        customer_code: Customer code to filter by
        agent_name: Optional agent hostname filter
        policy_id: Optional policy ID filter
        min_score: Optional minimum score filter
        max_score: Optional maximum score filter

    Returns:
        List of all matching SCA policy results (no pagination)
    """
    logger.info(
        f"Collecting ALL SCA results from Wazuh Manager for report: customer_code={customer_code}, "
        f"agent_name={agent_name}, policy_id={policy_id}, "
        f"min_score={min_score}, max_score={max_score}"
    )

    # Apply customer access filtering
    accessible_customers = await customer_access_handler.get_user_accessible_customers(
        current_user, db_session
    )

    if "*" not in accessible_customers and customer_code not in accessible_customers:
        logger.warning(f"User {current_user.username} denied access to customer {customer_code}")
        return []

    try:
        # Use existing collect function to get all SCA results from Wazuh Manager
        all_sca_results = await collect_sca_for_all_agents(
            db_session=db_session,
            customer_code=customer_code,
            agent_name=agent_name,
            policy_id=policy_id,
            policy_name=None,  # Not used for reports
            min_score=min_score,
            max_score=max_score,
        )

        logger.info(f"Successfully collected {len(all_sca_results)} SCA policy results from Wazuh Manager for report")
        return all_sca_results

    except Exception as e:
        logger.error(f"Error collecting SCA results for report: {e}")
        raise


async def generate_sca_csv_report(
    db_session: AsyncSession,
    current_user: User,
    request: SCAReportGenerateRequest,
    report_id: Optional[int] = None,
) -> SCAReportGenerateResponse:
    """
    Generate a CSV SCA report for a specific customer and store it in MinIO.

    Uses Wazuh Manager API to fetch all SCA policy-level data for comprehensive reports.

    Args:
        db_session: Database session
        current_user: Current authenticated user
        request: Report generation request with filters
        report_id: Optional existing report ID (for background task updates)

    Returns:
        SCAReportGenerateResponse with report details
    """
    try:
        # Verify customer access
        accessible_customers = await customer_access_handler.get_user_accessible_customers(
            current_user, db_session
        )

        if "*" not in accessible_customers and request.customer_code not in accessible_customers:
            # If we have a report_id, update it to failed status
            if report_id:
                stmt = select(SCAReport).filter(SCAReport.id == report_id)
                result = await db_session.execute(stmt)
                report = result.scalars().first()
                if report:
                    report.status = "failed"
                    report.error_message = "Insufficient permissions"
                    await db_session.commit()

            return SCAReportGenerateResponse(
                success=False,
                message=f"Access denied to customer {request.customer_code}",
                error="Insufficient permissions",
            )

        # If report_id exists, get the existing report name and object_key
        # Otherwise generate new ones
        if report_id:
            stmt = select(SCAReport).filter(SCAReport.id == report_id)
            result = await db_session.execute(stmt)
            existing_report = result.scalars().first()

            if not existing_report:
                return SCAReportGenerateResponse(
                    success=False,
                    message=f"Report ID {report_id} not found",
                    error="Report not found",
                )

            # Use existing report name and paths
            report_name = existing_report.report_name
            file_name = existing_report.file_name
            object_key = existing_report.object_key
            bucket_name = existing_report.bucket_name

            logger.info(
                f"Generating SCA report for existing record: {report_name} (ID: {report_id})"
            )
        else:
            # Generate new report name for synchronous generation
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            report_name = request.report_name or f"sca_report_{timestamp}"
            file_name = f"{report_name}.csv"
            object_key = f"{request.customer_code}/{file_name}"
            bucket_name = "sca-reports"

            logger.info(f"Generating new SCA report: {report_name}")

        # Fetch ALL SCA results from Wazuh Manager API (no pagination limits)
        all_sca_results = await collect_sca_for_report(
            db_session=db_session,
            current_user=current_user,
            customer_code=request.customer_code,
            agent_name=request.agent_name,
            policy_id=request.policy_id,
            min_score=request.min_score,
            max_score=request.max_score,
        )

        logger.info(f"Fetched {len(all_sca_results)} SCA policy results from Wazuh Manager for report")

        if not all_sca_results:
            # If we have a report_id, update it to failed status
            if report_id:
                stmt = select(SCAReport).filter(SCAReport.id == report_id)
                result = await db_session.execute(stmt)
                report = result.scalars().first()
                if report:
                    report.status = "failed"
                    report.error_message = "No SCA results found matching criteria"
                    await db_session.commit()

            return SCAReportGenerateResponse(
                success=False,
                message="No SCA results found matching the specified criteria",
                error="No data to export",
            )

        # Generate CSV content
        csv_buffer = io.StringIO()
        csv_writer = csv.writer(csv_buffer)

        # Write headers
        headers = [
            "Agent ID",
            "Agent Name",
            "Customer Code",
            "Policy ID",
            "Policy Name",
            "Description",
            "Total Checks",
            "Passed",
            "Failed",
            "Invalid",
            "Score",
            "Start Scan",
            "End Scan",
            "References",
            "Hash File",
        ]
        csv_writer.writerow(headers)

        # Count totals
        total_policies = len(all_sca_results)
        total_checks = sum(result.total_checks for result in all_sca_results)
        passed_count = sum(result.pass_count for result in all_sca_results)
        failed_count = sum(result.fail_count for result in all_sca_results)
        invalid_count = sum(result.invalid_count for result in all_sca_results)

        # Write data rows
        for result in all_sca_results:
            try:
                row = [
                    result.agent_id,
                    result.agent_name,
                    result.customer_code or "",
                    result.policy_id,
                    result.policy_name,
                    result.description,
                    result.total_checks,
                    result.pass_count,
                    result.fail_count,
                    result.invalid_count,
                    result.score,
                    result.start_scan,
                    result.end_scan,
                    result.references or "",
                    result.hash_file or "",
                ]
                csv_writer.writerow(row)

            except Exception as row_error:
                logger.error(f"Error processing SCA row: {row_error}")
                continue

        # Get CSV content as bytes
        csv_content = csv_buffer.getvalue().encode("utf-8")
        csv_buffer.close()

        # Calculate file hash
        file_hash = hashlib.sha256(csv_content).hexdigest()

        # Store in MinIO
        minio_result = await store_file_in_minio(
            file_content=csv_content,
            bucket_name=bucket_name,
            object_key=object_key,
            content_type="text/csv",
        )

        if not minio_result["success"]:
            # If we have a report_id, update it to failed status
            if report_id:
                stmt = select(SCAReport).filter(SCAReport.id == report_id)
                result = await db_session.execute(stmt)
                report = result.scalars().first()
                if report:
                    report.status = "failed"
                    report.error_message = minio_result.get("error", "Unknown error")
                    await db_session.commit()

            return SCAReportGenerateResponse(
                success=False,
                message="Failed to store report in MinIO",
                error=minio_result.get("error", "Unknown error"),
            )

        # Build filters JSON
        filters = {}
        if request.agent_name:
            filters["agent_name"] = request.agent_name
        if request.policy_id:
            filters["policy_id"] = request.policy_id
        if request.min_score is not None:
            filters["min_score"] = request.min_score
        if request.max_score is not None:
            filters["max_score"] = request.max_score

        # Check if we're updating an existing report or creating a new one
        if report_id:
            # Update existing report (background task scenario)
            stmt = select(SCAReport).filter(SCAReport.id == report_id)
            result = await db_session.execute(stmt)
            report_record = result.scalars().first()

            if report_record:
                report_record.file_size = len(csv_content)
                report_record.file_hash = file_hash
                report_record.total_policies = total_policies
                report_record.total_checks = total_checks
                report_record.passed_count = passed_count
                report_record.failed_count = failed_count
                report_record.invalid_count = invalid_count
                report_record.status = "completed"
                report_record.error_message = None

                await db_session.commit()
                await db_session.refresh(report_record)

                logger.info(
                    f"Successfully updated SCA report: {report_name} (ID: {report_id})"
                )
            else:
                logger.error(f"Report ID {report_id} not found for update")
                return SCAReportGenerateResponse(
                    success=False,
                    message=f"Report ID {report_id} not found",
                    error="Report not found",
                )
        else:
            # Create new database record (synchronous scenario)
            report_record = SCAReport(
                report_name=report_name,
                customer_code=request.customer_code,
                bucket_name=bucket_name,
                object_key=object_key,
                file_name=file_name,
                file_size=len(csv_content),
                file_hash=file_hash,
                generated_by=current_user.id,
                filters_json=json.dumps(filters),
                total_policies=total_policies,
                total_checks=total_checks,
                passed_count=passed_count,
                failed_count=failed_count,
                invalid_count=invalid_count,
                status="completed",
            )

            db_session.add(report_record)
            await db_session.commit()
            await db_session.refresh(report_record)

            logger.info(f"Successfully generated SCA report: {report_name}")

        # Build response
        report_response = SCAReportResponse(
            id=report_record.id,
            report_name=report_record.report_name,
            customer_code=report_record.customer_code,
            file_name=report_record.file_name,
            file_size=report_record.file_size,
            generated_at=report_record.generated_at,
            generated_by=report_record.generated_by,
            total_policies=report_record.total_policies,
            total_checks=report_record.total_checks,
            passed_count=report_record.passed_count,
            failed_count=report_record.failed_count,
            invalid_count=report_record.invalid_count,
            filters_applied=json.loads(report_record.filters_json or "{}"),
            status=report_record.status,
            download_url=f"/api/v1/sca/reports/{report_record.id}/download",
        )

        return SCAReportGenerateResponse(
            success=True,
            message=f"Successfully generated report with {total_policies} SCA policy results",
            report=report_response,
        )

    except Exception as e:
        logger.error(f"Error generating SCA report: {e}")

        # If we have a report_id, update it to failed status
        if report_id:
            try:
                stmt = select(SCAReport).filter(SCAReport.id == report_id)
                result = await db_session.execute(stmt)
                report = result.scalars().first()
                if report:
                    report.status = "failed"
                    report.error_message = str(e)
                    await db_session.commit()
            except Exception as update_error:
                logger.error(f"Failed to update report status: {update_error}")

        return SCAReportGenerateResponse(
            success=False,
            message="Failed to generate SCA report",
            error=str(e),
        )


async def list_sca_reports(
    db_session: AsyncSession,
    current_user: User,
    customer_code: Optional[str] = None,
) -> SCAReportListResponse:
    """List available SCA reports"""
    try:
        # Get accessible customers
        accessible_customers = await customer_access_handler.get_user_accessible_customers(
            current_user, db_session
        )

        # Build query
        query = select(SCAReport).order_by(desc(SCAReport.generated_at))

        # Apply customer filtering
        if "*" not in accessible_customers:
            query = query.filter(SCAReport.customer_code.in_(accessible_customers))

        if customer_code:
            if (
                "*" not in accessible_customers
                and customer_code not in accessible_customers
            ):
                return SCAReportListResponse(
                    reports=[],
                    total_count=0,
                    success=True,
                    message=f"Access denied to customer {customer_code}",
                )
            query = query.filter(SCAReport.customer_code == customer_code)

        result = await db_session.execute(query)
        reports = result.scalars().all()

        report_list = []
        for report in reports:
            report_response = SCAReportResponse(
                id=report.id,
                report_name=report.report_name,
                customer_code=report.customer_code,
                file_name=report.file_name,
                file_size=report.file_size,
                generated_at=report.generated_at,
                generated_by=report.generated_by,
                total_policies=report.total_policies,
                total_checks=report.total_checks,
                passed_count=report.passed_count,
                failed_count=report.failed_count,
                invalid_count=report.invalid_count,
                filters_applied=json.loads(report.filters_json or "{}"),
                status=report.status,
                error_message=report.error_message,
                download_url=f"/api/v1/sca/reports/{report.id}/download",
            )
            report_list.append(report_response)

        return SCAReportListResponse(
            reports=report_list,
            total_count=len(report_list),
            success=True,
            message=f"Found {len(report_list)} SCA reports",
        )

    except Exception as e:
        logger.error(f"Error listing SCA reports: {e}")
        return SCAReportListResponse(
            reports=[],
            total_count=0,
            success=False,
            message=f"Failed to list reports: {e}",
        )


async def get_sca_report_download(
    db_session: AsyncSession,
    current_user: User,
    report_id: int,
) -> Dict[str, Any]:
    """Get SCA report for download"""
    try:
        # Get report record
        result = await db_session.execute(
            select(SCAReport).filter(SCAReport.id == report_id)
        )
        report = result.scalars().first()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        # Verify customer access
        accessible_customers = await customer_access_handler.get_user_accessible_customers(
            current_user, db_session
        )

        if (
            "*" not in accessible_customers
            and report.customer_code not in accessible_customers
        ):
            raise HTTPException(status_code=403, detail="Access denied to this report")

        # Retrieve file from MinIO
        file_data = await retrieve_file_from_minio(
            bucket_name=report.bucket_name,
            object_key=report.object_key,
        )

        if not file_data["success"]:
            raise HTTPException(status_code=500, detail="Failed to retrieve report file")

        return {
            "file_content": file_data["file_content"],
            "file_name": report.file_name,
            "content_type": "text/csv",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving SCA report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve report: {e}")

async def delete_sca_report(
    db_session: AsyncSession,
    current_user: User,
    report_id: int,
) -> Dict[str, Any]:
    """
    Delete an SCA report and its associated file from MinIO.

    Args:
        db_session: Database session
        current_user: Current authenticated user
        report_id: ID of the report to delete

    Returns:
        Dict with success status and message
    """
    try:
        # Get report record
        result = await db_session.execute(
            select(SCAReport).filter(SCAReport.id == report_id)
        )
        report = result.scalars().first()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        # Verify customer access
        accessible_customers = await customer_access_handler.get_user_accessible_customers(
            current_user, db_session
        )

        if (
            "*" not in accessible_customers
            and report.customer_code not in accessible_customers
        ):
            raise HTTPException(status_code=403, detail="Access denied to this report")

        # Delete file from MinIO
        logger.info(f"Deleting SCA report file from MinIO: {report.bucket_name}/{report.object_key}")

        minio_result = await delete_file_from_minio(
            bucket_name=report.bucket_name,
            object_key=report.object_key,
        )

        if not minio_result["success"]:
            logger.warning(f"Failed to delete file from MinIO: {minio_result.get('message')}")
            # Continue with database deletion even if MinIO deletion fails

        # Delete database record
        await db_session.delete(report)
        await db_session.commit()

        logger.info(f"Successfully deleted SCA report: {report.report_name} (ID: {report_id})")

        return {
            "success": True,
            "message": f"Successfully deleted report '{report.report_name}'",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting SCA report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {e}")

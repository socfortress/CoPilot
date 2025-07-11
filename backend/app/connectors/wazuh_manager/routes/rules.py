# App specific imports
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import Path
from fastapi import Query
from fastapi import Security
from fastapi import UploadFile
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.routes.auth import AuthHandler
from app.connectors.wazuh_manager.models.rules import DisabledRule

# from app.connectors.wazuh_manager.schema.rules import RuleExclude
from app.connectors.wazuh_manager.schema.rules import AllDisabledRuleResponse
from app.connectors.wazuh_manager.schema.rules import RuleDisable
from app.connectors.wazuh_manager.schema.rules import RuleDisableResponse
from app.connectors.wazuh_manager.schema.rules import RuleEnable
from app.connectors.wazuh_manager.schema.rules import RuleEnableResponse
from app.connectors.wazuh_manager.schema.rules import RuleExcludeRequest
from app.connectors.wazuh_manager.schema.rules import RuleExcludeResponse
from app.connectors.wazuh_manager.schema.rules import WazuhRuleFileContentResponse
from app.connectors.wazuh_manager.schema.rules import WazuhRuleFilesResponse
from app.connectors.wazuh_manager.schema.rules import WazuhRuleFileUploadResponse
from app.connectors.wazuh_manager.schema.rules import WazuhRulesResponse

# from app.connectors.wazuh_manager.schema.rules import RuleExclude
# from app.connectors.wazuh_manager.schema.rules import RuleExcludeResponse
from app.connectors.wazuh_manager.services.rules import disable_rule
from app.connectors.wazuh_manager.services.rules import enable_rule
from app.connectors.wazuh_manager.services.rules import get_wazuh_rule_file_content
from app.connectors.wazuh_manager.services.rules import get_wazuh_rule_files
from app.connectors.wazuh_manager.services.rules import get_wazuh_rules
from app.connectors.wazuh_manager.services.rules import post_to_copilot_ai_module
from app.connectors.wazuh_manager.services.rules import update_wazuh_rule_file

# from app.connectors.wazuh_manager.services.rules import exclude_rule
from app.db.db_session import get_db

# from app.connectors.wazuh_manager.services.rules import exclude_rule


NEW_LEVEL = "1"
wazuh_manager_rules_router = APIRouter()
auth_handler = AuthHandler()


@wazuh_manager_rules_router.get(
    "/rule/disabled",
    response_model=AllDisabledRuleResponse,
    description="Get all disabled rules",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_disabled_rules(
    session: AsyncSession = Depends(get_db),
) -> AllDisabledRuleResponse:
    """
    Retrieve all disabled rules from the database.

    Parameters:
    - session: The database session to use (AsyncSession).

    Returns:
    - AllDisabledRuleResponse: The response containing the list of disabled rules (AllDisabledRuleResponse).
    """
    result = await session.execute(select(DisabledRule))
    disabled_rules = result.scalars().all()
    return AllDisabledRuleResponse(
        disabled_rules=disabled_rules,
        success=True,
        message="Successfully fetched all disabled rules",
    )


@wazuh_manager_rules_router.post(
    "/rule/disable",
    response_model=RuleDisableResponse,
    description="Disable a Wazuh Rule",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def disable_wazuh_rule(
    rule: RuleDisable,
    session: AsyncSession = Depends(get_db),
    username: str = Depends(AuthHandler().get_current_user),
) -> RuleDisableResponse:
    """
    Disable a Wazuh Rule.

    Args:
        rule (RuleDisable): The rule to be disabled.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).
        username (str, optional): The username of the current user. Defaults to Depends(AuthHandler().get_current_user).

    Returns:
        RuleDisableResponse: The response containing the disabled rule information.

    Raises:
        HTTPException: If the rule is already disabled or if the rule cannot be disabled.
    """
    # Asynchronously check if the rule is already disabled
    result = await session.execute(
        select(DisabledRule).where(DisabledRule.rule_id == rule.rule_id),
    )
    if result.scalars().first():
        raise HTTPException(status_code=500, detail="Rule is already disabled")

    # This should be converted to an async operation if it's not already
    rule_disabled = await disable_rule(rule)
    if rule_disabled:
        new_disabled_rule = DisabledRule(
            rule_id=rule.rule_id,
            previous_level=rule_disabled.previous_level,
            new_level=NEW_LEVEL,
            reason_for_disabling=rule.reason_for_disabling,
            length_of_time=rule.length_of_time,
            disabled_by=username.username,
        )
        session.add(new_disabled_rule)
        await session.commit()
        return rule_disabled
    else:
        raise HTTPException(status_code=404, detail="Was not able to disable rule")


@wazuh_manager_rules_router.post(
    "/rule/enable",
    response_model=RuleEnableResponse,
    description="Enable a Wazuh Rule",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def enable_wazuh_rule(
    rule: RuleEnable,
    session: AsyncSession = Depends(get_db),
) -> RuleEnableResponse:
    """
    Enable a Wazuh rule.

    Args:
        rule (RuleEnable): The rule to enable.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        RuleEnableResponse: The response indicating whether the rule was enabled successfully.

    Raises:
        HTTPException: If the rule is already enabled or if the rule could not be enabled.
    """
    # Asynchronously fetch the disabled rule
    logger.info(f"rule: {rule}")
    result = await session.execute(
        select(DisabledRule).where(DisabledRule.rule_id == rule.rule_id),
    )
    disabled_rule = result.scalars().first()

    if not disabled_rule:
        raise HTTPException(status_code=404, detail="Rule is already enabled")

    # This should be converted to an async operation if it's not already
    rule_enabled = await enable_rule(rule, disabled_rule.previous_level)

    if rule_enabled:
        await session.delete(disabled_rule)
        await session.commit()
        return rule_enabled
    else:
        raise HTTPException(status_code=404, detail="Was not able to enable rule")


@wazuh_manager_rules_router.post(
    "/rule/exclude",
    response_model=RuleExcludeResponse,
    description="Retrieve recommended exclusion for a Wazuh Rule",
)
async def exclude_wazuh_rule(request: RuleExcludeRequest) -> RuleExcludeResponse:
    return await post_to_copilot_ai_module(data=request)


@wazuh_manager_rules_router.get(
    "/rules",
    response_model=WazuhRulesResponse,
    description="List Wazuh rules",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def list_wazuh_rules(
    rule_ids: Optional[List[int]] = Query(None, description="List of rule IDs"),
    pretty: Optional[bool] = Query(False, description="Show results in human-readable format"),
    wait_for_complete: Optional[bool] = Query(False, description="Disable timeout response"),
    offset: Optional[int] = Query(0, ge=0, description="First element to return"),
    limit: Optional[int] = Query(500, ge=1, le=100000, description="Maximum number of elements"),
    select: Optional[List[str]] = Query(None, description="Fields to return"),
    sort: Optional[str] = Query(None, description="Sort fields"),
    search: Optional[str] = Query(None, description="Search text"),
    q: Optional[str] = Query(None, description="Query filter"),
    status: Optional[str] = Query(None, description="Rule status filter"),
    group: Optional[str] = Query(None, description="Rule group filter"),
    level: Optional[str] = Query(None, description="Rule level filter"),
    filename: Optional[List[str]] = Query(None, description="Filename filter"),
    relative_dirname: Optional[str] = Query(None, description="Directory filter"),
    pci_dss: Optional[str] = Query(None, description="PCI DSS filter"),
    gdpr: Optional[str] = Query(None, description="GDPR filter"),
    gpg13: Optional[str] = Query(None, description="GPG13 filter"),
    hipaa: Optional[str] = Query(None, description="HIPAA filter"),
    nist_800_53: Optional[str] = Query(None, description="NIST 800-53 filter"),
    tsc: Optional[str] = Query(None, description="TSC filter"),
    mitre: Optional[str] = Query(None, description="MITRE filter"),
    distinct: Optional[bool] = Query(False, description="Distinct values only"),
) -> WazuhRulesResponse:
    """
    List Wazuh rules with comprehensive filtering options.

    Returns a list of Wazuh rules from the Wazuh Manager API with support for
    filtering by various criteria including compliance frameworks and MITRE ATT&CK.
    """
    # Use **locals() to pass all parameters efficiently
    params = {k: v for k, v in locals().items() if k not in ["auth_handler"]}
    return await get_wazuh_rules(**params)


@wazuh_manager_rules_router.get(
    "/rules/files",
    response_model=WazuhRuleFilesResponse,
    description="List Wazuh rule files",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def list_wazuh_rule_files(
    pretty: Optional[bool] = Query(False, description="Show results in human-readable format"),
    wait_for_complete: Optional[bool] = Query(False, description="Disable timeout response"),
    offset: Optional[int] = Query(0, ge=0, description="First element to return in the collection"),
    limit: Optional[int] = Query(500, ge=1, le=100000, description="Maximum number of elements to return"),
    sort: Optional[str] = Query(None, description="Sort the collection by a field or fields"),
    search: Optional[str] = Query(None, description="Look for elements containing the specified string"),
    relative_dirname: Optional[str] = Query(None, description="Filter by relative directory name"),
    filename: Optional[List[str]] = Query(None, description="Filter by filename of rule files"),
    status: Optional[str] = Query(None, description="Filter by list status (enabled, disabled, all)"),
    q: Optional[str] = Query(None, description="Query to filter results by"),
    select: Optional[List[str]] = Query(None, description="Select which fields to return"),
    distinct: Optional[bool] = Query(False, description="Look for distinct values"),
) -> WazuhRuleFilesResponse:
    """
    Retrieve a list of Wazuh rule files from the Wazuh Manager.

    This endpoint provides access to all rule files used to define Wazuh rules,
    including their status and location within the ruleset directory structure.

    Parameters:
    - pretty: Format results for human readability
    - wait_for_complete: Disable request timeout
    - offset: Pagination offset (default: 0)
    - limit: Maximum results per page (default: 500, max: 100000)
    - sort: Fields to sort by (use +/- prefix for ascending/descending)
    - search: Text search across file properties
    - relative_dirname: Filter by relative directory path
    - filename: Filter by specific rule filenames
    - status: Filter by file status (enabled/disabled/all)
    - q: Advanced query filter
    - select: Comma-separated list of fields to return
    - distinct: Return only distinct values

    Returns:
    - WazuhRuleFilesResponse: List of rule files with their status and location metadata.
    """
    # Use locals() to capture all parameters, excluding non-parameter variables
    params = {k: v for k, v in locals().items()}
    return await get_wazuh_rule_files(**params)


@wazuh_manager_rules_router.get(
    "/rules/files/{filename}",
    response_model=WazuhRuleFileContentResponse,
    description="Get Wazuh rule file content",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def get_wazuh_rule_file_content_endpoint(
    filename: str = Path(..., description="Filename (rule or decoder) to get content for"),
    pretty: Optional[bool] = Query(False, description="Show results in human-readable format"),
    wait_for_complete: Optional[bool] = Query(False, description="Disable timeout response"),
    raw: Optional[bool] = Query(True, description="Format response in plain text"),
    relative_dirname: Optional[str] = Query(None, description="Filter by relative directory name"),
) -> WazuhRuleFileContentResponse:
    """
    Get the content of a specified rule file in the ruleset.

    This endpoint retrieves the full content of a Wazuh rule file, which can contain
    multiple rule groups and individual rules with their configurations.

    Parameters:
    - filename: The name of the rule file to retrieve (required)
    - pretty: Format results for human readability
    - wait_for_complete: Disable request timeout
    - raw: Return content as plain text instead of structured data
    - relative_dirname: Filter by relative directory name

    Returns:
    - WazuhRuleFileContentResponse: The content of the rule file, either as structured
      data (default) or as raw text (when raw=true).

    Raises:
    - 404: If the specified rule file is not found
    - 500: If there's an error retrieving the file content
    """
    # Use locals() to capture all parameters, excluding the filename path parameter
    params = {k: v for k, v in locals().items() if k != "filename"}
    return await get_wazuh_rule_file_content(filename, **params)


@wazuh_manager_rules_router.put(
    "/rules/files/{filename}",
    response_model=WazuhRuleFileUploadResponse,
    description="Upload or update a Wazuh rule file",
    dependencies=[Security(AuthHandler().get_current_user, scopes=["admin"])],
)
async def update_wazuh_rule_file_endpoint(
    filename: str = Path(..., description="Name of the rule file to upload/update"),
    file: UploadFile = File(..., description="Rule file content (XML format)"),
    pretty: Optional[bool] = Query(False, description="Show results in human-readable format"),
    wait_for_complete: Optional[bool] = Query(False, description="Disable timeout response"),
    overwrite: Optional[bool] = Query(True, description="Whether to overwrite the file if it exists"),
    relative_dirname: Optional[str] = Query(None, description="Relative directory name"),
) -> WazuhRuleFileUploadResponse:
    """
    Upload or update a Wazuh rule file in the ruleset.

    This endpoint allows you to upload a new rule file or update an existing one
    in the Wazuh Manager ruleset. The file should be in XML format containing
    valid Wazuh rule definitions.

    Parameters:
    - filename: The name of the rule file to upload/update (required)
    - file: The rule file content as a binary upload (required, should be XML format)
    - pretty: Format results for human readability
    - wait_for_complete: Disable request timeout
    - overwrite: Whether to overwrite the file if it already exists
    - relative_dirname: Relative directory name where the file should be placed

    Returns:
    - WazuhRuleFileUploadResponse: Confirmation of successful upload/update with file details

    Raises:
    - 400: If the file format is invalid or parameters are incorrect
    - 409: If the file already exists and overwrite is False
    - 500: If there's an error uploading the file
    """
    # Validate file content type (should be XML or octet-stream)
    if file.content_type and not any(ct in file.content_type.lower() for ct in ["xml", "text", "octet-stream", "application/xml"]):
        logger.warning(f"Unexpected content type: {file.content_type}")

    try:
        # Read file content
        file_content = await file.read()

        # Validate that we have content
        if not file_content:
            raise HTTPException(status_code=400, detail="File content is empty")

        # Basic XML validation (check for XML tags)
        file_content_str = file_content.decode("utf-8", errors="ignore")
        if not file_content_str.strip().startswith("<"):
            logger.warning("File does not appear to be XML format")

        logger.info(f"Received file upload: {filename}, size: {len(file_content)} bytes")

        # Call service function
        return await update_wazuh_rule_file(
            filename=filename,
            file_content=file_content,
            pretty=pretty,
            wait_for_complete=wait_for_complete,
            overwrite=overwrite,
            relative_dirname=relative_dirname,
        )

    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid file encoding. File must be UTF-8 encoded XML.")
    except Exception as e:
        logger.error(f"Error processing file upload for {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing file upload: {str(e)}")

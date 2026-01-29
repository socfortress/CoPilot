from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.incidents.middleware.tag_access import tag_access_handler
from app.incidents.schema.db_operations import AlertTagItem
from app.incidents.schema.db_operations import AllTagsResponse
from app.incidents.schema.db_operations import RoleTagAccessResponse
from app.incidents.schema.db_operations import TagAccessCreate
from app.incidents.schema.db_operations import TagAccessSettingsItem
from app.incidents.schema.db_operations import TagAccessSettingsResponse
from app.incidents.schema.db_operations import TagAccessSettingsUpdate
from app.incidents.schema.db_operations import UserEffectiveAccessResponse
from app.incidents.schema.db_operations import UserTagAccessResponse
from app.incidents.services import tag_access as tag_access_service

tag_access_router = APIRouter()


def _require_admin(current_user: User) -> User:
    """Verify user has admin role."""
    from app.auth.models.users import RoleEnum

    if current_user.role_id != RoleEnum.admin.value:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def _tags_to_response(tags) -> List[AlertTagItem]:
    """Convert AlertTag objects to response items."""
    return [AlertTagItem(id=t.id, tag=t.tag) for t in tags]


# ============================================
# Settings Endpoints
# ============================================


@tag_access_router.get(
    "/settings",
    response_model=TagAccessSettingsResponse,
    description="Get current tag access settings (admin only)",
)
async def get_tag_access_settings(
    current_user: User = Security(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current tag access settings."""
    _require_admin(current_user)

    settings = await tag_access_service.get_or_create_tag_settings(db)

    # Get default tag name if set
    default_tag_name = None
    if settings.default_tag_id:
        tag = await tag_access_service.get_tag_by_id(settings.default_tag_id, db)
        if tag:
            default_tag_name = tag.tag

    return TagAccessSettingsResponse(
        settings=TagAccessSettingsItem(
            enabled=settings.enabled,
            untagged_alert_behavior=settings.untagged_alert_behavior,
            default_tag_id=settings.default_tag_id,
            default_tag_name=default_tag_name,
        ),
        success=True,
        message="Settings retrieved successfully",
    )


@tag_access_router.put(
    "/settings",
    response_model=TagAccessSettingsResponse,
    description="Update tag access settings (admin only)",
)
async def update_tag_access_settings(
    request: TagAccessSettingsUpdate,
    current_user: User = Security(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update tag access settings."""
    _require_admin(current_user)

    # Validate default_tag_id exists if specified
    if request.default_tag_id:
        tag = await tag_access_service.get_tag_by_id(request.default_tag_id, db)
        if not tag:
            raise HTTPException(
                status_code=404,
                detail=f"Tag with id {request.default_tag_id} not found",
            )

    settings = await tag_access_service.update_tag_access_settings(
        enabled=request.enabled,
        untagged_alert_behavior=request.untagged_alert_behavior.value,
        default_tag_id=request.default_tag_id,
        updated_by=current_user.username,
        db=db,
    )

    # Get default tag name if set
    default_tag_name = None
    if settings.default_tag_id:
        tag = await tag_access_service.get_tag_by_id(settings.default_tag_id, db)
        if tag:
            default_tag_name = tag.tag

    logger.info(f"Admin {current_user.username} updated tag access settings")

    # Return with settings nested under 'settings' key to match schema
    return TagAccessSettingsResponse(
        settings=TagAccessSettingsItem(
            enabled=settings.enabled,
            untagged_alert_behavior=settings.untagged_alert_behavior,
            default_tag_id=settings.default_tag_id,
            default_tag_name=default_tag_name,
        ),
        success=True,
        message="Settings updated successfully",
    )


# ============================================
# Tag List Endpoints
# ============================================


@tag_access_router.get(
    "/tags",
    response_model=AllTagsResponse,
    description="List all available tags",
)
async def list_all_tags(
    current_user: User = Security(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all available tags."""
    tags = await tag_access_service.get_all_tags(db)

    return AllTagsResponse(
        tags=_tags_to_response(tags),
        success=True,
        message=f"Retrieved {len(tags)} tags",
    )


# ============================================
# User Tag Access Endpoints
# ============================================


@tag_access_router.get(
    "/user/{user_id}",
    response_model=UserTagAccessResponse,
    description="Get tags assigned to a specific user (admin only)",
)
async def get_user_tag_access(
    user_id: int,
    current_user: User = Security(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get tags assigned to a specific user."""
    _require_admin(current_user)

    user = await tag_access_service.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tags = await tag_access_service.get_user_accessible_tags(user_id, db)

    return UserTagAccessResponse(
        user_id=user_id,
        username=user.username,
        accessible_tags=_tags_to_response(tags),
        success=True,
        message="User tag access retrieved successfully",
    )


@tag_access_router.put(
    "/user/{user_id}",
    response_model=UserTagAccessResponse,
    description="Set tags for a user - replaces existing (admin only)",
)
async def set_user_tag_access(
    user_id: int,
    request: TagAccessCreate,
    current_user: User = Security(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set tags for a user (replaces existing)."""
    _require_admin(current_user)

    user = await tag_access_service.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate all tag IDs exist
    for tag_id in request.tag_ids:
        tag = await tag_access_service.get_tag_by_id(tag_id, db)
        if not tag:
            raise HTTPException(
                status_code=404,
                detail=f"Tag with id {tag_id} not found",
            )

    tags = await tag_access_service.set_user_tag_access(user_id, request.tag_ids, db)

    logger.info(
        f"Admin {current_user.username} set tag access for user {user.username}: {request.tag_ids}",
    )

    return UserTagAccessResponse(
        user_id=user_id,
        username=user.username,
        accessible_tags=_tags_to_response(tags),
        success=True,
        message="User tag access updated successfully",
    )


@tag_access_router.post(
    "/user/{user_id}/add",
    response_model=UserTagAccessResponse,
    description="Add tags to a user's access (admin only)",
)
async def add_user_tag_access(
    user_id: int,
    request: TagAccessCreate,
    current_user: User = Security(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add tags to a user's access without removing existing."""
    _require_admin(current_user)

    user = await tag_access_service.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate all tag IDs exist
    for tag_id in request.tag_ids:
        tag = await tag_access_service.get_tag_by_id(tag_id, db)
        if not tag:
            raise HTTPException(
                status_code=404,
                detail=f"Tag with id {tag_id} not found",
            )

    tags = await tag_access_service.add_user_tag_access(user_id, request.tag_ids, db)

    logger.info(
        f"Admin {current_user.username} added tag access for user {user.username}: {request.tag_ids}",
    )

    return UserTagAccessResponse(
        user_id=user_id,
        username=user.username,
        accessible_tags=_tags_to_response(tags),
        success=True,
        message="Tags added to user access successfully",
    )


@tag_access_router.post(
    "/user/{user_id}/remove",
    response_model=UserTagAccessResponse,
    description="Remove tags from a user's access (admin only)",
)
async def remove_user_tag_access(
    user_id: int,
    request: TagAccessCreate,
    current_user: User = Security(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove specific tags from a user's access."""
    _require_admin(current_user)

    user = await tag_access_service.get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tags = await tag_access_service.remove_user_tag_access(user_id, request.tag_ids, db)

    logger.info(
        f"Admin {current_user.username} removed tag access for user {user.username}: {request.tag_ids}",
    )

    return UserTagAccessResponse(
        user_id=user_id,
        username=user.username,
        accessible_tags=_tags_to_response(tags),
        success=True,
        message="Tags removed from user access successfully",
    )


# ============================================
# Role Tag Access Endpoints
# ============================================


@tag_access_router.get(
    "/role/{role_id}",
    response_model=RoleTagAccessResponse,
    description="Get tags assigned to a specific role (admin only)",
)
async def get_role_tag_access(
    role_id: int,
    current_user: User = Security(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get tags assigned to a specific role."""
    _require_admin(current_user)

    role = await tag_access_service.get_role_by_id(role_id, db)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    tags = await tag_access_service.get_role_accessible_tags(role_id, db)

    return RoleTagAccessResponse(
        role_id=role_id,
        role_name=role.name,
        accessible_tags=_tags_to_response(tags),
        success=True,
        message="Role tag access retrieved successfully",
    )


@tag_access_router.put(
    "/role/{role_id}",
    response_model=RoleTagAccessResponse,
    description="Set tags for a role - replaces existing (admin only)",
)
async def set_role_tag_access(
    role_id: int,
    request: TagAccessCreate,
    current_user: User = Security(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set tags for a role (replaces existing)."""
    _require_admin(current_user)

    role = await tag_access_service.get_role_by_id(role_id, db)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Validate all tag IDs exist
    for tag_id in request.tag_ids:
        tag = await tag_access_service.get_tag_by_id(tag_id, db)
        if not tag:
            raise HTTPException(
                status_code=404,
                detail=f"Tag with id {tag_id} not found",
            )

    tags = await tag_access_service.set_role_tag_access(role_id, request.tag_ids, db)

    logger.info(
        f"Admin {current_user.username} set tag access for role {role.name}: {request.tag_ids}",
    )

    return RoleTagAccessResponse(
        role_id=role_id,
        role_name=role.name,
        accessible_tags=_tags_to_response(tags),
        success=True,
        message="Role tag access updated successfully",
    )


@tag_access_router.post(
    "/role/{role_id}/add",
    response_model=RoleTagAccessResponse,
    description="Add tags to a role's access (admin only)",
)
async def add_role_tag_access(
    role_id: int,
    request: TagAccessCreate,
    current_user: User = Security(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add tags to a role's access without removing existing."""
    _require_admin(current_user)

    role = await tag_access_service.get_role_by_id(role_id, db)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Validate all tag IDs exist
    for tag_id in request.tag_ids:
        tag = await tag_access_service.get_tag_by_id(tag_id, db)
        if not tag:
            raise HTTPException(
                status_code=404,
                detail=f"Tag with id {tag_id} not found",
            )

    tags = await tag_access_service.add_role_tag_access(role_id, request.tag_ids, db)

    logger.info(
        f"Admin {current_user.username} added tag access for role {role.name}: {request.tag_ids}",
    )

    return RoleTagAccessResponse(
        role_id=role_id,
        role_name=role.name,
        accessible_tags=_tags_to_response(tags),
        success=True,
        message="Tags added to role access successfully",
    )


@tag_access_router.post(
    "/role/{role_id}/remove",
    response_model=RoleTagAccessResponse,
    description="Remove tags from a role's access (admin only)",
)
async def remove_role_tag_access(
    role_id: int,
    request: TagAccessCreate,
    current_user: User = Security(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove specific tags from a role's access."""
    _require_admin(current_user)

    role = await tag_access_service.get_role_by_id(role_id, db)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    tags = await tag_access_service.remove_role_tag_access(role_id, request.tag_ids, db)

    logger.info(
        f"Admin {current_user.username} removed tag access for role {role.name}: {request.tag_ids}",
    )

    return RoleTagAccessResponse(
        role_id=role_id,
        role_name=role.name,
        accessible_tags=_tags_to_response(tags),
        success=True,
        message="Tags removed from role access successfully",
    )


# ============================================
# Current User Effective Access
# ============================================


@tag_access_router.get(
    "/me",
    response_model=UserEffectiveAccessResponse,
    description="Get current user's effective access (customer + tags)",
)
async def get_my_effective_access(
    current_user: User = Security(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's effective access (combines role + user-specific)."""
    # Get tag RBAC status
    tag_rbac_enabled = await tag_access_handler.is_tag_rbac_enabled(db)

    # Get accessible tags
    accessible_tag_ids = await tag_access_handler.get_user_accessible_tags(current_user, db)
    is_unrestricted = "*" in accessible_tag_ids

    if is_unrestricted:
        # User has unrestricted access - show all tags
        all_tags = await tag_access_service.get_all_tags(db)
        tag_list = _tags_to_response(all_tags)
    else:
        # Get specific tags user can access
        from sqlalchemy import select

        from app.incidents.models import AlertTag

        if accessible_tag_ids:
            result = await db.execute(
                select(AlertTag).where(AlertTag.id.in_(accessible_tag_ids)),
            )
            tags = result.scalars().all()
            tag_list = _tags_to_response(tags)
        else:
            tag_list = []

    # Get customer access (using existing middleware if available)
    try:
        from app.middleware.customer_access import customer_access_handler

        accessible_customers = await customer_access_handler.get_user_accessible_customers(
            current_user,
            db,
        )
        customer_list = list(accessible_customers) if "*" not in accessible_customers else ["*"]
    except ImportError:
        customer_list = ["*"]  # Fallback if customer access handler doesn't exist

    # Get role name
    role_name = None
    if current_user.role_id:
        role = await tag_access_service.get_role_by_id(current_user.role_id, db)
        if role:
            role_name = role.name

    return UserEffectiveAccessResponse(
        user_id=current_user.id,
        username=current_user.username,
        role_id=current_user.role_id,
        role_name=role_name,
        accessible_customers=customer_list,
        accessible_tags=tag_list,
        is_tag_unrestricted=is_unrestricted,
        tag_rbac_enabled=tag_rbac_enabled,
        success=True,
        message="Effective access retrieved successfully",
    )

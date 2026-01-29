from datetime import datetime
from typing import List
from typing import Optional

from loguru import logger
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import Role
from app.auth.models.users import RoleTagAccess
from app.auth.models.users import User
from app.auth.models.users import UserTagAccess
from app.incidents.models import AlertTag
from app.incidents.models import TagAccessSettings

# ============================================
# Tag Access Settings
# ============================================


async def get_or_create_tag_settings(db: AsyncSession) -> TagAccessSettings:
    """Get existing settings or create default ones."""
    result = await db.execute(select(TagAccessSettings).limit(1))
    settings = result.scalars().first()

    if settings is None:
        settings = TagAccessSettings(
            enabled=False,
            untagged_alert_behavior="visible_to_all",
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        logger.info("Created default tag access settings")

    return settings


async def get_tag_access_settings(db: AsyncSession) -> Optional[TagAccessSettings]:
    """Get the global tag access settings, or None if not configured."""
    result = await db.execute(select(TagAccessSettings).limit(1))
    return result.scalars().first()


async def update_tag_access_settings(
    enabled: bool,
    untagged_alert_behavior: str,
    default_tag_id: Optional[int],
    updated_by: str,
    db: AsyncSession,
) -> TagAccessSettings:
    """Update global tag access settings."""
    settings = await get_or_create_tag_settings(db)

    settings.enabled = enabled
    settings.untagged_alert_behavior = untagged_alert_behavior
    settings.default_tag_id = default_tag_id
    settings.updated_by = updated_by
    settings.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(settings)

    logger.info(
        f"Tag access settings updated by {updated_by}: "
        f"enabled={enabled}, behavior={untagged_alert_behavior}, default_tag_id={default_tag_id}",
    )
    return settings


# ============================================
# User Tag Access
# ============================================


async def get_user_accessible_tags(user_id: int, db: AsyncSession) -> List[AlertTag]:
    """Get all tags a user has direct access to (not including role-based)."""
    result = await db.execute(
        select(AlertTag).join(UserTagAccess, UserTagAccess.tag_id == AlertTag.id).where(UserTagAccess.user_id == user_id),
    )
    return list(result.scalars().all())


async def set_user_tag_access(
    user_id: int,
    tag_ids: List[int],
    db: AsyncSession,
) -> List[AlertTag]:
    """
    Set the tags a user can access (replaces existing).

    Args:
        user_id: The user ID
        tag_ids: List of tag IDs to grant access to
        db: Database session

    Returns:
        List of AlertTag objects the user now has access to
    """
    # Remove existing access
    await db.execute(
        delete(UserTagAccess).where(UserTagAccess.user_id == user_id),
    )

    # Add new access
    for tag_id in tag_ids:
        access = UserTagAccess(user_id=user_id, tag_id=tag_id)
        db.add(access)

    await db.commit()

    logger.info(f"Set tag access for user {user_id}: {tag_ids}")

    # Return the tags
    if tag_ids:
        result = await db.execute(
            select(AlertTag).where(AlertTag.id.in_(tag_ids)),
        )
        return list(result.scalars().all())
    return []


async def add_user_tag_access(
    user_id: int,
    tag_ids: List[int],
    db: AsyncSession,
) -> List[AlertTag]:
    """Add tags to a user's access (doesn't remove existing)."""
    for tag_id in tag_ids:
        # Check if already exists
        result = await db.execute(
            select(UserTagAccess).where(
                UserTagAccess.user_id == user_id,
                UserTagAccess.tag_id == tag_id,
            ),
        )
        if result.scalars().first() is None:
            access = UserTagAccess(user_id=user_id, tag_id=tag_id)
            db.add(access)

    await db.commit()

    logger.info(f"Added tag access for user {user_id}: {tag_ids}")
    return await get_user_accessible_tags(user_id, db)


async def remove_user_tag_access(
    user_id: int,
    tag_ids: List[int],
    db: AsyncSession,
) -> List[AlertTag]:
    """Remove specific tags from a user's access."""
    await db.execute(
        delete(UserTagAccess).where(
            UserTagAccess.user_id == user_id,
            UserTagAccess.tag_id.in_(tag_ids),
        ),
    )
    await db.commit()

    logger.info(f"Removed tag access for user {user_id}: {tag_ids}")
    return await get_user_accessible_tags(user_id, db)


# ============================================
# Role Tag Access
# ============================================


async def get_role_accessible_tags(role_id: int, db: AsyncSession) -> List[AlertTag]:
    """Get all tags a role has access to."""
    result = await db.execute(
        select(AlertTag).join(RoleTagAccess, RoleTagAccess.tag_id == AlertTag.id).where(RoleTagAccess.role_id == role_id),
    )
    return list(result.scalars().all())


async def set_role_tag_access(
    role_id: int,
    tag_ids: List[int],
    db: AsyncSession,
) -> List[AlertTag]:
    """Set the tags a role can access (replaces existing)."""
    # Remove existing access
    await db.execute(
        delete(RoleTagAccess).where(RoleTagAccess.role_id == role_id),
    )

    # Add new access
    for tag_id in tag_ids:
        access = RoleTagAccess(role_id=role_id, tag_id=tag_id)
        db.add(access)

    await db.commit()

    logger.info(f"Set tag access for role {role_id}: {tag_ids}")

    # Return the tags
    if tag_ids:
        result = await db.execute(
            select(AlertTag).where(AlertTag.id.in_(tag_ids)),
        )
        return list(result.scalars().all())
    return []


async def add_role_tag_access(
    role_id: int,
    tag_ids: List[int],
    db: AsyncSession,
) -> List[AlertTag]:
    """Add tags to a role's access (doesn't remove existing)."""
    for tag_id in tag_ids:
        # Check if already exists
        result = await db.execute(
            select(RoleTagAccess).where(
                RoleTagAccess.role_id == role_id,
                RoleTagAccess.tag_id == tag_id,
            ),
        )
        if result.scalars().first() is None:
            access = RoleTagAccess(role_id=role_id, tag_id=tag_id)
            db.add(access)

    await db.commit()

    logger.info(f"Added tag access for role {role_id}: {tag_ids}")
    return await get_role_accessible_tags(role_id, db)


async def remove_role_tag_access(
    role_id: int,
    tag_ids: List[int],
    db: AsyncSession,
) -> List[AlertTag]:
    """Remove specific tags from a role's access."""
    await db.execute(
        delete(RoleTagAccess).where(
            RoleTagAccess.role_id == role_id,
            RoleTagAccess.tag_id.in_(tag_ids),
        ),
    )
    await db.commit()

    logger.info(f"Removed tag access for role {role_id}: {tag_ids}")
    return await get_role_accessible_tags(role_id, db)


# ============================================
# Tag Queries
# ============================================


async def get_all_tags(db: AsyncSession) -> List[AlertTag]:
    """Get all available tags."""
    result = await db.execute(select(AlertTag))
    return list(result.scalars().all())


async def get_tag_by_id(tag_id: int, db: AsyncSession) -> Optional[AlertTag]:
    """Get a tag by ID."""
    result = await db.execute(
        select(AlertTag).where(AlertTag.id == tag_id),
    )
    return result.scalars().first()


# ============================================
# User Queries (helpers)
# ============================================


async def get_user_by_id(user_id: int, db: AsyncSession) -> Optional[User]:
    """Get a user by ID."""
    result = await db.execute(
        select(User).where(User.id == user_id),
    )
    return result.scalars().first()


async def get_role_by_id(role_id: int, db: AsyncSession) -> Optional[Role]:
    """Get a role by ID."""
    result = await db.execute(
        select(Role).where(Role.id == role_id),
    )
    return result.scalars().first()


async def get_all_roles(db: AsyncSession) -> List[Role]:
    """Get all roles."""
    result = await db.execute(select(Role))
    return list(result.scalars().all())

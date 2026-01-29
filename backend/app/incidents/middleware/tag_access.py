from typing import Any
from typing import Dict
from typing import Set
from typing import Union

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import RoleEnum
from app.auth.models.users import RoleTagAccess
from app.auth.models.users import User
from app.auth.models.users import UserTagAccess
from app.incidents.models import Alert
from app.incidents.models import AlertToTag
from app.incidents.models import TagAccessSettings


class TagAccessHandler:
    """
    Handles tag-based access control for alerts.

    This works alongside customer_access_handler to provide multi-dimensional
    access control:
    - Customer access: Which customers' data can the user see?
    - Tag access: Which tagged alerts can the user see?

    Both filters are applied (AND logic) when tag RBAC is enabled.
    """

    # Roles that bypass tag restrictions (full access)
    UNRESTRICTED_ROLES = {RoleEnum.admin.value, RoleEnum.scheduler.value}

    async def is_tag_rbac_enabled(self, db: AsyncSession) -> bool:
        """Check if tag-based RBAC is enabled globally."""
        result = await db.execute(select(TagAccessSettings).limit(1))
        settings = result.scalars().first()

        if settings is None:
            # No settings configured = disabled (backward compatible)
            return False

        return settings.enabled

    async def get_tag_access_settings(self, db: AsyncSession) -> TagAccessSettings:
        """Get the global tag access settings, or None if not configured."""
        result = await db.execute(select(TagAccessSettings).limit(1))
        return result.scalars().first()

    async def get_user_accessible_tags(self, user: User, db: AsyncSession) -> Set[Union[int, str]]:
        """
        Get the set of tag IDs a user can access.

        Returns:
            Set of tag IDs, or {"*"} for unrestricted access
        """
        # Check if tag RBAC is even enabled
        if not await self.is_tag_rbac_enabled(db):
            return {"*"}  # Tag RBAC disabled = no filtering

        # Admin and scheduler roles bypass tag restrictions
        if user.role_id in self.UNRESTRICTED_ROLES:
            logger.debug(f"User {user.username} has unrestricted role, bypassing tag RBAC")
            return {"*"}

        accessible_tags: Set[int] = set()

        # Get user-specific tag access
        user_tags_result = await db.execute(select(UserTagAccess.tag_id).where(UserTagAccess.user_id == user.id))
        user_tags = {row[0] for row in user_tags_result}
        accessible_tags.update(user_tags)

        # Get role-based tag access
        if user.role_id:
            role_tags_result = await db.execute(select(RoleTagAccess.tag_id).where(RoleTagAccess.role_id == user.role_id))
            role_tags = {row[0] for row in role_tags_result}
            accessible_tags.update(role_tags)

        logger.debug(f"User {user.username} has access to tags: {accessible_tags}")
        return accessible_tags

    async def can_user_access_alert(self, user: User, alert_id: int, db: AsyncSession) -> bool:
        """
        Check if a user can access a specific alert based on tags.

        This should be called AFTER customer access is verified.
        """
        # Check if tag RBAC is enabled
        if not await self.is_tag_rbac_enabled(db):
            return True  # Tag RBAC disabled

        # Admin/scheduler bypass
        if user.role_id in self.UNRESTRICTED_ROLES:
            return True

        # Get the alert's tags
        alert_tag_ids = await self._get_alert_tag_ids(alert_id, db)

        # Handle untagged alerts
        if not alert_tag_ids:
            return await self._can_access_untagged_alert(user, db)

        # Get user's accessible tags
        accessible_tags = await self.get_user_accessible_tags(user, db)

        if "*" in accessible_tags:
            return True

        # User can access if they have access to ANY of the alert's tags
        return bool(alert_tag_ids & accessible_tags)

    async def _get_alert_tag_ids(self, alert_id: int, db: AsyncSession) -> Set[int]:
        """Get all tag IDs for an alert."""
        result = await db.execute(select(AlertToTag.tag_id).where(AlertToTag.alert_id == alert_id))
        return {row[0] for row in result}

    async def _can_access_untagged_alert(self, user: User, db: AsyncSession) -> bool:
        """
        Determine if user can access an untagged alert based on settings.
        """
        settings = await self.get_tag_access_settings(db)

        if settings is None:
            return True  # No settings = visible to all

        behavior = settings.untagged_alert_behavior

        if behavior == "visible_to_all":
            return True
        elif behavior == "admin_only":
            return user.role_id in self.UNRESTRICTED_ROLES
        elif behavior == "default_tag":
            # Check if user has access to the default tag
            if settings.default_tag_id is None:
                return True  # No default tag configured
            accessible_tags = await self.get_user_accessible_tags(user, db)
            if "*" in accessible_tags:
                return True
            return settings.default_tag_id in accessible_tags

        return True  # Unknown behavior = allow

    def build_tag_filter_subquery(self, accessible_tags: Set[Union[int, str]]):
        """
        Build a SQLAlchemy subquery for tag-based filtering.

        Returns a subquery that can be used with .where(Alert.id.in_(subquery))
        """
        if "*" in accessible_tags:
            return None  # No filter needed

        if not accessible_tags:
            # User has no tag access - return subquery that matches nothing
            return select(Alert.id).where(Alert.id == -1)

        # Subquery: alert IDs that have at least one accessible tag
        return select(AlertToTag.alert_id).where(AlertToTag.tag_id.in_(accessible_tags)).distinct()

    async def check_alert_tag_access(
        self,
        user: User,
        alert: Any,  # Alert or AlertOut object
        session: AsyncSession,
    ) -> bool:
        """
        Check if a user has tag-based access to a specific alert.

        Args:
            user: The user to check access for
            alert: The alert object (must have 'tags' attribute)
            session: Database session

        Returns:
            True if user has access, False otherwise
        """
        # Get user's tag filters
        tag_filters = await self.build_alert_query_filters(user, session)
        accessible_tags = tag_filters["accessible_tags"]

        # If user has wildcard access, allow everything
        if "*" in accessible_tags:
            return True

        # Get alert's tag IDs
        alert_tag_ids = set()
        if hasattr(alert, "tags") and alert.tags:
            for tag_item in alert.tags:
                # Handle both AlertToTag objects and AlertTagBase objects
                if hasattr(tag_item, "tag_id"):
                    alert_tag_ids.add(tag_item.tag_id)
                elif hasattr(tag_item, "id"):
                    alert_tag_ids.add(tag_item.id)

        # Check if alert is untagged
        is_untagged = len(alert_tag_ids) == 0

        # If alert is untagged, check if untagged alerts are allowed
        if is_untagged:
            return tag_filters["include_untagged"]

        # Check if user has access to any of the alert's tags
        if accessible_tags:
            accessible_tag_ids = set(accessible_tags)
            if alert_tag_ids & accessible_tag_ids:  # Intersection
                return True

        return False

    async def build_alert_query_filters(
        self,
        user: User,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Build query filters for alert access based on user's tag permissions.

        Returns a dict with:
        - accessible_tags: Set of tag IDs the user can access (or {"*"} for all)
        - include_untagged: Whether to include alerts without tags
        - default_tag_id: If set, untagged alerts are treated as having this tag
        """
        # Check if tag RBAC is enabled
        if not await self.is_tag_rbac_enabled(db):
            return {"accessible_tags": {"*"}, "include_untagged": True, "default_tag_id": None}

        # Admins and schedulers have full access
        if user.role_id in [RoleEnum.admin.value, RoleEnum.scheduler.value]:
            return {"accessible_tags": {"*"}, "include_untagged": True, "default_tag_id": None}

        # Get user's accessible tags
        accessible_tags = await self.get_user_accessible_tags(user, db)

        # If user has wildcard access, they can see everything
        if "*" in accessible_tags:
            return {"accessible_tags": {"*"}, "include_untagged": True, "default_tag_id": None}

        # Get settings for untagged alert behavior
        settings = await self.get_tag_access_settings(db)  # Changed from _get_settings
        include_untagged = False
        default_tag_id = None

        if settings:
            if settings.untagged_alert_behavior == "visible_to_all":
                include_untagged = True
            elif settings.untagged_alert_behavior == "admin_only":
                include_untagged = False
            elif settings.untagged_alert_behavior == "default_tag":
                # If user has access to the default tag, they can see untagged alerts
                default_tag_id = settings.default_tag_id
                if default_tag_id and default_tag_id in accessible_tags:
                    include_untagged = True
                else:
                    include_untagged = False

        return {
            "accessible_tags": accessible_tags,
            "include_untagged": include_untagged,
            "default_tag_id": default_tag_id,
        }


# Singleton instance
tag_access_handler = TagAccessHandler()

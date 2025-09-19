from typing import List
from fastapi import HTTPException
from loguru import logger

# ! New with Async
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload
from sqlmodel import select

from app.auth.models.users import Password
from app.auth.models.users import Role
from app.auth.models.users import User
from app.db.db_session import async_engine

passwords_in_memory = {}


def select_all_users_sync(session: Session) -> List[User]:
    """
    Retrieves all Users from the database with their role information.

    Args:
        session: The database session to use for the query.

    Returns:
        List[User]: A list of all Users in the database with role information loaded.
    """
    result = session.exec(select(User).options(selectinload(User.role)))
    return result.all()


async def select_all_users():
    """
    Async version: Retrieves all Users from the database with their role information.

    Returns:
        List[User]: A list of all Users in the database with role information loaded.
    """
    async with AsyncSession(async_engine) as session:
        statement = select(User).options(selectinload(User.role))
        result = await session.execute(statement)
        return result.scalars().all()


async def find_user(name: str):
    """
    Find a user by their username.

    Args:
        name (str): The username of the user to find.

    Returns:
        User: The user object if found, None otherwise.
    """
    try:
        async with AsyncSession(async_engine) as session:
            statement = select(User).where(User.username == name)
            result = await session.execute(statement)
            return result.scalars().first()
    except Exception as e:
        logger.error(f"Error: {e}")
        return None


async def get_role(name: str):
    """
    Retrieve the role name for a given user name.

    Args:
        name (str): The name of the user.

    Returns:
        str: The name of the user's role.
    """
    async with AsyncSession(async_engine) as session:
        user = await find_user(name)
        if user:
            statement = select(Role).where(Role.id == user.role_id)
            result = await session.execute(statement)
            role = result.scalars().first()
            return role.name


async def check_admin_user_exists(session: AsyncSession) -> bool:
    """
    Check if admin user exists in the database
    If not, return False

    :param session: The database session
    :type session: AsyncSession
    :return: True if admin user exists, False otherwise
    :rtype: bool
    """
    statement = select(User).where(User.username == "admin")
    result = await session.execute(statement)
    user = result.scalars().first()
    return user is not None


async def check_scheduler_user_exists(session: AsyncSession) -> bool:
    """
    Check if scheduler user exists in the database
    If not, return False

    :param session: The database session to use for the query
    :type session: AsyncSession
    :return: True if the scheduler user exists, False otherwise
    :rtype: bool
    """
    statement = select(User).where(User.username == "scheduler")
    result = await session.execute(statement)
    user = result.scalars().first()
    return user is not None


async def create_admin_user(session: AsyncSession):
    """
    Check if the admin user exists in the database.
    If not, create the admin user.

    Parameters:
    - session: The database session to use for querying and committing changes.

    Returns:
    - None
    """
    if not await check_admin_user_exists(
        session,
    ):  # The check function needs to be passed the session as well
        # Create the admin user
        password_model = Password.generate(length=24)
        admin_user = User(
            username="admin",
            password=password_model.hashed,  # Assuming you store the hashed password
            email="admin@admin.com",
            role_id=1,  # Make sure the role_id corresponds to the admin role in your DB
        )
        session.add(admin_user)
        admin_username = admin_user.username
        await session.commit()
        logger.info(f"Added new admin user with username: {admin_username}")
        logger.info(f"Admin user password: {password_model}")
    else:
        logger.info("Admin user already exists.")
    return


async def create_scheduler_user(session: AsyncSession):
    """
    Check if the scheduler user exists in the database.
    If not, create the scheduler user.

    Parameters:
    - session: The database session to use for querying and committing changes.

    Returns:
    - None
    """
    if not await check_scheduler_user_exists(
        session,
    ):  # The check function needs to be passed the session as well
        # Create the scheduler user
        password_model = Password.generate(length=12)
        scheduler_user = User(
            username="scheduler",
            password=password_model.hashed,  # Assuming you store the hashed password
            email="scheduler@scheduler.com",
            role_id=3,  # Make sure the role_id corresponds to the scheduler role in your DB
        )
        session.add(scheduler_user)
        scheduler_username = scheduler_user.username
        password_plain = password_model.plain
        await session.commit()
        logger.info(f"Added new scheduler user with username: {scheduler_username}")
        logger.info(f"Scheduler user password: {password_plain}")
        passwords_in_memory["scheduler"] = password_plain
    else:
        logger.info("Scheduler user already exists.")
    return


async def remove_scheduler_user(session: AsyncSession):
    """
    Check if the scheduler user exists in the database.
    If so, remove the scheduler user.

    Args:
        session (AsyncSession): The async session object used for database operations.

    Returns:
        None
    """
    # Check if the scheduler user exists
    statement = select(User).where(User.username == "scheduler")
    result = await session.execute(statement)
    scheduler_user = result.scalars().first()

    if scheduler_user:
        # Remove the scheduler user
        await session.delete(scheduler_user)
        await session.commit()  # This is awaited because commit is async
        logger.info("Scheduler user removed.")
    else:
        logger.info("Scheduler user does not exist.")


def get_scheduler_password():
    """
    Retrieve the scheduler user's unhashed password from memory.

    Returns:
        str: The unhashed password of the scheduler user.
    """
    return passwords_in_memory.get("scheduler")


async def delete_user(user_id: int, session: AsyncSession):
    """
    Delete a user from the database.

    Args:
        user_id (int): The ID of the user to delete.
        session (AsyncSession): The database session to use for the operation.

    Returns:
        None
    """
    # First check if user exists
    statement = select(User).where(User.id == user_id)
    result = await session.execute(statement)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.id == 1:
        raise HTTPException(status_code=403, detail="Cannot delete admin user")

    # Database operations in try block
    try:
        await session.delete(user)
        await session.commit()
        logger.info(f"User with ID {user_id} deleted.")
    except Exception as e:
        await session.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting user")

    return {"message": "User deleted successfully.", "success": True}

from loguru import logger

# ! New with Async
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth.models.users import Password
from app.auth.models.users import Role
from fastapi import HTTPException
from app.auth.models.users import User
from app.db.db_session import async_engine
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

passwords_in_memory = {}


async def select_all_users():
    """
    Retrieves all users from the database.

    Returns:
        List[User]: A list of User objects representing all the users in the database.
    """
    async with AsyncSession(async_engine) as session:
        statement = select(User)
        results = await session.execute(statement)
        return results.scalars().all()


async def find_user(name: str):
    """
    Find a user by their username.

    Args:
        name (str): The username of the user to find.

    Returns:
        User: The user object if found, None otherwise.
    """
    async with AsyncSession(async_engine) as session:
        statement = select(User).where(User.username == name)
        result = await session.execute(statement)
        return result.scalars().first()


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
    if not await check_admin_user_exists(session):  # The check function needs to be passed the session as well
        # Create the admin user
        password_model = Password.generate(length=12)
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
    if not await check_scheduler_user_exists(session):  # The check function needs to be passed the session as well
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

# ! TODO: Password Reset Token Generation ! #
# def get_reset_token(user, expires_sec=1800):
#     """
#     Generate a password reset token for the given user.

#     Args:
#         user (User): The user to generate the token for.
#         expires_sec (int, optional): The number of seconds the token will be valid for.
#             Defaults to 1800.

#     Returns:
#         str: The generated token.
#     """
#     s = Serializer(user.password, expires_sec)
#     return s.dumps({"user_id": user.id}).decode("utf-8")

# async def reset_password(token, new_password):
#     """
#     Reset the password for the user associated with the given token.

#     Args:
#         token (str): The token associated with the user.
#         new_password (str): The new password to set for the user.

#     Returns:
#         bool: True if the password was reset, False otherwise.
#     """
#     s = Serializer(secret)
#     try:
#         username = s.loads(token)['username']
#     except:
#         raise HTTPException(
#             status_code=401,
#             detail="Invalid or expired reset token",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     user = await find_user(username)
#     if user is None:
#         return False

#     hashed_password = self.get_password_hash(new_password)
#     # Here you would need to implement a method to update the user's password in your database
#     await update_user_password(username, hashed_password)

#     return True

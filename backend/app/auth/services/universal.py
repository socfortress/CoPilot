import asyncio
import random
import string

from loguru import logger

# ! New with Async
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session
from sqlmodel import select

from app.auth.models.users import Password
from app.auth.models.users import Role
from app.auth.models.users import User
from app.db.db_session import async_engine

passwords_in_memory = {}

# def select_all_users():
#     with Session(engine) as session:
#         statement = select(User)
#         res = session.exec(statement).all()
#         return res


# def find_user(name):
#     with Session(engine) as session:
#         statement = select(User).where(User.username == name)
#         return session.exec(statement).first()


# def get_role(name):
#     with Session(engine) as session:
#         statement = select(User).where(User.username == name)
#         res = session.exec(statement).first()
#         # Get the role name
#         statement = select(Role).where(Role.id == res.role_id)
#         role = session.exec(statement).first()
#         return role.name


async def select_all_users():
    async with AsyncSession(async_engine) as session:
        statement = select(User)
        results = await session.execute(statement)
        return results.scalars().all()


async def find_user(name: str):
    async with AsyncSession(async_engine) as session:
        statement = select(User).where(User.username == name)
        result = await session.execute(statement)
        return result.scalars().first()


async def get_role(name: str):
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
    """
    statement = select(User).where(User.username == "admin")
    result = await session.execute(statement)
    user = result.scalars().first()
    return user is not None


async def check_scheduler_user_exists(session: AsyncSession) -> bool:
    """
    Check if scheduler user exists in the database
    If not, return False
    """
    statement = select(User).where(User.username == "scheduler")
    result = await session.execute(statement)
    user = result.scalars().first()
    return user is not None


async def create_admin_user(session: AsyncSession):
    """
    Check if the admin user exists in the database.
    If not, create the admin user.
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
    """
    return passwords_in_memory.get("scheduler")

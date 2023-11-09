from loguru import logger

# ! New with Async
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Session
from sqlmodel import select

from app.auth.models.users import Role
from app.auth.models.users import User
from app.db.db_session import async_engine

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

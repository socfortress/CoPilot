from sqlmodel import Session
from sqlmodel import select

from app.auth.models.users import User
from app.db.db_session import engine


def select_all_users():
    with Session(engine) as session:
        statement = select(User)
        res = session.exec(statement).all()
        return res


def find_user(name):
    with Session(engine) as session:
        statement = select(User).where(User.username == name)
        return session.exec(statement).first()

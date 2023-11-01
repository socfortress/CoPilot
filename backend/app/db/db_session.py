from sqlmodel import Session
from sqlmodel import create_engine

from settings import SQLALCHEMY_DATABASE_URI

engine = create_engine(SQLALCHEMY_DATABASE_URI, connect_args={"check_same_thread": False})
session = Session(bind=engine)

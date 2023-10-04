from sqlmodel import create_engine
from sqlmodel import Session
from settings import SQLALCHEMY_DATABASE_URI

engine = create_engine(SQLALCHEMY_DATABASE_URI)
session = Session(bind=engine)
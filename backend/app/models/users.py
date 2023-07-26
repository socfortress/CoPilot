from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from app import db
from app import ma

class Users(db.Model):
    """
    Class for users which stores various user details.
    This class inherits from SQLAlchemy's Model class.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    customerCode: Column[String] = db.Column(db.String(11), nullable=False)
    usersFirstName: Column[String] = db.Column(db.String(50))
    usersLastName: Column[String] = db.Column(db.String(50))
    usersEmail: Column[String] = db.Column(db.String(50))
    usersRole: Column[String] = db.Column(db.String(100))
    imageFile: Column[String] = db.Column(db.String(64))
    notifications: Column[Integer] = db.Column(db.SmallInteger, nullable=False)
    createdAt: Column[DateTime] = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, customerCode: str, notifications: int, usersFirstName: str = None,
                 usersLastName: str = None, usersEmail: str = None, usersRole: str = None,
                 imageFile: str = None, createdAt: datetime = None):
        """
        Initialize a new instance of the Users class.

        :param customerCode: The code of the customer.
        :param usersFirstName: The first name of the user.
        :param usersLastName: The last name of the user.
        :param usersEmail: The email of the user.
        :param usersRole: The role of the user.
        :param imageFile: The file name of the user's image.
        :param notifications: Whether the user has notifications enabled (1) or not (0).
        :param createdAt: The date the user was created.
        """
        self.customerCode = customerCode
        self.usersFirstName = usersFirstName
        self.usersLastName = usersLastName
        self.usersEmail = usersEmail
        self.usersRole = usersRole
        self.imageFile = imageFile
        self.notifications = notifications
        self.createdAt = createdAt

    def __repr__(self) -> str:
        """
        Returns a string representation of the Users instance.

        :return: A string representation of the usersEmail.
        """
        return f"<User {self.usersEmail}>"

class UsersSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the Users class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields = (
            "id",
            "customerCode",
            "usersFirstName",
            "usersLastName",
            "usersEmail",
            "usersRole",
            "imageFile",
            "notifications",
            "createdAt",
        )

users_schema: UsersSchema = UsersSchema()
users_schema: UsersSchema = UsersSchema(many=True)

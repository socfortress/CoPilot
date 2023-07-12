from datetime import datetime
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from app import db
from app import ma

# Path: backend\app\models.py
class EmailCredentials(db.Model):
    """
    Class for storing user email credentials and SMTP settings.
    This class inherits from SQLAlchemy's Model class.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    email: Column[String] = db.Column(db.String(100), nullable=False, unique=True)
    password: Column[String] = db.Column(db.String(100), nullable=False)
    smtp_server: Column[String] = db.Column(db.String(100), nullable=False)
    smtp_port: Column[Integer] = db.Column(db.Integer, nullable=False)
    timestamp: Column[DateTime] = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, email: str, password: str, smtp_server: str, smtp_port: int):
        """
        Initialize a new instance of the EmailCredentials class.

        :param email: The email of the user.
        :param password: The email password of the user.
        :param smtp_server: The SMTP server.
        :param smtp_port: The SMTP port.
        """
        self.email = email
        self.password = password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def __repr__(self) -> str:
        """
        Returns a string representation of the EmailCredentials instance.

        :return: A string representation of the email.
        """
        return f"<EmailCredentials {self.email}>"


class EmailCredentialsSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the EmailCredentials class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields: tuple = (
            "id",
            "email",
            "password",
            "smtp_server",
            "smtp_port",
            "timestamp",
        )


email_credentials_schema: EmailCredentialsSchema = EmailCredentialsSchema()
email_credentials_schemas: EmailCredentialsSchema = EmailCredentialsSchema(many=True)

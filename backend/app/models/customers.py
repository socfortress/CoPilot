from datetime import datetime

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from app import db
from app import ma


class Customers(db.Model):
    """
    Class for customers which stores various customer details.
    This class inherits from SQLAlchemy's Model class.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    customerCode: Column[String] = db.Column(db.String(11), nullable=False)
    parentCustomerCode: Column[String] = db.Column(db.String(11))
    customerName: Column[String] = db.Column(db.String(50), nullable=False)
    contactLastName: Column[String] = db.Column(db.String(50))
    contactFirstName: Column[String] = db.Column(db.String(50))
    phone: Column[String] = db.Column(db.String(50))
    addressLine1: Column[String] = db.Column(db.String(1024))
    addressLine2: Column[String] = db.Column(db.String(1024))
    city: Column[String] = db.Column(db.String(50))
    state: Column[String] = db.Column(db.String(50))
    postalCode: Column[String] = db.Column(db.String(15))
    country: Column[String] = db.Column(db.String(50))
    customerType: Column[String] = db.Column(db.String(50))
    logoFile: Column[String] = db.Column(db.String(64))
    createdAt: Column[DateTime] = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(
        self,
        customerCode,
        customerName,
        parentCustomerCode=None,
        contactLastName=None,
        contactFirstName=None,
        phone=None,
        addressLine1=None,
        addressLine2=None,
        city=None,
        state=None,
        postalCode=None,
        country=None,
        customerType=None,
        logoFile=None,
        createdAt=None,
    ):
        """
        Initialize a new instance of the Customer class.

        :param customerCode: The code of the customer used as the Wazuh-Agent Label.
        :param customerName: The name of the customer.
        :param parentCustomerCode: The code of the parent customer.
        :param contactLastName: The last name of the contact.
        :param contactFirstName: The first name of the contact.
        :param phone: The phone number of the contact.
        :param addressLine1: The first line of the customer's address.
        :param addressLine2: The second line of the customer's address.
        :param city: The city of the customer's address.
        :param state: The state of the customer's address.
        :param postalCode: The postal code of the customer's address.
        :param country: The country of the customer's address.
        :param customerType: The type of the customer.
        :param logoFile: The file name of the customer's logo.
        :param createdAt: The date the customer was created.
        """
        self.customerCode = customerCode
        self.customerName = customerName
        self.parentCustomerCode = parentCustomerCode
        self.contactLastName = contactLastName
        self.contactFirstName = contactFirstName
        self.phone = phone
        self.addressLine1 = addressLine1
        self.addressLine2 = addressLine2
        self.city = city
        self.state = state
        self.postalCode = postalCode
        self.country = country
        self.customerType = customerType
        self.logoFile = logoFile
        self.createdAt = createdAt

    def __repr__(self) -> str:
        """
        Returns a string representation of the Customer instance.

        :return: A string representation of the customerCode.
        """
        return f"<Customer {self.customerCode}>"


class CustomerSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the Customer class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields = (
            "id",
            "customerCode",
            "parentCustomerCode",
            "customerName",
            "contactLastName",
            "contactFirstName",
            "phone",
            "addressLine1",
            "addressLine2",
            "city",
            "state",
            "postalCode",
            "country",
            "customerType",
            "logoFile",
            "createdAt",
        )


customer_schema: CustomerSchema = CustomerSchema()
customers_schema: CustomerSchema = CustomerSchema(many=True)


class CustomersMeta(db.Model):
    """
    Class for customermeta which stores various customer metadata.
    This class inherits from SQLAlchemy's Model class.
    """

    id: Column[Integer] = db.Column(db.Integer, primary_key=True)
    clientName: Column[String] = db.Column(db.String(255))
    customerCode: Column[String] = db.Column(db.String(11), nullable=False)
    customerMetaGraylogIndex: Column[String] = db.Column(db.String(1024))
    customerMetaGraylogStream: Column[String] = db.Column(db.String(1024))
    customerMetaInfluxOrg: Column[String] = db.Column(db.String(1024))
    customerMetaGrafanaOrg: Column[String] = db.Column(db.String(1024))
    customerMetaWazuhGroup: Column[String] = db.Column(db.String(1024))
    indexRetention: Column[Integer] = db.Column(db.Integer)
    wazuhRegistrationPort: Column[Integer] = db.Column(db.Integer)
    wazuhLogIngestionPort: Column[Integer] = db.Column(db.Integer)

    def __init__(
        self,
        customerCode,
        clientName=None,
        customerMetaGraylogIndex=None,
        customerMetaGraylogStream=None,
        customerMetaInfluxOrg=None,
        customerMetaGrafanaOrg=None,
        customerMetaWazuhGroup=None,
        indexRetention=None,
        wazuhRegistrationPort=None,
        wazuhLogIngestionPort=None,
    ):
        """
        Initialize a new instance of the CustomerMeta class.

        :param customerCode: The code of the customer.
        :param clientName: The name of the client.
        :param customerMetaGraylogIndex: The Graylog index of the customer metadata.
        :param customerMetaGraylogStream: The Graylog stream of the customer metadata.
        :param customerMetaInfluxOrg: The InfluxOrg of the customer metadata.
        :param customerMetaGrafanaOrg: The GrafanaOrg of the customer metadata.
        :param customerMetaWazuhGroup: The WazuhGroup of the customer metadata.
        :param indexRetention: The index retention of the customer metadata.
        :param wazuhRegistrationPort: The Wazuh registration port of the customer's Wazuh Agents.
        :param wazuhLogIngestionPort: The Wazuh log ingestion port of the customer's Wazuh Agents.
        """
        self.customerCode = customerCode
        self.clientName = clientName
        self.customerMetaGraylogIndex = customerMetaGraylogIndex
        self.customerMetaGraylogStream = customerMetaGraylogStream
        self.customerMetaInfluxOrg = customerMetaInfluxOrg
        self.customerMetaGrafanaOrg = customerMetaGrafanaOrg
        self.customerMetaWazuhGroup = customerMetaWazuhGroup
        self.indexRetention = indexRetention
        self.wazuhRegistrationPort = wazuhRegistrationPort
        self.wazuhLogIngestionPort = wazuhLogIngestionPort

    def __repr__(self) -> str:
        """
        Returns a string representation of the CustomerMeta instance.

        :return: A string representation of the customerCode.
        """
        return f"<CustomerMeta {self.customerCode}>"


class CustomerMetaSchema(ma.Schema):
    """
    Schema for serializing and deserializing instances of the CustomerMeta class.
    """

    class Meta:
        """
        Meta class defines the fields to be serialized/deserialized.
        """

        fields = (
            "id",
            "clientName",
            "customerCode",
            "customerMetaGraylogIndex",
            "customerMetaGraylogStream",
            "customerMetaInfluxOrg",
            "customerMetaGrafanaOrg",
            "customerMetaWazuhGroup",
            "indexRetention",
            "wazuhRegistrationPort",
            "wazuhLogIngestionPort",
        )


customer_meta_schema: CustomerMetaSchema = CustomerMetaSchema()
customers_meta_schema: CustomerMetaSchema = CustomerMetaSchema(many=True)

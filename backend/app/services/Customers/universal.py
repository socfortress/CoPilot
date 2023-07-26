import os
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from jinja2 import Environment
from jinja2 import FileSystemLoader
from loguru import logger
from datetime import datetime

from app import db
from app.models.customers import Customers
from app.models.customers import customer_schema
from app.models.customers import customers_schema


class UniversalCustomers:
    @staticmethod
    def create(customerCode: str, customerName: str, parentCustomerCode: str = None,
               contactLastName: str = None, contactFirstName: str = None, phone: str = None,
               addressLine1: str = None, addressLine2: str = None, city: str = None,
               state: str = None, postalCode: str = None, country: str = None,
               customerType: str = None, logoFile: str = None, createdAt: datetime = None) -> Dict[str, Union[int, str]]:
        """
        Create a new customer and add it to the database.

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
        :return: Dictionary of the created customer.
        """
        new_customer = Customers(customerCode, customerName, parentCustomerCode, contactLastName,
                                 contactFirstName, phone, addressLine1, addressLine2, city,
                                 state, postalCode, country, customerType, logoFile, createdAt)
        db.session.add(new_customer)
        db.session.commit()
        return {
            "message": "Customer created successfully.",
            "success": True,
            "customer": customer_schema.dump(new_customer),
        }

    @staticmethod
    def read_by_id(id: int) -> Optional[Dict[str, Union[int, str]]]:
        """
        Fetch customer by their id.

        :param id: ID of the customer.
        :return: Dictionary of the customer or None if not found.
        """
        customer = Customers.query.get(id)
        return customer_schema.dump(customer) if customer else None

    @staticmethod
    def read_by_customerCode(customerCode: str) -> Optional[Dict[str, Union[int, str]]]:
        """
        Fetch customer by customerCode.

        :param customerCode: The code of the customer.
        :return: Dictionary of the customer or None if not found.
        """
        customer = Customers.query.filter_by(customerCode=customerCode).first()
        return customer_schema.dump(customer) if customer else None

    @staticmethod
    def read_all() -> List[Dict[str, Union[int, str]]]:
        """
        Fetch all customers.

        :return: List of dictionaries of all customers.
        """
        customers = Customers.query.all()
        return {
            "message": "Customers retrieved successfully.",
            "success": True,
            "customers": customers_schema.dump(customers, many=True),
        }

    @staticmethod
    def update(
        id: int,
        customerCode: Optional[str] = None,
        customerName: Optional[str] = None,
        parentCustomerCode: Optional[str] = None,
        contactLastName: Optional[str] = None,
        contactFirstName: Optional[str] = None,
        phone: Optional[str] = None,
        addressLine1: Optional[str] = None,
        addressLine2: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        postalCode: Optional[str] = None,
        country: Optional[str] = None,
        customerType: Optional[str] = None,
        logoFile: Optional[str] = None,
        createdAt: Optional[datetime] = None,
    ) -> Optional[Dict[str, Union[int, str]]]:
        """
        Update existing customer.

        :param id: ID of the customer.
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
        :return: Dictionary of the updated customer or None if not found.
        """
        customer = Customers.query.get(id)
        if not customer:
            return None
        if customerCode is not None:
            customer.customerCode = customerCode
        if customerName is not None:
            customer.customerName = customerName
        if parentCustomerCode is not None:
            customer.parentCustomerCode = parentCustomerCode
        if contactLastName is not None:
            customer.contactLastName = contactLastName
        if contactFirstName is not None:
            customer.contactFirstName = contactFirstName
        if phone is not None:
            customer.phone = phone
        if addressLine1 is not None:
            customer.addressLine1 = addressLine1
        if addressLine2 is not None:
            customer.addressLine2 = addressLine2
        if city is not None:
            customer.city = city
        if state is not None:
            customer.state = state
        if postalCode is not None:
            customer.postalCode = postalCode
        if country is not None:
            customer.country = country
        if customerType is not None:
            customer.customerType = customerType
        if logoFile is not None:
            customer.logoFile = logoFile
        if createdAt is not None:
            customer.createdAt = createdAt

        db.session.commit()
        return customer_schema.dump(customer)

    @staticmethod
    def delete_all():
        """
        Delete all customers from the table.
        """
        Customers.query.delete()
        db.session.commit()

    @staticmethod
    def delete_by_id(id: int):
        """
        Delete a customer with the given id.

        :param id: ID of the customer to delete.
        """
        Customers.query.filter(Customers.id == id).delete()
        db.session.commit()


from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from app import db
from app.models.customers import Customers
from app.models.customers import CustomersMeta
from app.models.customers import customer_meta_schema
from app.models.customers import customer_schema
from app.models.customers import customers_meta_schema
from app.models.customers import customers_schema


class UniversalCustomers:
    @staticmethod
    def create(
        customerCode: str,
        customerName: str,
        parentCustomerCode: str = None,
        contactLastName: str = None,
        contactFirstName: str = None,
        phone: str = None,
        addressLine1: str = None,
        addressLine2: str = None,
        city: str = None,
        state: str = None,
        postalCode: str = None,
        country: str = None,
        customerType: str = None,
        logoFile: str = None,
        createdAt: datetime = None,
    ) -> Dict[str, Union[int, str]]:
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
        new_customer = Customers(
            customerCode,
            customerName,
            parentCustomerCode,
            contactLastName,
            contactFirstName,
            phone,
            addressLine1,
            addressLine2,
            city,
            state,
            postalCode,
            country,
            customerType,
            logoFile,
            createdAt,
        )
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


class UniversalCustomersMeta:
    @staticmethod
    def create(
        customerCode: str,
        clientName: str = None,
        customerMetaGraylogIndex: str = None,
        customerMetaGraylogStream: str = None,
        customerMetaInfluxOrg: str = None,
        customerMetaGrafanaOrg: str = None,
        customerMetaWazuhGroup: str = None,
        indexRetention: int = None,
        wazuhRegistrationPort: int = None,
        wazuhLogIngestionPort: int = None,
    ) -> Dict[str, Union[int, str]]:
        """
        Create a new customer meta and add it to the database.

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
        :return: Dictionary of the created customer meta.
        """
        new_customer_meta = CustomersMeta(
            customerCode,
            clientName,
            customerMetaGraylogIndex,
            customerMetaGraylogStream,
            customerMetaInfluxOrg,
            customerMetaGrafanaOrg,
            customerMetaWazuhGroup,
            indexRetention,
            wazuhRegistrationPort,
            wazuhLogIngestionPort,
        )
        db.session.add(new_customer_meta)
        db.session.commit()
        return {
            "message": "Customer Meta created successfully.",
            "success": True,
            "customersMeta": customer_meta_schema.dump(new_customer_meta),
        }

    @staticmethod
    def read_by_id(id: int) -> Optional[Dict[str, Union[int, str]]]:
        """
        Fetch customer meta by their id.

        :param id: ID of the customer meta.
        :return: Dictionary of the customer meta or None if not found.
        """
        customer_meta = CustomersMeta.query.get(id)
        return customer_meta_schema.dump(customer_meta) if customer_meta else None

    @staticmethod
    def read_by_customerCode(customerCode: str) -> Optional[Dict[str, Union[int, str]]]:
        """
        Fetch customer meta by customerCode.

        :param customerCode: The code of the customer meta.
        :return: Dictionary of the customer meta or None if not found.
        """
        customer_meta = CustomersMeta.query.filter_by(customerCode=customerCode).first()
        return customer_meta_schema.dump(customer_meta) if customer_meta else None

    @staticmethod
    def read_all() -> List[Dict[str, Union[int, str]]]:
        """
        Fetch all customer metas.

        :return: List of dictionaries of all customer metas.
        """
        customer_metas = CustomersMeta.query.all()
        return {
            "message": "Customer Metas retrieved successfully.",
            "success": True,
            "customersMetas": customers_meta_schema.dump(customer_metas, many=True),
        }

    @staticmethod
    def update(
        id: int,
        customerCode: Optional[str] = None,
        clientName: Optional[str] = None,
        customerMetaGraylogIndex: Optional[str] = None,
        customerMetaGraylogStream: Optional[str] = None,
        customerMetaInfluxOrg: Optional[str] = None,
        customerMetaGrafanaOrg: Optional[str] = None,
        customerMetaWazuhGroup: Optional[str] = None,
        indexRetention: Optional[int] = None,
        wazuhRegistrationPort: Optional[int] = None,
        wazuhLogIngestionPort: Optional[int] = None,
    ) -> Optional[Dict[str, Union[int, str]]]:
        """
        Update existing customer meta.

        :param id: ID of the customer meta.
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
        :return: Dictionary of the updated customer meta or None if not found.
        """
        customer_meta = CustomersMeta.query.get(id)
        if not customer_meta:
            return None
        if customerCode is not None:
            customer_meta.customerCode = customerCode
        if clientName is not None:
            customer_meta.clientName = clientName
        if customerMetaGraylogIndex is not None:
            customer_meta.customerMetaGraylogIndex = customerMetaGraylogIndex
        if customerMetaGraylogStream is not None:
            customer_meta.customerMetaGraylogStream = customerMetaGraylogStream
        if customerMetaInfluxOrg is not None:
            customer_meta.customerMetaInfluxOrg = customerMetaInfluxOrg
        if customerMetaGrafanaOrg is not None:
            customer_meta.customerMetaGrafanaOrg = customerMetaGrafanaOrg
        if customerMetaWazuhGroup is not None:
            customer_meta.customerMetaWazuhGroup = customerMetaWazuhGroup
        if indexRetention is not None:
            customer_meta.indexRetention = indexRetention
        if wazuhRegistrationPort is not None:
            customer_meta.wazuhRegistrationPort = wazuhRegistrationPort
        if wazuhLogIngestionPort is not None:
            customer_meta.wazuhLogIngestionPort = wazuhLogIngestionPort

        db.session.commit()
        return customer_meta_schema.dump(customer_meta)

    @staticmethod
    def delete_all():
        """
        Delete all customer metas from the table.
        """
        CustomersMeta.query.delete()
        db.session.commit()

    @staticmethod
    def delete_by_id(id: int):
        """
        Delete a customer meta with the given id.

        :param id: ID of the customer meta to delete.
        """
        CustomersMeta.query.filter(CustomersMeta.id == id).delete()
        db.session.commit()

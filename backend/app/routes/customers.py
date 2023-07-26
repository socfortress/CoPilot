from datetime import datetime

from flask import Blueprint
from flask import jsonify
from flask import request
from loguru import logger

from app.services.Customers.universal import UniversalCustomers
from app.services.Customers.universal import UniversalCustomersMeta

bp = Blueprint("customers", __name__)


@bp.route("/customers/create", methods=["POST"])
def create_customer():
    """
    Endpoint to store a new customer into `customers` table.

    Returns:
        Tuple[jsonify, int]: A Tuple where the first element is a JSON response
        indicating if the customer was stored successfully and the second element
        is the HTTP status code.
    """
    logger.info(f"Received data to create a new customer: {request.json}")
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request", "success": False}), 400

    customerCode = request.json.get("customerCode", None)
    customerName = request.json.get("customerName", None)
    parentCustomerCode = request.json.get("parentCustomerCode", None)
    contactLastName = request.json.get("contactLastName", None)
    contactFirstName = request.json.get("contactFirstName", None)
    phone = request.json.get("phone", None)
    addressLine1 = request.json.get("addressLine1", None)
    addressLine2 = request.json.get("addressLine2", None)
    city = request.json.get("city", None)
    state = request.json.get("state", None)
    postalCode = request.json.get("postalCode", None)
    country = request.json.get("country", None)
    customerType = request.json.get("customerType", None)
    logoFile = request.json.get("logoFile", None)
    createdAt = request.json.get("createdAt", None)
    if createdAt:
        createdAt = datetime.fromisoformat(createdAt.replace("Z", "+00:00"))

    new_customer = UniversalCustomers.create(
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

    return jsonify(new_customer), 201


@bp.route("/customers/read/all", methods=["GET"])
def read_all_customers():
    """
    Endpoint to list all customers from the `customers` table.

    Returns:
        jsonify: A JSON response containing the list of all customers.
    """
    logger.info("Received request to get all customers")
    customers = UniversalCustomers.read_all()
    return jsonify(customers)


@bp.route("/customers/read/<int:id>", methods=["GET"])
def read_customer_by_id(id: int):
    """
    Endpoint to fetch a customer by their id.

    Returns:
        Tuple[jsonify, int]: A Tuple where the first element is a JSON response
        containing the customer and the second element is the HTTP status code.
    """
    logger.info(f"Received request to get customer with id {id}")
    customer = UniversalCustomers.read_by_id(id)
    if customer:
        return jsonify(customer), 200
    return jsonify({"message": "Customer not found", "success": False}), 404


@bp.route("/customers/update/<int:id>", methods=["PUT"])
def update_customer(id: int):
    """
    Endpoint to update a customer into `customers` table.

    Returns:
        Tuple[jsonify, int]: A Tuple where the first element is a JSON response
        indicating if the customer was updated successfully and the second element
        is the HTTP status code.
    """
    logger.info(f"Received data to update a customer: {request.json}")
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request", "success": False}), 400

    customerCode = request.json.get("customerCode", None)
    customerName = request.json.get("customerName", None)
    parentCustomerCode = request.json.get("parentCustomerCode", None)
    contactLastName = request.json.get("contactLastName", None)
    contactFirstName = request.json.get("contactFirstName", None)
    phone = request.json.get("phone", None)
    addressLine1 = request.json.get("addressLine1", None)
    addressLine2 = request.json.get("addressLine2", None)
    city = request.json.get("city", None)
    state = request.json.get("state", None)
    postalCode = request.json.get("postalCode", None)
    country = request.json.get("country", None)
    customerType = request.json.get("customerType", None)
    logoFile = request.json.get("logoFile", None)
    createdAt = request.json.get("createdAt", None)
    if createdAt:
        createdAt = datetime.fromisoformat(createdAt.replace("Z", "+00:00"))

    updated_customer = UniversalCustomers.update(
        id,
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

    return jsonify(updated_customer), 201


@bp.route("/customers_meta/create", methods=["POST"])
def create_customer_meta():
    """
    Endpoint to create a new entry in the `CustomersMeta` table.

    Returns:
        Tuple[jsonify, int]: A Tuple where the first element is a JSON response
        indicating if the customer meta was created successfully and the second element
        is the HTTP status code.
    """
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request", "success": False}), 400

    customerCode = request.json.get("customerCode", None)
    clientName = request.json.get("clientName", None)
    customerMetaGraylogIndex = request.json.get("customerMetaGraylogIndex", None)
    customerMetaGraylogStream = request.json.get("customerMetaGraylogStream", None)
    customerMetaInfluxOrg = request.json.get("customerMetaInfluxOrg", None)
    customerMetaGrafanaOrg = request.json.get("customerMetaGrafanaOrg", None)
    customerMetaWazuhGroup = request.json.get("customerMetaWazuhGroup", None)
    indexRetention = request.json.get("indexRetention", None)
    wazuhRegistrationPort = request.json.get("wazuhRegistrationPort", None)
    wazuhLogIngestionPort = request.json.get("wazuhLogIngestionPort", None)

    new_customer_meta = UniversalCustomersMeta.create(
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

    return jsonify(new_customer_meta), 201


@bp.route("/customers_meta/read/all", methods=["GET"])
def read_all_customers_meta():
    """
    Endpoint to list all customers from the `customers` table.

    Returns:
        jsonify: A JSON response containing the list of all customers.
    """
    logger.info("Received request to get all customers")
    customers = UniversalCustomersMeta.read_all()
    return jsonify(customers)


@bp.route("/customers_meta/read/<int:id>", methods=["GET"])
def read_customer_meta_by_id(id: int):
    """
    Endpoint to fetch a customer by their id.

    Returns:
        Tuple[jsonify, int]: A Tuple where the first element is a JSON response
        containing the customer and the second element is the HTTP status code.
    """
    logger.info(f"Received request to get customer with id {id}")
    customer = UniversalCustomersMeta.read_by_id(id)
    if customer:
        return jsonify(customer), 200
    return jsonify({"message": "Customer not found", "success": False}), 404


@bp.route("/customers_meta/update/<int:id>", methods=["PUT"])
def update_customer_meta(id: int):
    """
    Endpoint to update a customersmeta details into the `customers_meta` table.

    Returns:
        Tuple[jsonify, int]: A Tuple where the first element is a JSON response
        indicating if the customer was updated successfully and the second element
        is the HTTP status code.
    """
    logger.info(f"Received data to update a customer: {request.json}")
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request", "success": False}), 400

    customerCode = request.json.get("customerCode", None)
    clientName = request.json.get("clientName", None)
    customerMetaGraylogIndex = request.json.get("customerMetaGraylogIndex", None)
    customerMetaGraylogStream = request.json.get("customerMetaGraylogStream", None)
    customerMetaInfluxOrg = request.json.get("customerMetaInfluxOrg", None)
    customerMetaGrafanaOrg = request.json.get("customerMetaGrafanaOrg", None)
    customerMetaWazuhGroup = request.json.get("customerMetaWazuhGroup", None)
    indexRetention = request.json.get("indexRetention", None)
    wazuhRegistrationPort = request.json.get("wazuhRegistrationPort", None)
    wazuhLogIngestionPort = request.json.get("wazuhLogIngestionPort", None)

    updated_customer_meta = UniversalCustomersMeta.update(
        id,
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

    return jsonify(updated_customer_meta), 201

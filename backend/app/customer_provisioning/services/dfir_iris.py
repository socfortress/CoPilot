from fastapi import HTTPException
from loguru import logger


from app.connectors.dfir_iris.utils.universal import fetch_and_validate_data
from app.connectors.dfir_iris.utils.universal import initialize_client_and_admin
from app.connectors.dfir_iris.utils.universal import initialize_client_and_customer
from app.connectors.dfir_iris.schema.admin import CreateCustomerResponse, ListCustomers

async def check_customer_exists(customer_name: str) -> bool:
    client, customer = await initialize_client_and_customer("DFIR-IRIS")
    result = await fetch_and_validate_data(client, customer.list_customers)
    customers = ListCustomers(**result)
    for customer in customers.data:
        if customer.customer_name == customer_name:
            return True


async def create_customer(customer_name: str) -> CreateCustomerResponse:
    # check if the customer exists
    exists = await check_customer_exists(customer_name)
    if exists:
        raise HTTPException(status_code=400, detail=f"Customer {customer_name} already exists")
    client, admin = await initialize_client_and_admin("DFIR-IRIS")
    result = await fetch_and_validate_data(client, admin.add_customer, customer_name)
    return CreateCustomerResponse(success=result["success"], data=result["data"])

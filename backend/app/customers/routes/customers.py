from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from loguru import logger
from starlette.status import HTTP_401_UNAUTHORIZED

# App specific imports
from app.customers.schema.customers import AgentModel
from app.customers.schema.customers import AgentsResponse
from app.customers.schema.customers import CustomerFullResponse
from app.customers.schema.customers import CustomerMetaRequestBody
from app.customers.schema.customers import CustomerMetaResponse
from app.customers.schema.customers import CustomerRequestBody
from app.customers.schema.customers import CustomerResponse
from app.customers.schema.customers import CustomersResponse
from app.db.db_session import session
from app.db.universal_models import Agents
from app.db.universal_models import Customers
from app.db.universal_models import CustomersMeta

# from app.healthchecks.agents.schema.agents import AgentModel
from app.healthchecks.agents.schema.agents import AgentHealthCheckResponse
from app.healthchecks.agents.schema.agents import TimeCriteriaModel
from app.healthchecks.agents.services.agents import velociraptor_agents_healthcheck
from app.healthchecks.agents.services.agents import wazuh_agents_healthcheck

customers_router = APIRouter()


def verify_admin(user):
    if not user.is_admin:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def verify_unique_customer_code(customer: CustomerRequestBody):
    existing_customer = session.query(Customers).filter(Customers.customer_code == customer.customer_code).first()
    if existing_customer:
        raise HTTPException(status_code=400, detail="Customer with this customer_code already exists")


@customers_router.post("", response_model=CustomerResponse, description="Create a new customer")
async def create_customer(customer: CustomerRequestBody) -> CustomerResponse:
    verify_unique_customer_code(customer)
    logger.info(f"Creating new customer: {customer}")
    new_customer = Customers(**customer.dict())
    session.add(new_customer)
    session.commit()
    return CustomerResponse(customer=customer, success=True, message="Customer created successfully")


@customers_router.get("", response_model=CustomersResponse, description="Get all customers")
async def get_customers() -> CustomersResponse:
    logger.info("Fetching all customers")
    customers = session.query(Customers).all()
    # Explode the customers list into a list of Customer objects
    customers = [CustomerRequestBody.parse_obj(customer.__dict__) for customer in customers]
    return CustomersResponse(customers=customers, success=True, message="Customers fetched successfully")


@customers_router.get("/{customer_code}", response_model=CustomerResponse, description="Get customer by customer_code")
async def get_customer(customer_code: str) -> CustomerResponse:
    logger.info(f"Fetching customer with customer_code: {customer_code}")
    customer = session.query(Customers).filter(Customers.customer_code == customer_code).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer with customer_code {customer_code} not found")
    return CustomerResponse(
        customer=CustomerRequestBody.parse_obj(customer.__dict__),
        success=True,
        message="Customer fetched successfully",
    )


@customers_router.put("/{customer_code}", response_model=CustomerResponse, description="Update customer by customer_code")
async def update_customer(customer_code: str, customer: CustomerRequestBody) -> CustomerResponse:
    logger.info(f"Updating customer with customer_code: {customer_code}")
    existing_customer = session.query(Customers).filter(Customers.customer_code == customer_code).first()
    if not existing_customer:
        raise HTTPException(status_code=404, detail=f"Customer with customer_code {customer_code} not found")
    existing_customer.update_from_model(customer)
    session.commit()
    return CustomerResponse(
        customer=CustomerRequestBody.parse_obj(customer.__dict__),
        success=True,
        message="Customer updated successfully",
    )


# ! TODO: Fix delete customer
# @customers_router.delete("/{customer_code}", response_model=CustomerResponse, description="Delete customer by customer_code")
# async def delete_customer(customer_code: str) -> CustomerResponse:
#     logger.info(f"Deleting customer with customer_code: {customer_code}")
#     existing_customer = session.query(Customers).filter(Customers.customer_code == customer_code).first()
#     if not existing_customer:
#         raise HTTPException(status_code=404, detail=f"Customer with customer_code {customer_code} not found")
#     session.delete(existing_customer)
#     session.commit()
#     return CustomerResponse(customer=CustomerRequestBody.parse_obj(existing_customer.__dict__), success=True, message="Customer deleted successfully")


@customers_router.post("/{customer_code}/meta", response_model=CustomerMetaResponse, description="Add new customer meta")
async def add_customer_meta(customer_code: str, customer_meta: CustomerMetaRequestBody) -> CustomerMetaResponse:
    logger.info(f"Adding new customer meta: {customer_meta}")
    existing_customer = session.query(Customers).filter(Customers.customer_code == customer_code).first()
    if not existing_customer:
        raise HTTPException(status_code=404, detail=f"Customer with customer_code {customer_code} not found")
    # Get the customer_code and customer_name from the existing customer and add it to the customer_meta object
    logger.info(f"Got existing customer: {existing_customer}")
    new_customer_meta = CustomersMeta(**customer_meta.dict())
    new_customer_meta.customer_code = existing_customer.customer_code
    new_customer_meta.customer_name = existing_customer.customer_name
    session.add(new_customer_meta)
    session.commit()
    return CustomerMetaResponse(customer_meta=customer_meta, success=True, message="Customer meta added successfully")


@customers_router.get("/{customer_code}/meta", response_model=CustomerMetaResponse, description="Get customer meta by customer_code")
async def get_customer_meta(customer_code: str) -> CustomerMetaResponse:
    logger.info(f"Fetching customer meta with customer_code: {customer_code}")
    customer_meta = session.query(CustomersMeta).filter(CustomersMeta.customer_code == customer_code).first()
    if not customer_meta:
        raise HTTPException(status_code=404, detail=f"Customer meta with customer_code {customer_code} not found")
    return CustomerMetaResponse(
        customer_meta=CustomerMetaRequestBody.parse_obj(customer_meta.__dict__),
        success=True,
        message="Customer meta fetched successfully",
    )


@customers_router.put("/{customer_code}/meta", response_model=CustomerMetaResponse, description="Update customer meta by customer_code")
async def update_customer_meta(customer_code: str, customer_meta: CustomerMetaRequestBody) -> CustomerMetaResponse:
    logger.info(f"Updating customer meta with customer_code: {customer_code}")
    existing_customer_meta = session.query(CustomersMeta).filter(CustomersMeta.customer_code == customer_code).first()
    if not existing_customer_meta:
        raise HTTPException(status_code=404, detail=f"Customer meta with customer_code {customer_code} not found")

    # Update the existing record with new values
    existing_customer_meta.update_from_model(customer_meta)
    logger.info(f"Updated existing customer meta: {existing_customer_meta}")

    # Commit the changes to the database
    session.commit()

    return CustomerMetaResponse(
        customer_meta=CustomerMetaRequestBody.parse_obj(customer_meta.__dict__),
        success=True,
        message="Customer meta updated successfully",
    )


# ! TODO: Fix delete customer meta
# @customers_router.delete("/{customer_code}/meta", response_model=CustomerMetaResponse, description="Delete customer meta by customer_code")
# async def delete_customer_meta(customer_code: str) -> CustomerMetaResponse:
#     logger.info(f"Deleting customer meta with customer_code: {customer_code}")
#     existing_customer_meta = session.query(CustomersMeta).filter(CustomersMeta.customer_code == customer_code).first()
#     if not existing_customer_meta:
#         raise HTTPException(status_code=404, detail=f"Customer meta with customer_code {customer_code} not found")
#     session.delete(existing_customer_meta)
#     session.commit()
#     return CustomerMetaResponse(customer_meta=CustomerMetaRequestBody.parse_obj(existing_customer_meta.__dict__), success=True, message="Customer meta deleted successfully")


@customers_router.get(
    "/{customer_code}/full",
    response_model=CustomerFullResponse,
    description="Get customer and customer meta by customer_code",
)
async def get_customer_full(customer_code: str) -> CustomerFullResponse:
    logger.info(f"Fetching customer and customer meta with customer_code: {customer_code}")
    customer = session.query(Customers).filter(Customers.customer_code == customer_code).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer with customer_code {customer_code} not found")
    customer_meta = session.query(CustomersMeta).filter(CustomersMeta.customer_code == customer_code).first()
    if not customer_meta:
        raise HTTPException(status_code=404, detail=f"Customer meta with customer_code {customer_code} not found")
    return CustomerFullResponse(
        customer=CustomerRequestBody.parse_obj(customer.__dict__),
        customer_meta=CustomerMetaRequestBody.parse_obj(customer_meta.__dict__),
        success=True,
        message="Customer and customer meta fetched successfully",
    )


# Get Agents for the given customer_code
@customers_router.get("/{customer_code}/agents", response_model=AgentsResponse, description="Get agents for the given customer_code")
async def get_agents(customer_code: str) -> AgentsResponse:
    logger.info(f"Fetching agents for customer_code: {customer_code}")
    customer = session.query(Customers).filter(Customers.customer_code == customer_code).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer with customer_code {customer_code} not found")
    agents = session.query(Agents).filter(Agents.customer_code == customer_code).all()
    # Explode the agents list into a list of Agent objects
    agents = [AgentModel.parse_obj(agent.__dict__) for agent in agents]
    return AgentsResponse(agents=agents, success=True, message="Agents fetched successfully")


# Retrieve the agents for the given customer_code then perform a healthcheck on them
@customers_router.get(
    "/{customer_code}/agents/healthcheck/wazuh",
    response_model=AgentHealthCheckResponse,
    description="Get agents healthcheck for the given customer_code",
)
async def get_wazuh_agents_healthcheck(
    customer_code: str,
    minutes: int = Query(60, description="Number of minutes within which the agent should have been last seen to be considered healthy."),
    hours: int = Query(0, description="Number of hours within which the agent should have been last seen to be considered healthy."),
    days: int = Query(0, description="Number of days within which the agent should have been last seen to be considered healthy."),
) -> AgentHealthCheckResponse:
    logger.info(f"Fetching agents for customer_code: {customer_code}")
    customer = session.query(Customers).filter(Customers.customer_code == customer_code).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer with customer_code {customer_code} not found")
    agents = session.query(Agents).filter(Agents.customer_code == customer_code).all()
    # Explode the agents list into a list of Agent objects
    agents = [AgentModel.parse_obj(agent.__dict__) for agent in agents]
    time_criteria = TimeCriteriaModel(minutes=minutes, hours=hours, days=days)
    return wazuh_agents_healthcheck(agents, time_criteria)


# Retrieve the agents for the given customer_code then perform a healthcheck on them
@customers_router.get(
    "/{customer_code}/agents/healthcheck/velociraptor",
    response_model=AgentHealthCheckResponse,
    description="Get agents healthcheck for the given customer_code",
)
async def get_velociraptor_agents_healthcheck(
    customer_code: str,
    minutes: int = Query(60, description="Number of minutes within which the agent should have been last seen to be considered healthy."),
    hours: int = Query(0, description="Number of hours within which the agent should have been last seen to be considered healthy."),
    days: int = Query(0, description="Number of days within which the agent should have been last seen to be considered healthy."),
) -> AgentHealthCheckResponse:
    logger.info(f"Fetching agents for customer_code: {customer_code}")
    customer = session.query(Customers).filter(Customers.customer_code == customer_code).first()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer with customer_code {customer_code} not found")
    agents = session.query(Agents).filter(Agents.customer_code == customer_code).all()
    # Explode the agents list into a list of Agent objects
    agents = [AgentModel.parse_obj(agent.__dict__) for agent in agents]
    time_criteria = TimeCriteriaModel(minutes=minutes, hours=hours, days=days)
    return velociraptor_agents_healthcheck(agents, time_criteria)

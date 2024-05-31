from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.status import HTTP_401_UNAUTHORIZED

from app.auth.utils import AuthHandler

# App specific imports
from app.customers.schema.customers import AgentModel
from app.customers.schema.customers import AgentsResponse
from app.customers.schema.customers import CustomerFullResponse
from app.customers.schema.customers import CustomerMetaRequestBody
from app.customers.schema.customers import CustomerMetaResponse
from app.customers.schema.customers import CustomerRequestBody
from app.customers.schema.customers import CustomerResponse
from app.customers.schema.customers import CustomersResponse
from app.db.db_session import get_db
from app.db.universal_models import Agents
from app.db.universal_models import Customers
from app.db.universal_models import CustomersMeta
from app.healthchecks.agents.schema.agents import AgentHealthCheckResponse
from app.healthchecks.agents.schema.agents import TimeCriteriaModel
from app.healthchecks.agents.services.agents import velociraptor_agents_healthcheck
from app.healthchecks.agents.services.agents import wazuh_agents_healthcheck

customers_router = APIRouter()


def verify_admin(user):
    """
    Verify if the user is an admin.

    Args:
        user: The user object to be verified.

    Raises:
        HTTPException: If the user is not an admin.

    Returns:
        None
    """
    if not user.is_admin:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Unauthorized")


async def verify_unique_customer_code(
    session: AsyncSession,
    customer: CustomerRequestBody,
):
    """
    Verifies if the given customer code is unique in the database.

    Args:
        session (AsyncSession): The database session.
        customer (CustomerRequestBody): The customer data to be verified.

    Raises:
        HTTPException: If a customer with the same customer code already exists in the database.
    """
    stmt = select(Customers).filter(Customers.customer_code == customer.customer_code)
    result = await session.execute(stmt)
    existing_customer = result.scalars().first()
    if existing_customer:
        raise HTTPException(
            status_code=400,
            detail="Customer with this customer_code already exists",
        )


@customers_router.post(
    "",
    response_model=CustomerResponse,
    description="Create a new customer",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def create_customer(
    customer: CustomerRequestBody,
    session: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """
    Create a new customer.

    Args:
        customer (CustomerRequestBody): The customer data to be created.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        CustomerResponse: The response containing the created customer data.

    Raises:
        None
    """
    await verify_unique_customer_code(session, customer)
    logger.info(f"Creating new customer: {customer}")
    new_customer = Customers(**customer.dict())
    session.add(new_customer)
    await session.commit()  # Use await to perform the commit operation asynchronously
    return CustomerResponse(
        customer=customer,
        success=True,
        message="Customer created successfully",
    )


@customers_router.get(
    "",
    response_model=CustomersResponse,
    description="Get all customers",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customers(session: AsyncSession = Depends(get_db)) -> CustomersResponse:
    """
    Fetches all customers from the database.

    Args:
        session (AsyncSession): The async session object used to interact with the database.

    Returns:
        CustomersResponse: The response containing the list of customers fetched successfully.
    """
    logger.info("Fetching all customers")

    # Asynchronous query to fetch all customers
    result = await session.execute(select(Customers))
    customers = result.scalars().all()

    # Parse the customer ORM objects into schema objects
    customers_list = [CustomerRequestBody.from_orm(customer) for customer in customers]
    return CustomersResponse(
        customers=customers_list,
        success=True,
        message="Customers fetched successfully",
    )


@customers_router.get(
    "/{customer_code}",
    response_model=CustomerResponse,
    description="Get customer by customer_code",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customer(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """
    Get customer by customer_code.

    Args:
        customer_code (str): The code of the customer to retrieve.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        CustomerResponse: The response containing the customer data.

    Raises:
        HTTPException: If the customer with the specified code is not found.
    """
    logger.info(f"Fetching customer with customer_code: {customer_code}")

    # Asynchronous query to fetch customer
    result = await session.execute(
        select(Customers).filter(Customers.customer_code == customer_code),
    )
    customer = result.scalars().first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer with customer_code {customer_code} not found",
        )

    # Convert ORM object to Pydantic model
    customer_data = CustomerRequestBody.from_orm(customer)
    return CustomerResponse(
        customer=customer_data,
        success=True,
        message="Customer fetched successfully",
    )


@customers_router.put(
    "/{customer_code}",
    response_model=CustomerResponse,
    description="Update customer by customer_code",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def update_customer(
    customer_code: str,
    customer: CustomerRequestBody,
    session: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """
    Update a customer with the given customer_code.

    Args:
        customer_code (str): The code of the customer to be updated.
        customer (CustomerRequestBody): The updated customer data.
        session (AsyncSession, optional): The asynchronous database session. Defaults to Depends(get_db).

    Returns:
        CustomerResponse: The response containing the updated customer data.

    Raises:
        HTTPException: If the customer with the given customer_code is not found.
    """
    logger.info(f"Updating customer with customer_code: {customer_code}")

    # Asynchronous query to find the existing customer
    result = await session.execute(
        select(Customers).filter(Customers.customer_code == customer_code),
    )
    existing_customer = result.scalars().first()

    if not existing_customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer with customer_code {customer_code} not found",
        )

    # Update model instance with input data
    for key, value in customer.dict().items():
        setattr(existing_customer, key, value)

    await session.commit()  # Commit changes asynchronously

    return CustomerResponse(
        customer=customer,  # CustomerRequestBody is already a Pydantic model
        success=True,
        message="Customer updated successfully",
    )


# ! TODO - Add a check to ensure that the customer_code is not being used by any agents
@customers_router.delete(
    "/{customer_code}",
    response_model=CustomerResponse,
    description="Delete customer by customer_code",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
)
async def delete_customer(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """
    Delete a customer by customer_code.

    Args:
        customer_code (str): The code of the customer to be deleted.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        CustomerResponse: The response containing the deleted customer data.

    Raises:
        HTTPException: If the customer with the given customer_code is not found.
    """
    logger.info(f"Deleting customer with customer_code: {customer_code}")

    result = await session.execute(
        select(Customers).filter(Customers.customer_code == customer_code),
    )
    existing_customer = result.scalars().first()

    if not existing_customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer with customer_code {customer_code} not found",
        )

    # Capture the customer data before deleting
    customer_data = CustomerRequestBody.from_orm(existing_customer)

    # Delete the customer
    await session.delete(existing_customer)
    await session.flush()  # Optional: Flush the changes to the database
    await session.commit()  # Commit the transaction
    # Close the session
    await session.close()

    return CustomerResponse(
        customer=customer_data,
        success=True,
        message="Customer deleted successfully",
    )


@customers_router.post(
    "/{customer_code}/meta",
    response_model=CustomerMetaResponse,
    description="Add new customer meta",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
    deprecated=True,
)
async def add_customer_meta(
    customer_code: str,
    customer_meta: CustomerMetaRequestBody,
    session: AsyncSession = Depends(get_db),
) -> CustomerMetaResponse:
    """
    Add new customer meta.

    Args:
        customer_code (str): The code of the customer.
        customer_meta (CustomerMetaRequestBody): The meta information of the customer.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        CustomerMetaResponse: The response containing the added customer meta.

    Raises:
        HTTPException: If the customer with the given customer_code is not found.
    """
    logger.info(f"Adding new customer meta: {customer_meta}")

    result = await session.execute(
        select(Customers).filter(Customers.customer_code == customer_code),
    )
    existing_customer = result.scalars().first()

    if not existing_customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer with customer_code {customer_code} not found",
        )

    logger.info(f"Got existing customer: {existing_customer}")
    new_customer_meta = CustomersMeta(**customer_meta.dict())
    new_customer_meta.customer_code = existing_customer.customer_code
    new_customer_meta.customer_name = existing_customer.customer_name

    session.add(new_customer_meta)
    await session.commit()  # Use await to perform the commit operation asynchronously

    return CustomerMetaResponse(
        customer_meta=customer_meta,
        success=True,
        message="Customer meta added successfully",
    )


@customers_router.get(
    "/{customer_code}/meta",
    response_model=CustomerMetaResponse,
    description="Get customer meta by customer_code",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
    deprecated=True,
)
async def get_customer_meta(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> CustomerMetaResponse:
    """
    Retrieve customer meta data by customer_code.

    Args:
        customer_code (str): The customer code.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        CustomerMetaResponse: The response containing the customer meta data.

    Raises:
        HTTPException: If the customer meta data is not found.
    """
    logger.info(f"Fetching customer meta with customer_code: {customer_code}")

    result = await session.execute(
        select(CustomersMeta).filter(CustomersMeta.customer_code == customer_code),
    )
    customer_meta = result.scalars().first()

    if not customer_meta:
        raise HTTPException(
            status_code=404,
            detail=f"Customer meta with customer_code {customer_code} not found",
        )

    # Assuming CustomerMetaRequestBody can be created from the ORM model directly
    customer_meta_data = CustomerMetaRequestBody.from_orm(customer_meta)
    return CustomerMetaResponse(
        customer_meta=customer_meta_data,
        success=True,
        message="Customer meta fetched successfully",
    )


@customers_router.put(
    "/{customer_code}/meta",
    response_model=CustomerMetaResponse,
    description="Update customer meta by customer_code",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
    deprecated=True,
)
async def update_customer_meta(
    customer_code: str,
    customer_meta: CustomerMetaRequestBody,
    session: AsyncSession = Depends(get_db),
) -> CustomerMetaResponse:
    """
    Update customer meta by customer_code.

    Args:
        customer_code (str): The customer code.
        customer_meta (CustomerMetaRequestBody): The updated customer meta.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        CustomerMetaResponse: The updated customer meta response.

    Raises:
        HTTPException: If the customer meta with the given customer_code is not found.
    """
    logger.info(f"Updating customer meta with customer_code: {customer_code}")

    result = await session.execute(
        select(CustomersMeta).filter(CustomersMeta.customer_code == customer_code),
    )
    existing_customer_meta = result.scalars().first()

    if not existing_customer_meta:
        raise HTTPException(
            status_code=404,
            detail=f"Customer meta with customer_code {customer_code} not found",
        )

    # Update the existing record with new values
    for key, value in customer_meta.dict(exclude_unset=True).items():
        setattr(existing_customer_meta, key, value)

    await session.commit()  # Commit the changes to the database asynchronously

    # Return the updated customer_meta
    return CustomerMetaResponse(
        customer_meta=customer_meta,
        success=True,
        message="Customer meta updated successfully",
    )


@customers_router.delete(
    "/{customer_code}/meta",
    response_model=CustomerMetaResponse,
    description="Delete customer meta by customer_code",
    dependencies=[Security(AuthHandler().require_any_scope("admin"))],
    deprecated=False,
)
async def delete_customer_meta(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> CustomerMetaResponse:
    """
    Delete customer meta by customer_code.

    Args:
        customer_code (str): The code of the customer meta to be deleted.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        CustomerMetaResponse: The response containing the deleted customer meta data.

    Raises:
        HTTPException: If the customer meta with the given customer_code is not found.
    """
    logger.info(f"Deleting customer meta with customer_code: {customer_code}")

    result = await session.execute(
        select(CustomersMeta).filter(CustomersMeta.customer_code == customer_code),
    )
    existing_customer_meta = result.scalars().first()

    if not existing_customer_meta:
        raise HTTPException(
            status_code=404,
            detail=f"Customer meta with customer_code {customer_code} not found",
        )

    # Store customer meta data for response before deleting
    customer_meta_data = CustomerMetaRequestBody.from_orm(existing_customer_meta)

    await session.delete(existing_customer_meta)
    await session.flush()  # Optional: Flush the changes to the database
    await session.commit()  # Ensure to await commit
    # Close the session
    await session.close()

    return CustomerMetaResponse(
        customer_meta=customer_meta_data,
        success=True,
        message="Customer meta deleted successfully",
    )


@customers_router.get(
    "/{customer_code}/full",
    response_model=CustomerFullResponse,
    description="Get customer and customer meta by customer_code",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_customer_full(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> CustomerFullResponse:
    """
    Retrieve the customer and customer meta information based on the customer code.

    Args:
        customer_code (str): The code of the customer to retrieve.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        CustomerFullResponse: The response containing the customer and customer meta information.

    Raises:
        HTTPException: If the customer with the specified code is not found.

    """
    logger.info(
        f"Fetching customer and customer meta with customer_code: {customer_code}",
    )

    customer_result = await session.execute(
        select(Customers).filter(Customers.customer_code == customer_code),
    )
    customer = customer_result.scalars().first()
    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer with customer_code {customer_code} not found",
        )

    customer_meta_result = await session.execute(
        select(CustomersMeta).filter(CustomersMeta.customer_code == customer_code),
    )
    customer_meta = customer_meta_result.scalars().first()
    if not customer_meta:
        return CustomerFullResponse(
            customer=CustomerRequestBody.from_orm(customer),
            success=True,
            message="Customer fetched successfully but customer meta not found",
        )

    return CustomerFullResponse(
        customer=CustomerRequestBody.from_orm(customer),
        customer_meta=CustomerMetaRequestBody.from_orm(customer_meta),
        success=True,
        message="Customer and customer meta fetched successfully",
    )


@customers_router.get(
    "/{customer_code}/agents",
    response_model=AgentsResponse,
    description="Get agents for the given customer_code",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_agents(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> AgentsResponse:
    """
    Fetches agents for the given customer_code.

    Args:
        customer_code (str): The code of the customer.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AgentsResponse: The response containing the fetched agents.
    """
    logger.info(f"Fetching agents for customer_code: {customer_code}")

    # Check if the customer exists
    customer_result = await session.execute(
        select(Customers).filter(Customers.customer_code == customer_code),
    )
    customer = customer_result.scalars().first()
    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer with customer_code {customer_code} not found",
        )

    # Asynchronously fetch all agents for the customer
    agents_result = await session.execute(
        select(Agents).filter(Agents.customer_code == customer_code),
    )
    agents = agents_result.scalars().all()

    # Convert ORM objects to Pydantic models
    agents_list = [AgentModel.from_orm(agent) for agent in agents]
    return AgentsResponse(
        agents=agents_list,
        success=True,
        message="Agents fetched successfully",
    )


@customers_router.get(
    "/{customer_code}/agents/healthcheck/wazuh",
    response_model=AgentHealthCheckResponse,
    description="Get agents healthcheck for the given customer_code",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_wazuh_agents_healthcheck(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
    minutes: int = Query(
        60,
        description="Number of minutes within which the agent should have been last seen to be considered healthy.",
    ),
    hours: int = Query(
        0,
        description="Number of hours within which the agent should have been last seen to be considered healthy.",
    ),
    days: int = Query(
        0,
        description="Number of days within which the agent should have been last seen to be considered healthy.",
    ),
) -> AgentHealthCheckResponse:
    """
    Get agents healthcheck for the given customer_code.

    Args:
        customer_code (str): The code of the customer.

    Returns:
        AgentHealthCheckResponse: The response containing the healthcheck information for the agents.
    """
    logger.info(f"Fetching agents for customer_code: {customer_code}")

    # Asynchronously fetch customer and agents
    customer_result = await session.execute(
        select(Customers).filter(Customers.customer_code == customer_code),
    )
    customer = customer_result.scalars().first()
    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer with customer_code {customer_code} not found",
        )

    agents_result = await session.execute(
        select(Agents).filter(Agents.customer_code == customer_code),
    )
    agents = agents_result.scalars().all()

    # Convert ORM objects to Pydantic models

    # Explode the agents list into a list of Agent objects
    agents = [AgentModel.parse_obj(agent.__dict__) for agent in agents]
    time_criteria = TimeCriteriaModel(minutes=minutes, hours=hours, days=days)
    return await wazuh_agents_healthcheck(agents, time_criteria)


@customers_router.get(
    "/{customer_code}/agents/healthcheck/velociraptor",
    response_model=AgentHealthCheckResponse,
    description="Get agents healthcheck for the given customer_code",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_velociraptor_agents_healthcheck(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
    minutes: int = Query(
        60,
        description="Number of minutes within which the agent should have been last seen to be considered healthy.",
    ),
    hours: int = Query(
        0,
        description="Number of hours within which the agent should have been last seen to be considered healthy.",
    ),
    days: int = Query(
        0,
        description="Number of days within which the agent should have been last seen to be considered healthy.",
    ),
) -> AgentHealthCheckResponse:
    """
    Fetches the healthcheck of agents for the given customer_code.

    Args:
        customer_code (str): The code of the customer.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).
        minutes (int, optional): Number of minutes within which the agent should have been last seen to be considered healthy. Defaults to 60.
        hours (int, optional): Number of hours within which the agent should have been last seen to be considered healthy. Defaults to 0.
        days (int, optional): Number of days within which the agent should have been last seen to be considered healthy. Defaults to 0.

    Returns:
        AgentHealthCheckResponse: The response containing the healthcheck of agents.
    """
    logger.info(f"Fetching agents for customer_code: {customer_code}")

    # Asynchronously fetch customer
    customer_result = await session.execute(
        select(Customers).filter(Customers.customer_code == customer_code),
    )
    customer = customer_result.scalars().first()
    if not customer:
        raise HTTPException(
            status_code=404,
            detail=f"Customer with customer_code {customer_code} not found",
        )

    # Asynchronously fetch all agents for the customer
    agents_result = await session.execute(
        select(Agents).filter(Agents.customer_code == customer_code),
    )
    agents = agents_result.scalars().all()
    agents = [AgentModel.parse_obj(agent.__dict__) for agent in agents]
    time_criteria = TimeCriteriaModel(minutes=minutes, hours=hours, days=days)
    return await velociraptor_agents_healthcheck(agents, time_criteria)

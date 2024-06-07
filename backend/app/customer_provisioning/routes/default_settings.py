from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.utils import AuthHandler
from app.customer_provisioning.models.default_settings import (
    CustomerProvisioningDefaultSettings,
)
from app.customer_provisioning.schema.default import (
    CustomerProvisioningDefaultSettingsResponse,
)
from app.db.db_session import get_db

customer_provisioning_default_settings_router = APIRouter()


@customer_provisioning_default_settings_router.get(
    "/default_settings",
    response_model=CustomerProvisioningDefaultSettingsResponse,
    description="Get all default settings for customer provisioning",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_all_customer_provisioning_default_settings(
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CustomerProvisioningDefaultSettings)
    result = await db.execute(stmt)
    customer_provisioning_default_settings = result.scalars().first()
    if not customer_provisioning_default_settings:
        raise HTTPException(
            status_code=404,
            detail="No customer provisioning default settings found",
        )
    logger.info(f"Customer Provisioning Default Settings retrieved successfully: {customer_provisioning_default_settings}")
    return CustomerProvisioningDefaultSettingsResponse(
        message="Customer Provisioning Default Settings retrieved successfully",
        success=True,
        customer_provisioning_default_settings=customer_provisioning_default_settings,
    )


@customer_provisioning_default_settings_router.post(
    "/default_settings",
    response_model=CustomerProvisioningDefaultSettingsResponse,
    description="Create a new default settings for customer provisioning",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def create_customer_provisioning_default_settings(
    customer_provisioning_default_settings: CustomerProvisioningDefaultSettings = Body(...),
    db: AsyncSession = Depends(get_db),
):
    # Check if there's already an entry
    stmt = select(CustomerProvisioningDefaultSettings)
    result = await db.execute(stmt)
    existing_settings = result.scalars().first()

    if existing_settings:
        raise HTTPException(status_code=400, detail="Only one customer provisioning default settings can exist")

    db.add(customer_provisioning_default_settings)
    await db.commit()
    return CustomerProvisioningDefaultSettingsResponse(
        message="Customer Provisioning Default Settings created successfully",
        success=True,
        customer_provisioning_default_settings=customer_provisioning_default_settings,
    )


@customer_provisioning_default_settings_router.put(
    "/default_settings",
    response_model=CustomerProvisioningDefaultSettingsResponse,
    description="Update default settings for customer provisioning",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def update_customer_provisioning_default_settings(
    customer_provisioning_default_settings: CustomerProvisioningDefaultSettings = Body(...),
    db: AsyncSession = Depends(get_db),
):
    # Fetch the existing record
    stmt = select(CustomerProvisioningDefaultSettings).where(
        CustomerProvisioningDefaultSettings.id == customer_provisioning_default_settings.id,
    )
    result = await db.execute(stmt)
    existing_settings = result.scalars().first()

    if not existing_settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    # Update the fields
    for key, value in customer_provisioning_default_settings.dict().items():
        setattr(existing_settings, key, value)

    await db.commit()
    await db.refresh(existing_settings)
    return CustomerProvisioningDefaultSettingsResponse(
        message="Customer Provisioning Default Settings updated successfully",
        success=True,
        customer_provisioning_default_settings=existing_settings,
    )


@customer_provisioning_default_settings_router.delete(
    "/default_settings",
    response_model=CustomerProvisioningDefaultSettingsResponse,
    description="Delete default settings for customer provisioning",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def delete_customer_provisioning_default_settings(
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CustomerProvisioningDefaultSettings)
    result = await db.execute(stmt)
    existing_settings = result.scalars().first()

    if not existing_settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    await db.delete(existing_settings)
    await db.commit()
    return CustomerProvisioningDefaultSettingsResponse(
        message="Customer Provisioning Default Settings deleted successfully",
        success=True,
        customer_provisioning_default_settings=existing_settings,
    )

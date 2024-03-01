from datetime import datetime as dt
from typing import Any
from typing import List
from loguru import logger
from typing import Optional
from licensing.models import *
from licensing.methods import Key, Helpers
from app.db.universal_models import License
from sqlalchemy import select
import os

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from pydantic import BaseModel, Field
from app.db.db_session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

class CreateLicenseRequest(BaseModel):
    """
    A Pydantic model for creating a license.

    Attributes:
        product_id (int): The product id.
        notes (str): The notes.
        new_customer (bool): Whether the customer is new.
        name (str): The customer name.
        email (str): The customer email.
        company_name (str): The customer company name.
    """
    product_id: int = Field(24355, title="The product id")
    notes: str = Field("Test Key", title="The notes")
    new_customer: bool = Field(True, title="Whether the customer is new")
    name: str = Field("Test Customer", title="The customer name")
    email: str = Field(..., title="The customer email")
    company_name: str = Field("Test Company", title="The customer company name")

class CreateCustomerKeyResult(BaseModel):
    customerId: int
    key: str
    result: int
    message: Optional[str]

class CreateCustomerKeyResponseModel(BaseModel):
    response: List[Optional[CreateCustomerKeyResult]]

class Customer(BaseModel):
    Id: int
    Name: str
    Email: str
    CompanyName: str
    Created: int

class RawResponse(BaseModel):
    license_key: str
    signature: str
    result: int
    message: str
    metadata: Optional[Any]

class LicenseResponse(BaseModel):
    product_id: int
    id: int
    key: str
    created: dt
    expires: dt
    period: int
    f1: bool
    f2: bool
    f3: bool
    f4: bool
    f5: bool
    f6: bool
    f7: bool
    f8: bool
    notes: str
    block: bool
    global_id: int
    customer: Customer
    activated_machines: List
    trial_activation: bool
    max_no_of_machines: int
    allowed_machines: Optional[Any]
    data_objects: List
    sign_date: dt
    reseller: Optional[Any]

license_router = APIRouter()

async def check_if_license_exists(session: AsyncSession):
    # Get the first row and raise HTTPException stating license already exists
    result = await session.execute(select(License))
    license = result.scalars().first()
    logger.info(f"License: {license}")
    if license:
        raise HTTPException(status_code=400, detail="License already exists")


def get_auth_token():
    auth = os.getenv("CRYPTOLENS_AUTH")
    if not auth:
        raise HTTPException(status_code=500, detail="Auth token not found")
    return auth

def get_rsa_pub_key():
    return "<RSAKeyValue><Modulus>vJusFdHoph6IyVrUnL7E3kH5YKsBdnIN5k+rW6J0g7gFPy7wBJfSDCtUMxB7XcOKiC1aZu/Wt7ShdzYsmYcd/duu4+qIMfP4CbW6RPIBFyj1Tk6xj72zKqU42sUymzzVVIeCtNdV0fkTdEZtI1zJeSXPcWtyY4PWOV1mFG9PST6uCuNDC+mXVESDyYHwd7JU8ZHDCEYD2eDJ4/58kT+jNpobS2BeRc4GMNPwISK/BNQG62X2sFJUWv7gB+qGXd/zqmucKEnB7Y1RyIVgnQPXKI/nrdoFHxRcUtEjhBMeqAQB0R8QvrMmlx1B7HzR+KBARTJdiPBrwxbopvhJus6c6Q==</Modulus><Exponent>AQAB</Exponent></RSAKeyValue>"

def get_product_id():
    return 24355

def create_key(auth, request):
    result, _ = Key.create_key(
        token=auth,
        product_id=request.product_id,
        period=365,
        notes=request.notes,
        new_customer=request.new_customer,
        name=request.name,
        email=request.email,
        company_name=request.company_name,
    )
    logger.info(result)
    result = CreateCustomerKeyResponseModel(response=[result])
    return result

async def add_license_to_db(session: AsyncSession, result, request):
    new_license = License(
        license_key=result.response[0].key,
        customer_name=request.name,
        customer_email=request.email,
        company_name=request.company_name,
    )
    logger.info(f"Adding new license: {new_license} to the database")
    session.add(new_license)
    await session.commit()
    return new_license

async def get_license(session: AsyncSession) -> License:
    result = await session.execute(select(License))
    license = result.scalars().first()
    if not license:
        raise HTTPException(status_code=404, detail="No license found")
    return license

def check_license(license: License):
    result, _ = Key.activate(
        token=get_auth_token(),
        rsa_pub_key=get_rsa_pub_key(),
        product_id=get_product_id(),
        key=license.license_key,
        machine_code=Helpers.GetMachineCode(v=2),
    )
    return result

def is_license_expired(license: dict) -> bool:
    """
    Check if a license is expired.

    Args:
        license (dict): The license to check.

    Returns:
        bool: True if the license is expired, False otherwise.
    """
    return dt.now() > license['expires']

@license_router.post(
    "/create_new_key",
    description="Create a new license key",
)
async def create_new_license_key(request: CreateLicenseRequest, session: AsyncSession = Depends(get_db)):
    """
    Create a new license key.

    Args:
        license_key (str): The license key to verify.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        LicenseVerificationResponse: A Pydantic model containing the verification status and message.
    """
    await check_if_license_exists(session)
    auth = get_auth_token()
    result = create_key(auth, request)
    await add_license_to_db(session, result, request)
    return result

@license_router.get(
    "/verify_license",
    response_model=LicenseResponse,
    description="Verify a license key",
)
async def verify_license_key(session: AsyncSession = Depends(get_db)) -> LicenseResponse:
    """"
    Verify a license key.

    Args:
        license_key (str): The license key to verify.

    Returns:
        LicenseVerificationResponse: A Pydantic model containing the verification status and message.
    """
    try:
        license = await get_license(session)
        result = check_license(license)
        result = result.__dict__
        if is_license_expired(result):
            raise HTTPException(status_code=400, detail="License is expired")
        return result
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail="License verification failed")


import os
from datetime import datetime as dt
from enum import Enum
from typing import Any
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from licensing.methods import Data
from licensing.methods import Helpers
from licensing.methods import Key

# from licensing.models import *
from loguru import logger
from pydantic import BaseModel
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_session import get_db
from app.db.universal_models import License


class ReplaceLicenseRequest(BaseModel):
    """
    A Pydantic model for replacing a license.

    Attributes:
        license_key (str): The license key to replace.
    """

    license_key: str = Field(..., title="The license key to replace")


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
    success: bool = Field(..., title="Indicates if the key creation was successful")
    message: str = Field(..., title="The message")


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

class VerifyLicenseResponse(BaseModel):
    license: LicenseResponse
    success: bool
    message: str

class GetLicenseResponse(BaseModel):
    license_key: str
    success: bool
    message: str

class GetLicenseFeaturesResponse(BaseModel):
    features: List[str]
    success: bool
    message: str

class Feature(Enum):
    MIMECAST = "MIMECAST"
    SAP_SIEM = "SAP SIEM"
    HUNTRESS = "HUNTRESS"
    REPORTING = "REPORTING"
    # Add more features as needed

    @classmethod
    def get_feature_name(cls, feature_name):
        feature_map = {
            cls.MIMECAST.value: "MIMECAST",
            cls.SAP_SIEM.value: "SAP SIEM",
            cls.HUNTRESS.value: "HUNTRESS",
            cls.REPORTING.value: "REPORTING",
            # Add more mappings as needed
        }
        return feature_map.get(feature_name)

class SubscriptionCatalog(str, Enum):
    """
    The subscription catalog.
    """

    MIMECAST = (
        "Integrate your SIEM stack with Mimecast to detect and respond to advanced threats."
        "This integration includes ingesting of Mimecast logs into your SIEM stack, Grafana dashboards,"
        "and alerts for advanced threat detection.",
    )
    HUNTRESS = (
        "Integrate your SIEM stack with Huntress to detect and respond to advanced threats."
    )



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
    rsa_public_key = os.getenv("RSA_PUBLIC_KEY")
    if not rsa_public_key:
        raise HTTPException(status_code=500, detail="RSA public key not found")
    return rsa_public_key


def get_product_id():
    product_id = os.getenv("PRODUCT_ID")
    if not product_id:
        raise HTTPException(status_code=500, detail="Product id not found")
    return product_id


def create_trial_key(auth, request):
    result, _ = Key.create_key(
        token=auth,
        product_id=request.product_id,
        period=7,
        notes=request.notes,
        new_customer=request.new_customer,
        name=request.name,
        email=request.email,
        company_name=request.company_name,
    )
    logger.info(result)
    result = CreateCustomerKeyResponseModel(response=[result])
    return result


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
    try:
        result = await session.execute(select(License))
        license = result.scalars().first()
        if not license:
            raise HTTPException(status_code=404, detail="No license found")
        return license
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=404, detail="No license found")

def check_license(license: License):
    logger.info(f"Checking license: {license}")
    result, _ = Key.activate(
        token=get_auth_token(),
        rsa_pub_key=get_rsa_pub_key(),
        product_id=get_product_id(),
        key=license.license_key,
        machine_code=Helpers.GetMachineCode(v=2),
    )
    return result


def extend_license(license: License, period: int):
    result, _ = Key.extend_license(
        token=get_auth_token(),
        product_id=get_product_id(),
        key=license.license_key,
        no_of_days=period,
    )
    logger.info(result)
    return result


def is_license_expired(license: dict) -> bool:
    """
    Check if a license is expired.

    Args:
        license (dict): The license to check.

    Returns:
        bool: True if the license is expired, False otherwise.
    """
    return dt.now() > license["expires"]


async def is_feature_enabled(feature_name: str, session: AsyncSession) -> bool:
    """
    Check if a feature is enabled in a license.

    Args:
        license (License): The license to check.
        feature_name (str): The feature name to check.
        session (AsyncSession): The database session.

    Returns:
        bool: True if the feature is enabled, False otherwise.
    """
    license = await get_license(session)
    license_details = LicenseResponse(**check_license(license).__dict__)
    for data_object in license_details.data_objects:
        if data_object["Name"] == feature_name and data_object["IntValue"] == 1:
            return True

    raise HTTPException(status_code=400, detail="Feature not enabled. You must purchase a license to use this feature.")


@license_router.post(
    "/create_trial_key",
    description="Create a trial license key",
)
async def create_trial_license_key(request: CreateLicenseRequest, session: AsyncSession = Depends(get_db)):
    """
    Create a trial license key.

    Args:
        request (CreateLicenseRequest): The request containing the license key to create.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        LicenseVerificationResponse: A Pydantic model containing the verification status and message.
    """
    await check_if_license_exists(session)
    auth = get_auth_token()
    result = create_trial_key(auth, request)
    await add_license_to_db(session, result, request)
    return result


@license_router.post(
    "/create_new_key",
    response_model=CreateCustomerKeyResponseModel,
    description="Create a new license key",
)
async def create_new_license_key(request: CreateLicenseRequest, session: AsyncSession = Depends(get_db)) -> CreateCustomerKeyResponseModel:
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
    return CreateCustomerKeyResponseModel(response=result.response, success=True, message="License created successfully")


@license_router.post(
    "/extend_license",
    description="Extend a license",
)
async def extend_license_key(period: int, session: AsyncSession = Depends(get_db)):
    """
    Extend a license key.

    Args:
        period (int): The period to extend the license by.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        LicenseVerificationResponse: A Pydantic model containing the verification status and message.
    """
    try:
        license = await get_license(session)
        logger.info(f"License: {license}")
        result = extend_license(license, period)
        return {"message": "License extended successfully", "success": True}
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail="License extension failed")


@license_router.get(
    "/verify_license",
    response_model=VerifyLicenseResponse,
    description="Verify a license key",
)
async def verify_license_key(session: AsyncSession = Depends(get_db)) -> VerifyLicenseResponse:
    """ "
    Verify a license key.

    Args:
        license_key (str): The license key to verify.

    Returns:
        LicenseVerificationResponse: A Pydantic model containing the verification status and message.
    """
    license = await get_license(session)
    try:
        logger.info(f"License: {license}")
        result = check_license(license)
        result = result.__dict__
        logger.info(result)
        if is_license_expired(result):
            raise HTTPException(status_code=400, detail="License is expired")
        return VerifyLicenseResponse(license=result, success=True, message="License verified successfully")
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail="License verification failed")

@license_router.get(
    "/get_license",
    description="Get a license",
)
async def get_license_key(session: AsyncSession = Depends(get_db)) -> GetLicenseResponse:
    """ "
    Get a license key.

    Args:
        license_key (str): The license key to verify.

    Returns:
        LicenseVerificationResponse: A Pydantic model containing the verification status and message.
    """
    license = await get_license(session)
    return GetLicenseResponse(license_key=license.license_key, success=True, message="License retrieved successfully")

@license_router.get(
    "/get_license_features",
    response_model=GetLicenseFeaturesResponse,
    description="Get license features",
)
async def get_license_features(session: AsyncSession = Depends(get_db)) -> GetLicenseFeaturesResponse:
    """
    Get the features enabled in a license.

    Args:
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        dict: A dictionary containing the features enabled in the license.
    """
    license = await get_license(session)
    try:
        license_details = LicenseResponse(**check_license(license).__dict__)
        features = {}
        for data_object in license_details.data_objects:
            features[data_object["Name"]] = data_object["IntValue"]
        return GetLicenseFeaturesResponse(
            features=[feature for feature, value in features.items() if value == 1],
            success=True,
            message="License features retrieved successfully",
        )
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail="Failed to get license features")


@license_router.post(
    "/add_feature/{feature_name}",
    description="Add a feature to a license",
)
async def add_feature_to_license(feature_name: str, session: AsyncSession = Depends(get_db)):
    """
    Add a feature to a license.

    Args:
        feature_name (str): The feature name to add.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        LicenseVerificationResponse: A Pydantic model containing the verification status and message.
    """
    logger.info(f"Adding feature: {feature_name} to license")
    # Check if the feature name is valid
    feature_name = Feature.get_feature_name(feature_name)
    if feature_name is None:
        logger.error("Invalid feature name")
        raise HTTPException(status_code=400, detail="Invalid feature name")
    try:
        license = await get_license(session)
        logger.info(f"License: {license}")
        result, _ = Data.add_data_object_to_key(
            token=get_auth_token(),
            product_id=get_product_id(),
            key=license.license_key,
            name=feature_name,
            string_value=f"[{feature_name}]",
            check_for_duplicates=True,
            int_value=1,
        )
        logger.info(result)
        return result
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail="Feature addition failed")


@license_router.post(
    "/replace_license_in_db",
    description="Replace a license",
)
async def replace_license_in_db(request: ReplaceLicenseRequest, session: AsyncSession = Depends(get_db)):
    """
    Replace a license in the database.

    Args:
        request (ReplaceLicenseRequest): The request containing the license key to replace.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        LicenseVerificationResponse: A Pydantic model containing the verification status and message.
    """
    try:
        # Update the license in the database
        result = await session.execute(select(License))
        license = result.scalars().first()
        if not license:
            raise HTTPException(status_code=404, detail="No license found")
        license.license_key = request.license_key
        await session.commit()
        return {"message": "License replaced successfully", "success": True}
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail="License replacement failed")

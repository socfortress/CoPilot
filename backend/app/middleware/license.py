import os
from datetime import datetime as dt
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import requests
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger
from pydantic import BaseModel
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.schema import UpdateConnector
from app.connectors.services import ConnectorServices
from app.db.db_session import get_db
from app.db.universal_models import License


class ThreatIntelRegisterRequest(BaseModel):
    """
    A Pydantic model for registering to the SOCFortress Threat Intel Feed which
        requires a valid API key.
    """

    customer_name: str = Field(..., description="The customer name")
    requested_by: str = Field("CoPilot", description="The system requesting access")
    registration_url: str = Field("https://intel.socfortress.co/register", description="The registration URL")
    requesting_api_key: str = Field(os.getenv("COPILOT_API_KEY"), description="The requesting API key")


class ThreatIntelRegisterResponse(BaseModel):
    """
    A Pydantic model for the response to registering to the SOCFortress Threat Intel Feed.
    """

    api_key: str = Field(..., description="The API key")
    success: bool = Field(..., description="Indicates if the registration was successful")
    message: str = Field(..., description="The message")


class ReplaceLicenseRequest(BaseModel):
    """
    A Pydantic model for replacing a license.

    Attributes:
        license_key (str): The license key to replace.
    """

    license_key: str = Field(..., title="The license key to replace")


class TrialLicenseRequest(BaseModel):
    period: Optional[int] = Field(7, title="The period of the trial license")
    email: str = Field(..., title="The email of the user")
    feature_name: str = Field(..., title="The feature name")
    customer_name: str = Field(..., title="The customer name")
    company_name: str = Field(..., title="The company name")


class TrialLicenseResponse(BaseModel):
    license_key: str
    success: bool
    message: str


class CreateCustomerKeyResult(BaseModel):
    customerId: int
    key: str
    result: int
    message: Optional[str]


class CreateCustomerKeyResponseModel(BaseModel):
    response: List[Optional[CreateCustomerKeyResult]]


class CreateCustomerKeyRouteResponse(BaseModel):
    response: List[Optional[CreateCustomerKeyResult]]
    success: bool = Field(..., title="Indicates if the key creation was successful")
    message: str = Field(..., title="The message")


class Customer(BaseModel):
    id: int
    name: str
    email: str
    companyName: str
    created: dt


class RawResponse(BaseModel):
    license_key: str
    signature: str
    result: int
    message: str
    metadata: Optional[Any]


class LicenseResponse(BaseModel):
    productId: int
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
    globalId: int
    customer: Customer
    activatedMachines: List
    trialActivation: bool
    maxNoOfMachines: int
    allowedMachines: Optional[Any]
    dataObjects: List
    signDate: dt
    reseller: Optional[Any] = None


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


class IsFeatureEnabledResponse(BaseModel):
    enabled: bool
    success: bool
    message: str


class Feature(BaseModel):
    id: int
    subscription_price_id: str
    name: str
    price: int
    currency: str
    info: str
    short_description: str
    full_description: str


class GetSubscriptionCatalogFeaturesResponse(BaseModel):
    features: List[Feature]
    success: bool
    message: str


class FeatureSubscriptionRequest(BaseModel):
    feature_id: int = Field(..., example=1)
    cancel_url: str = Field(..., example="https://example.com/cancel")
    success_url: str = Field(..., example="https://example.com/success")
    customer_email: str = Field(..., example="info@socfortress.co")
    company_name: str = Field(..., example="SOCFORTRESS")


class GetLicenseByEmailRequest(BaseModel):
    email: str = Field(..., example="info@socfortress.co")


class AddLicenseToDB(BaseModel):
    customer_name: str
    customer_email: str
    company_name: str


###### ! CREATE SESSION CHECKOUT ! ######
class AutomaticTax(BaseModel):
    enabled: bool
    liability: Optional[str] = None
    status: Optional[str] = None


class CustomText(BaseModel):
    after_submit: Optional[str] = None
    shipping_address: Optional[str] = None
    submit: Optional[str] = None
    terms_of_service_acceptance: Optional[str] = None


class InvoiceData(BaseModel):
    account_tax_ids: Optional[str] = None
    custom_fields: Optional[str] = None
    description: Optional[str] = None
    footer: Optional[str] = None
    issuer: Optional[str] = None
    metadata: Dict = {}
    rendering_options: Optional[str] = None


class InvoiceCreation(BaseModel):
    enabled: bool
    invoice_data: InvoiceData


class PaymentMethodOptionsCard(BaseModel):
    request_three_d_secure: str


class PaymentMethodOptions(BaseModel):
    card: PaymentMethodOptionsCard


class PhoneNumberCollection(BaseModel):
    enabled: bool


class TotalDetails(BaseModel):
    amount_discount: int
    amount_shipping: int
    amount_tax: int


class CustomerDetails(BaseModel):
    address: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    tax_exempt: Optional[str] = None
    tax_ids: Optional[str] = None


class CheckoutSession(BaseModel):
    after_expiration: Optional[str] = None
    allow_promotion_codes: Optional[str] = None
    amount_subtotal: int
    amount_total: int
    automatic_tax: AutomaticTax
    billing_address_collection: Optional[str] = None
    cancel_url: str
    client_reference_id: Optional[str] = None
    client_secret: Optional[str] = None
    consent: Optional[str] = None
    consent_collection: Optional[str] = None
    created: int
    currency: str
    currency_conversion: Optional[str] = None
    custom_fields: List = []
    custom_text: CustomText
    customer: Optional[str] = None
    customer_creation: Optional[str] = None
    customer_details: Optional[CustomerDetails] = None
    customer_email: Optional[str] = None
    expires_at: int
    id: str
    invoice: Optional[str] = None
    invoice_creation: Optional[InvoiceCreation] = None
    livemode: bool
    locale: Optional[str] = None
    metadata: Dict
    mode: str
    object: str
    payment_intent: Optional[str] = None
    payment_link: Optional[str] = None
    payment_method_collection: str
    payment_method_configuration_details: Optional[str] = None
    payment_method_options: PaymentMethodOptions
    payment_method_types: List[str]
    payment_status: str
    phone_number_collection: PhoneNumberCollection
    recovered_from: Optional[str] = None
    setup_intent: Optional[str] = None
    shipping_address_collection: Optional[str] = None
    shipping_cost: Optional[str] = None
    shipping_details: Optional[str] = None
    shipping_options: List = []
    status: str
    submit_type: Optional[str] = None
    subscription: Optional[str] = None
    success_url: str
    total_details: TotalDetails
    ui_mode: str
    url: str


class CheckoutSessionResponse(BaseModel):
    success: bool = True
    message: str = "Checkout session created successfully"
    session: CheckoutSession


class CancelSubscriptionRequest(BaseModel):
    customer_email: str
    subscription_price_id: str
    feature_name: str


class CancelSubscriptionResponse(BaseModel):
    success: bool
    message: str


class RetrieveDockerCompose(BaseModel):
    docker_compose: str
    success: bool
    message: str


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


async def add_license_to_db(session: AsyncSession, result, request: AddLicenseToDB):
    """
    Add a new license to the database.

    :param session: AsyncSession object for the database session
    :param result: The license key to be added
    :param request: The request object containing customer details
    :return: The newly added License object
    """

    new_license = License(
        license_key=result,
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        company_name=request.company_name,
    )

    logger.info(f"Adding new license: {new_license} to the database")
    session.add(new_license)
    await session.commit()
    return new_license


async def get_license(session: AsyncSession) -> License:
    """
    Get the license from the database

    :param session: The AsyncSession object for the database
    :return: The License object
    """
    result = await session.execute(select(License))
    license = result.scalars().first()
    if license is None:
        raise HTTPException(status_code=404, detail="No license found")
    else:
        return license


def is_license_expired(license: dict) -> bool:
    """
    Check if a license is expired.

    Args:
        license (dict): The license to check.

    Returns:
        bool: True if the license is expired, False otherwise.
    """
    logger.info(f"License: {license}")
    expires = dt.strptime(license["data"]["license"]["expires"], "%Y-%m-%dT%H:%M:%S.%f")
    return dt.now() > expires


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
    result = await send_post_request("verify-license", data={"license_key": license.license_key})
    for data_object in result["data"]["license"]["dataObjects"]:
        if data_object["name"] == feature_name and data_object["intValue"] == 1:
            return True

    raise HTTPException(status_code=400, detail="Feature not enabled. You must purchase a license to use this feature.")


async def send_get_request(endpoint: str) -> Dict[str, Any]:
    """
    Sends a GET request to the Shuffle service.

    Args:
        endpoint (str): The endpoint to send the GET request to.

    Returns:
        Dict[str, Any]: The response from the GET request.
    """
    logger.info(f"Sending GET request to {endpoint}")

    try:
        HEADERS = {
            "x-api-key": f"{os.getenv('COPILOT_API_KEY')}",
            "Content-Type": "application/json",
            "module-version": "1.0",
        }
        response = requests.get(
            f"https://license.socfortress.co/{endpoint}",
            headers=HEADERS,
            verify=False,
        )

        if response.status_code == 204:
            return {
                "data": None,
                "success": True,
                "message": "Successfully completed request with no content",
            }
        else:
            return {
                "data": response.json(),
                "success": False if response.status_code >= 400 else True,
                "message": "Successfully retrieved data",
            }
    except Exception as e:
        logger.error(f"Failed to send GET request to {endpoint} with error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send GET request to {endpoint} with error: {e}",
        )


@license_router.get(
    "/subscription_features",
    description="Get the subscription features available",
    response_model=GetSubscriptionCatalogFeaturesResponse,
)
async def get_subscription_catalog():
    """
    Get the subscription catalog. This is handled by the Middleware running in SOCFortress Infra

    Returns:
        dict: A dictionary containing the subscription catalog.
    """
    try:
        results = await send_get_request("features")
        return GetSubscriptionCatalogFeaturesResponse(
            features=results["data"]["features"],
            success=results["success"],
            message=results["message"],
        )
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail="Failed to get subscription features")


@license_router.post(
    "/retrieve_license_by_email",
    description="Retrieve a license by email",
    response_model=GetLicenseResponse,
)
async def retrieve_license_by_email(request: GetLicenseByEmailRequest, session: AsyncSession = Depends(get_db)) -> GetLicenseResponse:
    """
    Retrieve a license by email.

    Args:
        request (GetLicenseRequest): The request containing the email to retrieve the license by.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        GetLicenseResponse: A Pydantic model containing the license key, success status, and message.
    """
    # Check if a license with the given email already exists in the database
    result = await session.execute(select(License).where(License.customer_email == request.email))
    existing_license = result.scalars().first()
    if existing_license:
        return GetLicenseResponse(
            license_key=existing_license.license_key,
            success=True,
            message="License retrieved successfully",
        )

    results = await send_post_request("retrieve-license-by-email", data={"email": request.email})
    logger.info(f"Results: {results}")
    if results["data"]["success"] is False:
        raise HTTPException(status_code=400, detail=f"Failed to retrieve license by email: {results['data']['message']}")

    # Add the license to the database
    await add_license_to_db(
        session,
        results["data"]["license"]["key"],
        AddLicenseToDB(
            customer_email=results["data"]["license"]["customer"]["email"],
            customer_name=results["data"]["license"]["customer"]["name"],
            company_name=results["data"]["license"]["customer"]["companyName"],
        ),
    )
    return GetLicenseResponse(
        license_key=results["data"]["license"]["key"],
        success=results["data"]["success"],
        message=results["data"]["message"],
    )


@license_router.post(
    "/create_checkout_session",
    description="Create a checkout session",
    response_model=CheckoutSessionResponse,
)
async def create_checkout_session(request: FeatureSubscriptionRequest):
    """
    Create a checkout session.

    Args:
        request (FeatureSubscriptionRequest): The request containing the feature id and user id.

    Returns:
        dict: A dictionary containing the checkout session.
    """
    results = await send_post_request(
        "create-checkout-session",
        data={
            "feature_id": request.feature_id,
            "cancel_url": request.cancel_url,
            "success_url": request.success_url,
            "customer_email": request.customer_email,
            "company_name": request.company_name,
        },
    )
    logger.info(f"Results: {results}")
    if results["data"]["success"] is False:
        raise HTTPException(status_code=400, detail=f"Failed to create checkout session: {results['data']['message']}")
    return CheckoutSessionResponse(
        session=results["data"]["session"],
        success=results["data"]["success"],
        message=results["data"]["message"],
    )


@license_router.post(
    "/trial_license",
    description="Create a trial license",
    response_model=TrialLicenseResponse,
)
async def create_trial_license_key(request: TrialLicenseRequest, session: AsyncSession = Depends(get_db)) -> TrialLicenseResponse:
    """
    Create a trial license key.

    Args:
        request (CreateLicenseRequest): The request containing the license key to create.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        LicenseVerificationResponse: A Pydantic model containing the verification status and message.
    """
    await check_if_license_exists(session)
    results = await send_post_request(
        "trial-license",
        data={
            "email": request.email,
            "feature_name": request.feature_name,
            "customer_name": request.customer_name,
            "period": request.period,
            "company_name": request.company_name,
        },
    )
    logger.info(f"Results: {results}")
    if results["data"]["success"] is False:
        raise HTTPException(status_code=400, detail=f"Failed to create trial license: {results['data']['message']}")
    await add_license_to_db(
        session,
        results["data"]["license_key"],
        AddLicenseToDB(
            customer_email=request.email,
            customer_name=request.customer_name,
            company_name=request.company_name,
        ),
    )
    return TrialLicenseResponse(
        license_key=results["data"]["license_key"],
        success=results["data"]["success"],
        message=results["data"]["message"],
    )


@license_router.post(
    "/cancel_subscription",
    description="Cancel a subscription",
    response_model=CancelSubscriptionResponse,
)
async def cancel_subscription(request: CancelSubscriptionRequest) -> CancelSubscriptionResponse:
    """
    Cancel a subscription.

    Args:
        request (CancelSubscriptionRequest): The request containing the customer email, subscription price id, and feature name.

    Returns:
        dict: A dictionary containing the cancellation status.
    """
    results = await send_post_request(
        "cancel-subscription",
        data={
            "customer_email": request.customer_email,
            "subscription_price_id": request.subscription_price_id,
            "feature_name": request.feature_name,
        },
    )
    logger.info(f"Results: {results}")
    if results["data"]["success"] is False:
        raise HTTPException(status_code=400, detail=f"Failed to cancel subscription: {results['data']['message']}")
    return CancelSubscriptionResponse(
        success=results["data"]["success"],
        message=results["data"]["message"],
    )


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
        result = await send_post_request("verify-license", data={"license_key": license.license_key})
        if is_license_expired(result):
            raise HTTPException(status_code=400, detail="License is expired")
        return VerifyLicenseResponse(license=result["data"]["license"], success=True, message="License verified successfully")
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


async def send_post_request(endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Sends a POST request to the Shuffle service.

    Args:
        endpoint (str): The endpoint to send the POST request to.
        data (Dict[str, Any]): The data to send with the POST request.
        connector_name (str, optional): The name of the connector to use. Defaults to "Shuffle".

    Returns:
        Dict[str, Any]: The response from the POST request.
    """
    logger.info(f"Sending POST request to {endpoint}")

    try:
        HEADERS = {
            "x-api-key": f"{os.getenv('COPILOT_API_KEY')}",
            "Content-Type": "application/json",
            "module-version": "1.0",
        }
        response = requests.post(
            f"https://license.socfortress.co/{endpoint}",
            headers=HEADERS,
            json=data,
            verify=False,
        )

        if response.status_code == 200:
            return {
                "data": response.json(),
                "success": True,
                "message": "Successfully retrieved data",
            }
        else:
            return {
                "success": False,
                "message": f"Failed to send POST request to {endpoint}",
            }
    except Exception as e:
        logger.error(f"Failed to send POST request to {endpoint} with error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send POST request to {endpoint} with error: {e}",
        )


@license_router.get(
    "/is_feature_enabled/{feature_name}",
    response_model=IsFeatureEnabledResponse,
    description="Check if a feature is enabled in a license",
)
async def is_feature_enabled_route(feature_name: str, session: AsyncSession = Depends(get_db)) -> IsFeatureEnabledResponse:
    """
    Check if a feature is enabled in a license.

    Args:
        feature_name (str): The feature name to check.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        bool: True if the feature is enabled, False otherwise.
    """
    if await is_feature_enabled(feature_name, session):
        return IsFeatureEnabledResponse(
            enabled=True,
            success=True,
            message="Feature is enabled",
        )
    else:
        return IsFeatureEnabledResponse(
            enabled=False,
            success=True,
            message="Feature is not enabled",
        )


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
        results = await send_post_request("license-features", data={"license_key": license.license_key})
        return GetLicenseFeaturesResponse(
            features=results["data"]["features"],
            success=results["success"],
            message=results["message"],
        )
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail="Failed to get license features")


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
            # Verify the license key
            license_data = await send_post_request("verify-license", data={"license_key": request.license_key})
            if is_license_expired(license_data):
                raise HTTPException(status_code=400, detail="License is expired")
            # Create a new License object with the data from the dictionary
            license = License(
                license_key=license_data["data"]["license"]["key"],
                customer_name=license_data["data"]["license"]["customer"]["name"],
                customer_email=license_data["data"]["license"]["customer"]["email"],
                company_name=license_data["data"]["license"]["customer"]["companyName"],
            )
            session.add(license)
        license.license_key = request.license_key
        await session.commit()
        return {"message": "License replaced successfully", "success": True}
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail="License replacement failed")


@license_router.post(
    "/retrieve-docker-compose",
    response_model=RetrieveDockerCompose,
    description="Retrieve Docker Compose for features enabled",
)
async def retrieve_docker_compose(session: AsyncSession = Depends(get_db)) -> RetrieveDockerCompose:
    """
    Retrieve the Docker Compose for features enabled in the license.

    Args:
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        RetrieveDockerCompose: A Pydantic model containing the Docker Compose for features enabled.
    """
    try:
        license = await get_license(session)
        if license.license_key:
            results = await send_post_request("retrieve-docker-compose", data={"license_key": license.license_key})
            logger.info(f"Results: {results}")
            return RetrieveDockerCompose(
                docker_compose=results["data"]["docker_compose"],
                success=results["success"],
                message=results["message"],
            )
        else:
            return RetrieveDockerCompose(
                docker_compose="",
                success=False,
                message="License key not found",
            )
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail="Failed to retrieve Docker Compose")


def create_headers(request: ThreatIntelRegisterRequest) -> Dict[str, str]:
    return {
        "x-api-key": request.requesting_api_key,
        "Content-Type": "application/json",
        "module": "1.0",
        "SOCFortress_Threat_Intel": "c1f882d9-cd09-4f9c-81a6-71fe0fb53129",
    }


def create_payload(request: ThreatIntelRegisterRequest) -> Dict[str, str]:
    return {
        "customer_name": request.customer_name,
        "requested_by": request.requested_by,
    }


async def update_connector(response: ThreatIntelRegisterResponse, session: AsyncSession):
    """
    When Threat Intel is purchased, add the API key to the connector.
    """
    await ConnectorServices.update_connector_by_id(
        connector_id=10,
        connector=UpdateConnector(
            connector_api_key=response.api_key,
            connector_url="https://intel.socfortress.co/search",
        ),
        session=session,
    )

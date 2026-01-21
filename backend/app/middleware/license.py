import json
import os
from datetime import datetime as dt
from datetime import timedelta
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
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.schema import UpdateConnector
from app.connectors.services import ConnectorServices
from app.db.db_session import get_db
from app.db.universal_models import License
from app.db.universal_models import LicenseCache


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

# Cache duration in hours
CACHE_DURATION_HOURS = 1


def normalize_api_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize API responses to handle different response structures.
    Some endpoints return data wrapped in 'data' key, others don't.

    Args:
        response: Raw API response

    Returns:
        Normalized response with consistent structure
    """
    if "data" in response:
        # Response has data wrapper - return as is
        return response
    else:
        # Response doesn't have data wrapper - wrap it
        return {"data": response, "success": response.get("success", True), "message": response.get("message", "Success")}


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


async def get_license(session: AsyncSession, raise_on_missing: bool = True) -> Optional[License]:
    """
    Get the license from the database

    :param session: The AsyncSession object for the database
    :param raise_on_missing: If True, raise HTTPException when no license found. If False, return None.
    :return: The License object or None
    """
    result = await session.execute(select(License))
    license = result.scalars().first()
    if license is None:
        if raise_on_missing:
            raise HTTPException(status_code=404, detail="No license found. A license must be created first.")
        else:
            return None
    else:
        return license


async def get_cached_feature(session: AsyncSession, license_key: str, feature_name: str) -> Optional[LicenseCache]:
    """
    Get cached feature information if it exists and is not expired.

    Args:
        session: Database session
        license_key: The license key
        feature_name: The feature name to check

    Returns:
        LicenseCache object if valid cache exists, None otherwise
    """
    current_time = dt.utcnow()

    result = await session.execute(
        select(LicenseCache).where(
            LicenseCache.license_key == license_key,
            LicenseCache.feature_name == feature_name,
            LicenseCache.expires_at > current_time,
        ),
    )

    cached_feature = result.scalars().first()

    if cached_feature:
        logger.info(f"Found valid cache for feature '{feature_name}' (expires at {cached_feature.expires_at})")
        return cached_feature
    else:
        logger.info(f"No valid cache found for feature '{feature_name}'")
        return None


async def cache_license_features(session: AsyncSession, license_key: str, license_data: Dict[str, Any]) -> None:
    """
    Cache license features from license verification response.

    Args:
        session: Database session
        license_key: The license key
        license_data: The license verification response data
    """
    try:
        # Clear existing cache for this license key
        await session.execute(delete(LicenseCache).where(LicenseCache.license_key == license_key))

        current_time = dt.utcnow()
        expires_at = current_time + timedelta(hours=CACHE_DURATION_HOURS)

        # Store the full license data as JSON string for reference
        license_json = json.dumps(license_data)

        # Extract features from dataObjects - handle both response formats
        if "data" in license_data and "license" in license_data["data"]:
            # Wrapped format: {"data": {"license": {"dataObjects": [...]}}}
            data_objects = license_data["data"]["license"].get("dataObjects", [])
        elif "license" in license_data:
            # Direct format: {"license": {"dataObjects": [...]}}
            data_objects = license_data["license"].get("dataObjects", [])
        elif "dataObjects" in license_data:
            # Bare format: {"dataObjects": [...]}
            data_objects = license_data.get("dataObjects", [])
        else:
            logger.warning("Could not find dataObjects in license response")
            data_objects = []

        # Track which features we've processed
        processed_features = set()

        for data_object in data_objects:
            feature_name = data_object.get("name")
            is_enabled = data_object.get("intValue") == 1

            if feature_name:
                cache_entry = LicenseCache(
                    license_key=license_key,
                    feature_name=feature_name,
                    is_enabled=is_enabled,
                    cached_at=current_time,
                    expires_at=expires_at,
                    license_data=license_json,
                )

                session.add(cache_entry)
                processed_features.add(feature_name)

                logger.info(f"Cached feature '{feature_name}': {'enabled' if is_enabled else 'disabled'}")

        await session.commit()
        logger.info(f"Successfully cached {len(processed_features)} features for license {license_key[:8]}...")

    except Exception as e:
        logger.error(f"Error caching license features: {str(e)}")
        await session.rollback()
        raise


async def invalidate_license_cache(session: AsyncSession, license_key: str) -> None:
    """
    Invalidate (delete) all cached entries for a specific license key.

    Args:
        session: Database session
        license_key: The license key to invalidate cache for
    """
    try:
        result = await session.execute(delete(LicenseCache).where(LicenseCache.license_key == license_key))
        deleted_count = result.rowcount
        await session.commit()

        logger.info(f"Invalidated {deleted_count} cache entries for license {license_key[:8]}...")

    except Exception as e:
        logger.error(f"Error invalidating license cache: {str(e)}")
        await session.rollback()


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


async def is_feature_enabled(feature_name: str, session: AsyncSession, message: str = None) -> bool:
    """
    Check if a feature is enabled in a license.
    Uses cache first, falls back to API if cache miss or expired.

    Args:
        feature_name (str): The feature name to check.
        session (AsyncSession): The database session.
        message (str, optional): Custom error message.

    Returns:
        bool: True if the feature is enabled, False otherwise.
    """
    license = await get_license(session)

    # Check cache first
    cached_feature = await get_cached_feature(session, license.license_key, feature_name)

    if cached_feature:
        logger.info(f"Using cached result for feature '{feature_name}': {'enabled' if cached_feature.is_enabled else 'disabled'}")

        if cached_feature.is_enabled:
            return True
        else:
            # Feature is disabled according to cache
            if message:
                raise HTTPException(status_code=400, detail=message)
            raise HTTPException(
                status_code=400,
                detail=f"Feature is not enabled. You must purchase the {feature_name} license to use this feature.",
            )

    # Cache miss - fetch from API
    logger.info(f"Cache miss for feature '{feature_name}', fetching from API")

    try:
        result = await send_post_request("verify-license", data={"license_key": license.license_key})

        # Normalize response format
        normalized_result = normalize_api_response(result)

        # Cache the results
        await cache_license_features(session, license.license_key, normalized_result)

        # Check if feature is enabled
        data_objects = normalized_result["data"]["license"].get("dataObjects", [])
        for data_object in data_objects:
            if data_object["name"] == feature_name and data_object["intValue"] == 1:
                logger.info(f"Feature '{feature_name}' is enabled (from API)")
                return True

        # Feature not found or not enabled
        logger.info(f"Feature '{feature_name}' is not enabled (from API)")

        if message:
            raise HTTPException(status_code=400, detail=message)

        raise HTTPException(
            status_code=400,
            detail=f"Feature is not enabled. You must purchase the {feature_name} license to use this feature.",
        )

    except HTTPException:
        # Re-raise HTTP exceptions (like feature not enabled)
        raise
    except Exception as e:
        logger.error(f"Error verifying license from API: {str(e)}")
        # If API fails, we can't verify - raise an error
        raise HTTPException(status_code=500, detail=f"Unable to verify license: {str(e)}")


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
            timeout=10,
        )

        if response.status_code == 204:
            return {"success": True, "message": "No content"}
        else:
            return response.json()
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
        result = await send_get_request("features")
        normalized_result = normalize_api_response(result)

        # Handle different response structures for subscription features
        features = []
        if "data" in normalized_result and "features" in normalized_result["data"]:
            features = normalized_result["data"]["features"]
        elif "features" in normalized_result:
            features = normalized_result["features"]
        else:
            logger.warning(f"No features found in response: {normalized_result}")
            features = []

        return GetSubscriptionCatalogFeaturesResponse(
            features=features,
            success=normalized_result.get("success", True),
            message=normalized_result.get("message", "Subscription features retrieved successfully"),
        )
    except Exception as e:
        logger.error(f"Error getting subscription catalog: {str(e)}")
        return GetSubscriptionCatalogFeaturesResponse(
            features=[],
            success=False,
            message=f"Error getting subscription catalog: {str(e)}",
        )


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
            message="License already exists in database",
        )

    results = await send_post_request("retrieve-license-by-email", data={"email": request.email})
    normalized_results = normalize_api_response(results)
    logger.info(f"Results: {normalized_results}")
    if normalized_results["data"]["success"] is False:
        raise HTTPException(status_code=400, detail=normalized_results["data"]["message"])

    # Add the license to the database
    await add_license_to_db(
        session,
        normalized_results["data"]["license"]["key"],
        AddLicenseToDB(
            customer_email=normalized_results["data"]["license"]["customer"]["email"],
            customer_name=normalized_results["data"]["license"]["customer"]["name"],
            company_name=normalized_results["data"]["license"]["customer"]["companyName"],
        ),
    )
    return GetLicenseResponse(
        license_key=normalized_results["data"]["license"]["key"],
        success=normalized_results["data"]["success"],
        message=normalized_results["data"]["message"],
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
    normalized_results = normalize_api_response(results)
    logger.info(f"Results: {normalized_results}")
    if normalized_results["data"]["success"] is False:
        raise HTTPException(status_code=400, detail=normalized_results["data"]["message"])
    return CheckoutSessionResponse(
        session=normalized_results["data"]["session"],
        success=normalized_results["data"]["success"],
        message=normalized_results["data"]["message"],
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
            "period": request.period,
            "email": request.email,
            "feature_name": request.feature_name,
            "customer_name": request.customer_name,
            "company_name": request.company_name,
        },
    )
    normalized_results = normalize_api_response(results)
    logger.info(f"Results: {normalized_results}")
    if normalized_results["data"]["success"] is False:
        raise HTTPException(status_code=400, detail=normalized_results["data"]["message"])

    # Add the license to the database
    await add_license_to_db(
        session,
        normalized_results["data"]["license_key"],
        AddLicenseToDB(
            customer_email=request.email,
            customer_name=request.customer_name,
            company_name=request.company_name,
        ),
    )

    return TrialLicenseResponse(
        license_key=normalized_results["data"]["license_key"],
        success=normalized_results["data"]["success"],
        message=normalized_results["data"]["message"],
    )


@license_router.post(
    "/cancel_subscription",
    description="Cancel a subscription",
    response_model=CancelSubscriptionResponse,
)
async def cancel_subscription(request: CancelSubscriptionRequest) -> CancelSubscriptionResponse:
    results = await send_post_request(
        "cancel-subscription",
        data={
            "customer_email": request.customer_email,
            "subscription_price_id": request.subscription_price_id,
            "feature_name": request.feature_name,
        },
    )
    normalized_results = normalize_api_response(results)
    logger.info(f"Results: {normalized_results}")
    if normalized_results["data"]["success"] is False:
        raise HTTPException(status_code=400, detail=normalized_results["data"]["message"])
    return CancelSubscriptionResponse(
        success=normalized_results["data"]["success"],
        message=normalized_results["data"]["message"],
    )


@license_router.get(
    "/verify_license",
    response_model=VerifyLicenseResponse,
    description="Verify a license key",
)
async def verify_license_key(session: AsyncSession = Depends(get_db)) -> VerifyLicenseResponse:
    license = await get_license(session)

    # Check if we have a recent cache entry for any feature of this license
    current_time = dt.utcnow()
    result = await session.execute(
        select(LicenseCache).where(LicenseCache.license_key == license.license_key, LicenseCache.expires_at > current_time).limit(1),
    )

    cached_entry = result.scalars().first()

    if cached_entry and cached_entry.license_data:
        logger.info("Using cached license verification data")
        try:
            license_data = json.loads(cached_entry.license_data)
            # Handle both wrapped and unwrapped formats
            if "data" in license_data and "license" in license_data["data"]:
                license_obj = license_data["data"]["license"]
                success = license_data["data"]["success"]
            elif "license" in license_data:
                license_obj = license_data["license"]
                success = license_data.get("success", True)
            else:
                raise ValueError("Invalid cached license data format")

            return VerifyLicenseResponse(
                license=license_obj,
                success=success,
                message="License verified successfully (from cache)",
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Error parsing cached license data: {e}, falling back to API")

    # No valid cache, fetch from API
    logger.info("No valid cache found, verifying license via API")
    results = await send_post_request("verify-license", data={"license_key": license.license_key})

    # Normalize response format
    normalized_results = normalize_api_response(results)

    # Cache the results
    await cache_license_features(session, license.license_key, normalized_results)

    logger.info(f"Results: {normalized_results}")
    if not normalized_results.get("success", True):
        raise HTTPException(status_code=400, detail=normalized_results.get("message", "License verification failed"))

    # Handle both response formats for return value
    if "data" in normalized_results and "license" in normalized_results["data"]:
        license_obj = normalized_results["data"]["license"]
        success = normalized_results["data"]["success"]
        message = normalized_results["data"]["message"]
    else:
        license_obj = normalized_results["license"]
        success = normalized_results.get("success", True)
        message = normalized_results.get("message", "License verified successfully")

    return VerifyLicenseResponse(
        license=license_obj,
        success=success,
        message=message,
    )


@license_router.get(
    "/get_license",
    description="Get a license",
)
async def get_license_key(session: AsyncSession = Depends(get_db)) -> GetLicenseResponse:
    license = await get_license(session)
    return GetLicenseResponse(
        license_key=license.license_key,
        success=True,
        message="License retrieved successfully",
    )


async def send_post_request(endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Sends a POST request to the Shuffle service.

    Args:
        endpoint (str): The endpoint to send the POST request to.
        data (Dict[str, Any]): The data to send with the POST request.

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
            timeout=10,
        )

        if response.status_code == 204:
            return {"success": True, "message": "No content"}
        else:
            return response.json()
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
    try:
        await is_feature_enabled(feature_name, session)
        return IsFeatureEnabledResponse(
            enabled=True,
            success=True,
            message=f"Feature '{feature_name}' is enabled",
        )
    except HTTPException as e:
        if e.status_code == 400:  # Feature not enabled
            return IsFeatureEnabledResponse(
                status_code=400,
                message=e.detail,
            )
        else:
            raise


@license_router.get(
    "/get_license_features",
    response_model=GetLicenseFeaturesResponse,
    description="Get license features",
)
async def get_license_features(session: AsyncSession = Depends(get_db)) -> GetLicenseFeaturesResponse:
    license = await get_license(session)

    # Try to get features from cache first
    current_time = dt.utcnow()
    result = await session.execute(
        select(LicenseCache).where(
            LicenseCache.license_key == license.license_key,
            LicenseCache.expires_at > current_time,
            LicenseCache.is_enabled == True,
        ),
    )

    cached_features = result.scalars().all()

    if cached_features:
        logger.info(f"Using cached license features ({len(cached_features)} features)")
        features = [cache.feature_name for cache in cached_features]
        return GetLicenseFeaturesResponse(
            features=features,
            success=True,
            message="License features retrieved successfully (from cache)",
        )

    # No cache, fetch from API
    logger.info("No cached features found, fetching from API")
    results = await send_post_request("license-features", data={"license_key": license.license_key})

    # This endpoint returns features directly without data wrapper
    logger.info(f"Results: {results}")
    if not results.get("success", True):
        raise HTTPException(status_code=400, detail=results.get("message", "Failed to get license features"))

    # For license-features endpoint, create a fake normalized response to cache the features
    fake_license_data = {
        "data": {
            "license": {"dataObjects": [{"name": feature, "intValue": 1} for feature in results.get("features", [])]},
            "success": True,
        },
    }

    # Cache the results
    await cache_license_features(session, license.license_key, fake_license_data)

    return GetLicenseFeaturesResponse(
        features=results.get("features", []),
        success=results.get("success", True),
        message=results.get("message", "License features retrieved successfully"),
    )


@license_router.post(
    "/replace_license_in_db",
    description="Replace a license or create one if it doesn't exist",
)
async def replace_license_in_db(request: ReplaceLicenseRequest, session: AsyncSession = Depends(get_db)):
    # Get license without raising error if it doesn't exist
    license = await get_license(session, raise_on_missing=False)

    if license:
        # Existing license - replace it
        logger.info(f"Replacing existing license {license.license_key[:8]}... with {request.license_key[:8]}...")

        # Invalidate cache for old license
        await invalidate_license_cache(session, license.license_key)

        # Update license key
        license.license_key = request.license_key
        await session.commit()

        logger.info("License replaced successfully")
        return {"success": True, "message": "License replaced successfully"}
    else:
        # No existing license - create a new one
        logger.info("No existing license found, creating new license")

        # Verify the new license key first to get customer details
        results = await send_post_request("verify-license", data={"license_key": request.license_key})
        normalized_results = normalize_api_response(results)

        if not normalized_results.get("success", True):
            raise HTTPException(status_code=400, detail="Invalid license key")

        # Extract customer info from license verification
        license_data = normalized_results["data"]["license"]
        customer_data = license_data["customer"]

        # Create new license in database
        await add_license_to_db(
            session,
            request.license_key,
            AddLicenseToDB(
                customer_email=customer_data["email"],
                customer_name=customer_data["name"],
                company_name=customer_data["companyName"],
            ),
        )

        logger.info("License created successfully")
        return {"success": True, "message": "License created successfully"}


@license_router.post(
    "/retrieve-docker-compose",
    response_model=RetrieveDockerCompose,
    description="Retrieve Docker Compose for features enabled",
)
async def retrieve_docker_compose(session: AsyncSession = Depends(get_db)) -> RetrieveDockerCompose:
    license = await get_license(session)
    results = await send_post_request("retrieve-docker-compose", data={"license_key": license.license_key})

    # This endpoint returns data directly without wrapper
    logger.info(f"Results: {results}")
    if not results.get("success", True):
        raise HTTPException(status_code=400, detail=results.get("message", "Failed to retrieve Docker Compose"))

    return RetrieveDockerCompose(
        docker_compose=results.get("docker_compose", ""),
        success=results.get("success", True),
        message=results.get("message", "Docker Compose retrieved successfully"),
    )


@license_router.post(
    "/invalidate_cache",
    description="Manually invalidate license cache",
)
async def invalidate_cache_route(session: AsyncSession = Depends(get_db)):
    """
    Manually invalidate the license cache.
    Useful for testing or when you want to force a fresh license check.
    """
    license = await get_license(session)
    await invalidate_license_cache(session, license.license_key)

    return {"success": True, "message": "License cache invalidated successfully"}


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

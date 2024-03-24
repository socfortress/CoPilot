from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import root_validator


class InvokeSapSiemRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        "SAP SIEM",
        description="The integration name.",
        examples=["SAP SIEM"],
    )
    threshold: Optional[int] = Field(
        3,
        description="Number of 'Invalid LoginID' before the first 'OK'",
    )
    time_range: Optional[str] = Field(
        "15m",
        pattern="^[1-9][0-9]*[mhdw]$",
        description="Time range for the query (1m, 1h, 1d, 1w)",
    )

    lower_bound: str = None
    upper_bound: str = None

    @root_validator(pre=True)
    def set_time_bounds(cls, values):
        time_range = values.get("time_range")
        if time_range:
            unit = time_range[-1]
            amount = int(time_range[:-1])

            now = datetime.utcnow()

            if unit == "m":
                lower_bound = now - timedelta(minutes=amount)
            elif unit == "h":
                lower_bound = now - timedelta(hours=amount)
            elif unit == "d":
                lower_bound = now - timedelta(days=amount)
            elif unit == "w":
                lower_bound = now - timedelta(weeks=amount)

            values["lower_bound"] = lower_bound.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            values["upper_bound"] = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        return values


class InvokeSAPSiemResponse(BaseModel):
    success: bool
    message: str


class SapSiemAuthKeys(BaseModel):
    API_KEY: str = Field(
        ...,
        description="YOUR API KEY",
        examples=["3_yUWT3uDMs9E1N87r4Ey"],
    )
    SECRET_KEY: str = Field(
        ...,
        description="YOUR SECRET KEY",
        examples=["4ijD6uMCca"],
    )
    USER_KEY: Optional[str] = Field(
        None,
        description="YOUR USER KEY",
        examples=["AK9zAL"],
    )
    API_DOMAIN: str = Field(
        ...,
        description="YOUR API DOMAIN",
        examples=["audit.eu1.gigya.com"],
    )


class CollectSapSiemRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    apiKey: str = Field(..., description="API key for authorization")
    secretKey: str = Field(..., description="Secret key for authorization")
    userKey: str = Field(..., description="User key for identification")
    apiDomain: str = Field(..., description="API domain")
    threshold: Optional[int] = Field(
        1,
        description="Number of 'Invalid LoginID' before the first 'OK'",
    )
    lower_bound: str = None
    upper_bound: str = None


######### ! SAP API RESPONSE ! #########
class HttpReq(BaseModel):
    SDK: str = Field(
        ...,
        description="Software Development Kit used for the HTTP request",
    )
    country: str = Field(..., description="Country code")


class Params(BaseModel):
    clientContext: Optional[str] = Field(None, description="Client context information")
    include: Optional[str] = Field(None, description="Data to include in the response")
    password: str = Field(..., description="Password for the user")
    loginID: str = Field(..., description="Login ID of the user")
    apiKey: str = Field(..., description="API key for authorization")
    format: Optional[str] = Field(None, description="Response format")
    secret: Optional[str] = Field(None, description="Secret key for authorization")
    userKey: Optional[str] = Field(None, description="User key for identification")


class UserAgent(BaseModel):
    os: str = Field(..., description="Operating system of the user")
    browser: str = Field(..., description="Browser used by the user")
    raw: Optional[str] = Field(None, description="Raw user agent string")
    version: str = Field(..., description="Browser version")
    platform: str = Field(..., description="Platform type (desktop/mobile)")


class UserKeyDetails(BaseModel):
    name: Optional[str] = Field(None, description="Name of the user")
    emailDomain: Optional[str] = Field(None, description="Email domain of the user")


class Restrictions(BaseModel):
    ipWhitelistRestricted: bool = Field(
        ...,
        description="Is IP whitelisting restricted",
    )
    ipWhitelistRestrictionEnforced: bool = Field(
        ...,
        description="Is IP whitelist restriction enforced",
    )
    ipBlacklistRestricted: bool = Field(
        ...,
        description="Is IP blacklisting restricted",
    )
    ipBlacklistRestrictionEnforced: bool = Field(
        ...,
        description="Is IP blacklist restriction enforced",
    )


class Result(BaseModel):
    callID: str = Field(..., description="Unique identifier for the call")
    authType: Optional[str] = Field(None, description="Type of authentication used")
    timestamp: str = Field(
        ...,
        alias="@timestamp",
        description="Timestamp of the event",
    )
    errCode: str = Field(..., description="Error code")
    errDetails: Optional[str] = Field(None, description="Detailed error message")
    errMessage: str = Field(..., description="Error message")
    endpoint: str = Field(..., description="API endpoint hit")
    userKey: Optional[str] = Field(None, description="User key for identification")
    httpReq: HttpReq = Field(..., description="HTTP request details")
    ip: str = Field(..., description="IP address of the user")
    serverIP: str = Field(..., description="Server IP address")
    params: Params = Field(..., description="Parameters passed in the request")
    uid: Optional[str] = Field(
        "No uid found",
        description="Unique identifier for the user",
    )
    apikey: str = Field(..., description="API key used for the request")
    userAgent: UserAgent = Field(..., description="User agent details")
    userKeyDetails: Optional[UserKeyDetails] = Field(
        None,
        description="Details related to user key",
    )
    XffFirstIp: str = Field(..., description="First IP in the X-Forwarded-For header")
    restrictions: Restrictions = Field(..., description="IP restrictions")
    riskScore: Optional[str] = Field(
        None,
        description="Risk score associated with the request",
    )
    event_timestamp: Optional[datetime] = Field(
        None,
        description="Timestamp of the event",
    )
    case_created: Optional[str] = Field(
        "False",
        description="Whether a case has been created for the event",
    )
    event_analyzed: Optional[str] = Field(
        "False",
        description="Whether the event has been analyzed",
    )
    event_analyzed_multiple_logins: Optional[str] = Field(
        "False",
        description="Whether the event has been analyzed for multiple logins",
    )
    event_analyzed_success_login_diff_ip: Optional[str] = Field(
        "False",
        description="Whether the event has been analyzed for successful login from different IP",
    )
    event_analyzed_same_user_failed_diff_ip: Optional[str] = Field(
        "False",
        description="Whether the event has been analyzed for same user failed login from different IP",
    )
    event_analyzed_same_user_failed_diff_geo: Optional[str] = Field(
        "False",
        description="Whether the event has been analyzed for same user failed login from different geo",
    )
    event_analyzed_same_user_successful_diff_geo: Optional[str] = Field(
        "False",
        description="Whether the event has been analyzed for same user successful login from different geo",
    )
    event_analyzed_brute_force_ip: Optional[str] = Field(
        "False",
        description="Whether the event has been analyzed for brute force IP",
    )
    event_analyzed_brute_force_same_ip: Optional[str] = Field(
        "False",
        description="Whether the event has been analyzed for brute force same IP",
    )
    event_analyzed_successful_login_after_failures_diff_loginID: Optional[str] = Field(
        "False",
        description="Whether the event has been analyzed for successful login after failures",
    )


class SapSiemResponseBody(BaseModel):
    results: List[Result] = Field(..., description="List of result objects")
    totalCount: int = Field(..., description="Total count of results")
    statusCode: int = Field(..., description="Status code of the response")
    errorCode: int = Field(..., description="Error code of the response")
    statusReason: str = Field(..., description="Status reason of the response")
    callId: str = Field(..., description="Unique identifier for the overall call")
    time: str = Field(..., description="Time of the response")
    objectsCount: int = Field(..., description="Count of objects in results")


#### ! WAZUH INDEXER RESULTS ! ####


class SapSiemSource(BaseModel):
    logSource: Optional[str] = Field(None, description="The source of the log")
    params_loginID: str = Field(..., description="The login ID of the user")
    errCode: str = Field(..., description="The error code")
    ip: str = Field(..., description="The IP address of the user")
    httpReq_country: str = Field(..., description="The country from which the HTTP request originated")
    event_timestamp: str = Field(..., description="The timestamp of the event")
    errMessage: Optional[str] = Field(None, description="The error message")
    customer_code: str = Field(..., description="The customer code")
    errDetails: Optional[str] = Field(None, description="Detailed error message")


class SapSiemHit(BaseModel):
    index: str = Field(..., description="The index of the hit", alias="_index")
    id: str = Field(..., description="The ID of the hit", alias="_id")
    score: Optional[float] = Field(None, description="The score of the hit", alias="_score")
    source: SapSiemSource = Field(..., description="The source data of the hit", alias="_source")
    sort: Optional[List[int]] = Field(None, description="The sort order of the hit")


class SapSiemTotal(BaseModel):
    value: int = Field(..., description="The total number of hits")
    relation: str = Field(..., description="The relation of the total hits")


class SapSiemHits(BaseModel):
    total: SapSiemTotal = Field(..., description="The total hits data")
    max_score: Optional[float] = Field(None, description="The maximum score among the hits")
    hits: List[SapSiemHit] = Field(..., description="The list of hits")


class SapSiemShards(BaseModel):
    total: int = Field(..., description="The total number of shards")
    successful: int = Field(..., description="The number of successful shards")
    skipped: int = Field(..., description="The number of skipped shards")
    failed: int = Field(..., description="The number of failed shards")


class SapSiemWazuhIndexerResponse(BaseModel):
    scroll_id: Optional[str] = Field(None, description="The scroll ID", alias="_scroll_id")
    took: int = Field(..., description="The time it took to execute the request")
    timed_out: bool = Field(..., description="Whether the request timed out")
    shards: SapSiemShards = Field(..., description="The shards data", alias="_shards")
    hits: SapSiemHits = Field(..., description="The hits data")


class SuspiciousLogin(BaseModel):
    customer_code: str
    logSource: Optional[str] = Field(None)
    loginID: str
    country: Optional[str]
    ip: str
    event_timestamp: str
    errMessage: str
    index: Optional[str] = Field(None, description="The index of the hit", alias="_index")
    id: Optional[str] = Field(None, description="The ID of the hit", alias="_id")
    errDetails: Optional[str] = Field(None, description="Detailed error message")


class ErrCode(Enum):
    """
    Error codes for SAP SIEM
    """

    INVALID_LOGIN_ID = "403042"  # Invalid LoginID
    IP_BLOCKED = "403051"  # IP is blocked
    ACCOUNT_TEMPORARILY_LOCKED = "403120"  # Account temporarily locked
    OK = "0"  # Successful login


################# ! IRIS CASE CREATION SCHEMA ! #################
class IrisCasePayload(BaseModel):
    case_name: str = Field(..., description="The name of the case.")
    case_description: str = Field(..., description="The description of the case.")
    case_customer: int = Field(1, description="The customer of the case.")
    case_classification: int = Field(
        1,
        description="The classification of the case.",
    )
    soc_id: str = Field("1", description="The SOC ID of the case.")
    custom_attributes: Optional[Dict] = Field(
        None,
        description="The custom attributes of the case.",
    )
    create_customer: bool = Field(
        False,
        description="The create customer flag of the case.",
    )

    def to_dict(self):
        return self.dict(exclude_none=True)


class ModificationHistoryEntry(BaseModel):
    user: str
    user_id: int
    action: str


class CaseData(BaseModel):
    case_id: int
    open_date: str
    modification_history: Dict[str, ModificationHistoryEntry]
    close_date: Optional[str]
    case_description: str
    classification_id: int
    case_soc_id: str
    case_name: str
    custom_attributes: Optional[Dict[str, str]]
    case_uuid: str
    review_status_id: Optional[int]
    state_id: int
    case_customer: int
    reviewer_id: Optional[int]
    user_id: int
    owner_id: int
    closing_note: Optional[str]
    status_id: int


class CaseResponse(BaseModel):
    success: bool
    data: CaseData


################# ! IRIS ASSET ADD SCHEMA ! #################
class AddAssetModel(BaseModel):
    name: str
    asset_type: int
    analysis_status: int = Field(
        None,
        description="The analysis status ID of the asset.",
    )
    compromise_status: int = Field(
        None,
        description="The asset compromise status ID of the asset.",
    )
    asset_tags: Optional[List[str]] = Field(
        None,
        description="The asset tags of the asset.",
    )
    description: Optional[str] = Field(
        None,
        description="The asset description of the asset.",
    )
    asset_domain: Optional[str] = Field(
        None,
        description="The asset domain of the asset.",
    )
    ip: Optional[str] = Field(None, description="The asset IP of the asset.")
    ioc_links: Optional[List[int]] = Field(
        None,
        description="The IoC links of the asset.",
    )
    custom_attributes: Optional[Dict[str, str]] = Field(
        None,
        description="The custom attributes of the asset.",
    )

    def to_dict(self):
        return self.dict(exclude_none=True)

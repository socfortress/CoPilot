import base64
import hashlib
import hmac
import uuid
from datetime import datetime
from datetime import timedelta
from enum import Enum
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import HttpUrl
from pydantic import root_validator


class PipelineRuleTitles(Enum):
    WAZUH_INFO = "WAZUH CREATE FIELD SYSLOG LEVEL - INFO"
    WAZUH_WARNING = "WAZUH CREATE FIELD SYSLOG LEVEL - WARNING"
    WAZUH_NOTICE = "WAZUH CREATE FIELD SYSLOG LEVEL - NOTICE"
    WAZUH_ALERT = "WAZUH CREATE FIELD SYSLOG LEVEL - ALERT"
    OFFICE365_TIMESTAMP = "Office365 Timestamp - UTC"


class PipelineTitles(Enum):
    OFFICE365 = "OFFICE365 PROCESSING PIPELINE"


class MimecastRequest(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    integration_name: str = Field(
        "Mimecast",
        description="The integration name.",
        examples=["Mimecast"],
    )
    time_range: Optional[str] = Field(
        "15m",
        pattern="^[1-9][0-9]*[mhdw]$",
        description="Time range for the query (1m, 1h, 1d, 1w)",
    )


class MimecastResponse(BaseModel):
    success: bool
    message: str


class MimecastAuthKeys(BaseModel):
    APP_ID: str = Field(
        ...,
        description="YOUR DEVELOPER APPLICATION ID",
        examples=["00002"],
    )
    APP_KEY: str = Field(
        ...,
        description="YOUR DEVELOPER APPLICATION KEY",
        examples=["00002"],
    )
    EMAIL_ADDRESS: Optional[str] = Field(
        None,
        description="EMAIL ADDRESS OF YOUR ADMINISTRATOR",
        examples=["00002"],
    )
    ACCESS_KEY: str = Field(
        ...,
        description="ACCESS KEY FOR YOUR ADMINISTRATOR",
        examples=["00002"],
    )
    SECRET_KEY: str = Field(
        ...,
        description="SECRET KEY FOR YOUR ADMINISTRATOR",
        examples=["00002"],
    )
    URI = str = Field(
        "/api/audit/get-siem-logs",
        description="URI FOR YOUR API Endpoint",
        examples=["/api/audit/get-siem-logs"],
    )


class APIEndpointRegion(BaseModel):
    code: str
    api: HttpUrl
    mpp: HttpUrl
    adminConsole: HttpUrl
    name: str


class APIEndpointDataItem(BaseModel):
    emailAddress: str
    emailToken: str
    authenticate: List
    region: APIEndpointRegion


class APIEndpointMeta(BaseModel):
    status: int


class APIEndpointData(BaseModel):
    meta: APIEndpointMeta
    data: List[APIEndpointDataItem]
    fail: List


class MimecastAPIEndpointResponse(BaseModel):
    data: APIEndpointData
    success: bool
    message: str


class MimecastScheduledResponse(BaseModel):
    success: bool
    message: str


# ! MIMECAST TTP URLS ! #
class MimecastHeaders(BaseModel):
    Authorization: str = Field(
        ...,
        description="The Authorization header typically containing the access token.",
    )
    x_mc_app_id: str = Field(
        ...,
        alias="x-mc-app-id",
        description="The Application ID for Mimecast.",
    )
    x_mc_date: str = Field(
        ...,
        alias="x-mc-date",
        description="The date when the request was made.",
    )
    x_mc_req_id: str = Field(
        ...,
        alias="x-mc-req-id",
        description="The unique request ID.",
    )
    Content_Type: str = Field(
        ...,
        alias="Content-Type",
        description="The type of content, usually application/json.",
    )

    class Config:
        allow_population_by_field_name = True  # This allows field population by both alias and field name


class MimecastTTPURLSRequest(BaseModel):
    ApplicationID: str = Field(..., description="The ID of the Mimecast application.")
    ApplicationKey: str = Field(
        ...,
        description="The key associated with the Mimecast application.",
    )
    AccessKey: str = Field(..., description="The access key for API authentication.")
    SecretKey: str = Field(..., description="The secret key for API authentication.")
    EmailAddress: str = Field(
        ...,
        description="The email address of the Mimecast administrator.",
    )
    BaseURL: Optional[str] = Field(
        None,
        description="The base URL for the Mimecast API.",
    )
    time_range: Optional[str] = Field(
        "15m",
        pattern="^[1-9][0-9]*[mhdw]$",
        description="Time range for the query (1m, 1h, 1d, 1w)",
    )
    # headers: Dict[str, str] = Field(default_factory=dict)  # default empty dictionary
    headers: Optional[MimecastHeaders] = Field(
        None,
        description="The headers generated for the request.",
    )
    pagination_token: str = Field(None, description="Pagination token for API calls")

    lower_bound: str = None
    upper_bound: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generate_headers("/api/ttp/url/get-logs")  # default URI

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

    def generate_headers(self, uri: str) -> dict:
        """Generate Mimecast request headers."""

        request_id = str(uuid.uuid4())
        hdr_date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S") + " UTC"

        dataToSign = ":".join([hdr_date, request_id, uri, self.ApplicationKey])

        hmac_sha1 = hmac.new(
            base64.b64decode(self.SecretKey),
            dataToSign.encode(),
            digestmod=hashlib.sha1,
        ).digest()
        sig = base64.b64encode(hmac_sha1).rstrip()

        headers_dict = {
            "Authorization": "MC " + self.AccessKey + ":" + sig.decode(),
            "x-mc-app-id": self.ApplicationID,
            "x-mc-date": hdr_date,
            "x-mc-req-id": request_id,
            "Content-Type": "application/json",
        }

        self.headers = MimecastHeaders(
            **headers_dict,
        )  # Create a new instance of MimecastHeaders and assign

        return headers_dict


##### ! SENDING REQUEST TO MIMECAST ! #####
class DataItem(BaseModel):
    oldestFirst: bool = Field(..., description="Ordering flag, oldest first if true.")
    from_: datetime = Field(
        ...,
        alias="from",
        description="Start date-time in ISO 8601 format.",
    )
    to: datetime = Field(..., description="End date-time in ISO 8601 format.")
    route: str = Field(..., description="Routing information.")
    scanResult: str = Field(..., description="Scan result.")

    class Config:
        allow_population_by_field_name = True  # This allows field population by both alias and field name


class RequestBody(BaseModel):
    meta: Dict = Field({}, description="Meta information.")
    data: List[DataItem] = Field(..., description="List of data items.")


class TTPResponseClickLogs(BaseModel):
    userEmailAddress: str
    fromUserEmailAddress: str
    url: str
    ttpDefinition: str
    subject: str
    action: str
    adminOverride: str
    userOverride: str
    scanResult: str
    category: str
    sendingIp: str
    userAwarenessAction: str
    date: str
    actions: str
    route: str
    creationMethod: str
    emailPartsDescription: List[str]
    messageId: str


class TTPResponseDataItem(BaseModel):
    clickLogs: List[TTPResponseClickLogs]


class TTPResponsePagination(BaseModel):
    pageSize: int
    totalCount: int
    next: Optional[str]


class ResponseMeta(BaseModel):
    pagination: TTPResponsePagination
    status: int


class TtpURLResponseBody(BaseModel):
    meta: ResponseMeta
    data: List[TTPResponseDataItem]
    fail: List[Dict]  # Adjust this based on the actual structure of the "fail" field


class ResponseAttachmentLogs(BaseModel):
    senderAddress: str
    recipientAddress: str
    fileName: str
    fileType: str
    result: str
    actionTriggered: str
    date: str
    details: str
    route: str
    messageId: str
    subject: str
    fileHash: str
    definition: str


class ResponseDataItemAttachment(BaseModel):
    attachmentLogs: List[ResponseAttachmentLogs]


class TtpURLAttachmentResponseBody(BaseModel):
    meta: ResponseMeta
    data: List[ResponseDataItemAttachment]
    fail: List[Dict]  # Adjust this based on the actual structure of the "fail" field

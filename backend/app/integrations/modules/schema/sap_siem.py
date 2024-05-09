from datetime import datetime
from datetime import timedelta
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


class CustomerDetails(BaseModel):
    customer_code: str = Field(
        ...,
        description="The customer code.",
        examples=["00002"],
    )
    iris_customer_id: int = Field(
        ...,
        description="The customer ID in IRIS.",
        examples=[1],
    )


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
    auth_keys: SapSiemAuthKeys = Field(
        ...,
        description="The authentication keys for the SAP SIEM integration.",
    )
    customer_details: CustomerDetails = Field(
        ...,
        description="The customer details.",
    )

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

    def to_dict(self):
        return self.dict()


class InvokeSapSiemAnalysis(BaseModel):
    threshold: int = Field(
        0,
        description="Number of 'Invalid LoginID' before the first 'OK'",
    )
    time_range: int = Field(
        "15",
        description="Time range for the query (1m, 1h, 1d, 1w)",
    )
    iris_customer_id: int = Field(
        ...,
        description="The customer ID in IRIS.",
        examples=[1],
    )

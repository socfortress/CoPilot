import ipaddress
import re
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator

HASH_REGEX = re.compile(
    r"[a-fA-F\d]{32}|[a-fA-F\d]{64}",
)  # Update this regex to match your specific hash format
DOMAIN_REGEX = re.compile(
    r"^(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,6}$",
)  # Update this regex to match your specific domain format


class AnalyzersResponse(BaseModel):
    analyzers: List[str]
    message: str
    success: bool


class RunAnalyzerBody(BaseModel):
    analyzer_name: str = Field(..., description="Name of the analyzer to be run.")
    analyzer_data: str = Field(
        ...,
        description="The Indicator of Compromise (IoC) to be analyzed.",
    )
    data_type: Optional[str] = Field(
        default=None,
        description="Data type determined after validation",
    )

    @validator("analyzer_data", pre=True, always=True)
    def validate_and_set_data_type(cls, value: str, values: dict) -> str:
        is_valid, data_type = cls.is_valid_datatype(value)
        if not is_valid:
            raise ValueError(f"Invalid data type: {data_type}")
        values["data_type"] = data_type
        return value

    @classmethod
    def is_valid_datatype(cls, value: str) -> Tuple[bool, str]:
        if cls._is_valid_ipv4(value):
            return True, "ip"
        elif cls._is_valid_hash(value):
            return True, "hash"
        elif cls._is_valid_domain(value):
            return True, "domain"
        else:
            return False, "Unknown"

    @staticmethod
    def _is_valid_ipv4(value: str) -> bool:
        try:
            ipaddress.IPv4Address(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_valid_hash(value: str) -> bool:
        return bool(HASH_REGEX.match(value))

    @staticmethod
    def _is_valid_domain(value: str) -> bool:
        return bool(DOMAIN_REGEX.match(value))


class RunAnalyzerResponse(BaseModel):
    report: Dict[str, Any]
    message: str
    success: bool


class AnalyzerJobData(BaseModel):
    data: str = Field(
        ...,
        description="The Indicator of Compromise (IoC) to be analyzed.",
    )
    dataType: str = Field(
        ...,
        description="The type of the IoC (e.g., 'IP', 'hash', 'domain').",
    )
    tlp: int = Field(1, description="Traffic Light Protocol (TLP) level.")
    message: str = Field(
        "custom message sent to analyzer",
        description="Custom message.",
    )

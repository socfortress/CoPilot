import re
from datetime import datetime
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator

class SigmaRulesLevel(str, Enum):
    """
    Represents the Sigma rules level.
    """
    high = "high"
    critical = "critical"

class SigmaRuleUploadRequest(BaseModel):
    rule_levels: List[SigmaRulesLevel] = Field(
        ...,
        description="The Sigma rule levels to upload.",
    )


class DownloadSigmaRulesRequest(BaseModel):
    url: str = Field(
        "https://github.com/SigmaHQ/sigma/releases/download/r2024-07-17/sigma_all_rules.zip",
        title="URL",
        description="The URL to download the Sigma rules from.",
    )
    folder: str = Field(
        "windows",
        title="Folder",
        description="The folder of Sigma rules to download.",
    )


class BulkUploadToDBResponse(BaseModel):
    success: bool
    message: str


class SigmaQueriesOut(BaseModel):
    """
    Represents the Sigma queries output.
    """

    id: int
    rule_name: str
    rule_query: str
    active: bool
    time_interval: str
    last_updated: Optional[datetime] = None
    last_execution_time: Optional[datetime] = None


class SigmaQueryOutResponse(BaseModel):
    """
    Represents the Sigma query output response.
    """

    sigma_queries: Optional[List[SigmaQueriesOut]] = []
    success: bool
    message: str


class RunActiveSigmaQueries(BaseModel):
    query: str = Field(
        ...,
        description="The query to run.",
    )
    time_interval: str = Field(
        ...,
        description="The time interval to run the query for.",
    )
    last_execution_time: datetime = None
    rule_name: str = Field(
        ...,
        description="The name of the rule.",
    )
    index: str = Field(
        "wazuh*",
        description="The index to run the query on.",
    )


class CreateSigmaQuery(BaseModel):
    """
    Represents the Sigma query creation request.
    """

    rule_name: str
    rule_query: str
    active: bool
    time_interval: str

    @validator("rule_name")
    def validate_rule_name(cls, rule_name: str) -> str:
        """
        Validates the rule name.

        Args:
            rule_name (str): The rule name.

        Returns:
            str: The validated rule name.
        """
        if len(rule_name) < 1:
            raise ValueError("The rule name must not be empty.")

        return rule_name

    @validator("rule_query")
    def validate_rule_query(cls, rule_query: str) -> str:
        """
        Validates the rule query.

        Args:
            rule_query (str): The rule query.

        Returns:
            str: The validated rule query.
        """
        if len(rule_query) < 1:
            raise ValueError("The rule query must not be empty.")

        return rule_query

    @validator("time_interval")
    def validate_time_interval(cls, time_interval: str) -> str:
        """
        Validates the time interval.

        Args:
            time_interval (str): The time interval.

        Returns:
            str: The validated time interval.
        """
        if not re.match(r"^\d+[mhd]$", time_interval):
            raise ValueError("The time interval must be in the format of minutes (e.g., '1m'), hours (e.g., '1h'), or days (e.g., '1d').")

        return time_interval


class QueryString(BaseModel):
    query: str
    analyze_wildcard: bool


class MustItem(BaseModel):
    query_string: QueryString


class BoolQuery(BaseModel):
    must: List[MustItem]


class Query(BaseModel):
    bool: BoolQuery


class SigmaQueryGenerationResponse(BaseModel):
    query: Query


class UpdateSigmaActive(BaseModel):
    rule_name: str
    active: bool


class UpdateSigmaTimeInterval(BaseModel):
    rule_name: str
    time_interval: str

    @validator("time_interval")
    def validate_time_interval(cls, time_interval: str) -> str:
        """
        Validates the time interval.

        Args:
            time_interval (str): The time interval.

        Returns:
            str: The validated time interval.
        """
        if not re.match(r"^\d+[mhd]$", time_interval):
            raise ValueError("The time interval must be in the format of minutes (e.g., '1m'), hours (e.g., '1h'), or days (e.g., '1d').")

        return time_interval

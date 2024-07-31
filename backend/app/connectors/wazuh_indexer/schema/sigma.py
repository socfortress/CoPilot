from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
import re

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator
from datetime import datetime

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
        if not re.match(r'^\d+[mhd]$', time_interval):
            raise ValueError("The time interval must be in the format of minutes (e.g., '1m'), hours (e.g., '1h'), or days (e.g., '1d').")

        return time_interval

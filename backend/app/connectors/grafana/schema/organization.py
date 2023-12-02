from pydantic import BaseModel
from enum import Enum


class GrafanaCreateOrganizationResponse(BaseModel):
    message: str
    orgId: int

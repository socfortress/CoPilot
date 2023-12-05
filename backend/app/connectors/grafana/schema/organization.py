from enum import Enum

from pydantic import BaseModel


class GrafanaCreateOrganizationResponse(BaseModel):
    message: str
    orgId: int

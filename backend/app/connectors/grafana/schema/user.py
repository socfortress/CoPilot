from pydantic import BaseModel
from pydantic import Field


class UserOrganizationAddRequest(BaseModel):
    """
    Request model for adding a user to an organization in Grafana.
    """

    loginorEmail: str = Field(
        ...,
        description="Login or email of the user to be added.",
    )
    role: str = Field(
        "Viewer",
        description="Role to assign to the user in the organization.",
    )
    organizationId: str = Field(
        ...,
        description="ID of the organization to which the user will be added.",
    )


class UserOrganizationAddResponse(BaseModel):
    """
    Response model for adding a user to an organization in Grafana.
    """

    success: bool = Field(
        ...,
        description="Indicates whether the operation was successful.",
    )
    message: str = Field(
        ...,
        description="Message describing the result of the operation.",
    )

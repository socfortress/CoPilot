from pydantic import BaseModel
from pydantic import Field

class DecomissionCustomerResponse(BaseModel):
    message: str = Field(..., example="Customer decommissioned successfully", description="Message indicating the customer was decommissioned successfully")
    success: bool = Field(..., example=True, description="Whether the customer was decommissioned successfully or not")

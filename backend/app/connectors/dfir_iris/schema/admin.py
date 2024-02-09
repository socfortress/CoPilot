import uuid
from datetime import datetime
from typing import Dict
from typing import List
from typing import Optional

from pydantic import UUID4
from pydantic import BaseModel


class CreateCustomerData(BaseModel):
    customer_id: int
    customer_sla: Optional[str] = None
    customer_name: str
    customer_description: Optional[str] = None
    creation_date: datetime
    custom_attributes: Dict
    last_update_date: datetime
    client_uuid: uuid.UUID


class CreateCustomerResponse(BaseModel):
    success: bool
    data: CreateCustomerData


class Customer(BaseModel):
    customer_name: str
    customer_id: int
    customer_uuid: UUID4
    customer_description: Optional[str] = None
    customer_sla: Optional[str] = None


class ListCustomers(BaseModel):
    success: bool
    data: List[Customer]

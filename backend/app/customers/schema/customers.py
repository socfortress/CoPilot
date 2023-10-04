from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List

class CustomerRequestBody(BaseModel):
    customer_code: str = Field(..., description="Unique code for the customer")
    customer_name: str = Field(..., description="Name of the customer")
    contact_last_name: str = Field(..., description="Last name of the contact person")
    contact_first_name: str = Field(..., description="First name of the contact person")
    
    parent_customer_code: Optional[str] = Field(None, description="Code for the parent customer")
    phone: Optional[str] = Field(None, description="Phone number")
    address_line1: Optional[str] = Field(None, description="First line of the address")
    address_line2: Optional[str] = Field(None, description="Second line of the address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State")
    postal_code: Optional[str] = Field(None, description="Postal Code")
    country: Optional[str] = Field(None, description="Country")
    customer_type: Optional[str] = Field(None, description="Type of the customer")
    logo_file: Optional[str] = Field(None, description="Logo file for the customer")

    class Config:
        schema_extra = {
            "example": {
                "customer_code": "CUST123",
                "customer_name": "Sample Customer",
                "contact_last_name": "Doe",
                "contact_first_name": "John",
                "phone": "123-456-7890",
                "address_line1": "123 Main St",
                "address_line2": "Apt 4",
                "city": "Anytown",
                "state": "CA",
                "postal_code": "12345",
                "country": "USA",
                "customer_type": "Enterprise",
                "logo_file": "logo.png"
            }
        }

class CustomerResponse(BaseModel):
    customer: Optional[CustomerRequestBody]
    success: bool
    message: str

class CustomersResponse(BaseModel):
    customers: list[CustomerRequestBody]
    success: bool
    message: str

############# Customer Meta
class CustomerMetaRequestBody(BaseModel):
    customer_meta_graylog_index: str = Field(..., description="Graylog index for the customer")
    customer_meta_graylog_stream: str = Field(..., description="Graylog stream for the customer")
    customer_meta_influx_org: str = Field(..., description="InfluxDB organization for the customer")
    customer_meta_grafana_org: str = Field(..., description="Grafana organization for the customer")
    customer_meta_wazuh_group: str = Field(..., description="Wazuh group for the customer")
    index_retention: int = Field(..., description="Index retention for the customer")
    wazuh_registration_port: int = Field(..., description="Wazuh registration port for the customer")
    wazuh_log_ingestion_port: int = Field(..., description="Wazuh log ingestion port for the customer")

    class Config:
        schema_extra = {
            "example": {
                "customer_meta_graylog_index": "graylog_index",
                "customer_meta_graylog_stream": "graylog_stream",
                "customer_meta_influx_org": "influx_org",
                "customer_meta_grafana_org": "grafana_org",
                "customer_meta_wazuh_group": "wazuh_group",
                "index_retention": 30,
                "wazuh_registration_port": 1514,
                "wazuh_log_ingestion_port": 1515
            }
        }

class CustomerMetaResponse(BaseModel):
    customer_meta: Optional[CustomerMetaRequestBody]
    success: bool
    message: str

############# Customer Full Response
class CustomerFullResponse(BaseModel):
    customer: Optional[CustomerRequestBody]
    customer_meta: Optional[CustomerMetaRequestBody]
    success: bool
    message: str


############# Agent Model #############
class AgentModel(BaseModel):
    id: Optional[int]
    os: Optional[str]
    label: Optional[str]
    wazuh_last_seen: Optional[datetime]
    velociraptor_last_seen: Optional[datetime]
    velociraptor_agent_version: Optional[str]
    ip_address: Optional[str]
    agent_id: Optional[str]
    hostname: Optional[str]
    critical_asset: Optional[bool]
    velociraptor_id: Optional[str]
    wazuh_agent_version: Optional[str]
    customer_code: Optional[str]

    class Config:
        orm_mode = True

class AgentsResponse(BaseModel):
    agents: Optional[List[AgentModel]] = Field([], description="List of agents")
    success: bool
    message: str
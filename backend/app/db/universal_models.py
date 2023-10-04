from sqlmodel import SQLModel, Field, Column, Relationship
from typing import Optional
from datetime import datetime


class Customers(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    customer_code: str = Field(max_length=11, nullable=False)
    parent_customer_code: Optional[str] = Field(max_length=11)
    customer_name: str = Field(max_length=50, nullable=False)
    contact_last_name: Optional[str] = Field(max_length=50)
    contact_first_name: Optional[str] = Field(max_length=50)
    phone: Optional[str] = Field(max_length=50)
    address_line1: Optional[str] = Field(max_length=1024)
    address_line2: Optional[str] = Field(max_length=1024)
    city: Optional[str] = Field(max_length=50)
    state: Optional[str] = Field(max_length=50)
    postal_code: Optional[str] = Field(max_length=15)
    country: Optional[str] = Field(max_length=50)
    customer_type: Optional[str] = Field(max_length=50)
    logo_file: Optional[str] = Field(max_length=64)
    created_at: datetime = Field(default=datetime.utcnow())
    
    agents: list["Agents"] = Relationship(back_populates="customer")
    meta: Optional["CustomersMeta"] = Relationship(back_populates="customer")

    def update_from_model(self, customer):
        self.customer_code = customer.customer_code
        self.parent_customer_code = customer.parent_customer_code
        self.customer_name = customer.customer_name
        self.contact_last_name = customer.contact_last_name
        self.contact_first_name = customer.contact_first_name
        self.phone = customer.phone
        self.address_line1 = customer.address_line1
        self.address_line2 = customer.address_line2
        self.city = customer.city
        self.state = customer.state
        self.postal_code = customer.postal_code
        self.country = customer.country
        self.customer_type = customer.customer_type
        self.logo_file = customer.logo_file

class CustomersMeta(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    customer_code: str = Field(foreign_key="customers.customer_code", nullable=False)
    customer_name: str = Field(max_length=255)
    customer_meta_graylog_index: str = Field(max_length=1024)
    customer_meta_graylog_stream: str = Field(max_length=1024)
    customer_meta_influx_org: str = Field(max_length=1024)
    customer_meta_grafana_org: str = Field(max_length=1024)
    customer_meta_wazuh_group: str = Field(max_length=1024)
    index_retention: Optional[int] = Field()
    wazuh_registration_port: Optional[int] = Field()
    wazuh_log_ingestion_port: Optional[int] = Field()

    # Link back to Customers
    customer: Optional["Customers"] = Relationship(back_populates="meta")

    def update_from_model(self, customer_meta):
        if hasattr(customer_meta, 'customer_code'):
            self.customer_code = customer_meta.customer_code
        if hasattr(customer_meta, 'customer_name'):
            self.customer_name = customer_meta.customer_name
        self.customer_meta_graylog_index = customer_meta.customer_meta_graylog_index
        self.customer_meta_graylog_stream = customer_meta.customer_meta_graylog_stream
        self.customer_meta_influx_org = customer_meta.customer_meta_influx_org
        self.customer_meta_grafana_org = customer_meta.customer_meta_grafana_org
        self.customer_meta_wazuh_group = customer_meta.customer_meta_wazuh_group
        self.index_retention = customer_meta.index_retention
        self.wazuh_registration_port = customer_meta.wazuh_registration_port
        self.wazuh_log_ingestion_port = customer_meta.wazuh_log_ingestion_port

class Agents(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    agent_id: str = Field(index=True)
    ip_address: str = Field(max_length=256)
    os: str = Field(max_length=256)
    hostname: str = Field(max_length=256)
    label: str = Field(max_length=256)
    critical_asset: bool = Field(default=False)
    wazuh_last_seen: datetime
    velociraptor_id: str = Field(max_length=256)
    velociraptor_last_seen: datetime
    wazuh_agent_version: str = Field(max_length=256)
    velociraptor_agent_version: str = Field(max_length=256)
    customer_code: Optional[str] = Field(foreign_key="customers.customer_code")
    
    customer: Optional[Customers] = Relationship(back_populates="agents")

    @classmethod
    def create_from_model(cls, wazuh_agent, velociraptor_agent, customer_code):
        return cls(
            agent_id=wazuh_agent.agent_id,
            hostname=wazuh_agent.agent_name,
            ip_address=wazuh_agent.agent_ip,
            os=wazuh_agent.agent_os,
            label=wazuh_agent.agent_label,
            wazuh_last_seen=wazuh_agent.agent_last_seen_as_datetime,
            wazuh_agent_version=wazuh_agent.wazuh_agent_version,
            velociraptor_id=velociraptor_agent.client_id if velociraptor_agent.client_id else "n/a",
            velociraptor_last_seen=velociraptor_agent.client_last_seen_as_datetime,
            velociraptor_agent_version=velociraptor_agent.client_version,
            customer_code=customer_code
        )

    def update_from_model(self, wazuh_agent, velociraptor_agent, customer_code):
        self.agent_id = wazuh_agent.agent_id
        self.hostname = wazuh_agent.agent_name
        self.ip_address = wazuh_agent.agent_ip
        self.os = wazuh_agent.agent_os
        self.label = wazuh_agent.agent_label
        self.wazuh_last_seen = wazuh_agent.agent_last_seen_as_datetime
        self.wazuh_agent_version = wazuh_agent.wazuh_agent_version
        self.velociraptor_id = velociraptor_agent.client_id if velociraptor_agent.client_id else "n/a"
        self.velociraptor_last_seen = velociraptor_agent.client_last_seen_as_datetime
        self.velociraptor_agent_version = velociraptor_agent.client_version
        self.customer_code = customer_code

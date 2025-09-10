from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import LargeBinary
from sqlmodel import Field
from sqlmodel import Relationship
from sqlmodel import SQLModel


class Customers(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    customer_code: str = Field(sa_column_kwargs={"index": True}, max_length=50, nullable=False)
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
    customer_meta_grafana_org_id: str = Field(max_length=1024)
    customer_meta_wazuh_group: str = Field(max_length=1024)
    customer_meta_index_retention: Optional[str] = Field()
    customer_meta_wazuh_registration_port: Optional[str] = Field()
    customer_meta_wazuh_log_ingestion_port: Optional[str] = Field()
    customer_meta_wazuh_api_port: Optional[str] = Field()
    customer_meta_wazuh_auth_password: Optional[str] = Field(max_length=1024)
    customer_meta_iris_customer_id: Optional[int] = Field()
    customer_meta_office365_organization_id: Optional[str] = Field(max_length=1024)
    customer_meta_portainer_stack_id: Optional[int] = Field()

    # Link back to Customers
    customer: Optional["Customers"] = Relationship(back_populates="meta")

    def update_from_model(self, customer_meta):
        if hasattr(customer_meta, "customer_code"):
            self.customer_code = customer_meta.customer_code
        if hasattr(customer_meta, "customer_name"):
            self.customer_name = customer_meta.customer_name
        self.customer_meta_graylog_index = customer_meta.customer_meta_graylog_index
        self.customer_meta_graylog_stream = customer_meta.customer_meta_graylog_stream
        self.customer_meta_grafana_org_id = customer_meta.customer_meta_grafana_org_id
        self.customer_meta_wazuh_group = customer_meta.customer_meta_wazuh_group
        self.customer_meta_index_retention = customer_meta.customer_meta_index_retention
        self.customer_meta_wazuh_registration_port = customer_meta.customer_meta_wazuh_registration_port
        self.customer_meta_wazuh_log_ingestion_port = customer_meta.customer_meta_wazuh_log_ingestion_port
        self.customer_meta_wazuh_api_port = customer_meta.customer_meta_wazuh_api_port
        self.customer_meta_wazuh_auth_password = customer_meta.customer_meta_wazuh_auth_password
        self.customer_meta_iris_customer_id = customer_meta.customer_meta_iris_customer_id
        self.customer_meta_office365_organization_id = customer_meta.customer_meta_office365_organization_id
        self.customer_meta_portainer_stack_id = customer_meta.customer_meta_portainer_stack_id


class Agents(SQLModel, table=True):
    id: Optional[int] = Field(primary_key=True)
    agent_id: str = Field(index=True, max_length=256)
    ip_address: str = Field(max_length=256)
    os: str = Field(max_length=256)
    hostname: str = Field(max_length=256)
    label: str = Field(max_length=256)
    critical_asset: bool = Field(default=False)
    wazuh_last_seen: datetime
    velociraptor_id: Optional[str] = Field(max_length=256)
    velociraptor_last_seen: Optional[datetime]
    wazuh_agent_version: str = Field(max_length=256)
    wazuh_agent_status: str = Field("not found", max_length=256)
    velociraptor_agent_version: Optional[str] = Field(max_length=256)
    customer_code: Optional[str] = Field(foreign_key="customers.customer_code", max_length=256)
    quarantined: bool = Field(default=False)
    velociraptor_org: Optional[str] = Field(max_length=256)

    customer: Optional[Customers] = Relationship(back_populates="agents")
    vulnerabilities: Optional[list["AgentVulnerabilities"]] = Relationship(back_populates="agent")

    @classmethod
    def create_from_model(cls, wazuh_agent, velociraptor_agent, customer_code):
        # Check if agent_last_seen is 'Unknown' and set wazuh_last_seen accordingly
        if wazuh_agent.agent_last_seen == "Unknown":
            wazuh_last_seen_value = "1970-01-01T00:00:00+00:00"  # default datetime value
        else:
            wazuh_last_seen_value = wazuh_agent.agent_last_seen_as_datetime

        return cls(
            agent_id=wazuh_agent.agent_id,
            hostname=wazuh_agent.agent_name,
            ip_address=wazuh_agent.agent_ip,
            os=wazuh_agent.agent_os,
            label=wazuh_agent.agent_label,
            wazuh_last_seen=wazuh_last_seen_value,
            wazuh_agent_version=wazuh_agent.wazuh_agent_version,
            wazuh_agent_status=wazuh_agent.wazuh_agent_status if wazuh_agent.wazuh_agent_status else "not found",
            velociraptor_id=velociraptor_agent.client_id if velociraptor_agent and velociraptor_agent.client_id else None,
            velociraptor_last_seen=velociraptor_agent.client_last_seen_as_datetime
            if velociraptor_agent and velociraptor_agent.client_last_seen_as_datetime
            else None,
            velociraptor_agent_version=velociraptor_agent.client_version
            if velociraptor_agent and velociraptor_agent.client_version
            else None,
            customer_code=customer_code,
            velociraptor_org=velociraptor_agent.client_org if velociraptor_agent and velociraptor_agent.client_org else None,
        )

    @classmethod
    def create_wazuh_agent_from_model(cls, wazuh_agent, customer_code):
        if wazuh_agent.agent_last_seen == "Unknown":
            wazuh_last_seen_value = "1970-01-01T00:00:00+00:00"
        else:
            wazuh_last_seen_value = wazuh_agent.agent_last_seen_as_datetime

        return cls(
            agent_id=wazuh_agent.agent_id,
            hostname=wazuh_agent.agent_name,
            ip_address=wazuh_agent.agent_ip,
            os=wazuh_agent.agent_os,
            label=wazuh_agent.agent_label,
            wazuh_last_seen=wazuh_last_seen_value,
            wazuh_agent_version=wazuh_agent.wazuh_agent_version,
            wazuh_agent_status=wazuh_agent.wazuh_agent_status if wazuh_agent.wazuh_agent_status else "not found",
            customer_code=customer_code,
        )

    def update_from_model(self, wazuh_agent, velociraptor_agent, customer_code):
        if wazuh_agent.agent_last_seen == "Unknown" or wazuh_agent.agent_last_seen == "1970-01-01T00:00:00+00:00":
            wazuh_last_seen_value = datetime.strptime(
                "1970-01-01T00:00:00+00:00",
                "%Y-%m-%dT%H:%M:%S%z",
            )  # default datetime value
        else:
            wazuh_last_seen_value = wazuh_agent.agent_last_seen_as_datetime

        self.agent_id = wazuh_agent.agent_id
        self.hostname = wazuh_agent.agent_name
        self.ip_address = wazuh_agent.agent_ip
        self.os = wazuh_agent.agent_os
        self.label = wazuh_agent.agent_label
        self.wazuh_last_seen = wazuh_last_seen_value
        self.wazuh_agent_version = wazuh_agent.wazuh_agent_version
        self.wazuh_agent_status = wazuh_agent.wazuh_agent_status if wazuh_agent.wazuh_agent_status else "not found"
        self.velociraptor_id = velociraptor_agent.client_id if velociraptor_agent and velociraptor_agent.client_id else None
        self.velociraptor_last_seen = (
            velociraptor_agent.client_last_seen_as_datetime
            if velociraptor_agent and velociraptor_agent.client_last_seen_as_datetime
            else None
        )
        self.velociraptor_agent_version = (
            velociraptor_agent.client_version if velociraptor_agent and velociraptor_agent.client_version else None
        )
        self.customer_code = customer_code
        self.velociraptor_org = velociraptor_agent.client_org if velociraptor_agent and velociraptor_agent.client_org else None

    def update_wazuh_agent_from_model(self, wazuh_agent, customer_code):
        if wazuh_agent.agent_last_seen == "Unknown" or wazuh_agent.agent_last_seen == "1970-01-01T00:00:00+00:00":
            wazuh_last_seen_value = datetime.strptime(
                "1970-01-01T00:00:00+00:00",
                "%Y-%m-%dT%H:%M:%S%z",
            )
        else:
            wazuh_last_seen_value = wazuh_agent.agent_last_seen_as_datetime

        self.agent_id = wazuh_agent.agent_id
        self.hostname = wazuh_agent.agent_name
        self.ip_address = wazuh_agent.agent_ip
        self.os = wazuh_agent.agent_os
        self.label = wazuh_agent.agent_label
        self.wazuh_last_seen = wazuh_last_seen_value
        self.wazuh_agent_version = wazuh_agent.wazuh_agent_version
        self.wazuh_agent_status = wazuh_agent.wazuh_agent_status if wazuh_agent.wazuh_agent_status else "not found"
        self.customer_code = customer_code

    def update_velociraptor_details(self, velociraptor_agent):
        logger.info(f"Updating Velociraptor details for agent {self}")
        self.velociraptor_id = velociraptor_agent.client_id if velociraptor_agent and velociraptor_agent.client_id else None
        self.velociraptor_last_seen = (
            velociraptor_agent.client_last_seen_as_datetime
            if velociraptor_agent and velociraptor_agent.client_last_seen_as_datetime
            else None
        )
        self.velociraptor_agent_version = (
            velociraptor_agent.client_version if velociraptor_agent and velociraptor_agent.client_version else None
        )
        logger.info(f"Updated with Velociraptor details: {self}")
        self.velociraptor_org = velociraptor_agent.client_org if velociraptor_agent and velociraptor_agent.client_org else None


class LogEntry(SQLModel, table=True):
    __tablename__ = "log_entries"
    id: Optional[int] = Field(primary_key=True)
    timestamp: datetime = Field(default=datetime.utcnow())
    event_type: str = Field(default="Info", max_length=256)
    user_id: int = Field(default=None, nullable=True)
    route: str = Field(default=None, nullable=True, max_length=256)
    method: str = Field(default=None, nullable=True, max_length=256)
    status_code: int
    message: str = Field(default=None, nullable=True, max_length=5024)
    additional_info: str = Field(default=None, nullable=True, max_length=5024)


class License(SQLModel, table=True):
    __tablename__ = "license"
    id: Optional[int] = Field(primary_key=True)
    license_key: str = Field(max_length=1024)
    customer_name: str = Field(max_length=1024)
    customer_email: str = Field(max_length=1024)
    company_name: str = Field(max_length=1024)


class LicenseCache(SQLModel, table=True):
    __tablename__ = "license_cache"
    id: Optional[int] = Field(primary_key=True)
    license_key: str = Field(max_length=1024, index=True)
    feature_name: str = Field(max_length=256, index=True)
    is_enabled: bool = Field(default=False)
    cached_at: datetime = Field(default=datetime.utcnow, index=True)
    expires_at: datetime = Field(index=True)
    license_data: Optional[str] = Field(max_length=5000)  # Store full license JSON as string for reference


class SchedulerJob(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True, nullable=False, max_length=255)
    next_run_time: float = Field(sa_column=Column(Float(), index=True))
    job_state: bytes = Field(sa_column=Column(LargeBinary(), nullable=False))

    def __repr__(self):
        return f"<SchedulerJob(id={self.id}, next_run_time={self.next_run_time})>"


class AgentVulnerabilities(SQLModel, table=True):
    __tablename__ = "agent_vulnerabilities"

    id: Optional[int] = Field(primary_key=True)
    cve_id: str = Field(default="UNKNOWN_CVE", max_length=50, index=True)
    severity: str = Field(default="UNKNOWN", max_length=50, index=True)
    title: str = Field(max_length=255)
    references: str = Field(default=None, max_length=2048)
    status: str = Field(default="Active", max_length=50, index=True)
    discovered_at: datetime = Field(index=True)
    remediated_at: Optional[datetime] = Field(default=None)
    epss_score: Optional[str] = Field(default=None, max_length=50)
    epss_percentile: Optional[str] = Field(default=None, max_length=50)
    package_name: Optional[str] = Field(default=None, max_length=255)

    # Foreign keys
    agent_id: str = Field(foreign_key="agents.agent_id", max_length=256, index=True)
    customer_code: Optional[str] = Field(foreign_key="customers.customer_code", max_length=50, index=True)

    # Relationship back to the Agents model
    agent: Optional["Agents"] = Relationship(back_populates="vulnerabilities")

    def update_from_model(self, vulnerability_data):
        """Update vulnerability from external data source"""
        if hasattr(vulnerability_data, "cve_id"):
            self.cve_id = vulnerability_data.cve_id
        if hasattr(vulnerability_data, "severity"):
            self.severity = vulnerability_data.severity
        if hasattr(vulnerability_data, "title"):
            self.title = vulnerability_data.title
        if hasattr(vulnerability_data, "references"):
            self.references = vulnerability_data.references
        if hasattr(vulnerability_data, "detected_at"):
            self.discovered_at = vulnerability_data.detected_at
        if hasattr(vulnerability_data, "status"):
            self.status = vulnerability_data.status
        if hasattr(vulnerability_data, "epss_score"):
            self.epss_score = vulnerability_data.epss_score
        if hasattr(vulnerability_data, "epss_percentile"):
            self.epss_percentile = vulnerability_data.epss_percentile
        if hasattr(vulnerability_data, "package_name"):
            self.package_name = vulnerability_data.package_name
        if hasattr(vulnerability_data, "remediated_at"):
            self.remediated_at = vulnerability_data.remediated_at

    @classmethod
    def create_from_model(cls, vulnerability_data, agent_id, customer_code=None):
        """Create a new vulnerability record from external data"""
        return cls(
            cve_id=getattr(vulnerability_data, "cve_id", "UNKNOWN_CVE"),
            severity=getattr(vulnerability_data, "severity", "UNKNOWN"),
            title=getattr(vulnerability_data, "title", ""),
            references=getattr(vulnerability_data, "references", None),
            status=getattr(vulnerability_data, "status", "Active"),
            epss_score=getattr(vulnerability_data, "epss_score", None),
            epss_percentile=getattr(vulnerability_data, "epss_percentile", None),
            package_name=getattr(vulnerability_data, "package_name", None),
            discovered_at=getattr(vulnerability_data, "detected_at", datetime.utcnow()),
            agent_id=agent_id,
            customer_code=customer_code,
        )

from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import LargeBinary
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT
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
    data_store: list["AgentDataStore"] = Relationship(back_populates="agent")

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


class AgentDataStore(SQLModel, table=True):
    __tablename__ = "agent_datastore"

    id: Optional[int] = Field(primary_key=True)

    # Agent information
    agent_id: str = Field(foreign_key="agents.agent_id", max_length=256, index=True, nullable=False)
    velociraptor_id: str = Field(max_length=256, nullable=False)
    # Removed customer_code - access via agent.customer_code relationship

    # Artifact collection details
    artifact_name: str = Field(max_length=255, nullable=False, index=True)
    flow_id: str = Field(max_length=255, nullable=False, index=True)
    collection_time: datetime = Field(default_factory=datetime.utcnow, index=True)

    # MinIO storage details
    bucket_name: str = Field(max_length=255, nullable=False, default="velociraptor-artifacts")
    object_key: str = Field(max_length=1024, nullable=False)  # Path: agent_id/flow_id/filename.zip
    file_name: str = Field(max_length=255, nullable=False)  # Original file name
    content_type: str = Field(max_length=100, default="application/zip")
    file_size: int = Field(nullable=False)  # File size in bytes
    file_hash: str = Field(max_length=128, nullable=False)  # SHA-256 hash

    # Metadata
    uploaded_by: Optional[int] = Field(default=None)  # User ID who initiated the collection
    notes: Optional[str] = Field(sa_column=Column(Text), nullable=True)

    # Status tracking
    status: str = Field(max_length=50, default="completed", index=True)  # completed, failed, processing
    error_message: Optional[str] = Field(sa_column=Column(Text), nullable=True)

    # Relationship to Agents table
    agent: Optional["Agents"] = Relationship(back_populates="data_store")


class LogEntry(SQLModel, table=True):
    __tablename__ = "log_entries"
    id: Optional[int] = Field(primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
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


class CustomerPortalSettings(SQLModel, table=True):
    __tablename__ = "customer_portal_settings"

    id: Optional[int] = Field(primary_key=True)
    title: str = Field(max_length=255, default="CoPilot")
    logo_base64: Optional[str] = Field(default=None, sa_column=Column(LONGTEXT))  # Use TEXT column for large base64 data
    logo_mime_type: Optional[str] = Field(default=None, max_length=50)  # e.g., "image/png", "image/jpeg"
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[int] = Field(default=None)  # User ID who last updated

    def update_from_request(
        self,
        title: Optional[str] = None,
        logo_base64: Optional[str] = None,
        logo_mime_type: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> None:
        """
        Update settings from request data.
        If a field is explicitly None, restore it to default value.
        """
        # Get default values for restoration
        defaults = self.get_default_values()

        # Update title - if None is passed, restore to default
        if title is not None:
            self.title = title
        elif title is None and hasattr(self, "_explicit_none_title"):
            self.title = defaults["title"]

        # Update logo_base64 - if None is passed, restore to default
        if logo_base64 is not None:
            self.logo_base64 = logo_base64
        elif logo_base64 is None and hasattr(self, "_explicit_none_logo"):
            self.logo_base64 = defaults["logo_base64"]

        # Update logo_mime_type - if None is passed, restore to default
        if logo_mime_type is not None:
            self.logo_mime_type = logo_mime_type
        elif logo_mime_type is None and hasattr(self, "_explicit_none_mime"):
            self.logo_mime_type = defaults["logo_mime_type"]

        self.updated_by = user_id
        self.updated_at = datetime.now()

    @staticmethod
    def get_default_values() -> dict:
        """Get default values for restoration."""
        return {
            "title": "CoPilot",
            "logo_base64": None,
            "logo_mime_type": None,
        }

    @classmethod
    def create_default(cls) -> "CustomerPortalSettings":
        """Create default settings."""
        defaults = cls.get_default_values()
        return cls(
            title=defaults["title"],
            logo_base64=defaults["logo_base64"],
            logo_mime_type=defaults["logo_mime_type"],
        )


class VulnerabilityReport(SQLModel, table=True):
    __tablename__ = "vulnerability_reports"

    id: Optional[int] = Field(primary_key=True)

    # Report metadata
    report_name: str = Field(max_length=255, nullable=False)
    customer_code: str = Field(foreign_key="customers.customer_code", max_length=50, index=True, nullable=False)

    # MinIO storage details
    bucket_name: str = Field(max_length=255, nullable=False, default="vulnerability-reports")
    object_key: str = Field(max_length=1024, nullable=False)  # Path: customer_code/report_name_timestamp.csv
    file_name: str = Field(max_length=255, nullable=False)  # CSV filename
    file_size: int = Field(nullable=False)  # File size in bytes
    file_hash: str = Field(max_length=128, nullable=False)  # SHA-256 hash

    # Report generation details
    generated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    generated_by: int = Field(nullable=False)  # User ID who generated the report

    # Report filters applied
    filters_json: Optional[str] = Field(sa_column=Column(Text), nullable=True)  # JSON string of filters used

    # Statistics
    total_vulnerabilities: int = Field(default=0)
    critical_count: int = Field(default=0)
    high_count: int = Field(default=0)
    medium_count: int = Field(default=0)
    low_count: int = Field(default=0)

    # Status
    status: str = Field(max_length=50, default="completed", index=True)  # completed, failed, processing
    error_message: Optional[str] = Field(sa_column=Column(Text), nullable=True)

    # Relationship to Customers table
    customer: Optional["Customers"] = Relationship()


class SCAReport(SQLModel, table=True):
    __tablename__ = "sca_reports"

    id: Optional[int] = Field(primary_key=True)

    # Report metadata
    report_name: str = Field(max_length=255, nullable=False)
    customer_code: str = Field(foreign_key="customers.customer_code", max_length=50, index=True, nullable=False)

    # MinIO storage details
    bucket_name: str = Field(max_length=255, nullable=False, default="sca-reports")
    object_key: str = Field(max_length=1024, nullable=False)  # Path: customer_code/report_name_timestamp.csv
    file_name: str = Field(max_length=255, nullable=False)  # CSV filename
    file_size: int = Field(nullable=False, default=0)  # File size in bytes
    file_hash: str = Field(max_length=128, nullable=False, default="pending")  # SHA-256 hash

    # Report generation details
    generated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    generated_by: int = Field(nullable=False)  # User ID who generated the report

    # Report filters applied
    filters_json: Optional[str] = Field(sa_column=Column(Text), nullable=True)  # JSON string of filters used

    # SCA Statistics
    total_policies: int = Field(default=0)  # Number of policy results in report
    total_checks: int = Field(default=0)  # Sum of all checks across policies
    passed_count: int = Field(default=0)  # Sum of passed checks
    failed_count: int = Field(default=0)  # Sum of failed checks
    invalid_count: int = Field(default=0)  # Sum of invalid/not applicable checks

    # Status tracking (for background generation)
    status: str = Field(max_length=50, default="processing", index=True)  # processing, completed, failed
    error_message: Optional[str] = Field(sa_column=Column(Text), nullable=True)

    # Relationship to Customers table
    customer: Optional["Customers"] = Relationship()


class EventSources(SQLModel, table=True):
    __tablename__ = "event_sources"

    id: Optional[int] = Field(primary_key=True)
    customer_code: str = Field(
        foreign_key="customers.customer_code",
        max_length=50,
        index=True,
        nullable=False,
    )
    name: str = Field(max_length=255, nullable=False)
    index_pattern: str = Field(max_length=1024, nullable=False)
    event_type: str = Field(max_length=50, nullable=False)  # EDR, EPP, Cloud Integration, Network Security
    time_field: str = Field(max_length=255, nullable=False, default="timestamp")
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    customer: Optional["Customers"] = Relationship()

    class Config:
        # Enforce event_type values at the application level
        pass

    def update_from_model(self, source_data):
        if hasattr(source_data, "name"):
            self.name = source_data.name
        if hasattr(source_data, "index_pattern"):
            self.index_pattern = source_data.index_pattern
        if hasattr(source_data, "event_type"):
            self.event_type = source_data.event_type
        if hasattr(source_data, "time_field"):
            self.time_field = source_data.time_field
        if hasattr(source_data, "enabled"):
            self.enabled = source_data.enabled
        self.updated_at = datetime.utcnow()


class EnabledDashboards(SQLModel, table=True):
    __tablename__ = "enabled_dashboards"
    __table_args__ = (
        UniqueConstraint(
            "customer_code",
            "event_source_id",
            "library_card",
            "template_id",
            name="uq_enabled_dashboard",
        ),
    )

    id: Optional[int] = Field(primary_key=True)
    customer_code: str = Field(
        foreign_key="customers.customer_code",
        max_length=50,
        index=True,
        nullable=False,
    )
    event_source_id: int = Field(foreign_key="event_sources.id", nullable=False, index=True)
    library_card: str = Field(max_length=255, nullable=False)
    template_id: str = Field(max_length=255, nullable=False)
    display_name: str = Field(max_length=255, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    customer: Optional["Customers"] = Relationship()
    event_source: Optional["EventSources"] = Relationship()


class AiAnalystJob(SQLModel, table=True):
    __tablename__ = "ai_analyst_job"

    id: str = Field(primary_key=True, max_length=64)
    alert_id: int = Field(nullable=False, index=True)
    customer_code: str = Field(foreign_key="customers.customer_code", max_length=64, index=True, nullable=False)
    status: str = Field(default="pending", max_length=50, index=True)  # pending, running, completed, failed
    alert_type: Optional[str] = Field(default=None, max_length=64)
    triggered_by: str = Field(max_length=50, nullable=False)  # scheduled, manual, webhook
    template_used: Optional[str] = Field(default=None, max_length=128)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(sa_column=Column(Text), default=None)

    customer: Optional["Customers"] = Relationship()
    reports: list["AiAnalystReport"] = Relationship(back_populates="job")


class AiAnalystReport(SQLModel, table=True):
    __tablename__ = "ai_analyst_report"

    id: Optional[int] = Field(primary_key=True)
    job_id: str = Field(foreign_key="ai_analyst_job.id", max_length=64, nullable=False, index=True)
    alert_id: int = Field(nullable=False, index=True)
    customer_code: str = Field(foreign_key="customers.customer_code", max_length=64, index=True, nullable=False)
    severity_assessment: Optional[str] = Field(default=None, max_length=50)  # Critical, High, Medium, Low, Informational
    report_markdown: Optional[str] = Field(sa_column=Column(LONGTEXT), default=None)
    summary: Optional[str] = Field(sa_column=Column(Text), default=None)
    recommended_actions: Optional[str] = Field(sa_column=Column(Text), default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    job: Optional["AiAnalystJob"] = Relationship(back_populates="reports")
    iocs: list["AiAnalystIoc"] = Relationship(back_populates="report")
    customer: Optional["Customers"] = Relationship()


class AiAnalystIoc(SQLModel, table=True):
    __tablename__ = "ai_analyst_ioc"

    id: Optional[int] = Field(primary_key=True)
    report_id: int = Field(foreign_key="ai_analyst_report.id", nullable=False, index=True)
    alert_id: int = Field(nullable=False, index=True)
    customer_code: str = Field(foreign_key="customers.customer_code", max_length=64, index=True, nullable=False)
    ioc_value: str = Field(max_length=512, nullable=False)
    ioc_type: str = Field(max_length=50, nullable=False)  # ip, domain, hash, process, url, user, command
    vt_verdict: str = Field(default="unknown", max_length=50)  # malicious, suspicious, clean, unknown
    vt_score: Optional[str] = Field(default=None, max_length=32)
    details: Optional[str] = Field(sa_column=Column(Text), default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    report: Optional["AiAnalystReport"] = Relationship(back_populates="iocs")
    customer: Optional["Customers"] = Relationship()
    ioc_reviews: list["AiAnalystIocReview"] = Relationship(back_populates="ioc")


class AiAnalystReview(SQLModel, table=True):
    __tablename__ = "ai_analyst_review"
    __table_args__ = (
        UniqueConstraint(
            "report_id",
            "reviewer_user_id",
            name="uq_ai_analyst_review_report_reviewer",
        ),
    )

    id: Optional[int] = Field(primary_key=True)
    report_id: int = Field(foreign_key="ai_analyst_report.id", nullable=False, index=True)
    alert_id: int = Field(nullable=False, index=True)
    customer_code: str = Field(foreign_key="customers.customer_code", max_length=64, index=True, nullable=False)
    reviewer_user_id: int = Field(nullable=False, index=True)
    overall_verdict: Optional[str] = Field(default=None, max_length=4)  # up, down
    template_choice: Optional[str] = Field(default=None, max_length=7)  # correct, wrong, partial
    template_used: Optional[str] = Field(default=None, max_length=128)
    rating_instructions: Optional[int] = Field(default=None)  # 1–5
    rating_artifacts: Optional[int] = Field(default=None)  # 1–5
    rating_severity: Optional[int] = Field(default=None)  # 1–5
    missing_steps: Optional[str] = Field(sa_column=Column(Text), default=None)
    suggested_edits: Optional[str] = Field(sa_column=Column(Text), default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: Optional[datetime] = Field(default=None)

    report: Optional["AiAnalystReport"] = Relationship()
    customer: Optional["Customers"] = Relationship()
    ioc_reviews: list["AiAnalystIocReview"] = Relationship(back_populates="review")
    palace_lessons: list["AiAnalystPalaceLesson"] = Relationship(back_populates="review")


class AiAnalystIocReview(SQLModel, table=True):
    __tablename__ = "ai_analyst_ioc_review"

    id: Optional[int] = Field(primary_key=True)
    review_id: int = Field(foreign_key="ai_analyst_review.id", nullable=False, index=True)
    ioc_id: int = Field(foreign_key="ai_analyst_ioc.id", nullable=False, index=True)
    verdict_correct: bool = Field(nullable=False)
    note: Optional[str] = Field(sa_column=Column(Text), default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    review: Optional["AiAnalystReview"] = Relationship(back_populates="ioc_reviews")
    ioc: Optional["AiAnalystIoc"] = Relationship(back_populates="ioc_reviews")


class AiAnalystPalaceLesson(SQLModel, table=True):
    __tablename__ = "ai_analyst_palace_lesson"

    id: Optional[int] = Field(primary_key=True)
    review_id: Optional[int] = Field(foreign_key="ai_analyst_review.id", default=None, index=True)  # nullable — can be standalone
    customer_code: str = Field(foreign_key="customers.customer_code", max_length=64, index=True, nullable=False)
    lesson_type: str = Field(max_length=20, nullable=False)  # environment, false_positives, assets, threat_intel
    lesson_text: str = Field(sa_column=Column(Text), nullable=False)
    durability: str = Field(default="durable", max_length=8)  # one_off, durable
    status: str = Field(default="pending", max_length=8, index=True)  # pending, ingested, failed, expired
    # drawer_id returned by mempalace add_drawer — required to call
    # delete_drawer later when the durability sweeper expires one-offs.
    # Nullable because legacy rows predate this column and because the
    # drainer may fail to capture it if NanoClaw returns a malformed body.
    drawer_id: Optional[str] = Field(default=None, max_length=64, index=True)
    ingested_at: Optional[datetime] = Field(default=None)
    # Timestamp of the sweeper's delete_drawer call. Set when status flips
    # from 'ingested' → 'expired' so audit queries can tell "never swept"
    # apart from "swept but failed".
    expired_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    review: Optional["AiAnalystReview"] = Relationship(back_populates="palace_lessons")
    customer: Optional["Customers"] = Relationship()

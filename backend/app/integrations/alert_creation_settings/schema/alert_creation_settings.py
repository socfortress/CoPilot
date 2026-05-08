from typing import List
from typing import Optional

from pydantic import BaseModel


class AlertCreationEventConfigCreate(BaseModel):
    event_id: str
    field: str
    value: str


class EventOrderCreate(BaseModel):
    order_label: str
    event_configs: List[AlertCreationEventConfigCreate]


class AlertCreationSettingsCreate(BaseModel):
    customer_code: str
    customer_name: str
    excluded_wazuh_rules: Optional[str] = None
    excluded_suricata_rules: Optional[str] = None
    timefield: Optional[str] = None
    office365_organization_id: Optional[str] = None
    iris_customer_id: Optional[int] = None
    iris_customer_name: Optional[str] = None
    iris_index: Optional[str] = None
    grafana_url: Optional[str] = None
    misp_url: Optional[str] = None
    opencti_url: Optional[str] = None
    custom_message: Optional[str] = None
    shuffle_endpoint: Optional[str] = None
    nvd_url: Optional[str] = "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId"
    event_orders: Optional[List[EventOrderCreate]] = None


class AlertCreationEventConfigResponse(BaseModel):
    event_id: str
    field: str
    value: str


class EventOrderResponse(BaseModel):
    order_label: str
    event_configs: List[AlertCreationEventConfigResponse]


class AlertCreationSettingsResponse(BaseModel):
    customer_code: str
    customer_name: str
    excluded_wazuh_rules: Optional[str] = None
    excluded_suricata_rules: Optional[str] = None
    timefield: Optional[str] = None
    office365_organization_id: Optional[str] = None
    iris_customer_id: Optional[int] = None
    iris_customer_name: Optional[str] = None
    iris_index: Optional[str] = None
    grafana_url: Optional[str] = None
    misp_url: Optional[str] = None
    opencti_url: Optional[str] = None
    custom_message: Optional[str] = None
    shuffle_endpoint: Optional[str] = None
    nvd_url: Optional[str] = "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId"
    event_orders: Optional[List[EventOrderResponse]] = None

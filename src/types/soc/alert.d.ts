import type { AlertSourceContent } from "../alerts"

export interface SocAlert {
	alert_classification_id: string | null
	alert_context: AlertContext
	alert_creation_time: string
	alert_customer_id: number
	alert_description: string
	alert_id: number
	alert_note: null | string
	alert_owner_id: number | null
	alert_resolution_status_id: string | null
	alert_severity_id: number
	alert_source_content: AlertSourceContent
	alert_source_event_time: string
	alert_source_link: null | string
	alert_source_ref: string | null
	alert_source: AlertSource
	alert_status_id: number
	alert_tags: null | string
	alert_title: string
	alert_uuid: string
	assets: any[]
	cases: any[]
	classification: string | null
	comments: any[]
	customer: Customer
	iocs: any[]
	modification_history: { [key: string]: ModificationHistory }
	owner: Owner | null
	resolution_status: string | null
	severity: Severity
	status: Status
}

type IPAddress = `${number}.${number}.${number}.${number}`

export interface AlertContext {
	alert_id: string
	alert_level: number
	alert_name: string
	asset_ip: IPAddress
	asset_name: string
	asset_type: number
	customer_id?: string
	process_id: string
	rule_id: string
	rule_mitre_id: string
	rule_mitre_tactic: string
	rule_mitre_technique: string
}

export enum AlertSource {
	CoPilot = "CoPilot",
	Wazuh = "Wazuh"
}

export interface Customer {
	customer_description: null | string
	custom_attributes: { [key: string]: any } | null
	creation_date: string
	customer_sla: null | string
	customer_name: string
	last_update_date: string
	client_uuid: string
	customer_id: number
}

export interface ModificationHistory {
	user: string
	user_id: number
	action: string
}

export interface Owner {
	id: number
	user_login: string
	user_name: string
	user_email: string
}

export interface Severity {
	severity_description: string
	severity_name: SeverityNameEnum
	severity_id: number
}

export enum SeverityNameEnum {
	High = "High"
}

export interface Status {
	status_description: string
	status_name: StatusName
	status_id: number
}

export enum StatusName {
	Assigned = "Assigned"
}

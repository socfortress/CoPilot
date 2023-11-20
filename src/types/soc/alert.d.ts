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
type Latitude = number
type Longitude = number
type Location = `${Latitude},${Longitude}`

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

export interface AlertSourceContent {
	agent_id: string
	agent_ip_city_name?: string
	agent_ip_country_code?: string
	agent_ip_geolocation?: Location
	agent_ip_reserved_ip?: boolean
	agent_ip: IPAddress
	agent_labels_customer: string
	agent_name: string
	ask_socfortress_message?: string
	data_action?: string
	data_authors?: string
	data_calendarTime?: string
	data_columns_cid?: string
	data_columns_cmdline?: string
	data_columns_cwd?: string
	data_columns_duration?: string
	data_columns_exit_code?: string
	data_columns_gid?: string
	data_columns_ntime?: string
	data_columns_parent?: string
	data_columns_path?: string
	data_columns_pid?: string
	data_columns_probe_error?: string
	data_columns_syscall?: string
	data_columns_tid?: string
	data_columns_uid?: string
	data_counter?: string
	data_document?: string
	data_epoch?: string
	data_event_CreationUtcTime?: string
	data_event_Image?: string
	data_event_ProcessGuid?: string
	data_event_ProcessId?: string
	data_event_RuleName?: string
	data_event_TargetFilename?: string
	data_event_User?: string
	data_event_UtcTime?: string
	data_falsepositives?: string
	data_group?: DataGroup
	data_hostIdentifier?: string
	data_id?: string
	data_kind?: DataKind
	data_level?: DataLevel
	data_logsource_category?: DataLogsourceCategory
	data_logsource_product?: DataLogsourceProduct
	data_name?: string
	data_numerics?: string
	data_path?: string
	data_references?: string
	data_source?: DataSource
	data_status?: string
	data_system_Channel?: string
	data_system_Computer?: string
	data_system_Correlation?: string
	data_system_EventID?: string
	data_system_EventRecordID?: string
	data_system_Execution_attributes_ProcessID?: string
	data_system_Execution_attributes_ThreadID?: string
	data_system_Keywords?: string
	data_system_Level?: string
	data_system_Opcode?: string
	data_system_Provider_attributes_Guid?: string
	data_system_Provider_attributes_Name?: string
	data_system_Security_attributes_UserID?: string
	data_system_Task?: string
	data_system_TimeCreated_attributes_SystemTime?: string
	data_system_Version?: string
	data_tags?: string
	data_timestamp?: string
	data_unixTime?: string
	data_win_eventdata_callTrace?: string
	data_win_eventdata_company?: string
	data_win_eventdata_creationUtcTime?: string
	data_win_eventdata_description?: string
	data_win_eventdata_fileVersion?: string
	data_win_eventdata_grantedAccess?: string
	data_win_eventdata_hashes?: string
	data_win_eventdata_image?: string
	data_win_eventdata_imageLoaded?: string
	data_win_eventdata_originalFileName?: string
	data_win_eventdata_processGuid?: string
	data_win_eventdata_processId?: string
	data_win_eventdata_product?: string
	data_win_eventdata_ruleName?: string
	data_win_eventdata_signatureStatus?: string
	data_win_eventdata_signed?: string
	data_win_eventdata_sourceImage?: string
	data_win_eventdata_sourceProcessGUID?: string
	data_win_eventdata_sourceProcessId?: string
	data_win_eventdata_sourceThreadId?: string
	data_win_eventdata_sourceUser?: string
	data_win_eventdata_targetFilename?: string
	data_win_eventdata_targetImage?: string
	data_win_eventdata_targetProcessGUID?: string
	data_win_eventdata_targetProcessId?: string
	data_win_eventdata_targetUser?: string
	data_win_eventdata_user?: string
	data_win_eventdata_utcTime?: string
	data_win_system_channel?: string
	data_win_system_computer?: string
	data_win_system_eventID?: string
	data_win_system_eventRecordID?: string
	data_win_system_keywords?: string
	data_win_system_level?: string
	data_win_system_message?: string
	data_win_system_opcode?: string
	data_win_system_processID?: string
	data_win_system_providerGuid?: string
	data_win_system_providerName?: string
	data_win_system_severityValue?: string
	data_win_system_systemTime?: string
	data_win_system_task?: string
	data_win_system_threadID?: string
	data_win_system_version?: string
	decoder_name: string
	gl2_accounted_message_size: number
	gl2_message_id: string
	gl2_processing_error: string
	gl2_remote_ip: IPAddress
	gl2_remote_port: number
	gl2_source_input: string
	gl2_source_node: string
	hash_sha256?: string
	id: string
	location: string
	manager_name: string
	message: string
	msg_timestamp: string
	parent_process_id?: string
	process_cmd_line?: string
	process_id?: string
	process_image?: string
	process_name?: string
	rule_description: string
	rule_firedtimes: number
	rule_group1: DataLogsourceProduct
	rule_group2: string
	rule_group3?: DataSource
	rule_groups: string
	rule_id: string
	rule_level: number
	rule_mail: boolean
	rule_mitre_id?: string
	rule_mitre_tactic?: string
	rule_mitre_technique?: string
	sha256?: string
	sigma_name_encoded?: string
	source_reserved_ip: boolean
	source: IPAddress
	streams: string[]
	syslog_level: SyslogLevel
	syslog_type: SyslogType
	timestamp_utc: string
	timestamp: string
	true: number
}

export enum DataGroup {
	Sigma = "Sigma"
}

export enum DataKind {
	Individual = "individual"
}

export enum DataLevel {
	High = "high"
}

export enum DataLogsourceCategory {
	FileEvent = "file_event"
}

export enum DataLogsourceProduct {
	Osquery = "osquery",
	Sysmon = "sysmon",
	Windows = "windows"
}

export enum DataSource {
	Sigma = "sigma",
	Windows = "windows"
}

export enum SyslogLevel {
	Alert = "ALERT"
}

export enum SyslogType {
	Wazuh = "wazuh"
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

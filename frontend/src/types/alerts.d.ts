export interface AlertsByHost {
	agent_name: string
	number_of_alerts: number
}

export interface AlertsByRule {
	rule: string
	number_of_alerts: number
}

export interface AlertsByRulePerHost {
	agent_name: string
	number_of_alerts: number
	rule: string
}

export interface AlertsSummary {
	index_name: string
	total_alerts: number
	alerts: Alert[]
}

type IPAddress = `${number}.${number}.${number}.${number}`
type Timestamp = number
type Latitude = number
type Longitude = number
type Location = `${Latitude},${Longitude}`

export interface Alert {
	_index: string
	_id: string
	_score: null
	_source: AlertSourceContent
	sort: Timestamp[]
}

export interface AlertSourceContent {
	agent_id: string
	agent_ip_city_name?: string
	agent_ip_country_code?: string
	agent_ip_geolocation?: AlertSourceAgentIPGeolocation
	agent_ip_reserved_ip?: boolean
	agent_ip: AlertSourceAgentIP
	agent_labels_customer: string
	agent_name: string
	alert_url?: string
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
	data_group?: AlertSourceDataGroup
	data_hostIdentifier?: string
	data_id?: string
	data_kind?: AlertSourceDataKind
	data_level?: AlertSourceDataLevelEnum
	data_logsource_category?: AlertSourceDataLogsourceCategory
	data_logsource_product?: AlertSourceDataLogsourceProduct
	data_name?: string
	data_numerics?: string
	data_path?: string
	data_references?: string
	data_source?: AlertSourceDataLogsourceProduct
	data_status?: AlertSourceDataStatus
	data_system_Channel?: string
	data_system_Computer?: string
	data_system_Correlation?: string | null
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
	data_vulnerability_assigner?: string
	data_vulnerability_cve_version?: string
	data_vulnerability_cve?: string
	data_vulnerability_cvss_cvss3_base_score?: string
	data_vulnerability_cvss_cvss3_vector_access_complexity?: string
	data_vulnerability_cvss_cvss3_vector_attack_vector?: string
	data_vulnerability_cvss_cvss3_vector_availability?: AlertSourceDataLevelEnum
	data_vulnerability_cvss_cvss3_vector_confidentiality_impact?: AlertSourceDataLevelEnum
	data_vulnerability_cvss_cvss3_vector_integrity_impact?: AlertSourceDataLevelEnum
	data_vulnerability_cvss_cvss3_vector_privileges_required?: string
	data_vulnerability_cvss_cvss3_vector_scope?: string
	data_vulnerability_cvss_cvss3_vector_user_interaction?: string
	data_vulnerability_cwe_reference?: string
	data_vulnerability_package_architecture?: string
	data_vulnerability_package_condition?: string
	data_vulnerability_package_name?: string
	data_vulnerability_package_version?: string
	data_vulnerability_published?: string
	data_vulnerability_rationale?: string
	data_vulnerability_references?: string
	data_vulnerability_severity?: string
	data_vulnerability_status?: string
	data_vulnerability_title?: string
	data_vulnerability_type?: string
	data_vulnerability_updated?: string
	data_win_eventdata_callTrace?: string
	data_win_eventdata_commandLine?: string
	data_win_eventdata_company?: string
	data_win_eventdata_currentDirectory?: string
	data_win_eventdata_description?: string
	data_win_eventdata_fileVersion?: string
	data_win_eventdata_grantedAccess?: string
	data_win_eventdata_hashes?: string
	data_win_eventdata_image?: string
	data_win_eventdata_integrityLevel?: AlertSourceDataWinEventdataIntegrityLevel
	data_win_eventdata_logonGuid?: string
	data_win_eventdata_logonId?: string
	data_win_eventdata_originalFileName?: string
	data_win_eventdata_parentCommandLine?: string
	data_win_eventdata_parentImage?: string
	data_win_eventdata_parentProcessGuid?: string
	data_win_eventdata_parentProcessId?: string
	data_win_eventdata_parentUser?: string
	data_win_eventdata_processGuid?: string
	data_win_eventdata_processId?: string
	data_win_eventdata_product?: string
	data_win_eventdata_ruleName?: string
	data_win_eventdata_sourceImage?: string
	data_win_eventdata_sourceProcessGUID?: string
	data_win_eventdata_sourceProcessId?: string
	data_win_eventdata_sourceThreadId?: string
	data_win_eventdata_sourceUser?: string
	data_win_eventdata_targetImage?: string
	data_win_eventdata_targetProcessGUID?: string
	data_win_eventdata_targetProcessId?: string
	data_win_eventdata_targetUser?: string
	data_win_eventdata_terminalSessionId?: string
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
	data_win_system_severityValue?: AlertSourceDataWinSystemSeverityValue
	data_win_system_systemTime?: string
	data_win_system_task?: string
	data_win_system_threadID?: string
	data_win_system_version?: string
	decoder_name: AlertSourceDecoderName
	epss_cve?: string
	epss_date?: string
	epss_epss?: string
	epss_percentile?: string
	gl2_accounted_message_size: number
	gl2_message_id: string
	gl2_processing_error: string
	gl2_remote_ip: AlertSourceIP
	gl2_remote_port: number
	gl2_source_input: string
	gl2_source_node: string
	hash_sha256?: string
	id: string
	location: string
	manager_name: string
	message: string
	msg_timestamp?: string
	parent_process_id?: string
	process_cmd_line?: string
	process_id?: string
	process_image?: string
	process_name?: string
	rule_description: string
	rule_firedtimes: number
	rule_gdpr?: string
	rule_group1: string
	rule_group2?: string
	rule_group3?: AlertSourceDataLogsourceProduct
	rule_groups: string
	rule_id: string
	rule_level: number
	rule_mail: boolean
	rule_mitre_id?: string
	rule_mitre_tactic?: string
	rule_mitre_technique?: string
	rule_pci_dss?: string
	rule_tsc?: string
	sha256?: string
	sigma_name_encoded?: string
	source_reserved_ip: boolean
	source: AlertSourceIP
	streams: string[]
	syslog_level: AlertSourceSyslogLevel
	syslog_type: AlertSourceSyslogType
	timestamp_utc: string
	timestamp: string
	type?: string
	true: number
}

export type AlertSourceAgentIP = IPAddress
export type AlertSourceIP = IPAddress
export type AlertSourceAgentIPGeolocation = Location

export enum AlertSourceDataGroup {
	Sigma = "Sigma"
}

export enum AlertSourceDataKind {
	Individual = "individual"
}

export enum AlertSourceDataLevelEnum {
	High = "high"
}

export enum AlertSourceDataLogsourceCategory {
	FileEvent = "file_event"
}

export enum AlertSourceDataLogsourceProduct {
	Sigma = "sigma",
	Windows = "windows",
	Osquery = "osquery",
	Sysmon = "sysmon"
}

export enum AlertSourceDataStatus {
	Experimental = "experimental"
}

export enum AlertSourceDataWinEventdataIntegrityLevel {
	System = "System"
}

export enum AlertSourceDataWinSystemSeverityValue {
	Information = "INFORMATION"
}

export enum AlertSourceDecoderName {
	JSON = "json",
	WindowsEventchannel = "windows_eventchannel"
}

export enum AlertSourceSyslogLevel {
	Alert = "ALERT"
}

export enum AlertSourceSyslogType {
	Wazuh = "wazuh"
}

export interface WazuhRuleExclude {
	wazuh_rule: string
	explanation: string
}

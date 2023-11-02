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
	_source: AlertSource
	sort: Timestamp[]
}

export interface AlertSource {
	source_reserved_ip: boolean
	data_win_system_eventRecordID?: string
	agent_id: string
	agent_name: string
	data_win_eventdata_sourceProcessGUID?: string
	gl2_remote_ip: AlertSourceGl2RemoteIP
	data_win_system_eventID?: string
	gl2_remote_port: number
	agent_labels_customer: string
	agent_ip_city_name?: string
	source: AlertSourceGl2RemoteIP
	data_win_eventdata_targetImage?: string
	gl2_source_input: string
	rule_level: number
	data_win_eventdata_sourceUser?: string
	data_win_system_task?: string
	timestamp_utc: string
	syslog_type: AlertSourceSyslogType
	data_win_system_threadID?: string
	rule_description: string
	gl2_source_node: string
	id: string
	data_win_eventdata_grantedAccess?: string
	data_win_eventdata_sourceImage?: string
	rule_mitre_tactic?: string
	gl2_accounted_message_size: number
	data_win_eventdata_utcTime?: string
	streams: string[]
	rule_mitre_id?: string
	gl2_message_id: string
	data_win_system_computer?: string
	data_win_eventdata_ruleName?: string
	agent_ip: AlertSourceAgentIP
	true: number
	rule_groups: string
	data_win_system_keywords?: string
	data_win_system_level?: string
	data_win_eventdata_targetProcessGUID?: string
	data_win_system_severityValue?: AlertSourceDataWinSystemSeverityValue
	data_win_eventdata_targetUser?: string
	agent_ip_geolocation?: AlertSourceAgentIPGeolocation
	rule_mitre_technique?: string
	rule_firedtimes: number
	data_win_system_systemTime?: string
	rule_mail: boolean
	decoder_name: AlertSourceDecoderName
	agent_ip_country_code?: string
	data_win_system_processID?: string
	data_win_system_channel?: string
	syslog_level: AlertSourceSyslogLevel
	data_win_system_providerName?: string
	data_win_system_version?: string
	data_win_system_providerGuid?: string
	timestamp: string
	data_win_eventdata_callTrace?: string
	data_win_system_opcode?: string
	gl2_processing_error: string
	data_win_eventdata_sourceProcessId?: string
	message: string
	rule_id: string
	manager_name: string
	location: string
	data_win_eventdata_targetProcessId?: string
	rule_group3?: AlertSourceDataLogsourceProduct
	data_win_system_message?: string
	data_win_eventdata_sourceThreadId?: string
	msg_timestamp?: string
	rule_group2?: string
	rule_group1: string
	data_system_Task?: string
	data_system_Correlation?: string | null
	data_system_Version?: string
	data_level?: AlertSourceDataLevelEnum
	data_event_ProcessId?: string
	data_system_Opcode?: string
	data_status?: AlertSourceDataStatus
	data_system_Computer?: string
	data_document?: string
	data_event_UtcTime?: string
	data_source?: AlertSourceDataLogsourceProduct
	data_system_Security_attributes_UserID?: string
	data_timestamp?: string
	data_system_Level?: string
	data_event_CreationUtcTime?: string
	data_system_Execution_attributes_ProcessID?: string
	data_system_EventRecordID?: string
	process_id?: string
	data_system_TimeCreated_attributes_SystemTime?: string
	data_event_RuleName?: string
	data_logsource_category?: AlertSourceDataLogsourceCategory
	data_system_Keywords?: string
	sigma_name_encoded?: string
	data_group?: AlertSourceDataGroup
	data_event_User?: string
	data_path?: string
	data_system_Provider_attributes_Name?: string
	data_name?: string
	data_id?: string
	data_tags?: string
	data_kind?: AlertSourceDataKind
	data_logsource_product?: AlertSourceDataLogsourceProduct
	ask_socfortress_message?: string
	data_system_Channel?: string
	data_references?: string
	data_event_ProcessGuid?: string
	data_falsepositives?: string
	data_event_Image?: string
	data_system_Execution_attributes_ThreadID?: string
	data_system_EventID?: string
	data_system_Provider_attributes_Guid?: string
	data_event_TargetFilename?: string
	data_authors?: string
	data_vulnerability_package_architecture?: string
	data_vulnerability_cvss_cvss3_vector_integrity_impact?: AlertSourceDataLevelEnum
	rule_tsc?: string
	data_vulnerability_cve_version?: string
	epss_cve?: string
	data_vulnerability_cvss_cvss3_vector_confidentiality_impact?: AlertSourceDataLevelEnum
	epss_percentile?: string
	data_vulnerability_cvss_cvss3_vector_availability?: AlertSourceDataLevelEnum
	epss_epss?: string
	data_vulnerability_title?: string
	data_vulnerability_updated?: string
	data_vulnerability_type?: string
	data_vulnerability_references?: string
	epss_date?: string
	data_vulnerability_rationale?: string
	data_vulnerability_package_name?: string
	data_vulnerability_cvss_cvss3_vector_attack_vector?: string
	data_vulnerability_published?: string
	data_vulnerability_assigner?: string
	data_vulnerability_cvss_cvss3_base_score?: string
	data_vulnerability_package_version?: string
	rule_gdpr?: string
	data_vulnerability_severity?: string
	data_vulnerability_cvss_cvss3_vector_scope?: string
	data_vulnerability_cvss_cvss3_vector_access_complexity?: string
	rule_pci_dss?: string
	data_vulnerability_cwe_reference?: string
	data_vulnerability_cvss_cvss3_vector_user_interaction?: string
	data_vulnerability_cve?: string
	data_vulnerability_cvss_cvss3_vector_privileges_required?: string
	data_vulnerability_package_condition?: string
	data_vulnerability_status?: string
	parent_process_id?: string
	data_columns_cwd?: string
	data_calendarTime?: string
	data_counter?: string
	data_columns_duration?: string
	process_name?: string
	process_cmd_line?: string
	data_hostIdentifier?: string
	data_columns_probe_error?: string
	process_image?: string
	data_columns_uid?: string
	data_columns_gid?: string
	data_columns_syscall?: string
	data_columns_cid?: string
	data_columns_exit_code?: string
	data_columns_ntime?: string
	data_columns_cmdline?: string
	data_columns_tid?: string
	data_columns_pid?: string
	data_numerics?: string
	data_columns_path?: string
	data_unixTime?: string
	data_action?: string
	data_epoch?: string
	data_columns_parent?: string
	data_win_eventdata_description?: string
	data_win_eventdata_user?: string
	sha256?: string
	data_win_eventdata_originalFileName?: string
	data_win_eventdata_company?: string
	data_win_eventdata_parentUser?: string
	data_win_eventdata_integrityLevel?: AlertSourceDataWinEventdataIntegrityLevel
	data_win_eventdata_currentDirectory?: string
	agent_ip_reserved_ip?: boolean
	data_win_eventdata_hashes?: string
	data_win_eventdata_image?: string
	data_win_eventdata_parentProcessGuid?: string
	data_win_eventdata_parentProcessId?: string
	data_win_eventdata_fileVersion?: string
	data_win_eventdata_parentImage?: string
	data_win_eventdata_processGuid?: string
	data_win_eventdata_commandLine?: string
	data_win_eventdata_processId?: string
	data_win_eventdata_parentCommandLine?: string
	data_win_eventdata_terminalSessionId?: string
	hash_sha256?: string
	data_win_eventdata_logonGuid?: string
	data_win_eventdata_logonId?: string
	data_win_eventdata_product?: string
}

export type AlertSourceAgentIP = IPAddress
export type AlertSourceGl2RemoteIP = IPAddress
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
	Windows = "windows"
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

export interface MitreTechnique {
	technique_id: string
	technique_name: string
	count: number
	last_seen: string
	tactics: MitreTactic[]
}

export interface MitreTactic {
	id: string
	name: string
	short_name: string
}

export interface MitreTechniqueDetails {
	description: string
	name: string
	id: string
	modified_time: Date
	created_time: Date
	tactics: string[]
	url: string
	source: string
	external_id: string
	references: MitreReference[]
	mitigations: string[]
	subtechnique_of: string | null
	techniques: string[] | null
	groups: string[]
	software: string[]
	mitre_detection: string
	mitre_version: string
	deprecated: number
	remote_support: number
	network_requirements: number
	platforms: string[]
	data_sources: string[]
	is_subtechnique: boolean
}

export interface MitreReference {
	url: string
	description: string
	source: string
}

export interface MitreMitigationDetails {
	mitre_version: string
	deprecated: number
	description: string
	name: string
	id: string
	modified_time: Date
	created_time: Date
	techniques: string[]
	references: MitreReference[]
	url: string
	source: string
	external_id: string
}

export interface MitreSoftwareDetails {
	mitre_version: string
	deprecated: number
	description: string
	name: string
	id: string
	modified_time: Date
	created_time: Date
	groups: string[]
	techniques: string[]
	references: MitreReference[]
	url: string
	source: string
	external_id: string
	platforms: null | string[]
	aliases: null | string[]
	type: null | string
}

export interface MitreTacticDetails {
	description: string
	name: string
	id: string
	modified_time: Date
	created_time: Date
	short_name: string
	techniques: string[]
	references: MitreReference[]
	url: string
	source: string
	external_id: string
}

export interface MitreGroupDetails {
	mitre_version: string
	deprecated: number
	description: string
	name: string
	id: string
	modified_time: Date
	created_time: Date
	software: string[]
	techniques: string[]
	references: MitreReference[]
	url: string
	source: string
	external_id: string
	aliases: null | string[]
	country: null | string
}

export interface MitreEventDetails {
	data_source_ip: string
	data_host_architecture: string
	agent_id: string
	agent_name: string
	gl2_remote_ip: string
	data_resource: string
	agent_labels_customer: string
	data_ecs_version: string
	timestamp_utc: Date
	data_host_os_codename: string
	syslog_type: string
	gl2_source_node: string
	id: string
	data_dns_question_etld_plus_one: string
	data_server_port: string
	rule_mitre_tactic: string
	gl2_accounted_message_size: number
	data_agent_type: string
	streams: string[]
	rule_mitre_id: string
	data_destination_bytes: string
	data_event_dataset: string
	"data_@metadata_beat": string
	agent_ip: string
	data_source_port: string
	data_host_id: string
	data_event_kind: string
	data_network_protocol: string
	dns_response_code: string
	dns_query: string
	data_dns_response_code: string
	data_network_community_id: string
	data_dns_flags_truncated_response: string
	rule_mail: boolean
	data_dns_opt_udp_size: string
	data_event_category: string
	data_dns_flags_recursion_available: string
	data_dns_opt_version: string
	timestamp: Date
	data_host_mac: string
	data_agent_id: string
	data_destination_port: string
	data_dns_type: string
	traffic_direction: string
	rule_id: string
	data_dns_question_class: string
	cluster_node: string
	dst_port: string
	"data_@timestamp": Date
	data_event_duration: string
	data_host_os_platform: string
	data_host_name: string
	data_dns_flags_recursion_desired: string
	data_dns_question_subdomain: string
	gl2_remote_port: number
	data_host_os_type: string
	source: string
	gl2_source_input: string
	rule_level: number
	data_event_type: string
	data_host_os_family: string
	data_dns_additionals_count: string
	data_dns_flags_authentic_data: string
	protocol: string
	data_dns_answers: string
	data_event_start: Date
	data_agent_ephemeral_id: string
	rule_description: string
	data_related_ip: string
	data_agent_version: string
	data_status: string
	data_query: string
	"data_@metadata_type": string
	data_method: string
	data_dns_question_registered_domain: string
	data_server_ip: string
	gl2_message_id: string
	data_dns_answers_count: string
	data_network_type: string
	data_dns_opt_ext_rcode: string
	data_client_port: string
	data_network_bytes: string
	data_dns_resolved_ip: string
	data_host_containerized: string
	true: number
	data_host_hostname: string
	rule_groups: string
	data_client_bytes: string
	data_dns_question_type: string
	data_host_ip: string
	data_destination_ip: string
	rule_mitre_technique: string
	rule_firedtimes: number
	data_network_transport: string
	dst_ip: string
	src_ip: string
	decoder_name: string
	syslog_level: string
	data_dns_op_code: string
	data_host_os_version: string
	data_host_os_kernel: string
	cluster_name: string
	data_source_bytes: string
	gl2_processing_error: string
	data_dns_opt_do: string
	data_dns_authorities_count: string
	data_dns_question_name: string
	message: string
	dns_answer: string
	data_dns_id: string
	src_port: string
	manager_name: string
	data_network_direction: string
	data_dns_question_top_level_domain: string
	data_event_end: Date
	data_agent_name: string
	data_client_ip: string
	data_dns_flags_authoritative: string
	data_server_bytes: string
	data_type: string
	data_dns_header_flags: string
	data_dns_flags_checking_disabled: string
	location: string
	"data_@metadata_version": string
	data_host_os_name: string
	rule_group3: string
	msg_timestamp: Date
	rule_group2: string
	rule_group1: string
}

export interface MitreAtomicTest {
	technique_id: string
	technique_name: string
	test_count: number
	categories: MitreAtomicTestCategory[]
	has_prerequisites: boolean
}

export enum MitreAtomicTestCategory {
	Linux = "linux",
	Macos = "macos",
	Windows = "windows"
}

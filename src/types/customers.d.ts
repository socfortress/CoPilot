// required: customer_code, customer_name, contact_last_name, contact_first_name
export interface Customer {
	customer_code: string
	customer_name: string
	contact_last_name: string
	contact_first_name: string
	parent_customer_code: string | null
	phone: string
	address_line1: string
	address_line2: string
	city: string
	state: string
	postal_code: string
	country: string
	customer_type: string
	logo_file: string
}

// all required
export interface CustomerMeta {
	customer_meta_graylog_index: string
	customer_meta_graylog_stream: string
	customer_meta_grafana_org_id: string
	customer_meta_wazuh_group: string
	customer_meta_index_retention: string
	customer_meta_wazuh_registration_port: string
	customer_meta_wazuh_log_ingestion_port: string
	customer_meta_wazuh_auth_password: string
}

export type CustomerHealthcheckSource = "wazuh" | "velociraptor"

export interface CustomerAgentHealth {
	id: number
	os: string
	label: string
	wazuh_last_seen: string
	velociraptor_last_seen: string
	velociraptor_agent_version: string
	ip_address: string
	agent_id: string
	hostname: string
	critical_asset: boolean
	velociraptor_id: string
	wazuh_agent_version: string
	customer_code: string
	unhealthy_wazuh_agent: boolean | null
	unhealthy_velociraptor_agent: boolean | null
	unhealthy_recent_logs_collected: null
}

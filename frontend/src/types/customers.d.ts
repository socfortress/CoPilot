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

export interface CustomerMeta {
	id: number
	customer_code: string
	customer_name: string
	customer_meta_graylog_index: string
	customer_meta_graylog_stream: string
	customer_meta_grafana_org_id: string
	customer_meta_wazuh_group: string
	customer_meta_index_retention: string
	customer_meta_wazuh_registration_port: string
	customer_meta_wazuh_log_ingestion_port: string
	customer_meta_wazuh_auth_password: string
	customer_meta_iris_customer_id: number
	customer_meta_office365_organization_id: string
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

export interface CustomerProvision {
	customer_name: string
	customer_code: string
	customer_index_name: string
	customer_grafana_org_name: string
	hot_data_retention: number
	index_replicas: number
	/** default this to 1 */
	index_shards: number
	/** default to Wazuh */
	customer_subscription: string[] // ??
	dashboards_to_include: {
		dashboards: string[]
		/** default to 0 */
		organizationId: number
		/** default to 0 */
		folderId: number
		/** default to "uid-to-be-replaced" */
		datasourceUid: string
	}
	wazuh_auth_password: string
	wazuh_registration_port: string
	wazuh_logs_port: string
	wazuh_api_port: string
	wazuh_cluster_name: string
	wazuh_cluster_key: string
	wazuh_master_ip: string
	grafana_url: string
	provision_wazuh_worker: boolean
	provision_ha_proxy: boolean
	dfir_iris_username: string
}

export interface CustomerDecommissionedData {
	agents_deleted: string[]
	groups_deleted: string[]
	stream_deleted: string
	index_deleted: string
}

export interface CustomerProvisioningDefaultSettings {
	id: number
	cluster_name: string
	cluster_key: string
	master_ip: string
	grafana_url: string
	wazuh_worker_hostname: string
}

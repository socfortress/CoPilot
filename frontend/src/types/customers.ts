// required on create/update: customer_code, customer_name, contact_last_name, contact_first_name.
// A stored row may still lack the contact names (the columns are nullable), and the API returns it as is.
export interface Customer {
	customer_code: string
	customer_name: string
	contact_last_name: string | null
	contact_first_name: string | null
	parent_customer_code: string | null
	phone: string
	address_line1: string
	address_line2: string
	city: string
	state: string
	postal_code: string
	country: string
	customer_type: string
	// TODO-FE: consider removing it (logo_file)
	logo_file: string
	is_provisioned?: boolean
}

export interface CustomerMeta {
	id: number
	customer_code: string
	customer_name: string
	customer_meta_graylog_index: string
	customer_meta_graylog_stream: string
	customer_meta_grafana_org_id: string
	customer_meta_wazuh_group: string
	customer_meta_index_retention: string | null
	customer_meta_wazuh_registration_port: string | null
	customer_meta_wazuh_log_ingestion_port: string | null
	customer_meta_wazuh_auth_password: string | null
	customer_meta_iris_customer_id: number
	customer_meta_office365_organization_id: string
	customer_meta_wazuh_api_port: string | null
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

/** How long an agent must have gone unseen to be deleted (#1291): at least 24 hours. */
export interface UnhealthyDeleteThreshold {
	value: number
	unit: "hours" | "days"
}

/** What deleting a requested agent would do, judged by the backend at the time of the request. */
export type UnhealthyAgentVerdict = "deletable" | "active_elsewhere" | "seen_recently" | "wazuh_manager" | "not_found"

export interface UnhealthyAgentPreview {
	agent_id: string
	verdict: UnhealthyAgentVerdict
	hostname: string | null
	label: string | null
	os: string | null
	/** When the list's tool last saw it (naive UTC). */
	last_seen: string | null
	/** When the other tool last saw it (naive UTC). */
	other_last_seen: string | null
}

export type UnhealthyVerdictCounts = Record<UnhealthyAgentVerdict, number>

export interface UnhealthyAgentsPreview {
	source: CustomerHealthcheckSource
	not_seen_for: UnhealthyDeleteThreshold
	/** Agents last seen before this moment (naive UTC) are stale. */
	cutoff: string
	counts: UnhealthyVerdictCounts
	agents: UnhealthyAgentPreview[]
}

export interface UnhealthyAgentDeleteResult {
	agent_id: string
	hostname: string | null
	outcome: "deleted" | "skipped" | "failed"
	/** Why a skipped agent was skipped. */
	reason: UnhealthyAgentVerdict | null
	/** Upstreams that did not confirm: the agent left CoPilot but may still be enrolled there. */
	unconfirmed: CustomerHealthcheckSource[]
}

export interface UnhealthyAgentsDeletion {
	source: CustomerHealthcheckSource
	not_seen_for: UnhealthyDeleteThreshold
	requested: number
	deleted: number
	skipped: number
	failed: number
	unconfirmed: number
	results: UnhealthyAgentDeleteResult[]
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
	wazuh_worker_hostname: string
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
	repo_url?: string | null
	repo_username?: string | null
	repo_password?: string | null
	windows_edr_installer?: string | null
	wazuh_domain?: string | null
}

export interface EDRInstallCommands {
	windows: string
	linux: string
	macos: string
}

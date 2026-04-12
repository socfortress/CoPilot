export interface Agent {
	id: number
	agent_id: string
	ip_address: string
	os: string
	hostname: string
	label: string
	critical_asset: boolean
	wazuh_last_seen: string
	velociraptor_id: string | null
	velociraptor_last_seen: string | null
	wazuh_agent_version: string
	wazuh_agent_status: string
	velociraptor_agent_version: string | null
	customer_code: string
	quarantined: boolean
	velociraptor_org: string | null
}

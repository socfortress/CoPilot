export interface NetworkConnector {
	id: number
	network_connector_name: string
	description: string
	network_connector_details: string
	network_connector_keys: NetworkConnectorKey[]
}

export interface NetworkConnectorKey {
	auth_key_name: string
}

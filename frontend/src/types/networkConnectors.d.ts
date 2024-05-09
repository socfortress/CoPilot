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

export interface CustomerNetworkConnector {
	customer_code: string
	id: number
	deployed: boolean
	customer_name: string
	network_connector_service_id: number
	network_connector_service_name: string
	network_connectors_subscriptions: NetworkConnectorsSubscription[]
}

export interface NetworkConnectorsSubscription {
	id: number
	customer_id: number
	network_connectors_service_id: number
	network_connectors_service: NetworkConnectorsService
	network_connectors_keys: NetworkConnectorsKey[]
}

export interface NetworkConnectorsKey {
	id: number
	auth_key_name: string
	auth_value: string
	subscription_id: number
}

export interface NetworkConnectorsService {
	auth_type: string
	service_name: string
	id: number
}

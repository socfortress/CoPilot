export interface AvailableIntegration {
	id: number
	integration_name: string
	description: string
	integration_details: string
	auth_keys: IntegrationAuthKey[]
}

export interface IntegrationAuthKey {
	auth_key_name: string
}

export interface CustomerIntegration {
	customer_code: string
	id: number
	deployed: boolean
	customer_name: string
	integration_service_id: number
	integration_service_name: string
	integration_subscriptions: IntegrationSubscription[]
}

export interface IntegrationSubscription {
	id: number
	customer_id: number
	integration_service_id: number
	integration_service: IntegrationService
	integration_auth_keys: IntegrationAuthKeyFull[]
}

export interface IntegrationAuthKeyFull {
	id: number
	auth_key_name: string
	auth_value: string
	subscription_id: number
}

export interface IntegrationService {
	auth_type: string
	service_name: string
	id: number
}

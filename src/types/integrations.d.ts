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

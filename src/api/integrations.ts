import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { AvailableIntegration, CustomerIntegration } from "@/types/integrations"

export interface NewIntegration {
	customer_code: string
	customer_name: string
	integration_name: string
	integration_config: {
		auth_type: string
		config_key: string
		config_value: string
	}
	integration_auth_keys: {
		auth_key_name: string
		auth_value: string
	}[]
}

export default {
	getAvailableIntegrations() {
		return HttpClient.get<FlaskBaseResponse & { available_integrations: AvailableIntegration[] }>(
			`/integrations/available_integrations`
		)
	},
	getCustomerIntegrations(customerCode: string) {
		return HttpClient.get<FlaskBaseResponse & { available_integrations: CustomerIntegration[] }>(
			`/integrations/customer_integrations/${customerCode}`
		)
	},
	createIntegrations(payload: NewIntegration) {
		return HttpClient.post<FlaskBaseResponse & { available_integrations: CustomerIntegration[] }>(
			`/integrations/create_integration`,
			payload
		)
	}
}

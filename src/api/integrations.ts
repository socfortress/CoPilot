import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { AvailableIntegration, CustomerIntegration } from "@/types/integrations"

export interface NewIntegration {
	customer_code: string
	customer_name: string
	integration_name: string
	integration_auth_keys: {
		auth_key_name: string
		auth_value: string
	}[]
}

export interface NewIntegrationPayload {
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
	createIntegration(props: NewIntegration) {
		const payload: NewIntegrationPayload = {
			...props,
			integration_config: {
				auth_type: "Wazuh",
				config_key: "endpoint",
				config_value: "not applicable"
			}
		}
		return HttpClient.post<FlaskBaseResponse>(`/integrations/create_integration`, payload)
	},

	office365Provision(customerCode: string, integrationName: string) {
		return HttpClient.post<FlaskBaseResponse>(`/office365/provision`, {
			customer_code: customerCode,
			integration_name: integrationName
		})
	}
}

import type { FlaskBaseResponse } from "@/types/flask.d"
import type { AvailableIntegration, CustomerIntegration } from "@/types/integrations.d"
import { HttpClient } from "../httpClient"

export interface NewIntegration {
	customer_code: string
	customer_name: string
	integration_name: string
	integration_auth_keys: {
		auth_key_name: string
		auth_value: string
	}[]
}

export interface NewIntegrationPayload extends NewIntegration {
	integration_config: {
		auth_type: string
		config_key: string
		config_value: string
	}
}

export default {
	// #region Integrations
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
	deleteIntegration(customerCode: string, integrationName: string) {
		return HttpClient.delete<FlaskBaseResponse>(`/integrations/delete_integration`, {
			data: { customer_code: customerCode, integration_name: integrationName }
		})
	},
	// #endregion

	// #region Provision
	office365Provision(customerCode: string, integrationName: string) {
		return HttpClient.post<FlaskBaseResponse>(`/office365/provision`, {
			customer_code: customerCode,
			integration_name: integrationName || "Office365"
		})
	},
	mimecastProvision(customerCode: string, integrationName: string) {
		return HttpClient.post<FlaskBaseResponse>(`/mimecast/provision`, {
			customer_code: customerCode,
			integration_name: integrationName || "Mimecast"
		})
	},
	crowdstrikeProvision(customerCode: string, integrationName: string) {
		return HttpClient.post<FlaskBaseResponse>(`/crowdstrike/provision`, {
			customer_code: customerCode,
			integration_name: integrationName || "Crowdstrike",
			hot_data_retention: 30,
			index_replicas: 0
		})
	},
	duoProvision(customerCode: string, integrationName: string) {
		return HttpClient.post<FlaskBaseResponse>(`/duo/provision`, {
			customer_code: customerCode,
			integration_name: integrationName || "Duo",
			time_interval: 15
		})
	},
	darktraceProvision(customerCode: string, integrationName: string) {
		return HttpClient.post<FlaskBaseResponse>(`/darktrace/provision`, {
			customer_code: customerCode,
			integration_name: integrationName || "Darktrace",
			time_interval: 15
		})
	},
	bitdefenderProvision(customerCode: string, integrationName: string) {
		return HttpClient.post<FlaskBaseResponse>(`/bitdefender/provision`, {
			customer_code: customerCode,
			integration_name: integrationName || "BitDefender",
			hot_data_retention: 30,
			index_replicas: 0
		})
	}
	// #endregion
}

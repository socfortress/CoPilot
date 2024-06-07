import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type {
	Customer,
	CustomerAgentHealth,
	CustomerDecommissionedData,
	CustomerMeta,
	CustomerProvision,
	CustomerProvisioningDefaultSettings
} from "@/types/customers.d"
import type { Agent } from "@/types/agents.d"

export interface CustomerAgentsHealthcheckQuery {
	minutes?: number
	hours?: number
	days?: number
}

export interface ProvisioningDefaultSettingsPayload {
	id: number
	clusterName: string
	clusterKey: string
	masterIp: string
	grafanaUrl: string
	wazuhWorkerHostname: string
}

export default {
	getCustomers(code?: string) {
		return HttpClient.get<FlaskBaseResponse & { customers?: Customer[]; customer?: Customer }>(
			`/customers${code ? "/" + code : ""}`
		)
	},
	createCustomer(customer: Customer) {
		return HttpClient.post<FlaskBaseResponse & { customer: Customer }>(`/customers`, customer)
	},
	updateCustomer(customer: Customer, code?: string) {
		return HttpClient.put<FlaskBaseResponse & { customer: Customer }>(
			`/customers/${code || customer.customer_code}`,
			customer
		)
	},
	deleteCustomer(code: string) {
		return HttpClient.delete<FlaskBaseResponse & { customer: Customer }>(`/customers/${code}`)
	},
	/** @deprecated */
	getCustomerMeta(code: string) {
		return HttpClient.get<FlaskBaseResponse & { customer_meta: CustomerMeta }>(`/customers/${code}/meta`)
	},
	/** @deprecated */
	updateCustomerMeta(meta: CustomerMeta, code: string) {
		return HttpClient.put<FlaskBaseResponse & { customer_meta: CustomerMeta }>(`/customers/${code}/meta`, meta)
	},
	/** @deprecated */
	createCustomerMeta(meta: CustomerMeta, code: string) {
		return HttpClient.post<FlaskBaseResponse & { customer_meta: CustomerMeta }>(`/customers/${code}/meta`, meta)
	},
	/** @deprecated */
	deleteCustomerMeta(code: string) {
		return HttpClient.delete<FlaskBaseResponse & { customer_meta: CustomerMeta }>(`/customers/${code}/meta`)
	},
	getCustomerFull(code: string) {
		return HttpClient.get<FlaskBaseResponse & { customer: Customer; customer_meta?: CustomerMeta }>(
			`/customers/${code}/full`
		)
	},
	getCustomerAgents(code: string) {
		return HttpClient.get<FlaskBaseResponse & { agents: Agent[] }>(`/customers/${code}/agents`)
	},
	getCustomerAgentsHealthcheckWazuh(code: string, query?: CustomerAgentsHealthcheckQuery) {
		return HttpClient.get<
			FlaskBaseResponse & {
				healthy_wazuh_agents: CustomerAgentHealth[]
				unhealthy_wazuh_agents: CustomerAgentHealth[]
			}
		>(`/customers/${code}/agents/healthcheck/wazuh`, {
			params: {
				minutes: query?.minutes || 0,
				hours: query?.hours || 0,
				days: query?.days || 0
			}
		})
	},
	getCustomerAgentsHealthcheckVelociraptor(code: string, query?: CustomerAgentsHealthcheckQuery) {
		return HttpClient.get<
			FlaskBaseResponse & {
				healthy_velociraptor_agents: CustomerAgentHealth[]
				unhealthy_velociraptor_agents: CustomerAgentHealth[]
			}
		>(`/customers/${code}/agents/healthcheck/velociraptor`, {
			params: {
				minutes: query?.minutes || 0,
				hours: query?.hours || 0,
				days: query?.days || 0
			}
		})
	},
	newCustomerProvision(provision: CustomerProvision, code: string) {
		return HttpClient.post<FlaskBaseResponse & { customer_meta: CustomerMeta; wazuh_worker_provisioned: boolean }>(
			`/customer_provisioning/provision`,
			provision,
			{
				params: {
					customer_code: code
				}
			}
		)
	},
	getCustomerProvision(code: string) {
		return HttpClient.get<FlaskBaseResponse & { customer_meta: CustomerMeta }>(
			`/customer_provisioning/provision/${code}`
		)
	},
	decommissionCustomer(code: string) {
		return HttpClient.post<FlaskBaseResponse & { decomissioned_data: CustomerDecommissionedData }>(
			`/customer_provisioning/decommission`,
			{},
			{
				params: {
					customer_code: code
				}
			}
		)
	},
	getProvisioningDashboards() {
		return HttpClient.get<FlaskBaseResponse & { available_dashboards: string[] }>(
			`/customer_provisioning/provision/dashboards`
		)
	},
	getProvisioningSubscriptions() {
		return HttpClient.get<FlaskBaseResponse & { available_subscriptions: string[] }>(
			`/customer_provisioning/provision/subscriptions`
		)
	},
	getProvisioningDefaultSettings() {
		return HttpClient.get<
			FlaskBaseResponse & { customer_provisioning_default_settings: CustomerProvisioningDefaultSettings }
		>(`/customer_provisioning/default_settings`)
	},
	setProvisioningDefaultSettings(payload: ProvisioningDefaultSettingsPayload) {
		return HttpClient.post<
			FlaskBaseResponse & { customer_provisioning_default_settings: CustomerProvisioningDefaultSettings }
		>(`/customer_provisioning/default_settings`, {
			id: payload.id,
			cluster_name: payload.clusterName,
			cluster_key: payload.clusterKey,
			master_ip: payload.masterIp,
			grafana_url: payload.grafanaUrl,
			wazuh_worker_hostname: payload.wazuhWorkerHostname
		})
	},
	updateProvisioningDefaultSettings(payload: ProvisioningDefaultSettingsPayload) {
		return HttpClient.put<
			FlaskBaseResponse & { customer_provisioning_default_settings: CustomerProvisioningDefaultSettings }
		>(`/customer_provisioning/default_settings`, {
			id: payload.id,
			cluster_name: payload.clusterName,
			cluster_key: payload.clusterKey,
			master_ip: payload.masterIp,
			grafana_url: payload.grafanaUrl,
			wazuh_worker_hostname: payload.wazuhWorkerHostname
		})
	}
}

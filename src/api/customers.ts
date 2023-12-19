import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { Customer, CustomerAgentHealth, CustomerMeta } from "@/types/customers.d"
import type { Agent } from "@/types/agents.d"

export interface CustomerAgentsHealthcheckQuery {
	minutes?: number
	hours?: number
	days?: number
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
	getCustomerMeta(code: string) {
		return HttpClient.get<FlaskBaseResponse & { customer_meta: CustomerMeta }>(`/customers/${code}/meta`)
	},
	updateCustomerMeta(meta: CustomerMeta, code: string) {
		return HttpClient.put<FlaskBaseResponse & { customer_meta: CustomerMeta }>(`/customers/${code}/meta`, meta)
	},
	createCustomerMeta(meta: CustomerMeta, code: string) {
		return HttpClient.post<FlaskBaseResponse & { customer_meta: CustomerMeta }>(`/customers/${code}/meta`, meta)
	},
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
	}
}

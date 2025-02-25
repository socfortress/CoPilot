import type { FlaskBaseResponse } from "@/types/flask.d"
import type { PortainerStack } from "@/types/portainer.d"
import { HttpClient } from "../httpClient"

export default {
	getCustomerStackId(customerName: string) {
		return HttpClient.get<FlaskBaseResponse & { stack_id: number }>(`/portainer/get-customer-stack-id`, {
			params: { customer_name: customerName }
		})
	},
	getStackDetails(stackId: number) {
		return HttpClient.get<FlaskBaseResponse & { data: PortainerStack }>(`/portainer/stack-details`, {
			params: { stack_id: stackId }
		})
	},
	startWazuhCustomerStack(stackId: number) {
		return HttpClient.post<FlaskBaseResponse & { data: PortainerStack }>(
			`/portainer/start-wazuh-customer-stack`,
			undefined,
			{
				params: { stack_id: stackId }
			}
		)
	},
	stopWazuhCustomerStack(stackId: number) {
		return HttpClient.post<FlaskBaseResponse & { data: PortainerStack }>(
			`/portainer/stop-wazuh-customer-stack`,
			undefined,
			{
				params: { stack_id: stackId }
			}
		)
	}
}

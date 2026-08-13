import type { FlaskBaseResponse } from "@/types/flask"
import type { PortainerStack } from "@/types/portainer"
import { HttpClient } from "../http-client"

export default {
	getCustomerStackId(customerName: string, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { stack_id: number }>(`/portainer/get-customer-stack-id`, {
			params: { customer_name: customerName },
			signal
		})
	},
	getStackDetails(stackId: number, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { data: PortainerStack }>(`/portainer/stack-details`, {
			params: { stack_id: stackId },
			signal
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

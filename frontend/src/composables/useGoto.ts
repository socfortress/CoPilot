import { useRouter } from "vue-router"

export function useGoto() {
	const router = useRouter()

	function gotoCustomer(params?: { code?: string | number; action?: "add-customer" }) {
		if (params?.code) {
			router.push({ name: "Customers", query: { code: params.code.toString() } })
		} else if (params?.action) {
			router.push({ name: "Customers", query: { action: params.action.toString() } })
		} else {
			router.push({ name: "Customers" })
		}
	}

	function gotoAgent(agentId?: string | number) {
		if (agentId) {
			router.push({ name: "Agent", params: { id: agentId.toString() } })
		} else {
			router.push({ name: "Agents" })
		}
	}

	function gotoIndex(indexName?: string) {
		router.push({ name: "Indices", query: indexName ? { index_name: indexName } : {} })
	}

	function gotoLicense() {
		router.push({ name: "License" })
	}

	function gotoHealthcheck() {
		router.push({ name: "Healthcheck" })
	}

	function gotoGraylogMetrics() {
		router.push({ name: "Graylog-Metrics" })
	}

	function gotoGraylogManagement(tabName?: "messages" | "alerts" | "events" | "streams" | "provisioning" | "inputs") {
		router.push({ name: "Graylog-Management", hash: tabName ? `#${tabName}` : undefined })
	}

	function gotoSocAlerts() {
		router.push({ name: "Soc-Alerts" })
	}

	function gotoAlerts() {
		router.push({ name: "Alerts" })
	}

	function gotoConnectors() {
		router.push({ name: "Connectors" })
	}

	function gotoGraylogPipelines(rule?: string) {
		router.push({ name: "Graylog-Pipelines", query: rule ? { rule } : {} })
	}

	function gotoSocUsers(userId?: string | number) {
		router.push({ name: "Soc-Users", query: userId ? { user_id: userId } : {} })
	}

	return {
		gotoCustomer,
		gotoAgent,
		gotoIndex,
		gotoLicense,
		gotoHealthcheck,
		gotoGraylogMetrics,
		gotoGraylogManagement,
		gotoSocAlerts,
		gotoGraylogPipelines,
		gotoSocUsers,
		gotoAlerts,
		gotoConnectors
	}
}

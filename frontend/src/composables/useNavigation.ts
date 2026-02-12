import { useRouter } from "vue-router"

export function useNavigation() {
	const router = useRouter()

	function routeCustomer(params?: { code?: string | number; action?: "add-customer" }) {
		if (params?.code) {
			router.push({ name: "Customers", query: { code: params.code.toString() } })
		} else if (params?.action) {
			router.push({ name: "Customers", query: { action: params.action.toString() } })
		} else {
			router.push({ name: "Customers" })
		}
	}

	function routeAgent(agentId?: string | number) {
		if (agentId) {
			router.push({ name: "Agent", params: { id: agentId.toString() } })
		} else {
			router.push({ name: "Agents" })
		}
	}

	function routeIndex(indexName?: string) {
		router.push({ name: "Indices", query: indexName ? { index_name: indexName } : {} })
	}

	function routeLicense() {
		router.push({ name: "License" })
	}

	function routeHealthcheck() {
		router.push({ name: "Healthcheck" })
	}

	function routeGraylogMetrics() {
		router.push({ name: "Graylog-Metrics" })
	}

	function routeGraylogManagement(
		tabName?: "messages" | "alerts" | "events" | "streams" | "provisioning" | "inputs"
	) {
		router.push({ name: "Graylog-Management", hash: tabName ? `#${tabName}` : undefined })
	}

	function routeSocAlerts() {
		router.push({ name: "Soc-Alerts" })
	}

	function routeAlerts() {
		router.push({ name: "Alerts" })
	}

	function routeConnectors() {
		router.push({ name: "Connectors" })
	}

	function routeGraylogPipelines(rule?: string) {
		router.push({ name: "Graylog-Pipelines", query: rule ? { rule } : {} })
	}

	function routeSocUsers(userId?: string | number) {
		router.push({ name: "Soc-Users", query: userId ? { user_id: userId } : {} })
	}

	function routeIncidentManagementAlerts(alertId?: number) {
		router.push({ name: "IncidentManagement-Alerts", query: alertId ? { alert_id: alertId } : {} })
	}

	function routeIncidentManagementCases(caseId?: number) {
		router.push({ name: "IncidentManagement-Cases", query: caseId ? { case_id: caseId } : {} })
	}

	return {
		routeCustomer,
		routeAgent,
		routeIndex,
		routeLicense,
		routeHealthcheck,
		routeGraylogMetrics,
		routeGraylogManagement,
		routeSocAlerts,
		routeGraylogPipelines,
		routeSocUsers,
		routeAlerts,
		routeConnectors,
		routeIncidentManagementAlerts,
		routeIncidentManagementCases
	}
}

import type { RouteLocationRaw } from "vue-router"
import { useRouter } from "vue-router"

export function useNavigation() {
	const router = useRouter()

	function routerConstructor(route: RouteLocationRaw) {
		return {
			navigate: () => router.push(route),
			replace: () => router.replace(route),
			valueOf: () => router.resolve(route).href,
			toString: () => router.resolve(route).href,
			fullUrl: () => {
				const resolved = router.resolve(route)
				return `${window.location.protocol}//${window.location.host}${resolved.href}`
			}
		}
	}

	function routeCustomer(params?: { code?: string | number; action?: "add-customer" }) {
		if (params?.code) {
			return routerConstructor({ name: "Customers", query: { code: params.code.toString() } })
		} else if (params?.action) {
			return routerConstructor({ name: "Customers", query: { action: params.action.toString() } })
		} else {
			return routerConstructor({ name: "Customers" })
		}
	}

	function routeAgent(agentId?: string | number) {
		if (agentId) {
			return routerConstructor({ name: "Agent", params: { id: agentId.toString() } })
		} else {
			return routerConstructor({ name: "Agents" })
		}
	}

	function routeIndex(indexName?: string) {
		return routerConstructor({ name: "Indices", query: indexName ? { index_name: indexName } : {} })
	}

	function routeLicense() {
		return routerConstructor({ name: "License" })
	}

	function routeHealthcheck() {
		return routerConstructor({ name: "Healthcheck" })
	}

	function routeGraylogMetrics() {
		return routerConstructor({ name: "Graylog-Metrics" })
	}

	function routeGraylogManagement(
		tabName?: "messages" | "alerts" | "events" | "streams" | "provisioning" | "inputs"
	) {
		return routerConstructor({ name: "Graylog-Management", hash: tabName ? `#${tabName}` : undefined })
	}

	function routeSocAlerts() {
		return routerConstructor({ name: "Soc-Alerts" })
	}

	function routeAlerts() {
		return routerConstructor({ name: "Alerts" })
	}

	function routeConnectors() {
		return routerConstructor({ name: "Connectors" })
	}

	function routeGraylogPipelines(rule?: string) {
		return routerConstructor({ name: "Graylog-Pipelines", query: rule ? { rule } : {} })
	}

	function routeSocUsers(userId?: string | number) {
		return routerConstructor({ name: "Soc-Users", query: userId ? { user_id: userId } : {} })
	}

	function routeIncidentManagementAlerts(alertId?: number) {
		return routerConstructor({ name: "IncidentManagement-Alerts", query: alertId ? { alert_id: alertId } : {} })
	}

	function routeIncidentManagementCases(caseId?: number) {
		return routerConstructor({ name: "IncidentManagement-Cases", query: caseId ? { case_id: caseId } : {} })
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

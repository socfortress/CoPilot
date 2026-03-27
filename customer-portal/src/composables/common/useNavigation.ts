import type { RouteLocationRaw } from "vue-router"
import type { AlertsListFilters } from "@/composables/alerts/useAlertsList"
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

	function routeAgents(options?: { customerId?: number }) {
		let route

		if (options?.customerId) {
			route = {
				name: "AgentsList",
				query: {
					agents_filters: JSON.stringify({ customer_id: options.customerId }),
					agents_pagination: JSON.stringify({ page: 1 })
				}
			}
		} else {
			route = { name: "AgentsList" }
		}

		return routerConstructor(route)
	}

	function routeAgent(agentId: string | number) {
		const route = { name: "AgentOverview", params: { id: agentId.toString() } }

		return routerConstructor(route)
	}

	function routeCustomers(options?: { name?: string }) {
		let route

		if (options?.name) {
			route = {
				name: "CustomersList",
				query: {
					customers_filters: JSON.stringify({ name: options.name }),
					customers_pagination: JSON.stringify({ page: 1 })
				}
			}
		} else {
			route = { name: "CustomersList" }
		}

		return routerConstructor(route)
	}

	function routeCustomer(customerId: string | number) {
		const route = { name: "CustomerOverview", params: { id: customerId.toString() } }

		return routerConstructor(route)
	}

	function routePackage(packageId: string | number) {
		const route = { name: "PackageOverview", params: { id: packageId.toString() } }

		return routerConstructor(route)
	}

	function routePackages(options?: { agentId?: number; hours_back?: number }) {
		let route

		if (options?.agentId) {
			route = {
				name: "PackagesList",
				query: {
					packages_pagination: JSON.stringify({ page: 1, page_size: 50 }),
					packages_filters: JSON.stringify({
						filters: { agent_id: options.agentId, hours_back: options.hours_back || 24 },
						mode: "results"
					})
				}
			}
		} else {
			route = { name: "PackagesList" }
		}

		return routerConstructor(route)
	}

	function routePort(portId: string | number) {
		const route = { name: "PortOverview", params: { id: portId.toString() } }

		return routerConstructor(route)
	}

	function routePorts(options?: { agentId?: number; hours_back?: number }) {
		let route

		if (options?.agentId) {
			route = {
				name: "PortsList",
				query: {
					ports_pagination: JSON.stringify({ page: 1, page_size: 50 }),
					ports_filters: JSON.stringify({
						filters: { agent_id: options.agentId, hours_back: options.hours_back || 24 },
						mode: "results"
					})
				}
			}
		} else {
			route = { name: "PortsList" }
		}

		return routerConstructor(route)
	}

	function routeProcess(processId: string | number) {
		const route = { name: "ProcessOverview", params: { id: processId.toString() } }

		return routerConstructor(route)
	}

	function routeProcesses(options?: { agentId?: number; hours_back?: number }) {
		let route

		if (options?.agentId) {
			route = {
				name: "ProcessesList",
				query: {
					processes_pagination: JSON.stringify({ page: 1, page_size: 50 }),
					processes_filters: JSON.stringify({
						filters: { agent_id: options.agentId, hours_back: options.hours_back || 24 },
						mode: "results"
					})
				}
			}
		} else {
			route = { name: "ProcessesList" }
		}

		return routerConstructor(route)
	}

	function routeVulnerability(vulnerabilityId: string | number) {
		const route = { name: "VulnerabilityOverview", params: { id: vulnerabilityId.toString() } }

		return routerConstructor(route)
	}

	function routeVulnerabilities(options?: { agentId?: number; days_back?: number }) {
		let route

		if (options?.agentId) {
			route = {
				name: "VulnerabilitiesList",
				query: {
					vulnerabilities_pagination: JSON.stringify({ page: 1, page_size: 50 }),
					vulnerabilities_filters: JSON.stringify({
						filters: { agent_id: options.agentId, days_back: options.days_back || 7 },
						mode: "results"
					})
				}
			}
		} else {
			route = { name: "VulnerabilitiesList" }
		}

		return routerConstructor(route)
	}

	function routeAlert(alertId: string | number) {
		const route = { name: "AlertOverview", params: { id: alertId.toString() } }

		return routerConstructor(route)
	}

	function routeAlerts(options?: Partial<AlertsListFilters>) {
		let route

		const listFilters: AlertsListFilters = {
			agent_id: options?.agent_id,
			hours_back: options?.hours_back || 24,
			...options
		}

		// Build query if we have any filters
		const hasFilters = Object.values(listFilters).some(v => v !== undefined && v !== null && v !== "")
		if (hasFilters) {
			route = {
				name: "AlertsList",
				query: {
					alerts_pagination: JSON.stringify({ page: 1, page_size: 50 }),
					alerts_filters: JSON.stringify({ listFilters, mode: "list" })
				}
			}
		} else {
			route = { name: "AlertsList" }
		}

		return routerConstructor(route)
	}

	function routeCollectors(options?: { active?: boolean }) {
		let route

		if (options?.active != null) {
			route = {
				name: "SystemCollectorsList",
				query: {
					collectors_filters: JSON.stringify({ active: options.active }),
					collectors_pagination: JSON.stringify({ page: 1 })
				}
			}
		} else {
			route = { name: "SystemCollectorsList" }
		}

		return routerConstructor(route)
	}

	function routeCollector(collectorId: string | number) {
		const route = { name: "SystemCollectorOverview", params: { id: collectorId.toString() } }

		return routerConstructor(route)
	}

	function routeTasks(options?: { name?: string; scheduled?: boolean }) {
		let route

		if (options?.name || options?.scheduled != null) {
			route = {
				name: "SystemTasksList",
				query: {
					tasks_filters: JSON.stringify({ name: options.name, scheduled: options.scheduled }),
					tasks_pagination: JSON.stringify({ page: 1 })
				}
			}
		} else {
			route = { name: "SystemTasksList" }
		}

		return routerConstructor(route)
	}

	function routeTask(taskId: string | number) {
		const route = { name: "SystemTaskOverview", params: { id: taskId.toString() } }

		return routerConstructor(route)
	}

	function routeMonitoring() {
		const route = { name: "SystemMonitoring" }

		return routerConstructor(route)
	}

	function routeCelery() {
		const route = { name: "SystemCelery" }

		return routerConstructor(route)
	}

	return {
		routeAgents,
		routeAgent,
		routeCustomers,
		routeCustomer,
		routePackage,
		routePackages,
		routePort,
		routePorts,
		routeProcess,
		routeProcesses,
		routeVulnerability,
		routeVulnerabilities,
		routeAlert,
		routeAlerts,
		routeCollectors,
		routeCollector,
		routeTasks,
		routeTask,
		routeCelery,
		routeMonitoring
	}
}

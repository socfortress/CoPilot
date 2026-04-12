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

	function routeEventSearch(params?: { customer_code?: string; source_name?: string; query?: string }) {
		const routeQuery: Record<string, string> = {}
		if (params?.customer_code) routeQuery.customer_code = params.customer_code
		if (params?.source_name) routeQuery.source_name = params.source_name
		if (params?.query) routeQuery.query = params.query
		return routerConstructor({ name: "EventSearch", query: routeQuery })
	}

	function routeAlertsList() {
		return routerConstructor({ name: "AlertsList" })
	}

	function routeCasesList() {
		return routerConstructor({ name: "CasesList" })
	}

	function routeDashboardsList() {
		return routerConstructor({ name: "DashboardsList" })
	}

	function routeDashboardViewer(dashboardId: number) {
		return routerConstructor({ name: "DashboardViewer", params: { id: dashboardId.toString() } })
	}

	return {
		routeEventSearch,
		routeAlertsList,
		routeCasesList,
		routeDashboardsList,
		routeDashboardViewer
	}
}

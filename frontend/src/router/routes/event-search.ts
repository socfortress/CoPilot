import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

/** vue-router already decodes path params — this only flattens the repeated-param shape. */
function routeParam(raw: string | string[] | undefined): string {
	if (!raw) return ""
	return Array.isArray(raw) ? raw[0] : raw
}

export const eventSearchRoutes: RouteRecordRaw[] = [
	{
		path: "/event-search/:customerCode/:sourceName/:indexName/:eventId",
		name: "EventSearch-Event",
		component: () => import("@/views/events/Event.vue"),
		meta: { title: "Event", auth: true, roles: RouteRole.All }
	},
	{
		path: "/event-search/:customerCode/:sourceName/:indexName",
		redirect: to => ({
			name: "EventSearch",
			query: {
				customer_code: routeParam(to.params.customerCode),
				source_name: routeParam(to.params.sourceName)
			}
		})
	},
	{
		path: "/event-search/:customerCode/:sourceName",
		redirect: to => ({
			name: "EventSearch",
			query: {
				customer_code: routeParam(to.params.customerCode),
				source_name: routeParam(to.params.sourceName)
			}
		})
	},
	{
		path: "/event-search/:customerCode",
		redirect: to => ({
			name: "EventSearch",
			query: {
				customer_code: routeParam(to.params.customerCode)
			}
		})
	},
	{
		path: "/event-search",
		name: "EventSearch",
		component: () => import("@/views/events/EventSearch.vue"),
		meta: { title: "Event Search", auth: true, roles: RouteRole.All }
	}
]

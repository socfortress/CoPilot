import type { RouteRecordRaw } from "vue-router"
import { AuthUserRole } from "@/types/auth"

// SOCFortress UBA (user behavior analytics): entities ranked by risk, UBA alerts, suppressions.
// The connector (URL + API key) is configured under Connectors; this page is for using it.
// One UBA alert and one entity also have a page of their own (the same view as the page's drawers),
// so a CoPilot incident alert raised by UBA can link straight to them. Both are scoped by customer:
// every UBA call is. An entity key carries `\`, `:` and `@`; the router encodes it in the path.
// The path's prefixes redirect to the matching view of the page, so every breadcrumb leads somewhere.
export const ubaRoutes: RouteRecordRaw[] = [
	{
		path: "/uba",
		name: "Uba",
		component: () => import("@/views/Uba.vue"),
		meta: { title: "User Behavior Analytics", auth: true, roles: [AuthUserRole.Admin, AuthUserRole.Analyst] }
	},
	{
		path: "/uba/:customerCode",
		redirect: to => ({ name: "Uba", query: { customer: to.params.customerCode } })
	},
	{
		path: "/uba/:customerCode/:tab(alerts|entities)",
		redirect: to => ({ name: "Uba", query: { customer: to.params.customerCode, tab: to.params.tab } })
	},
	{
		path: "/uba/:customerCode/alerts/:alertId",
		name: "UbaAlert",
		component: () => import("@/views/UbaAlert.vue"),
		meta: { title: "UBA Alert", auth: true, roles: [AuthUserRole.Admin, AuthUserRole.Analyst], skipPin: true }
	},
	{
		path: "/uba/:customerCode/entities/:entityKey",
		name: "UbaEntity",
		component: () => import("@/views/UbaEntity.vue"),
		meta: { title: "UBA Entity", auth: true, roles: [AuthUserRole.Admin, AuthUserRole.Analyst], skipPin: true }
	}
]

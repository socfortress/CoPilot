import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const customersRoutes: RouteRecordRaw[] = [
	{
		path: "/customers",
		name: "Customers",
		component: () => import("@/views/customers/Customers.vue"),
		meta: { title: "Customers", auth: true, roles: RouteRole.All }
	},
	{
		path: "/customers/new",
		name: "CustomerNew",
		component: () => import("@/views/customers/CustomerNew.vue"),
		meta: { title: "Add Customer", auth: true, roles: RouteRole.All }
	},
	{
		path: "/customers/:code/healthcheck/:source/:agentId",
		name: "CustomerHealthcheckAgent",
		component: () => import("@/views/customers/CustomerHealthcheckAgent.vue"),
		meta: { title: "Agent Healthcheck", auth: true, roles: RouteRole.All }
	},
	{
		path: "/customers/:code/healthcheck/:source",
		redirect: to => `/customers/${to.params.code}`
	},
	{
		path: "/customers/:code/healthcheck",
		redirect: to => `/customers/${to.params.code}`
	},
	{
		path: "/customers/:code",
		name: "Customer",
		component: () => import("@/views/customers/Customer.vue"),
		meta: { title: "Customer", auth: true, roles: RouteRole.All }
	},
	{
		path: "/customer-portal",
		name: "CustomerPortal",
		component: () => import("@/views/customers/CustomerPortal.vue"),
		meta: { title: "Customer Portal", auth: true, roles: RouteRole.All }
	}
]

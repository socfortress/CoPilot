import type { RouteRecordRaw } from "vue-router"
import { AuthUserRole } from "@/types/auth"

// Customers' SOCFortress WAFs (#1168): pick a customer and WAF, then the live views.
// Configuring a WAF stays on the customer (Customers → WAF); this page is for using it.
export const wafRoutes: RouteRecordRaw[] = [
	{
		path: "/waf",
		name: "Waf",
		component: () => import("@/views/Waf.vue"),
		meta: { title: "WAF", auth: true, roles: [AuthUserRole.Admin, AuthUserRole.Analyst] }
	}
]

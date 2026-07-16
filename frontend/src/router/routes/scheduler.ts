import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const schedulerRoutes: RouteRecordRaw[] = [
	{
		path: "/scheduler",
		name: "Scheduler",
		component: () => import("@/views/scheduler/Scheduler.vue"),
		meta: { title: "Scheduler", auth: true, roles: RouteRole.All }
	},
	{
		path: "/scheduler/:id",
		name: "SchedulerJob",
		component: () => import("@/views/scheduler/SchedulerJob.vue"),
		meta: { title: "Scheduler Job", auth: true, roles: RouteRole.All }
	}
]

import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const agentsRoutes: RouteRecordRaw[] = [
	{
		path: "/agents",
		meta: {
			auth: true,
			roles: RouteRole.All
		},
		children: [
			{
				path: "",
				name: "Agents",
				component: () => import("@/views/agents/Agents.vue"),
				meta: { title: "Agents" }
			},
			{
				path: ":id",
				name: "Agent",
				component: () => import("@/views/agents/Overview.vue"),
				meta: { title: "Agent", skipPin: true }
			},
			{
				path: "sysmon-config",
				name: "SysmonConfig",
				component: () => import("@/views/agents/SysmonConfig.vue"),
				meta: { title: "Sysmon Config" }
			},
			{
				path: "detection-rules",
				name: "DetectionRules",
				component: () => import("@/views/agents/DetectionRules.vue"),
				meta: { title: "Detection Rules" }
			},
			{
				path: "groups",
				name: "Groups",
				component: () => import("@/views/agents/Groups.vue"),
				meta: { title: "Groups" }
			},
			{
				path: "copilot-actions",
				name: "CopilotActions",
				component: () => import("@/views/agents/CopilotActions.vue"),
				meta: { title: "CoPilot Actions" }
			},
			{
				path: "/copilot-searches",
				name: "CopilotSearches",
				component: () => import("@/views/agents/CopilotSearches.vue"),
				meta: {
					title: "CoPilot Searches"
				}
			},
			{
				path: "vulnerability-overview",
				name: "VulnerabilityOverview",
				component: () => import("@/views/agents/VulnerabilityOverview.vue"),
				meta: { title: "Vulnerability Overview" }
			},
			{
				path: "sca-overview",
				name: "ScaOverview",
				component: () => import("@/views/agents/ScaOverview.vue"),
				meta: { title: "SCA Overview" }
			},
			{
				path: "sca-policies",
				name: "ScaPolicies",
				component: () => import("@/views/agents/ScaPolicies.vue"),
				meta: { title: "SCA Policies" }
			},
			{
				path: "/patch-tuesday",
				name: "PatchTuesday",
				component: () => import("@/views/agents/PatchTuesdayOverview.vue"),
				meta: { title: "Patch Tuesday" }
			}
		]
	}
]

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
				path: ":id/sca",
				redirect: to => ({
					name: "Agent",
					params: { id: to.params.id }
				})
			},
			{
				path: ":id/data-store",
				redirect: to => ({
					name: "Agent",
					params: { id: to.params.id }
				})
			},
			{
				path: ":id/data-store/:artifactId",
				name: "AgentArtifact",
				component: () => import("@/views/agents/AgentArtifact.vue"),
				meta: { title: "Agent Artifact", skipPin: true }
			},
			{
				path: ":id/sca/:policyId/checks",
				redirect: to => ({
					name: "AgentSca",
					params: { id: to.params.id, policyId: to.params.policyId }
				})
			},
			{
				path: ":id/sca/:policyId/checks/:checkId",
				name: "AgentScaCheck",
				component: () => import("@/views/agents/AgentScaCheck.vue"),
				meta: { title: "Agent SCA Check", skipPin: true }
			},
			{
				path: ":id/sca/:policyId",
				name: "AgentSca",
				component: () => import("@/views/agents/AgentSca.vue"),
				meta: { title: "Agent SCA Policy", skipPin: true }
			},
			{
				path: ":id/vulnerabilities",
				redirect: to => ({
					name: "Agent",
					params: { id: to.params.id }
				})
			},
			{
				path: ":id/vulnerabilities/:cve",
				name: "AgentVulnerability",
				component: () => import("@/views/agents/AgentVulnerability.vue"),
				meta: { title: "Agent Vulnerability", skipPin: true }
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
				// action names contain dots/spaces — :path converter keeps them intact
				path: "copilot-actions/:name(.*)",
				name: "CopilotAction",
				component: () => import("@/views/agents/CopilotAction.vue"),
				meta: { title: "CoPilot Action", skipPin: true }
			},
			{
				path: "/copilot-searches/:ruleId",
				name: "CopilotSearchRule",
				component: () => import("@/views/agents/CopilotSearchRule.vue"),
				meta: { title: "CoPilot Search Rule", skipPin: true }
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
				path: "vulnerability-overview/:agentName",
				redirect: { name: "VulnerabilityOverview" }
			},
			{
				path: "vulnerability-overview/:agentName/:cve",
				name: "VulnerabilityOverviewItem",
				component: () => import("@/views/agents/VulnerabilityOverviewItem.vue"),
				meta: { title: "Vulnerability", skipPin: true }
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
				path: "/patch-tuesday/:cycle",
				redirect: { name: "PatchTuesday" }
			},
			{
				path: "/patch-tuesday/:cycle/:cve",
				name: "PatchTuesdayItem",
				component: () => import("@/views/agents/PatchTuesdayItem.vue"),
				meta: { title: "Patch Tuesday CVE", skipPin: true }
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

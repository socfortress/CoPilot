import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const assessmentsRoutes: RouteRecordRaw[] = [
	{
		path: "/cloud-security-assessment",
		name: "CloudSecurityAssessment",
		component: () => import("@/views/CloudSecurityAssessment.vue"),
		meta: { title: "Cloud Sec. Assess.", auth: true, roles: RouteRole.All }
	},
	{
		path: "/web-vulnerability-assessment",
		name: "WebVulnerabilityAssessment",
		component: () => import("@/views/WebVulnerabilityAssessment.vue"),
		meta: { title: "Web Vuln. Assess.", auth: true, roles: RouteRole.All }
	},
	{
		path: "/github-audit",
		name: "GitHubAudit",
		component: () => import("@/views/GitHubAuditOverview.vue"),
		meta: {
			title: "GitHub Audit",
			auth: true,
			roles: RouteRole.All
		}
	}
]

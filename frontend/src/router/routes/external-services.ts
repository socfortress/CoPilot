import type { RouteRecordRaw } from "vue-router"
import { RouteRole } from "@/types/auth"

export const externalServicesRoutes: RouteRecordRaw[] = [
	{
		path: "/external-services",
		redirect: "/external-services/third-party-integrations",
		meta: {
			auth: true,
			roles: RouteRole.All
		},
		children: [
			{
				path: "third-party-integrations",
				name: "ExternalServices-ThirdPartyIntegrations",
				component: () => import("@/views/externalServices/ThirdPartyIntegrations.vue"),
				meta: { title: "Third Party Integrations" }
			},
			{
				path: "third-party-integrations/:id",
				name: "ExternalServices-ThirdPartyIntegration",
				component: () => import("@/views/externalServices/ThirdPartyIntegration.vue"),
				meta: { title: "Third Party Integration" }
			},
			{
				path: "network-connectors",
				name: "ExternalServices-NetworkConnectors",
				component: () => import("@/views/externalServices/NetworkConnectors.vue"),
				meta: { title: "Network Connectors" }
			},
			{
				path: "shuffle-app-auth",
				name: "ExternalServices-ShuffleAppAuth",
				component: () => import("@/views/externalServices/ShuffleAppAuth.vue"),
				meta: { title: "Shuffle App Auth" }
			}
		]
	}
]

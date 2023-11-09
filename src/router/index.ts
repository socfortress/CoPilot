import { createRouter, createWebHistory } from "vue-router"
import Analytics from "@/views/Dashboard/Analytics.vue"
import { UserRole } from "@/types/auth.d"
import components from "./components"
import { Layout } from "@/types/theme.d"
import { authCheck } from "@/utils/auth"

const router = createRouter({
	history: createWebHistory(import.meta.env.BASE_URL),
	routes: [
		{
			path: "/",
			redirect: "/indices"
		},
		{
			path: "/indices",
			name: "Indices",
			component: () => import("@/views/socfortress/Indices.vue"),
			meta: { title: "Indices", auth: true, roles: UserRole.All }
		},
		{
			path: "/connectors",
			name: "Connectors",
			component: () => import("@/views/socfortress/Connectors.vue"),
			meta: { title: "Connectors", auth: true, roles: UserRole.All }
		},
		{
			path: "/agents",
			name: "Agents",
			component: () => import("@/views/socfortress/Agents.vue"),
			meta: { title: "Agents", auth: true, roles: UserRole.All }
		},
		{
			path: "/agent/:id?",
			name: "Agent",
			component: () => import("@/views/socfortress/AgentOverview.vue"),
			meta: { title: "Agent", auth: true, roles: UserRole.All }
		},
		{
			path: "/graylog",
			redirect: "/graylog/management",
			meta: {
				auth: true,
				roles: UserRole.All
			},
			children: [
				{
					path: "management",
					name: "Graylog-Management",
					component: () => import("@/views/socfortress/graylog/Management.vue"),
					meta: { title: "Management" }
				},
				{
					path: "metrics",
					name: "Graylog-Metrics",
					component: () => import("@/views/socfortress/graylog/Metrics.vue"),
					meta: { title: "Metrics" }
				},
				{
					path: "pipelines",
					name: "Graylog-Pipelines",
					component: () => import("@/views/socfortress/graylog/Pipelines.vue"),
					meta: { title: "Pipelines" }
				}
			]
		},
		{
			path: "/alerts",
			name: "Alerts",
			component: () => import("@/views/socfortress/Alerts.vue"),
			meta: { title: "Alerts", auth: true, roles: UserRole.All }
		},

		// DEMO PAGES ==========================================================

		{
			path: "/dashboard",
			redirect: "/dashboard/analytics",
			meta: {
				auth: true,
				roles: UserRole.All
			},
			children: [
				{
					path: "analytics",
					name: "Dashboard-Analytics",
					component: Analytics,
					meta: { title: "Analytics" }
				},
				{
					path: "ecommerce",
					name: "Dashboard-eCommerce",
					component: () => import("@/views/Dashboard/eCommerce.vue"),
					meta: { title: "eCommerce" }
				}
			]
		},
		{
			path: "/calendar",
			name: "Apps-Calendars-FullCalendar",
			component: () => import("@/views/Apps/Calendars/FullCalendar.vue"),
			meta: { title: "Calendar", auth: true, roles: UserRole.All }
		},
		{
			path: "/email",
			name: "Apps-Mailbox",
			component: () => import("@/views/Apps/Mailbox.vue"),
			meta: { title: "Email", auth: true, roles: UserRole.All }
		},
		{
			path: "/chat",
			name: "Apps-Chat",
			component: () => import("@/views/Apps/Chat.vue"),
			meta: { title: "Chat", auth: true, roles: UserRole.All }
		},
		{
			path: "/kanban",
			name: "Apps-Kanban",
			component: () => import("@/views/Apps/Kanban.vue"),
			meta: { title: "Kanban", auth: true, roles: UserRole.All }
		},
		{
			path: "/notes",
			name: "Apps-Notes",
			component: () => import("@/views/Apps/Notes.vue"),
			meta: { title: "Notes", auth: true, roles: UserRole.All }
		},
		{
			path: "/typography",
			name: "Typography",
			component: () => import("@/views/Typography.vue"),
			meta: { title: "Typography", auth: true, roles: UserRole.All }
		},
		{
			path: "/cards",
			redirect: "/cards/basic",
			meta: {
				auth: true,
				roles: UserRole.All
			},
			children: [
				{
					path: "basic",
					name: "Cards-Basic",
					component: () => import("@/views/Cards/Basic.vue"),
					meta: { title: "Cards Basic" }
				},
				{
					path: "ecommerce",
					name: "Cards-Ecommerce",
					component: () => import("@/views/Cards/Ecommerce.vue"),
					meta: { title: "Cards Ecommerce" }
				},
				{
					path: "list",
					name: "Cards-List",
					component: () => import("@/views/Cards/List.vue"),
					meta: { title: "Cards List" }
				},
				{
					path: "extra",
					name: "Cards-Extra",
					component: () => import("@/views/Cards/Extra.vue"),
					meta: { title: "Cards Extra" }
				},
				{
					path: "combo",
					name: "Cards-Combo",
					component: () => import("@/views/Cards/Combo.vue"),
					meta: { title: "Cards Combo" }
				}
			]
		},
		components,
		{
			path: "/toolbox",
			redirect: "/toolbox/refresh-tool",
			meta: {
				auth: true,
				roles: UserRole.All
			},
			children: [
				{
					path: "refresh-tool",
					name: "Toolbox-RefreshTool",
					// route level code-splitting
					// this generates a separate chunk (About.[hash].js) for this route
					// which is lazy-loaded when the route is visited.
					component: () => import("@/views/Toolbox/RefreshTool.vue"),
					meta: { title: "Refresh Tool" }
				},
				{
					path: "tour",
					name: "Toolbox-Tour",
					component: () => import("@/views/Toolbox/Tour.vue"),
					meta: { title: "Tour" }
				}
			]
		},
		{
			path: "/layout",
			redirect: "/layout/left-sidebar",
			meta: {
				auth: true,
				roles: UserRole.All
			},
			children: [
				{
					path: "left-sidebar",
					name: "Layout-LeftSidebar",
					component: () => import("@/views/Layout/LeftSidebar.vue"),
					meta: { title: "Left Sidebar" }
				},
				{
					path: "right-sidebar",
					name: "Layout-RightSidebar",
					component: () => import("@/views/Layout/RightSidebar.vue"),
					meta: { title: "Right Sidebar" }
				},
				{
					path: "full-width",
					name: "Layout-FullWidth",
					component: () => import("@/views/Layout/FullWidth.vue"),
					meta: { title: "Full Width" }
				}
			]
		},
		{
			path: "/maps",
			redirect: "/maps/google-maps",
			meta: {
				auth: true,
				roles: UserRole.All
			},
			children: [
				{
					path: "google-maps",
					name: "Maps-GoogleMaps",
					component: () => import("@/views/Maps/GoogleMaps.vue"),
					meta: { title: "Google maps" }
				},
				{
					path: "maplibre",
					name: "Maps-MapLibre",
					component: () => import("@/views/Maps/MapLibre.vue"),
					meta: { title: "MapLibre" }
				},
				{
					path: "leaflet",
					name: "Maps-Leaflet",
					component: () => import("@/views/Maps/Leaflet.vue"),
					meta: { title: "Leaflet" }
				},
				{
					path: "vectormap",
					name: "Maps-VectorMap",
					component: () => import("@/views/Maps/VectorMap.vue"),
					meta: { title: "Vector Map" }
				}
			]
		},
		{
			path: "/editors",
			redirect: "/editors/quill",
			meta: {
				auth: true,
				roles: UserRole.All
			},
			children: [
				{
					path: "quill",
					name: "Editors-Quill",
					component: () => import("@/views/Editors/Quill.vue"),
					meta: { title: "Quill" }
				},
				{
					path: "tiptap",
					name: "Editors-Tiptap",
					component: () => import("@/views/Editors/Tiptap.vue"),
					meta: { title: "Tiptap" }
				},
				{
					path: "milkdown",
					name: "Editors-Milkdown",
					component: () => import("@/views/Editors/Milkdown.vue"),
					meta: { title: "Milkdown" }
				}
			]
		},
		{
			path: "/charts",
			redirect: "/charts/apexcharts",
			meta: {
				auth: true,
				roles: UserRole.All
			},
			children: [
				{
					path: "apexcharts",
					name: "Charts-ApexCharts",
					component: () => import("@/views/Charts/ApexCharts.vue"),
					meta: { title: "ApexCharts" }
				},
				{
					path: "chartjs",
					name: "Charts-ChartJS",
					component: () => import("@/views/Charts/ChartJS.vue"),
					meta: { title: "ChartJS" }
				}
			]
		},
		{
			path: "/multi-language",
			name: "MultiLanguage",
			component: () => import("@/views/MultiLanguage.vue"),
			meta: { title: "Multi Language", auth: true, roles: UserRole.All }
		},
		{
			path: "/icons",
			name: "Icons",
			component: () => import("@/views/Icons.vue"),
			meta: { title: "Icons", auth: true, roles: UserRole.All }
		},
		{
			path: "/tables",
			redirect: "/tables/base",
			meta: {
				auth: true,
				roles: UserRole.All
			},
			children: [
				{
					path: "base",
					name: "Tables-Base",
					component: () => import("@/views/Tables/Base.vue"),
					meta: { title: "Tables Base" }
				},
				{
					path: "data-table",
					name: "Tables-DataTable",
					component: () => import("@/views/Tables/DataTable.vue"),
					meta: { title: "Data Table" }
				}
			]
		},

		{
			path: "/profile",
			name: "Profile",
			component: () => import("@/views/Profile.vue"),
			meta: { title: "Profile", auth: true, roles: UserRole.All }
		},

		{
			path: "/login",
			name: "Login",
			component: () => import("@/views/Auth/Login.vue"),
			meta: { title: "Login", forceLayout: Layout.Blank, checkAuth: true }
		},
		{
			path: "/logout",
			name: "Logout",
			redirect: "/login"
		},
		{
			path: "/:pathMatch(.*)*",
			name: "NotFound",
			component: () => import("@/views/NotFound.vue"),
			meta: { forceLayout: Layout.Blank }
		}
	]
})

router.beforeEach(route => {
	return authCheck(route)
})

export default router

import { createRouter, createWebHistory } from "vue-router"
import Analytics from "@/views/Dashboard/Analytics.vue"
import components from "./components"
import { Layout } from "@/types/theme.d"

const router = createRouter({
	history: createWebHistory(import.meta.env.BASE_URL),
	routes: [
		{
			path: "/",
			redirect: "/dashboard/analytics"
		},
		{
			path: "/indices",
			name: "indices",
			component: () => import("@/views/socfortress/Indices.vue"),
			meta: { title: "Indices", auth: true, roles: "all" }
		},
		/*
		{
			path: "/inputs",
			name: "inputs",
			component: () => import("@/views/socfortress/Inputs.vue"),
			meta: {  title: "Inputs", auth: true, roles: "all" }
		},
		*/
		{
			path: "/connectors",
			name: "connectors",
			component: () => import("@/views/socfortress/Connectors.vue"),
			meta: { title: "Connectors", auth: true, roles: "all" }
		},
		{
			path: "/agents",
			name: "agents",
			component: () => import("@/views/socfortress/Agents.vue"),
			meta: { title: "Agents", auth: true, roles: "all" }
		},
		{
			path: "/agent/:id?",
			name: "agent",
			component: () => import("@/views/socfortress/AgentOverview.vue"),
			meta: { title: "Agent", auth: true, roles: "all" }
		},

		{
			path: "/dashboard",
			redirect: "/dashboard/analytics",
			meta: {
				auth: true,
				roles: "all"
			},
			children: [
				{
					path: "analytics",
					name: "analytics",
					component: Analytics,
					meta: { title: "Analytics" }
				},
				{
					path: "ecommerce",
					name: "ecommerce",
					component: () => import("@/views/Dashboard/eCommerce.vue"),
					meta: { title: "eCommerce" }
				}
			]
		},
		{
			path: "/calendar",
			name: "calendar",
			component: () => import("@/views/Apps/Calendars/FullCalendar.vue"),
			meta: { title: "Calendar", auth: true, roles: "all" }
		},
		/*
		{
			path: "/calendars",
			redirect: "/calendars/vue-cal",
			meta: {
				auth: true,
				roles: "all"
			},
			children: [
				{
					path: "vue-cal",
					name: "vue-cal",
					component: () => import("@/views/Apps/Calendars/VueCal.vue"),
					meta: {  title: "Vue Cal" }
				},
				{
					path: "full-calendar",
					name: "full-calendar",
					component: () => import("@/views/Apps/Calendars/FullCalendar.vue"),
					meta: {  title: "Full Calendar" }
				}
			]
		},
		*/
		{
			path: "/email",
			name: "email",
			component: () => import("@/views/Apps/Mailbox.vue"),
			meta: { title: "Email", auth: true, roles: "all" }
		},
		{
			path: "/chat",
			name: "chat",
			component: () => import("@/views/Apps/Chat.vue"),
			meta: { title: "Chat", auth: true, roles: "all" }
		},
		{
			path: "/kanban",
			name: "kanban",
			component: () => import("@/views/Apps/Kanban.vue"),
			meta: { title: "Kanban", auth: true, roles: "all" }
		},
		{
			path: "/notes",
			name: "notes",
			component: () => import("@/views/Apps/Notes.vue"),
			meta: { title: "Notes", auth: true, roles: "all" }
		},
		{
			path: "/typography",
			name: "typography",
			component: () => import("@/views/Typography.vue"),
			meta: { title: "Typography", auth: true, roles: "all" }
		},
		{
			path: "/cards",
			redirect: "/cards/basic",
			meta: {
				auth: true,
				roles: "all"
			},
			children: [
				{
					path: "basic",
					name: "cards-basic",
					component: () => import("@/views/Cards/Basic.vue"),
					meta: { title: "Cards Basic" }
				},
				{
					path: "ecommerce",
					name: "cards-ecommerce",
					component: () => import("@/views/Cards/Ecommerce.vue"),
					meta: { title: "Cards Ecommerce" }
				},
				{
					path: "list",
					name: "cards-list",
					component: () => import("@/views/Cards/List.vue"),
					meta: { title: "Cards List" }
				},
				{
					path: "extra",
					name: "cards-extra",
					component: () => import("@/views/Cards/Extra.vue"),
					meta: { title: "Cards Extra" }
				},
				{
					path: "combo",
					name: "cards-combo",
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
				roles: "all"
			},
			children: [
				{
					path: "refresh-tool",
					name: "toolbox-refresh-tool",
					// route level code-splitting
					// this generates a separate chunk (About.[hash].js) for this route
					// which is lazy-loaded when the route is visited.
					component: () => import("@/views/Toolbox/RefreshTool.vue"),
					meta: { title: "Refresh Tool" }
				},
				{
					path: "tour",
					name: "toolbox-tour",
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
				roles: "all"
			},
			children: [
				{
					path: "left-sidebar",
					name: "layout-left-sidebar",
					component: () => import("@/views/Layout/LeftSidebar.vue"),
					meta: { title: "Left Sidebar" }
				},
				{
					path: "right-sidebar",
					name: "layout-right-sidebar",
					component: () => import("@/views/Layout/RightSidebar.vue"),
					meta: { title: "Right Sidebar" }
				},
				{
					path: "full-width",
					name: "layout-full-width",
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
				roles: "all"
			},
			children: [
				{
					path: "google-maps",
					name: "maps-google-maps",
					component: () => import("@/views/Maps/GoogleMaps.vue"),
					meta: { title: "Google maps" }
				},
				{
					path: "maplibre",
					name: "maps-maplibre",
					component: () => import("@/views/Maps/MapLibre.vue"),
					meta: { title: "MapLibre" }
				},
				{
					path: "leaflet",
					name: "maps-leaflet",
					component: () => import("@/views/Maps/Leaflet.vue"),
					meta: { title: "Leaflet" }
				},
				{
					path: "vectormap",
					name: "maps-vectormap",
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
				roles: "all"
			},
			children: [
				{
					path: "quill",
					name: "editors-quill",
					component: () => import("@/views/Editors/Quill.vue"),
					meta: { title: "Quill" }
				},
				{
					path: "tiptap",
					name: "editors-tiptap",
					component: () => import("@/views/Editors/Tiptap.vue"),
					meta: { title: "Tiptap" }
				},
				{
					path: "milkdown",
					name: "editors-milkdown",
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
				roles: "all"
			},
			children: [
				{
					path: "apexcharts",
					name: "charts-apexcharts",
					component: () => import("@/views/Charts/ApexCharts.vue"),
					meta: { title: "ApexCharts" }
				},
				{
					path: "chartjs",
					name: "charts-chartjs",
					component: () => import("@/views/Charts/ChartJS.vue"),
					meta: { title: "ChartJS" }
				}
			]
		},
		{
			path: "/multi-language",
			name: "multi-language",
			component: () => import("@/views/MultiLanguage.vue"),
			meta: { title: "Multi Language", auth: true, roles: "all" }
		},
		{
			path: "/icons",
			redirect: "/icons/xicons",
			meta: {
				auth: true,
				roles: "all"
			},
			children: [
				{
					path: "xicons",
					name: "icons-xicons",
					component: () => import("@/views/Icons/Xicons.vue"),
					meta: { title: "xIcons" }
				},
				{
					path: "flag",
					name: "icons-flag",
					component: () => import("@/views/Icons/Flag.vue"),
					meta: { title: "Flag Icons" }
				}
			]
		},
		{
			path: "/tables",
			redirect: "/tables/base",
			meta: {
				auth: true,
				roles: "all"
			},
			children: [
				{
					path: "base",
					name: "tables-base",
					component: () => import("@/views/Tables/Base.vue"),
					meta: { title: "Tables Base" }
				},
				{
					path: "data-table",
					name: "tables-data-table",
					component: () => import("@/views/Tables/DataTable.vue"),
					meta: { title: "Data Table" }
				}
			]
		},

		{
			path: "/profile",
			name: "profile",
			component: () => import("@/views/Profile.vue"),
			meta: { title: "Profile", auth: true, roles: "all" }
		},

		{
			path: "/login",
			name: "login",
			component: () => import("@/views/Auth/Login.vue"),
			meta: { title: "Login", forceLayout: Layout.Blank, checkAuth: true }
		},
		{
			path: "/logout",
			name: "logout",
			redirect: "/login"
		},
		{
			path: "/:pathMatch(.*)*",
			name: "not-found",
			component: () => import("@/views/NotFound.vue"),
			meta: { forceLayout: Layout.Blank }
		}
	]
})

export default router

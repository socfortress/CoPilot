import { createRouter, createWebHistory } from "vue-router"
import Analytics from "@/views/Dashboard/Analytics.vue"

import AnalyticsIcon from "@vicons/ionicons5/Analytics"
import EcommerceIcon from "@vicons/fluent/ShoppingBagPercent20Regular"
import MapIcon from "@vicons/carbon/Map"
import EditorIcon from "@vicons/carbon/Pen"
import CalendarIcon from "@vicons/carbon/Calendar"
import EmailIcon from "@vicons/carbon/Email"
import ChatIcon from "@vicons/carbon/Chat"
import CardsIcon from "@vicons/fluent/PreviewLink20Regular"
import KanbanIcon from "@vicons/fluent/GridKanban20Regular"
import NotesIcon from "@vicons/carbon/Notebook"
import PersonIcon from "@vicons/ionicons5/PersonOutline"
import ToolboxIcon from "@vicons/carbon/ToolBox"
import MultiLanguageIcon from "@vicons/ionicons5/Language"
import IconsIcon from "@vicons/fluent/Icons24Regular"
import FlagIconsIcon from "@vicons/carbon/Flag"
import TablesIcon from "@vicons/carbon/ShowDataCards"
import LoginIcon from "@vicons/carbon/Login"
import LayoutIcon from "@vicons/fluent/DualScreenVerticalScroll24Regular"
import TypographyIcon from "@vicons/fluent/TextFont16Regular"

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
					meta: { icon: AnalyticsIcon, title: "Analytics" }
				},
				{
					path: "ecommerce",
					name: "ecommerce",
					component: () => import("@/views/Dashboard/eCommerce.vue"),
					meta: { icon: EcommerceIcon, title: "eCommerce" }
				}
			]
		},
		{
			path: "/calendar",
			name: "calendar",
			component: () => import("@/views/Apps/Calendars/FullCalendar.vue"),
			meta: { icon: CalendarIcon, title: "Calendar", auth: true, roles: "all" }
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
					meta: { icon: CalendarIcon, title: "Vue Cal" }
				},
				{
					path: "full-calendar",
					name: "full-calendar",
					component: () => import("@/views/Apps/Calendars/FullCalendar.vue"),
					meta: { icon: CalendarIcon, title: "Full Calendar" }
				}
			]
		},
		*/
		{
			path: "/email",
			name: "email",
			component: () => import("@/views/Apps/Mailbox.vue"),
			meta: { icon: EmailIcon, title: "Email", auth: true, roles: "all" }
		},
		{
			path: "/chat",
			name: "chat",
			component: () => import("@/views/Apps/Chat.vue"),
			meta: { icon: ChatIcon, title: "Chat", auth: true, roles: "all" }
		},
		{
			path: "/kanban",
			name: "kanban",
			component: () => import("@/views/Apps/Kanban.vue"),
			meta: { icon: KanbanIcon, title: "Kanban", auth: true, roles: "all" }
		},
		{
			path: "/notes",
			name: "notes",
			component: () => import("@/views/Apps/Notes.vue"),
			meta: { icon: NotesIcon, title: "Notes", auth: true, roles: "all" }
		},
		{
			path: "/typography",
			name: "typography",
			component: () => import("@/views/Typography.vue"),
			meta: { icon: TypographyIcon, title: "Typography", auth: true, roles: "all" }
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
					meta: { icon: CardsIcon, title: "Cards Basic" }
				},
				{
					path: "ecommerce",
					name: "cards-ecommerce",
					component: () => import("@/views/Cards/Ecommerce.vue"),
					meta: { icon: CardsIcon, title: "Cards Ecommerce" }
				},
				{
					path: "list",
					name: "cards-list",
					component: () => import("@/views/Cards/List.vue"),
					meta: { icon: CardsIcon, title: "Cards List" }
				},
				{
					path: "extra",
					name: "cards-extra",
					component: () => import("@/views/Cards/Extra.vue"),
					meta: { icon: CardsIcon, title: "Cards Extra" }
				},
				{
					path: "combo",
					name: "cards-combo",
					component: () => import("@/views/Cards/Combo.vue"),
					meta: { icon: CardsIcon, title: "Cards Combo" }
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
					meta: { icon: ToolboxIcon, title: "Refresh Tool" }
				},
				{
					path: "tour",
					name: "toolbox-tour",
					component: () => import("@/views/Toolbox/Tour.vue"),
					meta: { icon: ToolboxIcon, title: "Tour" }
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
					meta: { icon: LayoutIcon, title: "Left Sidebar" }
				},
				{
					path: "right-sidebar",
					name: "layout-right-sidebar",
					component: () => import("@/views/Layout/RightSidebar.vue"),
					meta: { icon: LayoutIcon, title: "Right Sidebar" }
				},
				{
					path: "full-width",
					name: "layout-full-width",
					component: () => import("@/views/Layout/FullWidth.vue"),
					meta: { icon: LayoutIcon, title: "Full Width" }
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
					meta: { icon: MapIcon, title: "Google maps" }
				},
				{
					path: "maplibre",
					name: "maps-maplibre",
					component: () => import("@/views/Maps/MapLibre.vue"),
					meta: { icon: MapIcon, title: "MapLibre" }
				},
				{
					path: "leaflet",
					name: "maps-leaflet",
					component: () => import("@/views/Maps/Leaflet.vue"),
					meta: { icon: MapIcon, title: "Leaflet" }
				},
				{
					path: "vectormap",
					name: "maps-vectormap",
					component: () => import("@/views/Maps/VectorMap.vue"),
					meta: { icon: MapIcon, title: "Vector Map" }
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
					meta: { icon: EditorIcon, title: "Quill" }
				},
				{
					path: "tiptap",
					name: "editors-tiptap",
					component: () => import("@/views/Editors/Tiptap.vue"),
					meta: { icon: EditorIcon, title: "Tiptap" }
				},
				{
					path: "milkdown",
					name: "editors-milkdown",
					component: () => import("@/views/Editors/Milkdown.vue"),
					meta: { icon: EditorIcon, title: "Milkdown" }
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
					meta: { icon: EditorIcon, title: "ApexCharts" }
				},
				{
					path: "chartjs",
					name: "charts-chartjs",
					component: () => import("@/views/Charts/ChartJS.vue"),
					meta: { icon: EditorIcon, title: "ChartJS" }
				}
			]
		},
		{
			path: "/multi-language",
			name: "multi-language",
			component: () => import("@/views/MultiLanguage.vue"),
			meta: { icon: MultiLanguageIcon, title: "Multi Language", auth: true, roles: "all" }
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
					meta: { icon: IconsIcon, title: "xIcons" }
				},
				{
					path: "flag",
					name: "icons-flag",
					component: () => import("@/views/Icons/Flag.vue"),
					meta: { icon: FlagIconsIcon, title: "Flag Icons" }
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
					meta: { icon: TablesIcon, title: "Tables Base" }
				},
				{
					path: "data-table",
					name: "tables-data-table",
					component: () => import("@/views/Tables/DataTable.vue"),
					meta: { icon: TablesIcon, title: "Data Table" }
				},
				{
					path: "grid",
					name: "tables-grid",
					component: () => import("@/views/Tables/Grid.vue"),
					meta: { icon: TablesIcon, title: "Data Grid" }
				}
			]
		},

		{
			path: "/profile",
			name: "profile",
			component: () => import("@/views/Profile.vue"),
			meta: { icon: PersonIcon, title: "Profile", auth: true, roles: "all" }
		},

		{
			path: "/login",
			name: "login",
			component: () => import("@/views/Auth/Login.vue"),
			meta: { icon: LoginIcon, title: "Login", forceLayout: Layout.Blank, checkAuth: true }
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

import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"
import { h } from "vue"
import { RouterLink } from "vue-router"
import { ICONS } from "@/const"
import { i18nGlobal } from "@/lang"
import { renderIcon } from "@/utils"

export interface NavbarFeatures {
	/** The SLA page is on for one of the user's customers (#1187). */
	sla?: boolean
	/** The Activity page is on for one of the user's customers (#1284). */
	activity?: boolean
	/** The Exposure page is on for one of the user's customers (#1289). */
	exposure?: boolean
}

// Labels are translated as the menu renders them (#1310), so they follow a language change.
export default function getItems({
	sla = false,
	activity = false,
	exposure = false
}: NavbarFeatures = {}): MenuMixedOption[] {
	const items: MenuMixedOption[] = [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Overview"
						}
					},
					{ default: () => i18nGlobal.t("navigation.routes.overview") }
				),
			key: "Overview",
			icon: renderIcon(ICONS.dashboard)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "AlertsList"
						}
					},
					{ default: () => i18nGlobal.t("navigation.routes.alerts") }
				),
			key: "AlertsList",
			icon: renderIcon(ICONS.alerts)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "CasesList"
						}
					},
					{ default: () => i18nGlobal.t("navigation.routes.cases") }
				),
			key: "CasesList",
			icon: renderIcon(ICONS.cases)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "AgentsList"
						}
					},
					{ default: () => i18nGlobal.t("navigation.routes.agents") }
				),
			key: "AgentsList",
			icon: renderIcon(ICONS.agents)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "EventSearch"
						}
					},
					{ default: () => i18nGlobal.t("navigation.routes.eventSearch") }
				),
			key: "EventSearch",
			icon: renderIcon(ICONS.eventSearch)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "ReportsList"
						}
					},
					{ default: () => i18nGlobal.t("navigation.routes.reports") }
				),
			key: "ReportsList",
			icon: renderIcon(ICONS.reports)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "DashboardsList"
						}
					},
					{ default: () => i18nGlobal.t("navigation.routes.dashboards") }
				),
			key: "DashboardsList",
			icon: renderIcon(ICONS.processes)
		}
	]

	if (exposure) {
		items.push({
			label: () =>
				h(
					RouterLink,
					{ to: { name: "Exposure" }, "data-testid": "nav-exposure" },
					{ default: () => i18nGlobal.t("navigation.routes.exposure") }
				),
			key: "Exposure",
			icon: renderIcon(ICONS.exposure)
		})
	}

	if (activity) {
		items.push({
			label: () =>
				h(
					RouterLink,
					{ to: { name: "Activity" }, "data-testid": "nav-activity" },
					{ default: () => i18nGlobal.t("navigation.routes.activity") }
				),
			key: "Activity",
			icon: renderIcon(ICONS.activity)
		})
	}

	if (sla) {
		items.push({
			label: () =>
				h(RouterLink, { to: { name: "Sla" }, "data-testid": "nav-sla" }, { default: () => i18nGlobal.t("navigation.routes.sla") }),
			key: "Sla",
			icon: renderIcon(ICONS.sla)
		})
	}

	return items
}

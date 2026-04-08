import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"
import { h } from "vue"
import { RouterLink } from "vue-router"
import { ICONS } from "@/const"
import { renderIcon } from "@/utils"

export default function getItems(): MenuMixedOption[] {
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
					{ default: () => "Overview" }
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
					{ default: () => "Alerts" }
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
					{ default: () => "Cases" }
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
							name: "Agents"
						}
					},
					{ default: () => "Agents" }
				),
			key: "Agents",
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
					{ default: () => "Event Search" }
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
							name: "DashboardsList"
						}
					},
					{ default: () => "Dashboards" }
				),
			key: "DashboardsList",
			icon: renderIcon(ICONS.processes)
		}
	]

	return items
}

import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"
import { h } from "vue"
import { RouterLink } from "vue-router"
import { ICONS } from "@/const"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import { renderIcon } from "@/utils"

export default function getItems(): MenuMixedOption[] {
	const authStore = useAuthStore()
	const userRole = authStore.userRole
	const isSuperuser = authStore.isSuperuser
	const isAnalyst = userRole === AuthUserRole.Analyst

	const systemChildren: MenuMixedOption[] = []

	if (isSuperuser || isAnalyst) {
		systemChildren.push({
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "SystemCollectorsList"
						}
					},
					{ default: () => "Collectors" }
				),
			key: "SystemCollectorsList"
		})
	}

	if (isSuperuser) {
		systemChildren.push(
			{
				label: () =>
					h(
						RouterLink,
						{
							to: {
								name: "SystemTasksList"
							}
						},
						{ default: () => "Tasks" }
					),
				key: "SystemTasksList"
			},
			{
				label: () =>
					h(
						RouterLink,
						{
							to: {
								name: "SystemMonitoring"
							}
						},
						{ default: () => "Monitoring" }
					),
				key: "SystemMonitoring"
			},
			{
				label: () =>
					h(
						RouterLink,
						{
							to: {
								name: "SystemCelery"
							}
						},
						{ default: () => "Celery" }
					),
				key: "SystemCelery"
			}
		)
	}

	const items: MenuMixedOption[] = [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Dashboard"
						}
					},
					{ default: () => "Dashboard" }
				),
			key: "Dashboard",
			icon: renderIcon(ICONS.dashboard)
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
					{ default: () => "Agents" }
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
							name: "CustomerList"
						}
					},
					{ default: () => "Customers" }
				),
			key: "CustomerList",
			icon: renderIcon(ICONS.customers)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "PackagesList"
						}
					},
					{ default: () => "Packages" }
				),
			key: "PackagesList",
			icon: renderIcon(ICONS.packages)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "PortsList"
						}
					},
					{ default: () => "Ports" }
				),
			key: "PortsList",
			icon: renderIcon(ICONS.ports)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "ProcessesList"
						}
					},
					{ default: () => "Processes" }
				),
			key: "ProcessesList",
			icon: renderIcon(ICONS.processes)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "VulnerabilitiesList"
						}
					},
					{ default: () => "Vulnerabilities" }
				),
			key: "VulnerabilitiesList",
			icon: renderIcon(ICONS.vulnerabilities)
		}
	]

	if (systemChildren.length) {
		items.push({
			label: "System",
			key: "system",
			icon: renderIcon(ICONS.system),
			children: systemChildren
		})
	}

	return items
}

import { renderIcon } from "@/utils"
import { h } from "vue"
import { RouterLink } from "vue-router"
import { type MenuMixedOption } from "naive-ui/es/menu/src/interface"

const BlankIcon = "carbon:document-blank"

export default function getItems(mode: "vertical" | "horizontal", collapsed: boolean): MenuMixedOption[] {
	return [
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Indices"
						}
					},
					{ default: () => "Indices" }
				),
			key: "Indices",
			icon: renderIcon(BlankIcon)
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
			icon: renderIcon(BlankIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Connectors"
						}
					},
					{ default: () => "Connectors" }
				),
			key: "Connectors",
			icon: renderIcon(BlankIcon)
		},
		{
			label: "Graylog",
			key: "Graylog",
			icon: renderIcon(BlankIcon),
			children: [
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "Graylog-Management"
								}
							},
							{ default: () => "Management" }
						),
					key: "Graylog-Management"
				},
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "Graylog-Metrics"
								}
							},
							{ default: () => "Metrics" }
						),
					key: "Graylog-Metrics"
				},
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "Graylog-Pipelines"
								}
							},
							{ default: () => "Pipelines" }
						),
					key: "Graylog-Pipelines"
				}
			]
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Alerts"
						}
					},
					{ default: () => "Alerts" }
				),
			key: "Alerts",
			icon: renderIcon(BlankIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Artifacts"
						}
					},
					{ default: () => "Artifacts" }
				),
			key: "Artifacts",
			icon: renderIcon(BlankIcon)
		},
		{
			label: "SOC",
			key: "SOC",
			icon: renderIcon(BlankIcon),
			children: [
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "Soc-Alerts"
								}
							},
							{ default: () => "Alerts" }
						),
					key: "Soc-Alerts"
				},
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "Soc-Cases"
								}
							},
							{ default: () => "Cases" }
						),
					key: "Soc-Cases"
				},
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "Soc-Users"
								}
							},
							{ default: () => "Users" }
						),
					key: "Soc-Users"
				}
			]
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Healthcheck"
						}
					},
					{ default: () => "Healthcheck" }
				),
			key: "Healthcheck",
			icon: renderIcon(BlankIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Customers"
						}
					},
					{ default: () => "Customers" }
				),
			key: "Customers",
			icon: renderIcon(BlankIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Logs"
						}
					},
					{ default: () => "Logs" }
				),
			key: "Logs",
			icon: renderIcon(BlankIcon)
		}
	]
}

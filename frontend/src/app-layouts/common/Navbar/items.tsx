import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"
import IncidentManagementIcon from "@/assets/icons/alert-settings-icon.svg"
import { renderIcon } from "@/utils"
import { h } from "vue"

import { RouterLink } from "vue-router"

const OverviewIcon = "carbon:dashboard"
const IndiciesIcon = "ph:list-magnifying-glass"
const AgentsIcon = "carbon:network-3"
const ConnectorsIcon = "carbon:hybrid-networking"
const GraylogIcon = "majesticons:pulse-line"
const AlertsIcon = "carbon:warning-hex"
const ArtifactsIcon = "carbon:document-multiple-01"
// const SocIcon = "carbon:security"
const HealthcheckIcon = "ph:heartbeat"
const CustomersIcon = "carbon:user-multiple"
const ExternalServicesIcon = "carbon:ibm-cloud-direct-link-2-dedicated"
const ReportCreationIcon = "carbon:report-data"
const SchedulerIcon = "material-symbols:autoplay"

export default function getItems(): MenuMixedOption[] {
	return [
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
			icon: renderIcon(OverviewIcon)
		},
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
			icon: renderIcon(IndiciesIcon)
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
			icon: renderIcon(AgentsIcon)
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
			icon: renderIcon(ConnectorsIcon)
		},
		{
			label: "Graylog",
			key: "Graylog",
			icon: renderIcon(GraylogIcon),
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
			icon: renderIcon(AlertsIcon)
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
			icon: renderIcon(ArtifactsIcon)
		},
		/*
		{
			label: "SOC",
			key: "Soc",
			icon: renderIcon(SocIcon),
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
				},
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "Soc-PendingAlerts"
								}
							},
							{ default: () => "Pending Alerts" }
						),
					key: "Soc-PendingAlerts"
				}
			]
		},
		*/
		{
			label: "Incident Management",
			key: "IncidentManagement",
			icon: renderIcon(IncidentManagementIcon),
			children: [
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "IncidentManagement-Sources"
								}
							},
							{ default: () => "Sources" }
						),
					key: "IncidentManagement-Sources"
				},
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "IncidentManagement-Alerts"
								}
							},
							{ default: () => "Alerts" }
						),
					key: "IncidentManagement-Alerts"
				},
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "IncidentManagement-Cases"
								}
							},
							{ default: () => "Cases" }
						),
					key: "IncidentManagement-Cases"
				},
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "IncidentManagement-Sigma"
								}
							},
							{ default: () => "SIGMA" }
						),
					key: "IncidentManagement-Sigma"
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
			icon: renderIcon(HealthcheckIcon)
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
			icon: renderIcon(CustomersIcon)
		},
		{
			label: "External Services",
			key: "ExternalServices",
			icon: renderIcon(ExternalServicesIcon),
			children: [
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "ExternalServices-ThirdPartyIntegrations"
								}
							},
							{ default: () => "3rd Party Integrations" }
						),
					key: "ExternalServices-ThirdPartyIntegrations"
				},
				{
					label: () =>
						h(
							RouterLink,
							{
								to: {
									name: "ExternalServices-NetworkConnectors"
								}
							},
							{ default: () => "Network Connectors" }
						),
					key: "ExternalServices-NetworkConnectors"
				}
			]
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "ReportCreation"
						}
					},
					{ default: () => "Report Creation" }
				),
			key: "ReportCreation",
			icon: renderIcon(ReportCreationIcon)
		},
		{
			label: () =>
				h(
					RouterLink,
					{
						to: {
							name: "Scheduler"
						}
					},
					{ default: () => "Scheduler" }
				),
			key: "Scheduler",
			icon: renderIcon(SchedulerIcon)
		}
	]
}

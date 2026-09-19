import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const PlatformIcon = "carbon:settings"

function group(label: string, key: string, children: MenuMixedOption[]): MenuMixedOption {
	return { label, key, children }
}

/**
 * Deployment configuration, gathered from the old Tools / Log Management /
 * Healthcheck / Notifications sections and the avatar menu (#1152).
 *
 * Visible to analysts, mirroring the access they already had. Only what they
 * couldn't use or see before is admin-only: the Notifications pages (admin-only
 * routes) and SSO / Audit Log (admin-only in the old avatar menu).
 */
export function getPlatformItem(isAdmin: boolean): MenuMixedOption {
	const adminOnly = (items: MenuMixedOption[]) => (isAdmin ? items : [])

	return parentMenuItem("Platform", "Platform", PlatformIcon, [
		group("Connectors & Integrations", "Platform-Integrations", [
			routerLinkItem("Connectors", "Connectors"),
			routerLinkItem("Integrations", "ExternalServices-ThirdPartyIntegrations"),
			routerLinkItem("Network Connectors", "ExternalServices-NetworkConnectors"),
			routerLinkItem("Shuffle App Auth", "ExternalServices-ShuffleAppAuth")
		]),
		...adminOnly([
			group("Notifications", "Platform-Notifications", [
				routerLinkItem("Internal Routes", "InternalNotifications"),
				routerLinkItem("Message Templates", "MessageTemplates")
			])
		]),
		group("Log Management", "Platform-LogManagement", [
			routerLinkItem("Index Management", "Indices"),
			routerLinkItem("Snapshot & Restore", "Snapshots"),
			routerLinkItem("Graylog Management", "Graylog-Management"),
			routerLinkItem("Graylog Metrics", "Graylog-Metrics"),
			routerLinkItem("Graylog Pipelines", "Graylog-Pipelines")
		]),
		group("Health", "Platform-Health", [
			routerLinkItem("Healthcheck Alerts", "Healthcheck"),
			routerLinkItem("Metrics", "Metrics")
		]),
		group("Access", "Platform-Access", [
			routerLinkItem("Users", "Users"),
			...adminOnly([routerLinkItem("SSO", "SSOConfig"), routerLinkItem("Audit Log", "Audit")])
		]),
		group("System", "Platform-System", [
			routerLinkItem("Scheduler", "Scheduler"),
			routerLinkItem("Logs", "Logs"),
			routerLinkItem("License", "License"),
			routerLinkItem("Stack Provisioning", "StackProvisioning"),
			routerLinkItem("Customer Portal", "CustomerPortal")
		])
	])
}

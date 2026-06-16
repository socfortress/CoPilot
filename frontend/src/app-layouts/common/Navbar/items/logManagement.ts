import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const GraylogIcon = "majesticons:pulse-line"

export const logManagementItem: MenuMixedOption = parentMenuItem("Log Management", "LogManagement", GraylogIcon, [
	routerLinkItem("Index Management", "Indices"),
	routerLinkItem("Snapshot & Restore", "Snapshots"),
	routerLinkItem("Graylog Management", "Graylog-Management"),
	routerLinkItem("Graylog Metrics", "Graylog-Metrics"),
	routerLinkItem("Graylog Pipelines", "Graylog-Pipelines")
])

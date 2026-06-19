import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const AlertsIcon = "carbon:warning-hex"

export const siemItem: MenuMixedOption = parentMenuItem("SIEM", "SIEM", AlertsIcon, [
	routerLinkItem("Alerts", "Alerts-SIEM"),
	routerLinkItem("Event Search", "EventSearch"),
	routerLinkItem("Dashboards", "Dashboards"),
	routerLinkItem("MITRE ATT&CK", "Alerts-Mitre"),
	routerLinkItem("Atomic Red Team", "Alerts-AtomicRedTeam")
])

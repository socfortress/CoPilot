import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const InvestigateIcon = "carbon:search"

export const investigateItem: MenuMixedOption = parentMenuItem("Investigate", "Investigate", InvestigateIcon, [
	routerLinkItem("Event Search", "EventSearch"),
	// Raw alerts from the SIEM indices. Named apart from Incidents → Alerts,
	// the triage queue, which shared the label "Alerts" before #1152.
	routerLinkItem("SIEM Alerts", "Alerts-SIEM"),
	routerLinkItem("Dashboards", "Dashboards"),
	routerLinkItem("File Analysis", "FileAnalysis"),
	// One page with a tab per source; OpenCTI is a tab there, shown only for a
	// verified connector, rather than its own entry (#1153).
	routerLinkItem("Threat Intel", "ThreatIntel")
])

import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const InvestigateIcon = "carbon:search"

/** Opens the Threat Intel drawer rather than a page; handled in Navbar.vue. */
export const THREAT_INTEL_PANEL_KEY = "Investigate-ThreatIntel"

/**
 * @param showOpenCTI Only true for a verified OpenCTI connector. Most deployments
 *   don't run OpenCTI, so the entry would otherwise lead to an empty page.
 */
export function getInvestigateItem(showOpenCTI: boolean): MenuMixedOption {
	return parentMenuItem("Investigate", "Investigate", InvestigateIcon, [
		routerLinkItem("Event Search", "EventSearch"),
		// Raw alerts from the SIEM indices. Named apart from Incidents → Alerts,
		// the triage queue, which shared the label "Alerts" before #1152.
		routerLinkItem("SIEM Alerts", "Alerts-SIEM"),
		routerLinkItem("Dashboards", "Dashboards"),
		routerLinkItem("File Analysis", "FileAnalysis"),
		{ label: "Threat Intel", key: THREAT_INTEL_PANEL_KEY },
		...(showOpenCTI ? [routerLinkItem("OpenCTI", "OpenCTI")] : [])
	])
}

import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const DetectionsIcon = "carbon:radar"

// What fires, which was spread across the Detections Catalog, Agents and SIEM
// (#1152). Alert sources and exclusions sit under Incidents: they gate ingestion.
export const detectionsItem: MenuMixedOption = parentMenuItem("Detections", "Detections", DetectionsIcon, [
	routerLinkItem("Catalog", "DetectionCatalog"),
	routerLinkItem("CoPilot Searches", "CopilotSearches"),
	// The Wazuh rule-file editor, formerly "Agents → Detection Rules".
	routerLinkItem("Wazuh Rules", "DetectionRules"),
	routerLinkItem("MITRE ATT&CK", "Alerts-Mitre"),
	routerLinkItem("Atomic Red Team", "Alerts-AtomicRedTeam")
])

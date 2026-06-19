import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const AgentsIcon = "carbon:network-3"

const scaItem: MenuMixedOption = {
	label: "Security Configuration Assessment",
	key: "SCA",
	children: [routerLinkItem("SCA Overview", "ScaOverview"), routerLinkItem("SCA Policies", "ScaPolicies")]
}

export const agentsItem: MenuMixedOption = parentMenuItem("Agents", "Agents", AgentsIcon, [
	routerLinkItem("Agents list", "Agents"),
	routerLinkItem("Artifacts", "Artifacts"),
	routerLinkItem("Groups", "Groups"),
	routerLinkItem("Sysmon Config", "SysmonConfig"),
	routerLinkItem("Detection Rules", "DetectionRules"),
	routerLinkItem("CoPilot Actions", "CopilotActions"),
	routerLinkItem("CoPilot Searches", "CopilotSearches"),
	routerLinkItem("Vulnerability Overview", "VulnerabilityOverview"),
	routerLinkItem("Patch Tuesday", "PatchTuesday"),
	scaItem
])

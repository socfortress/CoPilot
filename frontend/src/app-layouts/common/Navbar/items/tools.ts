import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const ToolsIcon = "carbon:tool-box"

export const toolsItem: MenuMixedOption = parentMenuItem("Tools", "Tools", ToolsIcon, [
	routerLinkItem("Connectors", "Connectors"),
	{ label: "Stack Provisioning", key: "Tools-StackProvisioning" },
	routerLinkItem("Cloud Security Assessment", "CloudSecurityAssessment"),
	routerLinkItem("Web Vulnerability Assessment", "WebVulnerabilityAssessment"),
	routerLinkItem("GitHub Audit", "GitHubAudit"),
	{ label: "Active Response", key: "Tools-ActiveResponse" },
	{ label: "Threat Intel", key: "Tools-ThreatIntel" }
])

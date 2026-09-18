import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const ToolsIcon = "carbon:tool-box"

/**
 * @param showOpenCTI Only true for a verified OpenCTI connector. Most deployments
 *   don't run OpenCTI, so the entry would otherwise lead to an empty page.
 */
export function getToolsItem(showOpenCTI: boolean): MenuMixedOption {
  return parentMenuItem("Tools", "Tools", ToolsIcon, [
		routerLinkItem("Connectors", "Connectors"),
		routerLinkItem("File Analysis", "FileAnalysis"),
		{ label: "Stack Provisioning", key: "Tools-StackProvisioning" },
		routerLinkItem("Cloud Security Assessment", "CloudSecurityAssessment"),
		routerLinkItem("Web Vulnerability Assessment", "WebVulnerabilityAssessment"),
		routerLinkItem("GitHub Audit", "GitHubAudit"),
		{ label: "Active Response", key: "Tools-ActiveResponse" },
		{ label: "Threat Intel", key: "Tools-ThreatIntel" },
		...(showOpenCTI ? [routerLinkItem("OpenCTI", "OpenCTI")] : [])
	])
}

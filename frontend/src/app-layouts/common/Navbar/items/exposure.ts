import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const ExposureIcon = "carbon:security"

const configurationAssessmentItem: MenuMixedOption = {
	label: "Configuration Assessment",
	key: "Exposure-SCA",
	children: [routerLinkItem("SCA Overview", "ScaOverview"), routerLinkItem("SCA Policies", "ScaPolicies")]
}

// Weaknesses to fix before they are exploited: endpoint vulnerabilities and
// configuration, plus the cloud, web and GitHub posture assessments (#1152).
export const exposureItem: MenuMixedOption = parentMenuItem("Exposure", "Exposure", ExposureIcon, [
	routerLinkItem("Vulnerabilities", "VulnerabilityOverview"),
	routerLinkItem("Patch Tuesday", "PatchTuesday"),
	configurationAssessmentItem,
	routerLinkItem("Cloud Security Assessment", "CloudSecurityAssessment"),
	routerLinkItem("Web Vulnerability Assessment", "WebVulnerabilityAssessment"),
	routerLinkItem("GitHub Audit", "GitHubAudit")
])

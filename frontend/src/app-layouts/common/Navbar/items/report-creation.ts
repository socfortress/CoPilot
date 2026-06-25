import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const ReportCreationIcon = "carbon:report-data"

export const reportCreationItem: MenuMixedOption = parentMenuItem(
	"Report Creation",
	"ReportCreation",
	ReportCreationIcon,
	[
		routerLinkItem("General Reports", "ReportCreation"),
		routerLinkItem("Vulnerability Reports", "VulnerabilityReports"),
		routerLinkItem("SCA Reports", "SCAReports")
	]
)

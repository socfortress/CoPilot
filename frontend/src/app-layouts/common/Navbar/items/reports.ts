import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const ReportsIcon = "carbon:report-data"

export const reportsItem: MenuMixedOption = parentMenuItem("Reports", "Reports", ReportsIcon, [
	routerLinkItem("General Reports", "ReportCreation"),
	routerLinkItem("Vulnerability Reports", "VulnerabilityReports"),
	routerLinkItem("SCA Reports", "SCAReports")
])

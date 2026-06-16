import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import IncidentManagementIcon from "@/assets/icons/alert-settings-icon.svg"

import { parentMenuItem, routerLinkItem } from "./helpers"

export const incidentManagementItem: MenuMixedOption = parentMenuItem(
	"Incident Management",
	"IncidentManagement",
	IncidentManagementIcon,
	[
		routerLinkItem("Sources", "IncidentManagement-Sources"),
		routerLinkItem("Alerts", "IncidentManagement-Alerts"),
		routerLinkItem("Cases", "IncidentManagement-Cases"),
		routerLinkItem("Case Templates", "IncidentManagement-CaseTemplates")
		/*
		routerLinkItem("SIGMA", "IncidentManagement-Sigma"),
		*/
	]
)

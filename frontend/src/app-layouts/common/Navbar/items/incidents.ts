import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import IncidentManagementIcon from "@/assets/icons/alert-settings-icon.svg"

import { parentMenuItem, routerLinkItem } from "./helpers"

// The triage queue, led by the setup it depends on: until an alert source is
// defined nothing is ingested, so it comes first. Its page also holds the
// exclusion rules (#1152).
export const incidentsItem: MenuMixedOption = parentMenuItem("Incidents", "Incidents", IncidentManagementIcon, [
	routerLinkItem("Alert Sources & Exclusions", "IncidentManagement-Sources"),
	routerLinkItem("Alerts", "IncidentManagement-Alerts"),
	routerLinkItem("Cases", "IncidentManagement-Cases"),
	// What portal users asked the SOC (#1305): answered from the case or alert it is on.
	routerLinkItem("Customer Questions", "IncidentManagement-CustomerQuestions"),
	routerLinkItem("Case Templates", "IncidentManagement-CaseTemplates")
	/*
	routerLinkItem("SIGMA", "IncidentManagement-Sigma"),
	*/
])

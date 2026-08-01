import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { renderIcon } from "@/utils"

import { agentsItem } from "./items/agents"
import { healthcheckItem } from "./items/healthcheck"
import { routerLinkItem } from "./items/helpers"
import { incidentManagementItem } from "./items/incident-management"
import { logManagementItem } from "./items/log-management"
import { reportCreationItem } from "./items/report-creation"
import { siemItem } from "./items/siem"
import { toolsItem } from "./items/tools"

const OverviewIcon = "carbon:dashboard"
const CustomersIcon = "carbon:user-multiple"
const AiAnalystIcon = "carbon:machine-learning-model"
const DetectionCatalogIcon = "carbon:catalog"
const InternalNotificationsIcon = "carbon:notification"

export default function getItems(): MenuMixedOption[] {
	return [
		{
			...routerLinkItem("Overview", "Overview"),
			icon: renderIcon(OverviewIcon)
		},
		{
			...routerLinkItem("AI Analyst", "AiAnalyst"),
			icon: renderIcon(AiAnalystIcon)
		},
		{
			...routerLinkItem("Detections Catalog", "DetectionCatalog"),
			icon: renderIcon(DetectionCatalogIcon)
		},
		{
			...routerLinkItem("Customers", "Customers"),
			icon: renderIcon(CustomersIcon)
		},
		{
			// Deployment-wide: where the SOC's own assignment notifications go.
			// Distinct from a customer's routes, which live on the customer.
			...routerLinkItem("Internal Notifications", "InternalNotifications"),
			icon: renderIcon(InternalNotificationsIcon)
		},
		siemItem,
		incidentManagementItem,
		agentsItem,
		logManagementItem,
		reportCreationItem,
		healthcheckItem,
		toolsItem
	]
}

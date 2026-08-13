import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { renderIcon } from "@/utils"

import { agentsItem } from "./items/agents"
import { healthcheckItem } from "./items/healthcheck"
import { parentMenuItem, routerLinkItem } from "./items/helpers"
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
		// Deployment-wide notification config: where the SOC's own assignment
		// notifications go, and the shared message templates every route can
		// render with. Both are distinct from a customer's own routes, which
		// live on the customer.
		parentMenuItem("Notifications", "Notifications", InternalNotificationsIcon, [
			routerLinkItem("Internal Routes", "InternalNotifications"),
			routerLinkItem("Message Templates", "MessageTemplates")
		]),
		siemItem,
		incidentManagementItem,
		agentsItem,
		logManagementItem,
		reportCreationItem,
		healthcheckItem,
		toolsItem
	]
}

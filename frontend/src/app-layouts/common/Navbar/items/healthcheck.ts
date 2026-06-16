import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const HealthcheckIcon = "ph:heartbeat"

export const healthcheckItem: MenuMixedOption = parentMenuItem("Healthcheck", "HealthcheckMenu", HealthcheckIcon, [
	routerLinkItem("Healthcheck Alerts", "Healthcheck"),
	routerLinkItem("Metrics Overview", "Metrics")
])

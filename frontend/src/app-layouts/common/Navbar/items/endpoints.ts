import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const EndpointsIcon = "carbon:network-3"

// Only the fleet itself. Detection content moved to Detections, response
// actions to Respond, and vulnerabilities / SCA to Exposure (#1152).
// Sysmon Config deploys to endpoints: admins and responders only (#1219), like the page.
export function getEndpointsItem(canRespond: boolean): MenuMixedOption {
	return parentMenuItem("Endpoints", "Endpoints", EndpointsIcon, [
		routerLinkItem("Agents", "Agents"),
		routerLinkItem("Agent Groups", "Groups"),
		...(canRespond ? [routerLinkItem("Sysmon Config", "SysmonConfig")] : [])
	])
}

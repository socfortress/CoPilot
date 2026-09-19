import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const RespondIcon = "carbon:flash"

export const respondItem: MenuMixedOption = parentMenuItem("Respond", "Respond", RespondIcon, [
	routerLinkItem("Active Response", "ActiveResponse"),
	routerLinkItem("Artifacts", "Artifacts"),
	routerLinkItem("CoPilot Actions", "CopilotActions")
])

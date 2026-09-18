import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const RespondIcon = "carbon:flash"

/** Opens the Active Response wizard rather than a page; handled in Navbar.vue. */
export const ACTIVE_RESPONSE_PANEL_KEY = "Respond-ActiveResponse"

export const respondItem: MenuMixedOption = parentMenuItem("Respond", "Respond", RespondIcon, [
	{ label: "Active Response", key: ACTIVE_RESPONSE_PANEL_KEY },
	routerLinkItem("Artifacts", "Artifacts"),
	routerLinkItem("CoPilot Actions", "CopilotActions")
])

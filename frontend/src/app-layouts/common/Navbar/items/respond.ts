import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { parentMenuItem, routerLinkItem } from "./helpers"

const RespondIcon = "carbon:flash"

// CoPilot Actions run on endpoints: admins and responders only (#1219), like the page.
export function getRespondItem(canRespond: boolean): MenuMixedOption {
	return parentMenuItem("Respond", "Respond", RespondIcon, [
		routerLinkItem("Active Response", "ActiveResponse"),
		routerLinkItem("Artifacts", "Artifacts"),
		...(canRespond ? [routerLinkItem("CoPilot Actions", "CopilotActions")] : [])
	])
}

import type { MenuMixedOption } from "naive-ui/es/menu/src/interface"

import { useOpenCTIAvailability } from "@/composables/useOpenCTIAvailability"
import { useAuthStore } from "@/stores/auth"
import { renderIcon } from "@/utils"

import { detectionsItem } from "./items/detections"
import { endpointsItem } from "./items/endpoints"
import { exposureItem } from "./items/exposure"
import { routerLinkItem } from "./items/helpers"
import { incidentsItem } from "./items/incidents"
import { getInvestigateItem } from "./items/investigate"
import { getPlatformItem } from "./items/platform"
import { reportsItem } from "./items/reports"
import { respondItem } from "./items/respond"

const OverviewIcon = "carbon:dashboard"
const CustomersIcon = "carbon:user-multiple"
const AiAnalystIcon = "carbon:machine-learning-model"

/**
 * The sidebar, ordered the way SOC work happens: triage, investigate, respond,
 * tune detections, reduce exposure, then administer (#1152).
 *
 * Every leaf's key is its route name. Navbar.vue highlights the current page by
 * route name, so renaming or moving an item never breaks that as long as the
 * key stays the route name. The few keys that aren't route names open a panel
 * instead of a page (see Navbar.vue's handleMenuSelect).
 */
export default function getItems(): MenuMixedOption[] {
	// Both read inside the Navbar's computed, so the menu follows OpenCTI being
	// verified and the signed-in user's role without a reload.
	const { available: openCTIAvailable } = useOpenCTIAvailability()
	const authStore = useAuthStore()

	return [
		{
			...routerLinkItem("Overview", "Overview"),
			icon: renderIcon(OverviewIcon)
		},
		{
			...routerLinkItem("AI Analyst", "AiAnalyst"),
			icon: renderIcon(AiAnalystIcon)
		},
		incidentsItem,
		getInvestigateItem(openCTIAvailable.value),
		respondItem,
		detectionsItem,
		exposureItem,
		endpointsItem,
		{
			...routerLinkItem("Customers", "Customers"),
			icon: renderIcon(CustomersIcon)
		},
		reportsItem,
		getPlatformItem(authStore.isAdmin)
	]
}

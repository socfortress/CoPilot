import { createRouter, createWebHistory } from "vue-router"
import { resetNavigationScope } from "@/api/navigation-abort"
import { authCheck } from "@/utils/auth"
import { routes } from "./routes"

const router = createRouter({
	history: createWebHistory(import.meta.env.BASE_URL),
	routes
})

router.beforeEach(route => {
	return authCheck(route)
})

// Cancel the outgoing page's in-flight reads (#1072).
//
// `afterEach` rather than `beforeEach`: the navigation is confirmed by now, so a
// guard that redirects or cancels can no longer abort requests of a page we end
// up staying on — and it still runs before the incoming components mount, so the
// new page's own requests land in the fresh scope.
//
// Path-only: views that keep state in the query string (the Detection Catalog's
// `?tab=`/`?story=`, list filters synced to the URL) push a query change *while*
// their own request is in flight, and resetting there would cancel it.
router.afterEach((to, from) => {
	if (to.path !== from.path) {
		resetNavigationScope()
	}
})

export default router

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
// `beforeEach`, and the timing is the whole point. Every route in this app is
// lazily loaded (`component: () => import(...)`), so the router must fetch the
// target's JS chunk before it can complete the navigation. A browser allows only
// ~6 concurrent connections per host, and a page like Overview saturates them
// with requests that take seconds — so the chunk request *queues behind the page
// you are leaving*, and navigation appears to hang until those calls finish.
//
// This originally ran in `afterEach`, which fires only once navigation is
// confirmed — i.e. after the chunk has already been fetched. Correct, but far
// too late to free the connections that were blocking it. Leaving Overview
// immediately felt instant (few requests in flight); leaving after a second or
// two stalled.
//
// Registered *after* `authCheck` on purpose: guards run in registration order and
// a rejected navigation skips the rest, so a redirect to /login can never abort
// the requests of a page we end up staying on. There are no `beforeRouteLeave`
// guards in this app, so past this point the navigation always completes.
//
// Path-only: views that keep state in the query string (the Detection Catalog's
// `?tab=`/`?story=`, list filters synced to the URL) push a query change *while*
// their own request is in flight, and resetting there would cancel it.
router.beforeEach((to, from) => {
	if (to.path !== from.path) {
		resetNavigationScope()
	}
	return true
})

export default router

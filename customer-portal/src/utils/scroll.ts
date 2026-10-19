import type { RouteLocationNormalized } from "vue-router"

/**
 * A new page starts at the top; a change of the same page's query keeps the place.
 *
 * Filters, periods and tabs live in the query (`?trend=7d`, the alert filters) and are
 * written with `router.replace`: scrolling to the top on those made the page jump away from
 * the control the user had just used.
 */
export function startsAtTop(to: Pick<RouteLocationNormalized, "path">, from: Pick<RouteLocationNormalized, "path">) {
	return to.path !== from.path
}

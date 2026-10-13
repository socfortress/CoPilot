import type { RouteMatcherOptions } from "cypress/types/net-stubbing"

/**
 * The alerts list's one request (#1245), optionally only when it carries these query
 * values. Matched by path, not by glob: in a glob `?` is any one character, so
 * `alerts/filter?*` also matches `alerts/filter-options?…`.
 */
export function alertsListRequest(query?: Record<string, string>): RouteMatcherOptions {
	return { method: "GET", pathname: "/api/incidents/db_operations/alerts/filter", ...(query ? { query } : {}) }
}

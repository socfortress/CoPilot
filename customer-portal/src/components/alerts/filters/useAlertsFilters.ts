import type { AlertsFilters } from "./alertsFilters"
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { EMPTY_ALERTS_FILTERS, filtersFromQuery, filtersKey, withFilters } from "./alertsFilters"

/**
 * The alerts list's filters, read from and written to the query string (#1245).
 *
 * Writes `replace` the current entry (a filter change is not a page of history: the back
 * button leaves the list, as everywhere else in the portal). A change made while the
 * previous one is still being applied builds on it, not on the URL it is about to
 * replace, so two quick changes never undo each other.
 */
export function useAlertsFilters() {
	const route = useRoute()
	const router = useRouter()

	const filters = computed<AlertsFilters>(() => filtersFromQuery(route.query))
	let applying: AlertsFilters | null = null

	async function setFilters(patch: Partial<AlertsFilters>) {
		const current = applying ?? filters.value
		const next = { ...current, ...patch }
		if (filtersKey(next) === filtersKey(current)) return

		applying = next
		try {
			await router.replace({ query: withFilters(route.query, next) })
		} finally {
			if (applying === next) applying = null
		}
	}

	function clearFilters() {
		return setFilters(EMPTY_ALERTS_FILTERS)
	}

	return { filters, setFilters, clearFilters }
}

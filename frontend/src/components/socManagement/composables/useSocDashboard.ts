import type { Ref } from "vue"
import type { SocDashboardQuery } from "@/api/endpoints/soc-management"
import type { ApiError } from "@/types/common"
import type { SocDashboard } from "@/types/soc-management"
import { computed, shallowRef, watch } from "vue"
import Api from "@/api"

/** A stable key: the same filters must not refetch, and Date objects never compare equal. */
export function dashboardKey(query: SocDashboardQuery): string {
	return JSON.stringify({
		from: query.dateFrom.toISOString(),
		to: query.dateTo.toISOString(),
		customers: [...(query.customerCodes ?? [])].sort(),
		severities: [...(query.severities ?? [])].sort(),
		sources: [...(query.sources ?? [])].sort(),
		bucket: query.bucket ?? null
	})
}

function isAbort(error: unknown): boolean {
	const name = (error as { name?: string; code?: string })?.name
	const code = (error as { code?: string })?.code
	return name === "CanceledError" || name === "AbortError" || code === "ERR_CANCELED"
}

/**
 * Loads the dashboard for `query`, one snapshot per change of filters.
 *
 * A new load aborts the one still in flight, and only the latest load clears
 * `loading` — a superseded response can never overwrite a newer one. The previous
 * dashboard stays on screen while the next loads, so a filter change dims the page
 * instead of flashing skeletons.
 */
export function useSocDashboard(query: Ref<SocDashboardQuery>) {
	const dashboard = shallowRef<SocDashboard | null>(null)
	const loading = shallowRef(false)
	const error = shallowRef<ApiError | null>(null)
	let controller: AbortController | null = null

	async function load() {
		controller?.abort()
		const current = new AbortController()
		controller = current
		loading.value = true
		error.value = null
		try {
			const response = await Api.socManagement.getDashboard(query.value, current.signal)
			if (controller === current) dashboard.value = response.data
		} catch (err) {
			if (controller === current && !isAbort(err)) error.value = err as ApiError
		} finally {
			if (controller === current) loading.value = false
		}
	}

	watch(() => dashboardKey(query.value), load, { immediate: true })

	return {
		dashboard: computed(() => dashboard.value),
		loading: computed(() => loading.value),
		error: computed(() => error.value),
		reload: load
	}
}

import type { Ref } from "vue"
import type { TrendDay } from "./trend"
import type { ApiError } from "@/types/common"
import type { OverviewTrend, OverviewTrendRange } from "@/types/portal"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { getApiErrorMessage } from "@/utils"
import { trendDays } from "./trend"

/**
 * The Overview's trend: one `GET /customer_portal/overview/trend` per range and customer
 * filter change, apart from the Overview's own call so that call stays light (#1181).
 * Only the latest load counts, and the previous days stay on screen while the next ones
 * load.
 */
export function useOverviewTrend(range: Ref<OverviewTrendRange>) {
	const customerFilterStore = useCustomerFilterStore()
	const trend = ref<OverviewTrend | null>(null)
	const error = ref<string | null>(null)
	const { loading, run } = useLatestRequest()

	/** Local days, every one of them listed; `null` until the first answer. */
	const days = computed<TrendDay[] | null>(() => (trend.value ? trendDays(trend.value) : null))

	function load() {
		return run(
			async signal => {
				const { data } = await Api.portal.overviewTrend({
					range: range.value,
					customerCodes: customerFilterStore.queryCustomerCodes,
					signal
				})
				if (signal.aborted) return
				trend.value = data
				error.value = null
			},
			err => {
				error.value = getApiErrorMessage(err as ApiError)
			}
		)
	}

	// The store replaces the selection array on every change: no deep watch needed.
	watch([range, () => customerFilterStore.queryCustomerCodes], load, { immediate: true })

	return { trend, days, error, loading, reload: load }
}

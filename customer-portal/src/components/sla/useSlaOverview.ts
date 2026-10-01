import type { Ref } from "vue"
import type { PeriodPreset } from "./sla"
import type { ApiError } from "@/types/common"
import type { SlaOverview } from "@/types/sla"
import { ref, watch } from "vue"
import Api from "@/api"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { getApiErrorMessage } from "@/utils"
import { periodRange } from "./sla"

/**
 * The SLA page's data: one `GET /customer_portal/sla/overview` per period and customer
 * filter change. Only the latest load counts (`useLatestRequest`), and the previous
 * figures stay on screen while the next ones load, so switching periods never blanks
 * the page.
 */
export function useSlaOverview(period: Ref<PeriodPreset["key"]>) {
	const customerFilterStore = useCustomerFilterStore()
	const overview = ref<SlaOverview | null>(null)
	const error = ref<string | null>(null)
	const { loading, run } = useLatestRequest()

	function load() {
		const { from, to } = periodRange(period.value)
		return run(
			async signal => {
				const response = await Api.sla.getOverview(from, to, customerFilterStore.queryCustomerCodes, signal)
				overview.value = response.data
				error.value = null
			},
			err => {
				error.value = getApiErrorMessage(err as ApiError)
			}
		)
	}

	// The store replaces the selection array on every change: no deep watch needed.
	watch([period, () => customerFilterStore.queryCustomerCodes], load, { immediate: true })

	return { overview, error, loading, reload: load }
}

import type { Ref } from "vue"
import type { Activity, ActivityRange } from "@/types/activity"
import type { ApiError } from "@/types/common"
import { ref, watch } from "vue"
import Api from "@/api"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { getApiErrorMessage } from "@/utils"

/**
 * The Activity page's data (#1284): one `GET /customer_portal/activity` per range and
 * customer filter change. Only the latest load counts (`useLatestRequest`), and the
 * previous figures stay on screen while the next ones load, so switching ranges never
 * blanks the page.
 */
export function useActivity(range: Ref<ActivityRange>) {
	const customerFilterStore = useCustomerFilterStore()
	const activity = ref<Activity | null>(null)
	const error = ref<string | null>(null)
	const { loading, run } = useLatestRequest()

	function load() {
		return run(
			async signal => {
				const response = await Api.activity.getActivity(range.value, customerFilterStore.queryCustomerCodes, signal)
				// A response that lands after a newer load started must not overwrite it.
				if (signal.aborted) return
				activity.value = response.data
				error.value = null
			},
			err => {
				error.value = getApiErrorMessage(err as ApiError)
			}
		)
	}

	// The store replaces the selection array on every change: no deep watch needed.
	watch([range, () => customerFilterStore.queryCustomerCodes], load, { immediate: true })

	return { activity, error, loading, reload: load }
}

import type { SelectOption } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"

/**
 * Customers as naive-ui select options.
 *
 * State is module-level for the same reason as `useDetectionCategories`: the list
 * only moves when an operator adds or removes a customer, and several surfaces
 * (backtest, custom repos, …) need the very same options. Sharing one fetch also
 * means opening a second modal is instant rather than showing another spinner.
 * Concurrent callers await the same promise.
 */
const options = ref<SelectOption[]>([])
const loading = ref(false)
let inflight: Promise<void> | null = null

function fetchCustomers(): Promise<void> {
	if (inflight) return inflight

	loading.value = true
	inflight = Api.customers
		.getCustomers({})
		.then(res => {
			options.value = (res.data.customers || []).map(c => ({
				label: `${c.customer_name} (${c.customer_code})`,
				value: c.customer_code
			}))
		})
		.catch(() => {
			// Silent — the select simply has no options, which the callers already
			// handle by keeping their submit button disabled.
		})
		.finally(() => {
			loading.value = false
			inflight = null
		})

	return inflight
}

export function useCustomerOptions() {
	/** Fetch once; a second caller reuses what the first one loaded. */
	function load() {
		if (options.value.length) return Promise.resolve()
		return fetchCustomers()
	}

	/** Force a re-fetch — for when a customer was just created or removed. */
	function reload() {
		return fetchCustomers()
	}

	return {
		options: computed(() => options.value),
		loading: computed(() => loading.value),
		load,
		reload
	}
}

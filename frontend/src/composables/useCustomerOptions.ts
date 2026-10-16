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
// Bumped by `resetCustomerOptions`: an answer for the previous session is dropped.
let generation = 0

function fetchCustomers(): Promise<void> {
	if (inflight) return inflight

	const asked = generation
	loading.value = true
	inflight = Api.customers
		.getCustomers({})
		.then(res => {
			if (asked !== generation) return
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
			if (asked !== generation) return
			loading.value = false
			inflight = null
		})

	return inflight
}

/**
 * Forget the list (logout, `stores/auth.ts:setLogout`). `GET /customers` is scoped to the caller,
 * so the next user on a shared machine must never be offered the previous one's customers.
 */
export function resetCustomerOptions() {
	generation += 1
	options.value = []
	loading.value = false
	inflight = null
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

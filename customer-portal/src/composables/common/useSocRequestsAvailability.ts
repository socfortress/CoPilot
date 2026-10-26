import { readonly, ref } from "vue"
import Api from "@/api"

/**
 * Whether portal users may ask the SOC (#1305): for one customer (an alert's or a case's),
 * or for any customer the user may see.
 *
 * The switch changes only when an operator flips it in CoPilot, so the answer is cached
 * per customer code for the life of the page, as the in-flight promise so concurrent
 * callers share one request. `reset()` on logout: the next user may see other customers.
 */
const SELF = "__self__"
const cache = new Map<string, Promise<boolean>>()
const available = ref(false)

export function useSocRequestsAvailability() {
	function isEnabledFor(customerCode?: string): Promise<boolean> {
		const key = customerCode ?? SELF
		const cached = cache.get(key)
		if (cached) return cached

		const request = (async () => {
			try {
				const enabled = (await Api.socRequests.getAvailability(customerCode)).data.enabled === true
				if (key === SELF) available.value = enabled
				return enabled
			} catch {
				// A failed lookup must not pin the tab to "off" for the session: retry next time.
				cache.delete(key)
				return false
			}
		})()

		cache.set(key, request)
		return request
	}

	function reset() {
		cache.clear()
		available.value = false
	}

	return { available: readonly(available), isEnabledFor, reset }
}

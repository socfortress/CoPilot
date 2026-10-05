import { readonly, ref } from "vue"
import Api from "@/api"

/**
 * Whether the SLA page is on (#1187): for one customer, or for any customer the user
 * may see — which is what decides the menu entry.
 *
 * The switch changes only when an operator flips it in CoPilot, so the answer is cached
 * per customer code for the life of the page, as the in-flight promise so concurrent
 * callers share one request. `available` mirrors the "any customer" answer reactively,
 * for the menu. `reset()` on logout: the next user may see other customers.
 */
const SELF = "__self__"
const cache = new Map<string, Promise<boolean>>()
const available = ref(false)

export function useSlaAvailability() {
	function isEnabledFor(customerCode?: string): Promise<boolean> {
		const key = customerCode ?? SELF
		const cached = cache.get(key)
		if (cached) return cached

		const request = (async () => {
			try {
				const enabled = (await Api.sla.getAvailability(customerCode)).data.enabled === true
				if (key === SELF) available.value = enabled
				return enabled
			} catch {
				// A failed lookup must not pin the page to "off" for the session: retry next time.
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

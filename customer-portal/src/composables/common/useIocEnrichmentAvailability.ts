import { readonly, ref } from "vue"
import Api from "@/api"

/**
 * Whether portal users may check the IOCs of their alerts against Threat Intel (#1318): for one
 * customer (an alert's), or for any customer the user may see. On only when the customer's switch
 * is on and the SOC has a source to ask.
 *
 * The answer changes only when an operator acts in CoPilot, so it is cached per customer code for
 * the life of the page, as the in-flight promise so concurrent callers share one request.
 * `reset()` on logout: the next user may see other customers.
 */
const SELF = "__self__"
const cache = new Map<string, Promise<boolean>>()
const available = ref(false)

export function useIocEnrichmentAvailability() {
	function isEnabledFor(customerCode?: string): Promise<boolean> {
		const key = customerCode ?? SELF
		const cached = cache.get(key)
		if (cached) return cached

		const request = (async () => {
			try {
				const enabled = (await Api.iocEnrichment.getAvailability(customerCode)).data.enabled === true
				if (key === SELF) available.value = enabled
				return enabled
			} catch {
				// A failed lookup must not pin the checks to "off" for the session: retry next time.
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

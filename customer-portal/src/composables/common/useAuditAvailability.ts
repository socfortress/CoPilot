import type { PortalCustomer } from "@/types/auth"
import { readonly, ref } from "vue"
import Api from "@/api"

/**
 * Whether the caller gets the Audit Log page (#1298), and for which customers.
 *
 * Only a customer admin can, for the customers whose switch the SOC turned on; that changes
 * only when someone flips it in CoPilot, so the answer is cached for the life of the page, as
 * the in-flight promise so concurrent callers share one request. `available` and `customers`
 * mirror it reactively, for the menu and the page. `reset()` on logout: the next user is someone else.
 */
let cached: Promise<boolean> | null = null
const available = ref(false)
const customers = ref<PortalCustomer[]>([])

export function useAuditAvailability() {
	function check(): Promise<boolean> {
		if (cached) return cached
		const request = (async () => {
			try {
				const data = (await Api.audit.getAvailability()).data
				available.value = data.available === true
				customers.value = data.customers ?? []
				return available.value
			} catch {
				// A failed lookup must not pin the page to "off" for the session: retry next time.
				cached = null
				return false
			}
		})()
		cached = request
		return request
	}

	function reset() {
		cached = null
		available.value = false
		customers.value = []
	}

	return { available: readonly(available), customers: readonly(customers), check, reset }
}

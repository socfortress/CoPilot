import type { TalonChatAvailability } from "@/types/talonChat"
import { readonly, ref } from "vue"
import Api from "@/api"

/**
 * Whether "Ask Talon" is on (talon-analyst D97): for one customer, or for any customer the user
 * may see, which is what decides the menu entry. The same answer says whether the user may submit
 * a SOC draft (`can_draft`) and run an AI analysis (`can_request_analysis`) for that customer.
 *
 * The switch changes only when an admin flips it in CoPilot, so the answer is cached per customer
 * code for the life of the page, as the in-flight promise so concurrent callers share one request.
 * A failed lookup reads as off (hidden) and is not cached: the next caller asks again. CoPilot
 * and talon-analyst check the switch on every request anyway; this only decides what is shown.
 * `reset()` on logout: the next user may see other customers.
 */
const SELF = "__self__"
const cache = new Map<string, Promise<TalonChatAvailability | null>>()
const available = ref(false)

export function useTalonChatAvailability() {
	function availabilityFor(customerCode?: string): Promise<TalonChatAvailability | null> {
		const key = customerCode ?? SELF
		const cached = cache.get(key)
		if (cached) return cached

		const request = (async () => {
			try {
				const answer = (await Api.talonChat.getAvailability(customerCode)).data
				const enabled = answer?.enabled === true
				if (key === SELF) available.value = enabled
				if (!enabled) return null
				return {
					customer_code: answer.customer_code ?? customerCode ?? null,
					enabled,
					log_search: answer.log_search === true,
					can_draft: answer.can_draft === true,
					can_request_analysis: answer.can_request_analysis === true
				}
			} catch {
				// A failed lookup must not pin the page to "off" for the session: retry next time.
				cache.delete(key)
				return null
			}
		})()

		cache.set(key, request)
		return request
	}

	async function isEnabledFor(customerCode?: string): Promise<boolean> {
		return (await availabilityFor(customerCode)) !== null
	}

	function reset() {
		cache.clear()
		available.value = false
	}

	return { available: readonly(available), availabilityFor, isEnabledFor, reset }
}

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
 * `invalidate()` drops a customer's answer when a request says the switch is off now (`portal_off`).
 *
 * A failed lookup is its own state, `error` ("couldn't check"): hidden where only a yes or no is
 * needed (the menu, the alert's button), and never cached, so the next caller asks again. CoPilot
 * and talon-analyst check the switch on every request anyway; this only decides what is shown.
 *
 * `reset()` on logout: the next user may see other customers. It bumps a generation, so a lookup
 * still in flight from the session that ended can't set the menu for the next one.
 */
export type TalonChatAvailabilityState = "on" | "off" | "error"

export interface TalonChatAvailabilityLookup {
	state: TalonChatAvailabilityState
	availability: TalonChatAvailability | null
}

const SELF = "__self__"
const cache = new Map<string, Promise<TalonChatAvailabilityLookup>>()
const available = ref(false)
let generation = 0

const OFF: TalonChatAvailabilityLookup = { state: "off", availability: null }
const ERROR: TalonChatAvailabilityLookup = { state: "error", availability: null }

export function useTalonChatAvailability() {
	function lookup(customerCode?: string): Promise<TalonChatAvailabilityLookup> {
		const key = customerCode ?? SELF
		const cached = cache.get(key)
		if (cached) return cached

		const asked = generation
		// Held first: a failure removes this very request from the cache, never a newer one.
		const own: { request?: Promise<TalonChatAvailabilityLookup> } = {}
		const request = (async (): Promise<TalonChatAvailabilityLookup> => {
			try {
				const answer = (await Api.talonChat.getAvailability(customerCode)).data
				// The session that asked has ended: its answer is nobody's.
				if (asked !== generation) return OFF
				const enabled = answer?.enabled === true
				if (key === SELF) available.value = enabled
				if (!enabled) return OFF
				return {
					state: "on" as const,
					availability: {
						customer_code: answer.customer_code ?? customerCode ?? null,
						enabled,
						log_search: answer.log_search === true,
						can_draft: answer.can_draft === true,
						can_request_analysis: answer.can_request_analysis === true
					}
				}
			} catch {
				// A failed lookup must not pin the page to "off" for the session: ask again next time.
				if (cache.get(key) === own.request) cache.delete(key)
				return ERROR
			}
		})()
		own.request = request

		cache.set(key, request)
		return request
	}

	async function availabilityFor(customerCode?: string): Promise<TalonChatAvailability | null> {
		return (await lookup(customerCode)).availability
	}

	async function isEnabledFor(customerCode?: string): Promise<boolean> {
		return (await lookup(customerCode)).state === "on"
	}

	/** Forget a customer's answer, and the caller-wide one: a request found its switch off. */
	function invalidate(customerCode?: string) {
		if (customerCode) cache.delete(customerCode)
		cache.delete(SELF)
	}

	function reset() {
		generation += 1
		cache.clear()
		available.value = false
	}

	return { available: readonly(available), lookup, availabilityFor, isEnabledFor, invalidate, reset }
}

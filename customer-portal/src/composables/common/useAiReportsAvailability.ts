import Api from "@/api"

/**
 * Resolves the per-customer AI report switch so views can decide whether to
 * render the AI surfaces at all.
 *
 * The answer changes only when an operator flips the switch in CoPilot, so it is
 * cached per customer code for the lifetime of the page — a user paging through
 * alerts of the same customer asks the backend once. The cache stores the
 * in-flight promise, not the value, so N concurrent callers share one request.
 */
const cache = new Map<string, Promise<boolean>>()

function cacheKey(customerCode?: string) {
	return customerCode ?? "__self__"
}

export function useAiReportsAvailability() {
	function isEnabledFor(customerCode?: string): Promise<boolean> {
		const key = cacheKey(customerCode)
		const cached = cache.get(key)
		if (cached) return cached

		const request = Api.aiReports
			.getAvailability(customerCode)
			.then(res => res.data.enabled === true)
			// A failed lookup must not permanently pin the surface to "off":
			// drop it from the cache so the next view retries.
			.catch(() => {
				cache.delete(key)
				return false
			})

		cache.set(key, request)
		return request
	}

	/** Call after anything that could change the stored switch (e.g. re-login). */
	function reset() {
		cache.clear()
	}

	return { isEnabledFor, reset }
}

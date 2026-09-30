import { computed, ref } from "vue"
import Api from "@/api"

/**
 * Whether this deployment has a verified SOCFortress UBA connector.
 *
 * Same shape as useOpenCTIAvailability: module-level state so every caller shares one
 * request; a successful answer is kept for the session, a failed one is not. The UBA
 * page shows setup guidance instead of its views until this is true.
 */
const verified = ref(false)
const configured = ref(false)
const loaded = ref(false)
let inflight: Promise<void> | null = null

function fetchAvailability(): Promise<void> {
	if (inflight) return inflight

	inflight = Api.uba
		.getAvailability()
		.then(res => {
			verified.value = !!res.data.verified
			configured.value = !!res.data.configured
			loaded.value = true
		})
		.catch(() => {
			// Silent: UBA stays unavailable, which is also right when the backend predates the route.
			verified.value = false
		})
		.finally(() => {
			inflight = null
		})

	return inflight
}

export function useUbaAvailability() {
	if (!loaded.value) {
		fetchAvailability()
	}

	return {
		available: computed(() => verified.value),
		configured: computed(() => configured.value),
		loaded: computed(() => loaded.value),
		refresh: fetchAvailability
	}
}

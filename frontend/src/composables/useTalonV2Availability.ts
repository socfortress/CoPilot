import { computed, ref } from "vue"
import Api from "@/api"

/**
 * Whether the "Talon v2" chat setting is on (`GET /talon/v2/availability`, talon-analyst M5-5).
 *
 * The AI Analyst page shows the v2 chat (threads, the customer picker) only when this is true and
 * the v1 chat otherwise, unchanged. Same shape as `useOpenCTIAvailability`: module-level state so
 * every caller shares one request, a successful answer kept for the session, a failed one not
 * (the v1 chat shows, and the next caller asks again). `settled` says the question was answered
 * either way, so the page doesn't flash one chat before the other. Cleared on logout
 * (`stores/auth.ts:setLogout`): the next user on a shared machine asks again.
 */
const enabled = ref(false)
const loaded = ref(false)
const failed = ref(false)
let inflight: Promise<void> | null = null

function fetchAvailability(): Promise<void> {
	if (inflight) return inflight

	failed.value = false
	inflight = Api.talonV2
		.getAvailability()
		.then(res => {
			enabled.value = res.data?.enabled === true
			loaded.value = true
		})
		.catch(() => {
			// Silent: the v1 chat stays, which is also right when the backend predates the route.
			enabled.value = false
			failed.value = true
		})
		.finally(() => {
			inflight = null
		})

	return inflight
}

/** Forget the answer (logout, or a test). */
export function resetTalonV2Availability() {
	enabled.value = false
	loaded.value = false
	failed.value = false
	inflight = null
}

export function useTalonV2Availability() {
	if (!loaded.value && !inflight) {
		fetchAvailability()
	}

	return {
		available: computed(() => enabled.value),
		loaded: computed(() => loaded.value),
		settled: computed(() => loaded.value || failed.value),
		refresh: fetchAvailability
	}
}

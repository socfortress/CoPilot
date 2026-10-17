import { computed, ref } from "vue"
import Api from "@/api"

/**
 * Whether the "Talon v2" chat setting is on (`GET /talon/v2/availability`, talon-analyst M5-5).
 *
 * The AI Analyst page shows the v2 chat (threads, the customer picker) only when this is true and
 * the v1 chat otherwise, unchanged. Same shape as `useOpenCTIAvailability`: module-level state so
 * every caller shares one request, a successful answer kept for the session, a failed one not
 * (the v1 chat shows, and the next caller asks again). An answer that takes longer than
 * `TALON_V2_AVAILABILITY_TIMEOUT_MS` counts as failed. `settled` says the question was answered
 * either way, so the page doesn't flash one chat before the other. Cleared on logout
 * (`stores/auth.ts:setLogout`): the next user on a shared machine asks again.
 */
const enabled = ref(false)
const loaded = ref(false)
const failed = ref(false)
let inflight: Promise<void> | null = null
// Bumped by a reset or a timeout: a late answer to an abandoned question changes nothing, so the
// page never swaps the v1 chat for the v2 one under the analyst's hands.
let generation = 0

/** How long the page waits for the answer before showing the v1 chat. */
export const TALON_V2_AVAILABILITY_TIMEOUT_MS = 5000

function fetchAvailability(): Promise<void> {
	if (inflight) return inflight

	const asked = ++generation
	const controller = new AbortController()
	failed.value = false

	const giveUp = () => {
		if (asked !== generation) return
		generation += 1
		controller.abort()
		enabled.value = false
		failed.value = true
		inflight = null
	}
	const timer = setTimeout(giveUp, TALON_V2_AVAILABILITY_TIMEOUT_MS)

	inflight = Api.talonV2
		.getAvailability(controller.signal)
		.then(res => {
			if (asked !== generation) return
			enabled.value = res.data?.enabled === true
			loaded.value = true
		})
		.catch(() => {
			// Silent: the v1 chat stays, which is also right when the backend predates the route.
			if (asked !== generation) return
			enabled.value = false
			failed.value = true
		})
		.finally(() => {
			clearTimeout(timer)
			if (asked === generation) inflight = null
		})

	return inflight
}

/** Forget the answer (logout, or a test). */
export function resetTalonV2Availability() {
	generation += 1
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

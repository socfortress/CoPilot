import { computed, ref } from "vue"
import Api from "@/api"

/**
 * Whether this deployment has a verified OpenCTI connector.
 *
 * Every OpenCTI surface (Threat Intel drawer section, alert IoC button, …) hides
 * itself unless this is true. Most deployments don't run OpenCTI, and a button
 * that only ever answers "No OpenCTI connector found" is noise.
 *
 * State is module-level on purpose: an alert page renders one IoC card per IoC,
 * and they all share a single request. A successful answer is kept for the
 * session; a failed one is not, so the next caller tries again. `refresh()`
 * exists for the Connectors page, where verifying OpenCTI should make it
 * appear without a reload.
 */
const verified = ref(false)
const platformUrl = ref<string | null>(null)
const loaded = ref(false)
let inflight: Promise<void> | null = null

function fetchAvailability(): Promise<void> {
	if (inflight) return inflight

	inflight = Api.opencti
		.getAvailability()
		.then(res => {
			verified.value = !!res.data.verified
			platformUrl.value = res.data.platform_url || null
			loaded.value = true
		})
		.catch(() => {
			// Silent. OpenCTI stays hidden, which is also the right answer when
			// the backend predates the availability route.
			verified.value = false
		})
		.finally(() => {
			inflight = null
		})

	return inflight
}

export function useOpenCTIAvailability() {
	if (!loaded.value) {
		fetchAvailability()
	}

	return {
		available: computed(() => verified.value),
		loaded: computed(() => loaded.value),
		refresh: fetchAvailability,
		/** Link to any OpenCTI object by internal or STIX id. Null when the platform URL is unknown. */
		objectUrl: (id: string) =>
			platformUrl.value ? `${platformUrl.value}/dashboard/id/${encodeURIComponent(id)}` : null
	}
}

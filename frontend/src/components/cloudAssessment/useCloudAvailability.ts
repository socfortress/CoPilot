import type { CloudAvailability } from "@/types/cloud-assessment"
import { ref } from "vue"
import Api from "@/api"

/** How long an answer is reused: it says whether copilot-prowler answers, which can change. */
const TTL_MS = 60_000

const availability = ref<CloudAvailability | null>(null)
let fetchedAt = 0
let pending: Promise<CloudAvailability | null> | null = null

/**
 * Whether cloud credentials can be stored and scans run, and copilot-prowler's versions: one
 * request per minute at most, shared by every component that asks. A failure is null (unknown),
 * never "off": the views then say nothing rather than something wrong.
 */
export function useCloudAvailability() {
	function load(force = false): Promise<CloudAvailability | null> {
		if (!force && availability.value && Date.now() - fetchedAt < TTL_MS) return Promise.resolve(availability.value)
		if (pending) return pending
		pending = Api.cloudAssessment
			.availability()
			.then(res => {
				availability.value = res.data
				fetchedAt = Date.now()
				return res.data
			})
			.catch(() => null)
			.finally(() => {
				pending = null
			})
		return pending
	}

	return { availability, load }
}

/** For the tests: forget what was fetched. */
export function resetCloudAvailability() {
	availability.value = null
	fetchedAt = 0
	pending = null
}

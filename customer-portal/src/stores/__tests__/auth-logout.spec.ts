import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useActivityAvailability } from "@/composables/common/useActivityAvailability"
import { useAiReportsAvailability } from "@/composables/common/useAiReportsAvailability"
import { useExposureAvailability } from "@/composables/common/useExposureAvailability"
import { useSlaAvailability } from "@/composables/common/useSlaAvailability"
import { useSocRequestsAvailability } from "@/composables/common/useSocRequestsAvailability"
import { useAuthStore } from "../auth"

const aiAvailability = vi.hoisted(() => vi.fn())
const slaAvailability = vi.hoisted(() => vi.fn())
const activityAvailability = vi.hoisted(() => vi.fn())
const exposureAvailability = vi.hoisted(() => vi.fn())
const socRequestsAvailability = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({
	default: {
		aiReports: { getAvailability: aiAvailability },
		sla: { getAvailability: slaAvailability },
		activity: { getAvailability: activityAvailability },
		exposure: { getAvailability: exposureAvailability },
		socRequests: { getAvailability: socRequestsAvailability }
	}
}))

function enabled() {
	return Promise.resolve({ data: { enabled: true, customer_code: null } })
}

/**
 * The per-customer switches are cached for the life of the page. A logout ends the
 * session that asked, and the next user may see other customers whose surfaces are
 * off — so on a shared machine they must not inherit the previous user's answers.
 */
describe("logout clears the cached portal switches", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		aiAvailability.mockReset().mockImplementation(enabled)
		slaAvailability.mockReset().mockImplementation(enabled)
		activityAvailability.mockReset().mockImplementation(enabled)
		exposureAvailability.mockReset().mockImplementation(enabled)
		socRequestsAvailability.mockReset().mockImplementation(enabled)
		useAiReportsAvailability().reset()
		useSlaAvailability().reset()
		useActivityAvailability().reset()
		useExposureAvailability().reset()
		useSocRequestsAvailability().reset()
	})

	it("asks the backend again after a logout", async () => {
		await useAiReportsAvailability().isEnabledFor("ACME")
		await useSlaAvailability().isEnabledFor()
		await useActivityAvailability().isEnabledFor()
		await useExposureAvailability().isEnabledFor()
		await useSocRequestsAvailability().isEnabledFor("ACME")
		expect(useSlaAvailability().available.value).toBe(true)
		expect(useActivityAvailability().available.value).toBe(true)
		expect(useExposureAvailability().available.value).toBe(true)

		useAuthStore().setLogout()

		expect(useSlaAvailability().available.value).toBe(false)
		expect(useActivityAvailability().available.value).toBe(false)
		expect(useExposureAvailability().available.value).toBe(false)
		await useAiReportsAvailability().isEnabledFor("ACME")
		await useSlaAvailability().isEnabledFor()
		await useExposureAvailability().isEnabledFor()
		expect(aiAvailability).toHaveBeenCalledTimes(2)
		expect(slaAvailability).toHaveBeenCalledTimes(2)
		await useActivityAvailability().isEnabledFor()
		expect(activityAvailability).toHaveBeenCalledTimes(2)
		expect(exposureAvailability).toHaveBeenCalledTimes(2)
		await useSocRequestsAvailability().isEnabledFor("ACME")
		expect(socRequestsAvailability).toHaveBeenCalledTimes(2)
	})
})

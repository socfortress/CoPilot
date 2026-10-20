import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { useActivityAvailability } from "@/composables/common/useActivityAvailability"
import { useAiReportsAvailability } from "@/composables/common/useAiReportsAvailability"
import { useSlaAvailability } from "@/composables/common/useSlaAvailability"
import { useAuthStore } from "../auth"

const aiAvailability = vi.hoisted(() => vi.fn())
const slaAvailability = vi.hoisted(() => vi.fn())
const activityAvailability = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({
	default: {
		aiReports: { getAvailability: aiAvailability },
		sla: { getAvailability: slaAvailability },
		activity: { getAvailability: activityAvailability }
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
		useAiReportsAvailability().reset()
		useSlaAvailability().reset()
		useActivityAvailability().reset()
	})

	it("asks the backend again after a logout", async () => {
		await useAiReportsAvailability().isEnabledFor("ACME")
		await useSlaAvailability().isEnabledFor()
		await useActivityAvailability().isEnabledFor()
		expect(useSlaAvailability().available.value).toBe(true)
		expect(useActivityAvailability().available.value).toBe(true)

		useAuthStore().setLogout()

		expect(useSlaAvailability().available.value).toBe(false)
		expect(useActivityAvailability().available.value).toBe(false)
		await useAiReportsAvailability().isEnabledFor("ACME")
		await useSlaAvailability().isEnabledFor()
		expect(aiAvailability).toHaveBeenCalledTimes(2)
		expect(slaAvailability).toHaveBeenCalledTimes(2)
		await useActivityAvailability().isEnabledFor()
		expect(activityAvailability).toHaveBeenCalledTimes(2)
	})
})

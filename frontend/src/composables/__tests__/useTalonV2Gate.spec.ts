/**
 * The gated "Talon v2" availability (M5-9b review): asked only when the surface shows a v2 view and
 * the role could use v2; a 403 is "off" for the session (never asked again), while a failure is
 * asked again by the next caller; logout forgets both.
 */
import { flushPromises } from "@vue/test-utils"
import { AxiosError, AxiosHeaders } from "axios"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { ref } from "vue"
import { resetTalonV2Availability, useTalonV2Availability } from "@/composables/useTalonV2Availability"
import { useTalonV2AvailabilityWhen } from "@/composables/useTalonV2Gate"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"

const getAvailability = vi.fn()

vi.mock("@/api", () => ({
	default: { talonV2: { getAvailability: (signal?: AbortSignal) => getAvailability(signal) } }
}))

function forbidden() {
	const headers = new AxiosHeaders()
	return new AxiosError("forbidden", "ERR_BAD_REQUEST", { headers }, null, {
		status: 403,
		statusText: "",
		data: { message: "Forbidden" },
		headers,
		config: { headers }
	})
}

function signInAs(role: AuthUserRole) {
	useAuthStore().user = { access_token: "t", username: "u", email: "", role }
}

describe("gated talon v2 availability", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetTalonV2Availability()
		getAvailability.mockReset()
	})

	it("asks only once the surface wants it, and only for a role v2 serves", async () => {
		signInAs(AuthUserRole.Analyst)
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true, run_view: true } })
		const shown = ref(false)
		const { available, runView } = useTalonV2AvailabilityWhen(shown)
		await flushPromises()
		expect(getAvailability).not.toHaveBeenCalled()
		expect(available.value).toBe(false)
		shown.value = true
		await flushPromises()
		expect(getAvailability).toHaveBeenCalledTimes(1)
		expect(available.value && runView.value).toBe(true)
	})

	it.each([AuthUserRole.Scheduler, AuthUserRole.CustomerUser, AuthUserRole.Unknown])(
		"never asks for %s",
		async role => {
			signInAs(role)
			getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
			const { available } = useTalonV2AvailabilityWhen(true)
			await flushPromises()
			expect(getAvailability).not.toHaveBeenCalled()
			expect(available.value).toBe(false)
		}
	)

	it("a 403 is off for the session: never asked again, until logout", async () => {
		signInAs(AuthUserRole.Analyst)
		getAvailability.mockRejectedValue(forbidden())
		const first = useTalonV2Availability()
		await flushPromises()
		expect(first.available.value).toBe(false)
		expect(first.settled.value).toBe(true)
		useTalonV2Availability()
		useTalonV2AvailabilityWhen(true)
		await flushPromises()
		expect(getAvailability).toHaveBeenCalledTimes(1)

		resetTalonV2Availability()
		getAvailability.mockResolvedValue({ data: { success: true, enabled: true } })
		const next = useTalonV2Availability()
		await flushPromises()
		expect(getAvailability).toHaveBeenCalledTimes(2)
		expect(next.available.value).toBe(true)
	})

	it("any other failure is asked again by the next caller", async () => {
		signInAs(AuthUserRole.Analyst)
		getAvailability.mockRejectedValueOnce(new Error("network")).mockResolvedValue({ data: { enabled: true } })
		useTalonV2Availability()
		await flushPromises()
		const again = useTalonV2Availability()
		await flushPromises()
		expect(getAvailability).toHaveBeenCalledTimes(2)
		expect(again.available.value).toBe(true)
	})
})

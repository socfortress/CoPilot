/** The global automation switch (talon-analyst D85, plan AP-2): read, then saved as switched. */
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import TalonAutomationSettings from "../TalonAutomationSettings.vue"

const getSettings = vi.fn()
const putSettings = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonAutomation: {
			getSettings: (...a: unknown[]) => getSettings(...a),
			putSettings: (...a: unknown[]) => putSettings(...a)
		}
	}
}))

function render() {
	return mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(TalonAutomationSettings)) }))
}

enableAutoUnmount(afterEach)

describe("talon automation global switch", () => {
	beforeEach(() => {
		getSettings.mockReset().mockResolvedValue({ data: { success: true, message: "", automation_enabled: false } })
		putSettings
			.mockReset()
			.mockImplementation((on: boolean) =>
				Promise.resolve({ data: { success: true, message: "", automation_enabled: on } })
			)
	})

	it("shows the stored state and saves the switch", async () => {
		const wrapper = render()
		await flushPromises()
		expect(getSettings).toHaveBeenCalledWith(expect.any(AbortSignal))
		expect(wrapper.get('[data-testid="talon-automation-settings-state"]').text()).toContain("Off")
		await wrapper.get('[data-testid="talon-automation-switch"]').trigger("click")
		await flushPromises()
		expect(putSettings).toHaveBeenCalledWith(true)
		expect(wrapper.get('[data-testid="talon-automation-settings-state"]').text()).toContain("may run")
	})

	it("shows CoPilot's refusal", async () => {
		getSettings.mockRejectedValue(
			Object.assign(new Error("x"), {
				isAxiosError: true,
				response: { status: 403, data: { detail: "Admins only" } }
			})
		)
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-automation-settings-error"]').text()).toBe("Admins only")
	})
})

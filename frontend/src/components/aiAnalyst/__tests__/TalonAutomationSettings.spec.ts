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

/** `TalonAutomationSwitchResponse` as CoPilot answers it. */
function switchAnswer(on: boolean) {
	return {
		success: true,
		message: "",
		connector_name: "Talon",
		automation_enabled: on,
		updated_by_user_id: null,
		updated_at: null
	}
}

function render() {
	return mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(TalonAutomationSettings)) }))
}

enableAutoUnmount(afterEach)

describe("talon automation global switch", () => {
	beforeEach(() => {
		getSettings.mockReset().mockResolvedValue({ data: switchAnswer(false) })
		putSettings.mockReset().mockImplementation((on: boolean) => Promise.resolve({ data: switchAnswer(on) }))
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
				response: { status: 403, data: { success: false, message: "Admins only" } }
			})
		)
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-automation-settings-error"]').text()).toBe("Admins only")
	})
})

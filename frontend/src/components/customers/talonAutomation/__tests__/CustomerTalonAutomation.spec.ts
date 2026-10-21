/**
 * The customer's AI Automation tab (talon-analyst D85, plan AP-2 frontend): every level's four
 * modes render and save as chosen, any mode directly (Q2); raising level 3 or 4 needs the
 * honest-risk acknowledgement and then sends `acknowledge_risk: true` (Q7); caps are only lowered.
 */
import type { TalonAutomationPolicy } from "@/api/endpoints/talonAutomation"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import CustomerTalonAutomation from "../CustomerTalonAutomation.vue"

const getPolicy = vi.fn()
const putPolicy = vi.fn()

vi.mock("@/api", () => ({
	default: {
		talonAutomation: {
			getPolicy: (...a: unknown[]) => getPolicy(...a),
			putPolicy: (...a: unknown[]) => putPolicy(...a)
		}
	}
}))

const ModalStub = defineComponent({
	name: "Modal",
	props: { show: { type: Boolean, default: false } },
	setup:
		(props, { slots }) =>
		() =>
			props.show ? h("div", { "data-testid": "modal-stub" }, slots.default?.()) : null
})

function policy(over: Partial<TalonAutomationPolicy> = {}): TalonAutomationPolicy {
	return {
		customer_code: "ACME",
		exists: true,
		level_1_mode: "auto",
		level_2_mode: "off",
		level_3_mode: "off",
		level_4_mode: "off",
		level_2_artifacts: ["Windows.System.Pslist"],
		file_allow_globs: { windows: ["C:\\Users\\*\\Downloads\\*"] },
		caps: {
			per_alert_level_1: { default: 2, override: null, effective: 2 },
			per_customer_commands_day: { default: 20, override: 10, effective: 10 }
		},
		risk_acknowledged_by: null,
		risk_acknowledged_at: null,
		updated_by: "admin",
		updated_at: "2026-10-20T10:00:00Z",
		version: 3,
		...over
	}
}

function render() {
	return mount(
		defineComponent({
			setup: () => () => h(NMessageProvider, null, () => h(CustomerTalonAutomation, { customerCode: "ACME" }))
		}),
		{ global: { stubs: { NModal: ModalStub, Modal: ModalStub } } }
	)
}

type Wrapper = ReturnType<typeof render>

async function choose(wrapper: Wrapper, level: number, mode: string) {
	await wrapper.get(`[data-testid="automation-level-${level}-${mode}"] input`).setValue(true)
	await nextTick()
}

function checked(wrapper: Wrapper, level: number) {
	return ["off", "shadow", "propose", "auto"].filter(
		mode =>
			(wrapper.get(`[data-testid="automation-level-${level}-${mode}"] input`).element as HTMLInputElement).checked
	)
}

function lastBody() {
	return putPolicy.mock.calls.at(-1)?.[1]
}

enableAutoUnmount(afterEach)

describe("customer AI Automation tab", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		getPolicy.mockReset().mockResolvedValue({ data: { success: true, message: "", policy: policy() } })
		putPolicy
			.mockReset()
			.mockImplementation((_code: string, body: Record<string, unknown>) =>
				Promise.resolve({ data: { success: true, message: "", policy: policy({ ...body, version: 4 }) } })
			)
	})

	it("renders four modes for each of levels 1-4, with the stored mode chosen and shadow suggested", async () => {
		const wrapper = render()
		await flushPromises()
		expect(getPolicy).toHaveBeenCalledWith("ACME", expect.any(AbortSignal))
		for (const level of [1, 2, 3, 4]) {
			for (const mode of ["off", "shadow", "propose", "auto"]) {
				expect(wrapper.find(`[data-testid="automation-level-${level}-${mode}"]`).exists()).toBe(true)
			}
		}
		expect(checked(wrapper, 1)).toEqual(["auto"])
		expect(checked(wrapper, 3)).toEqual(["off"])
		expect(wrapper.get('[data-testid="automation-help"]').text()).toMatch(/suggest\s+shadow\s+first/)
		expect(wrapper.get('[data-testid="automation-caps"]').text()).toContain("Commands")
		expect(wrapper.find('[data-testid="automation-would-have-run"]').exists()).toBe(true)
	})

	it("saves any mode chosen directly at levels 1-2, without a risk confirm", async () => {
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="automation-save"]').attributes("disabled")).toBeDefined()
		await choose(wrapper, 1, "shadow")
		await choose(wrapper, 2, "auto") // straight from off to auto: no shadow gate
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		expect(wrapper.find('[data-testid="automation-risk-dialog"]').exists()).toBe(false)
		expect(putPolicy).toHaveBeenCalledTimes(1)
		expect(putPolicy).toHaveBeenCalledWith("ACME", {
			level_1_mode: "shadow",
			level_2_mode: "auto",
			level_3_mode: "off",
			level_4_mode: "off",
			level_2_artifacts: ["Windows.System.Pslist"],
			file_allow_globs: { windows: ["C:\\Users\\*\\Downloads\\*"] },
			cap_overrides: { per_alert_level_1: null, per_customer_commands_day: 10 },
			acknowledge_risk: false,
			version: 3
		})
		expect(checked(wrapper, 2)).toEqual(["auto"])
	})

	it("sends a lowered cap override", async () => {
		const wrapper = render()
		await flushPromises()
		const input = wrapper.get('[data-testid="automation-cap-per_alert_level_1-override"] input')
		await input.setValue("1")
		await input.trigger("blur")
		await nextTick()
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		expect(lastBody().cap_overrides).toEqual({ per_alert_level_1: 1, per_customer_commands_day: 10 })
	})

	for (const level of [3, 4]) {
		it(`raising level ${level} needs the acknowledgement, then sends acknowledge_risk: true`, async () => {
			const wrapper = render()
			await flushPromises()
			await choose(wrapper, level, "shadow")
			await wrapper.get('[data-testid="automation-save"]').trigger("click")
			await flushPromises()

			// Nothing is sent before the box is ticked; the honest risk is shown.
			expect(putPolicy).not.toHaveBeenCalled()
			const dialog = wrapper.get('[data-testid="automation-risk-dialog"]')
			expect(dialog.get('[data-testid="automation-risk-text"]').text()).toContain(
				"anyone who can write text into this customer's logs can try to steer a command onto that host"
			)
			const confirm = wrapper.get('[data-testid="automation-risk-confirm"]')
			expect(confirm.attributes("disabled")).toBeDefined()
			await confirm.trigger("click")
			await flushPromises()
			expect(putPolicy).not.toHaveBeenCalled()

			await wrapper.get('[data-testid="automation-risk-ack"]').trigger("click")
			await nextTick()
			expect(wrapper.get('[data-testid="automation-risk-confirm"]').attributes("disabled")).toBeUndefined()
			await wrapper.get('[data-testid="automation-risk-confirm"]').trigger("click")
			await flushPromises()
			expect(putPolicy).toHaveBeenCalledTimes(1)
			expect(lastBody()).toMatchObject({ [`level_${level}_mode`]: "shadow", acknowledge_risk: true })
			expect(wrapper.find('[data-testid="automation-risk-dialog"]').exists()).toBe(false)
		})
	}

	it("cancelling the risk confirm sends nothing and keeps the edit", async () => {
		const wrapper = render()
		await flushPromises()
		await choose(wrapper, 4, "auto")
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		await wrapper.get('[data-testid="automation-risk-cancel"]').trigger("click")
		await flushPromises()
		expect(putPolicy).not.toHaveBeenCalled()
		expect(wrapper.find('[data-testid="automation-risk-dialog"]').exists()).toBe(false)
		expect(checked(wrapper, 4)).toEqual(["auto"])
	})

	it("raising level 3 again (shadow to auto) asks again; lowering it does not", async () => {
		getPolicy.mockResolvedValue({
			data: { success: true, message: "", policy: policy({ level_3_mode: "shadow" }) }
		})
		const wrapper = render()
		await flushPromises()
		await choose(wrapper, 3, "auto")
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		expect(wrapper.find('[data-testid="automation-risk-dialog"]').exists()).toBe(true)
		await wrapper.get('[data-testid="automation-risk-cancel"]').trigger("click")
		await flushPromises()

		await choose(wrapper, 3, "off")
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		expect(wrapper.find('[data-testid="automation-risk-dialog"]').exists()).toBe(false)
		expect(lastBody()).toMatchObject({ level_3_mode: "off", acknowledge_risk: false })
	})

	it("shows CoPilot's refusal text", async () => {
		putPolicy.mockRejectedValue(
			Object.assign(new Error("refused"), {
				isAxiosError: true,
				response: { status: 403, data: { detail: "Talon service user isn't assigned to this customer" } }
			})
		)
		const wrapper = render()
		await flushPromises()
		await choose(wrapper, 1, "off")
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		expect(wrapper.get('[data-testid="automation-error"]').text()).toBe(
			"Talon service user isn't assigned to this customer"
		)
	})
})

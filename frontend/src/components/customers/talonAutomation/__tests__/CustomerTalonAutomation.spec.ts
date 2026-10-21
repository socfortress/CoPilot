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

const RISK_TEXT =
	"At levels 3 and 4 an automatic investigation runs commands on the alert's host without a person approving each one. Anyone who can write text into this customer's logs can try to steer such a command onto that host."

/** `TalonAutomationPolicyResponse` as CoPilot's AP-2 answers it (cap names from its `CAP_DEFAULTS`). */
function policy(over: Partial<TalonAutomationPolicy> = {}): TalonAutomationPolicy {
	return {
		success: true,
		message: "Talon automation policy retrieved",
		customer_code: "ACME",
		exists: true,
		automation_enabled: true,
		level_1_mode: "auto",
		level_2_mode: "off",
		level_3_mode: "off",
		level_4_mode: "off",
		level_2_artifacts: ["Windows.System.Pslist"],
		file_allow_globs: { windows: ["C:\\Users\\*\\Downloads\\*"] },
		caps: { commands_per_customer_day: 10 },
		effective_caps: { per_alert: 2, per_host_hour: 6, commands_per_customer_day: 10 },
		cap_defaults: { per_alert: 2, per_host_hour: 6, commands_per_customer_day: 20 },
		enforced_caps: ["per_alert", "per_host_hour"],
		startable_levels: [1],
		service_user_assigned: true,
		risk_acknowledgement_text: RISK_TEXT,
		risk_acknowledged_by_user_id: null,
		risk_acknowledged_by_username: null,
		risk_acknowledged_at: null,
		shadow_reviewed: null,
		version: 3,
		updated_by_user_id: 1,
		updated_by_username: "admin",
		updated_at: "2026-10-20T10:00:00Z",
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
		getPolicy.mockReset().mockResolvedValue({ data: policy() })
		putPolicy
			.mockReset()
			.mockImplementation((_code: string, body: Record<string, unknown>) =>
				Promise.resolve({ data: policy({ ...(body as Partial<TalonAutomationPolicy>), version: 4 }) })
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
		expect(wrapper.find('[data-testid="automation-would-have-run"]').exists()).toBe(true)
		// Propose isn't built yet (AP-5): tagged at every level.
		for (const level of [1, 2, 3, 4]) {
			expect(wrapper.get(`[data-testid="automation-level-${level}-propose-unavailable"]`).text()).toBe(
				"Not available yet"
			)
		}
		// Only level 1 is startable today; 2-4 are marked, and still settable.
		expect(wrapper.find('[data-testid="automation-level-1-unavailable"]').exists()).toBe(false)
		for (const level of [2, 3, 4]) {
			expect(wrapper.find(`[data-testid="automation-level-${level}-unavailable"]`).text()).toBe(
				"Not available yet"
			)
		}
	})

	it("lists the caps by CoPilot's names, with defaults, overrides and what is enforced", async () => {
		const wrapper = render()
		await flushPromises()
		const rows = wrapper.findAll('[data-testid^="automation-cap-"][data-testid$="-override"]')
		expect(rows).toHaveLength(3)
		const commands = wrapper.get('[data-testid="automation-cap-commands_per_customer_day"]')
		expect(commands.text()).toContain("20")
		expect(commands.text()).toContain("10")
		expect(commands.text()).not.toContain("Enforced")
		expect(wrapper.get('[data-testid="automation-cap-per_alert"]').text()).toContain("Enforced")
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
			caps: { commands_per_customer_day: 10 },
			acknowledge_risk: false,
			expected_version: 3
		})
		expect(checked(wrapper, 2)).toEqual(["auto"])
	})

	it("sends a lowered cap override, and null caps for a customer with none", async () => {
		getPolicy.mockResolvedValue({
			data: policy({ exists: false, version: 0, caps: null, level_2_artifacts: null, file_allow_globs: null })
		})
		const wrapper = render()
		await flushPromises()
		await choose(wrapper, 1, "shadow")
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		expect(lastBody()).toMatchObject({
			caps: null,
			level_2_artifacts: null,
			file_allow_globs: null,
			expected_version: 0
		})

		const input = wrapper.get('[data-testid="automation-cap-per_alert-override"] input')
		await input.setValue("1")
		await input.trigger("blur")
		await nextTick()
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		expect(lastBody().caps).toEqual({ per_alert: 1 })
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
			expect(dialog.get('[data-testid="automation-risk-text"]').text()).toBe(RISK_TEXT) // CoPilot's own text
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
		getPolicy.mockResolvedValue({ data: policy({ level_3_mode: "shadow" }) })
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

	for (const [status, text] of [
		[409, "The automation policy changed since it was read; read it again and review the change"],
		[409, "No level can be raised: the Talon service user isn't assigned to this customer"],
		[400, "Raising level 3 or 4 needs acknowledge_risk: true (the admin acknowledges the risk text)"]
	] as const) {
		it(`shows CoPilot's ${status} refusal and keeps the edit: ${text}`, async () => {
			putPolicy.mockRejectedValue(
				Object.assign(new Error("refused"), {
					isAxiosError: true,
					response: { status, data: { success: false, message: text } }
				})
			)
			const wrapper = render()
			await flushPromises()
			await choose(wrapper, 2, "shadow")
			await wrapper.get('[data-testid="automation-save"]').trigger("click")
			await flushPromises()
			expect(wrapper.get('[data-testid="automation-error"]').text()).toBe(text)
			expect(checked(wrapper, 2)).toEqual(["shadow"])
		})
	}

	it("warns when the switch is off or the service user isn't assigned", async () => {
		getPolicy.mockResolvedValue({ data: policy({ automation_enabled: false, service_user_assigned: false }) })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-testid="automation-switch-off"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="automation-unassigned"]').exists()).toBe(true)
	})

	it("moving level 3 from off to propose asks for the acknowledgement", async () => {
		const wrapper = render()
		await flushPromises()
		await choose(wrapper, 3, "propose")
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		expect(wrapper.find('[data-testid="automation-risk-dialog"]').exists()).toBe(true)
		expect(putPolicy).not.toHaveBeenCalled()
	})

	it("after a tick, a cancel and a reopen, the box is unticked again", async () => {
		const wrapper = render()
		await flushPromises()
		await choose(wrapper, 4, "shadow")
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		await wrapper.get('[data-testid="automation-risk-ack"]').trigger("click")
		await nextTick()
		expect(wrapper.get('[data-testid="automation-risk-ack"]').classes()).toContain("n-checkbox--checked")
		expect(wrapper.get('[data-testid="automation-risk-confirm"]').attributes("disabled")).toBeUndefined()
		await wrapper.get('[data-testid="automation-risk-cancel"]').trigger("click")
		await flushPromises()

		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		expect(wrapper.get('[data-testid="automation-risk-ack"]').classes()).not.toContain("n-checkbox--checked")
		expect(wrapper.get('[data-testid="automation-risk-confirm"]').attributes("disabled")).toBeDefined()
		await wrapper.get('[data-testid="automation-risk-confirm"]').trigger("click")
		await flushPromises()
		expect(putPolicy).not.toHaveBeenCalled()
	})

	it("can't confirm the risk when CoPilot sent no risk text", async () => {
		getPolicy.mockResolvedValue({ data: policy({ risk_acknowledgement_text: "  " }) })
		const wrapper = render()
		await flushPromises()
		await choose(wrapper, 3, "shadow")
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		expect(wrapper.find('[data-testid="automation-risk-text-missing"]').exists()).toBe(true)
		await wrapper.get('[data-testid="automation-risk-ack"]').trigger("click")
		await nextTick()
		expect(wrapper.get('[data-testid="automation-risk-confirm"]').attributes("disabled")).toBeDefined()
		await wrapper.get('[data-testid="automation-risk-confirm"]').trigger("click")
		await flushPromises()
		expect(putPolicy).not.toHaveBeenCalled()
	})

	it("on a stale-version 409, reads the policy again and keeps the edit for review", async () => {
		putPolicy.mockRejectedValueOnce(
			Object.assign(new Error("refused"), {
				isAxiosError: true,
				response: {
					status: 409,
					data: {
						success: false,
						message: "The automation policy changed since it was read; read it again and review the change"
					}
				}
			})
		)
		const wrapper = render()
		await flushPromises()
		getPolicy.mockResolvedValue({ data: policy({ level_1_mode: "shadow", version: 5 }) })
		await choose(wrapper, 2, "shadow")
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()

		expect(getPolicy).toHaveBeenCalledTimes(2)
		expect(wrapper.get('[data-testid="automation-reread"]').text()).toContain("version 5")
		// The admin's edit is kept (level 1 as they left it, level 2 as they set it), against version 5.
		expect(checked(wrapper, 1)).toEqual(["auto"])
		expect(checked(wrapper, 2)).toEqual(["shadow"])
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		expect(lastBody()).toMatchObject({ level_1_mode: "auto", level_2_mode: "shadow", expected_version: 5 })
	})

	it("an unassigned-customer 409 doesn't read the policy again", async () => {
		putPolicy.mockRejectedValue(
			Object.assign(new Error("refused"), {
				isAxiosError: true,
				response: {
					status: 409,
					data: {
						success: false,
						message: "No level can be raised: the Talon service user isn't assigned to this customer"
					}
				}
			})
		)
		const wrapper = render()
		await flushPromises()
		await choose(wrapper, 2, "shadow")
		await wrapper.get('[data-testid="automation-save"]').trigger("click")
		await flushPromises()
		expect(getPolicy).toHaveBeenCalledTimes(1)
		expect(wrapper.find('[data-testid="automation-reread"]').exists()).toBe(false)
	})

	it("reload reads the policy again and drops the edit", async () => {
		const wrapper = render()
		await flushPromises()
		await choose(wrapper, 2, "auto")
		await wrapper.get('[data-testid="automation-reload"]').trigger("click")
		await flushPromises()
		expect(getPolicy).toHaveBeenCalledTimes(2)
		expect(checked(wrapper, 2)).toEqual(["off"])
	})
})

/**
 * The business profile's form (plan K1-8): the time there, and the customer's own SLA calendar offered
 * for copying. The rules and the body are in `knowledge.spec.ts`.
 */
import type { BusinessCalendar } from "@/types/soc-management"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import CustomerKnowledgeForm from "../CustomerKnowledgeForm.vue"

const getCalendar = vi.fn()
const create = vi.fn()

vi.mock("@/api", () => ({
	default: {
		socManagement: { getCalendar: (...a: unknown[]) => getCalendar(...a) },
		customerKnowledge: { create: (...a: unknown[]) => create(...a), update: vi.fn() }
	}
}))

const ROME: BusinessCalendar = {
	customer_code: "ACME",
	source: "customer",
	timezone: "Europe/Rome",
	week: {
		mon: [["09:00", "17:00"]],
		tue: [],
		wed: [],
		thu: [],
		fri: [["09:00", "13:00"]],
		sat: [],
		sun: []
	},
	holidays: ["2026-12-25"]
}

async function render(kind: "business_profile" | "network_zone" = "business_profile") {
	const Host = defineComponent({
		setup: () => () =>
			h(NMessageProvider, null, {
				default: () => h(CustomerKnowledgeForm, { customerCode: "ACME", kind, editingFact: null })
			})
	})
	const wrapper = mount(Host, { global: { stubs: { Icon: true } } })
	await flushPromises()
	return wrapper
}

enableAutoUnmount(afterEach)

beforeEach(() => {
	getCalendar.mockReset().mockResolvedValue({ data: { success: true, calendar: ROME } })
	create.mockReset()
})

describe("the business profile's form", () => {
	it("asks for the customer's own SLA calendar, and only on this kind", async () => {
		await render()
		expect(getCalendar).toHaveBeenCalledWith("ACME")
		getCalendar.mockClear()
		await render("network_zone")
		expect(getCalendar).not.toHaveBeenCalled()
	})

	it("copies the customer's SLA calendar: its zone and its week", async () => {
		const wrapper = await render()
		const copy = wrapper.get('[data-testid="knowledge-copy-sla"]')
		await copy.trigger("click")
		await flushPromises()
		const form = wrapper.getComponent(CustomerKnowledgeForm)
		const state = (form.vm.$ as unknown as { setupState: { form: Record<string, unknown> } }).setupState.form
		expect(state.timeZone).toBe("Europe/Rome")
		expect((state.week as Record<string, unknown>).mon).toEqual([["09:00", "17:00"]])
		expect((state.week as Record<string, unknown>).tue).toEqual([])
		expect(wrapper.get('[data-testid="knowledge-now-there"]').text()).toMatch(/^It's \w+day \d\d:\d\d there now\.$/)
	})

	it.each([
		[
			"the deployment's default",
			() => Promise.resolve({ data: { success: true, calendar: { ...ROME, source: "global" } } })
		],
		["no answer", () => Promise.reject(new Error("down"))]
	])("doesn't offer %s", async (_name, answer) => {
		getCalendar.mockImplementation(answer)
		const wrapper = await render()
		expect(wrapper.find('[data-testid="knowledge-copy-sla"]').exists()).toBe(false)
		expect(wrapper.get('[data-testid="knowledge-now-there"]').text()).toContain("Pick the zone")
	})
})

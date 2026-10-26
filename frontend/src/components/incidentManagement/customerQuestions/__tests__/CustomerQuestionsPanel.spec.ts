import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
import CustomerQuestionsPanel from "../CustomerQuestionsPanel.vue"
import { question } from "./fixtures"

const socRequests = vi.hoisted(() => ({ list: vi.fn(), markAnswered: vi.fn() }))
vi.mock("@/api", () => ({ default: { socRequests } }))

function render(props: Record<string, unknown>) {
	return mount(
		defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(CustomerQuestionsPanel, props as never)) })
	)
}

beforeEach(() => {
	setActivePinia(createPinia())
	socRequests.list.mockReset()
	socRequests.markAnswered.mockReset()
})

/** The customer's questions on a case or alert overview (#1305). */
describe("the customer questions panel", () => {
	it("shows the open questions of this case, and counts the answered ones", async () => {
		socRequests.list.mockResolvedValue({
			data: {
				requests: [
					question(1, { case_id: 4, urgency: "high", question: "Line one\nline two" }),
					question(2, { case_id: 4, status: "answered" }),
					// Asked from an alert of the case but filed on another case: not this one's.
					question(3, { case_id: 8, origin_alert_id: 4 })
				]
			}
		})
		const wrapper = render({ entity: "case", entityId: 4 })
		await flushPromises()
		expect(socRequests.list).toHaveBeenCalledWith({ caseId: 4 })
		const rows = wrapper.findAll("[data-testid=customer-question]")
		expect(rows).toHaveLength(1)
		expect(rows[0]?.get("[data-testid=customer-question-urgency]").text()).toBe("High")
		expect(rows[0]?.get("[data-testid=customer-question-text]").text()).toBe("Line one\nline two")
		expect(wrapper.get("[data-testid=customer-questions-answered]").text()).toBe("1 earlier question answered")
	})

	it("marks one answered", async () => {
		socRequests.list.mockResolvedValue({ data: { requests: [question(1, { alert_id: 9 })] } })
		socRequests.markAnswered.mockResolvedValue({
			data: { request: question(1, { alert_id: 9, status: "answered", answered_via: "manual" }) }
		})
		const wrapper = render({ entity: "alert", entityId: 9 })
		await flushPromises()
		expect(socRequests.list).toHaveBeenCalledWith({ alertId: 9 })
		await wrapper.get("[data-testid=customer-question-answered]").trigger("click")
		await flushPromises()
		expect(socRequests.markAnswered).toHaveBeenCalledWith(1)
		expect(wrapper.find("[data-testid=customer-question]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=customer-questions-answered]").text()).toBe("1 earlier question answered")
	})

	it("shows nothing without questions, or when they can't be read", async () => {
		socRequests.list.mockResolvedValueOnce({ data: { requests: [] } })
		expect(render({ entity: "case", entityId: 4 }).find("[data-testid=customer-questions-panel]").exists()).toBe(false)
		socRequests.list.mockRejectedValueOnce(new Error("403"))
		const failed = render({ entity: "case", entityId: 4 })
		await flushPromises()
		expect(failed.find("[data-testid=customer-questions-panel]").exists()).toBe(false)
	})

	it("reads again when the case changes (a comment may have answered it)", async () => {
		socRequests.list.mockResolvedValue({ data: { requests: [] } })
		const refreshKey = ref("a")
		mount(
			defineComponent({
				setup: () => () =>
					h(NMessageProvider, null, () =>
						h(CustomerQuestionsPanel, { entity: "case", entityId: 4, refreshKey: refreshKey.value }))
			})
		)
		await flushPromises()
		refreshKey.value = "b"
		await flushPromises()
		expect(socRequests.list).toHaveBeenCalledTimes(2)
	})
})

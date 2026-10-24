import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import AskSoc from "../AskSoc.vue"
import { request } from "./fixtures"

const socRequests = vi.hoisted(() => ({
	listForAlert: vi.fn(),
	listForCase: vi.fn(),
	askOnAlert: vi.fn(),
	askOnCase: vi.fn()
}))
vi.mock("@/api", () => ({ default: { socRequests } }))

function render(entity: "alert" | "case", entityId: number) {
	const asked = vi.fn()
	const wrapper = mount(
		defineComponent({
			setup: () => () => h(NMessageProvider, null, () => h(AskSoc, { entity, entityId, onAsked: asked }))
		})
	)
	return { wrapper, asked }
}

async function type(wrapper: ReturnType<typeof render>["wrapper"], text: string) {
	await wrapper.get("[data-testid=ask-soc-question] textarea").setValue(text)
}

async function choose(wrapper: ReturnType<typeof render>["wrapper"], group: string, value: string) {
	const input = wrapper.findAll(`[data-testid=${group}] input`).find(i => i.element.getAttribute("value") === value)
	await input?.setValue(true)
}

beforeEach(() => {
	setActivePinia(createPinia())
	for (const fn of Object.values(socRequests)) fn.mockReset()
})

/** "Ask the SOC" on an alert or a case of the portal (#1305). */
describe("asking the SOC about an alert", () => {
	it("lists the questions already asked, with whether the SOC answered", async () => {
		socRequests.listForAlert.mockResolvedValue({
			data: {
				requests: [
					request(2, { case_id: 4, origin_alert_id: 9, urgency: "high", question: "Line one\nline two" }),
					request(1, { alert_id: 9, status: "answered", answered_at: "2026-10-24T08:00:00Z" })
				],
				open_case_id: 4
			}
		})
		const { wrapper } = render("alert", 9)
		await flushPromises()
		expect(socRequests.listForAlert).toHaveBeenCalledWith(9, expect.any(AbortSignal))
		const rows = wrapper.findAll("[data-testid=ask-soc-request]")
		expect(rows.map(r => r.get("[data-testid=ask-soc-request-status]").text())).toEqual([
			"Waiting for the SOC",
			"Answered"
		])
		expect(rows[0]?.text()).toContain("Urgency: High")
		expect(rows[0]?.get("[data-testid=ask-soc-request-filed]").text()).toContain("On case #4")
		expect(rows[0]?.get("[data-testid=ask-soc-request-question]").text()).toBe("Line one\nline two")
		expect(rows[1]?.find("[data-testid=ask-soc-request-filed]").exists()).toBe(false)
		// The alert has an open case: that is where a question goes by default.
		expect(wrapper.get("[data-testid=ask-soc-target-case]").text()).toContain("Add to case #4")
	})

	it("offers to open a case when the alert has none, and sends where the user chose", async () => {
		socRequests.listForAlert.mockResolvedValue({ data: { requests: [], open_case_id: null } })
		socRequests.askOnAlert.mockResolvedValue({ data: { request: request(5, { alert_id: 9 }) } })
		const { wrapper, asked } = render("alert", 9)
		await flushPromises()
		expect(wrapper.get("[data-testid=ask-soc-empty]").text()).toContain("No question asked about this alert yet.")
		expect(wrapper.get("[data-testid=ask-soc-target-case]").text()).toContain("Open a case from this alert")

		await type(wrapper, "  Should we isolate the host?\r\n  ")
		await choose(wrapper, "ask-soc-urgency", "high")
		await choose(wrapper, "ask-soc-target", "alert")
		socRequests.listForAlert.mockResolvedValue({ data: { requests: [request(5, { alert_id: 9 })], open_case_id: null } })
		await wrapper.get("[data-testid=ask-soc-form]").trigger("submit")
		await flushPromises()

		expect(socRequests.askOnAlert).toHaveBeenCalledWith(9, {
			question: "Should we isolate the host?",
			urgency: "high",
			target: "alert"
		})
		expect(asked).toHaveBeenCalledWith(expect.objectContaining({ id: 5 }))
		// The form starts over, and the list shows the new question.
		expect((wrapper.get("[data-testid=ask-soc-question] textarea").element as HTMLTextAreaElement).value).toBe("")
		expect(wrapper.findAll("[data-testid=ask-soc-request]")).toHaveLength(1)
	})

	it("sends nothing until the question can be sent, and says why", async () => {
		socRequests.listForAlert.mockResolvedValue({ data: { requests: [] } })
		const { wrapper } = render("alert", 9)
		await flushPromises()
		await wrapper.get("[data-testid=ask-soc-form]").trigger("submit")
		await flushPromises()
		expect(socRequests.askOnAlert).not.toHaveBeenCalled()
		expect(wrapper.get("[data-testid=ask-soc-problem]").text()).toBe("Write your question for the SOC")

		await type(wrapper, "a".repeat(2001))
		expect(wrapper.get("[data-testid=ask-soc-count]").text()).toBe("2001 / 2000")
		await wrapper.get("[data-testid=ask-soc-form]").trigger("submit")
		expect(socRequests.askOnAlert).not.toHaveBeenCalled()
		expect(wrapper.get("[data-testid=ask-soc-problem]").text()).toBe("Keep the question under 2000 characters")
	})

	it("shows the backend's refusal and keeps what was typed", async () => {
		socRequests.listForAlert.mockResolvedValue({ data: { requests: [] } })
		socRequests.askOnAlert.mockRejectedValue({
			response: { status: 429, data: { message: "You asked about this alert a moment ago: ask again in 7 minutes." } }
		})
		const { wrapper, asked } = render("alert", 9)
		await flushPromises()
		await type(wrapper, "Again?")
		await wrapper.get("[data-testid=ask-soc-form]").trigger("submit")
		await flushPromises()
		expect(wrapper.get("[data-testid=ask-soc-error]").text()).toContain("ask again in 7 minutes")
		expect((wrapper.get("[data-testid=ask-soc-question] textarea").element as HTMLTextAreaElement).value).toBe("Again?")
		expect(asked).not.toHaveBeenCalled()
	})

	it("says when the questions can't be read, and tries again", async () => {
		socRequests.listForAlert.mockRejectedValueOnce({ response: { status: 500, data: { message: "Failed" } } })
		socRequests.listForAlert.mockResolvedValue({ data: { requests: [] } })
		const { wrapper } = render("alert", 9)
		await flushPromises()
		const error = wrapper.get("[data-testid=ask-soc-list-error]")
		await error.get("button").trigger("click")
		await flushPromises()
		expect(wrapper.find("[data-testid=ask-soc-list-error]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=ask-soc-empty]").exists()).toBe(true)
	})
})

describe("asking the SOC about a case", () => {
	it("has no choice of target and sends on the case", async () => {
		socRequests.listForCase.mockResolvedValue({ data: { requests: [request(3, { case_id: 4, origin_alert_id: 9 })] } })
		socRequests.askOnCase.mockResolvedValue({ data: { request: request(6, { case_id: 4 }) } })
		const { wrapper, asked } = render("case", 4)
		await flushPromises()
		expect(wrapper.find("[data-testid=ask-soc-target]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=ask-soc-request-filed]").text()).toContain("Asked from alert #9")

		await type(wrapper, "When will this be closed?")
		await wrapper.get("[data-testid=ask-soc-form]").trigger("submit")
		await flushPromises()
		expect(socRequests.askOnCase).toHaveBeenCalledWith(4, { question: "When will this be closed?", urgency: "normal" })
		expect(asked).toHaveBeenCalledTimes(1)
	})
})

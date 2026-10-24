import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { resetOpenCustomerQuestions, useOpenCustomerQuestions } from "@/composables/useOpenCustomerQuestions"
import CustomerQuestionBadge from "../CustomerQuestionBadge.vue"
import { question } from "./fixtures"

const socRequests = vi.hoisted(() => ({ list: vi.fn(), markAnswered: vi.fn() }))
vi.mock("@/api", () => ({ default: { socRequests } }))

function answer(requests = [question(1, { case_id: 4 }), question(2, { case_id: 4 }), question(3, { alert_id: 9 })]) {
	return Promise.resolve({ data: { requests, total: requests.length, open: requests.length } })
}

beforeEach(() => {
	socRequests.list.mockReset()
	resetOpenCustomerQuestions()
})

/** "Customer question" on case and alert rows (#1305). */
describe("the customer question badge", () => {
	it("shows on a row with open questions, with the count when there are several", async () => {
		socRequests.list.mockImplementation(() => answer())
		const onCase = mount(CustomerQuestionBadge, { props: { entity: "case", entityId: 4 } })
		const onAlert = mount(CustomerQuestionBadge, { props: { entity: "alert", entityId: 9 } })
		const none = mount(CustomerQuestionBadge, { props: { entity: "case", entityId: 5 } })
		await flushPromises()
		expect(onCase.get("[data-testid=customer-question-badge]").text()).toBe("Customer question2")
		expect(onAlert.get("[data-testid=customer-question-badge]").text()).toBe("Customer question")
		expect(none.find("[data-testid=customer-question-badge]").exists()).toBe(false)
		// One request for every row of a list.
		expect(socRequests.list).toHaveBeenCalledTimes(1)
		expect(socRequests.list).toHaveBeenCalledWith({ status: "open" })
	})

	it("shows nothing when the questions can't be read, and tries again next time", async () => {
		socRequests.list.mockRejectedValueOnce(new Error("down"))
		socRequests.list.mockImplementationOnce(() => answer())
		const first = mount(CustomerQuestionBadge, { props: { entity: "case", entityId: 4 } })
		await flushPromises()
		expect(first.find("[data-testid=customer-question-badge]").exists()).toBe(false)
		mount(CustomerQuestionBadge, { props: { entity: "case", entityId: 4 } })
		await flushPromises()
		expect(socRequests.list).toHaveBeenCalledTimes(2)
		expect(first.find("[data-testid=customer-question-badge]").exists()).toBe(true)
	})

	it("reads again once invalidated, and forgets everything at logout", async () => {
		socRequests.list.mockImplementation(() => answer())
		const { ensure, invalidate, countFor } = useOpenCustomerQuestions()
		await ensure()
		await ensure()
		expect(socRequests.list).toHaveBeenCalledTimes(1)
		socRequests.list.mockImplementation(() => answer([]))
		await invalidate()
		expect(countFor("case", 4)).toBe(0)
		expect(socRequests.list).toHaveBeenCalledTimes(2)
		socRequests.list.mockImplementation(() => answer())
		await invalidate()
		resetOpenCustomerQuestions()
		expect(countFor("case", 4)).toBe(0)
	})
})

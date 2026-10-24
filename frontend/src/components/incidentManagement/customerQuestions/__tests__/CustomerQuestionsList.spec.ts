import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import CustomerQuestionsList from "../CustomerQuestionsList.vue"
import { question } from "./fixtures"

const socRequests = vi.hoisted(() => ({ list: vi.fn(), markAnswered: vi.fn() }))
vi.mock("@/api", () => ({ default: { socRequests } }))

const globalCodes = ref<string[]>([])
let onFilterChange: ((codes: string[]) => void) | null = null
vi.mock("@/composables/useGlobalCustomerFilter", () => ({
	useGlobalCustomerFilter: () => ({
		globalCustomerCodes: globalCodes,
		onGlobalCustomerFilterChange: (cb: (codes: string[]) => void) => {
			onFilterChange = cb
		}
	})
}))

vi.mock("@/components/incidentManagement/cases/CaseDetails.vue", () => ({
	__esModule: true,
	default: defineComponent({
		props: { caseId: Number },
		setup: props => () => h("div", { "data-testid": "case-details" }, `case ${props.caseId}`)
	})
}))
vi.mock("@/components/incidentManagement/alerts/AlertDetails.vue", () => ({
	__esModule: true,
	default: defineComponent({
		props: { alertId: Number },
		setup: props => () => h("div", { "data-testid": "alert-details" }, `alert ${props.alertId}`)
	})
}))

const page = { render: () => null }

async function render(path = "/customer-questions") {
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [
			{ path: "/customer-questions", name: "IncidentManagement-CustomerQuestions", component: page },
			{ path: "/incident-management/cases/:id", name: "IncidentManagement-Case", component: page },
			{ path: "/incident-management/alerts/:id", name: "IncidentManagement-Alert", component: page }
		]
	})
	await router.push(path)
	await router.isReady()
	const wrapper = mount(
		defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(CustomerQuestionsList)) }),
		{ global: { plugins: [router] }, attachTo: document.body }
	)
	await flushPromises()
	return { wrapper, router }
}

function listed(requests = [question(1, { case_id: 4, title: "Odd sign-in", urgency: "high" }), question(2, { alert_id: 9 })]) {
	return { data: { requests, total: 5, open: requests.length } }
}

beforeEach(() => {
	setActivePinia(createPinia())
	socRequests.list.mockReset()
	socRequests.markAnswered.mockReset()
	globalCodes.value = []
	onFilterChange = null
})

afterEach(() => {
	document.body.innerHTML = ""
})

/** Incidents → Customer questions (#1305). */
describe("the customer questions page", () => {
	it("lists the open questions of the customers in the global filter", async () => {
		globalCodes.value = ["ACME"]
		socRequests.list.mockResolvedValue(listed())
		const { wrapper } = await render()
		expect(socRequests.list).toHaveBeenCalledWith({ status: "open", customerCodes: ["ACME"] })
		const rows = wrapper.findAll("[data-testid=customer-question-row]")
		expect(rows).toHaveLength(2)
		expect(rows[0]?.get("[data-testid=customer-question-target]").text()).toContain("Odd sign-in")
		expect(rows[0]?.text()).toContain("High")
		expect(wrapper.get("[data-testid=customer-questions-status]").text()).toContain("Open (2)")
		expect(wrapper.get("[data-testid=customer-questions-status]").text()).toContain("All (5)")
	})

	it("keeps the status in the URL, the default left out", async () => {
		socRequests.list.mockResolvedValue(listed([]))
		const { wrapper, router } = await render("/customer-questions?status=answered")
		expect(socRequests.list).toHaveBeenLastCalledWith({ status: "answered", customerCodes: [] })
		expect(wrapper.get("[data-testid=customer-questions-empty]").text()).toContain("No customer questions")

		await router.replace({ query: { status: "all" } })
		await flushPromises()
		expect(socRequests.list).toHaveBeenLastCalledWith({ status: null, customerCodes: [] })

		const open = wrapper.findAll("[data-testid=customer-questions-status] input").find(i => i.element.getAttribute("value") === "open")
		await open?.trigger("change")
		await flushPromises()
		expect(router.currentRoute.value.query).toEqual({})
		expect(socRequests.list).toHaveBeenLastCalledWith({ status: "open", customerCodes: [] })
		expect(wrapper.get("[data-testid=customer-questions-empty]").text()).toContain("No question waiting for the SOC")
	})

	it("follows the global customer filter live", async () => {
		socRequests.list.mockResolvedValue(listed([]))
		await render()
		onFilterChange?.(["BETA", "GAMMA"])
		await flushPromises()
		expect(socRequests.list).toHaveBeenLastCalledWith({ status: "open", customerCodes: ["BETA", "GAMMA"] })
	})

	it("marks a question answered and reads the list again", async () => {
		// The page's own reads name the customers; the shared badge cache's read doesn't.
		let answered = false
		socRequests.list.mockImplementation(async (query: { customerCodes?: string[] }) =>
			query.customerCodes && !answered ? listed() : listed([question(2, { alert_id: 9 })])
		)
		socRequests.markAnswered.mockImplementation(async () => {
			answered = true
			return { data: { request: question(1, { status: "answered" }) } }
		})
		const { wrapper } = await render()
		await wrapper.findAll("[data-testid=customer-question-mark]")[0]?.trigger("click")
		await flushPromises()
		expect(socRequests.markAnswered).toHaveBeenCalledWith(1)
		expect(wrapper.findAll("[data-testid=customer-question-row]")).toHaveLength(1)
	})

	it("shows an answered question with who answered it, without the button", async () => {
		socRequests.list.mockResolvedValue(
			listed([
				question(3, {
					case_id: 4,
					status: "answered",
					answered_at: "2026-10-01T13:00:00Z",
					answered_by: "soc.analyst",
					answered_via: "comment"
				})
			])
		)
		const { wrapper } = await render("/customer-questions?status=answered")
		expect(wrapper.find("[data-testid=customer-question-mark]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=customer-question-done]").text()).toContain("soc.analyst")
	})

	it("opens the case in a modal whose header leads to its page", async () => {
		socRequests.list.mockResolvedValue(listed())
		const { wrapper } = await render()
		await wrapper.findAll("[data-testid=customer-question-target]")[0]?.trigger("click")
		await flushPromises()
		expect(document.body.querySelector("[data-testid=case-details]")?.textContent).toBe("case 4")
		const link = document.body.querySelector("[data-testid=modal-page-button]")
		expect(link?.getAttribute("href")).toContain("/incident-management/cases/4")

		await wrapper.findAll("[data-testid=customer-question-target]")[1]?.trigger("click")
		await flushPromises()
		expect(document.body.querySelector("[data-testid=alert-details]")?.textContent).toBe("alert 9")
	})

	it("says why the list could not be read, and tries again", async () => {
		socRequests.list.mockRejectedValueOnce({ response: { data: { message: "Not allowed" } } })
		socRequests.list.mockResolvedValue(listed([]))
		const { wrapper } = await render()
		const error = wrapper.get("[data-testid=customer-questions-error]")
		expect(error.text()).toContain("Not allowed")
		await error.get("button").trigger("click")
		await flushPromises()
		expect(wrapper.find("[data-testid=customer-questions-error]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=customer-questions-empty]").exists()).toBe(true)
	})
})

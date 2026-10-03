import type { SocDashboard } from "@/types/soc-management"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"
import AnalystsTab from "../tabs/AnalystsTab.vue"
import CustomersTab from "../tabs/CustomersTab.vue"
import OverviewTab from "../tabs/OverviewTab.vue"
import RulesTab from "../tabs/RulesTab.vue"
import SlaTab from "../tabs/SlaTab.vue"
import WorkloadTab from "../tabs/WorkloadTab.vue"
import { dashboard } from "./fixtures"

const getAttention = vi.fn()
vi.mock("@/api", () => ({
	default: { socManagement: { getAttention: (...args: unknown[]) => getAttention(...args) } }
}))

// Charts are covered by charts.spec.ts; here they only need to mount.
vi.mock("vue-echarts", () => ({
	default: defineComponent({ name: "VChart", props: { option: Object }, setup: () => () => h("div", { class: "v-chart" }) })
}))

function router() {
	const blank = { render: () => null }
	return createRouter({
		history: createMemoryHistory(),
		routes: [
			{ path: "/", component: blank },
			{ path: "/alerts", name: "IncidentManagement-Alerts", component: blank },
			{ path: "/cases", name: "IncidentManagement-Cases", component: blank },
			{ path: "/alerts/:id", name: "IncidentManagement-Alert", component: blank },
			{ path: "/cases/:id", name: "IncidentManagement-Case", component: blank }
		]
	})
}

async function render(component: unknown, props: Record<string, unknown>) {
	const appRouter = router()
	await appRouter.push("/")
	await appRouter.isReady()
	const wrapper = mount(component as never, { props: props as never, global: { plugins: [appRouter] } })
	await flushPromises()
	return { wrapper, router: appRouter }
}

function kpi(wrapper: { get: (s: string) => { text: () => string } }, id: string) {
	return wrapper.get(`[data-testid=${id}] [data-testid=kpi-value]`).text()
}

function adminView(): SocDashboard {
	return dashboard()
}

function analystView(): SocDashboard {
	const snapshot = dashboard()
	return dashboard({
		viewer: { username: "ana", is_admin: false, sees_all_analysts: false },
		analysts: snapshot.analysts.filter(row => row.username === "ana"),
		workload: { ...snapshot.workload, by_assignee: snapshot.workload.by_assignee.filter(row => row.username === "ana") }
	})
}

beforeEach(() => {
	setActivePinia(createPinia())
	getAttention.mockReset()
	getAttention.mockResolvedValue({ data: { items: dashboard().attention, total: 2 } })
})

describe("overviewTab", () => {
	it("puts each headline number in its tile, with the delta against the previous period", async () => {
		const { wrapper } = await render(OverviewTab, { dashboard: adminView() })
		expect(kpi(wrapper, "kpi-alerts-opened")).toBe("1,284")
		expect(wrapper.get("[data-testid=kpi-alerts-opened]").text()).toContain("+10%")
		expect(kpi(wrapper, "kpi-tta")).toBe("12m")
		expect(kpi(wrapper, "kpi-breached")).toBe("2")
		expect(kpi(wrapper, "kpi-fp-rate")).toBe("31.5%")
		expect(wrapper.get("[data-testid=sla-gauge-value]").text()).toMatch(/96\.4/)
	})

	it("explains the dial in a tooltip: the arc, the colour bands, the objective notch", async () => {
		const { wrapper } = await render(OverviewTab, { dashboard: adminView() })
		const help = wrapper.get("[data-testid=hero-gauge-help]")
		expect(help.attributes("aria-label")).toBe("How to read the dial")
		await help.trigger("mouseenter")
		await new Promise(resolve => setTimeout(resolve, 250)) // the tooltip's show delay
		await flushPromises()
		const text = document.body.textContent ?? ""
		expect(text).toContain("met ÷ (met + breached)")
		expect(text).toContain("95% or more — on objective")
		expect(text).toContain("85–95% — below objective")
		expect(text).toContain("the 95% objective")
		wrapper.unmount()
	})

	it("links the opened-alerts and opened-cases tiles to their lists, keeping the customers in view", async () => {
		const scoped = dashboard({ customer_codes: ["ACME"] })
		const { wrapper } = await render(OverviewTab, { dashboard: scoped })
		expect(wrapper.get("[data-testid=kpi-alerts-opened-link]").attributes("href")).toBe("/alerts?customerCode=ACME")
		expect(wrapper.get("[data-testid=kpi-cases-opened-link]").attributes("href")).toBe("/cases")
		const { wrapper: everyone } = await render(OverviewTab, { dashboard: dashboard({ customer_codes: null }) })
		expect(everyone.get("[data-testid=kpi-alerts-opened-link]").attributes("href")).toBe("/alerts")
	})

	it("says how many open items wait on the customer, next to past SLA", async () => {
		const { wrapper } = await render(OverviewTab, { dashboard: adminView() })
		expect(wrapper.get("[data-testid=kpi-breached]").text()).toContain("1 at risk · 16 open · 4 waiting")
		const none = dashboard({ workload: { ...dashboard().workload, waiting_on_customer: 0 } })
		const { wrapper: quiet } = await render(OverviewTab, { dashboard: none })
		expect(quiet.get("[data-testid=kpi-breached]").text()).not.toContain("waiting")
	})

	it("lists the severities and links its panels to their tabs", async () => {
		const { wrapper } = await render(OverviewTab, { dashboard: adminView() })
		expect(wrapper.get("[data-testid=overview-severity-table]").text()).toContain("Critical")
		const buttons = wrapper.findAll("button").filter(b => /View all|SLA detail/.test(b.text()))
		for (const button of buttons) await button.trigger("click")
		expect(wrapper.emitted("openTab")?.flat()).toEqual(expect.arrayContaining(["workload", "sla"]))
	})
})

describe("slaTab", () => {
	it("shows the alert figures first and switches to cases", async () => {
		const { wrapper } = await render(SlaTab, { dashboard: adminView() })
		const tiles = () => wrapper.findAll("[data-testid=kpi-value]").map(tile => tile.text())
		expect(tiles()).toEqual(["98.0%", "96.4%", "12m", "3h 50m"])
		expect(wrapper.text()).toContain("targets: global policy")
		await wrapper.findAll("[data-testid=sla-entity] input")[1].setValue(true)
		await flushPromises()
		expect(tiles()).toEqual(["100.0%", "94.7%", "5m", "1d"])
	})

	it("puts the policy target next to the actual times of each severity", async () => {
		const { wrapper } = await render(SlaTab, { dashboard: adminView() })
		const table = wrapper.get("[data-testid=sla-severity-table]").text()
		expect(table).toContain("Critical")
		expect(table).toContain("15m") // Critical alert response target
		expect(table).toContain("4h") // Critical alert resolution target
	})
})

describe("analystsTab", () => {
	it("gives an admin every analyst", async () => {
		const { wrapper } = await render(AnalystsTab, { dashboard: adminView() })
		const table = wrapper.get("[data-testid=analysts-table]").text()
		expect(table).toContain("ana")
		expect(table).toContain("bob")
		expect(wrapper.find("[data-testid=analysts-own-only]").exists()).toBe(false)
	})

	it("gives an analyst their own row and says why", async () => {
		const { wrapper } = await render(AnalystsTab, { dashboard: analystView() })
		expect(wrapper.find("[data-testid=analysts-own-only]").exists()).toBe(true)
		expect(wrapper.text()).toContain("Your performance")
		expect(wrapper.get("[data-testid=analysts-table]").text()).not.toContain("bob")
	})
})

describe("rulesTab", () => {
	it("flags noisy rules and can show only them", async () => {
		const { wrapper } = await render(RulesTab, { dashboard: adminView() })
		const rows = () => wrapper.findAll("[data-testid=rules-table] tbody tr")
		expect(rows()).toHaveLength(2)
		expect(wrapper.get("[data-testid=rules-table]").text()).toContain("noisy")
		await wrapper.get("[data-testid=rules-only-noisy]").trigger("click")
		await flushPromises()
		expect(rows()).toHaveLength(1)
		expect(rows()[0].text()).toContain("Brute force SSH login")
	})

	it("opens the alert list filtered to a rule, and to the one customer in scope", async () => {
		const { wrapper, router: appRouter } = await render(RulesTab, { dashboard: dashboard({ customer_codes: ["ACME"] }) })
		const push = vi.spyOn(appRouter, "push")
		await wrapper.get("[aria-label='Open the alerts of Brute force SSH login']").trigger("click")
		expect(push).toHaveBeenCalledWith({
			name: "IncidentManagement-Alerts",
			query: { title: "Brute force SSH login", customerCode: "ACME" }
		})
	})
})

describe("customersTab", () => {
	it("lists customers and asks the page to focus on one", async () => {
		const { wrapper } = await render(CustomersTab, { dashboard: adminView() })
		expect(wrapper.get("[data-testid=customers-table]").text()).toContain("Acme Corp")
		await wrapper.get("[aria-label='Focus on ACME']").trigger("click")
		expect(wrapper.emitted("focusCustomer")?.[0]).toEqual(["ACME"])
	})
})

describe("workloadTab", () => {
	it("shows the live backlog, what waits on the customer, and the attention list", async () => {
		const { wrapper } = await render(WorkloadTab, { dashboard: adminView(), scope: { customerCodes: ["ACME"] } })
		expect(kpi(wrapper, "kpi-waiting")).toBe("4")
		expect(wrapper.get("[data-testid=kpi-waiting]").text()).toContain("clocks stopped until they reply")
		const [bySeverity, byAssignee] = wrapper.findAll("[data-testid=load-bars]")
		expect(bySeverity.attributes("aria-label")).toContain("Critical:")
		expect(byAssignee.attributes("aria-label")).toContain("bob:")
		expect(getAttention).toHaveBeenCalledWith(expect.objectContaining({ customerCodes: ["ACME"], limit: 200 }), expect.any(AbortSignal))
		expect(wrapper.get("[data-testid=attention-list]").text()).toContain("Ransomware note dropped")
	})

	it("reloads the attention list when its filters change", async () => {
		const { wrapper } = await render(WorkloadTab, { dashboard: adminView(), scope: {} })
		await wrapper.findAll("[data-testid=attention-state] input")[1].setValue(true)
		await flushPromises()
		expect(getAttention).toHaveBeenLastCalledWith(expect.objectContaining({ state: "breached" }), expect.any(AbortSignal))
	})

	it("gives an analyst only their own backlog", async () => {
		const { wrapper } = await render(WorkloadTab, { dashboard: analystView(), scope: {} })
		expect(wrapper.text()).toContain("Your backlog")
		const byAssignee = wrapper.findAll("[data-testid=load-bars]").at(-1)
		expect(byAssignee?.attributes("aria-label") ?? "").not.toContain("bob:")
	})

	it("says when the list could not be loaded", async () => {
		getAttention.mockImplementation(() => Promise.reject(Object.assign(new Error("boom"), { response: { data: { detail: "down" } } })))
		const { wrapper } = await render(WorkloadTab, { dashboard: adminView(), scope: {} })
		expect(wrapper.text()).toContain("Could not load the list: down")
	})
})

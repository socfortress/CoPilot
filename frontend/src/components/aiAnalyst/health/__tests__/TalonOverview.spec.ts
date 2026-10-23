/**
 * The Overview tab, now the Talon health dashboard: it shows the banner, CoPilot's own checks, the
 * component grid by group, the uptime bars, the charts and the configuration; it keeps CoPilot's
 * checks when Talon is unreachable or too old for the health API; a null metric is "no data", never
 * 0; it refreshes every 60 s only while the tab is shown and the page visible; and the 24 h / 7 d
 * toggle asks for `hours=168`.
 */
import type { TalonHealthReport } from "@/types/talonHealth"
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils"
import { AxiosError, AxiosHeaders } from "axios"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import TalonOverview from "../../TalonOverview.vue"
import { OLD_TALON_TEXT, REFRESH_MS, TALON_DOCS } from "../health"
import { bucket, healthReport, must, oldTalonReport, unreachableReport } from "./fixtures"

const getHealth = vi.fn()

vi.mock("@/api", () => ({
	default: { talonHealth: { getHealth: (...a: unknown[]) => getHealth(...a) } }
}))

vi.mock("vue-echarts", () => ({
	default: defineComponent({
		props: { option: { type: Object, required: true } },
		setup: () => () => h("div", { "data-testid": "v-chart" })
	})
}))

function answer(report: TalonHealthReport) {
	return Promise.resolve({ data: report })
}

function render(props: Record<string, unknown> = {}) {
	return mount(TalonOverview, { props })
}

function texts(wrapper: ReturnType<typeof render>, testId: string) {
	return wrapper.findAll(`[data-testid="${testId}"]`).map(n => n.text())
}

let visibility: DocumentVisibilityState = "visible"

enableAutoUnmount(afterEach)

describe("talon health dashboard", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		getHealth.mockReset()
		visibility = "visible"
		vi.spyOn(document, "visibilityState", "get").mockImplementation(() => visibility)
	})
	afterEach(() => {
		vi.useRealTimers()
		vi.restoreAllMocks()
	})

	it("shows a spinner, then the whole dashboard", async () => {
		let resolve!: (value: unknown) => void
		getHealth.mockReturnValue(new Promise(r => (resolve = r)))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-testid="talon-health-loading"]').exists()).toBe(true)
		resolve({ data: healthReport() })
		await flushPromises()

		expect(getHealth).toHaveBeenCalledWith(24, expect.any(AbortSignal))
		expect(wrapper.get('[data-testid="talon-health-banner-title"]').text()).toBe("Degraded")
		expect(wrapper.get('[data-testid="talon-health-version"]').text()).toContain("0.1.3")
		expect(wrapper.get('[data-testid="talon-health-uptime"]').text()).toBe("up 1 d 2 h")
		expect(wrapper.get('[data-testid="talon-health-checked"]').text()).toMatch(/^checked \d+s ago$/)

		// From CoPilot: words and icons, not colour alone.
		expect(wrapper.get('[data-testid="talon-check-connector"]').text()).toContain("Configured and verified")
		expect(wrapper.get('[data-testid="talon-check-connector"]').text()).toContain("http://talon-analyst-api:3100")
		expect(wrapper.get('[data-testid="talon-check-reachable"]').text()).toContain("Yes, 8 ms")
		expect(wrapper.get('[data-testid="talon-check-auth"]').text()).toContain("Accepted")
		expect(wrapper.get('[data-testid="talon-check-v2"]').text()).toContain("On")
		expect(wrapper.get('[data-testid="talon-copilot-facts"]').text()).toContain("Jobs failed in 24 h1")

		// The grid, by group, each with a pill that says its status.
		expect(wrapper.findAll("[data-group]").map(g => g.attributes("data-group"))).toEqual(["core", "mcp", "model"])
		expect(texts(wrapper, "talon-health-status")).toEqual(["OK", "OK", "Warning", "Failing"])
		const wazuh = wrapper.get('[data-component="wazuh_mcp"]')
		expect(wazuh.text()).toContain("How to fix")
		expect(wrapper.get('[data-component="api"]').text()).not.toContain("How to fix")

		// Uptime rows say it in words too.
		expect(texts(wrapper, "talon-uptime-summary")).toEqual(["all 1 OK", "1 warning of 1"])

		// Configuration.
		expect(wrapper.get('[data-testid="talon-config-live"]').findAll(".n-tag").map(t => t.text())).toEqual(["ACME", "GLOBEX"])
		expect(wrapper.get('[data-testid="talon-config-automation"]').text()).toBe("Level 1")
		expect(wrapper.get('[data-testid="talon-config-switch-chat_browser"]').text()).toContain("Not reported")
		expect(wrapper.get('[data-testid="talon-config-writeback"]').text()).toBe("Live")
		expect(wrapper.get('[data-testid="talon-config-budget-spent-today"]').text()).toBe("Spent today (UTC, all customers)$20.00")
		expect(wrapper.get('[data-testid="talon-config-budget-daily"]').text()).toBe("Default daily ceiling per customer$25.00")
		expect(wrapper.get('[data-testid="talon-config-budget-monthly"]').text()).toBe("Default monthly ceiling per customerUnlimited")
		// Tool errors aren't recorded: the chart says so rather than drawing zeros.
		expect(wrapper.get('[data-testid="talon-health-chart-tools"]').text()).toContain("Tool errors: no data")

		// The docs.
		expect(wrapper.get('[data-testid="talon-health-docs"]').attributes("href")).toBe(TALON_DOCS.overview)
		expect(wrapper.get('[data-testid="talon-health-docs"]').text()).toContain("What Talon does and how to set it up")
	})

	it("a null metric is no data, never 0", async () => {
		const report = healthReport()
		must(report.metrics.data).series = [
			bucket("2026-10-22T07:00:00Z", { queue_depth_max: null, cost_usd: null }),
			bucket("2026-10-22T08:00:00Z", { queue_depth_max: null })
		]
		getHealth.mockReturnValue(answer(report))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-health-chart-queue"]').text()).toContain("No data")
		// The table view opens from "Show the numbers".
		await wrapper.get('[data-testid="talon-health-charts"] .n-collapse-item__header-main').trigger("click")
		await flushPromises()
		const first = wrapper.findAll('[data-testid="talon-health-metrics-row"]')[0].findAll("td").map(c => c.text())
		expect(first[5]).toBe("no data") // queue max
		expect(first[7]).toBe("no data") // tool errors
		expect(first[9]).toBe("no data") // cost
		expect(first[6]).toBe("50") // tool calls
	})

	it("unreachable: CoPilot's checks with the reason, the rest unavailable", async () => {
		getHealth.mockReturnValue(answer(unreachableReport()))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-health-banner-title"]').text()).toBe("Down")
		expect(wrapper.get('[data-testid="talon-health-banner-reason"]').text()).toBe("Talon could not be reached (ConnectError)")
		expect(wrapper.get('[data-testid="talon-check-reachable"]').text()).toContain("No")
		expect(wrapper.get('[data-testid="talon-check-reachable-detail"]').text()).toBe(
			"Talon could not be reached (ConnectError)"
		)
		expect(wrapper.get('[data-testid="talon-check-connector"]').text()).toContain("Configured and verified")
		const unavailable = texts(wrapper, "talon-health-unavailable")
		expect(unavailable).toHaveLength(4)
		expect(unavailable.every(t => t === "Unavailable: Talon could not be reached (ConnectError)")).toBe(true)
	})

	it("an old Talon (404): the upgrade notice, and CoPilot's checks still shown", async () => {
		getHealth.mockReturnValue(answer(oldTalonReport()))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-health-old"]').text()).toContain(OLD_TALON_TEXT)
		expect(wrapper.get('[data-testid="talon-check-auth"]').text()).toContain("Accepted")
		expect(wrapper.get('[data-testid="talon-health-banner-title"]').text()).toBe("Status unknown")
		expect(texts(wrapper, "talon-health-unavailable").every(t => t.includes(OLD_TALON_TEXT))).toBe(true)
	})

	it("empty: no history and no activity yet", async () => {
		const report = healthReport()
		must(report.history.data).components = {}
		must(report.metrics.data).series = []
		getHealth.mockReturnValue(answer(report))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find('[data-testid="talon-uptime-empty"]').exists()).toBe(true)
		expect(wrapper.find('[data-testid="talon-health-metrics-empty"]').exists()).toBe(true)
	})

	it("an error from CoPilot itself is shown, and the last good render kept", async () => {
		getHealth.mockReturnValueOnce(answer(healthReport()))
		const wrapper = render()
		await flushPromises()
		getHealth.mockRejectedValueOnce(
			new AxiosError("x", "ERR", undefined, undefined, {
				status: 500,
				statusText: "",
				headers: {},
				config: { headers: new AxiosHeaders() },
				data: {}
			})
		)
		await wrapper.get('[data-testid="talon-health-refresh"]').trigger("click")
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-health-error"]').text()).toBe("CoPilot could not load Talon's health (HTTP 500)")
		expect(wrapper.find('[data-testid="talon-health-body"]').exists()).toBe(true)
	})

	it("the 7 d toggle asks for 168 hours", async () => {
		getHealth.mockImplementation(() => answer(healthReport()))
		const wrapper = render()
		await flushPromises()
		await wrapper.get('[data-testid="talon-health-window-168"]').trigger("click")
		await flushPromises()
		expect(getHealth).toHaveBeenLastCalledWith(168, expect.any(AbortSignal))
	})

	it("refreshes every 60 s, only while the tab is shown and the page visible", async () => {
		vi.useFakeTimers({ toFake: ["setInterval", "clearInterval", "Date"] })
		getHealth.mockImplementation(() => answer(healthReport()))
		const wrapper = render({ active: true })
		await flushPromises()
		expect(getHealth).toHaveBeenCalledTimes(1)
		vi.advanceTimersByTime(REFRESH_MS)
		await flushPromises()
		expect(getHealth).toHaveBeenCalledTimes(2)

		visibility = "hidden"
		vi.advanceTimersByTime(REFRESH_MS * 2)
		await flushPromises()
		expect(getHealth).toHaveBeenCalledTimes(2)
		// Back in view after more than a minute: one refresh at once.
		visibility = "visible"
		document.dispatchEvent(new Event("visibilitychange"))
		await flushPromises()
		expect(getHealth).toHaveBeenCalledTimes(3)

		await wrapper.setProps({ active: false })
		vi.advanceTimersByTime(REFRESH_MS * 2)
		await flushPromises()
		expect(getHealth).toHaveBeenCalledTimes(3)
		await wrapper.setProps({ active: true })
		await flushPromises()
		expect(getHealth).toHaveBeenCalledTimes(4)
	})

	it("the cost chart links the Usage tab only with v2 on", async () => {
		getHealth.mockReturnValue(answer(healthReport()))
		const wrapper = render({ usageAvailable: true })
		await flushPromises()
		await wrapper.get('[data-testid="talon-health-usage-link"]').trigger("click")
		expect(wrapper.emitted("open-tab")).toEqual([["usage"]])

		const off = healthReport()
		off.copilot.v2_enabled = false
		getHealth.mockReturnValue(answer(off))
		const other = render({ usageAvailable: false })
		await flushPromises()
		expect(other.find('[data-testid="talon-health-usage-link"]').exists()).toBe(false)
		expect(other.get('[data-testid="talon-check-v2"]').text()).toContain("Off")
	})

	it("a scoped analyst is told what the lists cover", async () => {
		const report = healthReport()
		report.copilot.scope = "assigned"
		must(must(report.health.data).config).live_customers = []
		getHealth.mockReturnValue(answer(report))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get('[data-testid="talon-config-live-none"]').text()).toBe("None of your customers")
		expect(wrapper.text()).toContain("cover only the customers assigned to you")
	})
})

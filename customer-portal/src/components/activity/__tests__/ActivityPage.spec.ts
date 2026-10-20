import type { Activity } from "@/types/activity"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider, NRadioGroup } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter, RouterView } from "vue-router"
import { filtersFromQuery } from "@/components/alerts/filters/alertsFilters"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import ActivityPage from "../ActivityPage.vue"
import { activityFixture } from "./fixtures"

const getActivity = vi.hoisted(() => vi.fn())
vi.mock("@/api", () => ({ default: { activity: { getActivity } } }))

function respond(value: Activity) {
	return Promise.resolve({ data: value })
}

async function mountPage(path = "/activity") {
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [
			{ path: "/activity", name: "Activity", component: ActivityPage },
			{ path: "/alerts", name: "AlertsList", component: { render: () => h("div", "alerts") } }
		]
	})
	await router.push(path)
	await router.isReady()
	const wrapper = mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(RouterView)) }), {
		global: { plugins: [router] },
		attachTo: document.body
	})
	await flushPromises()
	return { wrapper, router }
}

/** The query of a link's href, read back as the alerts list reads it. */
function linkFilters(href: string | undefined) {
	const url = new URL(href ?? "", "http://portal")
	return filtersFromQuery(Object.fromEntries(url.searchParams.entries()))
}

beforeEach(() => {
	setActivePinia(createPinia())
	getActivity.mockReset()
})

/** The Activity page (#1284). */
describe("activityPage", () => {
	it("asks for the last 30 days by default, for the customers in the filter", async () => {
		getActivity.mockImplementation(() => respond(activityFixture()))
		await mountPage()
		expect(getActivity).toHaveBeenCalledTimes(1)
		expect(getActivity.mock.calls[0]![0]).toBe("30d")
	})

	it("shows the headline figures and every breakdown", async () => {
		getActivity.mockImplementation(() => respond(activityFixture()))
		const { wrapper } = await mountPage()

		expect(wrapper.get("[data-testid=activity-kpi-alerts] [data-testid=activity-kpi-value]").text()).toBe("12")
		expect(wrapper.get("[data-testid=activity-kpi-alerts] [data-testid=activity-kpi-delta]").text()).toBe("+3")
		expect(wrapper.get("[data-testid=activity-kpi-false-positives] [data-testid=activity-kpi-value]").text()).toBe(
			"25%"
		)
		expect(
			wrapper.find("[data-testid=activity-kpi-false-positives] [data-testid=activity-kpi-delta]").exists()
		).toBe(false)
		const rows = (testid: string) =>
			wrapper.findAll(`[data-testid=${testid}-row]`).map(row => row.attributes("data-key"))
		expect(rows("activity-sources")).toEqual(["wazuh", "office365"])
		// Only the levels with something in either period.
		expect(rows("activity-severities")).toEqual(["Critical", "High"])
		expect(rows("activity-detections")).toEqual(["Brute force"])
		expect(rows("activity-assets")).toEqual(["web-01"])
		expect(rows("activity-tags")).toEqual(["vip"])
		expect(rows("activity-reasons")).toEqual(["RULE_TOO_SENSITIVE"])
		expect(rows("activity-case-types")).toEqual(["INC"])
		expect(wrapper.get("[data-testid=activity-case-statuses-row]").text()).toContain("Waiting on you")
		expect(wrapper.get("[data-testid=activity-noisy]").text()).toContain("2 of 4 reviewed · 50%")
		expect(wrapper.get("[data-testid=activity-verdict-split]").text()).toContain("Not reviewed yet")
		wrapper.unmount()
	})

	it("links each count to exactly the alerts it counted, in either period", async () => {
		getActivity.mockImplementation(() => respond(activityFixture()))
		const { wrapper } = await mountPage()

		const wazuh = wrapper.get("[data-testid=activity-sources-row][data-key=wazuh]")
		const current = linkFilters(wazuh.get("[data-testid=activity-row-count]").attributes("href"))
		expect([current.source, current.openedFrom, current.openedBefore]).toEqual([
			"wazuh",
			"2026-09-01T12:00:00Z",
			"2026-10-01T12:00:00Z"
		])
		const previous = linkFilters(wazuh.get("[data-testid=activity-row-previous]").attributes("href"))
		expect([previous.openedFrom, previous.openedBefore]).toEqual(["2026-08-02T12:00:00Z", "2026-09-01T12:00:00Z"])

		const detection = wrapper.get("[data-testid=activity-detections-row] [data-testid=activity-row-label]")
		expect(linkFilters(detection.attributes("href")).detection).toBe("Brute force")
		const tag = wrapper.get("[data-testid=activity-tags-row] [data-testid=activity-row-label]")
		expect(linkFilters(tag.attributes("href")).tags).toEqual(["vip"])
		const kpi = wrapper.get("[data-testid=activity-kpi-alerts] [data-testid=activity-kpi-value]")
		expect(linkFilters(kpi.attributes("href")).openedFrom).toBe("2026-09-01T12:00:00Z")

		// Severity, reasons and cases cannot be listed as counted: they are not links.
		expect(
			wrapper.get("[data-testid=activity-severities-row] [data-testid=activity-row-label]").element.tagName
		).toBe("SPAN")
		expect(
			wrapper.get("[data-testid=activity-case-types-row] [data-testid=activity-row-count]").element.tagName
		).toBe("SPAN")
		wrapper.unmount()
	})

	it("keeps the range in the URL, the default left out, and reloads for it", async () => {
		getActivity.mockImplementation(() => respond(activityFixture()))
		const { wrapper, router } = await mountPage("/activity?range=7d")
		expect(getActivity.mock.calls[0]![0]).toBe("7d")

		wrapper.findComponent(NRadioGroup).vm.$emit("update:value", "90d")
		await flushPromises()
		expect(router.currentRoute.value.query.range).toBe("90d")
		expect(getActivity.mock.calls.at(-1)![0]).toBe("90d")

		wrapper.findComponent(NRadioGroup).vm.$emit("update:value", "30d")
		await flushPromises()
		expect(router.currentRoute.value.query.range).toBeUndefined()
		wrapper.unmount()
	})

	it("reloads when the customer filter changes", async () => {
		getActivity.mockImplementation(() => respond(activityFixture()))
		const { wrapper } = await mountPage()
		expect(getActivity.mock.calls[0]![1]).toBeUndefined()
		useCustomerFilterStore().setSelected(["ACME"])
		await flushPromises()
		expect(getActivity).toHaveBeenCalledTimes(2)
		expect(getActivity.mock.calls[1]).toEqual(["30d", ["ACME"], expect.any(AbortSignal)])
		wrapper.unmount()
	})

	it("says the page is not available when the customer's switch is off", async () => {
		getActivity.mockImplementation(() => respond({ ...activityFixture(), enabled: false }))
		const { wrapper } = await mountPage()
		expect(wrapper.find("[data-testid=activity-disabled]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=activity-kpi-alerts]").exists()).toBe(false)
		wrapper.unmount()
	})

	it("shows a failed section on its own, the others still there", async () => {
		const failed = activityFixture()
		failed.alerts.error = "Failed to load the alerts"
		getActivity.mockImplementation(() => respond(failed))
		const { wrapper } = await mountPage()
		expect(wrapper.get("[data-testid=activity-sources-panel]").text()).toContain("Failed to load the alerts")
		expect(wrapper.find("[data-testid=activity-sources-row]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=activity-reasons-row]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=activity-case-types-row]").exists()).toBe(true)
		wrapper.unmount()
	})

	it("offers to try again when the first load fails, and keeps old figures when a later one does", async () => {
		getActivity.mockRejectedValueOnce({ response: { data: { detail: "Failed to load the activity" } } })
		getActivity.mockImplementation(() => respond(activityFixture()))
		const { wrapper } = await mountPage()
		expect(wrapper.get("[data-testid=panel-error]").text()).toContain("Try again")

		await wrapper.get("[data-testid=panel-error] button").trigger("click")
		await flushPromises()
		expect(wrapper.find("[data-testid=activity-kpi-alerts]").exists()).toBe(true)
		wrapper.unmount()
	})

	it("says what happened when nothing was opened in a breakdown", async () => {
		const quiet = activityFixture()
		quiet.alerts.top_assets = []
		getActivity.mockImplementation(() => respond(quiet))
		const { wrapper } = await mountPage()
		expect(wrapper.get("[data-testid=activity-assets-panel]").text()).toContain(
			"No alert named an asset this period"
		)
		wrapper.unmount()
	})
})

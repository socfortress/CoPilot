import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios"
import { flushPromises, mount } from "@vue/test-utils"
import axios from "axios"
import { NDropdown, NMessageProvider, NSelect } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"

/**
 * The filters that build an analyst's working queue (#1331): Opened (a date range on when
 * the alert reached the SOC), Unassigned, several statuses at once, Escalated and Linked
 * to Case. Each is sent to /alerts/filter, so it applies to the whole dataset.
 */

vi.mock("@/stores/auth", () => ({
	useAuthStore: () => ({ userToken: null, refreshToken: vi.fn() })
}))
vi.mock("@/composables/useGlobalCustomerFilter", async () => {
	const { ref: vueRef } = await import("vue")
	return {
		useGlobalCustomerFilter: () => ({ globalCustomerCodes: vueRef([]), onGlobalCustomerFilterChange: vi.fn() })
	}
})

const { HttpClient } = await import("@/api/http-client")
const alerts = (await import("@/api/endpoints/incidentManagement/alerts")).default
const AlertsFilters = (await import("../AlertsFilters.vue")).default

function recordingAdapter(seen: string[]): AxiosAdapter {
	return (config: InternalAxiosRequestConfig) => {
		seen.push(axios.getUri(config))
		// Never settles: the option lists the filter bar loads are not under test.
		return new Promise(() => {})
	}
}

const seen: string[] = []

beforeEach(() => {
	setActivePinia(createPinia())
	seen.length = 0
	HttpClient.defaults.adapter = recordingAdapter(seen)
})

async function sentParams(filters: Parameters<typeof alerts.getAlertsList>[0]["filters"]) {
	void alerts.getAlertsList({ filters })
	await vi.waitFor(() => expect(seen).toHaveLength(1))
	return new URL(seen[0], "http://x").searchParams
}

describe("the alerts endpoint", () => {
	it("sends several statuses as a repeated param, and a single one as a list of one", async () => {
		expect((await sentParams([{ type: "status", value: ["OPEN", "IN_PROGRESS"] }])).getAll("status")).toEqual([
			"OPEN",
			"IN_PROGRESS"
		])
		seen.length = 0
		expect((await sentParams([{ type: "status", value: "CLOSED" }])).getAll("status")).toEqual(["CLOSED"])
	})

	it("sends Opened as local midnights: the first day included, the day after the last excluded", async () => {
		const params = await sentParams([{ type: "opened", value: ["2026-10-01", "2026-10-03"] }])

		expect(new Date(params.get("opened_from") as string).getTime()).toBe(new Date(2026, 9, 1).getTime())
		expect(new Date(params.get("opened_before") as string).getTime()).toBe(new Date(2026, 9, 4).getTime())
	})

	it("sends Unassigned, Escalated and Linked to Case with the other filters", async () => {
		const params = await sentParams([
			{ type: "assignedTo", value: "UNASSIGNED" },
			{ type: "escalated", value: "false" },
			{ type: "linkedToCase", value: "true" },
			{ type: "severity", value: ["High"] }
		])

		expect(params.get("assigned_to")).toBe("UNASSIGNED")
		expect(params.get("escalated")).toBe("false")
		expect(params.get("linked_to_case")).toBe("true")
		expect(params.getAll("severity")).toEqual(["High"])
	})
})

async function mountFilters(props: Record<string, unknown>, query: Record<string, string | string[]> = {}) {
	const router = createRouter({
		history: createMemoryHistory(),
		routes: [{ path: "/", component: { render: () => null } }]
	})
	await router.push({ path: "/", query })
	const wrapper = mount(
		defineComponent({
			setup: () => () => h(NMessageProvider, null, { default: () => h(AlertsFilters, props) })
		}),
		{ global: { plugins: [router] } }
	)
	await flushPromises()
	return { wrapper, filters: wrapper.findComponent(AlertsFilters) }
}

describe("alertsFilters", () => {
	it("offers the new filters in the + menu", async () => {
		const { wrapper } = await mountFilters({})
		const keys = (wrapper.findComponent(NDropdown).props("options") as { key: string }[]).map(o => o.key)

		expect(keys).toEqual(expect.arrayContaining(["opened", "escalated", "linkedToCase"]))
	})

	it("lists Unassigned first among the assignees", async () => {
		const { wrapper } = await mountFilters({ preset: [{ type: "assignedTo", value: "UNASSIGNED" }] })
		const select = wrapper.findComponent(NSelect)

		expect((select.props("options") as { label: string; value: string }[])[0]).toEqual({
			label: "Unassigned",
			value: "UNASSIGNED"
		})
		expect(select.props("value")).toBe("UNASSIGNED")
	})

	it("makes Status a multi-select, and a status counter's single status a list", async () => {
		const { wrapper, filters } = await mountFilters({})

		;(filters.vm as unknown as { setFilter: (f: unknown[]) => void }).setFilter([{ type: "status", value: "OPEN" }])
		await flushPromises()

		expect(wrapper.findComponent(NSelect).props("multiple")).toBe(true)
		expect(filters.emitted("submit")?.at(-1)).toEqual([[{ type: "status", value: ["OPEN"] }]])
	})

	it("restores every new filter from the URL, dropping what the API would refuse", async () => {
		const { filters } = await mountFilters(
			{ useQueryString: true },
			{
				status: ["OPEN", "DONE"],
				opened: ["2026-10-01", "2026-10-03"],
				escalated: "maybe",
				linkedToCase: "false"
			}
		)

		expect(filters.emitted("submit")?.[0]).toEqual([
			[
				{ type: "status", label: "Status", value: ["OPEN"] },
				{ type: "opened", label: "Opened", value: ["2026-10-01", "2026-10-03"] },
				{ type: "linkedToCase", label: "Linked to Case", value: "false" }
			]
		])
	})

	it("drops an Opened range that is reversed, malformed or one day short", async () => {
		for (const opened of [["2026-10-03", "2026-10-01"], ["2026-10-01", "yesterday"], "2026-10-01"]) {
			const { filters } = await mountFilters({ useQueryString: true }, { opened })
			expect(filters.emitted("submit")).toBeUndefined()
		}
	})
})

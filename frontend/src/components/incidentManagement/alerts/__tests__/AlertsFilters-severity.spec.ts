import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios"
import { flushPromises, mount } from "@vue/test-utils"
import axios from "axios"
import { NMessageProvider, NSelect } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { createMemoryHistory, createRouter } from "vue-router"

/**
 * The Severity filter on the alerts list (#1322): any of several levels, sent as a
 * repeated `severity` param to /alerts/filter so it applies to the whole dataset and
 * combines with every other filter.
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

describe("the alerts endpoint", () => {
	it("sends the selected severities as a repeated param, with the other filters", async () => {
		void alerts.getAlertsList({
			filters: [
				{ type: "severity", value: ["Critical", "High"] },
				{ type: "status", value: "OPEN" }
			]
		})
		await vi.waitFor(() => expect(seen).toHaveLength(1))

		const url = new URL(seen[0], "http://x")
		expect(url.pathname).toMatch(/\/incidents\/db_operations\/alerts\/filter$/)
		expect(url.searchParams.getAll("severity")).toEqual(["Critical", "High"])
		expect(url.searchParams.get("status")).toBe("OPEN")
	})

	it("sends nothing for an emptied severity selection", async () => {
		void alerts.getAlertsList({ filters: [{ type: "severity", value: [] }] })
		await vi.waitFor(() => expect(seen).toHaveLength(1))

		expect(new URL(seen[0], "http://x").searchParams.has("severity")).toBe(false)
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
	return { wrapper, filters: wrapper.findComponent(AlertsFilters), router }
}

describe("alertsFilters", () => {
	it("offers the five levels, most severe first, in a multi-select", async () => {
		const { wrapper, filters } = await mountFilters({ preset: [{ type: "severity", value: ["High", "Low"] }] })

		const select = wrapper.findComponent(NSelect)
		expect(select.props("multiple")).toBe(true)
		expect((select.props("options") as { value: string }[]).map(o => o.value)).toEqual([
			"Critical",
			"High",
			"Medium",
			"Low",
			"Informational"
		])
		expect(select.props("value")).toEqual(["High", "Low"])
		expect(filters.emitted("submit")?.[0]).toEqual([[{ type: "severity", value: ["High", "Low"] }]])
	})

	it("restores the filter from the URL, a single level as a list and unknown levels dropped", async () => {
		const { filters } = await mountFilters(
			{ useQueryString: true },
			{ severity: ["High", "Bogus"], status: "OPEN" }
		)
		expect(filters.emitted("submit")?.[0]).toEqual([
			[
				{ type: "severity", label: "Severity", value: ["High"] },
				{ type: "status", label: "Status", value: ["OPEN"] }
			]
		])

		const single = await mountFilters({ useQueryString: true }, { severity: "Low" })
		expect(single.filters.emitted("submit")?.[0]).toEqual([
			[{ type: "severity", label: "Severity", value: ["Low"] }]
		])
	})

	it("ignores a URL whose only severities are unknown", async () => {
		const { filters } = await mountFilters({ useQueryString: true }, { severity: "Bogus" })
		expect(filters.emitted("submit")).toBeUndefined()
	})

	it("removing the severity filter submits without it", async () => {
		const { wrapper, filters } = await mountFilters({
			preset: [
				{ type: "severity", value: ["Critical"] },
				{ type: "status", value: "OPEN" }
			]
		})

		// The delete button sits right after the severity select in its input group.
		const deleteButton = wrapper.findAll(".n-input-group")[0].findAll("button").at(-1)
		expect(deleteButton).toBeDefined()
		await deleteButton?.trigger("click")

		expect(filters.emitted("submit")?.at(-1)).toEqual([[{ type: "status", value: ["OPEN"] }]])
	})
})

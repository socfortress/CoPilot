import type { QueryState } from "../eventSearchMemory"
import type { EventSearchResult, EventSourceItem } from "@/types/siem"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { useAuthStore } from "@/stores/auth"
import EventColumnPicker from "../EventColumnPicker.vue"
import EventSearchQueries from "../EventSearchQueries.vue"
import List from "../List.vue"
import { resetEventSearchMemoryCache } from "../useEventSearchMemory"

const siem = vi.hoisted(() => ({ getEventSources: vi.fn(), getFieldMappings: vi.fn(), queryEvents: vi.fn() }))
const downloadCsv = vi.hoisted(() => vi.fn())
const stored = vi.hoisted(() => new Map<string, string>())

vi.mock("@/api", () => ({ default: { siem } }))
vi.mock("vue-router", async original => ({ ...(await original<typeof import("vue-router")>()), useRoute: () => ({ query: {} }) }))
vi.mock("@/utils/secure-storage", async original => ({
	...(await original<typeof import("@/utils/secure-storage")>()),
	secureLocalStorage: () => ({ getItem: (k: string) => stored.get(k) ?? null, setItem: (k: string, v: string) => stored.set(k, v) })
}))
vi.mock("@/utils", async original => ({ ...(await original<typeof import("@/utils")>()), downloadCsv }))

const SOURCES: EventSourceItem[] = [
	{
		id: 1,
		customer_code: "A",
		name: "Wazuh",
		index_pattern: "wazuh-*",
		event_type: "EDR",
		time_field: "timestamp",
		enabled: true,
		displayed_columns: null,
		created_at: "",
		updated_at: ""
	} as EventSourceItem
]

function event(n: number): EventSearchResult {
	return {
		_id: `e${n}`,
		timestamp: `2026-10-01T12:0${n}:00`,
		agent_name: `web-${n}`,
		rule_level: 5,
		rule_description: "Login"
	} as unknown as EventSearchResult
}

const STATE: QueryState = {
	sourceName: "Wazuh",
	query: "rule_level:>=10",
	timeMode: "relative",
	time: 7,
	unit: "d",
	timeFrom: null,
	timeTo: null,
	pageSize: 100
}

async function render() {
	const wrapper = mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(List)) }), {
		global: { stubs: { EventDetails: true } }
	})
	await flushPromises()
	return wrapper
}

function headers(wrapper: Awaited<ReturnType<typeof render>>) {
  return wrapper.findAll("[data-testid=event-results] thead th").map(th => th.text()).filter(Boolean)
}

describe("event search list (#1258)", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetEventSearchMemoryCache()
		stored.clear()
		vi.clearAllMocks()
		useAuthStore().$patch({ user: { username: "alice", role: "customer_user", customer_codes: ["A"] } as never })
		siem.getEventSources.mockResolvedValue({ data: { event_sources: SOURCES } })
		siem.getFieldMappings.mockResolvedValue({ data: { fields: [{ field: "agent_name", type: "keyword" }] } })
		siem.queryEvents.mockResolvedValue({ data: { events: [event(0), event(1)], total: 5, scroll_id: "s1" } })
	})

	it("runs a remembered search with its own query, time and page size, and lists it as recent", async () => {
		const wrapper = await render()
		wrapper.findComponent(EventSearchQueries).vm.$emit("restore", STATE)
		await flushPromises()

		// The query is the parent's model: read too early, it is still the old (empty) text.
		expect(siem.queryEvents).toHaveBeenCalledWith("A", "Wazuh", { page_size: 100, query: "rule_level:>=10", timerange: "7d" })
		const recent = JSON.parse(stored.get("event-search:alice:A")!).recent
		expect(recent).toHaveLength(1)
		expect(recent[0]).toMatchObject({ query: "rule_level:>=10", time: 7, unit: "d" })
	})

	it("refuses a remembered search whose source is gone", async () => {
		const wrapper = await render()
		wrapper.findComponent(EventSearchQueries).vm.$emit("restore", { ...STATE, sourceName: "Office" })
		await flushPromises()
		expect(siem.queryEvents).not.toHaveBeenCalled()
		expect(document.body.textContent).toContain("The source “Office” is no longer available")
	})

	it("exports the loaded events in the columns on screen, and says more are left", async () => {
		const wrapper = await render()
		wrapper.findComponent(EventSearchQueries).vm.$emit("restore", STATE)
		await flushPromises()

		expect(wrapper.find("[data-testid=event-results-count]").text()).toBe("2 of 5 events loaded")
		await wrapper.find("[data-testid=event-export]").trigger("click")
		const [filename, csvHeaders, rows] = downloadCsv.mock.calls[0]!
		expect(filename).toMatch(/^events-Wazuh-\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}\.csv$/)
		expect(csvHeaders).toEqual(["Timestamp", "Level", "Source", "Rule"])
		expect(rows).toEqual([
			["2026-10-01T12:00:00.000Z", "5", "web-0", "Login"],
			["2026-10-01T12:01:00.000Z", "5", "web-1", "Login"]
		])
		expect(document.body.textContent).toContain("Exported 2 of 5 events: load more to include the rest")
	})

	it("keeps the picked columns per source and uses them for the table and the export", async () => {
		const wrapper = await render()
		wrapper.findComponent(EventSearchQueries).vm.$emit("restore", STATE)
		await flushPromises()
		expect(headers(wrapper)).toEqual(["Timestamp", "Level", "Source", "Rule", "Actions"])

		await wrapper.find("[data-testid=event-columns-toggle]").trigger("click")
		const picker = wrapper.findComponent(EventColumnPicker)
		expect(picker.props("fields")).toEqual([{ field: "agent_name", type: "keyword" }])
		picker.vm.$emit("save", [
			{ key: "agent_name", label: "Host" },
			{ key: "timestamp", label: "When" }
		])
		await flushPromises()

		expect(headers(wrapper)).toEqual(["Host", "When", "Actions"])
		expect(JSON.parse(stored.get("event-search:alice:A")!).columns.Wazuh).toHaveLength(2)
		await wrapper.find("[data-testid=event-export]").trigger("click")
		expect(downloadCsv.mock.calls[0]![1]).toEqual(["Host", "When"])
		expect(downloadCsv.mock.calls[0]![2][0]).toEqual(["web-0", "2026-10-01T12:00:00.000Z"])

		await wrapper.find("[data-testid=event-columns-toggle]").trigger("click")
		wrapper.findComponent(EventColumnPicker).vm.$emit("save", null)
		await flushPromises()
		expect(headers(wrapper)).toEqual(["Timestamp", "Level", "Source", "Rule", "Actions"])
	})
})

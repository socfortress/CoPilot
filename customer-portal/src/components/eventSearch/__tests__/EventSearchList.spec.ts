import type {
	DisplayColumn,
	EventSearchColumnTemplate,
	EventSearchMemory,
	EventSearchResult,
	EventSearchState,
	EventSourceItem
} from "@/types/siem"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import { useAuthStore } from "@/stores/auth"
import EventColumnPicker from "../EventColumnPicker.vue"
import EventColumnTemplates from "../EventColumnTemplates.vue"
import EventSearchQueries from "../EventSearchQueries.vue"
import List from "../List.vue"
import { resetEventSearchMemory } from "../useEventSearchMemory"

/** The server's side of the memory, as the routes answer it: the whole memory every time. */
const server = vi.hoisted(() => ({
	memory: { saved: [], recent: [], columns: {}, templates: [] } as EventSearchMemory,
	failColumns: false
}))
const reply = () => Promise.resolve({ data: { success: true, message: "ok", ...structuredClone(server.memory) } })
const siem = vi.hoisted(() => ({
	getEventSources: vi.fn(),
	getFieldMappings: vi.fn(),
	queryEvents: vi.fn(),
	getEventSearchMemory: vi.fn(),
	saveEventSearchQuery: vi.fn(),
	deleteEventSearchQuery: vi.fn(),
	rememberEventSearch: vi.fn(),
	clearEventSearchRecent: vi.fn(),
	setEventSearchColumns: vi.fn(),
	saveEventSearchTemplate: vi.fn(),
	deleteEventSearchTemplate: vi.fn()
}))
const downloadCsv = vi.hoisted(() => vi.fn())

vi.mock("@/api", () => ({ default: { siem } }))
vi.mock("vue-router", async original => ({
	...(await original<typeof import("vue-router")>()),
	useRoute: () => ({ query: {} })
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

const STATE: EventSearchState = {
	source_name: "Wazuh",
	query: "rule_level:>=10",
	time_mode: "relative",
	time_amount: 7,
	time_unit: "d",
	time_from: null,
	time_to: null,
	page_size: 100
}

async function render() {
	const wrapper = mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(List)) }), {
		global: { stubs: { EventDetails: true } }
	})
	await flushPromises()
	return wrapper
}

function headers(wrapper: Awaited<ReturnType<typeof render>>) {
	return wrapper
		.findAll("[data-testid=event-results] thead th")
		.map(th => th.text())
		.filter(Boolean)
}

async function restore(wrapper: Awaited<ReturnType<typeof render>>, state: EventSearchState) {
	wrapper.findComponent(EventSearchQueries).vm.$emit("restore", state)
	await flushPromises()
}

describe("event search list (#1258)", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetEventSearchMemory()
		vi.clearAllMocks()
		server.memory = { saved: [], recent: [], columns: {}, templates: [] }
		server.failColumns = false
		useAuthStore().$patch({ user: { username: "alice", role: "customer_user", customer_codes: ["A"] } as never })
		siem.getEventSources.mockResolvedValue({ data: { event_sources: SOURCES } })
		siem.getFieldMappings.mockResolvedValue({ data: { fields: [{ field: "agent_name", type: "keyword" }] } })
		siem.queryEvents.mockResolvedValue({ data: { events: [event(0), event(1)], total: 5, scroll_id: "s1" } })
		siem.getEventSearchMemory.mockImplementation(reply)
		siem.rememberEventSearch.mockImplementation((_code: string, state: EventSearchState) => {
			server.memory.recent = [{ ...state, ran_at: "2026-10-15T09:00:00Z" }]
			return reply()
		})
		siem.saveEventSearchQuery.mockImplementation((_code: string, name: string, state: EventSearchState) => {
			server.memory.saved = [{ ...state, id: 1, name, updated_at: "2026-10-15T09:00:00Z" }]
			return reply()
		})
		siem.saveEventSearchTemplate.mockImplementation(
			(_code: string, source: string, name: string, columns: DisplayColumn[]) => {
				server.memory.templates = [{ id: 9, source_name: source, name, columns, updated_at: "" }]
				return reply()
			}
		)
		siem.deleteEventSearchTemplate.mockImplementation(() => {
			server.memory.templates = []
			return reply()
		})
		siem.setEventSearchColumns.mockImplementation(
			(_code: string, source: string, columns: DisplayColumn[] | null) => {
				if (server.failColumns) return Promise.reject(new Error("Network Error"))
				if (columns?.length) server.memory.columns = { [source]: columns }
				else server.memory.columns = {}
				return reply()
			}
		)
	})

	it("reads the user's memory from the server for the customer on screen", async () => {
		server.memory.saved = [{ ...STATE, id: 7, name: "High level", updated_at: "2026-10-15T09:00:00Z" }]
		const wrapper = await render()
		expect(siem.getEventSearchMemory).toHaveBeenCalledWith("A")
		expect(siem.getEventSearchMemory).toHaveBeenCalledTimes(1) // the form and the results share it
		expect(wrapper.findComponent(EventSearchQueries).props("saved")).toHaveLength(1)
	})

	it("runs a remembered search with its own query, time and page size, and records it on the server", async () => {
		const wrapper = await render()
		await restore(wrapper, STATE)

		// The query is the parent's model: read too early, it is still the old (empty) text.
		expect(siem.queryEvents).toHaveBeenCalledWith("A", "Wazuh", {
			page_size: 100,
			query: "rule_level:>=10",
			timerange: "7d"
		})
		expect(siem.rememberEventSearch).toHaveBeenCalledWith("A", STATE)
		expect(wrapper.findComponent(EventSearchQueries).props("recent")).toHaveLength(1)
	})

	it("runs an absolute range at the instants it was saved with", async () => {
		const wrapper = await render()
		await restore(wrapper, {
			...STATE,
			time_mode: "absolute",
			time_from: "2026-10-01T06:00:00Z",
			time_to: "2026-10-01T08:30:00Z"
		})
		expect(siem.queryEvents).toHaveBeenCalledWith("A", "Wazuh", {
			page_size: 100,
			query: "rule_level:>=10",
			time_from: "2026-10-01T06:00:00.000Z",
			time_to: "2026-10-01T08:30:00.000Z"
		})
		expect(siem.rememberEventSearch.mock.calls[0]![1]).toMatchObject({
			time_mode: "absolute",
			time_from: "2026-10-01T06:00:00.000Z",
			time_to: "2026-10-01T08:30:00.000Z"
		})
	})

	it("saves the search on screen under a name", async () => {
		const wrapper = await render()
		await restore(wrapper, STATE)
		wrapper.findComponent(EventSearchQueries).vm.$emit("save", "High level")
		await flushPromises()
		expect(siem.saveEventSearchQuery).toHaveBeenCalledWith("A", "High level", STATE)
		expect(document.body.textContent).toContain("Saved “High level”")
	})

	it("refuses a remembered search whose source is gone", async () => {
		const wrapper = await render()
		await restore(wrapper, { ...STATE, source_name: "Office" })
		expect(siem.queryEvents).not.toHaveBeenCalled()
		expect(document.body.textContent).toContain("The source “Office” is no longer available")
	})

	it("exports the loaded events in the columns on screen, and says more are left", async () => {
		const wrapper = await render()
		await restore(wrapper, STATE)

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

	it("keeps the picked columns on the server and uses them for the table and the export", async () => {
		const wrapper = await render()
		await restore(wrapper, STATE)
		expect(headers(wrapper)).toEqual(["Timestamp", "Level", "Source", "Rule", "Actions"])

		await wrapper.find("[data-testid=event-columns-toggle]").trigger("click")
		const picker = wrapper.findComponent(EventColumnPicker)
		expect(picker.props("fields")).toEqual([{ field: "agent_name", type: "keyword" }])
		const picked = [
			{ key: "agent_name", label: "Host" },
			{ key: "timestamp", label: "When" }
		]
		picker.vm.$emit("save", picked)
		await flushPromises()

		expect(siem.setEventSearchColumns).toHaveBeenCalledWith("A", "Wazuh", picked)
		expect(headers(wrapper)).toEqual(["Host", "When", "Actions"])
		expect(wrapper.findComponent(EventColumnPicker).exists()).toBe(false)
		await wrapper.find("[data-testid=event-export]").trigger("click")
		expect(downloadCsv.mock.calls[0]![1]).toEqual(["Host", "When"])
		expect(downloadCsv.mock.calls[0]![2][0]).toEqual(["web-0", "2026-10-01T12:00:00.000Z"])

		await wrapper.find("[data-testid=event-columns-toggle]").trigger("click")
		wrapper.findComponent(EventColumnPicker).vm.$emit("save", null)
		await flushPromises()
		expect(siem.setEventSearchColumns).toHaveBeenLastCalledWith("A", "Wazuh", null)
		expect(headers(wrapper)).toEqual(["Timestamp", "Level", "Source", "Rule", "Actions"])
	})

	it("keeps the dialog open, and the table as it was, when the columns could not be kept", async () => {
		const wrapper = await render()
		await restore(wrapper, STATE)
		server.failColumns = true
		await wrapper.find("[data-testid=event-columns-toggle]").trigger("click")
		wrapper.findComponent(EventColumnPicker).vm.$emit("save", [{ key: "agent_name", label: "Host" }])
		await flushPromises()
		expect(wrapper.findComponent(EventColumnPicker).exists()).toBe(true)
		expect(headers(wrapper)).toEqual(["Timestamp", "Level", "Source", "Rule", "Actions"])
		expect(document.body.textContent).toContain("Network Error")
	})

	it("switches between the source's layout and the user's templates, naming the one in force", async () => {
		const triage: EventSearchColumnTemplate = {
			id: 9,
			source_name: "Wazuh",
			name: "Triage",
			columns: [{ key: "agent_name", label: "Host" }],
			updated_at: ""
		}
		server.memory.templates = [triage, { ...triage, id: 10, source_name: "Office", name: "Elsewhere" }]
		const wrapper = await render()
		await restore(wrapper, STATE)
		const switcher = wrapper.findComponent(EventColumnTemplates)
		expect(switcher.props("templates")).toEqual([triage])
		expect(switcher.props("activeKey")).toBe("source")
		expect(switcher.props("sourceName")).toBe("Default layout")

		switcher.vm.$emit("apply", triage)
		await flushPromises()
		expect(siem.setEventSearchColumns).toHaveBeenCalledWith("A", "Wazuh", triage.columns)
		expect(headers(wrapper)).toEqual(["Host", "Actions"])
		expect(switcher.props("activeKey")).toBe("9")

		// Editing the columns afterwards leaves the template alone: the layout reads as custom.
		await wrapper.find("[data-testid=event-columns-toggle]").trigger("click")
		wrapper.findComponent(EventColumnPicker).vm.$emit("save", [{ key: "agent_name", label: "Agent" }])
		await flushPromises()
		expect(switcher.props("activeKey")).toBeNull()

		switcher.vm.$emit("apply", null)
		await flushPromises()
		expect(siem.setEventSearchColumns).toHaveBeenLastCalledWith("A", "Wazuh", null)
		expect(switcher.props("activeKey")).toBe("source")
	})

	it("deletes a template from the Layout menu, saying so", async () => {
		server.memory.templates = [
			{
				id: 9,
				source_name: "Wazuh",
				name: "Triage",
				columns: [{ key: "agent_name", label: "Host" }],
				updated_at: ""
			}
		]
		const wrapper = await render()
		await restore(wrapper, STATE)
		const switcher = wrapper.findComponent(EventColumnTemplates)
		switcher.vm.$emit("delete", 9)
		await flushPromises()
		expect(siem.deleteEventSearchTemplate).toHaveBeenCalledWith("A", 9)
		expect(switcher.props("templates")).toEqual([])
		expect(document.body.textContent).toContain("Deleted the template “Triage”")
	})

	it("saves and deletes templates from the column dialog", async () => {
		const wrapper = await render()
		await restore(wrapper, STATE)
		await wrapper.find("[data-testid=event-columns-toggle]").trigger("click")
		const picker = wrapper.findComponent(EventColumnPicker)
		picker.vm.$emit("saveTemplate", "Triage", [{ key: "agent_name", label: "Host" }])
		await flushPromises()
		expect(siem.saveEventSearchTemplate).toHaveBeenCalledWith("A", "Wazuh", "Triage", [
			{ key: "agent_name", label: "Host" }
		])
		expect(document.body.textContent).toContain("Saved the template “Triage”")
		expect(picker.props("templates")).toHaveLength(1)

		picker.vm.$emit("deleteTemplate", 9)
		await flushPromises()
		expect(siem.deleteEventSearchTemplate).toHaveBeenCalledWith("A", 9)
		expect(picker.props("templates")).toEqual([])
	})
})

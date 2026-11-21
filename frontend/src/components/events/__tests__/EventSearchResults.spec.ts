import type { VueWrapper } from "@vue/test-utils"
import type { EventSource } from "@/types/event-sources"
import type { EventSearchResult } from "@/types/events"
import { flushPromises, mount } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it } from "vitest"
import { createMemoryHistory, createRouter } from "vue-router"
import { routes } from "@/router/routes"
import EventSearchResults from "../EventSearchResults.vue"

/**
 * The results of Event Search across several sources (#1356): each event says which source
 * it came from, links to its page under that source, and the table carries every searched
 * source's columns. One source keeps the table it always had.
 */

function source(partial: Partial<EventSource> & Pick<EventSource, "name" | "index_pattern">): EventSource {
	return {
		id: 1,
		customer_code: "ACME",
		event_type: "Network Security",
		time_field: "timestamp",
		enabled: true,
		created_at: "2026-01-01T00:00:00Z",
		updated_at: "2026-01-01T00:00:00Z",
		displayed_columns: null,
		...partial
	}
}

const FIREWALL = source({
	name: "Firewall",
	index_pattern: "fortigate-acme*",
	displayed_columns: [
		{ key: "timestamp", label: "Time" },
		{ key: "src_ip", label: "Source IP" },
		{ key: "action", label: "Action" }
	]
})
const ROUTER = source({
	name: "Router",
	index_pattern: "mikrotik-acme*",
	displayed_columns: [
		{ key: "src_ip", label: "Client" },
		{ key: "interface", label: "Interface" }
	]
})
const EDR = source({ name: "Wazuh EDR", index_pattern: "wazuh-alerts-*", event_type: "EDR" })

const EVENTS: EventSearchResult[] = [
	{
		_id: "f1",
		_index: "fortigate-acme_0",
		_source_name: "Firewall",
		timestamp: "2026-11-20T10:00:00Z",
		src_ip: "10.0.0.5",
		action: "deny"
	},
	{
		_id: "m1",
		_index: "mikrotik-acme_0",
		_source_name: "Router",
		timestamp: "2026-11-20T09:59:00Z",
		src_ip: "10.0.0.5",
		interface: "ether1"
	}
]

let wrapper: VueWrapper | null = null

function current(): VueWrapper {
	if (!wrapper) throw new Error("render() first")
	return wrapper
}

async function render(eventSources: EventSource[], extra: Record<string, unknown> = {}) {
	const router = createRouter({ history: createMemoryHistory(), routes })
	wrapper = mount(EventSearchResults, {
		props: {
			events: EVENTS,
			totalEvents: 2,
			loadingEvents: false,
			loadingMore: false,
			hasSearched: true,
			scrollId: null,
			eventSources,
			customerCode: "ACME",
			...extra
		},
		global: { plugins: [router] },
		attachTo: document.body
	})
	await flushPromises()
	return wrapper
}

function headers() {
  return current()
		.findAll("th")
		.map(th => th.text().trim())
		.filter(Boolean)
}

/** Each row's cell texts, the actions column left out. */
function rows() {
  return current()
		.findAll("tbody tr")
		.map(tr =>
			tr
				.findAll("td")
				.map(td => td.text().trim())
				.slice(0, -1)
		)
}

function eventLinks() {
  return current()
		.findAll("tbody tr")
		.map(tr => tr.find("a[href]").attributes("href"))
}

function columnsButton() {
	const button = current()
		.findAll("button")
		.find(b => b.text().includes("Columns"))
	if (!button) throw new Error("Columns button not found")
	return button
}

beforeEach(() => {
	setActivePinia(createPinia())
})

afterEach(() => {
	wrapper?.unmount()
	wrapper = null
	document.body.innerHTML = ""
})

describe("event search results", () => {
	it("keeps one source's own columns, links and column settings", async () => {
		await render([FIREWALL])

		expect(headers()).toEqual(["Time", "Source IP", "Action"])
		expect(headers()).not.toContain("Event source")
		expect(eventLinks()).toEqual([
			"/event-search/ACME/Firewall/fortigate-acme_0/f1",
			"/event-search/ACME/Firewall/mikrotik-acme_0/m1"
		])
		expect(columnsButton().attributes("disabled")).toBeUndefined()
		expect(current().text()).not.toContain("sources")
	})

	it("names each event's source when several were searched", async () => {
		await render([FIREWALL, ROUTER])

		expect(headers().slice(0, 2)).toEqual(["Timestamp", "Event source"])
		expect(rows().map(cells => cells[1])).toEqual(["Firewall", "Router"])
		expect(current().text()).toContain("from 2 sources")
	})

	it("links each event to its page under its own source", async () => {
		await render([FIREWALL, ROUTER])

		expect(eventLinks()).toEqual([
			"/event-search/ACME/Firewall/fortigate-acme_0/f1",
			"/event-search/ACME/Router/mikrotik-acme_0/m1"
		])
	})

	it("carries every searched source's columns, each once, the first label winning", async () => {
		await render([FIREWALL, ROUTER])

		// Firewall's `timestamp` column is left out (the first column shows the time), and
		// Router's `src_ip` is the same column as Firewall's, under Firewall's label.
		expect(headers()).toEqual(["Timestamp", "Event source", "Source IP", "Action", "Interface"])
		expect(rows()[1].slice(2)).toEqual(["10.0.0.5", "-", "ether1"])
	})

	it("adds the default columns for a searched source with none configured", async () => {
		await render([ROUTER, EDR])

		expect(headers()).toEqual(["Timestamp", "Event source", "Client", "Interface", "Host", "Rule", "Level", "Summary"])
	})

	it("leaves column settings to one source at a time", async () => {
		await render([FIREWALL, ROUTER])

		expect(columnsButton().attributes("disabled")).toBeDefined()
		expect(columnsButton().attributes("title")).toContain("search one source")
	})

	it("shows an event with no source of its own without a link", async () => {
		await render([FIREWALL, ROUTER], {
			events: [{ _id: "x1", _index: "other_0", _source_name: null, timestamp: "2026-11-20T10:00:00Z" }],
			totalEvents: 1
		})

		expect(rows()[0][1]).toBe("-")
		expect(current().find("tbody a[href]").exists()).toBe(false)
	})

	it("says what the indexer reported about the results", async () => {
		await render([FIREWALL, ROUTER], {
			warnings: ["1 of 4 shards could not answer: the results may be incomplete"]
		})

		expect(current().text()).toContain("1 of 4 shards could not answer: the results may be incomplete")
	})
})

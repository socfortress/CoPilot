import type { QueryState } from "../eventSearchMemory"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it } from "vitest"
import { nextTick, ref } from "vue"
import { useAuthStore } from "@/stores/auth"
import {
	clearRecent,
	deleteQuery,
	describeTime,
	emptyMemory,
	memoryKey,
	normalizeMemory,
	RECENT_LIMIT,
	rememberRecent,
	sameQuery,
	SAVED_LIMIT,
	saveQuery,
	setColumns
} from "../eventSearchMemory"
import { resetEventSearchMemoryCache, useEventSearchMemory } from "../useEventSearchMemory"

const STATE: QueryState = {
	sourceName: "wazuh",
	query: "rule_level:>=10",
	timeMode: "relative",
	time: 24,
	unit: "h",
	timeFrom: null,
	timeTo: null,
	pageSize: 50
}

/** Saved and recent queries and the columns per source (#1258). */
describe("event search memory: saved queries", () => {
	it("saves a query under a trimmed name, newest first", () => {
		let memory = saveQuery(emptyMemory(), "  Logins  ", STATE, 1, () => "a").memory
		memory = saveQuery(memory, "Blocked", { ...STATE, query: "action:blocked" }, 2, () => "b").memory
		expect(memory.saved.map(s => [s.name, s.id, s.savedAt])).toEqual([
			["Blocked", "b", 2],
			["Logins", "a", 1]
		])
	})

	it("updates a query saved under the same name, whatever its case, instead of duplicating it", () => {
		const first = saveQuery(emptyMemory(), "Logins", STATE, 1, () => "a").memory
		const { memory, replaced } = saveQuery(first, "LOGINS", { ...STATE, query: "new" }, 2, () => "b")
		expect(replaced).toBe(true)
		expect(memory.saved).toHaveLength(1)
		expect(memory.saved[0]).toMatchObject({ id: "a", name: "LOGINS", query: "new", savedAt: 2 })
	})

	it("refuses a blank name, and keeps at most the limit", () => {
		expect(() => saveQuery(emptyMemory(), "   ", STATE, 1)).toThrow()
		let memory = emptyMemory()
		for (let n = 0; n < SAVED_LIMIT + 5; n++) memory = saveQuery(memory, `q${n}`, STATE, n).memory
		expect(memory.saved).toHaveLength(SAVED_LIMIT)
		expect(memory.saved[0]?.name).toBe(`q${SAVED_LIMIT + 4}`)
	})

	it("keeps an absolute range only for an absolute search", () => {
		const { memory } = saveQuery(emptyMemory(), "x", { ...STATE, timeFrom: 1, timeTo: 2 }, 1)
		expect([memory.saved[0]?.timeFrom, memory.saved[0]?.timeTo]).toEqual([null, null])
	})

	it("deletes one query by id", () => {
		const memory = saveQuery(emptyMemory(), "Logins", STATE, 1, () => "a").memory
		expect(deleteQuery(memory, "a").saved).toEqual([])
	})
})

describe("event search memory: recent queries", () => {
	it("puts the latest on top, once, and keeps at most the limit", () => {
		let memory = rememberRecent(emptyMemory(), STATE, 1)
		memory = rememberRecent(memory, { ...STATE, query: "other" }, 2)
		memory = rememberRecent(memory, { ...STATE, pageSize: 250 }, 3) // the same search again
		expect(memory.recent.map(r => [r.query, r.ranAt])).toEqual([
			["rule_level:>=10", 3],
			["other", 2]
		])
		for (let n = 0; n < RECENT_LIMIT + 3; n++) memory = rememberRecent(memory, { ...STATE, query: `q${n}` }, 10 + n)
		expect(memory.recent).toHaveLength(RECENT_LIMIT)
		expect(clearRecent(memory).recent).toEqual([])
	})

	it("tells searches apart by source, query and time, not by page size", () => {
		expect(sameQuery(STATE, { ...STATE, pageSize: 25, query: "  rule_level:>=10 " })).toBe(true)
		expect(sameQuery(STATE, { ...STATE, sourceName: "office365" })).toBe(false)
		expect(sameQuery(STATE, { ...STATE, time: 7, unit: "d" })).toBe(false)
		const absolute = { ...STATE, timeMode: "absolute" as const, timeFrom: 1, timeTo: 2 }
		expect(sameQuery(absolute, { ...absolute, timeTo: 3 })).toBe(false)
	})
})

describe("event search memory: columns", () => {
	it("keeps a source's columns, and an empty choice goes back to the source's layout", () => {
		let memory = setColumns(emptyMemory(), "wazuh", [{ key: "agent.name", label: " " }])
		expect(memory.columns.wazuh).toEqual([{ key: "agent.name", label: "agent.name" }])
		memory = setColumns(memory, "wazuh", [])
		expect(memory.columns).toEqual({})
	})
})

describe("event search memory: reading what was stored", () => {
	it("never breaks on broken or foreign data", () => {
		for (const raw of [null, undefined, "", "{not json", 42, [], { saved: "x" }]) {
			expect(normalizeMemory(raw)).toEqual(emptyMemory())
		}
	})

	it("keeps what still makes sense and drops the rest, from an object or its JSON", () => {
		const stored = {
			saved: [
				{ id: "a", name: "Logins", ...STATE },
				{ id: "b", name: "", ...STATE },
				{ id: "c", name: "No source", ...STATE, sourceName: "" },
				{ id: "d", name: "Half absolute", ...STATE, timeMode: "absolute", timeFrom: 1 }
			],
			recent: [{ ...STATE, unit: "y", time: -1, pageSize: "x" }],
			columns: { wazuh: [{ key: "agent.name" }, { label: "no key" }], broken: "x" }
		}
		for (const raw of [stored, JSON.stringify(stored)]) {
			const memory = normalizeMemory(raw)
			expect(memory.saved.map(s => s.id)).toEqual(["a"])
			expect(memory.recent[0]).toMatchObject({ unit: "h", time: 24, pageSize: 50 })
			expect(memory.columns).toEqual({ wazuh: [{ key: "agent.name", label: "agent.name" }] })
		}
	})

	it("describes a time range in words", () => {
		expect(describeTime(STATE, String)).toBe("last 24 hours")
		expect(describeTime({ ...STATE, time: 1, unit: "w" }, String)).toBe("last 1 week")
		expect(describeTime({ ...STATE, timeMode: "absolute", timeFrom: 1, timeTo: 2 }, n => `t${n}`)).toBe("t1 → t2")
	})
})

describe("useEventSearchMemory", () => {
	function storage() {
		const items = new Map<string, string>()
		return { items, getItem: (k: string) => items.get(k) ?? null, setItem: (k: string, v: string) => items.set(k, v) }
	}

	beforeEach(() => {
		setActivePinia(createPinia())
		resetEventSearchMemoryCache()
	})

	function signIn(username: string) {
		const store = useAuthStore()
		store.user = { username, role: "customer_user", customer_codes: [] } as unknown as typeof store.user
	}

	it("keeps one entry per user and customer: another user of the browser sees nothing", () => {
		const store = storage()
		signIn("alice")
		useEventSearchMemory("ACME", store).save("Logins", STATE)
		expect([...store.items.keys()]).toEqual([memoryKey("alice", "ACME")])

		resetEventSearchMemoryCache()
		signIn("bob")
		expect(useEventSearchMemory("ACME", store).memory.value.saved).toEqual([])
	})

	it("shares one state between the form and the results, and follows the customer", async () => {
		const store = storage()
		signIn("alice")
		const customer = ref("ACME")
		const form = useEventSearchMemory(customer, store)
		const results = useEventSearchMemory(customer, store)

		form.remember(STATE)
		results.setColumns("wazuh", [{ key: "agent.name", label: "Agent" }])
		expect(results.memory.value.recent).toHaveLength(1)
		expect(form.columnsFor("wazuh")).toEqual([{ key: "agent.name", label: "Agent" }])

		customer.value = "BETA"
		await nextTick()
		expect(form.memory.value.recent).toEqual([])
	})

	it("remembers nothing without a signed-in user or a customer", () => {
		const store = storage()
		const memory = useEventSearchMemory(null, store)
		memory.remember(STATE)
		expect(memory.available.value).toBe(false)
		expect(store.items.size).toBe(0)
	})
})

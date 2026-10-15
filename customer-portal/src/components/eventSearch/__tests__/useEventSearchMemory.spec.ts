import type { QueryState } from "../eventSearchMemory"
import type { MemoryStorage } from "../useEventSearchMemory"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it } from "vitest"
import { nextTick, ref } from "vue"
import { useAuthStore } from "@/stores/auth"
import { resetEventSearchMemoryCache, useEventSearchMemory } from "../useEventSearchMemory"

function fakeStorage(): MemoryStorage & { data: Map<string, string> } {
	const data = new Map<string, string>()
	return {
		data,
		getItem: key => data.get(key) ?? null,
		setItem: (key, value) => void data.set(key, value)
	}
}

function signIn(username: string | null) {
	const auth = useAuthStore()
	auth.$patch({ user: username ? ({ username, role: "customer_user", customer_codes: ["A", "B"] } as never) : null })
}

const STATE: QueryState = {
	sourceName: "Wazuh",
	query: "rule_level:>=10",
	timeMode: "relative",
	time: 24,
	unit: "h",
	timeFrom: null,
	timeTo: null,
	pageSize: 50
}

describe("useEventSearchMemory", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetEventSearchMemoryCache()
	})

	it("remembers nothing without a signed-in user or a customer", () => {
		const storage = fakeStorage()
		signIn(null)
		const memory = useEventSearchMemory("A", storage)
		expect(memory.available.value).toBe(false)
		memory.save("x", STATE)
		expect(storage.data.size).toBe(0)

		signIn("alice")
		expect(useEventSearchMemory(null, storage).available.value).toBe(false)
	})

	it("stores per user and customer, so another user of the browser never sees it", () => {
		const storage = fakeStorage()
		signIn("alice")
		useEventSearchMemory("A", storage).save("Mine", STATE)
		expect([...storage.data.keys()]).toEqual(["event-search:alice:A"])
		expect(useEventSearchMemory("B", storage).memory.value.saved).toEqual([])

		signIn("bob")
		expect(useEventSearchMemory("A", storage).memory.value.saved).toEqual([])
	})

	it("shares one state between the form and the results, and reads it back after a reload", () => {
		const storage = fakeStorage()
		signIn("alice")
		const form = useEventSearchMemory("A", storage)
		const results = useEventSearchMemory("A", storage)
		results.setColumns("Wazuh", [{ key: "agent_name", label: "Host" }])
		form.remember(STATE)
		expect(form.columnsFor("Wazuh")).toEqual([{ key: "agent_name", label: "Host" }])
		expect(results.memory.value.recent).toHaveLength(1)

		resetEventSearchMemoryCache()
		const reloaded = useEventSearchMemory("A", storage)
		expect(reloaded.memory.value.recent[0]?.query).toBe("rule_level:>=10")
		expect(reloaded.columnsFor("Wazuh")).toEqual([{ key: "agent_name", label: "Host" }])
		expect(reloaded.columnsFor("Office")).toBeNull()
	})

	it("follows the customer it is given", async () => {
		const storage = fakeStorage()
		signIn("alice")
		const code = ref<string | null>("A")
		const memory = useEventSearchMemory(code, storage)
		memory.save("On A", STATE)
		code.value = "B"
		await nextTick()
		expect(memory.memory.value.saved).toEqual([])
		code.value = "A"
		await nextTick()
		expect(memory.memory.value.saved.map(s => s.name)).toEqual(["On A"])
	})

	it("reports an update of a name already saved, and deletes by id", () => {
		const storage = fakeStorage()
		signIn("alice")
		const memory = useEventSearchMemory("A", storage)
		expect(memory.save("Mine", STATE)).toBe(false)
		expect(memory.save("MINE", { ...STATE, query: "other" })).toBe(true)
		expect(memory.memory.value.saved).toHaveLength(1)
		memory.remove(memory.memory.value.saved[0]!.id)
		expect(memory.memory.value.saved).toEqual([])
		expect(JSON.parse(storage.data.get("event-search:alice:A")!).saved).toEqual([])
	})

	it("tolerates broken stored data", () => {
		const storage = fakeStorage()
		storage.data.set("event-search:alice:A", "{not json")
		signIn("alice")
		expect(useEventSearchMemory("A", storage).memory.value).toEqual({ version: 1, saved: [], recent: [], columns: {} })
	})
})

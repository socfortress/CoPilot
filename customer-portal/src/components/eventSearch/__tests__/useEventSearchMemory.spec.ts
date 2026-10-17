import type { EventSearchMemory, EventSearchState } from "@/types/siem"
import { flushPromises } from "@vue/test-utils"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { nextTick, ref } from "vue"
import { useAuthStore } from "@/stores/auth"
import { resetEventSearchMemory, useEventSearchMemory } from "../useEventSearchMemory"

const siem = vi.hoisted(() => ({
	getEventSearchMemory: vi.fn(),
	saveEventSearchQuery: vi.fn(),
	deleteEventSearchQuery: vi.fn(),
	rememberEventSearch: vi.fn(),
	clearEventSearchRecent: vi.fn(),
	setEventSearchColumns: vi.fn(),
	saveEventSearchTemplate: vi.fn(),
	deleteEventSearchTemplate: vi.fn()
}))
vi.mock("@/api", () => ({ default: { siem } }))

const STATE: EventSearchState = {
	source_name: "Wazuh",
	query: "rule_level:>=10",
	time_mode: "relative",
	time_amount: 24,
	time_unit: "h",
	time_from: null,
	time_to: null,
	page_size: 50
}

function memory(names: string[] = [], extra: Partial<EventSearchMemory> = {}): EventSearchMemory {
	return {
		saved: names.map((name, i) => ({ ...STATE, id: i + 1, name, updated_at: "2026-10-01T00:00:00Z" })),
		recent: [],
		columns: {},
		templates: [],
		...extra
	}
}

const answer = (data: object) => Promise.resolve({ data: { success: true, message: "ok", ...data } })

function signIn(username: string | null) {
	useAuthStore().$patch({
		user: username ? ({ username, role: "customer_user", customer_codes: ["A", "B"] } as never) : null
	})
}

describe("useEventSearchMemory", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		resetEventSearchMemory()
		vi.clearAllMocks()
		siem.getEventSearchMemory.mockImplementation((code: string) => answer(memory([`on ${code}`])))
	})

	it("asks nothing and keeps nothing without a signed-in user or a customer", async () => {
		signIn(null)
		const noUser = useEventSearchMemory("A")
		await flushPromises()
		expect(noUser.available.value).toBe(false)
		expect(siem.getEventSearchMemory).not.toHaveBeenCalled()
		await expect(noUser.save("x", STATE)).rejects.toThrow("Select a customer first")

		signIn("alice")
		const noCustomer = useEventSearchMemory(null)
		await flushPromises()
		expect(noCustomer.available.value).toBe(false)
		// Only the first one asks, now that someone signed in.
		expect(siem.getEventSearchMemory).toHaveBeenCalledTimes(1)
		await expect(noCustomer.save("x", STATE)).rejects.toThrow("Select a customer first")
	})

	it("reads the memory once per user and customer, whoever asks", async () => {
		signIn("alice")
		const form = useEventSearchMemory("A")
		const results = useEventSearchMemory("A")
		expect(form.loading.value).toBe(true)
		await flushPromises()
		expect(siem.getEventSearchMemory).toHaveBeenCalledTimes(1)
		expect(form.memory.value.saved.map(q => q.name)).toEqual(["on A"])
		expect(results.memory.value).toBe(form.memory.value)
		expect(form.loading.value).toBe(false)
	})

	it("follows the customer it is given, and the user", async () => {
		signIn("alice")
		const code = ref<string | null>("A")
		const search = useEventSearchMemory(code)
		await flushPromises()
		code.value = "B"
		await flushPromises()
		expect(search.memory.value.saved.map(q => q.name)).toEqual(["on B"])
		code.value = "A"
		await flushPromises()
		expect(siem.getEventSearchMemory).toHaveBeenCalledTimes(2)

		signIn("bob")
		await nextTick()
		await flushPromises()
		expect(siem.getEventSearchMemory).toHaveBeenCalledTimes(3)
	})

	it("takes every write's answer as the memory, for every component", async () => {
		signIn("alice")
		const form = useEventSearchMemory("A")
		const results = useEventSearchMemory("A")
		await flushPromises()

		siem.saveEventSearchQuery.mockReturnValue(answer({ ...memory(["on A", "Mine"]), replaced: false }))
		expect(await form.save("Mine", STATE)).toBe(false)
		expect(siem.saveEventSearchQuery).toHaveBeenCalledWith("A", "Mine", STATE)
		expect(results.memory.value.saved.map(q => q.name)).toEqual(["on A", "Mine"])

		siem.saveEventSearchQuery.mockReturnValue(answer({ ...memory(["on A", "MINE"]), replaced: true }))
		expect(await form.save("MINE", STATE)).toBe(true)

		siem.setEventSearchColumns.mockReturnValue(
			answer(memory([], { columns: { Wazuh: [{ key: "agent_name", label: "Host" }] } }))
		)
		await results.setColumns("Wazuh", [{ key: "agent_name", label: "Host" }])
		expect(siem.setEventSearchColumns).toHaveBeenCalledWith("A", "Wazuh", [{ key: "agent_name", label: "Host" }])
		expect(form.columnsFor("Wazuh")).toEqual([{ key: "agent_name", label: "Host" }])
		expect(form.columnsFor("Office")).toBeNull()

		siem.deleteEventSearchQuery.mockReturnValue(answer(memory()))
		await form.remove(1)
		expect(siem.deleteEventSearchQuery).toHaveBeenCalledWith("A", 1)
		siem.clearEventSearchRecent.mockReturnValue(answer(memory()))
		await form.clearRecent()
		expect(siem.clearEventSearchRecent).toHaveBeenCalledWith("A")
		expect(results.memory.value.saved).toEqual([])
	})

	it("lists a source's templates, and saves and deletes them", async () => {
		signIn("alice")
		const triage = {
			id: 3,
			source_name: "Wazuh",
			name: "Triage",
			columns: [{ key: "agent_name", label: "Host" }],
			updated_at: ""
		}
		const office = { ...triage, id: 4, source_name: "Office" }
		siem.getEventSearchMemory.mockImplementation(() => answer(memory([], { templates: [triage, office] })))
		const search = useEventSearchMemory("A")
		await flushPromises()
		expect(search.templatesFor("Wazuh")).toEqual([triage])
		expect(search.templatesFor(null)).toEqual([])

		siem.saveEventSearchTemplate.mockReturnValue(answer({ ...memory([], { templates: [office] }), replaced: true }))
		expect(await search.saveTemplate("Wazuh", "Triage", triage.columns)).toBe(true)
		expect(siem.saveEventSearchTemplate).toHaveBeenCalledWith("A", "Wazuh", "Triage", triage.columns)
		expect(search.templatesFor("Wazuh")).toEqual([])

		siem.deleteEventSearchTemplate.mockReturnValue(answer(memory()))
		await search.removeTemplate(4)
		expect(siem.deleteEventSearchTemplate).toHaveBeenCalledWith("A", 4)
		expect(search.memory.value.templates).toEqual([])
	})

	it("drops an answer that arrives after a newer one", async () => {
		signIn("alice")
		const search = useEventSearchMemory("A")
		await flushPromises()
		let slow: (value: unknown) => void = () => {}
		siem.rememberEventSearch.mockReturnValue(new Promise(resolve => (slow = resolve)))
		siem.saveEventSearchQuery.mockReturnValue(answer({ ...memory(["newer"]), replaced: false }))

		const remembering = search.remember(STATE)
		await search.save("newer", STATE)
		slow({ data: { success: true, message: "ok", ...memory(["older"]) } })
		await remembering
		expect(search.memory.value.saved.map(q => q.name)).toEqual(["newer"])
	})

	it("never fails a search because it could not be recorded", async () => {
		signIn("alice")
		const warn = vi.spyOn(console, "warn").mockImplementation(() => {})
		const search = useEventSearchMemory("A")
		await flushPromises()
		siem.rememberEventSearch.mockRejectedValue(new Error("offline"))
		await expect(search.remember(STATE)).resolves.toBeUndefined()
		expect(warn).toHaveBeenCalled()
		warn.mockRestore()
	})

	it("says why the memory could not be read, and reads it again on request", async () => {
		signIn("alice")
		siem.getEventSearchMemory.mockRejectedValueOnce({ response: { data: { message: "Database unavailable" } } })
		const search = useEventSearchMemory("A")
		await flushPromises()
		expect(search.error.value).toBe("Database unavailable.")
		await search.reload()
		expect(search.error.value).toBeNull()
		expect(search.memory.value.saved.map(q => q.name)).toEqual(["on A"])
	})

	it("forgets everything on logout, so the next user reads their own", async () => {
		signIn("alice")
		useEventSearchMemory("A")
		await flushPromises()
		resetEventSearchMemory()
		useEventSearchMemory("A")
		await flushPromises()
		expect(siem.getEventSearchMemory).toHaveBeenCalledTimes(2)
	})
})

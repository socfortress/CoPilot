/** The pinned sections, per user, and the hidden rail, per browser (#1325): localStorage only. */
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { nextTick } from "vue"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import { MAX_PINNED, PINNED_KEY_PREFIX, RAIL_HIDDEN_KEY, useSectionPreferences } from "../useSectionPreferences"

function signInAs(username: string) {
	useAuthStore().user = { access_token: "t", username, email: "", role: AuthUserRole.Analyst }
}

beforeEach(() => {
	setActivePinia(createPinia())
	localStorage.clear()
	signInAs("ana")
})

afterEach(() => {
	vi.restoreAllMocks()
})

describe("pinned sections", () => {
	it("are kept per user", async () => {
		const prefs = useSectionPreferences()
		prefs.togglePin("Event Sources")
		prefs.togglePin("SLA")
		expect(prefs.pinned.value).toEqual(["Event Sources", "SLA"])
		expect(prefs.isPinned("SLA")).toBe(true)
		expect(JSON.parse(localStorage.getItem(`${PINNED_KEY_PREFIX}ana`) ?? "")).toEqual(["Event Sources", "SLA"])
		prefs.togglePin("Event Sources")
		expect(prefs.pinned.value).toEqual(["SLA"])

		signInAs("bob")
		await nextTick()
		expect(prefs.pinned.value).toEqual([])
		signInAs("ana")
		await nextTick()
		expect(prefs.pinned.value).toEqual(["SLA"])
	})

	it("drop what is no section, duplicates and anything past the limit", () => {
		localStorage.setItem(
			`${PINNED_KEY_PREFIX}ana`,
			JSON.stringify(["SLA", "SLA", "nope", 3, ...Array.from({ length: 20 }).fill("WAF"), "Info"])
		)
		expect(useSectionPreferences().pinned.value).toEqual(["SLA", "WAF", "Info"])
		localStorage.setItem(`${PINNED_KEY_PREFIX}ana`, "{not json")
		expect(useSectionPreferences().pinned.value).toEqual([])
	})

	it("keep the newest when the limit is reached", () => {
		const prefs = useSectionPreferences()
		const ids = ["Info", "Provision", "Security", "Agents", "Deploy Agent", "Healthcheck Wazuh", "WAF", "SLA"] as const
		const more = ["Activity", "Exposure", "Audit Log", "AI Report", "Ask the SOC"] as const
		for (const id of [...ids, ...more]) prefs.togglePin(id)
		expect(prefs.pinned.value).toHaveLength(MAX_PINNED)
		expect(prefs.pinned.value[0]).toBe("Provision")
		expect(prefs.pinned.value.at(-1)).toBe("Ask the SOC")
	})

	it("still work for the page when storage refuses them", () => {
		vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
			throw new Error("blocked")
		})
		vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
			throw new Error("blocked")
		})
		const prefs = useSectionPreferences()
		expect(prefs.pinned.value).toEqual([])
		prefs.togglePin("SLA")
		expect(prefs.isPinned("SLA")).toBe(true)
		expect(prefs.railHidden.value).toBe(false)
		prefs.setRailHidden(true)
		expect(prefs.railHidden.value).toBe(true)
	})
})

describe("the hidden rail", () => {
	it("is remembered for the browser, not the user", () => {
		useSectionPreferences().setRailHidden(true)
		expect(localStorage.getItem(RAIL_HIDDEN_KEY)).toBe("true")
		signInAs("bob")
		expect(useSectionPreferences().railHidden.value).toBe(true)
	})
})

import type { PolicyMatrix } from "@/types/soc-management"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, ref } from "vue"
import { useAuthStore } from "@/stores/auth"
import { AuthUserRole } from "@/types/auth"
import PoliciesTab from "../tabs/PoliciesTab.vue"
import { CALENDAR, POLICY } from "./fixtures"

const api = {
	getPolicy: vi.fn(),
	getPolicyOverrides: vi.fn(),
	savePolicy: vi.fn(),
	deletePolicyOverride: vi.fn(),
	getCalendar: vi.fn(),
	saveCalendar: vi.fn(),
	deleteCalendar: vi.fn()
}
vi.mock("@/api", () => ({
	default: {
		socManagement: new Proxy(
			{},
			{ get: (_, name: string) => (...args: unknown[]) => api[name as keyof typeof api](...args) }
		)
	}
}))
vi.mock("@/composables/useCustomerOptions", () => ({
	useCustomerOptions: () => ({
		options: ref([
			{ label: "Acme Corp (ACME)", value: "ACME" },
			{ label: "Globex (GLOBEX)", value: "GLOBEX" },
			{ label: "Initech (INITECH)", value: "INITECH" }
		]),
		loading: ref(false),
		load: vi.fn()
	})
}))

function acmeMatrix(): PolicyMatrix {
	return {
		customer_code: "ACME",
		cells: POLICY.cells.map(cell =>
			cell.entity === "alert" && cell.severity === "Critical" ? { ...cell, ack_minutes: 5, source: "customer" } : cell
		)
	}
}

async function tab(role = AuthUserRole.Admin) {
	useAuthStore().user.role = role
	const wrapper = mount(
		defineComponent({ setup: () => () => h(NMessageProvider, null, { default: () => h(PoliciesTab) }) })
	)
	await flushPromises()
	return wrapper
}

beforeEach(() => {
	setActivePinia(createPinia())
	for (const mock of Object.values(api)) mock.mockReset()
	api.getPolicy.mockImplementation((code: string | null) => Promise.resolve({ data: { policy: code ? acmeMatrix() : POLICY } }))
	api.getPolicyOverrides.mockResolvedValue({
		data: { overrides: [{ customer_code: "ACME", cells: 1, updated_at: null, updated_by: "admin" }] }
	})
	api.getCalendar.mockResolvedValue({ data: { calendar: CALENDAR, customers_with_calendar: ["GLOBEX"], retargeted: 0 } })
})

describe("policiesTab", () => {
	it("lists the global scope first, then customers with overrides, marking overrides and own calendars", async () => {
		const wrapper = await tab()
		const scopes = wrapper.findAll("[data-testid^=policy-scope-]").filter(el => !el.attributes("data-testid")?.includes("calendar"))
		expect(scopes.map(el => el.attributes("data-testid"))).toEqual([
			"policy-scope-global",
			"policy-scope-ACME",
			"policy-scope-GLOBEX",
			"policy-scope-INITECH"
		])
		expect(wrapper.get("[data-testid=policy-scope-ACME]").text()).toContain("1 override")
		expect(wrapper.find("[data-testid=policy-scope-calendar-GLOBEX]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=policy-scope-calendar-ACME]").exists()).toBe(false)
		// A long customer list scrolls inside the panel, in Naive's scrollbar.
		const scroll = wrapper.get("[data-testid=policy-scopes]")
		expect(scroll.classes()).toContain("n-scrollbar")
		expect(scroll.find("[data-testid=policy-scope-INITECH]").exists()).toBe(true)
	})

	it("loads a customer's matrix and calendar when its scope is picked", async () => {
		const wrapper = await tab()
		await wrapper.get("[data-testid=policy-scope-ACME]").trigger("click")
		await flushPromises()
		expect(api.getPolicy).toHaveBeenLastCalledWith("ACME")
		expect(api.getCalendar).toHaveBeenLastCalledWith("ACME")
		expect(wrapper.get("[data-testid=policy-own-alert-Critical]").text()).toContain("Override")
		expect(wrapper.find("[data-testid=policy-remove-override]").exists()).toBe(true)
	})

	it("saves the whole matrix with the edited cell, and only when something changed", async () => {
		api.savePolicy.mockResolvedValue({ data: { policy: POLICY, retargeted: 0, message: "Saved the global policy" } })
		const wrapper = await tab()
		const save = wrapper.get("[data-testid=policy-save]")
		expect(save.attributes("disabled")).toBeDefined()
		await wrapper.get("[data-testid=policy-own-case-Low]").trigger("click")
		await wrapper.get("[data-testid=policy-hours-case-Low]").trigger("click")
		await wrapper.get("[data-testid=policy-apply-open]").trigger("click")
		await save.trigger("click")
		await flushPromises()
		const payload = api.savePolicy.mock.calls[0][0]
		expect(payload).toMatchObject({ customer_code: null, apply_to_open: true })
		expect(payload.cells).toHaveLength(10)
		expect(payload.cells.find((c: { entity: string; severity: string }) => c.entity === "case" && c.severity === "Low")).toEqual({
			entity: "case",
			severity: "Low",
			inherit: false,
			ack_minutes: 60,
			resolve_minutes: 480,
			business_hours: true
		})
	})

	it("is read-only for analysts, calendar included", async () => {
		const wrapper = await tab(AuthUserRole.Analyst)
		expect(wrapper.find("[data-testid=policy-readonly]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=policy-save]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=calendar-save]").exists()).toBe(false)
	})

	it("says when the policy could not be loaded", async () => {
		api.getPolicy.mockImplementation(() => Promise.reject(Object.assign(new Error("boom"), { response: { data: { detail: "denied" } } })))
		const wrapper = await tab()
		expect(wrapper.text()).toContain("Could not load the policy: denied")
	})
})

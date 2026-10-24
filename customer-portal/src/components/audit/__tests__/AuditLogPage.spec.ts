import type { AuditEntry, AuditLog } from "@/types/audit"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { createPinia, setActivePinia } from "pinia"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, reactive } from "vue"
import { useAuditAvailability } from "@/composables/common/useAuditAvailability"
import AuditLogPage from "../AuditLogPage.vue"

const audit = vi.hoisted(() => ({ getAvailability: vi.fn(), getLog: vi.fn(), exportLog: vi.fn() }))
vi.mock("@/api", () => ({ default: { audit } }))
const saveAs = vi.hoisted(() => vi.fn())
vi.mock("file-saver", () => ({ saveAs }))
// The details the modal shows, as their ids: what the page hands them is what is tested here.
vi.mock("@/components/alerts/AlertDetails", async () => {
	const { defineComponent, h } = await import("vue")
	return {
		default: defineComponent({
			props: { alertId: { type: Number, required: true } },
			setup: props => () => h("div", { "data-testid": "modal-alert" }, `alert ${props.alertId}`)
		})
	}
})
vi.mock("@/components/cases/CaseDetails", async () => {
	const { defineComponent, h } = await import("vue")
	return {
		default: defineComponent({
			props: { caseId: { type: Number, required: true } },
			setup: props => () => h("div", { "data-testid": "modal-case" }, `case ${props.caseId}`)
		})
	}
})

const route = vi.hoisted(() => ({ query: {} as Record<string, string> }))
const replace = vi.hoisted(() => vi.fn())
const push = vi.hoisted(() => vi.fn())
vi.mock("vue-router", async () => {
	const { defineComponent, h } = await import("vue")
	const RouterLink = defineComponent({
		props: { to: { type: Object, required: true } },
		setup: (props, { slots, attrs }) => () =>
			h("a", { ...attrs, "data-to": (props.to as { name: string }).name }, slots.default?.())
	})
	return {
		useRoute: () => route,
		useRouter: () => ({ replace, push, resolve: (to: { name: string }) => ({ href: `/${to.name}` }) }),
		RouterLink
	}
})

const ACME = { customer_code: "ACME", customer_name: "Acme Rome" }
const BETA = { customer_code: "BETA", customer_name: "Beta Milan" }

function entry(id: number, extra: Partial<AuditEntry> = {}): AuditEntry {
	return {
		id,
		timestamp: "2026-10-01T12:00:00Z",
		action: "alert.status_change",
		label: "Alert status changed",
		category: "alerts",
		actor: { kind: "member", username: "jane" },
		customer_code: "ACME",
		target: { type: "alert", id: "7", label: null },
		from_value: "OPEN",
		to_value: "PENDING_CUSTOMER",
		result: "success",
		source_ip: "203.0.113.7",
		...extra
	}
}

function log(extra: Partial<AuditLog> = {}): { data: AuditLog } {
	return {
		data: {
			entries: [
				entry(3),
				entry(2, {
					action: "case.create",
					label: "Case opened",
					category: "cases",
					actor: { kind: "soc", username: null },
					target: { type: "case", id: "4", label: "Ransomware" },
					from_value: null,
					to_value: null,
					source_ip: null
				}),
				entry(1, {
					action: "auth.login_failed",
					label: "Sign-in failed",
					category: "account",
					actor: { kind: "unknown", username: null },
					target: { type: "user", id: "jane", label: "jane" },
					from_value: null,
					to_value: null,
					result: "failure",
					source_ip: null
				})
			],
			total: 3,
			page: 1,
			page_size: 25,
			retention_days: 90,
			members: [
				{ id: 10, username: "boss" },
				{ id: 11, username: "jane" }
			],
			...extra
		}
	}
}

function render() {
	const reactiveRoute = reactive(route)
	Object.assign(route, reactiveRoute)
	return mount(defineComponent({ setup: () => () => h(NMessageProvider, null, () => h(AuditLogPage)) }), {
		attachTo: document.body
	})
}

beforeEach(() => {
	setActivePinia(createPinia())
	for (const fn of Object.values(audit)) fn.mockReset()
	saveAs.mockReset()
	replace.mockReset()
	push.mockReset()
	route.query = {}
	useAuditAvailability().reset()
	audit.getAvailability.mockResolvedValue({ data: { available: true, customers: [ACME] } })
	audit.getLog.mockResolvedValue(log())
})

afterEach(() => {
	document.body.innerHTML = ""
})

/** A customer admin's Audit Log page (#1298). */
describe("the audit log", () => {
	it("lists the entries newest first, the SOC as SOC, the customer's users by name", async () => {
		const wrapper = render()
		await flushPromises()
		const rows = wrapper.findAll("[data-testid=audit-row]")
		expect(rows.map(r => r.attributes("data-action"))).toEqual(["alert.status_change", "case.create", "auth.login_failed"])
		expect(rows.map(r => r.get("[data-testid=audit-actor]").text())).toEqual(["jane", "SOC", "Unknown"])
		expect(rows[0]?.get("[data-testid=audit-change]").text()).toBe("Open → Waiting on you")
		expect(rows[0]?.get("[data-testid=audit-ip]").text()).toBe("203.0.113.7")
		expect(rows[1]?.find("[data-testid=audit-ip]").exists()).toBe(false)
		expect(rows[2]?.find("[data-testid=audit-failure]").exists()).toBe(true)
		expect(wrapper.get("[data-testid=audit-total]").text()).toContain("3 entries")
		expect(wrapper.get("[data-testid=audit-total]").text()).toContain("Kept for 90 days")
	})

	it("opens an alert or a case in its modal instead of leaving the page, a user nowhere", async () => {
		const wrapper = render()
		await flushPromises()
		const targets = wrapper.findAll("[data-testid=audit-target]")
		expect(targets.map(t => [t.element.tagName, t.text()])).toEqual([
			["BUTTON", "Alert #7"],
			["BUTTON", "Case #4 · Ransomware"],
			["SPAN", "jane"]
		])

		await targets[0]!.trigger("click")
		await flushPromises()
		expect(push).not.toHaveBeenCalled()
		expect(document.body.querySelector(".n-card-header")?.textContent).toContain("Alert Details")
		expect(document.body.querySelector("[data-testid=modal-alert]")?.textContent).toBe("alert 7")

		await targets[1]!.trigger("click")
		await flushPromises()
		expect(document.body.querySelector("[data-testid=modal-case]")?.textContent).toBe("case 4")
		expect(document.body.querySelector("[data-testid=modal-alert]")).toBeNull()
	})

	it("leads from the modal's header to the entity's page", async () => {
		const wrapper = render()
		await flushPromises()
		await wrapper.findAll("[data-testid=audit-target]")[1]!.trigger("click")
		await flushPromises()
		;(document.body.querySelector("[data-testid=entity-modal-page]") as HTMLButtonElement).click()
		await flushPromises()
		expect(push).toHaveBeenCalledWith({ name: "CaseDetails", params: { id: "4" } })
	})

	it("asks the API for what the URL says", async () => {
		route.query = { category: "cases", user: "11", from: "2026-10-01", to: "2026-10-01", page: "2" }
		render()
		await flushPromises()
		const [query, codes] = audit.getLog.mock.calls[0] ?? []
		expect(query).toMatchObject({
			category: "cases",
			userId: 11,
			since: new Date(2026, 9, 1).toISOString(),
			until: new Date(2026, 9, 2).toISOString(),
			page: 2,
			pageSize: 25
		})
		expect(codes).toBeUndefined()
	})

	it("writes a filter into the URL, back to the first page", async () => {
		route.query = { page: "3", keep: "me" }
		const wrapper = render()
		await flushPromises()
		const select = wrapper.getComponent({ name: "Select" })
		select.vm.$emit("update:value", "account")
		expect(replace).toHaveBeenCalledWith({ query: { keep: "me", category: "account" } })
	})

	it("offers a customer filter only to an admin of several customers, and names their customers", async () => {
		const single = render()
		await flushPromises()
		expect(single.find("[data-testid=audit-filter-customer]").exists()).toBe(false)
		expect(single.find("[data-testid=audit-customer]").exists()).toBe(false)
		single.unmount()

		useAuditAvailability().reset()
		audit.getAvailability.mockResolvedValue({ data: { available: true, customers: [ACME, BETA] } })
		route.query = { customer: "BETA" }
		const several = render()
		await flushPromises()
		expect(several.find("[data-testid=audit-filter-customer]").exists()).toBe(true)
		expect(several.get("[data-testid=audit-customer]").text()).toBe("Acme Rome")
		expect(audit.getLog.mock.calls.at(-1)?.[1]).toEqual(["BETA"])
	})

	it("says it isn't theirs on a 403", async () => {
		audit.getLog.mockRejectedValue({ response: { status: 403, data: { detail: "no" } } })
		const wrapper = render()
		await flushPromises()
		expect(wrapper.find("[data-testid=audit-forbidden]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=audit-row]").exists()).toBe(false)
	})

	it("drops a user filter the API doesn't know (404)", async () => {
		route.query = { user: "99", category: "users" }
		audit.getLog.mockRejectedValue({ response: { status: 404, data: { detail: "User not found" } } })
		render()
		await flushPromises()
		expect(replace).toHaveBeenCalledWith({ query: { category: "users" } })
	})

	it("says when nothing matches the filters", async () => {
		route.query = { category: "reports" }
		audit.getLog.mockResolvedValue(log({ entries: [], total: 0 }))
		const wrapper = render()
		await flushPromises()
		expect(wrapper.get("[data-testid=audit-empty]").text()).toContain("Nothing matches these filters")
		expect(wrapper.get("[data-testid=audit-export]").attributes("disabled")).toBeDefined()
	})

	it("exports the filtered log and warns when it was cut", async () => {
		route.query = { category: "account" }
		audit.exportLog.mockResolvedValue({ data: new Blob(["x"]), headers: { "x-export-truncated": "true" } })
		const wrapper = render()
		await flushPromises()
		await wrapper.get("[data-testid=audit-export]").trigger("click")
		await flushPromises()
		expect(audit.exportLog.mock.calls[0]?.[0]).toMatchObject({ category: "account" })
		expect(saveAs).toHaveBeenCalledTimes(1)
		expect(saveAs.mock.calls[0]?.[1]).toMatch(/^audit-log-\d{8}-\d{4}\.csv$/)
		expect(document.body.textContent).toContain("newest 10,000 entries")
	})
})

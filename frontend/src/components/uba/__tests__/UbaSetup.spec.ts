import type { UbaProvisioning } from "@/types/uba"
import { flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import UbaSetup from "../UbaSetup.vue"

const getProvisioning = vi.fn()
const provision = vi.fn()
const getRollbacks = vi.fn()
const setMode = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		uba: {
			getProvisioning: (...args: unknown[]) => getProvisioning(...args),
			provision: (...args: unknown[]) => provision(...args),
			getRollbacks: (...args: unknown[]) => getRollbacks(...args),
			setMode: (...args: unknown[]) => setMode(...args)
		}
	}
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "yyyy-MM-dd HH:mm" } }) }))
vi.mock("naive-ui", async original => ({
	...(await original<typeof import("naive-ui")>()),
	useMessage: () => ({ success: vi.fn(), error: vi.fn() })
}))

const NOT_SET_UP: UbaProvisioning = {
	sources: { WAZUH: 1, O365: 2 },
	office365_tenants: ["aaaaaaaa-0000-4000-8000-000000000001", "aaaaaaaa-0000-4000-8000-000000000002"],
	problem: null,
	onboarding: null
}

function onboarding(status: string, extra = {}) {
	return {
		tenant: "acme",
		name: "Acme",
		status,
		active: true,
		bootstrap_days: 14,
		bootstrap_since: null,
		bootstrap_cursor: null,
		bootstrap_docs: 0,
		bootstrap_error: null,
		bootstrapped_until: null,
		office365_organization_ids: [],
		indices: {},
		...extra
	}
}

async function render() {
	const wrapper = mount(UbaSetup, { props: { customerCode: "acme" } })
	await flushPromises()
	return wrapper
}

describe("ubaSetup", () => {
	beforeEach(() => {
		auth.isAdmin = true
		getProvisioning.mockReset().mockResolvedValue({ data: NOT_SET_UP })
		getRollbacks.mockReset().mockResolvedValue({ data: { rollbacks: [] } })
		setMode.mockReset()
		provision.mockReset().mockResolvedValue({
			data: {
				steps: [{ step: "UBA tenant", status: "registered", detail: "pending" }],
				onboarding: onboarding("pending")
			}
		})
	})
	afterEach(() => {
		vi.useRealTimers()
	})

	it("says what it will create and sets the customer up with the chosen history", async () => {
		const wrapper = await render()
		const text = wrapper.text()
		expect(getProvisioning).toHaveBeenCalledWith("acme")
		expect(text).toContain("Wazuh and Microsoft 365 (2 tenants)")
		expect(text).not.toMatch(/\s[,.:;)]/) // no space before punctuation

		getProvisioning.mockResolvedValue({ data: { ...NOT_SET_UP, onboarding: onboarding("pending") } })
		const button = wrapper.findAll("button").find(b => b.text() === "Set up UBA")
		expect(button).toBeDefined()
		await button?.trigger("click")
		await flushPromises()
		expect(provision).toHaveBeenCalledWith("acme", { bootstrap_days: 14, deploy_wazuh_rules: false })
		expect(wrapper.text()).toContain("registered")
		expect(wrapper.text()).toContain("UBA starts replaying history within a minute")
		expect(wrapper.text()).toContain("Run setup again")
	})

	it("warns before deploying Wazuh rules", async () => {
		const wrapper = await render()
		expect(wrapper.text()).not.toContain("restarts the Wazuh manager")
		await wrapper.find("[role=checkbox]").trigger("click")
		expect(wrapper.text()).toContain("restarts the Wazuh manager")
	})

	it("shows the replay's progress and its error, and tells the page when the customer is live", async () => {
		vi.useFakeTimers({ toFake: ["setInterval", "clearInterval"] })
		getProvisioning.mockResolvedValue({
			data: {
				...NOT_SET_UP,
				onboarding: onboarding("error", {
					bootstrap_since: "2026-09-17T00:00:00Z",
					bootstrap_cursor: "2026-09-20T00:00:00Z",
					bootstrap_docs: 120000,
					bootstrap_error: "ConnectionError: indexer unreachable"
				})
			}
		})
		const wrapper = await render()
		expect(wrapper.text()).toContain("120,000 events")
		expect(wrapper.text()).toContain("indexer unreachable")

		getProvisioning.mockResolvedValue({ data: { ...NOT_SET_UP, onboarding: onboarding("live") } })
		vi.advanceTimersByTime(15000)
		await flushPromises()
		expect(wrapper.emitted("live")).toHaveLength(1)
	})

	it("runs again for a live customer, keeping its history setting, e.g. after Microsoft 365 is added", async () => {
		getProvisioning.mockResolvedValue({
			data: { ...NOT_SET_UP, onboarding: onboarding("live", { bootstrap_days: 7 }) }
		})
		const wrapper = mount(UbaSetup, { props: { customerCode: "acme", closable: true } })
		await flushPromises()
		const text = wrapper.text()
		expect(text).toContain("UBA setup for this customer")
		expect(text).toContain("UBA reads Wazuh and Microsoft 365 (2 tenants) for this customer")
		expect(text).toContain("run setup again so UBA reads the new streams too")
		expect(text).not.toContain("History to learn from") // a live customer is never replayed again
		expect(text).not.toMatch(/\s[,.:;)]/)

		const again = wrapper.findAll("button").find(b => b.text() === "Run setup again")
		expect(again).toBeDefined()
		await again?.trigger("click")
		await flushPromises()
		expect(provision).toHaveBeenCalledWith("acme", { bootstrap_days: 7, deploy_wazuh_rules: false })

		await wrapper.findAll("button").find(b => b.text() === "Close")?.trigger("click")
		expect(wrapper.emitted("close")).toHaveLength(1)
	})

	it("names the problem instead of offering setup", async () => {
		getProvisioning.mockResolvedValue({
			data: { ...NOT_SET_UP, sources: {}, problem: "Customer acme has no Wazuh stream on record" }
		})
		const wrapper = await render()
		expect(wrapper.text()).toContain("no Wazuh stream on record")
		expect(wrapper.findAll("button").some(b => b.text() === "Set up UBA")).toBe(false)
	})

	it("only tells analysts to ask an admin", async () => {
		auth.isAdmin = false
		const wrapper = await render()
		expect(getProvisioning).not.toHaveBeenCalled()
		expect(wrapper.text()).toContain("An admin can set it up")
	})

	it("switches a live customer to learning only", async () => {
		getProvisioning.mockResolvedValue({ data: { ...NOT_SET_UP, onboarding: onboarding("live", { mode: "active" }) } })
		setMode.mockResolvedValue({
			data: { message: "acme: UBA keeps learning", onboarding: onboarding("live", { mode: "learning" }) }
		})
		const wrapper = await render()
		expect(wrapper.text()).toContain("UBA alerts become CoPilot incident alerts")
		await wrapper.find("[data-testid=uba-mode-learning] input").setValue(true)
		await flushPromises()
		expect(setMode).toHaveBeenCalledWith("acme", "learning")
		expect(wrapper.text()).toContain("CoPilot gets no UBA alerts for this customer")
	})

	it("has no mode switch on a UBA without modes", async () => {
		getProvisioning.mockResolvedValue({ data: { ...NOT_SET_UP, onboarding: onboarding("live") } })
		const wrapper = await render()
		expect(wrapper.find("[data-testid=uba-mode]").exists()).toBe(false)
	})

	it("offers the rollback for a set-up customer, and not for one never set up", async () => {
		let wrapper = await render()
		expect(wrapper.find("[data-testid=uba-rollback-open]").exists()).toBe(false)

		getProvisioning.mockResolvedValue({ data: { ...NOT_SET_UP, onboarding: onboarding("live") } })
		wrapper = await render()
		expect(wrapper.find("[data-testid=uba-rollback-open]").text()).toContain("Roll back UBA")
	})

	it("offers the rollback while UBA cannot be reached", async () => {
		getProvisioning.mockRejectedValue({ response: { status: 502, data: { detail: "UBA is unreachable", reason: "unreachable" } } })
		const wrapper = await render()
		expect(wrapper.find("[data-testid=uba-rollback-open]").exists()).toBe(true)
	})

	it("shows the last rollback and offers to finish one that did not complete", async () => {
		getProvisioning.mockResolvedValue({
			data: { ...NOT_SET_UP, onboarding: onboarding("inactive", { active: false }) }
		})
		getRollbacks.mockResolvedValue({
			data: {
				rollbacks: [
					{
						id: 3,
						customer_code: "acme",
						status: "partial",
						started_at: "2026-10-13T10:00:00",
						finished_at: "2026-10-13T10:00:05",
						actor_username: "admin",
						message: "partial"
					}
				]
			}
		})
		const wrapper = await render()
		const text = wrapper.find("[data-testid=uba-rollback]").text()
		expect(text).toContain("by admin: partial")
		expect(text).toContain("View report")
		expect(wrapper.find("[data-testid=uba-rollback-open]").text()).toContain("Finish the rollback")
	})
})

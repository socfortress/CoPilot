import type { UbaProvisioning } from "@/types/uba"
import { flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import UbaSetup from "../UbaSetup.vue"

const getProvisioning = vi.fn()
const provision = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		uba: {
			getProvisioning: (...args: unknown[]) => getProvisioning(...args),
			provision: (...args: unknown[]) => provision(...args)
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
})

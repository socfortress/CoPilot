import type { UbaRuleSettings } from "@/types/uba"
import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import UbaRuleSettingsCard from "../UbaRuleSettings.vue"

const getRuleSettings = vi.fn()
const setRuleSetting = vi.fn()
const resetRuleSetting = vi.fn()
const setAlertThreshold = vi.fn()
const auth = { isAdmin: true }

vi.mock("@/api", () => ({
	default: {
		uba: {
			getRuleSettings: (...a: unknown[]) => getRuleSettings(...a),
			setRuleSetting: (...a: unknown[]) => setRuleSetting(...a),
			resetRuleSetting: (...a: unknown[]) => resetRuleSetting(...a),
			setAlertThreshold: (...a: unknown[]) => setAlertThreshold(...a),
			resetAlertThreshold: vi.fn()
		}
	}
}))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "yyyy-MM-dd HH:mm" } }) }))
vi.mock("naive-ui", async original => ({
	...(await original<typeof import("naive-ui")>()),
	useMessage: () => ({ success: vi.fn(), error: vi.fn() })
}))

function settings(overrides: Partial<UbaRuleSettings["rules"][number]> = {}): UbaRuleSettings {
	return {
		rules: [
			{
				rule_id: "auth.new_country",
				name: "Sign-in from a country never seen for this user",
				category: "auth",
				default_enabled: true,
				default_score: 30,
				enabled: true,
				score: 30,
				customized: false,
				changed_by: null,
				changed_at: null,
				...overrides
			},
			{
				rule_id: "mail.inbox_rule_change",
				name: "Inbox rule created or changed",
				category: "mail",
				default_enabled: true,
				default_score: 15,
				enabled: true,
				score: 15,
				customized: false,
				changed_by: null,
				changed_at: null
			}
		],
		alert_threshold: { value: 100, default: 100, customized: false, changed_by: null, changed_at: null, single_finding: 80 }
	}
}

async function render() {
	const wrapper = mount(UbaRuleSettingsCard, { props: { customerCode: "lab" } })
	await flushPromises()
	return wrapper
}

describe("ubaRuleSettings", () => {
	beforeEach(() => {
		auth.isAdmin = true
		getRuleSettings.mockReset().mockResolvedValue({ data: settings() })
		setRuleSetting.mockReset().mockResolvedValue({ data: settings({ enabled: false, customized: true, changed_by: "admin1" }) })
		resetRuleSetting.mockReset().mockResolvedValue({ data: settings() })
		setAlertThreshold.mockReset().mockResolvedValue({ data: settings() })
	})

	it("lists every rule with its group and the threshold", async () => {
		const text = (await render()).text()
		expect(getRuleSettings).toHaveBeenCalledWith("lab")
		expect(text).toContain("Sign-in from a country never seen for this user")
		expect(text).toContain("Sign-ins")
		expect(text).toContain("Email")
		expect(text).toContain("built in: 100")
		expect(text).not.toMatch(/\s[,.:;)]/)
	})

	it("turning a rule off sends only that, and shows who changed it", async () => {
		const wrapper = await render()
		// The rules' own switches, in the table (the toolbar's filter is a switch too).
		await wrapper.findAll(".n-data-table [role=switch]")[0].trigger("click")
		await flushPromises()
		expect(setRuleSetting).toHaveBeenCalledWith("lab", "auth.new_country", { enabled: false })
		expect(wrapper.text()).toContain("this customer")
		expect(wrapper.text()).toContain("admin1")
	})

	it("points back at the built-in value clear the customer's value", async () => {
		getRuleSettings.mockResolvedValue({ data: settings({ score: 10, customized: true, changed_by: "admin1" }) })
		const wrapper = await render()
		expect(wrapper.text()).toContain("built in 30")
		const input = wrapper.findAll("input").find(i => (i.element as HTMLInputElement).value === "10")
		expect(input).toBeDefined()
		await input?.setValue("30")
		await input?.trigger("blur")
		await flushPromises()
		expect(setRuleSetting).toHaveBeenCalledWith("lab", "auth.new_country", { score: null })
	})

	it("saves the alert threshold", async () => {
		const wrapper = await render()
		const input = wrapper.findAll("input").find(i => (i.element as HTMLInputElement).value === "100")
		expect(input).toBeDefined()
		await input?.setValue("150")
		await input?.trigger("keyup", { key: "Enter" })
		await flushPromises()
		expect(setAlertThreshold).toHaveBeenCalledWith("lab", 150)
	})

	it("analysts read the settings but cannot change them", async () => {
		auth.isAdmin = false
		const wrapper = await render()
		expect(wrapper.text()).toContain("Only admins can change them")
		const ruleSwitches = wrapper.findAll(".n-data-table [role=switch]")
		expect(ruleSwitches.length).toBeGreaterThan(0)
		expect(ruleSwitches.every(s => s.classes().some(c => c.includes("disabled")))).toBe(true)
		expect(wrapper.findAll("button").some(b => b.text() === "Save")).toBe(false)
	})
})

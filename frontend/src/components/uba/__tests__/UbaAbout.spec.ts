import type { UbaAbout } from "@/types/uba"
import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import UbaAboutCard from "../UbaAbout.vue"

const ABOUT: UbaAbout = {
	policy: {
		alert_threshold: 100,
		single_signal_threshold: 80,
		half_life_hours: 72,
		horizon_days: 14,
		repeat_window_hours: 24,
		repeat_decay: 0.5,
		privileged_multiplier: 1.5,
		max_native_per_window: 60
	},
	rule_count: 2,
	categories: [
		{
			id: "auth",
			label: "Sign-ins",
			summary: "How and from where people sign in.",
			rules: [
				{
					id: "auth.impossible_travel",
					name: "Impossible travel between sign-ins",
					description: "Two sign-ins too far apart to travel between.",
					how: "Compares each sign-in with the previous one.",
					score: 45,
					about: "the person or program that acted",
					mitre: ["T1078"],
					enabled: true
				},
				{
					id: "auth.new_device_os",
					name: "Sign-in from a new device type",
					description: "A device type not used before.",
					how: "Learns each user's usual device types for 14 days first.",
					score: 10,
					about: "the person or program that acted",
					mitre: [],
					enabled: true
				}
			]
		}
	]
}

const getAbout = vi.fn()
vi.mock("@/api", () => ({ default: { uba: { getAbout: (...args: unknown[]) => getAbout(...args) } } }))

async function render() {
	const wrapper = mount(UbaAboutCard, { props: { customerCode: "lab" } })
	await flushPromises()
	return wrapper
}

describe("ubaAbout", () => {
	beforeEach(() => {
		localStorage.clear()
		getAbout.mockReset().mockResolvedValue({ data: ABOUT })
	})

	it("explains risk with UBA's own numbers on the first visit", async () => {
		const text = (await render()).text()
		expect(getAbout).toHaveBeenCalledWith("lab")
		expect(text).toContain("when they reach 100 UBA raises an alert")
		expect(text).toContain("halve every 3 days")
		expect(text).toContain("between 10 and 45")
		expect(text).toContain("count 1.5×")
		expect(text).toContain("at most 60 points")
		expect(text).toContain("The 2 rules")
		expect(text).toContain("Sign-ins (2)")
		// Formatting never leaves a space before punctuation ("alert , which").
		expect(text).not.toMatch(/\s[,.:;)]/)
	})

	it("remembers that it was closed and does not load until opened", async () => {
		localStorage.setItem("uba-about-open", "false")
		const wrapper = await render()
		expect(getAbout).not.toHaveBeenCalled()
		expect(wrapper.text()).toContain("What UBA is, how risk adds up")
		await wrapper.find("button").trigger("click")
		await flushPromises()
		expect(getAbout).toHaveBeenCalledOnce()
	})
})

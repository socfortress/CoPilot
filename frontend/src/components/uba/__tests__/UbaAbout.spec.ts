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
const auth = { isAdmin: false }
vi.mock("@/api", () => ({ default: { uba: { getAbout: (...args: unknown[]) => getAbout(...args) } } }))
vi.mock("@/stores/auth", () => ({ useAuthStore: () => auth }))

async function render() {
	const wrapper = mount(UbaAboutCard, { props: { customerCode: "lab" }, attachTo: document.body })
	await flushPromises()
	return wrapper
}

/** Opens the drawer from the bar and returns what it shows (the drawer renders into the body). */
async function open(wrapper: Awaited<ReturnType<typeof render>>) {
	await wrapper.get("[data-testid=uba-about-toggle]").trigger("click")
	await flushPromises()
	return document.body.textContent ?? ""
}

describe("ubaAbout", () => {
	beforeEach(() => {
		auth.isAdmin = false
		document.body.innerHTML = ""
		getAbout.mockReset().mockResolvedValue({ data: ABOUT })
	})

	it("is a slim bar that loads nothing until it is opened", async () => {
		const wrapper = await render()
		expect(wrapper.text()).toContain("What UBA is, how risk adds up")
		expect(getAbout).not.toHaveBeenCalled()
		await open(wrapper)
		expect(getAbout).toHaveBeenCalledOnce()
		expect(getAbout).toHaveBeenCalledWith("lab")
	})

	it("explains risk with UBA's own numbers, in a drawer, one section under the other", async () => {
		const text = await open(await render())
		expect(text).toContain("when they reach 100 UBA raises an alert")
		expect(text).toContain("halve every 3 days")
		expect(text).toContain("between 10 and 45")
		expect(text).toContain("count 1.5×")
		expect(text).toContain("at most 60 points")
		expect(text).toContain("The 2 rules")
		expect(text).toContain("Sign-ins (2)")
		// Formatting never leaves a space before punctuation ("alert , which").
		const drawer = document.querySelector(".n-drawer")?.textContent ?? ""
		expect(drawer).not.toMatch(/\s[,.:;)]/)
		// Sections stack: no side-by-side grid inside the drawer.
		expect(document.querySelector(".n-drawer [class*=grid-cols-2]")).toBeNull()
	})

	it("offers admins the deployment guide, and nobody else", async () => {
		expect(await open(await render())).not.toContain("Deploying UBA")
		document.body.innerHTML = ""
		auth.isAdmin = true
		const text = await open(await render())
		expect(text).toContain("Deploying UBA (admins)")
		expect(text).toContain("create CoPilot's API key for all customers")
	})
})

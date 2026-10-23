/**
 * The toolbar's "What's new": hidden when there is nothing to show, a dot for unread items,
 * the drawer marks them read, and the sign-in modal shows unseen popup items once.
 */

import type { VueWrapper } from "@vue/test-utils"
import type { Announcement } from "@/types/announcements"
import { flushPromises, mount } from "@vue/test-utils"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { resetAnnouncements } from "@/composables/useAnnouncements"
import WhatsNew from "../WhatsNew.vue"

const getAnnouncements = vi.fn()

vi.mock("@/api", () => ({
	default: { announcements: { getAnnouncements: (...args: unknown[]) => getAnnouncements(...args) } }
}))
vi.mock("@/stores/auth", () => ({
	useAuthStore: () => ({ userName: "alice", isRoleGranted: () => true })
}))
vi.mock("@/stores/theme", () => ({ useThemeStore: () => ({ style: { "primary-color": "#00e19d" } }) }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { date: "dd/MM/yyyy" } }) }))
vi.mock("@/components/common/Markdown.vue", () => ({
	default: { props: ["source"], template: "<div class='md'>{{ source }}</div>" }
}))

function announcement(id: string, overrides: Partial<Announcement> = {}): Announcement {
	return {
		id,
		category: "product",
		title: `Title ${id}`,
		summary: `Summary ${id}`,
		body_markdown: "",
		image_url: null,
		image_alt: "",
		cta: null,
		published_at: "2026-10-20T00:00:00+00:00",
		expires_at: null,
		popup: false,
		...overrides
	}
}

function serve(items: Announcement[], enabled = true) {
	getAnnouncements.mockResolvedValue({ data: { success: true, message: "", enabled, announcements: items } })
}

// Unmounted after each test: the composable's state is shared, so a live instance from an
// earlier test would react to the next test's feed.
const mounted: VueWrapper[] = []

async function mountIt() {
	const wrapper = mount(WhatsNew, { attachTo: document.body })
	mounted.push(wrapper)
	await flushPromises()
	return wrapper
}

const body = () => document.body

describe("whatsNew", () => {
	beforeEach(() => {
		getAnnouncements.mockReset()
		localStorage.clear()
		sessionStorage.clear()
		resetAnnouncements()
	})
	afterEach(() => {
		mounted.splice(0).forEach(wrapper => wrapper.unmount())
		document.body.innerHTML = ""
	})

	it("is hidden when announcements are off or there are none", async () => {
		serve([announcement("a")], false)
		expect((await mountIt()).find("[data-testid=whats-new-trigger]").exists()).toBe(false)
		serve([])
		expect((await mountIt()).find("[data-testid=whats-new-trigger]").exists()).toBe(false)
	})

	it("shows a dot for unread items and clears it when the drawer opens", async () => {
		serve([announcement("a"), announcement("b")])
		localStorage.setItem("copilot.announcements.seen.alice", JSON.stringify(["b"]))
		const wrapper = await mountIt()
		const trigger = wrapper.get("[data-testid=whats-new-trigger]")
		expect(trigger.attributes("aria-label")).toBe("What's new (1 unread)")

		await trigger.trigger("click")
		await flushPromises()
		expect(body().querySelector("[data-testid=announcement-a] [data-testid=announcement-new]")).not.toBeNull()
		expect(body().querySelector("[data-testid=announcement-b] [data-testid=announcement-new]")).toBeNull()
		expect(wrapper.get("[data-testid=whats-new-trigger]").attributes("aria-label")).toBe("What's new")
		expect(JSON.parse(localStorage.getItem("copilot.announcements.seen.alice") || "[]").sort()).toEqual(["a", "b"])
	})

	it("opens the modal once for unseen popup items and marks them seen", async () => {
		serve([announcement("p1", { popup: true }), announcement("quiet"), announcement("p2", { popup: true })])
		await mountIt()
		expect(body().querySelector("[data-testid=whats-new-modal]")).not.toBeNull()
		expect(body().querySelector("[data-testid=whats-new-modal-page]")?.textContent?.trim()).toBe("1 of 2")
		expect(body().textContent).toContain("Title p1")
		const seen = JSON.parse(localStorage.getItem("copilot.announcements.seen.alice") || "[]")
		expect(seen.sort()).toEqual(["p1", "p2"])

		// A new page load in the same session does not show it again.
		mounted.splice(0).forEach(wrapper => wrapper.unmount())
		document.body.innerHTML = ""
		await mountIt()
		expect(body().querySelector("[data-testid=whats-new-modal]")).toBeNull()
	})

	it("no modal when every popup item was seen", async () => {
		serve([announcement("p1", { popup: true })])
		localStorage.setItem("copilot.announcements.seen.alice", JSON.stringify(["p1"]))
		await mountIt()
		expect(body().querySelector("[data-testid=whats-new-modal]")).toBeNull()
	})

	it("opens links in a new tab without a referrer, and images send none either", async () => {
		serve([
			announcement("a", {
				cta: { label: "Learn more", url: "https://github.com/socfortress/waf-platform-public" },
				image_url: "https://raw.githubusercontent.com/socfortress/copilot-announcements/main/img/waf.png"
			})
		])
		const wrapper = await mountIt()
		await wrapper.get("[data-testid=whats-new-trigger]").trigger("click")
		await flushPromises()
		const cta = body().querySelector("[data-testid=announcement-cta]")
		expect(cta?.getAttribute("href")).toBe("https://github.com/socfortress/waf-platform-public")
		expect(cta?.getAttribute("target")).toBe("_blank")
		expect(cta?.getAttribute("rel")).toBe("noopener noreferrer")
		expect(body().querySelector("[data-testid=announcement-image]")?.getAttribute("referrerpolicy")).toBe(
			"no-referrer"
		)
	})
})

import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick, ref } from "vue"
import Profile from "../Profile.vue"

const route = vi.hoisted(() => ({ query: {} as Record<string, string> }))
const server = vi.hoisted(() => ({ available: null as any, loadAvailability: vi.fn() }))

vi.mock("vue-router", () => ({ useRoute: () => route }))
vi.mock("@/stores/auth", () => ({
	useAuthStore: () => ({ userRoleName: "Customer_user", userName: "acme.viewer", accessibleCustomers: [], userPic: "" })
}))
vi.mock("@/composables/common/useServerNotifications", () => ({ useServerNotifications: () => server }))

function stub(text: string) {
	return { default: defineComponent({ setup: () => () => h("div", { "data-testid": text }, text) }) }
}
vi.mock("@/components/profile/ProfileSettings.vue", () => stub("pane-settings"))
vi.mock("@/components/profile/NotificationPreferences.vue", () => stub("pane-notifications"))
vi.mock("@/components/auth/ChangePasswordCard.vue", () => stub("pane-password"))
vi.mock("@/components/auth/TotpToggle.vue", () => stub("pane-totp"))
vi.mock("@/components/common/CustomerName.vue", () => stub("customer-name"))

async function render(enabled: boolean) {
	server.loadAvailability.mockImplementation(async () => {
		server.available.value = enabled
		return { enabled }
	})
	const wrapper = mount(Profile)
	await flushPromises()
	return wrapper
}

/** The profile's Notifications tab, which every notification email links to (#1282). */
describe("profile notifications tab", () => {
	beforeEach(() => {
		server.available = ref(false)
		route.query = { tab: "notifications" }
	})

	it("opens the tab from the email's link while notifications are on", async () => {
		const wrapper = await render(true)
		expect(wrapper.find("[data-testid=profile-tab-notifications]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=pane-notifications]").exists()).toBe(true)
	})

	it("shows Settings, not an empty page, when the link is opened while they are off", async () => {
		const wrapper = await render(false)
		expect(wrapper.find("[data-testid=profile-tab-notifications]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=pane-settings]").exists()).toBe(true)
	})

	it("moves to Settings when notifications are switched off while the tab is open", async () => {
		const wrapper = await render(true)
		server.available.value = false
		await nextTick()
		await flushPromises()
		expect(wrapper.find("[data-testid=pane-notifications]").exists()).toBe(false)
		expect(wrapper.find("[data-testid=pane-settings]").exists()).toBe(true)
	})

	it("opens Settings without the query", async () => {
		route.query = {}
		const wrapper = await render(true)
		expect(wrapper.find("[data-testid=pane-settings]").exists()).toBe(true)
	})
})

import type { User } from "@/types/user"
import { flushPromises, mount } from "@vue/test-utils"
import { NDialogProvider, NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h } from "vue"
import UserDetails from "../UserDetails.vue"

/**
 * A user's page shows their customer and tag access to whoever may read it. Another
 * user's access comes from admin-only routes; a non-admin reads their own through the
 * "me" route. A 403 must never be shown as "no customer assigned".
 */

const getUserCustomerAccess = vi.hoisted(() => vi.fn())
const getSettings = vi.hoisted(() => vi.fn())
const getUserTags = vi.hoisted(() => vi.fn())
const getMyEffectiveAccess = vi.hoisted(() => vi.fn())
const viewer = vi.hoisted(() => ({ isAdmin: false, userName: "alice" }))

vi.mock("@/api", () => ({
	default: {
		auth: { getUserCustomerAccess },
		tagRbac: { getSettings, getUserTags, getMyEffectiveAccess },
		users: { getUser: vi.fn() }
	}
}))

vi.mock("@/stores/auth", () => ({ useAuthStore: () => viewer }))
vi.mock("@/stores/settings", () => ({ useSettingsStore: () => ({ dateFormat: { datetime: "dd/MM/yyyy HH:mm" } }) }))

const ALICE: User = { id: 3, username: "alice", email: "alice@x", role_id: 5, role_name: "responder" }
const BOB: User = { id: 4, username: "bob", email: "bob@x", role_id: 2, role_name: "analyst" }

function render(user: User) {
	return mount(
		defineComponent({
			setup: () => () =>
				h(NMessageProvider, null, {
					default: () => h(NDialogProvider, null, { default: () => h(UserDetails, { user }) })
				})
		}),
		{ attachTo: document.body }
	)
}

beforeEach(() => {
	viewer.isAdmin = false
	viewer.userName = "alice"
	getUserCustomerAccess.mockReset().mockResolvedValue({ data: { success: true, customer_codes: ["ACME"] } })
	getSettings.mockReset().mockResolvedValue({ data: { success: true, settings: { enabled: true } } })
	getUserTags.mockReset().mockResolvedValue({ data: { success: true, accessible_tags: [] } })
	getMyEffectiveAccess.mockReset().mockResolvedValue({
		data: {
			success: true,
			accessible_customers: ["ACME", "GLOBEX"],
			accessible_tags: [{ id: 1, tag: "windows" }],
			is_tag_unrestricted: false,
			tag_rbac_enabled: true
		}
	})
	document.body.innerHTML = ""
})

describe("a non-admin on their own page", () => {
	it("sees their customers and tags, read through the me route", async () => {
		const wrapper = render(ALICE)
		await flushPromises()

		expect(getMyEffectiveAccess).toHaveBeenCalledOnce()
		expect(getUserCustomerAccess).not.toHaveBeenCalled()
		expect(getUserTags).not.toHaveBeenCalled()
		expect(wrapper.text()).toContain("ACME")
		expect(wrapper.text()).toContain("GLOBEX")
		expect(wrapper.text()).toContain("windows")
		expect(wrapper.find("[data-testid=user-no-customers]").exists()).toBe(false)
	})

	it("is warned only when they really have no customer", async () => {
		getMyEffectiveAccess.mockResolvedValue({
			data: {
				success: true,
				accessible_customers: [],
				accessible_tags: [],
				is_tag_unrestricted: true,
				tag_rbac_enabled: false
			}
		})
		const wrapper = render(ALICE)
		await flushPromises()

		expect(wrapper.find("[data-testid=user-no-customers]").exists()).toBe(true)
	})
})

describe("a non-admin on someone else's page", () => {
	it("is told the access is the admin's to see, without calling the admin routes", async () => {
		const wrapper = render(BOB)
		await flushPromises()

		expect(getUserCustomerAccess).not.toHaveBeenCalled()
		expect(getUserTags).not.toHaveBeenCalled()
		expect(getSettings).not.toHaveBeenCalled()
		expect(getMyEffectiveAccess).not.toHaveBeenCalled()
		expect(wrapper.find("[data-testid=user-access-hidden]").exists()).toBe(true)
		expect(wrapper.find("[data-testid=user-no-customers]").exists()).toBe(false)
	})
})

describe("an admin", () => {
	it("reads any user's access through the admin routes", async () => {
		viewer.isAdmin = true
		viewer.userName = "root"
		const wrapper = render(BOB)
		await flushPromises()

		expect(getUserCustomerAccess).toHaveBeenCalledWith(BOB.id)
		expect(getMyEffectiveAccess).not.toHaveBeenCalled()
		expect(wrapper.text()).toContain("ACME")
		expect(wrapper.find("[data-testid=user-access-hidden]").exists()).toBe(false)
	})
})

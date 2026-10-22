import { mount } from "@vue/test-utils"
import { NDropdown } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import Avatar from "../Avatar.vue"

const store = vi.hoisted(() => ({ isCustomerAdmin: false, userPic: "" }))
const push = vi.hoisted(() => vi.fn())
vi.mock("@/stores/auth", () => ({ useAuthStore: () => store }))
vi.mock("vue-router", () => ({ useRouter: () => ({ push }) }))

function keys() {
	const options = mount(Avatar).getComponent(NDropdown).props("options") as { key: string }[]
	return options.map(option => option.key)
}

/** The avatar marks a customer admin, whose menu says so and offers Users (#1296). */
describe("avatar menu", () => {
	beforeEach(() => {
		push.mockReset()
	})

	it("has no Users, no role line and no mark for a portal user who administers nothing", () => {
		store.isCustomerAdmin = false
		expect(keys()).toEqual(["route-Profile", "route-Logout"])
		const wrapper = mount(Avatar)
		expect(wrapper.find("[data-testid=toolbar-avatar-admin]").exists()).toBe(false)
		expect(wrapper.get("[data-testid=toolbar-avatar]").attributes("title")).toBeUndefined()
	})

	it("offers Users to a customer admin, between Profile and Logout, under a line naming the role", () => {
		store.isCustomerAdmin = true
		expect(keys()).toEqual(["role", "role-divider", "route-Profile", "route-Users", "route-Logout"])
	})

	it("marks a customer admin's avatar, for screen readers too", () => {
		store.isCustomerAdmin = true
		const wrapper = mount(Avatar)
		expect(wrapper.get("[data-testid=toolbar-avatar-admin]").attributes("aria-label")).toBe("Customer admin")
		expect(wrapper.get("[data-testid=toolbar-avatar]").attributes("title")).toBe("Customer admin")
	})

	it("opens the page a key names", () => {
		store.isCustomerAdmin = true
		mount(Avatar).getComponent(NDropdown).vm.$emit("select", "route-Users")
		expect(push).toHaveBeenCalledWith({ name: "Users" })
	})
})

import type { VNode } from "vue"
import { mount } from "@vue/test-utils"
import { NDropdown } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent } from "vue"
import Avatar from "../Avatar.vue"

const store = vi.hoisted(() => ({ isCustomerAdmin: false, userPic: "", userName: "giulia.bianchi" }))
const push = vi.hoisted(() => vi.fn())
vi.mock("@/stores/auth", () => ({ useAuthStore: () => store }))
vi.mock("vue-router", () => ({ useRouter: () => ({ push }) }))

function options() {
	return mount(Avatar).getComponent(NDropdown).props("options") as { key: string; render?: () => VNode }[]
}

function keys() {
	return options().map(option => option.key)
}

function userCard() {
	const [first] = options()
	expect(first?.key).toBe("signed-in-user")
	return mount(defineComponent({ render: () => first?.render?.() }))
}

/** The toolbar says who is signed in and as what; a customer admin's menu offers Users (#1296). */
describe("avatar", () => {
	beforeEach(() => {
		push.mockReset()
	})

	it("shows a portal user's name and role, with no Users and no admin tag", () => {
		store.isCustomerAdmin = false
		const wrapper = mount(Avatar)
		expect(wrapper.get("[data-testid=toolbar-avatar-name]").text()).toBe("giulia.bianchi")
		expect(wrapper.get("[data-testid=toolbar-avatar-role]").text()).toBe("Portal user")
		expect(wrapper.get("[data-testid=toolbar-avatar]").attributes("title")).toBe("giulia.bianchi · Portal user")
		expect(keys()).toEqual(["signed-in-user", "route-Profile", "route-Logout"])
		expect(userCard().find("[data-testid=toolbar-role]").exists()).toBe(false)
	})

	it("shows a customer admin as such, in the toolbar and on the menu's user card", () => {
		store.isCustomerAdmin = true
		const wrapper = mount(Avatar)
		expect(wrapper.get("[data-testid=toolbar-avatar-role]").text()).toBe("Customer admin")
		expect(wrapper.get("[data-testid=toolbar-avatar-role] span").attributes("style")).toContain("var(--info-color)")
		expect(userCard().get("[data-testid=toolbar-role]").text()).toBe("Customer admin")
	})

	it("offers Users to a customer admin, between Profile and Logout", () => {
		store.isCustomerAdmin = true
		expect(keys()).toEqual(["signed-in-user", "route-Profile", "route-Users", "route-Logout"])
	})

	it("opens the page a key names", () => {
		store.isCustomerAdmin = true
		mount(Avatar).getComponent(NDropdown).vm.$emit("select", "route-Users")
		expect(push).toHaveBeenCalledWith({ name: "Users" })
	})
})

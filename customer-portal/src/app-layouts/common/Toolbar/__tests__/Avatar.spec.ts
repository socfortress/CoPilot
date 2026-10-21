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

/** The avatar menu offers Users only to a customer admin (#1296). */
describe("avatar menu", () => {
	beforeEach(() => {
		push.mockReset()
	})

	it("has no Users for a portal user who administers nothing", () => {
		store.isCustomerAdmin = false
		expect(keys()).toEqual(["route-Profile", "route-Logout"])
	})

	it("offers Users to a customer admin, between Profile and Logout", () => {
		store.isCustomerAdmin = true
		expect(keys()).toEqual(["route-Profile", "route-Users", "route-Logout"])
	})

	it("opens the page a key names", () => {
		store.isCustomerAdmin = true
		mount(Avatar).getComponent(NDropdown).vm.$emit("select", "route-Users")
		expect(push).toHaveBeenCalledWith({ name: "Users" })
	})
})

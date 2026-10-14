import type { User } from "@/types/user"
import { flushPromises, mount } from "@vue/test-utils"
import { NMessageProvider } from "naive-ui"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { defineComponent, h, nextTick } from "vue"
import AssignCustomer from "../AssignCustomer.vue"
import AssignRole from "../AssignRole.vue"

/**
 * User admin and customers (#1219): an analyst or responder is never left without a
 * customer, a role change to one of them carries its customers, and an admin is never
 * offered customers at all.
 */

const assignRole = vi.hoisted(() => vi.fn())
const assignCustomerAccess = vi.hoisted(() => vi.fn())
const getUserCustomerAccess = vi.hoisted(() => vi.fn())
const getCustomers = vi.hoisted(() => vi.fn())

vi.mock("@/api", () => ({
	default: {
		auth: { assignRole, assignCustomerAccess, getUserCustomerAccess },
		customers: { getCustomers }
	}
}))

const ACME = { customer_code: "ACME", customer_name: "Acme" }

function withMessages(component: unknown, props: Record<string, unknown>) {
	return mount(
		defineComponent({
			setup: () => () => h(NMessageProvider, null, { default: () => h(component as never, props) })
		}),
		{ attachTo: document.body }
	)
}

function user(roleName: string, roleId: number): User {
	return { id: 4, username: "bob", email: "bob@x", role_id: roleId, role_name: roleName }
}

beforeEach(() => {
	assignRole.mockReset().mockResolvedValue({ data: { success: true, message: "ok" } })
	assignCustomerAccess.mockReset().mockResolvedValue({ data: { success: true, message: "ok" } })
	getUserCustomerAccess.mockReset().mockResolvedValue({ data: { success: true, customer_codes: [] } })
	getCustomers.mockReset().mockResolvedValue({ data: { success: true, customers: [ACME] } })
	document.body.innerHTML = ""
})

function body(selector: string) {
	return document.body.querySelector(selector) as HTMLElement | null
}

describe("assign role", () => {
	async function open(target: User) {
		const wrapper = withMessages(AssignRole, { user: target })
		await wrapper.get("button").trigger("click")
		await flushPromises()
		return wrapper
	}

	function choose(wrapper: ReturnType<typeof withMessages>, role: string) {
		const select = wrapper.findComponent(AssignRole).vm as unknown as {
			$: { setupState: { formModel: { role: string | null; customerCodes: string[] } } }
		}
		select.$.setupState.formModel.role = role
		return nextTick()
	}

	it("asks for customers when the new role is responder, and sends them with it", async () => {
		const wrapper = await open(user("customer_user", 4))
		await choose(wrapper, "responder")
		// The customer select is loaded on demand.
		await vi.dynamicImportSettled()
		await flushPromises()
		expect(body("[data-testid=user-customers-select]")).not.toBeNull()
		expect((body("[data-testid=assign-role-submit]") as HTMLButtonElement).disabled).toBe(true)

		const state = (
			wrapper.findComponent(AssignRole).vm as unknown as {
				$: { setupState: { formModel: { customerCodes: string[] } } }
			}
		).$.setupState.formModel
		state.customerCodes = ["ACME"]
		await nextTick()
		;(body("[data-testid=assign-role-submit]") as HTMLButtonElement).click()
		await flushPromises()
		expect(assignRole).toHaveBeenCalledWith(4, "responder", ["ACME"])
		wrapper.unmount()
	})

	it("starts from the user's current customers, so promoting an analyst keeps them", async () => {
		getUserCustomerAccess.mockResolvedValue({ data: { success: true, customer_codes: ["ACME"] } })
		const wrapper = await open(user("analyst", 2))
		await choose(wrapper, "responder")
		await flushPromises()
		;(body("[data-testid=assign-role-submit]") as HTMLButtonElement).click()
		await flushPromises()
		expect(assignRole).toHaveBeenCalledWith(4, "responder", ["ACME"])
		wrapper.unmount()
	})

	it("sends no customers for an admin", async () => {
		const wrapper = await open(user("analyst", 2))
		await choose(wrapper, "admin")
		await flushPromises()
		expect(body("[data-testid=user-customers-select]")).toBeNull()
		;(body("[data-testid=assign-role-submit]") as HTMLButtonElement).click()
		await flushPromises()
		expect(assignRole).toHaveBeenCalledWith(4, "admin", undefined)
		wrapper.unmount()
	})
})

describe("assign customers", () => {
	async function open(target: User, current: string[]) {
		getUserCustomerAccess.mockResolvedValue({ data: { success: true, customer_codes: current } })
		const wrapper = withMessages(AssignCustomer, { user: target })
		await wrapper.get("button").trigger("click")
		await flushPromises()
		return wrapper
	}

	it("will not empty an analyst's or responder's customers", async () => {
		for (const [name, id] of [
			["analyst", 2],
			["responder", 5]
		] as const) {
			const wrapper = await open(user(name, id), [])
			expect((body("[data-testid=assign-customers-submit]") as HTMLButtonElement).disabled, name).toBe(true)
			wrapper.unmount()
			document.body.innerHTML = ""
		}
	})

	it("still lets a portal user's customers be emptied", async () => {
		const wrapper = await open(user("customer_user", 4), [])
		expect((body("[data-testid=assign-customers-submit]") as HTMLButtonElement).disabled).toBe(false)
		wrapper.unmount()
	})
})

describe("user menu", () => {
	async function menuKeys(target: User) {
		const { default: UserDropdown } = await import("../UserDropdown.vue")
		const { NDropdown } = await import("naive-ui")
		const wrapper = mount(UserDropdown, { props: { user: target } })
		const options = wrapper.findComponent(NDropdown).props("options") as { key: string }[]
		wrapper.unmount()
		return options.map(option => option.key)
	}

	it("offers no customer assignment for an admin, who sees every customer", async () => {
		expect(await menuKeys(user("admin", 1))).not.toContain("AssignCustomer")
	})

	it("offers it for analysts and responders", async () => {
		expect(await menuKeys(user("analyst", 2))).toContain("AssignCustomer")
		expect(await menuKeys(user("responder", 5))).toContain("AssignCustomer")
	})
})
